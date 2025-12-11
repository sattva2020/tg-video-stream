"""Приём событий уведомлений и постановка плана в очередь."""
import logging
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.celery_app import celery_app
from src.core.config import settings
from src.database import get_db
from src.services.notifications.routing import EventPayload, NotificationRoutingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications/events", tags=["Notifications"])


class NotificationEventRequest(BaseModel):
    event_id: Optional[str] = Field(None, description="Внешний идентификатор события")
    severity: Optional[str] = Field(None, description="Уровень/категория (info/warn/crit)")
    tags: Optional[Dict] = Field(None, description="Произвольные теги события")
    host: Optional[str] = Field(None, description="Хост/источник события")
    context: Optional[Dict] = Field(None, description="Контекст для шаблонов")
    subject: Optional[str] = Field(None, description="Заголовок/тема")
    body: Optional[str] = Field(None, description="Текст события")


class NotificationEventResponse(BaseModel):
    status: str = "queued"
    event_id: str
    tasks_enqueued: int


def _enqueue_process_event(payload: Dict, *, delay_sec: int = 0) -> bool:
    """Кладёт задачу в очередь или логирует, если Celery недоступен."""
    if celery_app:
        try:
            celery_app.send_task(
                "notifications.process_event",
                args=[payload],
                queue=settings.NOTIFICATIONS_QUEUE,
                countdown=delay_sec,
            )
            return True
        except Exception:  # noqa: BLE001
            logger.exception("Failed to enqueue notification task")
            return False
    logger.warning("Celery app not configured; skipping enqueue", extra={"payload": payload})
    return False


@router.post("", response_model=NotificationEventResponse, status_code=status.HTTP_202_ACCEPTED)
def accept_event(request: NotificationEventRequest, db: Session = Depends(get_db)):
    event_id = request.event_id or str(uuid4())
    routing = NotificationRoutingService(db)
    plan = routing.build_delivery_plan(
        EventPayload(
            event_id=event_id,
            severity=request.severity,
            tags=request.tags,
            host=request.host,
            context=request.context,
            subject=request.subject,
            body=request.body,
        )
    )

    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching rules or recipients")

    enqueued = 0
    for item in plan:
        channel_ids: List[UUID] = item.get("channel_ids", [])
        delay = 0
        for channel_id in channel_ids:
            payload = {
                "event_id": event_id,
                "rule_id": str(item["rule_id"]),
                "channel_id": str(channel_id),
                "recipient_id": str(item["recipient_id"]),
                "context": item.get("context") or {},
                "subject": item.get("subject"),
                "body": item.get("body"),
            }
            if _enqueue_process_event(payload, delay_sec=delay):
                enqueued += 1
            delay += int(item.get("failover_timeout_sec") or 0)

    return NotificationEventResponse(event_id=event_id, tasks_enqueued=enqueued)
