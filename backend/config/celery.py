"""
Celery Configuration for ML Stock Analysis
-------------------------------------------
This module sets up the Celery application and auto-discovers tasks
from all installed Django apps.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Load config from Django settings, using the CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# ── Beat Schedule ─────────────────────────────────────────────────────
app.conf.beat_schedule = {
    'run-ml-pipeline-daily': {
        'task': 'ml_flow.run_ml_pipeline_for_all_portfolios',
        'schedule': crontab(hour=6, minute=0),  # Every day at 6:00 AM UTC
        'args': (),
    },
}
app.conf.timezone = 'UTC'
