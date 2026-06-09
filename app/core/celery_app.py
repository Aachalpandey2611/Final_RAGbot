from celery import Celery
from app.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "final_chatbot_worker",
    broker="redis://127.0.0.1:6379/1",
    backend="redis://127.0.0.1:6379/1",
    include=["app.tasks"]
)

# Optional configuration adjustments for Celery performance
celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1, # Processes one task at a time per worker to improve performance under long tasks
)
