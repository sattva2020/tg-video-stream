"""
Alert Groups API Routes.

API endpoints for viewing alert groups and statistics.
Создан в рамках Feature 013 (Alerting & Notification System).

Endpoints:
- GET /api/alerts/groups - List alert groups
- GET /api/alerts/groups/{group_id} - Get specific group details
- GET /api/alerts/groups/statistics - Get alert statistics
- PATCH /api/alerts/groups/{group_id}/resolve - Resolve alert group
"""

import logging
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.alert import AlertGroup, AlertInstance
from src.services.alert_service import AlertService
from api.auth import get_current_user
from src.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts/groups", tags=["Alerts"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class AlertGroupResponse(BaseModel):
    """Ответ с информацией о группе алертов."""
    id: uuid.UUID
    rule_id: uuid.UUID
    group_key: str
    name: Optional[str] = None
    status: str
    alert_count: int
    first_alert_at: str
    last_alert_at: str
    notification_sent: bool
    last_notification_at: Optional[str] = None
    notification_count: int = 0
    severity: str
    context: Optional[dict] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[uuid.UUID] = None
    created_at: str
    updated_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AlertGroupDetailResponse(BaseModel):
    """Ответ с детальной информацией о группе алертов."""
    id: uuid.UUID
    rule_id: uuid.UUID
    group_key: str
    name: Optional[str] = None
    status: str
    alert_count: int
    first_alert_at: str
    last_alert_at: str
    notification_sent: bool
    last_notification_at: Optional[str] = None
    notification_count: int = 0
    severity: str
    context: Optional[dict] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[uuid.UUID] = None
    created_at: str
    updated_at: Optional[str] = None
    # Instances in this group
    instances: List[dict] = []

    model_config = ConfigDict(from_attributes=True)


class AlertStatisticsResponse(BaseModel):
    """Ответ со статистикой алертов."""
    total_groups: int
    active_groups: int
    resolved_groups: int
    suppressed_groups: int
    total_alerts: int
    critical_alerts: int
    warning_alerts: int
    info_alerts: int
    most_active_group: Optional[dict] = None
    oldest_active_group: Optional[dict] = None
    average_alerts_per_group: Optional[float] = None


class ResolveGroupRequest(BaseModel):
    """Запрос на разрешение группы алертов."""
    resolved: bool = True


class ResolveGroupResponse(BaseModel):
    """Ответ на запрос разрешения группы."""
    success: bool
    message: str
    group_id: uuid.UUID


# ============================================================================
# Alert Groups Endpoints
# ============================================================================

