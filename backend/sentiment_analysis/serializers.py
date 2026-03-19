from rest_framework import serializers

from .models import SentimentAnalysisJob, SentimentAnalysisResult, SentimentArtifact, SentimentReport


class SentimentRunInputSerializer(serializers.Serializer):
    ticker = serializers.CharField(max_length=20)
    company_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    window_days = serializers.IntegerField(required=False, default=90, min_value=30, max_value=120)
    force_refresh = serializers.BooleanField(required=False, default=False)

    def validate_ticker(self, value):
        ticker = (value or "").strip().upper()
        if not ticker:
            raise serializers.ValidationError("Ticker is required.")
        return ticker


class SentimentArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentArtifact
        fields = [
            "id",
            "layer",
            "artifact_type",
            "file_path",
            "file_format",
            "row_count",
            "metadata_json",
            "created_at",
        ]


class SentimentReportSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = SentimentReport
        fields = ["id", "file_path", "created_at", "download_url"]

    def get_download_url(self, obj):
        request = self.context.get("request")
        if request is None:
            return None
        return request.build_absolute_uri(f"/api/sentiment/report/{obj.job_id}/pdf/")


class SentimentResultSerializer(serializers.ModelSerializer):
    ticker = serializers.CharField(source="job.ticker", read_only=True)
    company_name = serializers.CharField(source="job.company_name", read_only=True)
    status = serializers.CharField(source="job.status", read_only=True)
    stage = serializers.CharField(source="job.stage", read_only=True)
    progress = serializers.IntegerField(source="job.progress", read_only=True)
    requested_at = serializers.DateTimeField(source="job.requested_at", read_only=True)
    completed_at = serializers.DateTimeField(source="job.completed_at", read_only=True)
    artifacts = SentimentArtifactSerializer(source="job.artifacts", many=True, read_only=True)
    report = SentimentReportSerializer(source="job.report", read_only=True)

    class Meta:
        model = SentimentAnalysisResult
        fields = [
            "job",
            "ticker",
            "company_name",
            "status",
            "stage",
            "progress",
            "requested_at",
            "completed_at",
            "overall_label",
            "overall_confidence",
            "overall_score",
            "momentum",
            "risk_indicator",
            "summary_json",
            "distribution_json",
            "daily_trend_json",
            "weekly_trend_json",
            "correlation_json",
            "news_feed_json",
            "word_cloud_json",
            "embedding_json",
            "artifacts",
            "report",
        ]


class SentimentJobSerializer(serializers.ModelSerializer):
    result = SentimentResultSerializer(read_only=True)

    class Meta:
        model = SentimentAnalysisJob
        fields = [
            "id",
            "ticker",
            "company_name",
            "window_days",
            "force_refresh",
            "status",
            "stage",
            "progress",
            "error_message",
            "metadata_json",
            "requested_at",
            "started_at",
            "completed_at",
            "result",
        ]

