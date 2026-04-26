import logging
from celery import Celery
from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "agent_orchestrator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.execute_workflow": {"queue": "workflow_tasks"},
        "app.workers.tasks.process_telegram_message": {"queue": "agent_tasks"},
    },
    beat_schedule={
        "check-scheduled-agents": {
            "task": "app.workers.tasks.check_scheduled_agents",
            "schedule": 60.0,
        },
    },
    include=["app.workers.tasks"],
)

# Register task objects on the worker (include alone is not always enough in all Celery versions)
import app.workers.tasks  # noqa: E402,F401
