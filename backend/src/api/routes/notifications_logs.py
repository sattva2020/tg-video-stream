"""Журнал доставки уведомлений: фильтрация и просмотр деталей."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.notifications import DeliveryLogResponse
from src.services.notifications.base import NotificationService

router = APIRouter(prefix="/api/notifications/logs", tags=["Notifications"])


@router.get("", response_model=List[DeliveryLogResponse])
def list_delivery_logs(
    *,
    db: Session = Depends(get_db),
    rule_id: Optional[UUID] = Query(None, description="Фильтр по правилу"),
    channel_id: Optional[UUID] = Query(None, description="Фильтр по каналу"),
    recipient_id: Optional[UUID] = Query(None, description="Фильтр по получателю"),
    event_id: Optional[str] = Query(None, description="Фильтр по внешнему event_id"),
    statuses: Optional[List[str]] = Query(None, description="Список статусов: success/fail/failover/suppressed/rate-limited/deduped"),
    created_from: Optional[datetime] = Query(None, description="Начало диапазона создания"),
    created_to: Optional[datetime] = Query(None, description="Конец диапазона создания"),
    limit: int = Query(100, ge=1, le=500),
):
    service = NotificationService(db)
    normalized_statuses: Optional[List[str]] = None
    if statuses:
        flattened: List[str] = []
        for value in statuses:
            parts = [part.strip() for part in value.split(",") if part.strip()]
            flattened.extend(parts)
        if flattened:
            normalized_statuses = flattened
    logs = service.list_logs(
        rule_id=rule_id,
        channel_id=channel_id,
        recipient_id=recipient_id,
        event_id=event_id,
        statuses=normalized_statuses,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
    )
    return logs


@router.get("/{log_id}", response_model=DeliveryLogResponse)
def get_delivery_log(log_id: UUID, db: Session = Depends(get_db)):
    service = NotificationService(db)
    log = service.get_log(log_id)
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log not found")
    return log
