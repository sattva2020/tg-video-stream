"""API для тестирования алертов: ручной запуск для проверки."""
import logging
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from src.database import get_db
from src.services.alert_evaluator import EvaluationResult
from src.services.alert_service import AlertService
from src.services.alert_trigger_service import AlertTriggerService

router = APIRouter(prefix="/api/alerts/test", tags=["Alerts"])


class AlertTestRequest(BaseModel):
    """Запрос на тестовый запуск алерта."""

    alert_type: str = Field(..., description="Тип алерта (system_resource, viewer_count, api_rate_limit, stream_failure)")
    metric: str = Field(..., description="Метрика (cpu_usage, memory_usage, disk_usage, viewer_count, etc.)")
    value: float = Field(..., description="Значение метрики для теста")
    severity: str = Field(default="warning", description="Уровень важности (critical, warning, info)")
    context: Optional[dict] = Field(None, description="Дополнительный контекст алерта")


class AlertTestResponse(BaseModel):
    """Ответ на тестовый запуск алерта."""

    status: str = Field(..., description="Статус запуска (queued)")
    event_id: str = Field(..., description="ID события для отслеживания")
    instance_id: Optional[UUID] = Field(None, description="ID созданного экземпляра алерта")


@router.post("", response_model=AlertTestResponse, status_code=status.HTTP_202_ACCEPTED)
def test_alert(request: AlertTestRequest, db: Session = Depends(get_db)):
    """Ручной запуск алерта для тестирования.

    Создает тестовый алерт с указанными параметрами, игнорируя правила оценки.
    Полезен для проверки настроек уведомлений и форматирования сообщений.

    Args:
        request: Параметры тестового алерта
        db: Сессия базы данных

    Returns:
        AlertTestResponse: Статус запуска и ID события

    Raises:
        HTTPException: Ошибка при создании алерта
    """
    try:
        alert_service = AlertService(db)
        trigger_service = AlertTriggerService(db)

        # Создание временного правила для тестового алерта
        from src.schemas.alerts import AlertRuleCreate
        test_rule_data = AlertRuleCreate(
            name=f"[TEST] {request.alert_type}-{request.metric}",
            description=f"Temporary test rule for {request.alert_type}",
            enabled=True,
            alert_type=request.alert_type,
            severity=request.severity,
            conditions={
                "metric": request.metric,
                "operator": "gt",
                "threshold": request.value * 0.9,
            },
            cooldown_sec=0,  # Без коолдауна для тестов
            notify_on_recovery=False,
        )
        test_rule = alert_service.create_rule(test_rule_data)

        try:
            # Создание результата оценки для тестового алерта
            result = EvaluationResult(
                triggered=True,
                rule_id=test_rule.id,
                rule_name=test_rule.name,
                alert_type=request.alert_type,
                severity=request.severity,
                trigger_value={
                    "metric": request.metric,
                    "current_value": request.value,
                    "threshold": request.value * 0.9,
                    "operator": "gt",
                },
                context=request.context or {},
                reason=f"Manual test alert: {request.metric} = {request.value}",
            )

            # Запуск алерта
            instance = trigger_service.trigger_alert(result)

            if not instance:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create test alert instance",
                )

            # Формирование ответа
            event_id = str(uuid4())

            logger.info(
                f"Test alert triggered: {request.alert_type}",
                extra={
                    "event_id": event_id,
                    "test_alert_type": request.alert_type,
                    "metric": request.metric,
                    "value": request.value,
                    "instance_id": str(instance.id),
                    "rule_id": str(test_rule.id),
                },
            )

            return AlertTestResponse(
                status="queued",
                event_id=event_id,
                instance_id=instance.id,
            )

        finally:
            # Очистка: удаление временного правила
            try:
                alert_service.delete_rule(test_rule.id)
                logger.debug(f"Cleaned up test rule: {test_rule.id}")
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to cleanup test rule: {test_rule.id}",
                    extra={"error": str(cleanup_error)},
                )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering test alert: {str(exc)}",
        )
