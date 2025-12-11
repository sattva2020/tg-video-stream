"""API для правил маршрутизации уведомлений: CRUD и тестовые прогоны."""
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.notifications import notification_rule_channels
from src.schemas.notifications import (
    NotificationRuleCreate,
    NotificationRuleResponse,
    NotificationRuleUpdate,
)
from src.services.notifications.base import NotificationService
from src.services.notifications.routing import EventPayload, NotificationRoutingService
from src.api.routes.notifications_events import _enqueue_process_event
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/notifications/rules", tags=["Notifications"])


def _serialize_rule(rule, db: Session) -> NotificationRuleResponse:
    channel_rows = db.execute(
        select(notification_rule_channels.c.channel_id)
        .where(notification_rule_channels.c.rule_id == rule.id)
        .order_by(notification_rule_channels.c.priority.asc())
    ).scalars().all()

    return NotificationRuleResponse.model_validate(
        {
            "id": rule.id,
            "name": rule.name,
            "enabled": rule.enabled,
            "severity_filter": rule.severity_filter,
            "tag_filter": rule.tag_filter,
            "host_filter": rule.host_filter,
            "failover_timeout_sec": rule.failover_timeout_sec,
            "silence_windows": rule.silence_windows,
            "rate_limit": rule.rate_limit,
            "dedup_window_sec": rule.dedup_window_sec,
            "template_id": rule.template_id,
            "recipient_ids": [r.id for r in rule.recipients],
            "channel_ids": channel_rows,
            "test_channel_ids": rule.test_channel_ids or [],
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
        }
    )


class RuleTestRequest(BaseModel):
    event_id: Optional[str] = Field(None, description="Внешний идентификатор события")
    severity: Optional[str] = None
    tags: Optional[Dict] = None
    host: Optional[str] = None
    context: Optional[Dict] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class RuleTestResponse(BaseModel):
    status: str = "queued"
    event_id: str
    tasks_enqueued: int


@router.get("", response_model=List[NotificationRuleResponse])
def list_rules(
    enabled: Optional[bool] = Query(None, description="Фильтр по включённым правилам"),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    rules = service.list_rules(enabled=enabled)
    return [_serialize_rule(rule, db) for rule in rules]


@router.post("", response_model=NotificationRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(data: NotificationRuleCreate, db: Session = Depends(get_db)):
    service = NotificationService(db)
    rule = service.create_rule(data)
    return _serialize_rule(rule, db)


@router.get("/{rule_id}", response_model=NotificationRuleResponse)
def get_rule(rule_id: UUID, db: Session = Depends(get_db)):
    service = NotificationService(db)
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return _serialize_rule(rule, db)


@router.patch("/{rule_id}", response_model=NotificationRuleResponse)
def update_rule(rule_id: UUID, data: NotificationRuleUpdate, db: Session = Depends(get_db)):
    service = NotificationService(db)
    rule = service.update_rule(rule_id, data)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return _serialize_rule(rule, db)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: UUID, db: Session = Depends(get_db)):
    service = NotificationService(db)
    deleted = service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{rule_id}/test", response_model=RuleTestResponse, status_code=status.HTTP_202_ACCEPTED)
def test_rule(rule_id: UUID, request: RuleTestRequest, db: Session = Depends(get_db)):
    service = NotificationService(db)
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    event_id = request.event_id or str(uuid4())
    routing = NotificationRoutingService(db)

    # Собираем доставку только по этому правилу (без глобального матчинга)
    channel_ids = routing._ordered_channel_ids(rule.id)
    if not channel_ids or not rule.recipients:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rule has no channels or recipients")

    plan = [
        {
            "event_id": event_id,
            "rule_id": rule.id,
            "recipient_id": recipient.id,
            "channel_ids": channel_ids,
            "failover_timeout_sec": rule.failover_timeout_sec,
            "context": request.context or {},
            "subject": request.subject,
            "body": request.body,
        }
        for recipient in rule.recipients
    ]

    enqueued = 0
    for item in plan:
        delay = 0
        for channel_id in item["channel_ids"]:
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

    return RuleTestResponse(event_id=event_id, tasks_enqueued=enqueued)
