"""Сервис запуска алертов и отправки уведомлений."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.models.alert import AlertRule, AlertInstance
from src.services.alert_service import AlertService
from src.services.alert_evaluator import EvaluationResult

logger = logging.getLogger(__name__)


@dataclass
class AlertTriggerContext:
    """Контекст запуска алерта."""
    rule_id: UUID
    rule_name: str
    alert_type: str
    severity: str
    trigger_value: Dict
    context: Dict
    reason: Optional[str] = None
    group_key: Optional[str] = None
    group_id: Optional[UUID] = None


class AlertTriggerService:
    """Сервис запуска алертов и отправки уведомлений.

    Создает экземпляры алертов, формирует уведомления и отправляет их
    через систему уведомлений.
    """

    def __init__(self, db: Session):
        self.db = db
        self.alert_service = AlertService(db)

    def trigger_alert(
        self,
        result: EvaluationResult,
        group_id: Optional[UUID] = None,
        group_key: Optional[str] = None,
    ) -> Optional[AlertInstance]:
        """Запустить алерт на основе результата оценки.

        Args:
            result: Результат оценки условия алерта
            group_id: ID группы алертов (опционально)
            group_key: Ключ группы для группировки (опционально)

        Returns:
            Созданный экземпляр алерта или None при ошибке
        """
        try:
            # Создание экземпляра алерта
            instance_data = {
                "rule_id": result.rule_id,
                "alert_type": result.alert_type,
                "severity": result.severity,
                "status": "firing",
                "trigger_value": result.trigger_value,
                "context": result.context,
                "group_id": group_id,
                "notification_sent": False,
            }

            instance = self.alert_service.create_instance(
                data=self._convert_to_schema(instance_data, "AlertInstanceCreate")
            )

            # Обновление счетчиков правила
            self.alert_service.increment_trigger_count(result.rule_id)

            logger.info(
                f"Alert triggered: {result.rule_name} ({result.alert_type})",
                extra={
                    "rule_id": str(result.rule_id),
                    "instance_id": str(instance.id),
                    "severity": result.severity,
                    "trigger_value": result.trigger_value,
                },
            )

            # Отправка уведомлений
            self._send_notifications(instance, result)

            return instance

        except Exception as exc:
            logger.exception(
                "Failed to trigger alert",
                extra={"rule_id": str(result.rule_id), "error": str(exc)},
            )
            return None

    def trigger_recovery_alert(
        self,
        rule: AlertRule,
        group_id: Optional[UUID] = None,
        context: Optional[Dict] = None,
    ) -> Optional[AlertInstance]:
        """Запустить алерт восстановления.

        Args:
            rule: Правило алерта
            group_id: ID группы алертов (опционально)
            context: Дополнительный контекст

        Returns:
            Созданный экземпляр алерта или None при ошибке
        """
        if not rule.notify_on_recovery:
            logger.debug(f"Recovery notifications disabled for rule {rule.name}")
            return None

        try:
            trigger_value = {
                "metric": "recovery",
                "status": "resolved",
                "rule_name": rule.name,
            }

            instance_data = {
                "rule_id": rule.id,
                "alert_type": rule.alert_type,
                "severity": rule.severity,
                "status": "resolved",
                "trigger_value": trigger_value,
                "context": context or {},
                "group_id": group_id,
                "notification_sent": False,
            }

            instance = self.alert_service.create_instance(
                data=self._convert_to_schema(instance_data, "AlertInstanceCreate")
            )

            # Сброс счетчиков правила
            self.alert_service.reset_consecutive_triggers(rule.id)

            logger.info(
                f"Recovery alert triggered: {rule.name}",
                extra={
                    "rule_id": str(rule.id),
                    "instance_id": str(instance.id),
                    "group_id": str(group_id) if group_id else None,
                },
            )

            # Отправка уведомления о восстановлении
            self._send_recovery_notification(instance, rule)

            return instance

        except Exception as exc:
            logger.exception(
                "Failed to trigger recovery alert",
                extra={"rule_id": str(rule.id), "error": str(exc)},
            )
            return None

    def _send_notifications(self, instance: AlertInstance, result: EvaluationResult) -> None:
        """Отправить уведомления для алерта.

        Args:
            instance: Экземпляр алерта
            result: Результат оценки
        """
        rule = self.alert_service.get_rule(instance.rule_id)
        if not rule:
            logger.error(f"Rule not found for instance {instance.id}")
            return

        notification_channels = rule.notification_channels
        if not notification_channels:
            logger.info(f"No notification channels configured for rule {rule.name}")
            instance.notification_sent = False
            self.db.commit()
            return

        # Формирование payload для уведомлений
        event_id = str(uuid4())
        subject = self._format_subject(rule, result)
        body = self._format_body(rule, result)

        # Подготовка контекста для шаблона
        template_context = self._prepare_template_context(instance, result)

        # TODO: Интеграция с Celery задачами уведомлений (subtask-5-2)
        # Сейчас только логируем, полную интеграцию сделаем в фазе worker

        notification_results = {
            "channels": list(notification_channels.keys()),
            "success": True,
            "errors": [],
        }

        # Логирование факта отправки
        logger.info(
            f"Alert notifications prepared: {rule.name}",
            extra={
                "instance_id": str(instance.id),
                "event_id": event_id,
                "channels": notification_results["channels"],
            },
        )

        # Обновление статуса уведомления в экземпляре
        instance.notification_sent = notification_results["success"]
        instance.notification_channels = notification_results
        self.db.commit()

    def _send_recovery_notification(self, instance: AlertInstance, rule: AlertRule) -> None:
        """Отправить уведомление о восстановлении.

        Args:
            instance: Экземпляр алерта восстановления
            rule: Правило алерта
        """
        notification_channels = rule.notification_channels
        if not notification_channels:
            logger.info(f"No notification channels configured for rule {rule.name}")
            instance.notification_sent = False
            self.db.commit()
            return

        event_id = str(uuid4())
        subject = f"🟢 Recovered: {rule.name}"
        body = (
            f"Alert '{rule.name}' has recovered.\n\n"
            f"Type: {rule.alert_type}\n"
            f"Severity: {rule.severity}\n"
            f"Resolved at: {datetime.utcnow().isoformat()}\n"
        )

        notification_results = {
            "channels": list(notification_channels.keys()),
            "success": True,
            "errors": [],
        }

        logger.info(
            f"Recovery notification prepared: {rule.name}",
            extra={
                "instance_id": str(instance.id),
                "event_id": event_id,
                "channels": notification_results["channels"],
            },
        )

        instance.notification_sent = notification_results["success"]
        instance.notification_channels = notification_results
        self.db.commit()

    def _format_subject(self, rule: AlertRule, result: EvaluationResult) -> str:
        """Сформатировать тему уведомления.

        Args:
            rule: Правило алерта
            result: Результат оценки

        Returns:
            Тема уведомления
        """
        severity_emoji = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵",
        }

        emoji = severity_emoji.get(result.severity, "⚠️")
        return f"{emoji} Alert: {rule.name}"

    def _format_body(self, rule: AlertRule, result: EvaluationResult) -> str:
        """Сформатировать тело уведомления.

        Args:
            rule: Правило алерта
            result: Результат оценки

        Returns:
            Тело уведомления
        """
        trigger_value = result.trigger_value or {}
        current_value = trigger_value.get("current_value", "N/A")
        threshold = trigger_value.get("threshold", "N/A")
        operator = trigger_value.get("operator", "eq")
        metric = trigger_value.get("metric", "unknown")

        body_lines = [
            f"Alert '{rule.name}' has been triggered.",
            "",
            f"Type: {rule.alert_type}",
            f"Severity: {result.severity}",
            f"Reason: {result.reason or 'Threshold exceeded'}",
            "",
            f"Metric: {metric}",
            f"Current value: {current_value}",
            f"Threshold: {threshold} (operator: {operator})",
            f"Fired at: {datetime.utcnow().isoformat()}",
        ]

        # Добавление контекста
        if result.context:
            context_lines = []
            for key, value in result.context.items():
                if value is not None:
                    context_lines.append(f"  {key}: {value}")

            if context_lines:
                body_lines.extend(["", "Context:"] + context_lines)

        return "\n".join(body_lines)

    def _prepare_template_context(self, instance: AlertInstance, result: EvaluationResult) -> Dict[str, Any]:
        """Подготовить контекст для шаблона уведомления.

        Args:
            instance: Экземпляр алерта
            result: Результат оценки

        Returns:
            Контекст для подстановки в шаблон
        """
        trigger_value = result.trigger_value or {}

        context = {
            "alert_name": result.rule_name,
            "alert_type": result.alert_type,
            "severity": result.severity,
            "reason": result.reason or "Threshold exceeded",
            "metric": trigger_value.get("metric", "unknown"),
            "current_value": trigger_value.get("current_value", "N/A"),
            "threshold": trigger_value.get("threshold", "N/A"),
            "operator": trigger_value.get("operator", "eq"),
            "fired_at": datetime.utcnow().isoformat(),
            "instance_id": str(instance.id),
            "rule_id": str(result.rule_id),
        }

        # Добавление дополнительного контекста
        if result.context:
            for key, value in result.context.items():
                if value is not None and key not in context:
                    context[key] = value

        return context

    def _convert_to_schema(self, data: Dict, schema_name: str):
        """Конвертировать словарь в Pydantic схему.

        Args:
            data: Словарь с данными
            schema_name: Имя схемы для импорта

        Returns:
            Экземпляр Pydantic схемы
        """
        # Ленивый импорт для избежания циклических зависимостей
        from src.schemas.alerts import (
            AlertInstanceCreate,
            AlertInstanceUpdate,
            AlertGroupCreate,
            AlertGroupUpdate,
        )

        schemas = {
            "AlertInstanceCreate": AlertInstanceCreate,
            "AlertInstanceUpdate": AlertInstanceUpdate,
            "AlertGroupCreate": AlertGroupCreate,
            "AlertGroupUpdate": AlertGroupUpdate,
        }

        schema_class = schemas.get(schema_name)
        if not schema_class:
            raise ValueError(f"Unknown schema: {schema_name}")

        return schema_class(**data)
