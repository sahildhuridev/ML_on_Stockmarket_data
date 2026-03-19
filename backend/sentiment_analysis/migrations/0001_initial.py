from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SentimentAnalysisJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ticker", models.CharField(max_length=20)),
                ("company_name", models.CharField(blank=True, max_length=255)),
                ("window_days", models.PositiveIntegerField(default=90)),
                ("force_refresh", models.BooleanField(default=False)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed")], default="queued", max_length=20)),
                ("stage", models.CharField(choices=[("queued", "Queued"), ("fetching", "Fetching"), ("bronze", "Bronze"), ("silver", "Silver"), ("gold", "Gold"), ("embedding", "Embedding"), ("report", "Report"), ("completed", "Completed"), ("failed", "Failed")], default="queued", max_length=20)),
                ("progress", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("metadata_json", models.JSONField(blank=True, default=dict)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sentiment_jobs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-requested_at"]},
        ),
        migrations.CreateModel(
            name="SentimentAnalysisResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("overall_label", models.CharField(blank=True, max_length=20)),
                ("overall_confidence", models.FloatField(default=0.0)),
                ("overall_score", models.FloatField(default=0.0)),
                ("momentum", models.CharField(blank=True, max_length=50)),
                ("risk_indicator", models.CharField(blank=True, max_length=50)),
                ("summary_json", models.JSONField(blank=True, default=dict)),
                ("distribution_json", models.JSONField(blank=True, default=list)),
                ("daily_trend_json", models.JSONField(blank=True, default=list)),
                ("weekly_trend_json", models.JSONField(blank=True, default=list)),
                ("correlation_json", models.JSONField(blank=True, default=dict)),
                ("news_feed_json", models.JSONField(blank=True, default=list)),
                ("word_cloud_json", models.JSONField(blank=True, default=list)),
                ("embedding_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("job", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="result", to="sentiment_analysis.sentimentanalysisjob")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="SentimentArtifact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("layer", models.CharField(max_length=20)),
                ("artifact_type", models.CharField(max_length=50)),
                ("file_path", models.CharField(max_length=500)),
                ("file_format", models.CharField(max_length=20)),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("metadata_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="artifacts", to="sentiment_analysis.sentimentanalysisjob")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="SentimentReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file_path", models.CharField(max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="report", to="sentiment_analysis.sentimentanalysisjob")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
