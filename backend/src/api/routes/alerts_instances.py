"""История алертов: фильтрация и просмотр деталей."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.alerts import AlertInstanceResponse
from src.services.alert_service import AlertService

router = APIRouter(prefix="/api/alerts/instances", tags=["Alerts"])


@router.get("", response_model=List[AlertInstanceResponse])
def list_alert_instances(
    *,
    db: Session = Depends(get_db),
    rule_id: Optional[UUID] = Query(None, description="Фильтр по правилу"),
    status: Optional[str] = Query(None, description="Фильтр по статусу: firing/resolved/acknowledged/suppressed"),
    alert_type: Optional[str] = Query(None, description="Фильтр по типу алерта"),
    severity: Optional[str] = Query(None, description="Фильтр по уровню важности: critical/warning/info"),
    group_id: Optional[UUID] = Query(None, description="Фильтр по группе"),
    limit: int = Query(100, ge=1, le=500),
):
    service = AlertService(db)
    instances = service.list_instances(
        rule_id=rule_id,
        status=status,
        alert_type=alert_type,
        severity=severity,
        group_id=group_id,
        limit=limit,
    )
    return instances


@router.get("/{instance_id}", response_model=AlertInstanceResponse)
def get_alert_instance(instance_id: UUID, db: Session = Depends(get_db)):
    service = AlertService(db)
    instance = service.get_instance(instance_id)
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert instance not found")
    return instance
