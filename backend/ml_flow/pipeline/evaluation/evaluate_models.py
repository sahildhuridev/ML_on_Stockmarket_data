"""
Model Evaluation Module
-----------------------
Computes regression metrics (MSE, MAE, RMSE) for each trained model
and selects the best one by lowest RMSE.
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Evaluate trained models and pick the best."""

    @staticmethod
    def evaluate(models_dict: dict) -> dict:
        """
        Compute metrics for every model and identify the best.

        Args:
            models_dict: Output from ModelTrainer.train()
                         {model_name: {"predictions": ..., "y_test": ...}}

        Returns:
            {
                "metrics": {
                    "ModelName": {"mse": ..., "mae": ..., "rmse": ...},
                    ...
                },
                "best_model": "ModelName",
                "best_rmse": float,
            }
        """
        all_metrics = {}
        best_model = None
        best_rmse = float('inf')

        for name, result in models_dict.items():
            preds = np.array(result['predictions']).flatten()
            actual = np.array(result['y_test']).flatten()

            # Align lengths (ARIMA can sometimes differ by 1)
            min_len = min(len(preds), len(actual))
            preds = preds[:min_len]
            actual = actual[:min_len]

            if min_len == 0:
                logger.warning(f"Skipping {name}: no overlapping predictions")
                continue

            mse = float(np.mean((preds - actual) ** 2))
            mae = float(np.mean(np.abs(preds - actual)))
            rmse = float(np.sqrt(mse))

            all_metrics[name] = {
                "mse": round(mse, 6),
                "mae": round(mae, 6),
                "rmse": round(rmse, 6),
            }

            if rmse < best_rmse:
                best_rmse = rmse
                best_model = name

        logger.info(f"Evaluation complete — best model: {best_model} (RMSE={best_rmse:.4f})")

        return {
            "metrics": all_metrics,
            "best_model": best_model,
            "best_rmse": round(best_rmse, 6),
        }
