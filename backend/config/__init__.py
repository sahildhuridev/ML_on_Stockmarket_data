# Import Celery app so that shared_task uses this app.
# Guarded to avoid breaking the project if celery is not installed.
try:
    from .celery import app as celery_app
    __all__ = ('celery_app',)
except ImportError:
    pass
