from django.contrib import admin

from .models import SentimentAnalysisJob, SentimentAnalysisResult, SentimentArtifact, SentimentReport


@admin.register(SentimentAnalysisJob)
class SentimentAnalysisJobAdmin(admin.ModelAdmin):
    list_display = ("id", "ticker", "status", "stage", "progress", "requested_at", "completed_at")
    list_filter = ("status", "stage")
    search_fields = ("ticker", "company_name")


@admin.register(SentimentAnalysisResult)
class SentimentAnalysisResultAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "overall_label", "overall_score", "risk_indicator")
    search_fields = ("job__ticker", "job__company_name")


@admin.register(SentimentArtifact)
class SentimentArtifactAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "layer", "artifact_type", "file_format", "row_count", "created_at")
    list_filter = ("layer", "artifact_type", "file_format")


@admin.register(SentimentReport)
class SentimentReportAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "created_at")

