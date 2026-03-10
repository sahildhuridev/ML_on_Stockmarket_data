"""
Celery Tasks for ML Flow
-------------------------
Scheduled and on-demand tasks for running the ML pipeline.
"""

import logging
from celery import shared_task

from portfolios.models import Portfolio
from ml_flow.pipeline.pipeline_runner import MLPipelineRunner

logger = logging.getLogger(__name__)


@shared_task(name='ml_flow.run_pipeline_for_portfolio')
def run_pipeline_for_portfolio(portfolio_id: int, interval: str = '1h', training_days: int = 30):
    """
    Run the ML pipeline for a single portfolio (async via Celery).
    """
    try:
        result = MLPipelineRunner.run_pipeline(
            portfolio_id=portfolio_id,
            interval=interval,
            training_days=training_days,
        )
        logger.info(f"Pipeline completed for portfolio {portfolio_id}: {len(result.get('results', []))} stocks processed")
        return result
    except Exception as e:
        logger.error(f"Pipeline task failed for portfolio {portfolio_id}: {e}")
        raise


@shared_task(name='ml_flow.run_ml_pipeline_for_all_portfolios')
def run_ml_pipeline_for_all_portfolios():
    """
    Run the ML pipeline for ALL portfolios in the system.
    Designed to be called on a schedule (e.g. daily via Celery Beat).
    """
    portfolios = Portfolio.objects.all()
    total = portfolios.count()
    logger.info(f"Starting scheduled pipeline run for {total} portfolios")

    results = []
    for portfolio in portfolios:
        try:
            result = MLPipelineRunner.run_pipeline(
                portfolio_id=portfolio.id,
                interval='1h',
                training_days=30,
            )
            results.append({
                "portfolio_id": portfolio.id,
                "portfolio_name": portfolio.name,
                "status": "success",
                "stocks_processed": len(result.get('results', [])),
            })
        except Exception as e:
            logger.error(f"Scheduled pipeline failed for portfolio {portfolio.id}: {e}")
            results.append({
                "portfolio_id": portfolio.id,
                "portfolio_name": portfolio.name,
                "status": "failed",
                "error": str(e),
            })

    logger.info(f"Scheduled pipeline run complete: {len(results)}/{total} portfolios processed")
    return results
