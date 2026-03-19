from __future__ import annotations

import os
import math
import re
from collections import Counter

import json
import pandas as pd

from .providers import FinnhubClient, NewsApiClient, YFinanceClient
from .storage import dedupe_records, register_artifact, write_json, write_csv, write_parquet

try:
    from pyspark.sql import SparkSession, functions as F
    PYSPARK_AVAILABLE = True
except Exception:  # pragma: no cover
    SparkSession = None
    F = None
    PYSPARK_AVAILABLE = False

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
    TRANSFORMERS_AVAILABLE = True
except Exception:  # pragma: no cover
    AutoModelForSequenceClassification = None
    AutoTokenizer = None
    pipeline = None
    TRANSFORMERS_AVAILABLE = False

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except Exception:  # pragma: no cover
    faiss = None
    np = None
    FAISS_AVAILABLE = False


POSITIVE_WORDS = {"beat", "growth", "surge", "gain", "bullish", "strong", "profit", "rally", "upgrade", "record"}
NEGATIVE_WORDS = {"miss", "drop", "loss", "bearish", "weak", "downgrade", "risk", "decline", "warn", "lawsuit"}


def _clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", value).strip()


def _extract_text(record: dict) -> str:
    return _clean_text(
        " ".join(str(record.get(field, "") or "") for field in ["headline", "summary", "title", "description", "content"])
    )


def _normalize_news_record(record: dict, source: str, ticker: str) -> dict:
    published_at = record.get("datetime") or record.get("publishedAt") or record.get("date") or ""
    source_name = (record.get("source") or {}).get("name") if isinstance(record.get("source"), dict) else record.get("source")
    return {
        "ticker": ticker,
        "source": source,
        "record_type": "news" if "news" in source else "earnings",
        "external_id": str(record.get("id") or record.get("url") or record.get("headline") or record.get("title") or published_at),
        "published_at": str(published_at),
        "title": record.get("headline") or record.get("title") or "",
        "url": record.get("url") or "",
        "text": _extract_text(record),
        "source_name": source_name or source,
        "metadata": record,
    }


def _normalize_price_record(record: dict, ticker: str) -> dict:
    return {
        "ticker": ticker,
        "date": str(record.get("Date") or record.get("date") or ""),
        "open": float(record.get("Open", 0) or 0),
        "high": float(record.get("High", 0) or 0),
        "low": float(record.get("Low", 0) or 0),
        "close": float(record.get("Close", 0) or 0),
        "adj_close": float(record.get("Adj Close", 0) or 0),
        "volume": float(record.get("Volume", 0) or 0),
    }


class FinBertService:
    _classifier = None

    @classmethod
    def _get_classifier(cls):
        if cls._classifier is None and TRANSFORMERS_AVAILABLE:
            model_name = os.getenv("HF_MODEL_NAME", "ProsusAI/finbert")
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            cls._classifier = pipeline("sentiment-analysis", model=model, tokenizer=tokenizer)
        return cls._classifier

    @classmethod
    def score(cls, text: str) -> dict:
        classifier = cls._get_classifier()
        if classifier and text:
            result = classifier(text[:512])[0]
            confidence = float(result.get("score", 0.0))
            label = result.get("label", "neutral").title()
            signed_score = confidence if label == "Positive" else (-confidence if label == "Negative" else 0.0)
            return {"label": label, "confidence": round(confidence, 4), "score_0_10": round(((signed_score + 1) / 2) * 10, 2)}

        words = re.findall(r"[a-zA-Z']+", text.lower())
        positive_hits = sum(1 for word in words if word in POSITIVE_WORDS)
        negative_hits = sum(1 for word in words if word in NEGATIVE_WORDS)
        total = positive_hits + negative_hits
        if total == 0:
            return {"label": "Neutral", "confidence": 0.55, "score_0_10": 5.0}
        confidence = min(0.95, 0.55 + total * 0.04)
        if positive_hits > negative_hits:
            label = "Positive"
            signed_score = confidence
        elif negative_hits > positive_hits:
            label = "Negative"
            signed_score = -confidence
        else:
            label = "Neutral"
            signed_score = 0.0
        return {"label": label, "confidence": round(confidence, 4), "score_0_10": round(((signed_score + 1) / 2) * 10, 2)}


