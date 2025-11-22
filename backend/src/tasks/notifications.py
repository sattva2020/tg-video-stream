"""Notifications and background workers for admin alerts.

This module exposes `notify_admins_async(user_id)` which will either
- enqueue a background job using Celery (if CELERY_BROKER_URL is configured), or
- fall back to a synchronous call (dev-mode)

The actual sending functions (email/telegram) are intentionally minimal — full templates and provider integrations are implemented in later tasks.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Try to lazily import Celery when available
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except Exception:
    Celery = None
    CELERY_AVAILABLE = False


def _build_celery_app():
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        return None
    app = Celery('tg_video_streamer', broker=broker)
    return app


# Define the actual worker function (registered only if Celery available)
if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _build_celery_app()

    @celery_app.task(name='tasks.send_admin_notification')
    def send_admin_notification_task(user_id: str):
        # In a real worker this would import DB session and send emails/telegram
        logger.info(f"[worker] send_admin_notification_task called for user {user_id}")
        # Placeholder: actual send logic executed here
        return True


def notify_admins_async(user_id: str):
    """Attempt to schedule a notification job.

    If Celery is configured, call the Celery task `.delay(user_id)`.
    Otherwise call the task function synchronously (dev-mode).
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _build_celery_app()
        try:
            app.send_task('tasks.send_admin_notification', args=[str(user_id)])
            logger.info(f"Enqueued admin notification for user {user_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task")
            # fall through to sync
    # Dev fallback (synchronous)
    logger.info(f"Dev-mode: sending admin notification synchronously for {user_id}")
    # Here we would call send_admin_notification_sync — for now, return True
    return True
