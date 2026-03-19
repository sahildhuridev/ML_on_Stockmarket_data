from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta

import requests
import yfinance as yf
from django.utils import timezone


@dataclass
class ProviderPayload:
    source: str
    records: list[dict]


class FinnhubClient:
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self):
        self.api_key = os.getenv("FINNHUB_API_KEY", "").strip()

    def _get(self, path: str, params: dict) -> dict:
        if not self.api_key:
            return {}
        response = requests.get(
            f"{self.BASE_URL}/{path}",
            params={**params, "token": self.api_key},
            timeout=12,
        )
        response.raise_for_status()
        return response.json()

    def fetch_company_news(self, ticker: str, days: int) -> ProviderPayload:
        end = timezone.now().date()
        start = end - timedelta(days=days)
        data = self._get(
            "company-news",
            {"symbol": ticker, "from": start.isoformat(), "to": end.isoformat()},
        )
        return ProviderPayload(source="finnhub_news", records=data if isinstance(data, list) else [])

    def fetch_earnings(self, ticker: str, days: int) -> ProviderPayload:
        end = timezone.now().date()
        start = end - timedelta(days=days)
        data = self._get(
            "calendar/earnings",
            {"symbol": ticker, "from": start.isoformat(), "to": end.isoformat()},
        )
        return ProviderPayload(source="finnhub_earnings", records=data.get("earningsCalendar", []))


class NewsApiClient:
    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self):
        self.api_key = os.getenv("NEWSAPI_API_KEY", "").strip()

    def fetch_news(self, ticker: str, company_name: str, days: int) -> ProviderPayload:
        if not self.api_key:
            return ProviderPayload(source="newsapi_news", records=[])
        end = timezone.now()
        start = end - timedelta(days=days)
        response = requests.get(
            self.BASE_URL,
            params={
                "q": f'"{ticker}" OR "{company_name or ticker}" stock',
                "from": start.date().isoformat(),
                "to": end.date().isoformat(),
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 100,
                "apiKey": self.api_key,
            },
            timeout=12,
        )
        response.raise_for_status()
        return ProviderPayload(source="newsapi_news", records=response.json().get("articles", []))


class YFinanceClient:
    def fetch_prices(self, ticker: str, days: int) -> ProviderPayload:
        frame = yf.download(ticker, period=f"{max(days, 30)}d", interval="1d", progress=False)
        if frame is None or frame.empty:
            return ProviderPayload(source="yfinance_price", records=[])
        if hasattr(frame.columns, "nlevels") and frame.columns.nlevels > 1:
            frame.columns = frame.columns.get_level_values(0)
        frame = frame.reset_index()
        frame.columns = [str(col) for col in frame.columns]
        return ProviderPayload(source="yfinance_price", records=frame.to_dict(orient="records"))

