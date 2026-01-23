"""
Webhook Event Model
Spec: 026-api-webhook-ecosystem

Model for tracking webhook delivery attempts, status, and responses.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, DateTime, Integer, Text, Boolean, ForeignKey, Index, func, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator
from src.database import Base, GUID


class JSONBCompat(TypeDecorator):
    """Use JSONB on PostgreSQL and JSON elsewhere for test compatibility."""

    impl = JSONB
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class WebhookEvent(Base):
    """
    Запись о попытке доставки вебхука.
    Отслеживает статус, попытки и ответы для мониторинга и отладки.
    """
    __tablename__ = "webhook_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # Ссылка на webhooks.id (UUID)
    webhook_id = Column(GUID(), ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    # Тип события (например, "stream.started", "track.played")
    event_type = Column(String(255), nullable=False, index=True)
    # ID события в системе (если применимо)
    event_id = Column(String(255), nullable=True, index=True)

    # Детали доставки
    # Статус доставки: "pending", "success", "failed", "retrying"
    status = Column(String(50), nullable=False, default="pending", index=True)
    # Номер попытки (начинается с 1)
    attempt_number = Column(Integer, nullable=False, default=1)
    # Время попытки доставки
    attempted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # HTTP детали
    # Код статуса HTTP ответа (если получен)
    response_status_code = Column(Integer, nullable=True)
    # Тело ответа (если есть)
    response_body = Column(Text, nullable=True)
    # Заголовки ответа (если есть)
    response_headers = Column(JSONBCompat, nullable=True)

    # Данные для повтора
    # Нужно ли повторить попытку
    should_retry = Column(Boolean, nullable=False, server_default=text('false'), default=False)
    # Время следующей попытки (если запланирована)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    # Длительность запроса в миллисекундах
    duration_ms = Column(Integer, nullable=True)

    # Relationships
    webhook = relationship("Webhook", backref="events")

    # Indexes for performance
    __table_args__ = (
        Index('idx_webhook_events_webhook_id', 'webhook_id'),
        Index('idx_webhook_events_event_type', 'event_type'),
        Index('idx_webhook_events_status', 'status'),
        Index('idx_webhook_events_attempted_at', 'attempted_at'),
        Index('idx_webhook_events_event_id', 'event_id'),
    )

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, webhook_id='{self.webhook_id}', event_type='{self.event_type}', status='{self.status}')>"

    def mark_success(self, status_code: int, response_body: str = None, duration_ms: int = None) -> None:
        """Отметить событие как успешно доставленное."""
        self.status = "success"
        self.response_status_code = status_code
        self.response_body = response_body
        self.duration_ms = duration_ms
        self.should_retry = False
        self.next_retry_at = None

    def mark_failure(self, status_code: int = None, response_body: str = None,
                     should_retry: bool = False, next_retry_at: datetime = None,
                     duration_ms: int = None) -> None:
        """Отметить событие как неудачное."""
        self.status = "failed"
        self.response_status_code = status_code
        self.response_body = response_body
        self.should_retry = should_retry
        self.next_retry_at = next_retry_at
        self.duration_ms = duration_ms

    def mark_retrying(self, next_retry_at: datetime) -> None:
        """Отметить событие для повторной попытки."""
        self.status = "retrying"
        self.should_retry = True
        self.next_retry_at = next_retry_at
