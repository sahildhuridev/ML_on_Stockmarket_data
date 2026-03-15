from django.urls import path
from . import views

urlpatterns = [
    path('run-pipeline/', views.RunPipelineView.as_view(), name='ml_flow_run_pipeline'),
    path('forecasts/', views.ForecastRequestListCreateView.as_view(), name='ml_flow_forecasts'),
    path('forecasts/<int:pk>/', views.ForecastRequestDetailView.as_view(), name='ml_flow_forecast_detail'),
    path('pipeline-runs/', views.PipelineRunListView.as_view(), name='ml_flow_pipeline_runs'),
    path('pipeline-runs/<int:pk>/', views.PipelineRunDetailView.as_view(), name='ml_flow_pipeline_run_detail'),
    path('predictions/<int:portfolio_id>/', views.LatestPredictionsView.as_view(), name='ml_flow_latest_predictions'),
    path('experiments/', views.ExperimentListView.as_view(), name='ml_flow_experiments'),
    path('experiments/<str:experiment_name>/runs/', views.ExperimentRunsView.as_view(), name='ml_flow_experiment_runs'),
    path('experiments/run/<str:run_id>/', views.ExperimentRunDetailView.as_view(), name='ml_flow_experiment_run_detail'),
    path('model-ranking/<int:portfolio_id>/', views.ModelRankingView.as_view(), name='ml_flow_model_ranking'),
    path('monitoring/<int:portfolio_id>/', views.MonitoringDashboardView.as_view(), name='ml_flow_monitoring_dashboard'),
]
