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
        # Worker entrypoint — load the user and perform notifications
        logger.info(f"[worker] send_admin_notification_task called for user {user_id}")
        from database import SessionLocal
        from src.models.user import User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"User {user_id} not found for admin notification")
                return False
            return send_admin_notification_for_user(user)
        finally:
            db.close()


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
    # Dev fallback (synchronous) — attempt to perform send now
    logger.info(f"Dev-mode: sending admin notification synchronously for {user_id}")
    try:
        return send_admin_notification_sync(user_id)
    except Exception:
        logger.exception("Failed to send admin notification synchronously")
        return False


def send_admin_notification_for_user(user) -> bool:
    """Send notifications (email + telegram) for given user object.

    This helper is small and testable — accepts either ORM user object or any object
    with `email` and `id` attributes.
    """
    emails = os.getenv('ADMIN_NOTIFICATION_EMAILS')
    if emails:
        recipients = [e.strip() for e in emails.split(',') if e.strip()]
    else:
        recipients = []

    # Send email via FastMail if SMTP configured
    smtp_host = os.getenv('SMTP_HOST')
    if smtp_host and recipients:
        try:
            from fastapi_mail import FastMail, MessageSchema
            fm = FastMail(
                config={
                    "MAIL_USERNAME": os.getenv("SMTP_USER"),
                    "MAIL_PASSWORD": os.getenv("SMTP_PASS"),
                    "MAIL_FROM": os.getenv("SMTP_FROM", "no-reply@example.com"),
                    "MAIL_PORT": int(os.getenv("SMTP_PORT", 587)),
                    "MAIL_SERVER": smtp_host,
                    "MAIL_TLS": True,
                    "MAIL_SSL": False
                }
            )
            subject = f"New registered user: {user.email}"
            body = f"A new user has registered and is awaiting approval: {user.email} (id: {user.id})."
            message = MessageSchema(subject=subject, recipients=recipients, body=body, subtype="plain")
            fm.send_message(message)
            logger.info(f"Sent admin email notifications to: {recipients}")
        except Exception:
            logger.exception("Failed to send admin emails")

    # Telegram notifications
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chats = os.getenv('TELEGRAM_ADMIN_CHAT_IDS')
    if telegram_token and telegram_chats:
        import requests
        chat_ids = [c.strip() for c in telegram_chats.split(',') if c.strip()]
        for cid in chat_ids:
            try:
                text = f"New user awaiting approval: {user.email} (id: {user.id})"
                url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
                requests.post(url, json={"chat_id": cid, "text": text})
            except Exception:
                logger.exception("Failed to send telegram notification")

    return True


def send_admin_notification_sync(user_id: str) -> bool:
    """Synchronous helper to read user from DB and call send_admin_notification_for_user.

    Used by tests and dev fallback.
    """
    from database import SessionLocal
    from src.models.user import User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning("send_admin_notification_sync: user not found %s", user_id)
            return False
        return send_admin_notification_for_user(user)
    finally:
        db.close()
