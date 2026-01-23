"""API для правил алертов: CRUD операции."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.alerts import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
)
from src.services.alert_service import AlertService

router = APIRouter(prefix="/api/alerts/rules", tags=["Alerts"])


def _serialize_rule(rule) -> AlertRuleResponse:
    """Сериализация правила алерта в ответ API."""
    return AlertRuleResponse.model_validate(
        {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "enabled": rule.enabled,
            "alert_type": rule.alert_type,
            "severity": rule.severity,
            "category": rule.category,
            "conditions": rule.conditions,
            "cooldown_sec": rule.cooldown_sec,
            "rate_limit_minutes": rule.rate_limit_minutes,
            "rate_limit_count": rule.rate_limit_count,
            "notification_channels": rule.notification_channels,
            "notify_on_recovery": rule.notify_on_recovery,
            "auto_resolve": rule.auto_resolve,
            "escalation_enabled": rule.escalation_enabled,
            "escalation_rules": rule.escalation_rules,
            "active_windows": rule.active_windows,
            "silence_windows": rule.silence_windows,
            "last_triggered_at": rule.last_triggered_at,
            "last_resolved_at": rule.last_resolved_at,
            "trigger_count": rule.trigger_count,
            "consecutive_triggers": rule.consecutive_triggers,
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
            "created_by": rule.created_by,
            "updated_by": rule.updated_by,
        }
    )


@router.get("", response_model=List[AlertRuleResponse])
def list_rules(
    enabled: Optional[bool] = Query(None, description="Фильтр по включённым правилам"),
    alert_type: Optional[str] = Query(None, description="Фильтр по типу алерта"),
    severity: Optional[str] = Query(None, description="Фильтр по уровню важности"),
    db: Session = Depends(get_db),
):
    """Получить список правил алертов с опциональной фильтрацией."""
    service = AlertService(db)
    rules = service.list_rules(enabled=enabled, alert_type=alert_type, severity=severity)
    return [_serialize_rule(rule) for rule in rules]


@router.post("", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(data: AlertRuleCreate, db: Session = Depends(get_db)):
    """Создать новое правило алерта."""
    service = AlertService(db)
    rule = service.create_rule(data)
    return _serialize_rule(rule)


@router.get("/{rule_id}", response_model=AlertRuleResponse)
def get_rule(rule_id: UUID, db: Session = Depends(get_db)):
    """Получить правило алерта по ID."""
    service = AlertService(db)
    rule = service.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return _serialize_rule(rule)


@router.patch("/{rule_id}", response_model=AlertRuleResponse)
def update_rule(rule_id: UUID, data: AlertRuleUpdate, db: Session = Depends(get_db)):
    """Обновить правило алерта."""
    service = AlertService(db)
    rule = service.update_rule(rule_id, data)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return _serialize_rule(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: UUID, db: Session = Depends(get_db)):
    """Удалить правило алерта."""
    service = AlertService(db)
    deleted = service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
