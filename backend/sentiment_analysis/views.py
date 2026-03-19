import os

from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SentimentAnalysisJob
from .serializers import SentimentJobSerializer, SentimentResultSerializer, SentimentRunInputSerializer
from .services.search_service import StockSearchService
from .tasks import run_sentiment_analysis


class SentimentStockSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "")
        try:
            return Response(StockSearchService.search(query))
        except Exception as exc:
            return Response({"error": "Stock search failed", "details": str(exc)}, status=500)


class SentimentRunAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SentimentRunInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = SentimentAnalysisJob.objects.create(
            user=request.user,
            ticker=serializer.validated_data["ticker"],
            company_name=serializer.validated_data.get("company_name", ""),
            window_days=serializer.validated_data.get("window_days", 90),
            force_refresh=serializer.validated_data.get("force_refresh", False),
        )

        try:
            run_sentiment_analysis.delay(job.pk)
        except Exception:
            run_sentiment_analysis(job.pk)

        return Response({"job_id": job.pk, "status": job.status, "stage": job.stage, "progress": job.progress}, status=202)


class SentimentJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = SentimentAnalysisJob.objects.select_related("result").get(pk=job_id, user=request.user)
        except SentimentAnalysisJob.DoesNotExist:
            return Response({"error": "Job not found"}, status=404)
        return Response(SentimentJobSerializer(job, context={"request": request}).data)


class SentimentResultDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = SentimentAnalysisJob.objects.select_related("result", "report").prefetch_related("artifacts").get(pk=job_id, user=request.user)
        except SentimentAnalysisJob.DoesNotExist:
            return Response({"error": "Result not found"}, status=404)
        if not hasattr(job, "result"):
            return Response({"job": job.pk, "status": job.status, "stage": job.stage, "progress": job.progress, "message": "Analysis is still running."}, status=202)
        return Response(SentimentResultSerializer(job.result, context={"request": request}).data)


class SentimentReportDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = SentimentAnalysisJob.objects.select_related("report").get(pk=job_id, user=request.user)
        except SentimentAnalysisJob.DoesNotExist as exc:
            raise Http404("Report not found") from exc

        if not hasattr(job, "report") or not os.path.exists(job.report.file_path):
            raise Http404("Report file missing")

        return FileResponse(open(job.report.file_path, "rb"), content_type="application/pdf")
