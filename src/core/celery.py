import os
from collections.abc import Callable
from functools import wraps

from celery import Celery
from django.conf import settings
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.core.settings')

celery_app = Celery('src')

celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()
celery_app.conf.beat_schedule = settings.CELERY_BEAT_CONFIG
celery_app.conf.timezone = settings.CELERY_BEAT_TIMEZONE

def transactioned_task(name: str) -> Callable:
    def wrapped_decorator(func: Callable) -> Callable:
        @celery_app.task(
            name=name,
            retry_kwargs={"max_retries": settings.CELERY_MAX_RETRIES},
            rate_limit=settings.CELERY_RATE_LIMIT,
            serializer="pickle",
        )
        @wraps(func)
        def wrapper(*args, **kwargs):
            with transaction.atomic():
                result = func(*args, **kwargs)

            return result

        return wrapper
    return wrapped_decorator
