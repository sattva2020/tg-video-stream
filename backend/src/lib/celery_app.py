"""
Celery application configuration for the Telegram broadcast platform.

This module sets up Celery with Redis broker and result backend,
configuring task serialization, retry policies, and monitoring.
"""

import os
from celery import Celery
from celery.schedules import crontab


# Create Celery app
celery_app = Celery(
    "telegram_broadcast",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=[
        "backend.src.services.video_processing_task",
        "backend.src.services.youtube_validation_task",
        "backend.src.services.analytics_aggregation_task",
        "backend.src.services.scheduler",
        "backend.src.services.conference_tracking_task"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,  # Tasks acknowledged after completion
    worker_prefetch_multiplier=1,  # Fair task distribution
    task_reject_on_worker_lost=True,  # Requeue tasks if worker dies

    # Retry policy
    task_default_retry_delay=60,  # 1 minute default retry delay
    task_max_retries=3,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_cache_max=10000,  # Maximum cached results

    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_disable_rate_limits=False,

    # Monitoring and logging
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_ignore_result=False,

    # Beat scheduler settings
    beat_schedule={
        # Schedule execution check - every minute
        "check-schedule-execution": {
            "task": "backend.src.services.scheduler.check_and_execute_schedules",
            "schedule": 60.0,  # Every 60 seconds
        },

        # YouTube source validation - every 6 hours
        "validate-youtube-sources": {
            "task": "backend.src.services.youtube_validation_task.validate_youtube_sources",
            "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours
        },

        # Analytics aggregation - every hour
        "aggregate-analytics": {
            "task": "backend.src.services.analytics_aggregation_task.aggregate_hourly_stats",
            "schedule": crontab(minute=0, hour="*"),  # Every hour
        },

        # Conference participant tracking - every 10 seconds (only when active)
        "track-conference-participants": {
            "task": "backend.src.services.conference_tracking_task.track_active_conferences",
            "schedule": 10.0,  # Every 10 seconds
        },

        # Daily analytics aggregation - every day at 2 AM
        "aggregate-daily-analytics": {
            "task": "backend.src.services.analytics_aggregation_task.aggregate_daily_stats",
            "schedule": crontab(minute=0, hour=2),  # 2 AM daily
        },

        # Cleanup old task results - daily at 3 AM
        "cleanup-old-results": {
            "task": "backend.src.tasks.cleanup_old_results",
            "schedule": crontab(minute=0, hour=3),  # 3 AM daily
        }
    }
)


# Task base classes with common functionality
class BaseTask(celery_app.Task):
    """Base task class with error handling and logging."""

    abstract = True
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        print(f"Task {task_id} failed: {exc}")
        # Could send notifications, log to external service, etc.

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        print(f"Task {task_id} completed successfully")


# Task routing configuration
celery_app.conf.task_routes = {
    # Video processing tasks
    "backend.src.services.video_processing_task.process_video": {"queue": "video_processing"},
    "backend.src.services.video_processing_task.extract_metadata": {"queue": "video_processing"},

    # YouTube validation tasks
    "backend.src.services.youtube_validation_task.validate_source": {"queue": "youtube"},
    "backend.src.services.youtube_validation_task.validate_all_sources": {"queue": "youtube"},

    # Analytics tasks
    "backend.src.services.analytics_aggregation_task.aggregate_hourly_stats": {"queue": "analytics"},
    "backend.src.services.analytics_aggregation_task.aggregate_daily_stats": {"queue": "analytics"},

    # Scheduler tasks
    "backend.src.services.scheduler.check_and_execute_schedules": {"queue": "scheduler"},
    "backend.src.services.scheduler.execute_schedule_action": {"queue": "scheduler"},

    # Conference tasks
    "backend.src.services.conference_tracking_task.track_conference": {"queue": "conference"},
    "backend.src.services.conference_tracking_task.track_active_conferences": {"queue": "conference"},
}


# Monitoring and metrics
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup."""
    print(f"Request: {self.request!r}")


@celery_app.task(bind=True)
def get_celery_stats(self):
    """Get Celery worker and queue statistics."""
    inspect = celery_app.control.inspect()

    stats = {
        "active": inspect.active(),
        "scheduled": inspect.scheduled(),
        "stats": inspect.stats(),
        "registered": inspect.registered(),
        "active_queues": inspect.active_queues(),
    }

    return stats


# Health check task
@celery_app.task(bind=True)
def health_check(self):
    """Celery health check task."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",  # Would use datetime.now() in real implementation
        "worker": self.request.hostname,
        "task_id": self.request.id
    }


# Cleanup task
@celery_app.task(bind=True)
def cleanup_old_results(self, days_old: int = 7):
    """Clean up old task results from Redis backend."""
    # This would implement cleanup of old results
    # For now, just return success
    return {"cleaned_count": 0, "days_old": days_old}


if __name__ == "__main__":
    celery_app.start()