@router.get("", response_model=List[AlertGroupResponse])
async def list_alert_groups(
    rule_id: Optional[uuid.UUID] = Query(None, description="Фильтр по правилу"),
    status_filter: Optional[str] = Query(None, description="Фильтр по статусу (active, resolved, suppressed)"),
    severity: Optional[str] = Query(None, description="Фильтр по уровню важности (critical, warning, info)"),
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей"),
    limit: int = Query(50, ge=1, le=100, description="Максимальное количество записей"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить список групп алертов.

    Возвращает группы алертов с возможностью фильтрации и пагинации.
    Группы используются для предотвращения спама уведомлений при повторяющихся алертах.
    """
    try:
        service = AlertService(db)
        groups = service.list_groups(
            rule_id=rule_id if rule_id else None,
            status=status_filter,
            severity=severity,
            limit=limit + skip  # Fetch extra for pagination
        )

        # Apply pagination
        paginated_groups = groups[skip:skip + limit]

        # Конвертируем datetime в ISO format
        return [
            AlertGroupResponse(
                id=group.id,
                rule_id=group.rule_id,
                group_key=group.group_key,
                name=group.name,
                status=group.status,
                alert_count=group.alert_count,
                first_alert_at=group.first_alert_at.isoformat(),
                last_alert_at=group.last_alert_at.isoformat(),
                notification_sent=group.notification_sent,
                last_notification_at=group.last_notification_at.isoformat() if group.last_notification_at else None,
                notification_count=group.notification_count,
                severity=group.severity,
                context=group.context,
                resolved_at=group.resolved_at.isoformat() if group.resolved_at else None,
                resolved_by=group.resolved_by,
                created_at=group.created_at.isoformat(),
                updated_at=group.updated_at.isoformat() if group.updated_at else None
            )
            for group in paginated_groups
        ]

    except Exception as e:
        logger.error(f"Error listing alert groups: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alert groups: {str(e)}"
        )


@router.get("/statistics", response_model=AlertStatisticsResponse)
async def get_alert_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить статистику алертов.

    Возвращает агрегированную статистику по группам алертов и алертам.
    """
    try:
        # Подсчет групп по статусам
        total_groups = db.query(AlertGroup).count()
        active_groups = db.query(AlertGroup).filter(AlertGroup.status == "active").count()
        resolved_groups = db.query(AlertGroup).filter(AlertGroup.status == "resolved").count()
        suppressed_groups = db.query(AlertGroup).filter(AlertGroup.status == "suppressed").count()

        # Подсчет алертов по важности
        total_alerts = db.query(AlertInstance).count()
        critical_alerts = db.query(AlertInstance).filter(AlertInstance.severity == "critical").count()
        warning_alerts = db.query(AlertInstance).filter(AlertInstance.severity == "warning").count()
        info_alerts = db.query(AlertInstance).filter(AlertInstance.severity == "info").count()

        # Самая активная группа (больше всего алертов)
        most_active_group = (
            db.query(AlertGroup)
            .filter(AlertGroup.alert_count > 0)
            .order_by(AlertGroup.alert_count.desc())
            .first()
        )

        # Самая старая активная группа
        oldest_active_group = (
            db.query(AlertGroup)
            .filter(AlertGroup.status == "active")
            .order_by(AlertGroup.created_at.asc())
            .first()
        )

        # Среднее количество алертов на группу
        avg_alerts = None
        if total_groups > 0:
            total_alert_count = db.query(AlertGroup).with_entities(
                db.func.sum(AlertGroup.alert_count)
            ).scalar() or 0
            avg_alerts = round(total_alert_count / total_groups, 2)

        return AlertStatisticsResponse(
            total_groups=total_groups,
            active_groups=active_groups,
            resolved_groups=resolved_groups,
            suppressed_groups=suppressed_groups,
            total_alerts=total_alerts,
            critical_alerts=critical_alerts,
            warning_alerts=warning_alerts,
            info_alerts=info_alerts,
            most_active_group={
                "id": str(most_active_group.id),
                "group_key": most_active_group.group_key,
                "alert_count": most_active_group.alert_count,
                "severity": most_active_group.severity
            } if most_active_group else None,
            oldest_active_group={
                "id": str(oldest_active_group.id),
                "group_key": oldest_active_group.group_key,
                "created_at": oldest_active_group.created_at.isoformat(),
                "alert_count": oldest_active_group.alert_count
            } if oldest_active_group else None,
            average_alerts_per_group=avg_alerts
        )

    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alert statistics: {str(e)}"
        )


@router.get("/{group_id}", response_model=AlertGroupDetailResponse)
async def get_alert_group(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить детальную информацию о группе алертов.

    Возвращает информацию о группе вместе со списком входящих в неё алертов.
    """
    try:
        service = AlertService(db)
        group = service.get_group(group_id)

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert group {group_id} not found"
            )

        # Get instances in this group
        instances = db.query(AlertInstance).filter(
            AlertInstance.group_id == group_id
        ).order_by(AlertInstance.fired_at.desc()).limit(100).all()

        instances_data = [
            {
                "id": str(inst.id),
                "alert_type": inst.alert_type,
                "severity": inst.severity,
                "status": inst.status,
                "trigger_value": inst.trigger_value,
                "fired_at": inst.fired_at.isoformat(),
                "resolved_at": inst.resolved_at.isoformat() if inst.resolved_at else None,
                "duration_sec": inst.duration_sec
            }
            for inst in instances
        ]

        return AlertGroupDetailResponse(
            id=group.id,
            rule_id=group.rule_id,
            group_key=group.group_key,
            name=group.name,
            status=group.status,
            alert_count=group.alert_count,
            first_alert_at=group.first_alert_at.isoformat(),
            last_alert_at=group.last_alert_at.isoformat(),
            notification_sent=group.notification_sent,
            last_notification_at=group.last_notification_at.isoformat() if group.last_notification_at else None,
            notification_count=group.notification_count,
            severity=group.severity,
            context=group.context,
            resolved_at=group.resolved_at.isoformat() if group.resolved_at else None,
            resolved_by=group.resolved_by,
            created_at=group.created_at.isoformat(),
            updated_at=group.updated_at.isoformat() if group.updated_at else None,
            instances=instances_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert group: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alert group: {str(e)}"
        )


@router.patch("/{group_id}/resolve", response_model=ResolveGroupResponse)
async def resolve_alert_group(
    group_id: uuid.UUID,
    request: ResolveGroupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Разрешить группу алертов.

    Позволяет вручную отметить группу алертов как разрешенную.
    Это также обновит все входящие в группу алерты.
    """
    try:
        service = AlertService(db)
        group = service.get_group(group_id)

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert group {group_id} not found"
            )

        # Resolve the group
        resolved_group = service.resolve_group(group_id, resolved_by=current_user.id)

        if not resolved_group:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to resolve alert group"
            )

        # Also resolve all instances in this group
        instances = db.query(AlertInstance).filter(
            AlertInstance.group_id == group_id,
            AlertInstance.status == "firing"
        ).all()

        for instance in instances:
            service.resolve_instance(instance.id)

        return ResolveGroupResponse(
            success=True,
            message=f"Alert group {group_id} resolved successfully",
            group_id=group_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving alert group: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert group: {str(e)}"
        )
