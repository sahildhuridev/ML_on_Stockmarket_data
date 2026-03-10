"""
ML Pipeline Runner
------------------
Orchestrates the full ML pipeline: ingestion → validation → features →
training → evaluation → MLflow tracking → prediction.

Now includes:
  • Verification of pending HourlyPredictions at the start of each run
  • Per-model next-price predictions saved as HourlyPrediction (status=pending)
"""

import logging
import time
import numpy as np
from django.utils import timezone

from portfolios.models import Portfolio
from ml_flow.models import PipelineRun, Prediction, HourlyPrediction
from ml_flow.pipeline.ingestion.data_ingestion import DataIngestion
from ml_flow.pipeline.validation.data_validation import DataValidator
from ml_flow.pipeline.features.feature_engineering import FeatureEngineer
from ml_flow.pipeline.training.train_models import ModelTrainer
from ml_flow.pipeline.evaluation.evaluate_models import ModelEvaluator
from ml_flow.pipeline.tracking.mlflow_tracker import MLflowTracker

logger = logging.getLogger(__name__)


class MLPipelineRunner:
    """
    End-to-end ML pipeline for a portfolio's stocks.

    Usage:
        result = MLPipelineRunner.run_pipeline(portfolio_id=3)
    """

    @staticmethod
    def run_pipeline(
        portfolio_id: int,
        interval: str = "1h",
        training_days: int = 30,
        user=None,
    ) -> dict:
        """
        Execute the full ML workflow for every stock in a portfolio.
        """
        # ── Fetch portfolio ──────────────────────────────────────────
        try:
            portfolio = Portfolio.objects.get(id=portfolio_id)
        except Portfolio.DoesNotExist:
            raise ValueError(f"Portfolio with id={portfolio_id} does not exist")

        stocks = portfolio.stocks.all()
        if not stocks.exists():
            raise ValueError(f"Portfolio '{portfolio.name}' has no stocks")

        # ── STEP 0: Verify pending predictions from previous runs ────
        verification_summary = MLPipelineRunner._verify_pending_predictions(portfolio)

        # ── Create PipelineRun record ────────────────────────────────
        pipeline_run = PipelineRun.objects.create(
            portfolio=portfolio,
            triggered_by=user,
            status='running',
            interval=interval,
            training_days=training_days,
        )

        period = f"{training_days}d"
        stock_results = []

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

                # Save best-model prediction to DB
                Prediction.objects.create(
                    pipeline_run=pipeline_run,
                    ticker=ticker,
                    current_price=result['current_price'],
                    predicted_price=result['predicted_price'],
                    best_model=result['best_model'],
                    metrics=result['metrics'],
                )

                # Save PER-MODEL hourly predictions as PENDING
                for model_name, pred_price in result.get('per_model_predictions', {}).items():
                    HourlyPrediction.objects.create(
                        pipeline_run=pipeline_run,
                        ticker=ticker,
                        model_name=model_name,
                        predicted_price=pred_price,
                        current_price_at_prediction=result['current_price'],
                        status='pending',
                    )

            except Exception as e:
                logger.error(f"Pipeline failed for {ticker}: {e}")
                stock_results.append({
                    "ticker": ticker,
                    "error": str(e),
                })

        # ── Finalise run ─────────────────────────────────────────────
        pipeline_run.status = 'completed'
        pipeline_run.finished_at = timezone.now()
        pipeline_run.results_json = stock_results
        pipeline_run.save()

        # ── Build model ranking from all verified predictions ────────
        model_ranking = MLPipelineRunner._build_model_ranking(portfolio)

        return {
            "portfolio": portfolio.name,
            "pipeline_run_id": pipeline_run.pk,
            "results": stock_results,
            "verification_summary": verification_summary,
            "model_ranking": model_ranking,
        }

    # ────────────────────────────────────────────────────────────────
    # Verify pending predictions
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _verify_pending_predictions(portfolio) -> dict:
        """
        Fetch current prices for stocks that have pending HourlyPredictions
        and compute prediction errors.
        """
        pending = HourlyPrediction.objects.filter(
            pipeline_run__portfolio=portfolio,
            status='pending',
        )

        if not pending.exists():
            return {"verified_count": 0, "message": "No pending predictions to verify"}

        # Group by ticker
        tickers = set(pending.values_list('ticker', flat=True))
        verified_count = 0
        errors = []

        for ticker in tickers:
            try:
                # Fetch current price from yfinance
                actual_price = MLPipelineRunner._get_current_price(ticker)
                if actual_price is None:
                    continue

                ticker_pending = pending.filter(ticker=ticker)
                now = timezone.now()

                for hp in ticker_pending:
                    abs_err = abs(actual_price - hp.predicted_price)
                    pct_err = (abs_err / actual_price * 100) if actual_price != 0 else 0

                    hp.actual_price = actual_price
                    hp.absolute_error = round(abs_err, 4)
                    hp.pct_error = round(pct_err, 4)
                    hp.status = 'verified'
                    hp.verified_at = now
                    hp.save()
                    verified_count += 1

            except Exception as e:
                logger.warning(f"Could not verify predictions for {ticker}: {e}")
                errors.append(f"{ticker}: {e}")

        return {
            "verified_count": verified_count,
            "tickers_verified": list(tickers),
            "errors": errors if errors else None,
        }

    @staticmethod
    def _get_current_price(ticker: str) -> float | None:
        """Fetch current price via yfinance (last close or latest intraday)."""
        try:
            import yfinance as yf
            data = yf.download(ticker, period="1d", interval="1m", progress=False)
            if data is not None and not data.empty:
                close = data['Close']
                if hasattr(close, 'iloc'):
                    return float(close.iloc[-1].item() if hasattr(close.iloc[-1], 'item') else close.iloc[-1])
            # Fallback: daily
            data = yf.download(ticker, period="5d", interval="1d", progress=False)
            if data is not None and not data.empty:
                close = data['Close']
                return float(close.iloc[-1].item() if hasattr(close.iloc[-1], 'item') else close.iloc[-1])
            return None
        except Exception as e:
            logger.warning(f"Could not fetch price for {ticker}: {e}")
            return None

    # ────────────────────────────────────────────────────────────────
    # Build model ranking from all verified predictions
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_model_ranking(portfolio) -> list[dict]:
        """
        Rank models by average pct_error across all verified predictions
        for this portfolio.
        """
        verified = HourlyPrediction.objects.filter(
            pipeline_run__portfolio=portfolio,
            status='verified',
        )

        if not verified.exists():
            return []

        from collections import defaultdict
        model_stats = defaultdict(lambda: {"errors": [], "count": 0})

        for hp in verified:
            stats = model_stats[hp.model_name]
            stats["errors"].append(hp.pct_error)
            stats["count"] += 1

        ranking = []
        for model_name, stats in model_stats.items():
            errors = stats["errors"]
            avg_pct_error = sum(errors) / len(errors)
            avg_abs_error_list = [
                hp.absolute_error for hp in verified.filter(model_name=model_name)
                if hp.absolute_error is not None
            ]
            avg_abs_error = sum(avg_abs_error_list) / len(avg_abs_error_list) if avg_abs_error_list else 0

            ranking.append({
                "model_name": model_name,
                "avg_pct_error": round(avg_pct_error, 4),
                "avg_abs_error": round(avg_abs_error, 4),
                "min_pct_error": round(min(errors), 4),
                "max_pct_error": round(max(errors), 4),
                "total_predictions": stats["count"],
            })

        # Sort by avg_pct_error (lower is better)
        ranking.sort(key=lambda x: x["avg_pct_error"])

        # Add rank number
        for i, r in enumerate(ranking):
            r["rank"] = i + 1

        return ranking

    # ── Single-stock processor ────────────────────────────────────────

    @staticmethod
    def _process_single_stock(
        ticker: str,
        period: str,
        interval: str,
        training_days: int = 30,
        pipeline_run_id: int | None = None,
    ) -> dict:
        """Run the full pipeline for a single ticker."""

        # 1: Data Ingestion
        logger.info(f"[{ticker}] Stage 1: Data Ingestion")
        raw_df = DataIngestion.fetch(ticker, period=period, interval=interval)

        # 2: Data Validation
        logger.info(f"[{ticker}] Stage 2: Data Validation")
        clean_df, validation_report = DataValidator.validate(raw_df)

        # 3: Feature Engineering
        logger.info(f"[{ticker}] Stage 3: Feature Engineering")
        feature_df = FeatureEngineer.generate(clean_df)

        # 4: Model Training (with timing)
        logger.info(f"[{ticker}] Stage 4: Model Training")
        feature_columns = FeatureEngineer.FEATURE_COLUMNS
        train_start = time.time()
        models = ModelTrainer.train(feature_df, feature_columns)
        train_duration = time.time() - train_start

        # 5: Model Evaluation
        logger.info(f"[{ticker}] Stage 5: Model Evaluation")
        evaluation = ModelEvaluator.evaluate(models)

        # 7: Generate predictions from ALL models (for hourly tracking)
        logger.info(f"[{ticker}] Stage 7: Prediction (all models)")
        best_model_name = evaluation['best_model']
        current_price = float(feature_df['Close'].iloc[-1])

        per_model_predictions = {}
        for model_name, model_data in models.items():
            try:
                pred = MLPipelineRunner._predict_next(model_name, model_data, feature_df)
                per_model_predictions[model_name] = round(pred, 4)
            except Exception as e:
                logger.warning(f"Prediction failed for {model_name}: {e}")

        predicted_price = per_model_predictions.get(best_model_name, current_price)

        # 6: MLflow Experiment Tracking — COMPREHENSIVE
        logger.info(f"[{ticker}] Stage 6: Experiment Tracking (comprehensive)")
        for model_name, model_data in models.items():
            model_metrics = evaluation['metrics'].get(model_name, {})
            is_best = (model_name == best_model_name)

            MLflowTracker.log_experiment(
                ticker=ticker,
                model_name=model_name,
                params=model_data.get('params', {}),
                metrics=model_metrics,
                model=model_data.get('model'),
                is_best_model=is_best,
                pipeline_run_id=pipeline_run_id,
                training_duration_sec=train_duration,
                predictions=model_data.get('predictions'),
                y_test=model_data.get('y_test'),
                validation_report=validation_report,
                feature_df=feature_df,
                feature_columns=feature_columns,
                interval=interval,
                training_days=training_days,
                predicted_next_price=per_model_predictions.get(model_name),
                current_price=current_price,
            )

        return {
            "ticker": ticker,
            "current_price": round(current_price, 4),
            "predicted_price": round(predicted_price, 4),
            "best_model": best_model_name,
            "metrics": evaluation['metrics'].get(best_model_name, {}),
            "all_model_metrics": evaluation['metrics'],
            "validation_report": validation_report,
            "per_model_predictions": per_model_predictions,
        }

    @staticmethod
    def _predict_next(model_name: str, model_data: dict, df) -> float:
        """Use a model to predict the next price point."""
        if model_name == 'LinearRegression':
            model = model_data['model']
            feature_cols = model_data['params'].get('features', [])
            available = [c for c in feature_cols if c in df.columns]
            last_features = df[available].iloc[-1:].values
            pred = model.predict(last_features)
            return float(pred[0])

        elif model_name == 'ARIMA':
            model = model_data['model']
            pred = model.forecast(steps=1)
            return float(pred.iloc[0]) if hasattr(pred, 'iloc') else float(pred[0])

        elif model_name == 'LSTM':
            model = model_data['model']
            scaler = model_data.get('_scaler')
            close = df['Close'].values.flatten()
            seq_len = ModelTrainer.LSTM_SEQUENCE_LENGTH

            scaled = scaler.transform(close.reshape(-1, 1))
            last_seq = scaled[-seq_len:].reshape(1, seq_len, 1)
            pred_scaled = model.predict(last_seq, verbose=0)
            pred = scaler.inverse_transform(pred_scaled)
            return float(pred[0][0])

        else:
            return float(df['Close'].iloc[-1])
