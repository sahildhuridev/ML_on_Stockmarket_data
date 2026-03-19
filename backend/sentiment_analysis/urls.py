from django.urls import path

from .views import (
    SentimentJobDetailView,
    SentimentReportDownloadView,
    SentimentResultDetailView,
    SentimentRunAnalysisView,
    SentimentStockSearchView,
)

urlpatterns = [
    path("search-stocks/", SentimentStockSearchView.as_view(), name="sentiment-search-stocks"),
    path("run-analysis/", SentimentRunAnalysisView.as_view(), name="sentiment-run-analysis"),
    path("jobs/<int:job_id>/", SentimentJobDetailView.as_view(), name="sentiment-job-detail"),
    path("results/<int:job_id>/", SentimentResultDetailView.as_view(), name="sentiment-result-detail"),
    path("report/<int:job_id>/pdf/", SentimentReportDownloadView.as_view(), name="sentiment-report-download"),
]
