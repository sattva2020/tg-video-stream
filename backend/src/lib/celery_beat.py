"""
Celery Beat scheduler configuration for the Telegram broadcast platform.

This module configures the Celery Beat scheduler for periodic tasks
like schedule execution checks, YouTube validation, and analytics aggregation.
"""

import os
from celery import Celery
from celery.schedules import crontab

from .celery_app import celery_app


class CeleryBeatConfig:
    """Configuration for Celery Beat scheduler."""

    def __init__(self):
        """Initialize Celery Beat configuration."""
        self.app = celery_app

        # Configure beat schedule
        self.app.conf.beat_schedule = {

            # Schedule execution - check every minute for schedules to execute
            "check-schedule-execution": {
                "task": "backend.src.services.scheduler.check_and_execute_schedules",
                "schedule": 60.0,  # Every 60 seconds
                "args": (),
                "kwargs": {},
                "options": {"queue": "scheduler"}
            },

            # YouTube source validation - check every 6 hours
            "validate-youtube-sources": {
                "task": "backend.src.services.youtube_validation_task.validate_all_sources",
                "schedule": crontab(minute=0, hour="*/6"),  # Every 6 hours at :00
                "args": (),
                "kwargs": {},
                "options": {"queue": "youtube"}
            },

            # Hourly analytics aggregation - run every hour
            "aggregate-hourly-analytics": {
                "task": "backend.src.services.analytics_aggregation_task.aggregate_hourly_stats",
                "schedule": crontab(minute=0, hour="*"),  # Every hour at :00
                "args": (),
                "kwargs": {},
                "options": {"queue": "analytics"}
            },

            # Daily analytics aggregation - run daily at 2 AM
            "aggregate-daily-analytics": {
                "task": "backend.src.services.analytics_aggregation_task.aggregate_daily_stats",
                "schedule": crontab(minute=0, hour=2),  # 2 AM daily
                "args": (),
                "kwargs": {},
                "options": {"queue": "analytics"}
            },

            # Conference participant tracking - run every 10 seconds when conferences are active
            "track-conference-participants": {
                "task": "backend.src.services.conference_tracking_task.track_active_conferences",
                "schedule": 10.0,  # Every 10 seconds
                "args": (),
                "kwargs": {},
                "options": {"queue": "conference"}
            },

            # System health monitoring - run every 5 minutes
            "system-health-check": {
                "task": "backend.src.tasks.system_health_check",
                "schedule": 300.0,  # Every 5 minutes
                "args": (),
                "kwargs": {},
                "options": {"queue": "monitoring"}
            },

            # Database maintenance - run daily at 3 AM
            "database-maintenance": {
                "task": "backend.src.tasks.database_maintenance",
                "schedule": crontab(minute=0, hour=3),  # 3 AM daily
                "args": (),
                "kwargs": {},
                "options": {"queue": "maintenance"}
            },

            # Backup verification - run daily at 4 AM
            "verify-backups": {
                "task": "backend.src.tasks.verify_backups",
                "schedule": crontab(minute=0, hour=4),  # 4 AM daily
                "args": (),
                "kwargs": {},
                "options": {"queue": "maintenance"}
            },

            # Clean up old files - run weekly on Sunday at 5 AM
            "cleanup-old-files": {
                "task": "backend.src.tasks.cleanup_old_files",
                "schedule": crontab(minute=0, hour=5, day_of_week=0),  # Sunday 5 AM
                "args": (30,),  # Delete files older than 30 days
                "kwargs": {},
                "options": {"queue": "maintenance"}
            },

            # Generate reports - run weekly on Monday at 6 AM
            "generate-weekly-reports": {
                "task": "backend.src.tasks.generate_weekly_reports",
                "schedule": crontab(minute=0, hour=6, day_of_week=1),  # Monday 6 AM
                "args": (),
                "kwargs": {},
                "options": {"queue": "reporting"}
            }
        }

        # Beat scheduler settings
        self.app.conf.beat_schedule_filename = os.getenv(
            "CELERY_BEAT_SCHEDULE_FILE",
            "/tmp/celerybeat-schedule"
        )
        self.app.conf.beat_sync_every = 1  # Sync schedule every task
        self.app.conf.beat_max_loop_interval = 5  # Max time between schedule checks

    def get_schedule_info(self) -> dict:
        """
        Get information about the current beat schedule.

        Returns:
            dict: Schedule configuration information
        """
        return {
            "schedule_count": len(self.app.conf.beat_schedule),
            "schedules": list(self.app.conf.beat_schedule.keys()),
            "schedule_file": self.app.conf.beat_schedule_filename,
            "sync_every": self.app.conf.beat_sync_every,
            "max_loop_interval": self.app.conf.beat_max_loop_interval
        }


# Global beat config instance
_beat_config: CeleryBeatConfig = None


def get_beat_config() -> CeleryBeatConfig:
    """Get the global Celery Beat configuration instance."""
    global _beat_config
    if _beat_config is None:
        _beat_config = CeleryBeatConfig()
    return _beat_config


# Beat control functions
def start_beat():
    """Start the Celery Beat scheduler."""
    from celery.bin.beat import beat

    beat(app=celery_app).run()


def stop_beat():
    """Stop the Celery Beat scheduler."""
    # This would typically be handled by the process manager
    # For now, just log that beat should be stopped
    print("Celery Beat scheduler should be stopped")


def restart_beat():
    """Restart the Celery Beat scheduler."""
    stop_beat()
    start_beat()


# Schedule management functions
def add_dynamic_schedule(name: str, task: str, schedule, args=None, kwargs=None, options=None):
    """
    Add a dynamic schedule to the beat configuration.

    Args:
        name: Schedule name
        task: Task name to execute
        schedule: Schedule configuration (crontab, timedelta, etc.)
        args: Task positional arguments
        kwargs: Task keyword arguments
        options: Task execution options
    """
    config = get_beat_config()

    config.app.conf.beat_schedule[name] = {
        "task": task,
        "schedule": schedule,
        "args": args or (),
        "kwargs": kwargs or {},
        "options": options or {}
    }


def remove_dynamic_schedule(name: str):
    """
    Remove a dynamic schedule from the beat configuration.

    Args:
        name: Schedule name to remove
    """
    config = get_beat_config()

    if name in config.app.conf.beat_schedule:
        del config.app.conf.beat_schedule[name]


def list_schedules() -> dict:
    """
    List all configured schedules.

    Returns:
        dict: Schedule information
    """
    config = get_beat_config()
    return config.get_schedule_info()


# Health check for beat scheduler
def beat_health_check() -> dict:
    """
    Check the health of the Celery Beat scheduler.

    Returns:
        dict: Health check result
    """
    try:
        config = get_beat_config()
        schedule_info = config.get_schedule_info()

        return {
            "status": "healthy",
            "schedule_count": schedule_info["schedule_count"],
            "schedules": schedule_info["schedules"],
            "schedule_file": schedule_info["schedule_file"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    # Start beat scheduler when run directly
    start_beat()