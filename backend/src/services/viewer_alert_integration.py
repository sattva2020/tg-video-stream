"""
Viewer Count Alert Integration Service

Интеграционный сервис, связывающий ViewerCountMonitor с AlertTriggerService.

Обеспечивает автоматическое создание алертов при обнаружении низкого количества зрителей
или резкого падения аудитории, а также отправку уведомлений о восстановлении.

Функционал:
- Callback для низкого количества зрителей -> создание AlertInstance -> отправка уведомлений
- Callback для резкого падения аудитории -> создание AlertInstance -> отправка уведомлений
- Callback для восстановления -> создание resolved AlertInstance -> отправка уведомлений
- Группировка алертов для предотвращения спама
- Использование существующих AlertRule для viewer_count

Использование:
    integration = ViewerAlertIntegrationService()
    await integration.initialize()
    # Теперь проблемы с количеством зрителей автоматически создают алерты
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.services.alert_evaluator import EvaluationResult
from src.services.alert_trigger_service import AlertTriggerService
from src.services.alert_grouping_service import AlertGroupingService
from src.services.alert_service import AlertService
from src.services.monitors.viewer_count_monitor import (
    ViewerCountMonitor,
    ViewerCountStatus,
    get_viewer_count_monitor,
)
from src.models.alert import AlertRule

logger = logging.getLogger(__name__)


class ViewerAlertIntegrationService:
    """
    Интеграционный сервис для связывания мониторинга зрителей с алертами.

    Настраивает callbacks в ViewerCountMonitor для автоматического
    создания алертов через AlertTriggerService.
    """

    def __init__(self):
        self.viewer_monitor: Optional[ViewerCountMonitor] = None
        self._db_session_factory = None
        self._initialized = False

    def initialize(self) -> None:
        """Инициализировать интеграцию.

        Настраивает callbacks в ViewerCountMonitor для создания алертов.
        """
        if self._initialized:
            logger.warning("ViewerAlertIntegrationService already initialized")
            return

        try:
            # Создать factory для сессий БД
            engine = create_engine(settings.DATABASE_URL)
            self._db_session_factory = sessionmaker(bind=engine)

            # Получить монитор зрителей
            self.viewer_monitor = get_viewer_count_monitor()

            # Настроить callbacks
            self.viewer_monitor.on_low_viewers_callback = self._on_low_viewers
            self.viewer_monitor.on_viewers_drop_callback = self._on_viewers_drop
            self.viewer_monitor.on_recovery_callback = self._on_viewers_recovery

            self._initialized = True
            logger.info("ViewerAlertIntegrationService initialized successfully")

        except Exception as exc:
            logger.exception(f"Failed to initialize ViewerAlertIntegrationService: {exc}")
            raise

    def _get_db_session(self) -> Session:
        """Получить сессию БД."""
        if not self._db_session_factory:
            raise RuntimeError("ViewerAlertIntegrationService not initialized")
        return self._db_session_factory()

    async def _on_low_viewers(
        self,
        stream_id: str,
        count: int,
        threshold: int,
    ) -> None:
        """Callback при низком количестве зрителей.

        Создает алерт через AlertTriggerService.

        Args:
            stream_id: ID потока
            count: Текущее количество зрителей
            threshold: Пороговое значение
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для viewer_count
            rule = self._get_or_create_viewer_count_rule(db)

            if not rule:
                logger.error(f"Failed to get or create viewer_count rule for stream {stream_id}")
                return

            # Создать результат оценки
            evaluation_result = self._create_low_viewers_evaluation_result(
                rule=rule,
                stream_id=stream_id,
                count=count,
                threshold=threshold,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "stream_id": stream_id,
                "host": stream_id,
                "service": "stream",
                "tags": {
                    "alert_type": "low_viewers",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="viewer_count",
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
                    f"Low viewers alert triggered: {stream_id}",
                    extra={
                        "stream_id": stream_id,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "viewer_count": count,
                        "threshold": threshold,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for stream {stream_id}")

        except Exception as exc:
            logger.exception(
                f"Error in low_viewers callback for stream {stream_id}: {exc}"
            )
        finally:
            db.close()

    async def _on_viewers_drop(
        self,
        stream_id: str,
        current: int,
        peak: int,
        drop_percent: float,
    ) -> None:
        """Callback при резком падении количества зрителей.

        Создает алерт через AlertTriggerService.

        Args:
            stream_id: ID потока
            current: Текущее количество зрителей
            peak: Пиковое количество зрителей
            drop_percent: Процент падения
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для viewer_count
            rule = self._get_or_create_viewer_count_rule(db)

            if not rule:
                logger.error(f"Failed to get or create viewer_count rule for stream {stream_id}")
                return

            # Создать результат оценки
            evaluation_result = self._create_viewers_drop_evaluation_result(
                rule=rule,
                stream_id=stream_id,
                current=current,
                peak=peak,
                drop_percent=drop_percent,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "stream_id": stream_id,
                "host": stream_id,
                "service": "stream",
                "tags": {
                    "alert_type": "viewers_drop",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="viewer_count",
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
                    f"Viewers drop alert triggered: {stream_id}",
                    extra={
                        "stream_id": stream_id,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "current": current,
                        "peak": peak,
                        "drop_percent": drop_percent,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for stream {stream_id}")

        except Exception as exc:
            logger.exception(
                f"Error in viewers_drop callback for stream {stream_id}: {exc}"
            )
        finally:
            db.close()

    async def _on_viewers_recovery(self, stream_id: str) -> None:
        """Callback при восстановлении количества зрителей.

        Создает алерт восстановления через AlertTriggerService.

        Args:
            stream_id: ID потока
        """
        db = self._get_db_session()
        try:
            # Найти правило для viewer_count
            rule = self._get_viewer_count_rule(db)

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
                    f"Viewers recovery alert triggered: {stream_id}",
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
                f"Error in viewers_recovery callback for stream {stream_id}: {exc}"
            )
        finally:
            db.close()

    def _get_or_create_viewer_count_rule(self, db: Session) -> Optional[AlertRule]:
        """Найти или создать правило алерта для количества зрителей.

        Args:
            db: Сессия БД

        Returns:
            AlertRule для viewer_count
        """
        # Сначала пытаемся найти существующее правило
        rule = self._get_viewer_count_rule(db)

        if rule:
            return rule

        # Создать новое правило
        try:
            alert_service = AlertService(db)

            from src.schemas.alerts import AlertRuleCreate

            rule_data = AlertRuleCreate(
                name="Viewer Count Alert",
                description="Automatic alert triggered when viewer count drops below threshold or drops significantly",
                alert_type="viewer_count",
                severity="warning",
                enabled=True,
                conditions={
                    "metric": "viewer_count",
                    "operator": "lt",
                    "threshold": 10,
                    "drop_threshold_percent": 50.0,
                },
                notification_channels={},  # Будет заполнено администратором
                cooldown_sec=600,  # 10 минут
                notify_on_recovery=True,
                grouping_window_sec=300,  # 5 минут
            )

            rule = alert_service.create_rule(rule_data)
            logger.info(f"Created default viewer_count rule: {rule.id}")
            return rule

        except Exception as exc:
            logger.exception(f"Failed to create viewer_count rule: {exc}")
            return None

    def _get_viewer_count_rule(self, db: Session) -> Optional[AlertRule]:
        """Найти правило алерта для количества зрителей.

        Args:
            db: Сессия БД

        Returns:
            AlertRule для viewer_count или None
        """
        try:
            from src.models.alert import AlertRule

            rule = (
                db.query(AlertRule)
                .filter(
                    AlertRule.alert_type == "viewer_count",
                    AlertRule.enabled == True,
                )
                .order_by(AlertRule.created_at.desc())
                .first()
            )

            return rule

        except Exception as exc:
            logger.exception(f"Failed to query viewer_count rule: {exc}")
            return None

    def _create_low_viewers_evaluation_result(
        self,
        rule: AlertRule,
        stream_id: str,
        count: int,
        threshold: int,
    ) -> EvaluationResult:
        """Создать результат оценки для низкого количества зрителей.

        Args:
            rule: Правило алерта
            stream_id: ID потока
            count: Текущее количество зрителей
            threshold: Пороговое значение

        Returns:
            EvaluationResult
        """
        # Определить severity на основе того, насколько ниже порога
        drop_ratio = count / threshold if threshold > 0 else 0
        if drop_ratio < 0.2:
            severity = "critical"
        elif drop_ratio < 0.5:
            severity = "warning"
        else:
            severity = "info"

        trigger_value = {
            "metric": "viewer_count",
            "current_value": count,
            "threshold": threshold,
            "operator": "lt",
            "drop_ratio": round(drop_ratio, 2),
        }

        context = {
            "stream_id": stream_id,
            "host": stream_id,
            "service": "stream",
            "tags": {
                "alert_type": "low_viewers",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="viewer_count",
            severity=severity,
            trigger_value=trigger_value,
            context=context,
            reason=f"Viewer count dropped to {count} (threshold: {threshold})",
            should_cooldown=False,
            consecutive_failures_met=True,
        )

    def _create_viewers_drop_evaluation_result(
        self,
        rule: AlertRule,
        stream_id: str,
        current: int,
        peak: int,
        drop_percent: float,
    ) -> EvaluationResult:
        """Создать результат оценки для резкого падения зрителей.

        Args:
            rule: Правило алерта
            stream_id: ID потока
            current: Текущее количество зрителей
            peak: Пиковое количество зрителей
            drop_percent: Процент падения

        Returns:
            EvaluationResult
        """
        # Определить severity на основе процента падения
        if drop_percent >= 80:
            severity = "critical"
        elif drop_percent >= 50:
            severity = "warning"
        else:
            severity = "info"

        trigger_value = {
            "metric": "viewer_drop_rate",
            "current_value": current,
            "peak_value": peak,
            "drop_percent": drop_percent,
            "operator": "drop_gte",
        }

        context = {
            "stream_id": stream_id,
            "host": stream_id,
            "service": "stream",
            "tags": {
                "alert_type": "viewers_drop",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="viewer_count",
            severity=severity,
            trigger_value=trigger_value,
            context=context,
            reason=f"Viewer count dropped {drop_percent:.1f}% from {peak} to {current}",
            should_cooldown=False,
            consecutive_failures_met=True,
        )


# Singleton instance
_viewer_alert_integration: Optional[ViewerAlertIntegrationService] = None


def get_viewer_alert_integration() -> ViewerAlertIntegrationService:
    """Получить singleton экземпляр ViewerAlertIntegrationService."""
    global _viewer_alert_integration
    if _viewer_alert_integration is None:
        _viewer_alert_integration = ViewerAlertIntegrationService()
    return _viewer_alert_integration


async def initialize_viewer_alert_integration() -> None:
    """Инициализировать интеграцию мониторинга зрителей с алертами.

    Эта функция должна быть вызвана при старте приложения для настройки
    автоматического создания алертов при обнаружении проблем с количеством зрителей.
    """
    integration = get_viewer_alert_integration()
    integration.initialize()
    logger.info("Viewer alert integration initialized")
