"""
System Resource Alert Integration Service

Интеграционный сервис, связывающий SystemResourceMonitor с AlertTriggerService.

Обеспечивает автоматическое создание алертов при обнаружении высокого использования
системных ресурсов (CPU, memory, disk) и отправку уведомлений о восстановлении.

Функционал:
- Callback для CPU warning -> создание AlertInstance -> отправка уведомлений
- Callback для CPU critical -> создание AlertInstance -> отправка уведомлений
- Callback для memory warning -> создание AlertInstance -> отправка уведомлений
- Callback для memory critical -> создание AlertInstance -> отправка уведомлений
- Callback для disk warning -> создание AlertInstance -> отправка уведомлений
- Callback для disk critical -> создание AlertInstance -> отправка уведомлений
- Callback для восстановления -> создание resolved AlertInstance -> отправка уведомлений
- Группировка алертов для предотвращения спама
- Использование существующих AlertRule для system_resource

Использование:
    integration = SystemResourceAlertIntegrationService()
    await integration.initialize()
    # Теперь проблемы с системными ресурсами автоматически создают алерты
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
from src.services.monitors.system_resource_monitor import (
    SystemResourceMonitor,
    get_system_resource_monitor,
)
from src.models.alert import AlertRule

logger = logging.getLogger(__name__)


class SystemResourceAlertIntegrationService:
    """
    Интеграционный сервис для связывания мониторинга системных ресурсов с алертами.

    Настраивает callbacks в SystemResourceMonitor для автоматического
    создания алертов через AlertTriggerService.
    """

    def __init__(self):
        self.resource_monitor: Optional[SystemResourceMonitor] = None
        self._db_session_factory = None
        self._initialized = False

    def initialize(self) -> None:
        """Инициализировать интеграцию.

        Настраивает callbacks в SystemResourceMonitor для создания алертов.
        """
        if self._initialized:
            logger.warning("SystemResourceAlertIntegrationService already initialized")
            return

        try:
            # Создать factory для сессий БД
            engine = create_engine(settings.DATABASE_URL)
            self._db_session_factory = sessionmaker(bind=engine)

            # Получить монитор системных ресурсов
            self.resource_monitor = get_system_resource_monitor()

            # Настроить callbacks
            self.resource_monitor.on_cpu_warning_callback = self._on_cpu_warning
            self.resource_monitor.on_cpu_critical_callback = self._on_cpu_critical
            self.resource_monitor.on_memory_warning_callback = self._on_memory_warning
            self.resource_monitor.on_memory_critical_callback = self._on_memory_critical
            self.resource_monitor.on_disk_warning_callback = self._on_disk_warning
            self.resource_monitor.on_disk_critical_callback = self._on_disk_critical
            self.resource_monitor.on_recovery_callback = self._on_resource_recovery

            self._initialized = True
            logger.info("SystemResourceAlertIntegrationService initialized successfully")

        except Exception as exc:
            logger.exception(f"Failed to initialize SystemResourceAlertIntegrationService: {exc}")
            raise

    def _get_db_session(self) -> Session:
        """Получить сессию БД."""
        if not self._db_session_factory:
            raise RuntimeError("SystemResourceAlertIntegrationService not initialized")
        return self._db_session_factory()

    async def _on_cpu_warning(
        self,
        host: str,
        usage: float,
        threshold: float,
    ) -> None:
        """Callback при достижении CPU warning threshold.

        Создает алерт через AlertTriggerService.

        Args:
            host: Имя хоста
            usage: Текущее использование CPU (%)
            threshold: Порог warning (%)
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для system_resource
            rule = self._get_or_create_system_resource_rule(db)

            if not rule:
                logger.error(f"Failed to get or create system_resource rule for host {host}")
                return

            # Создать результат оценки
            evaluation_result = self._create_cpu_warning_evaluation_result(
                rule=rule,
                host=host,
                usage=usage,
                threshold=threshold,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "host": host,
                "service": "system",
                "tags": {
                    "alert_type": "cpu_warning",
                    "resource_type": "cpu",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="system_resource",
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
                logger.warning(
                    f"CPU warning alert triggered: {host}",
                    extra={
                        "host": host,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "usage": usage,
                        "threshold": threshold,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for host {host}")

        except Exception as exc:
            logger.exception(
                f"Error in cpu_warning callback for host {host}: {exc}"
            )
        finally:
            db.close()

    async def _on_cpu_critical(
        self,
        host: str,
        usage: float,
        threshold: float,
    ) -> None:
        """Callback при достижении CPU critical threshold.

        Создает алерт через AlertTriggerService.

        Args:
            host: Имя хоста
            usage: Текущее использование CPU (%)
            threshold: Порог critical (%)
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для system_resource
            rule = self._get_or_create_system_resource_rule(db)

            if not rule:
                logger.error(f"Failed to get or create system_resource rule for host {host}")
                return

            # Создать результат оценки
            evaluation_result = self._create_cpu_critical_evaluation_result(
                rule=rule,
                host=host,
                usage=usage,
                threshold=threshold,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "host": host,
                "service": "system",
                "tags": {
                    "alert_type": "cpu_critical",
                    "resource_type": "cpu",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="system_resource",
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
                logger.error(
                    f"CPU critical alert triggered: {host}",
                    extra={
                        "host": host,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "usage": usage,
                        "threshold": threshold,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for host {host}")

        except Exception as exc:
            logger.exception(
                f"Error in cpu_critical callback for host {host}: {exc}"
            )
        finally:
            db.close()

    async def _on_memory_warning(
        self,
        host: str,
        usage: float,
        threshold: float,
    ) -> None:
        """Callback при достижении memory warning threshold.

        Создает алерт через AlertTriggerService.

        Args:
            host: Имя хоста
            usage: Текущее использование памяти (%)
            threshold: Порог warning (%)
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для system_resource
            rule = self._get_or_create_system_resource_rule(db)

            if not rule:
                logger.error(f"Failed to get or create system_resource rule for host {host}")
                return

            # Создать результат оценки
            evaluation_result = self._create_memory_warning_evaluation_result(
                rule=rule,
                host=host,
                usage=usage,
                threshold=threshold,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "host": host,
                "service": "system",
                "tags": {
                    "alert_type": "memory_warning",
                    "resource_type": "memory",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="system_resource",
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
                logger.warning(
                    f"Memory warning alert triggered: {host}",
                    extra={
                        "host": host,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "usage": usage,
                        "threshold": threshold,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for host {host}")

        except Exception as exc:
            logger.exception(
                f"Error in memory_warning callback for host {host}: {exc}"
            )
        finally:
            db.close()

    async def _on_memory_critical(
        self,
        host: str,
        usage: float,
        threshold: float,
    ) -> None:
        """Callback при достижении memory critical threshold.

        Создает алерт через AlertTriggerService.

        Args:
            host: Имя хоста
            usage: Текущее использование памяти (%)
            threshold: Порог critical (%)
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для system_resource
            rule = self._get_or_create_system_resource_rule(db)

            if not rule:
                logger.error(f"Failed to get or create system_resource rule for host {host}")
                return

            # Создать результат оценки
            evaluation_result = self._create_memory_critical_evaluation_result(
                rule=rule,
                host=host,
                usage=usage,
                threshold=threshold,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "host": host,
                "service": "system",
                "tags": {
                    "alert_type": "memory_critical",
                    "resource_type": "memory",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="system_resource",
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
                logger.error(
                    f"Memory critical alert triggered: {host}",
                    extra={
                        "host": host,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "usage": usage,
                        "threshold": threshold,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for host {host}")

        except Exception as exc:
            logger.exception(
                f"Error in memory_critical callback for host {host}: {exc}"
            )
        finally:
            db.close()

    async def _on_disk_warning(
        self,
        host: str,
        usage: float,
        threshold: float,
    ) -> None:
        """Callback при достижении disk warning threshold.

        Создает алерт через AlertTriggerService.

        Args:
            host: Имя хоста
            usage: Текущее использование диска (%)
            threshold: Порог warning (%)
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для system_resource
            rule = self._get_or_create_system_resource_rule(db)

            if not rule:
                logger.error(f"Failed to get or create system_resource rule for host {host}")
                return

            # Создать результат оценки
            evaluation_result = self._create_disk_warning_evaluation_result(
                rule=rule,
                host=host,
                usage=usage,
                threshold=threshold,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "host": host,
                "service": "system",
                "tags": {
                    "alert_type": "disk_warning",
                    "resource_type": "disk",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="system_resource",
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
                logger.warning(
                    f"Disk warning alert triggered: {host}",
                    extra={
                        "host": host,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "usage": usage,
                        "threshold": threshold,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for host {host}")

        except Exception as exc:
            logger.exception(
                f"Error in disk_warning callback for host {host}: {exc}"
            )
        finally:
            db.close()

    async def _on_disk_critical(
        self,
        host: str,
        usage: float,
        threshold: float,
    ) -> None:
        """Callback при достижении disk critical threshold.

        Создает алерт через AlertTriggerService.

        Args:
            host: Имя хоста
            usage: Текущее использование диска (%)
            threshold: Порог critical (%)
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для system_resource
            rule = self._get_or_create_system_resource_rule(db)

            if not rule:
                logger.error(f"Failed to get or create system_resource rule for host {host}")
                return

            # Создать результат оценки
            evaluation_result = self._create_disk_critical_evaluation_result(
                rule=rule,
                host=host,
                usage=usage,
                threshold=threshold,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "host": host,
                "service": "system",
                "tags": {
                    "alert_type": "disk_critical",
                    "resource_type": "disk",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="system_resource",
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
                logger.error(
                    f"Disk critical alert triggered: {host}",
                    extra={
                        "host": host,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "usage": usage,
                        "threshold": threshold,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for host {host}")

        except Exception as exc:
            logger.exception(
                f"Error in disk_critical callback for host {host}: {exc}"
            )
        finally:
            db.close()

    async def _on_resource_recovery(self, host: str, resource_type: str) -> None:
        """Callback при восстановлении ресурса.

        Создает алерт восстановления через AlertTriggerService.

        Args:
            host: Имя хоста
            resource_type: Тип ресурса (cpu, memory, disk)
        """
        db = self._get_db_session()
        try:
            # Найти правило для system_resource
            rule = self._get_system_resource_rule(db)

            if not rule or not rule.notify_on_recovery:
                logger.debug(f"Recovery notifications disabled for host {host}")
                return

            # Найти активную группу для этого хоста и типа ресурса
            grouping_service = AlertGroupingService(db)
            active_groups = grouping_service.get_active_groups_for_rule(rule_id=rule.id)

            # Найти группу для этого хоста и resource_type
            group = None
            for active_group in active_groups:
                if (active_group.context and
                    active_group.context.get("host") == host and
                    active_group.context.get("tags", {}).get("resource_type") == resource_type):
                    group = active_group
                    break

            # Запустить алерт восстановления
            trigger_service = AlertTriggerService(db)
            context = {
                "host": host,
                "service": "system",
                "tags": {
                    "resource_type": resource_type,
                },
            }

            instance = trigger_service.trigger_recovery_alert(
                rule=rule,
                group_id=group.id if group else None,
                context=context,
            )

            if instance:
                logger.info(
                    f"Resource recovery alert triggered: {host} - {resource_type}",
                    extra={
                        "host": host,
                        "resource_type": resource_type,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                    },
                )

                # Разрешить группу
                if group:
                    grouping_service.resolve_group(group)

        except Exception as exc:
            logger.exception(
                f"Error in resource_recovery callback for host {host}, resource_type {resource_type}: {exc}"
            )
        finally:
            db.close()

    def _get_or_create_system_resource_rule(self, db: Session) -> Optional[AlertRule]:
        """Найти или создать правило алерта для системных ресурсов.

        Args:
            db: Сессия БД

        Returns:
            AlertRule для system_resource
        """
        # Сначала пытаемся найти существующее правило
        rule = self._get_system_resource_rule(db)

        if rule:
            return rule

        # Создать новое правило
        try:
            alert_service = AlertService(db)

            from src.schemas.alerts import AlertRuleCreate

            rule_data = AlertRuleCreate(
                name="System Resource Alert",
                description="Automatic alert triggered when system resource thresholds are exceeded",
                alert_type="system_resource",
                severity="warning",
                enabled=True,
                conditions={
                    "metric": "system_resource_usage",
                    "operator": "gte",
                    "threshold": 70.0,
                    "cpu_warning_threshold": 70.0,
                    "cpu_critical_threshold": 90.0,
                    "memory_warning_threshold": 75.0,
                    "memory_critical_threshold": 90.0,
                    "disk_warning_threshold": 80.0,
                    "disk_critical_threshold": 95.0,
                },
                notification_channels={},  # Будет заполнено администратором
                cooldown_sec=300,  # 5 минут
                notify_on_recovery=True,
                grouping_window_sec=300,  # 5 минут
            )

            rule = alert_service.create_rule(rule_data)
            logger.info(f"Created default system_resource rule: {rule.id}")
            return rule

        except Exception as exc:
            logger.exception(f"Failed to create system_resource rule: {exc}")
            return None

    def _get_system_resource_rule(self, db: Session) -> Optional[AlertRule]:
        """Найти правило алерта для системных ресурсов.

        Args:
            db: Сессия БД

        Returns:
            AlertRule для system_resource или None
        """
        try:
            from src.models.alert import AlertRule

            rule = (
                db.query(AlertRule)
                .filter(
                    AlertRule.alert_type == "system_resource",
                    AlertRule.enabled == True,
                )
                .order_by(AlertRule.created_at.desc())
                .first()
            )

            return rule

        except Exception as exc:
            logger.exception(f"Failed to query system_resource rule: {exc}")
            return None

    def _create_cpu_warning_evaluation_result(
        self,
        rule: AlertRule,
        host: str,
        usage: float,
        threshold: float,
    ) -> EvaluationResult:
        """Создать результат оценки для CPU warning.

        Args:
            rule: Правило алерта
            host: Имя хоста
            usage: Текущее использование CPU (%)
            threshold: Порог warning (%)

        Returns:
            EvaluationResult
        """
        trigger_value = {
            "metric": "cpu_usage",
            "current_value": usage,
            "threshold": threshold,
            "operator": "gte",
            "resource_type": "cpu",
        }

        context = {
            "host": host,
            "service": "system",
            "tags": {
                "alert_type": "cpu_warning",
                "resource_type": "cpu",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="system_resource",
            severity="warning",
            trigger_value=trigger_value,
            context=context,
            reason=f"CPU usage at {usage:.1f}% (warning threshold: {threshold:.1f}%)",
            should_cooldown=False,
            consecutive_failures_met=True,
        )

    def _create_cpu_critical_evaluation_result(
        self,
        rule: AlertRule,
        host: str,
        usage: float,
        threshold: float,
    ) -> EvaluationResult:
        """Создать результат оценки для CPU critical.

        Args:
            rule: Правило алерта
            host: Имя хоста
            usage: Текущее использование CPU (%)
            threshold: Порог critical (%)

        Returns:
            EvaluationResult
        """
        trigger_value = {
            "metric": "cpu_usage",
            "current_value": usage,
            "threshold": threshold,
            "operator": "gte",
            "resource_type": "cpu",
        }

        context = {
            "host": host,
            "service": "system",
            "tags": {
                "alert_type": "cpu_critical",
                "resource_type": "cpu",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="system_resource",
            severity="critical",
            trigger_value=trigger_value,
            context=context,
            reason=f"CPU usage at {usage:.1f}% - CRITICAL (threshold: {threshold:.1f}%)",
            should_cooldown=False,
            consecutive_failures_met=True,
        )

    def _create_memory_warning_evaluation_result(
        self,
        rule: AlertRule,
        host: str,
        usage: float,
        threshold: float,
    ) -> EvaluationResult:
        """Создать результат оценки для memory warning.

        Args:
            rule: Правило алерта
            host: Имя хоста
            usage: Текущее использование памяти (%)
            threshold: Порог warning (%)

        Returns:
            EvaluationResult
        """
        trigger_value = {
            "metric": "memory_usage",
            "current_value": usage,
            "threshold": threshold,
            "operator": "gte",
            "resource_type": "memory",
        }

        context = {
            "host": host,
            "service": "system",
            "tags": {
                "alert_type": "memory_warning",
                "resource_type": "memory",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="system_resource",
            severity="warning",
            trigger_value=trigger_value,
            context=context,
            reason=f"Memory usage at {usage:.1f}% (warning threshold: {threshold:.1f}%)",
            should_cooldown=False,
            consecutive_failures_met=True,
        )

    def _create_memory_critical_evaluation_result(
        self,
        rule: AlertRule,
        host: str,
        usage: float,
        threshold: float,
    ) -> EvaluationResult:
        """Создать результат оценки для memory critical.

        Args:
            rule: Правило алерта
            host: Имя хоста
            usage: Текущее использование памяти (%)
            threshold: Порог critical (%)

        Returns:
            EvaluationResult
        """
        trigger_value = {
            "metric": "memory_usage",
            "current_value": usage,
            "threshold": threshold,
            "operator": "gte",
            "resource_type": "memory",
        }

        context = {
            "host": host,
            "service": "system",
            "tags": {
                "alert_type": "memory_critical",
                "resource_type": "memory",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="system_resource",
            severity="critical",
            trigger_value=trigger_value,
            context=context,
            reason=f"Memory usage at {usage:.1f}% - CRITICAL (threshold: {threshold:.1f}%)",
            should_cooldown=False,
            consecutive_failures_met=True,
        )

    def _create_disk_warning_evaluation_result(
        self,
        rule: AlertRule,
        host: str,
        usage: float,
        threshold: float,
    ) -> EvaluationResult:
        """Создать результат оценки для disk warning.

        Args:
            rule: Правило алерта
            host: Имя хоста
            usage: Текущее использование диска (%)
            threshold: Порог warning (%)

        Returns:
            EvaluationResult
        """
        trigger_value = {
            "metric": "disk_usage",
            "current_value": usage,
            "threshold": threshold,
            "operator": "gte",
            "resource_type": "disk",
        }

        context = {
            "host": host,
            "service": "system",
            "tags": {
                "alert_type": "disk_warning",
                "resource_type": "disk",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="system_resource",
            severity="warning",
            trigger_value=trigger_value,
            context=context,
            reason=f"Disk usage at {usage:.1f}% (warning threshold: {threshold:.1f}%)",
            should_cooldown=False,
            consecutive_failures_met=True,
        )

    def _create_disk_critical_evaluation_result(
        self,
        rule: AlertRule,
        host: str,
        usage: float,
        threshold: float,
    ) -> EvaluationResult:
        """Создать результат оценки для disk critical.

        Args:
            rule: Правило алерта
            host: Имя хоста
            usage: Текущее использование диска (%)
            threshold: Порог critical (%)

        Returns:
            EvaluationResult
        """
        trigger_value = {
            "metric": "disk_usage",
            "current_value": usage,
            "threshold": threshold,
            "operator": "gte",
            "resource_type": "disk",
        }

        context = {
            "host": host,
            "service": "system",
            "tags": {
                "alert_type": "disk_critical",
                "resource_type": "disk",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="system_resource",
            severity="critical",
            trigger_value=trigger_value,
            context=context,
            reason=f"Disk usage at {usage:.1f}% - CRITICAL (threshold: {threshold:.1f}%)",
            should_cooldown=False,
            consecutive_failures_met=True,
        )


# Singleton instance
_system_resource_alert_integration: Optional[SystemResourceAlertIntegrationService] = None


def get_system_resource_alert_integration() -> SystemResourceAlertIntegrationService:
    """Получить singleton экземпляр SystemResourceAlertIntegrationService."""
    global _system_resource_alert_integration
    if _system_resource_alert_integration is None:
        _system_resource_alert_integration = SystemResourceAlertIntegrationService()
    return _system_resource_alert_integration


async def initialize_system_resource_alert_integration() -> None:
    """Инициализировать интеграцию мониторинга системных ресурсов с алертами.

    Эта функция должна быть вызвана при старте приложения для настройки
    автоматического создания алертов при обнаружении проблем с системными ресурсами.
    """
    integration = get_system_resource_alert_integration()
    integration.initialize()
    logger.info("System resource alert integration initialized")
