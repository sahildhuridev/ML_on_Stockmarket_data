from django.contrib.auth.models import User
from django.db import models


class SentimentAnalysisJob(models.Model):
    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    STAGE_CHOICES = [
        ("queued", "Queued"),
        ("fetching", "Fetching"),
        ("bronze", "Bronze"),
        ("silver", "Silver"),
        ("gold", "Gold"),
        ("embedding", "Embedding"),
        ("report", "Report"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sentiment_jobs")
    ticker = models.CharField(max_length=20)
    company_name = models.CharField(max_length=255, blank=True)
    window_days = models.PositiveIntegerField(default=90)
    force_refresh = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="queued")
    progress = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    metadata_json = models.JSONField(default=dict, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.ticker} sentiment job #{self.pk}"


class SentimentAnalysisResult(models.Model):
    job = models.OneToOneField(SentimentAnalysisJob, on_delete=models.CASCADE, related_name="result")
    overall_label = models.CharField(max_length=20, blank=True)
    overall_confidence = models.FloatField(default=0.0)
    overall_score = models.FloatField(default=0.0)
    momentum = models.CharField(max_length=50, blank=True)
    risk_indicator = models.CharField(max_length=50, blank=True)
    summary_json = models.JSONField(default=dict, blank=True)
    distribution_json = models.JSONField(default=list, blank=True)
    daily_trend_json = models.JSONField(default=list, blank=True)
    weekly_trend_json = models.JSONField(default=list, blank=True)
    correlation_json = models.JSONField(default=dict, blank=True)
    news_feed_json = models.JSONField(default=list, blank=True)
    word_cloud_json = models.JSONField(default=list, blank=True)
    embedding_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Sentiment result for {self.job.ticker}"


class SentimentArtifact(models.Model):
    job = models.ForeignKey(SentimentAnalysisJob, on_delete=models.CASCADE, related_name="artifacts")
    layer = models.CharField(max_length=20)
    artifact_type = models.CharField(max_length=50)
    file_path = models.CharField(max_length=500)
    file_format = models.CharField(max_length=20)
    row_count = models.PositiveIntegerField(default=0)
    metadata_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.layer}:{self.artifact_type} for {self.job.ticker}"


class SentimentReport(models.Model):
    job = models.OneToOneField(SentimentAnalysisJob, on_delete=models.CASCADE, related_name="report")
    file_path = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report for {self.job.ticker}"

