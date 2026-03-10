from django.db import models
from django.contrib.auth.models import User
from portfolios.models import Portfolio


class PipelineRun(models.Model):
    """Tracks each ML pipeline execution."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    portfolio = models.ForeignKey(
        Portfolio,
        on_delete=models.CASCADE,
        related_name='pipeline_runs',
    )
    triggered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pipeline_runs',
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    interval = models.CharField(max_length=10, default='1h')
    training_days = models.IntegerField(default=30)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    results_json = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"PipelineRun #{self.pk} — {self.portfolio.name} ({self.status})"


class Prediction(models.Model):
    """Stores per-stock prediction results from a pipeline run."""

    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.CASCADE,
        related_name='predictions',
    )
    ticker = models.CharField(max_length=20)
    current_price = models.FloatField()
    predicted_price = models.FloatField()
    best_model = models.CharField(max_length=100)
    metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticker}: {self.current_price} → {self.predicted_price} ({self.best_model})"


class HourlyPrediction(models.Model):
    """
    Stores per-model next-hour price predictions.

    Flow:
      1. Pipeline runs → saves one HourlyPrediction per (stock × model) with status='pending'.
      2. On next pipeline run → system fetches actual price, fills actual_price, computes error,
         updates status to 'verified'.
      3. Frontend shows ranking of which model was most accurate.
    """

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('expired', 'Expired'),
    ]

    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.CASCADE,
        related_name='hourly_predictions',
    )
    ticker = models.CharField(max_length=20)
    model_name = models.CharField(max_length=100)
    predicted_price = models.FloatField()
    current_price_at_prediction = models.FloatField(
        help_text="Price of the stock when the prediction was made",
    )
    actual_price = models.FloatField(
        null=True, blank=True,
        help_text="Actual price fetched on the next run",
    )
    absolute_error = models.FloatField(null=True, blank=True)
    pct_error = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    predicted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-predicted_at']

    def __str__(self):
        status_str = f"✓ err={self.pct_error:.2f}%" if self.status == 'verified' else "⏳ pending"
        return f"{self.ticker}/{self.model_name}: ${self.predicted_price:.2f} ({status_str})"
