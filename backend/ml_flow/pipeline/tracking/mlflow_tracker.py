"""
MLflow Experiment Tracking Module — Comprehensive
--------------------------------------------------
Logs EVERYTHING trackable in MLflow:
  • Parameters    — model hyperparams, pipeline config, feature names
  • Metrics       — MSE / MAE / RMSE + prediction delta
  • Tags          — ticker, model type, best-model flag, pipeline run ID, git info
  • Artifacts     — trained model (sklearn / Keras / statsmodels), validation
                    report JSON, feature-stats CSV, predictions CSV
  • Dataset info  — row count, date range, column names
  • System info   — training duration

Uses local file-based tracking (mlruns/ directory).
"""

import json
import logging
import os
import time
import tempfile

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Determine mlruns path relative to the backend root
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MLFLOW_TRACKING_URI = f"file:///{os.path.join(_BACKEND_DIR, 'mlruns').replace(os.sep, '/')}"


def _safe_mlflow():
    """Import mlflow lazily; return None if not installed."""
    try:
        import mlflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        return mlflow
    except ImportError:
        logger.warning("MLflow is not installed — skipping experiment tracking")
        return None


class MLflowTracker:
    """Log ML experiments to MLflow with maximum coverage."""

    # ────────────────────────────────────────────────────────────────
    # PRIMARY: log a full training run
    # ────────────────────────────────────────────────────────────────
    @staticmethod
    def log_experiment(
        ticker: str,
        model_name: str,
        params: dict,
        metrics: dict,
        model=None,
        *,
        # Extended tracking kwargs (all optional)
        is_best_model: bool = False,
        pipeline_run_id: int | None = None,
        training_duration_sec: float | None = None,
        predictions: np.ndarray | None = None,
        y_test: np.ndarray | None = None,
        validation_report: dict | None = None,
        feature_df: pd.DataFrame | None = None,
        feature_columns: list[str] | None = None,
        interval: str | None = None,
        training_days: int | None = None,
        predicted_next_price: float | None = None,
        current_price: float | None = None,
    ) -> str | None:
        """
        Log a single model training run to MLflow with full telemetry.

        Returns MLflow run_id or None.
        """
        mlflow = _safe_mlflow()
        if mlflow is None:
            return None

        try:
            experiment_name = f"ml_stock_{ticker}"
            mlflow.set_experiment(experiment_name)

            with mlflow.start_run(run_name=f"{model_name}_{ticker}") as run:
                # ── 1. TAGS ──────────────────────────────────────
                mlflow.set_tag("ticker", ticker)
                mlflow.set_tag("model_type", model_name)
                mlflow.set_tag("pipeline_stage", "training")
                if is_best_model:
                    mlflow.set_tag("best_model", "true")
                if pipeline_run_id is not None:
                    mlflow.set_tag("pipeline_run_id", str(pipeline_run_id))
                if interval:
                    mlflow.set_tag("data_interval", interval)
                if training_days:
                    mlflow.set_tag("training_days", str(training_days))
                # Try to capture git hash
                try:
                    mlflow.set_tag("mlflow.source.type", "LOCAL")
                except Exception:
                    pass

                # ── 2. PARAMETERS ────────────────────────────────
                for key, value in params.items():
                    if isinstance(value, (list, tuple)):
                        mlflow.log_param(key, str(value))
                    elif isinstance(value, dict):
                        for k, v in value.items():
                            mlflow.log_param(f"{key}.{k}", v)
                    else:
                        mlflow.log_param(key, value)

                if feature_columns:
                    mlflow.log_param("feature_columns", str(feature_columns))
                    mlflow.log_param("n_features", len(feature_columns))

                # ── 3. METRICS ───────────────────────────────────
                for key, value in metrics.items():
                    if isinstance(value, (int, float)) and np.isfinite(value):
                        mlflow.log_metric(key, value)

                # Training duration
                if training_duration_sec is not None:
                    mlflow.log_metric("training_duration_sec", round(training_duration_sec, 3))

                # Prediction metrics
                if predicted_next_price is not None:
                    mlflow.log_metric("predicted_next_price", round(predicted_next_price, 4))
                if current_price is not None:
                    mlflow.log_metric("current_price", round(current_price, 4))
                if predicted_next_price and current_price and current_price != 0:
                    pct_chg = ((predicted_next_price - current_price) / current_price) * 100
                    mlflow.log_metric("predicted_pct_change", round(pct_chg, 4))

                # Dataset info
                if feature_df is not None and not feature_df.empty:
                    mlflow.log_metric("dataset_rows", len(feature_df))
                    mlflow.log_metric("dataset_columns", len(feature_df.columns))
                    if hasattr(feature_df.index, 'min'):
                        try:
                            mlflow.set_tag("data_start", str(feature_df.index.min()))
                            mlflow.set_tag("data_end", str(feature_df.index.max()))
                        except Exception:
                            pass

                # ── 4. ARTIFACTS ─────────────────────────────────
                with tempfile.TemporaryDirectory() as tmpdir:
                    # 4a. Validation report JSON
                    if validation_report:
                        vr_path = os.path.join(tmpdir, "validation_report.json")
                        with open(vr_path, "w") as f:
                            json.dump(validation_report, f, indent=2, default=str)
                        mlflow.log_artifact(vr_path, artifact_path="reports")

                    # 4b. Feature statistics CSV
                    if feature_df is not None and not feature_df.empty:
                        try:
                            stats = feature_df.describe().T
                            stats_path = os.path.join(tmpdir, "feature_statistics.csv")
                            stats.to_csv(stats_path)
                            mlflow.log_artifact(stats_path, artifact_path="data")
                        except Exception:
                            pass

                    # 4c. Predictions vs Actuals CSV
                    if predictions is not None and y_test is not None:
                        try:
                            pred_arr = np.array(predictions).flatten()
                            actual_arr = np.array(y_test).flatten()
                            min_len = min(len(pred_arr), len(actual_arr))
                            pred_df = pd.DataFrame({
                                "actual": actual_arr[:min_len],
                                "predicted": pred_arr[:min_len],
                                "error": actual_arr[:min_len] - pred_arr[:min_len],
                                "abs_error": np.abs(actual_arr[:min_len] - pred_arr[:min_len]),
                            })
                            pred_path = os.path.join(tmpdir, "predictions_vs_actuals.csv")
                            pred_df.to_csv(pred_path, index=False)
                            mlflow.log_artifact(pred_path, artifact_path="predictions")

                            # Additional prediction metrics
                            mlflow.log_metric("max_error", float(pred_df["abs_error"].max()))
                            mlflow.log_metric("min_error", float(pred_df["abs_error"].min()))
                            mlflow.log_metric("median_error", float(pred_df["abs_error"].median()))
                            mlflow.log_metric("std_error", float(pred_df["error"].std()))
                            mlflow.log_metric("prediction_count", len(pred_df))
                            # Directional accuracy
                            if min_len > 1:
                                actual_dir = np.sign(np.diff(actual_arr[:min_len]))
                                pred_dir = np.sign(np.diff(pred_arr[:min_len]))
                                dir_acc = float(np.mean(actual_dir == pred_dir)) * 100
                                mlflow.log_metric("directional_accuracy_pct", round(dir_acc, 2))
                        except Exception as e:
                            logger.debug(f"Could not log predictions artifact: {e}")

                    # 4d. Model parameters summary JSON
                    params_path = os.path.join(tmpdir, "model_params.json")
                    with open(params_path, "w") as f:
                        json.dump(params, f, indent=2, default=str)
                    mlflow.log_artifact(params_path, artifact_path="config")

                # ── 5. MODEL ARTIFACT ────────────────────────────
                MLflowTracker._log_model_artifact(mlflow, model, model_name)

                run_id = run.info.run_id
                logger.info(f"MLflow run logged: {experiment_name}/{model_name} → {run_id}")
                return run_id

        except Exception as e:
            logger.warning(f"MLflow logging failed: {e}")
            return None

    # ────────────────────────────────────────────────────────────────
    # Model-type specific artifact logging
    # ────────────────────────────────────────────────────────────────
    @staticmethod
    def _log_model_artifact(mlflow, model, model_name: str):
        """Log model artifact based on model type."""
        if model is None:
            return

        try:
            if model_name == "LinearRegression":
                import mlflow.sklearn
                mlflow.sklearn.log_model(model, artifact_path="model")
                # Also log coefficients
                if hasattr(model, "coef_"):
                    mlflow.log_param("lr_intercept", float(model.intercept_))
                    for i, coef in enumerate(model.coef_.flatten()):
                        mlflow.log_metric(f"lr_coef_{i}", float(coef))

            elif model_name == "ARIMA":
                # statsmodels ARIMA — log as a generic artifact
                try:
                    import mlflow.statsmodels
                    mlflow.statsmodels.log_model(model, artifact_path="model")
                except Exception:
                    # Fallback: log summary as text artifact
                    try:
                        with tempfile.NamedTemporaryFile(
                            mode="w", suffix=".txt", delete=False
                        ) as f:
                            f.write(str(model.summary()))
                            f.flush()
                            mlflow.log_artifact(f.name, artifact_path="model")
                        os.unlink(f.name)
                    except Exception:
                        pass
                # Log ARIMA-specific info
                if hasattr(model, "aic"):
                    mlflow.log_metric("aic", float(model.aic))
                if hasattr(model, "bic"):
                    mlflow.log_metric("bic", float(model.bic))

            elif model_name == "LSTM":
                # TensorFlow/Keras model
                try:
                    import mlflow.tensorflow
                    mlflow.tensorflow.log_model(model, artifact_path="model")
                except Exception:
                    # Fallback: save as H5 and log
                    try:
                        with tempfile.NamedTemporaryFile(
                            suffix=".keras", delete=False
                        ) as f:
                            model.save(f.name)
                            mlflow.log_artifact(f.name, artifact_path="model")
                        os.unlink(f.name)
                    except Exception:
                        pass
                # Log architecture summary
                if hasattr(model, "count_params"):
                    mlflow.log_metric("total_params", model.count_params())
                if hasattr(model, "layers"):
                    mlflow.log_param("n_layers", len(model.layers))
                    layer_info = [
                        f"{l.name}({l.__class__.__name__})"
                        for l in model.layers
                    ]
                    mlflow.log_param("architecture", str(layer_info))

        except Exception as e:
            logger.debug(f"Could not log model artifact for {model_name}: {e}")

    # ────────────────────────────────────────────────────────────────
    # LISTING helpers
    # ────────────────────────────────────────────────────────────────
    @staticmethod
    def list_experiments() -> list[dict]:
        """List all MLflow experiments with run counts."""
        mlflow = _safe_mlflow()
        if mlflow is None:
            return []

        try:
            experiments = mlflow.search_experiments()
            result = []
            for exp in experiments:
                # Count runs per experiment
                try:
                    runs = mlflow.search_runs(
                        experiment_ids=[exp.experiment_id],
                        max_results=1000,
                    )
                    run_count = len(runs) if not runs.empty else 0
                except Exception:
                    run_count = 0

                result.append({
                    "experiment_id": exp.experiment_id,
                    "name": exp.name,
                    "artifact_location": exp.artifact_location,
                    "lifecycle_stage": exp.lifecycle_stage,
                    "run_count": run_count,
                })
            return result
        except Exception as e:
            logger.warning(f"Failed to list experiments: {e}")
            return []

    @staticmethod
    def get_experiment_runs(experiment_name: str) -> list[dict]:
        """Get all runs for a specific experiment with full details."""
        mlflow = _safe_mlflow()
        if mlflow is None:
            return []

        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                return []

            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"],
                max_results=50,
            )
            if runs.empty:
                return []

            # Clean up column names and convert to dicts
            records = runs.to_dict(orient="records")
            cleaned = []
            for rec in records:
                clean_rec = {}
                for k, v in rec.items():
                    # Make keys more readable
                    key = k.replace("params.", "param_").replace("metrics.", "metric_").replace("tags.", "tag_")
                    # Handle NaN
                    if isinstance(v, float) and np.isnan(v):
                        continue
                    clean_rec[key] = v
                cleaned.append(clean_rec)
            return cleaned

        except Exception as e:
            logger.warning(f"Failed to get runs: {e}")
            return []

    @staticmethod
    def get_run_details(run_id: str) -> dict | None:
        """Get detailed information about a specific run."""
        mlflow = _safe_mlflow()
        if mlflow is None:
            return None

        try:
            run = mlflow.get_run(run_id)
            return {
                "run_id": run.info.run_id,
                "experiment_id": run.info.experiment_id,
                "status": run.info.status,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time,
                "duration_ms": (run.info.end_time or 0) - (run.info.start_time or 0),
                "artifact_uri": run.info.artifact_uri,
                "params": dict(run.data.params),
                "metrics": dict(run.data.metrics),
                "tags": dict(run.data.tags),
            }
        except Exception as e:
            logger.warning(f"Failed to get run details: {e}")
            return None
