"""
Stream Failure Alert Integration Service

Интеграционный сервис, связывающий StreamFailureAlertMonitor с AlertTriggerService.

Обеспечивает автоматическое создание алертов при обнаружении отказов потоков
и отправку уведомлений о восстановлении.

Функционал:
- Callback для обнаружения отказов -> создание AlertInstance -> отправка уведомлений
- Callback для восстановления -> создание resolved AlertInstance -> отправка уведомлений
- Группировка алертов для предотвращения спама
- Использование существующих AlertRule для stream_failure

Использование:
    integration = StreamAlertIntegrationService()
    await integration.initialize()
    # Теперь отказы потоков автоматически создают алерты
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.services.alert_evaluator import EvaluationResult
from src.services.alert_trigger_service import AlertTriggerService
from src.services.alert_grouping_service import AlertGroupingService
from src.services.alert_service import AlertService
from src.services.stream_failure_monitor import (
    StreamFailureAlertMonitor,
    StreamHealthStatus,
    get_stream_failure_alert_monitor,
)
from src.models.alert import AlertRule

logger = logging.getLogger(__name__)


class StreamAlertIntegrationService:
    """
    Интеграционный сервис для связывания мониторинга отказов с алертами.

    Настраивает callbacks в StreamFailureAlertMonitor для автоматического
    создания алертов через AlertTriggerService.
    """

    def __init__(self):
        self.failure_monitor: Optional[StreamFailureAlertMonitor] = None
        self._db_session_factory = None
        self._initialized = False

    def initialize(self) -> None:
        """Инициализировать интеграцию.

        Настраивает callbacks в StreamFailureAlertMonitor для создания алертов.
        """
        if self._initialized:
            logger.warning("StreamAlertIntegrationService already initialized")
            return

        try:
            # Создать factory для сессий БД
            engine = create_engine(settings.DATABASE_URL)
            self._db_session_factory = sessionmaker(bind=engine)

            # Получить монитор отказов
            self.failure_monitor = get_stream_failure_alert_monitor()

            # Настроить callbacks
            self.failure_monitor.on_failure_detected_callback = self._on_failure_detected
            self.failure_monitor.on_failure_recovery_callback = self._on_failure_recovery

            self._initialized = True
            logger.info("StreamAlertIntegrationService initialized successfully")

        except Exception as exc:
            logger.exception(f"Failed to initialize StreamAlertIntegrationService: {exc}")
            raise

    def _get_db_session(self) -> Session:
        """Получить сессию БД."""
        if not self._db_session_factory:
            raise RuntimeError("StreamAlertIntegrationService not initialized")
        return self._db_session_factory()

    async def _on_failure_detected(
        self,
        stream_id: str,
        failure_type: str,
        message: str,
        health_status: StreamHealthStatus,
    ) -> None:
        """Callback при обнаружении отказа потока.

        Создает алерт через AlertTriggerService.

        Args:
            stream_id: ID потока
            failure_type: Тип отказа
            message: Сообщение об ошибке
            health_status: Статус здоровья потока
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для stream_failure
            rule = self._get_or_create_stream_failure_rule(db)

            if not rule:
                logger.error(f"Failed to get or create stream_failure rule for stream {stream_id}")
                return

            # Создать результат оценки
            evaluation_result = self._create_failure_evaluation_result(
                rule=rule,
                stream_id=stream_id,
                failure_type=failure_type,
                message=message,
                health_status=health_status,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "stream_id": stream_id,
                "host": health_status.stream_id,
                "service": "stream",
                "tags": {
                    "failure_type": failure_type,
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="stream_failure",
                severity=evaluation_result.severity,
            )

            # Запустить алерт
            trigger_service = AlertTriggerService(db)
            instance = trigger_service.trigger_alert(
                result=evaluation_result,
                group_id=group.id if group else None,
                group_key=group.group_key if group else None,
            )

            if instance:
                logger.info(
                    f"Stream failure alert triggered: {stream_id}",
                    extra={
                        "stream_id": stream_id,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "failure_type": failure_type,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for stream {stream_id}")

        except Exception as exc:
            logger.exception(
                f"Error in failure_detected callback for stream {stream_id}: {exc}"
            )
        finally:
            db.close()

    async def _on_failure_recovery(
        self,
        stream_id: str,
        health_status: StreamHealthStatus,
    ) -> None:
        """Callback при восстановлении потока.

        Создает алерт восстановления через AlertTriggerService.

        Args:
            stream_id: ID потока
            health_status: Статус здоровья потока
        """
        db = self._get_db_session()
        try:
            # Найти правило для stream_failure
            rule = self._get_stream_failure_rule(db)

            if not rule or not rule.notify_on_recovery:
                logger.debug(f"Recovery notifications disabled for stream {stream_id}")
                return

            # Найти активную группу для этого потока
            grouping_service = AlertGroupingService(db)
            active_groups = grouping_service.get_active_groups_for_rule(rule_id=rule.id)

            # Найти группу для этого stream_id
            group = None
            for active_group in active_groups:
                if active_group.context and active_group.context.get("stream_id") == stream_id:
                    group = active_group
                    break

            # Запустить алерт восстановления
            trigger_service = AlertTriggerService(db)
            context = {
                "stream_id": stream_id,
                "host": stream_id,
                "service": "stream",
            }

            instance = trigger_service.trigger_recovery_alert(
                rule=rule,
                group_id=group.id if group else None,
                context=context,
            )

            if instance:
                logger.info(
                    f"Stream recovery alert triggered: {stream_id}",
                    extra={
                        "stream_id": stream_id,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                    },
                )

                # Разрешить группу
                if group:
                    grouping_service.resolve_group(group)

        except Exception as exc:
            logger.exception(
                f"Error in failure_recovery callback for stream {stream_id}: {exc}"
            )
        finally:
            db.close()

    def _get_or_create_stream_failure_rule(self, db: Session) -> Optional[AlertRule]:
        """Найти или создать правило алерта для отказов потоков.

        Args:
            db: Сессия БД

        Returns:
            AlertRule для stream_failure
        """
        # Сначала пытаемся найти существующее правило
        rule = self._get_stream_failure_rule(db)

        if rule:
            return rule

        # Создать новое правило
        try:
            alert_service = AlertService(db)

            from src.schemas.alerts import AlertRuleCreate

            rule_data = AlertRuleCreate(
                name="Stream Failure Detection",
                description="Automatic alert triggered when stream failure is detected",
                alert_type="stream_failure",
                severity="critical",
                enabled=True,
                conditions={
                    "metric": "stream_health",
                    "operator": "eq",
                    "threshold": False,
                    "consecutive_failures": 3,
                },
                notification_channels={},  # Будет заполнено администратором
                cooldown_sec=300,  # 5 минут
                notify_on_recovery=True,
                grouping_window_sec=300,  # 5 минут
            )

            rule = alert_service.create_rule(rule_data)
            logger.info(f"Created default stream_failure rule: {rule.id}")
            return rule

        except Exception as exc:
            logger.exception(f"Failed to create stream_failure rule: {exc}")
            return None

    def _get_stream_failure_rule(self, db: Session) -> Optional[AlertRule]:
        """Найти правило алерта для отказов потоков.

        Args:
            db: Сессия БД

        Returns:
            AlertRule для stream_failure или None
        """
        try:
            from src.models.alert import AlertRule

            rule = (
                db.query(AlertRule)
                .filter(
                    AlertRule.alert_type == "stream_failure",
                    AlertRule.enabled == True,
                )
                .order_by(AlertRule.created_at.desc())
                .first()
            )

            return rule

        except Exception as exc:
            logger.exception(f"Failed to query stream_failure rule: {exc}")
            return None

    def _create_failure_evaluation_result(
        self,
        rule: AlertRule,
        stream_id: str,
        failure_type: str,
        message: str,
        health_status: StreamHealthStatus,
    ) -> EvaluationResult:
        """Создать результат оценки для отказа.

        Args:
            rule: Правило алерта
            stream_id: ID потока
            failure_type: Тип отказа
            message: Сообщение об ошибке
            health_status: Статус здоровья

        Returns:
            EvaluationResult
        """
        # Определить severity на основе типа отказа
        severity_mapping = {
            "network": "critical",
            "api": "critical",
            "codec": "warning",
            "session": "critical",
            "process_crash": "critical",
            "unknown": "warning",
        }
        severity = severity_mapping.get(failure_type, "warning")

        trigger_value = {
            "metric": "stream_health",
            "current_value": False,
            "threshold": False,
            "operator": "eq",
            "failure_type": failure_type,
            "consecutive_failures": health_status.consecutive_failures,
        }

        context = {
            "stream_id": stream_id,
            "host": stream_id,
            "service": "stream",
            "tags": {
                "failure_type": failure_type,
                "consecutive_failures": str(health_status.consecutive_failures),
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="stream_failure",
            severity=severity,
            trigger_value=trigger_value,
            context=context,
            reason=f"Stream failure detected: {failure_type} - {message}",
            should_cooldown=False,
            consecutive_failures_met=True,
        )


# Singleton instance
_stream_alert_integration: Optional[StreamAlertIntegrationService] = None


def get_stream_alert_integration() -> StreamAlertIntegrationService:
    """Получить singleton экземпляр StreamAlertIntegrationService."""
    global _stream_alert_integration
    if _stream_alert_integration is None:
        _stream_alert_integration = StreamAlertIntegrationService()
    return _stream_alert_integration


async def initialize_stream_alert_integration() -> None:
    """Инициализировать интеграцию мониторинга потоков с алертами.

    Эта функция должна быть вызвана при старте приложения для настройки
    автоматического создания алертов при обнаружении отказов потоков.
    """
    integration = get_stream_alert_integration()
    integration.initialize()
    logger.info("Stream alert integration initialized")
