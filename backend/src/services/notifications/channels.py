"""
Валидация конфигурации каналов и тестовая отправка через Apprise/Celery.
"""
import logging
import uuid
from typing import Dict, Optional

from apprise import Apprise
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.core.config import settings
from src.models.notifications import NotificationChannel
from src.schemas.notifications import NotificationChannelCreate, NotificationChannelUpdate
from src.services.notifications.base import NotificationService
from src.services.notifications.worker import send_test_notification  # noqa: F401 (регистрация задачи в Celery)

logger = logging.getLogger(__name__)


class ChannelValidationError(ValueError):
    """Ошибка валидации конфигурации канала."""


class NotificationChannelService:
    """Высокоуровневый сервис для каналов уведомлений (CRUD + тесты)."""

    def __init__(self, db: Session):
        self.db = db
        self.base = NotificationService(db)

    # CRUD обёртки с валидацией конфигурации
    def create_channel(self, data: NotificationChannelCreate) -> NotificationChannel:
        self._validate_config(data.type, data.config)
        try:
            return self.base.create_channel(data)
        except IntegrityError as exc:
            self.db.rollback()
            raise ChannelValidationError("Channel name must be unique") from exc

    def update_channel(self, channel_id, data: NotificationChannelUpdate) -> Optional[NotificationChannel]:
        if data.type is not None or data.config is not None:
            existing = self.base.get_channel(channel_id)
            target_type = data.type or (existing.type if existing else None)
            target_config = data.config or (existing.config if existing else {})
            if target_type:
                self._validate_config(target_type, target_config)
        try:
            return self.base.update_channel(channel_id, data)
        except IntegrityError as exc:
            self.db.rollback()
            raise ChannelValidationError("Channel name must be unique") from exc

    # Тестовая отправка
    def test_channel(
        self,
        *,
        channel_id,
        recipient: str,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        context: Optional[Dict] = None,
        use_celery: bool = True,
    ) -> str:
        channel = self.base.get_channel(channel_id)
        if not channel:
            raise ChannelValidationError("Channel not found")
        if not channel.enabled:
            raise ChannelValidationError("Channel is disabled")

        event_id = f"test-{uuid.uuid4()}"
        payload = {
            "event_id": event_id,
            "channel_id": str(channel.id),
            "recipient": recipient,
            "subject": subject or "Test notification",
            "body": body or "Test notification",
            "context": context or {},
        }

        if celery_app and use_celery:
            celery_app.send_task(
                "notifications.send_test",
                args=[payload],
                queue=settings.NOTIFICATIONS_QUEUE,
            )
            return event_id

        # Фоллбек: синхронно через Apprise
        app = Apprise()
        from src.services.notifications.worker import build_apprise_urls, render_subject, render_body

        urls = build_apprise_urls(channel.config, channel.type, recipient)
        if not urls:
            raise ChannelValidationError("No Apprise URL for channel")
        for url in urls:
            app.add(url)
        body_rendered = render_body(payload["body"], payload["context"])
        subject_rendered = render_subject(payload["subject"], payload["context"])
        success = app.notify(body=body_rendered, title=subject_rendered, notify_type=None)
        status = "success" if success else "fail"
        try:
            self.base.log_delivery(
                event_id=event_id,
                status=status,
                channel_id=channel.id,
                recipient_id=None,
                error_message=None if success else "send_test failed",
            )
        except Exception:
            logger.exception("Failed to log test delivery")
        return event_id

    # --- helpers ---
    @staticmethod
    def _validate_config(channel_type: str, config: Dict) -> None:
        if channel_type == "email":
            required = ["host", "user", "password"]
            missing = [f for f in required if not config.get(f)]
            if missing:
                raise ChannelValidationError(f"Email config missing fields: {', '.join(missing)}")
        if channel_type == "telegram":
            if not config.get("bot_token"):
                raise ChannelValidationError("Telegram config requires bot_token")
        if channel_type in {"webhook", "http", "https"}:
            if not config.get("url"):
                raise ChannelValidationError("Webhook config requires url")
        # Slack/SMS minimal checks optional here
