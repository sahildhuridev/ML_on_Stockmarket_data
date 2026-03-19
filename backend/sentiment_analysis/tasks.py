import logging

try:
    from celery import shared_task
except ImportError:  # pragma: no cover
    def shared_task(*_args, **_kwargs):
        def decorator(func):
            func.delay = func
            return func
        return decorator

from django.utils import timezone

from .models import SentimentAnalysisJob, SentimentAnalysisResult, SentimentReport
from .services.pipeline import EmbeddingStore, SentimentPipeline
from .services.reporting import SentimentReportBuilder
from .services.storage import get_job_root, register_artifact

logger = logging.getLogger(__name__)


def _update_job(job, *, status=None, stage=None, progress=None, error_message=None, metadata_json=None):
    if status is not None:
        job.status = status
    if stage is not None:
        job.stage = stage
    if progress is not None:
        job.progress = progress
    if error_message is not None:
        job.error_message = error_message
    if metadata_json is not None:
        job.metadata_json = {**(job.metadata_json or {}), **metadata_json}
    job.save()


@shared_task(name="sentiment_analysis.run_sentiment_analysis")
def run_sentiment_analysis(job_id: int):
    job = SentimentAnalysisJob.objects.get(pk=job_id)
    pipeline = SentimentPipeline(job)

    try:
        job.started_at = timezone.now()
        _update_job(job, status="running", stage="fetching", progress=10)

        news_rows, price_rows, bronze_meta = pipeline.fetch_sources()
        _update_job(job, stage="bronze", progress=25, metadata_json=bronze_meta)
        pipeline.write_bronze(news_rows, price_rows)

        silver_rows = pipeline.build_silver(news_rows)
        _update_job(job, stage="silver", progress=50, metadata_json={"silver_rows": len(silver_rows)})

        gold_payload = pipeline.build_gold(silver_rows, price_rows)
        gold_rows = gold_payload["gold_rows"]
        summary = gold_payload["summary"]
        _update_job(job, stage="gold", progress=75, metadata_json={"gold_rows": len(gold_rows)})

        embeddings_dir = get_job_root(job) / "embeddings"
        embeddings_dir.mkdir(parents=True, exist_ok=True)
        embedding_path = embeddings_dir / "news_embeddings.faiss"
        embedding_meta = EmbeddingStore.build(gold_rows, str(embedding_path))
        register_artifact(
            job,
            "gold",
            "embeddings",
            str(embedding_path),
            "faiss" if embedding_meta["backend"] == "faiss" else "json",
            len(gold_rows),
            embedding_meta,
        )
        _update_job(job, stage="embedding", progress=88)

        result, _ = SentimentAnalysisResult.objects.update_or_create(
            job=job,
            defaults={
                "overall_label": summary["summary"]["overall_sentiment"],
                "overall_confidence": summary["summary"]["confidence"],
                "overall_score": summary["summary"]["score"],
                "momentum": summary["summary"]["momentum"],
                "risk_indicator": summary["summary"]["risk_indicator"],
                "summary_json": summary["summary"],
                "distribution_json": summary["distribution"],
                "daily_trend_json": summary["daily_trend"],
                "weekly_trend_json": summary["weekly_trend"],
                "correlation_json": summary["correlation"],
                "news_feed_json": summary["news_feed"],
                "word_cloud_json": summary["word_cloud"],
                "embedding_json": {"backend": embedding_meta["backend"], "vector_count": embedding_meta["vectors"]},
            },
        )

        _update_job(job, stage="report", progress=95)
        report_path = SentimentReportBuilder.build(job, result)
        SentimentReport.objects.update_or_create(job=job, defaults={"file_path": report_path})

        job.completed_at = timezone.now()
        _update_job(job, status="completed", stage="completed", progress=100)
        return {"job_id": job.pk, "status": "completed"}
    except Exception as exc:
        logger.exception("Sentiment analysis failed for job %s", job_id)
        job.completed_at = timezone.now()
        _update_job(job, status="failed", stage="failed", progress=100, error_message=str(exc))
        raise
