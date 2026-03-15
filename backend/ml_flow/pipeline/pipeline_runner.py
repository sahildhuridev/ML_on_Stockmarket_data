"""
ML Pipeline Runner
------------------
Orchestrates the ML workflow and exact-date/time forecasting.
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timedelta, timezone as dt_timezone

import pandas as pd
from django.utils import timezone

from portfolios.models import Portfolio
from ml_flow.models import (
    PipelineRun,
    Prediction,
    HourlyPrediction,
    ForecastRequest,
    ForecastPrediction,
    SingleStockForecast,
)
from ml_flow.pipeline.ingestion.data_ingestion import DataIngestion
from ml_flow.pipeline.validation.data_validation import DataValidator
from ml_flow.pipeline.features.feature_engineering import FeatureEngineer
from ml_flow.pipeline.training.train_models import ModelTrainer
from ml_flow.pipeline.evaluation.evaluate_models import ModelEvaluator
from ml_flow.pipeline.tracking.mlflow_tracker import MLflowTracker

logger = logging.getLogger(__name__)


class MLPipelineRunner:
    """End-to-end ML pipeline and forecast orchestration."""

    INTERVAL_TO_DELTA = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "30m": timedelta(minutes=30),
        "1h": timedelta(hours=1),
        "1d": timedelta(days=1),
        "1wk": timedelta(weeks=1),
    }

    @staticmethod
    def run_pipeline(
        portfolio_id: int,
        interval: str = "1h",
        training_days: int = 30,
        user=None,
    ) -> dict:
        """Execute the ML workflow for every stock in a portfolio."""
        portfolio = MLPipelineRunner._get_portfolio(portfolio_id, user=user)
        stocks = portfolio.stocks.all()
        if not stocks.exists():
            raise ValueError(f"Portfolio '{portfolio.name}' has no stocks")

        verification_summary = MLPipelineRunner._verify_pending_predictions(portfolio)
        due_forecasts = MLPipelineRunner.resolve_due_forecasts(user=user, portfolio=portfolio)

        pipeline_run = PipelineRun.objects.create(
            portfolio=portfolio,
            triggered_by=user,
            status="running",
            interval=interval,
            training_days=training_days,
        )

        period = f"{training_days}d"
        stock_results = []

        try:
            for stock in stocks:
                ticker = stock.ticker
                try:
                    result = MLPipelineRunner._process_single_stock(
                        ticker=ticker,
                        period=period,
                        interval=interval,
                        training_days=training_days,
                        pipeline_run_id=pipeline_run.pk,
                    )
                    stock_results.append(result)

                    Prediction.objects.create(
                        pipeline_run=pipeline_run,
                        ticker=ticker,
                        current_price=result["current_price"],
                        predicted_price=result["predicted_price"],
                        best_model=result["best_model"],
                        metrics=result["metrics"],
                    )

                    for model_name, pred_price in result.get("per_model_predictions", {}).items():
                        HourlyPrediction.objects.create(
                            pipeline_run=pipeline_run,
                            ticker=ticker,
                            model_name=model_name,
                            predicted_price=pred_price,
                            current_price_at_prediction=result["current_price"],
                            status="pending",
                        )
                except Exception as exc:
                    logger.exception("Pipeline failed for %s", ticker)
                    stock_results.append({"ticker": ticker, "error": str(exc)})

            success_count = len([item for item in stock_results if not item.get("error")])
            error_count = len(stock_results) - success_count
            pipeline_run.finished_at = timezone.now()
            pipeline_run.results_json = stock_results

            if success_count and error_count:
                pipeline_run.status = "partial"
                pipeline_run.error_message = f"{error_count} stock(s) failed during execution."
            elif success_count:
                pipeline_run.status = "completed"
                pipeline_run.error_message = None
            else:
                pipeline_run.status = "failed"
                pipeline_run.error_message = "All stock predictions failed."

            pipeline_run.save()
        except Exception as exc:
            pipeline_run.status = "failed"
            pipeline_run.finished_at = timezone.now()
            pipeline_run.error_message = str(exc)
            pipeline_run.results_json = stock_results
            pipeline_run.save()
            raise

        model_ranking = MLPipelineRunner._build_model_ranking(portfolio)
        return {
            "portfolio": portfolio.name,
            "pipeline_run_id": pipeline_run.pk,
            "status": pipeline_run.status,
            "results": stock_results,
            "verification_summary": verification_summary,
            "due_forecasts_resolved": due_forecasts,
            "model_ranking": model_ranking,
        }

    @staticmethod
    def create_forecast(
        portfolio_id: int,
        target_datetime: datetime,
        prediction_scope: str = "portfolio",
        ticker: str | None = None,
        interval: str = "1h",
        training_days: int = 30,
        user=None,
    ) -> ForecastRequest:
        """Create a forecast request for an exact target datetime."""
        portfolio = MLPipelineRunner._get_portfolio(portfolio_id, user=user)
        target_datetime = MLPipelineRunner._normalize_datetime(target_datetime)
        resolved_target_datetime, alignment_note = MLPipelineRunner._align_target_datetime(
            target_datetime, interval
        )

        available_tickers = list(portfolio.stocks.values_list("ticker", flat=True))
        if prediction_scope == "single_stock":
            if not ticker:
                raise ValueError("Ticker is required for a single stock forecast.")
            ticker = ticker.upper()
            if ticker not in available_tickers:
                raise ValueError(f"Ticker '{ticker}' is not part of portfolio '{portfolio.name}'.")
            tickers = [ticker]
        else:
            if not available_tickers:
                raise ValueError(f"Portfolio '{portfolio.name}' has no stocks")
            tickers = available_tickers

        forecast_request = ForecastRequest.objects.create(
            portfolio=portfolio,
            created_by=user,
            prediction_scope=prediction_scope,
            interval=interval,
            training_days=training_days,
            requested_tickers=tickers,
            target_datetime=target_datetime,
            resolved_target_datetime=resolved_target_datetime,
            status="pending",
        )

        prediction_summaries = []
        errors = []
        period = f"{training_days}d"

        for symbol in tickers:
            try:
                result = MLPipelineRunner._forecast_single_stock(
                    ticker=symbol,
                    period=period,
                    interval=interval,
                    training_days=training_days,
                    target_datetime=resolved_target_datetime,
                )
                ForecastPrediction.objects.create(
                    forecast_request=forecast_request,
                    ticker=symbol,
                    best_model=result["best_model"],
                    current_price_at_request=result["current_price"],
                    predicted_price=result["predicted_price"],
                    model_predictions=result["per_model_predictions"],
                    model_metrics=result["all_model_metrics"],
                    status="pending",
                )
                prediction_summaries.append(result)
            except Exception as exc:
                logger.exception("Forecast creation failed for %s", symbol)
                errors.append({"ticker": symbol, "error": str(exc)})

        if prediction_summaries:
            forecast_request.status = "pending" if not errors else "partial"
            forecast_request.error_message = None if not errors else f"{len(errors)} stock(s) failed during forecasting."
            forecast_request.results_json = {
                "alignment_note": alignment_note,
                "summary": MLPipelineRunner._summarize_forecast_results(prediction_summaries),
                "stock_results": prediction_summaries,
                "errors": errors or None,
            }
        else:
            forecast_request.status = "failed"
            forecast_request.error_message = errors[0]["error"] if errors else "Forecast generation failed."
            forecast_request.results_json = {
                "alignment_note": alignment_note,
                "summary": {},
                "stock_results": [],
                "errors": errors or None,
            }

        forecast_request.save()
        return forecast_request

    @staticmethod
    def create_single_stock_forecast(
        ticker: str,
        company_name: str,
        target_datetime: datetime,
        interval: str = "1h",
        training_days: int = 30,
        user=None,
    ) -> SingleStockForecast:
        """Create an exact datetime forecast for one stock."""
        target_datetime = MLPipelineRunner._normalize_datetime(target_datetime)
        resolved_target_datetime, alignment_note = MLPipelineRunner._align_target_datetime(
            target_datetime, interval
        )

        result = MLPipelineRunner._forecast_single_stock(
            ticker=ticker,
            period=f"{training_days}d",
            interval=interval,
            training_days=training_days,
            target_datetime=resolved_target_datetime,
        )

        current_price = result["current_price"]
        predicted_price = result["predicted_price"]
        forecast = SingleStockForecast.objects.create(
            created_by=user,
            ticker=ticker.upper(),
            company_name=company_name or ticker.upper(),
            interval=interval,
            training_days=training_days,
            target_datetime=target_datetime,
            resolved_target_datetime=resolved_target_datetime,
            status="pending",
            current_price=current_price,
            predicted_price=predicted_price,
            best_model=result["best_model"],
            model_predictions=result["per_model_predictions"],
            model_metrics=result["all_model_metrics"],
            steps_ahead=result["steps_ahead"],
            results_json={
                "alignment_note": alignment_note,
                "summary": {
                    "ticker": ticker.upper(),
                    "company_name": company_name or ticker.upper(),
                    "current_price": current_price,
                    "predicted_price": predicted_price,
                    "predicted_change": round(predicted_price - current_price, 4),
                    "predicted_change_pct": round(
                        ((predicted_price - current_price) / current_price * 100) if current_price else 0,
                        4,
                    ),
                    "target_datetime": resolved_target_datetime.isoformat(),
                    "steps_ahead": result["steps_ahead"],
                    "best_model": result["best_model"],
                },
            },
        )
        return forecast

    @staticmethod
    def resolve_due_forecasts(user=None, portfolio=None, portfolio_id: int | None = None) -> dict:
        """Resolve all forecast requests that are due for verification."""
        now = timezone.now()
        queryset = ForecastRequest.objects.filter(
            status__in=["pending", "partial"],
            resolved_target_datetime__lte=now,
        ).prefetch_related("forecast_predictions", "portfolio")

        if portfolio is not None:
            queryset = queryset.filter(portfolio=portfolio)
        elif portfolio_id is not None:
            queryset = queryset.filter(portfolio_id=portfolio_id)

        if user is not None:
            queryset = queryset.filter(portfolio__user=user)

        resolved = 0
        partial = 0
        expired = 0
        failures = []

        for forecast_request in queryset:
            try:
                status = MLPipelineRunner._resolve_single_forecast_request(forecast_request)
                if status == "resolved":
                    resolved += 1
                elif status == "partial":
                    partial += 1
                elif status == "expired":
                    expired += 1
            except Exception as exc:
                logger.exception("Failed to resolve forecast request %s", forecast_request.pk)
                failures.append({"forecast_request_id": forecast_request.pk, "error": str(exc)})

        return {
            "resolved": resolved,
            "partial": partial,
            "expired": expired,
            "failures": failures or None,
        }

    @staticmethod
    def resolve_due_single_stock_forecasts(user=None) -> dict:
        """Resolve all due single-stock forecasts against market data."""
        now = timezone.now()
        queryset = SingleStockForecast.objects.filter(
            status="pending",
            resolved_target_datetime__lte=now,
        )
        if user is not None:
            queryset = queryset.filter(created_by=user)

        resolved = 0
        expired = 0
        failures = []

        for forecast in queryset:
            try:
                actual_price, actual_ts = MLPipelineRunner._get_price_near_datetime(
                    forecast.ticker,
                    forecast.resolved_target_datetime or forecast.target_datetime,
                    forecast.interval,
                )
                if actual_price is None:
                    if now > (forecast.resolved_target_datetime or forecast.target_datetime) + (
                        MLPipelineRunner._get_interval_delta(forecast.interval) * 2
                    ):
                        forecast.status = "expired"
                        forecast.resolved_at = timezone.now()
                        forecast.save(update_fields=["status", "resolved_at"])
                        expired += 1
                    continue

                forecast.actual_price = actual_price
                forecast.actual_price_timestamp = actual_ts
                forecast.absolute_error = round(abs(actual_price - (forecast.predicted_price or 0)), 4)
                forecast.pct_error = round(
                    (forecast.absolute_error / actual_price * 100) if actual_price else 0,
                    4,
                )
                actual_direction = actual_price - (forecast.current_price or 0)
                predicted_direction = (forecast.predicted_price or 0) - (forecast.current_price or 0)
                forecast.direction_match = (
                    math.copysign(1, actual_direction) == math.copysign(1, predicted_direction)
                    if actual_direction != 0 and predicted_direction != 0
                    else actual_direction == predicted_direction
                )
                forecast.status = "resolved"
                forecast.resolved_at = timezone.now()
                forecast.results_json = {
                    **(forecast.results_json or {}),
                    "analysis": {
                        "actual_price": round(actual_price, 4),
                        "actual_price_timestamp": actual_ts.isoformat() if actual_ts else None,
                        "absolute_error": forecast.absolute_error,
                        "pct_error": forecast.pct_error,
                        "direction_match": forecast.direction_match,
                    },
                }
                forecast.save()
                resolved += 1
            except Exception as exc:
                logger.exception("Failed to resolve single-stock forecast %s", forecast.pk)
                failures.append({"forecast_id": forecast.pk, "error": str(exc)})

        return {
            "resolved": resolved,
            "expired": expired,
            "failures": failures or None,
        }

    @staticmethod
    def _resolve_single_forecast_request(forecast_request: ForecastRequest) -> str:
        """Resolve a single forecast request against market data."""
        target_datetime = forecast_request.resolved_target_datetime or forecast_request.target_datetime
        target_datetime = MLPipelineRunner._normalize_datetime(target_datetime)
        delta = MLPipelineRunner._get_interval_delta(forecast_request.interval)
        verified_count = 0
        pending_count = 0
        expired_count = 0

        for prediction in forecast_request.forecast_predictions.filter(status="pending"):
            actual_price, actual_ts = MLPipelineRunner._get_price_near_datetime(
                prediction.ticker,
                target_datetime,
                forecast_request.interval,
            )
            if actual_price is None:
                if timezone.now() > target_datetime + (delta * 2):
                    prediction.status = "expired"
                    prediction.verified_at = timezone.now()
                    prediction.save(update_fields=["status", "verified_at"])
                    expired_count += 1
                else:
                    pending_count += 1
                continue

            prediction.actual_price = actual_price
            prediction.actual_price_timestamp = actual_ts
            prediction.absolute_error = round(abs(actual_price - prediction.predicted_price), 4)
            prediction.pct_error = round(
                (prediction.absolute_error / actual_price * 100) if actual_price else 0,
                4,
            )

            actual_direction = actual_price - prediction.current_price_at_request
            predicted_direction = prediction.predicted_price - prediction.current_price_at_request
            prediction.direction_match = (
                math.copysign(1, actual_direction) == math.copysign(1, predicted_direction)
                if actual_direction != 0 and predicted_direction != 0
                else actual_direction == predicted_direction
            )
            prediction.status = "verified"
            prediction.verified_at = timezone.now()
            prediction.save()
            verified_count += 1

        predictions = list(forecast_request.forecast_predictions.all())
        if predictions and all(p.status == "verified" for p in predictions):
            forecast_request.status = "resolved"
            forecast_request.resolved_at = timezone.now()
        elif predictions and any(p.status == "verified" for p in predictions):
            forecast_request.status = "partial"
            forecast_request.resolved_at = timezone.now()
        elif predictions and all(p.status == "expired" for p in predictions):
            forecast_request.status = "expired"
            forecast_request.resolved_at = timezone.now()

        summary = MLPipelineRunner._build_forecast_analysis(predictions)
        existing = forecast_request.results_json or {}
        existing["analysis"] = summary
        existing["verification"] = {
            "verified_count": verified_count,
            "pending_count": pending_count,
            "expired_count": expired_count,
        }
        forecast_request.results_json = existing
        forecast_request.save(update_fields=["status", "resolved_at", "results_json"])
        return forecast_request.status

    @staticmethod
    def _get_portfolio(portfolio_id: int, user=None) -> Portfolio:
        filters = {"id": portfolio_id}
        if user is not None:
            filters["user"] = user
        try:
            return Portfolio.objects.get(**filters)
        except Portfolio.DoesNotExist:
            raise ValueError(f"Portfolio with id={portfolio_id} does not exist")

    @staticmethod
    def _verify_pending_predictions(portfolio) -> dict:
        """Verify the next-run hourly predictions against the current market price."""
        pending = HourlyPrediction.objects.filter(
            pipeline_run__portfolio=portfolio,
            status="pending",
        )

        if not pending.exists():
            return {"verified_count": 0, "message": "No pending predictions to verify"}

        tickers = set(pending.values_list("ticker", flat=True))
        verified_count = 0
        errors = []

        for ticker in tickers:
            try:
                actual_price = MLPipelineRunner._get_current_price(ticker)
                if actual_price is None:
                    continue

                now = timezone.now()
                for hp in pending.filter(ticker=ticker):
                    abs_err = abs(actual_price - hp.predicted_price)
                    pct_err = (abs_err / actual_price * 100) if actual_price else 0
                    hp.actual_price = actual_price
                    hp.absolute_error = round(abs_err, 4)
                    hp.pct_error = round(pct_err, 4)
                    hp.status = "verified"
                    hp.verified_at = now
                    hp.save()
                    verified_count += 1
            except Exception as exc:
                logger.warning("Could not verify predictions for %s: %s", ticker, exc)
                errors.append(f"{ticker}: {exc}")

        return {
            "verified_count": verified_count,
            "tickers_verified": list(tickers),
            "errors": errors if errors else None,
        }

    @staticmethod
    def _get_current_price(ticker: str) -> float | None:
        """Fetch current price via yfinance (latest intraday, then daily fallback)."""
        try:
            import yfinance as yf

            data = yf.download(ticker, period="1d", interval="1m", progress=False)
            if data is not None and not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                close = data["Close"]
                return float(close.iloc[-1].item() if hasattr(close.iloc[-1], "item") else close.iloc[-1])

            data = yf.download(ticker, period="5d", interval="1d", progress=False)
            if data is not None and not data.empty:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                close = data["Close"]
                return float(close.iloc[-1].item() if hasattr(close.iloc[-1], "item") else close.iloc[-1])
            return None
        except Exception as exc:
            logger.warning("Could not fetch price for %s: %s", ticker, exc)
            return None

    @staticmethod
    def _build_model_ranking(portfolio) -> list[dict]:
        """Rank models by average percentage error across verified hourly predictions."""
        verified = HourlyPrediction.objects.filter(
            pipeline_run__portfolio=portfolio,
            status="verified",
        )
        if not verified.exists():
            return []

        from collections import defaultdict

        model_stats = defaultdict(lambda: {"errors": [], "abs_errors": []})
        for hp in verified:
            if hp.pct_error is not None:
                model_stats[hp.model_name]["errors"].append(hp.pct_error)
            if hp.absolute_error is not None:
                model_stats[hp.model_name]["abs_errors"].append(hp.absolute_error)

        ranking = []
        for model_name, stats in model_stats.items():
            errors = stats["errors"] or [0]
            abs_errors = stats["abs_errors"] or [0]
            ranking.append({
                "model_name": model_name,
                "avg_pct_error": round(sum(errors) / len(errors), 4),
                "avg_abs_error": round(sum(abs_errors) / len(abs_errors), 4),
                "min_pct_error": round(min(errors), 4),
                "max_pct_error": round(max(errors), 4),
                "total_predictions": len(errors),
            })

        ranking.sort(key=lambda item: item["avg_pct_error"])
        for idx, item in enumerate(ranking, start=1):
            item["rank"] = idx
        return ranking

    @staticmethod
    def _process_single_stock(
        ticker: str,
        period: str,
        interval: str,
        training_days: int = 30,
        pipeline_run_id: int | None = None,
    ) -> dict:
        """Run the training and next-step prediction flow for a single ticker."""
        stack = MLPipelineRunner._prepare_model_stack(
            ticker=ticker,
            period=period,
            interval=interval,
            training_days=training_days,
            pipeline_run_id=pipeline_run_id,
        )
        return {
            "ticker": ticker,
            "current_price": round(stack["current_price"], 4),
            "predicted_price": round(stack["predicted_price"], 4),
            "best_model": stack["best_model_name"],
            "metrics": stack["evaluation"]["metrics"].get(stack["best_model_name"], {}),
            "all_model_metrics": stack["evaluation"]["metrics"],
            "validation_report": stack["validation_report"],
            "per_model_predictions": stack["per_model_predictions"],
        }

    @staticmethod
    def _forecast_single_stock(
        ticker: str,
        period: str,
        interval: str,
        training_days: int,
        target_datetime: datetime,
    ) -> dict:
        """Generate a horizon-based forecast for a single stock."""
        stack = MLPipelineRunner._prepare_model_stack(
            ticker=ticker,
            period=period,
            interval=interval,
            training_days=training_days,
        )
        last_market_timestamp = MLPipelineRunner._normalize_datetime(stack["feature_df"].index[-1].to_pydatetime())
        steps_ahead = MLPipelineRunner._calculate_forecast_steps(
            last_market_timestamp,
            target_datetime,
            interval,
        )

        horizon_predictions = {}
        for model_name, model_data in stack["models"].items():
            try:
                horizon_predictions[model_name] = round(
                    MLPipelineRunner._predict_horizon(
                        model_name=model_name,
                        model_data=model_data,
                        feature_df=stack["feature_df"],
                        base_df=stack["clean_df"],
                        steps=steps_ahead,
                        interval=interval,
                    ),
                    4,
                )
            except Exception as exc:
                logger.warning("Future prediction failed for %s/%s: %s", ticker, model_name, exc)

        predicted_price = horizon_predictions.get(stack["best_model_name"], stack["current_price"])
        return {
            "ticker": ticker,
            "current_price": round(stack["current_price"], 4),
            "predicted_price": round(predicted_price, 4),
            "best_model": stack["best_model_name"],
            "all_model_metrics": stack["evaluation"]["metrics"],
            "per_model_predictions": horizon_predictions,
            "steps_ahead": steps_ahead,
            "last_market_timestamp": last_market_timestamp.isoformat(),
        }

    @staticmethod
    def _prepare_model_stack(
        ticker: str,
        period: str,
        interval: str,
        training_days: int,
        pipeline_run_id: int | None = None,
    ) -> dict:
        """Prepare the training stack and MLflow tracking for a ticker."""
        logger.info("[%s] Stage 1: Data Ingestion", ticker)
        raw_df = DataIngestion.fetch(ticker, period=period, interval=interval)

        logger.info("[%s] Stage 2: Data Validation", ticker)
        clean_df, validation_report = DataValidator.validate(raw_df)

        logger.info("[%s] Stage 3: Feature Engineering", ticker)
        feature_df = FeatureEngineer.generate(clean_df)

        logger.info("[%s] Stage 4: Model Training", ticker)
        feature_columns = FeatureEngineer.FEATURE_COLUMNS
        train_start = time.time()
        models = ModelTrainer.train(feature_df, feature_columns)
        train_duration = time.time() - train_start

        logger.info("[%s] Stage 5: Model Evaluation", ticker)
        evaluation = ModelEvaluator.evaluate(models)
        best_model_name = evaluation["best_model"]
        if not best_model_name:
            raise ValueError("No best model could be selected")

        current_price = float(feature_df["Close"].iloc[-1])
        per_model_predictions = {}
        for model_name, model_data in models.items():
            try:
                per_model_predictions[model_name] = round(
                    MLPipelineRunner._predict_next(model_name, model_data, feature_df),
                    4,
                )
            except Exception as exc:
                logger.warning("Prediction failed for %s/%s: %s", ticker, model_name, exc)

        predicted_price = per_model_predictions.get(best_model_name, current_price)

        logger.info("[%s] Stage 6: Experiment Tracking", ticker)
        for model_name, model_data in models.items():
            try:
                MLflowTracker.log_experiment(
                    ticker=ticker,
                    model_name=model_name,
                    params=model_data.get("params", {}),
                    metrics=evaluation["metrics"].get(model_name, {}),
                    model=model_data.get("model"),
                    is_best_model=(model_name == best_model_name),
                    pipeline_run_id=pipeline_run_id,
                    training_duration_sec=train_duration,
                    predictions=model_data.get("predictions"),
                    y_test=model_data.get("y_test"),
                    validation_report=validation_report,
                    feature_df=feature_df,
                    feature_columns=feature_columns,
                    interval=interval,
                    training_days=training_days,
                    predicted_next_price=per_model_predictions.get(model_name),
                    current_price=current_price,
                )
            except Exception as exc:
                logger.warning("MLflow tracking failed for %s/%s: %s", ticker, model_name, exc)

        return {
            "ticker": ticker,
            "clean_df": clean_df,
            "feature_df": feature_df,
            "models": models,
            "evaluation": evaluation,
            "validation_report": validation_report,
            "best_model_name": best_model_name,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "per_model_predictions": per_model_predictions,
        }

    @staticmethod
    def _predict_next(model_name: str, model_data: dict, df: pd.DataFrame) -> float:
        """Use a trained model to predict the next price point."""
        if model_name == "LinearRegression":
            model = model_data["model"]
            feature_cols = model_data["params"].get("features", [])
            available = [col for col in feature_cols if col in df.columns]
            last_features = df[available].iloc[-1:].values
            pred = model.predict(last_features)
            return float(pred[0])

        if model_name == "ARIMA":
            model = model_data["model"]
            pred = model.forecast(steps=1)
            return float(pred.iloc[0]) if hasattr(pred, "iloc") else float(pred[0])

        if model_name == "LSTM":
            model = model_data["model"]
            scaler = model_data.get("_scaler")
            close = df["Close"].values.flatten()
            seq_len = ModelTrainer.LSTM_SEQUENCE_LENGTH

            scaled = scaler.transform(close.reshape(-1, 1))
            last_seq = scaled[-seq_len:].reshape(1, seq_len, 1)
            pred_scaled = model.predict(last_seq, verbose=0)
            pred = scaler.inverse_transform(pred_scaled)
            return float(pred[0][0])

        return float(df["Close"].iloc[-1])

    @staticmethod
    def _predict_horizon(
        model_name: str,
        model_data: dict,
        feature_df: pd.DataFrame,
        base_df: pd.DataFrame,
        steps: int,
        interval: str,
    ) -> float:
        """Predict a future price several steps ahead."""
        if steps <= 1:
            return MLPipelineRunner._predict_next(model_name, model_data, feature_df)

        if model_name == "ARIMA":
            pred = model_data["model"].forecast(steps=steps)
            return float(pred.iloc[-1]) if hasattr(pred, "iloc") else float(pred[-1])

        market_cols = [col for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if col in base_df.columns]
        simulated_df = base_df[market_cols].copy()
        last_ts = base_df.index[-1]

        for _ in range(steps):
            engineered_df = FeatureEngineer.generate(simulated_df.copy())
            next_price = MLPipelineRunner._predict_next(model_name, model_data, engineered_df)
            last_ts = last_ts + MLPipelineRunner._get_interval_delta(interval)
            simulated_df = MLPipelineRunner._append_synthetic_row(
                simulated_df,
                next_timestamp=last_ts,
                predicted_close=next_price,
            )

        return float(next_price)

    @staticmethod
    def _append_synthetic_row(
        df: pd.DataFrame,
        next_timestamp,
        predicted_close: float,
    ) -> pd.DataFrame:
        """Append a synthetic market row so multi-step forecasting can continue."""
        updated = df.copy()
        last_row = updated.iloc[-1].copy()

        for col in ["Open", "High", "Low", "Close", "Adj Close"]:
            if col in updated.columns:
                last_row[col] = predicted_close
        if "Volume" in updated.columns:
            last_row["Volume"] = float(last_row["Volume"]) if pd.notna(last_row["Volume"]) else 0.0

        updated.loc[next_timestamp] = last_row
        return updated.sort_index()

    @staticmethod
    def _calculate_forecast_steps(last_timestamp: datetime, target_datetime: datetime, interval: str) -> int:
        """Calculate the number of model steps required to reach the target."""
        last_timestamp = MLPipelineRunner._normalize_datetime(last_timestamp)
        target_datetime = MLPipelineRunner._normalize_datetime(target_datetime)
        delta = MLPipelineRunner._get_interval_delta(interval)

        if target_datetime <= last_timestamp:
            return 1

        diff_seconds = (target_datetime - last_timestamp).total_seconds()
        return max(1, math.ceil(diff_seconds / delta.total_seconds()))

    @staticmethod
    def _align_target_datetime(target_datetime: datetime, interval: str) -> tuple[datetime, str]:
        """Align the requested datetime to the nearest model interval boundary."""
        target_datetime = MLPipelineRunner._normalize_datetime(target_datetime)
        delta = MLPipelineRunner._get_interval_delta(interval)
        seconds = int(delta.total_seconds())
        target_seconds = int(target_datetime.timestamp())

        if target_seconds % seconds == 0:
            return target_datetime, "Requested time already matches the selected interval."

        aligned_seconds = ((target_seconds // seconds) + 1) * seconds
        aligned = datetime.fromtimestamp(aligned_seconds, tz=dt_timezone.utc)
        return aligned, f"Requested time was aligned to the next {interval} market bucket."

    @staticmethod
    def _normalize_datetime(value: datetime) -> datetime:
        """Ensure all datetimes are timezone-aware UTC values."""
        if timezone.is_naive(value):
            return timezone.make_aware(value, dt_timezone.utc)
        return value.astimezone(dt_timezone.utc)

    @staticmethod
    def _get_interval_delta(interval: str) -> timedelta:
        """Map a model interval string to a timedelta."""
        return MLPipelineRunner.INTERVAL_TO_DELTA.get(interval, timedelta(hours=1))

    @staticmethod
    def _get_price_near_datetime(
        ticker: str,
        target_datetime: datetime,
        interval: str,
    ) -> tuple[float | None, datetime | None]:
        """Fetch the nearest available market price around a target datetime."""
        try:
            import yfinance as yf

            delta = MLPipelineRunner._get_interval_delta(interval)
            start = target_datetime - max(delta * 10, timedelta(days=2))
            end = target_datetime + max(delta * 3, timedelta(days=2))

            data = yf.download(
                ticker,
                start=start,
                end=end,
                interval=interval,
                progress=False,
            )
            if data is None or data.empty:
                fallback_interval = "1d" if interval != "1d" else interval
                data = yf.download(
                    ticker,
                    start=start - timedelta(days=7),
                    end=end + timedelta(days=7),
                    interval=fallback_interval,
                    progress=False,
                )
                if data is None or data.empty:
                    return None, None

            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            close_series = data["Close"].dropna()
            if close_series.empty:
                return None, None

            index = pd.to_datetime(close_series.index)
            if index.tz is None:
                index = index.tz_localize(dt_timezone.utc)
            else:
                index = index.tz_convert(dt_timezone.utc)

            candidates = list(zip(index, close_series.values))
            before = [item for item in candidates if item[0] <= target_datetime]
            if before:
                chosen_ts, chosen_price = before[-1]
            else:
                chosen_ts, chosen_price = candidates[0]

            return float(chosen_price), chosen_ts.to_pydatetime()
        except Exception as exc:
            logger.warning("Could not fetch price near %s for %s: %s", target_datetime, ticker, exc)
            return None, None

    @staticmethod
    def _summarize_forecast_results(predictions: list[dict]) -> dict:
        """Build a lightweight summary for newly generated forecasts."""
        if not predictions:
            return {}

        current_total = sum(item["current_price"] for item in predictions)
        predicted_total = sum(item["predicted_price"] for item in predictions)
        return {
            "stock_count": len(predictions),
            "aggregate_current_price": round(current_total, 4),
            "aggregate_predicted_price": round(predicted_total, 4),
            "aggregate_predicted_change_pct": round(
                ((predicted_total - current_total) / current_total * 100) if current_total else 0,
                4,
            ),
            "bullish_count": len([item for item in predictions if item["predicted_price"] >= item["current_price"]]),
            "bearish_count": len([item for item in predictions if item["predicted_price"] < item["current_price"]]),
        }

    @staticmethod
    def _build_forecast_analysis(predictions: list[ForecastPrediction]) -> dict:
        """Build actual-vs-predicted analysis after forecasts are resolved."""
        if not predictions:
            return {}

        verified = [prediction for prediction in predictions if prediction.status == "verified"]
        if not verified:
            return {
                "total_predictions": len(predictions),
                "verified_predictions": 0,
                "pending_predictions": len([p for p in predictions if p.status == "pending"]),
                "expired_predictions": len([p for p in predictions if p.status == "expired"]),
            }

        predicted_total = sum(pred.predicted_price for pred in verified)
        actual_total = sum(pred.actual_price or 0 for pred in verified)
        current_total = sum(pred.current_price_at_request for pred in verified)
        pct_errors = [pred.pct_error for pred in verified if pred.pct_error is not None]
        direction_matches = [pred.direction_match for pred in verified if pred.direction_match is not None]

        return {
            "total_predictions": len(predictions),
            "verified_predictions": len(verified),
            "avg_pct_error": round(sum(pct_errors) / len(pct_errors), 4) if pct_errors else 0,
            "max_pct_error": round(max(pct_errors), 4) if pct_errors else 0,
            "direction_accuracy_pct": round(
                (sum(1 for item in direction_matches if item) / len(direction_matches) * 100)
                if direction_matches else 0,
                4,
            ),
            "aggregate_current_price": round(current_total, 4),
            "aggregate_predicted_price": round(predicted_total, 4),
            "aggregate_actual_price": round(actual_total, 4),
            "aggregate_prediction_gap": round(predicted_total - actual_total, 4),
            "aggregate_prediction_gap_pct": round(
                ((predicted_total - actual_total) / actual_total * 100) if actual_total else 0,
                4,
            ),
        }