class EmbeddingStore:
    VECTOR_SIZE = 32

    @classmethod
    def _embed(cls, text: str) -> list[float]:
        vector = [0.0] * cls.VECTOR_SIZE
        for token in re.findall(r"[a-zA-Z']+", (text or "").lower()):
            vector[hash(token) % cls.VECTOR_SIZE] += 1.0
        magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [round(value / magnitude, 6) for value in vector]

    @classmethod
    def build(cls, rows: list[dict], output_path: str) -> dict:
        embeddings = [cls._embed(row.get("text", "")) for row in rows]
        metadata = [
            {
                "external_id": row.get("external_id"),
                "published_at": row.get("published_at"),
                "label": row.get("label"),
                "title": row.get("title"),
            }
            for row in rows
        ]
        if FAISS_AVAILABLE and embeddings:
            index = faiss.IndexFlatL2(cls.VECTOR_SIZE)
            index.add(np.array(embeddings, dtype="float32"))
            faiss.write_index(index, output_path)
            return {"backend": "faiss", "vectors": len(embeddings), "metadata": metadata}
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump({"vectors": embeddings, "metadata": metadata}, handle, indent=2)
        return {"backend": "json-fallback", "vectors": len(embeddings), "metadata": metadata}


class SentimentPipeline:
    def __init__(self, job):
        self.job = job
        self.finnhub = FinnhubClient()
        self.newsapi = NewsApiClient()
        self.yfinance = YFinanceClient()

    def fetch_sources(self) -> tuple[list[dict], list[dict], dict]:
        ticker = self.job.ticker
        company_name = self.job.company_name
        window_days = self.job.window_days

        news_payloads = [
            self.finnhub.fetch_company_news(ticker, window_days),
            self.newsapi.fetch_news(ticker, company_name, window_days),
            self.finnhub.fetch_earnings(ticker, window_days),
            self.yfinance.fetch_news(ticker),
        ]
        price_payload = self.yfinance.fetch_prices(ticker, window_days)

        news_rows = []
        for payload in news_payloads:
            news_rows.extend(_normalize_news_record(record, payload.source, ticker) for record in payload.records)

        price_rows = [_normalize_price_record(record, ticker) for record in price_payload.records]
        return (
            news_rows,
            price_rows,
            {
                "news_records": len(news_rows),
                "price_records": len(price_rows),
                "sources": {payload.source: len(payload.records) for payload in news_payloads},
            },
        )

    def write_bronze(self, news_rows: list[dict], price_rows: list[dict]) -> None:
        news_json = write_json(self.job, "bronze", "news_raw", news_rows)
        news_csv = write_csv(self.job, "bronze", "news_raw", news_rows)
        price_json = write_json(self.job, "bronze", "prices_raw", price_rows)
        price_csv = write_csv(self.job, "bronze", "prices_raw", price_rows)

        register_artifact(self.job, "bronze", "news_raw", news_json, "json", len(news_rows))
        register_artifact(self.job, "bronze", "news_raw_table", news_csv, "csv", len(news_rows))
        register_artifact(self.job, "bronze", "prices_raw", price_json, "json", len(price_rows))
        register_artifact(self.job, "bronze", "prices_raw_table", price_csv, "csv", len(price_rows))

    def build_silver(self, news_rows: list[dict]) -> list[dict]:
        if not news_rows:
            raise ValueError("No sentiment articles or earnings records were returned by Finnhub, NewsAPI, or Yahoo Finance.")

        if PYSPARK_AVAILABLE and news_rows:
            spark = SparkSession.builder.master("local[*]").appName("sentiment-analysis").getOrCreate()
            try:
                frame = spark.createDataFrame(news_rows)
                frame = frame.withColumn("text", F.trim(F.regexp_replace(F.col("text"), r"\s+", " ")))
                frame = frame.withColumn("text_length", F.length(F.col("text")))
                frame = frame.withColumn("content_key", F.sha2(F.concat_ws("||", "ticker", "source", "title", "published_at"), 256))
                frame = frame.dropDuplicates(["content_key"])
                silver_rows = [row.asDict() for row in frame.collect()]
            finally:
                spark.stop()
        else:
            seen = set()
            silver_rows = []
            for row in news_rows:
                clean_row = {**row, "text": _clean_text(row.get("text", ""))}
                content_key = f"{clean_row['ticker']}|{clean_row['source']}|{clean_row['title']}|{clean_row['published_at']}"
                if content_key in seen or not clean_row["text"]:
                    continue
                seen.add(content_key)
                clean_row["content_key"] = content_key
                clean_row["text_length"] = len(clean_row["text"])
                silver_rows.append(clean_row)

        silver_rows = dedupe_records(silver_rows)
        silver_path, silver_format = write_parquet(self.job, "silver", "normalized_news", silver_rows)
        register_artifact(self.job, "silver", "normalized_news", silver_path, silver_format, len(silver_rows), {"engine": "pyspark" if PYSPARK_AVAILABLE else "pandas"})
        if not silver_rows:
            raise ValueError("Raw sentiment records were fetched, but no usable text remained after cleaning and deduplication.")
        return silver_rows

    def build_gold(self, silver_rows: list[dict], price_rows: list[dict]) -> dict:
        gold_rows = [{**row, **FinBertService.score(row.get("text", ""))} for row in silver_rows]
        gold_path, gold_format = write_parquet(self.job, "gold", "sentiment_scores", gold_rows)
        register_artifact(
            self.job,
            "gold",
            "sentiment_scores",
            gold_path,
            gold_format,
            len(gold_rows),
            {"model": os.getenv("HF_MODEL_NAME", "ProsusAI/finbert") if TRANSFORMERS_AVAILABLE else "lexicon-fallback"},
        )
        return {"gold_rows": gold_rows, "summary": self._aggregate(gold_rows, price_rows)}

    def _aggregate(self, gold_rows: list[dict], price_rows: list[dict]) -> dict:
        if not gold_rows:
            return {
                "summary": {"overall_sentiment": "Neutral", "confidence": 0.0, "score": 5.0, "momentum": "Stable", "risk_indicator": "Unknown", "article_count": 0},
                "distribution": [],
                "daily_trend": [],
                "weekly_trend": [],
                "correlation": {"value": 0.0, "direction": "flat"},
                "news_feed": [],
                "word_cloud": [],
            }

        news_df = pd.DataFrame(gold_rows)
        news_df["published_at"] = pd.to_datetime(news_df["published_at"], errors="coerce")
        news_df["date"] = news_df["published_at"].dt.date.astype(str)
        news_df["week"] = news_df["published_at"].dt.to_period("W").astype(str)
        score_map = {"Positive": 1, "Neutral": 0, "Negative": -1}
        news_df["signed_score"] = news_df["label"].map(score_map).fillna(0) * news_df["confidence"].fillna(0)

        label_counts = news_df["label"].value_counts().to_dict()
        overall_signed = float(news_df["signed_score"].mean()) if not news_df.empty else 0.0
        overall_label = "Positive" if overall_signed > 0.15 else "Negative" if overall_signed < -0.15 else "Neutral"
        overall_confidence = float(news_df["confidence"].mean()) if not news_df.empty else 0.0
        overall_score = float(news_df["score_0_10"].mean()) if not news_df.empty else 5.0

        daily = news_df.groupby("date").agg(avg_score=("score_0_10", "mean"), article_count=("external_id", "count")).reset_index().sort_values("date")
        weekly = news_df.groupby("week").agg(avg_score=("score_0_10", "mean"), article_count=("external_id", "count")).reset_index().sort_values("week")

        correlation_value = 0.0
        correlation_direction = "flat"
        price_df = pd.DataFrame(price_rows)
        if not price_df.empty:
            price_df["date"] = pd.to_datetime(price_df["date"], errors="coerce").dt.date.astype(str)
            price_df["close"] = pd.to_numeric(price_df["close"], errors="coerce")
            price_df["daily_return"] = price_df["close"].pct_change().fillna(0)
            merged = daily.merge(price_df[["date", "daily_return", "close"]], on="date", how="inner")
            if len(merged) > 1:
                correlation_value = float(merged["avg_score"].corr(merged["daily_return"]))
                if math.isnan(correlation_value):
                    correlation_value = 0.0
                correlation_direction = "positive" if correlation_value > 0.15 else "negative" if correlation_value < -0.15 else "flat"

        momentum_delta = float(daily["avg_score"].tail(3).mean() - daily["avg_score"].head(3).mean()) if len(daily) >= 2 else 0.0
        momentum = "Improving" if momentum_delta > 0.3 else "Weakening" if momentum_delta < -0.3 else "Stable"
        negative_share = label_counts.get("Negative", 0) / len(gold_rows)
        risk_indicator = "High" if negative_share > 0.45 else "Moderate" if negative_share > 0.2 else "Low"

        words = Counter()
        for text in news_df["text"].tolist():
            for token in re.findall(r"[a-zA-Z']+", text.lower()):
                if len(token) > 3:
                    words[token] += 1

        distribution = [{"label": label, "value": count, "percentage": round((count / len(gold_rows)) * 100, 2)} for label, count in label_counts.items()]
        news_feed = news_df.sort_values("published_at", ascending=False)[["title", "source", "published_at", "label", "confidence", "score_0_10", "url"]].head(20).fillna("").to_dict(orient="records")

        return {
            "summary": {
                "overall_sentiment": overall_label,
                "confidence": round(overall_confidence, 4),
                "score": round(overall_score, 2),
                "momentum": momentum,
                "risk_indicator": risk_indicator,
                "article_count": int(len(gold_rows)),
            },
            "distribution": distribution,
            "daily_trend": daily.to_dict(orient="records"),
            "weekly_trend": weekly.to_dict(orient="records"),
            "correlation": {"value": round(correlation_value, 4), "direction": correlation_direction},
            "news_feed": news_feed,
            "word_cloud": [{"text": word, "value": count} for word, count in words.most_common(30)],
        }
