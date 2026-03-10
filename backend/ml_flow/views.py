"""
ML Flow API Views
-----------------
Thin view layer that delegates all ML logic to the pipeline runner.
"""

import logging
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import PipelineRun, Prediction, HourlyPrediction
from portfolios.models import Portfolio
from .serializers import (
    PipelineRunSerializer,
    PipelineRunListSerializer,
    PredictionSerializer,
    HourlyPredictionSerializer,
    RunPipelineInputSerializer,
)
from .pipeline.pipeline_runner import MLPipelineRunner
from .pipeline.tracking.mlflow_tracker import MLflowTracker
from .pipeline.monitoring.drift_analyzer import DriftAnalyzer

logger = logging.getLogger(__name__)


class RunPipelineView(APIView):
    """
    POST /api/ml_flow/run-pipeline/

    Execute the full ML pipeline for a portfolio.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RunPipelineInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        portfolio_id = serializer.validated_data['portfolio_id']
        interval = serializer.validated_data.get('interval', '1h')
        training_days = serializer.validated_data.get('training_days', 30)

        try:
            result = MLPipelineRunner.run_pipeline(
                portfolio_id=portfolio_id,
                interval=interval,
                training_days=training_days,
                user=request.user,
            )
            return Response(result, status=200)
        except ValueError as e:
            return Response({"error": str(e)}, status=400)
        except Exception as e:
            logger.exception("Pipeline execution failed")
            return Response(
                {"error": "Pipeline execution failed", "details": str(e)},
                status=500,
            )


class PipelineRunListView(ListAPIView):
    """
    GET /api/ml_flow/pipeline-runs/

    List all pipeline runs for the authenticated user's portfolios.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PipelineRunListSerializer

    def get_queryset(self):
        return PipelineRun.objects.filter(
            portfolio__user=self.request.user
        ).select_related('portfolio')


class PipelineRunDetailView(RetrieveAPIView):
    """
    GET /api/ml_flow/pipeline-runs/<pk>/

    Retrieve a specific pipeline run with its predictions.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PipelineRunSerializer

    def get_queryset(self):
        return PipelineRun.objects.filter(
            portfolio__user=self.request.user
        ).select_related('portfolio').prefetch_related('predictions')


class LatestPredictionsView(APIView):
    """
    GET /api/ml_flow/predictions/<portfolio_id>/

    Return the latest predictions for all stocks in a portfolio.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, portfolio_id):
        # Find the latest completed run for this portfolio
        latest_run = (
            PipelineRun.objects
            .filter(portfolio_id=portfolio_id, portfolio__user=request.user, status='completed')
            .order_by('-finished_at')
            .first()
        )

        if not latest_run:
            return Response(
                {"error": "No completed pipeline runs found for this portfolio"},
                status=404,
            )

        predictions = latest_run.predictions.all()
        serializer = PredictionSerializer(predictions, many=True)

        return Response({
            "portfolio_id": portfolio_id,
            "pipeline_run_id": latest_run.pk,
            "ran_at": latest_run.finished_at,
            "predictions": serializer.data,
        })


class ExperimentListView(APIView):
    """
    GET /api/ml_flow/experiments/

    List all MLflow experiments (from local mlruns directory).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        experiments = MLflowTracker.list_experiments()
        return Response({"experiments": experiments})


class ExperimentRunsView(APIView):
    """
    GET /api/ml_flow/experiments/<experiment_name>/runs/

    List all runs for a specific MLflow experiment with full details.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, experiment_name):
        runs = MLflowTracker.get_experiment_runs(experiment_name)
        return Response({"experiment": experiment_name, "runs": runs})


class ExperimentRunDetailView(APIView):
    """
    GET /api/ml_flow/experiments/run/<run_id>/

    Get detailed information about a specific MLflow run.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, run_id):
        details = MLflowTracker.get_run_details(run_id)
        if details is None:
            return Response({"error": "Run not found"}, status=404)
        return Response(details)


class ModelRankingView(APIView):
    """
    GET /api/ml_flow/model-ranking/<portfolio_id>/

    Returns:
      - pending predictions (awaiting verification)
      - verified predictions (with actual prices and errors)
      - model ranking (models sorted by avg % error)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, portfolio_id):
        try:
            portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
        except Exception:
            return Response({"error": "Portfolio not found"}, status=404)

        # Pending predictions
        pending = HourlyPrediction.objects.filter(
            pipeline_run__portfolio=portfolio,
            status='pending',
        )

        # Verified predictions (latest 50)
        verified = HourlyPrediction.objects.filter(
            pipeline_run__portfolio=portfolio,
            status='verified',
        )[:50]

        # Build ranking
        from ml_flow.pipeline.pipeline_runner import MLPipelineRunner
        ranking = MLPipelineRunner._build_model_ranking(portfolio)

        return Response({
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "pending_predictions": HourlyPredictionSerializer(pending, many=True).data,
            "verified_predictions": HourlyPredictionSerializer(verified, many=True).data,
            "model_ranking": ranking,
        })

class MonitoringDashboardView(APIView):
    """
    GET /api/ml_flow/monitoring/<portfolio_id>/
    
    Returns data for System Monitoring, Predictions History, and Prediction Trends.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, portfolio_id):
        try:
            portfolio = Portfolio.objects.get(id=portfolio_id, user=request.user)
        except Exception:
            return Response({"error": "Portfolio not found"}, status=404)

        # 1. Fetch all predictions for the portfolio (pending and verified)
        all_preds = HourlyPrediction.objects.filter(
            pipeline_run__portfolio=portfolio
        ).order_by('-predicted_at')
        
        # 2. Extract verified (sort ascending for charts)
        verified = sorted([p for p in all_preds if p.status == 'verified'], key=lambda x: x.predicted_at)
        
        # 3. Drift Analysis
        drift_results = DriftAnalyzer.analyze_drift(verified)
        
        # 4. Error Over Time (for System Monitoring Chart)
        error_over_time = [
            {
                "timestamp": p.predicted_at.isoformat(),
                "model_name": p.model_name,
                "pct_error": round(p.pct_error, 2),
                "ticker": p.ticker
            } for p in verified
        ]
        
        # 5. Trend Stats
        trend_stats = DriftAnalyzer.compute_trend_stats(verified)
        
        # 6. Actual vs Predicted (for Trend Chart)
        actual_vs_predicted = [
            {
                "timestamp": p.predicted_at.isoformat(),
                "ticker": p.ticker,
                "model_name": p.model_name,
                "predicted": round(p.predicted_price, 2),
                "actual": round(p.actual_price, 2)
            } for p in verified
        ]

        # Use the serializer for history to get standard format
        history_data = HourlyPredictionSerializer(all_preds[:500], many=True).data

        return Response({
            "portfolio_id": portfolio_id,
            "portfolio_name": portfolio.name,
            "system_monitoring": {
                "drift_status": list(drift_results.values()),
                "error_over_time": error_over_time,
            },
            "predictions_history": history_data,
            "prediction_trends": {
                "stats": trend_stats,
                "actual_vs_predicted": actual_vs_predicted
            }
        })
