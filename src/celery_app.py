from celery import Celery
from celery.schedules import crontab

from src.config.settings import settings


celery_app = Celery(
    "online_cinema",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

celery_app.autodiscover_tasks(
    ["src.accounts"],
)

celery_app.conf.beat_schedule = {
    "cleanup-expired-activation-tokens": {
        "task": (
            "src.accounts.tasks."
            "cleanup_expired_activation_tokens"
        ),
        "schedule": crontab(minute=0),
    },
}
