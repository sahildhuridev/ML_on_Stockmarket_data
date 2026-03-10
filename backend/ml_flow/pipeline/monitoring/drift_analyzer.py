import numpy as np
from collections import defaultdict
from typing import List, Dict, Any

class DriftAnalyzer:
    """
    Analyzes historical prediction data to detect drift, stability, and ensemble accuracy.
    """

    RECENT_WINDOW_SIZE = 10
    DRIFT_THRESHOLD_MULTIPLIER = 1.5  # If recent error is 1.5x baseline error

    @staticmethod
    def analyze_drift(verified_predictions: List[Any]) -> Dict[str, Any]:
        """
        Calculates model drift per model.
        
        Args:
            verified_predictions: List of HourlyPrediction objects that have been verified.
            
        Returns:
            Dict mapping model_name to its drift metrics.
        """
        model_groups = defaultdict(list)
        for p in verified_predictions:
            model_groups[p.model_name].append(p)
            
        results = {}
        for model_name, preds in model_groups.items():
            # Sort chronologically (oldest first)
            preds.sort(key=lambda x: x.predicted_at)
            
            if len(preds) < DriftAnalyzer.RECENT_WINDOW_SIZE + 1:
                # Not enough data for drift detection
                avg_error = np.mean([p.pct_error for p in preds]) if preds else 0.0
                results[model_name] = {
                    "model_name": model_name,
                    "drift_detected": False,
                    "baseline_error": avg_error,
                    "recent_error": avg_error,
                    "status": "Safe (Not Enough Data)"
                }
                continue
                
            recent = preds[-DriftAnalyzer.RECENT_WINDOW_SIZE:]
            baseline = preds[:-DriftAnalyzer.RECENT_WINDOW_SIZE]
            
            recent_error = np.mean([p.pct_error for p in recent])
            baseline_error = np.mean([p.pct_error for p in baseline]) if baseline else recent_error
            
            # Prevent division by zero or extremely small baselines causing false positive drift
            baseline_error = max(baseline_error, 0.5) 
            
            drift_detected = recent_error > (baseline_error * DriftAnalyzer.DRIFT_THRESHOLD_MULTIPLIER)
            
            results[model_name] = {
                "model_name": model_name,
                "drift_detected": drift_detected,
                "baseline_error": round(baseline_error, 4),
                "recent_error": round(recent_error, 4),
                "status": "Drift Detected!" if drift_detected else "Safe"
            }
            
        return results

    @staticmethod
    def compute_trend_stats(verified_predictions: List[Any]) -> Dict[str, Any]:
        """
        Computes advanced trends: Directional Accuracy, Stability, and Ensemble Accuracy.
        """
        if not verified_predictions:
            return {
                "directional_accuracy_pct": 0.0,
                "stability_variance": 0.0,
                "ensemble_accuracy_pct": 0.0,
                "total_verified": 0
            }

        # 1. Directional Accuracy
        correct_direction = 0
        absolute_errors = []
        
        # 2. Ensemble calculation: group by predicted_at (time slot) + ticker
        # We need to approximate grouping by run. We can group by pipeline_run_id as a proxy for the same hour.
        ensemble_groups = defaultdict(list)
        
        for p in verified_predictions:
            # Directional hit?
            actual_diff = p.actual_price - p.current_price_at_prediction
            pred_diff = p.predicted_price - p.current_price_at_prediction
            
            # If both moved in the same direction (or both stayed flat)
            if (actual_diff > 0 and pred_diff > 0) or \
               (actual_diff < 0 and pred_diff < 0) or \
               (actual_diff == 0 and pred_diff == 0):
                correct_direction += 1
                
            absolute_errors.append(p.absolute_error)
            
            ensemble_groups[p.pipeline_run_id].append({
                "predicted": p.predicted_price,
                "actual": p.actual_price
            })
            
        directional_accuracy = (correct_direction / len(verified_predictions)) * 100
        
        # Variance of absolute error
        stability_variance = np.var(absolute_errors) if len(absolute_errors) > 1 else 0.0
        
        # Ensemble Accuracy (average the predictions for a given run, compare to actual)
        ensemble_pct_errors = []
        for run_id, preds in ensemble_groups.items():
            if not preds: continue
            avg_pred = np.mean([x['predicted'] for x in preds])
            # Assume actual price is same across the specific run/ticker combo (using the first one)
            actual = preds[0]['actual'] 
            if actual > 0:
                err = abs(avg_pred - actual) / actual * 100
                ensemble_pct_errors.append(err)
                
        ensemble_accuracy = np.mean(ensemble_pct_errors) if ensemble_pct_errors else 0.0

        return {
            "directional_accuracy_pct": round(directional_accuracy, 2),
            "stability_variance": round(stability_variance, 4),
            "ensemble_error_pct": round(ensemble_accuracy, 2),
            "total_verified": len(verified_predictions)
        }
