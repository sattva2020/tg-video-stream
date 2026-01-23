"""
API Rate Limit Alert Integration Service

Интеграционный сервис, связывающий ApiRateLimitMonitor с AlertTriggerService.

Обеспечивает автоматическое создание алертов при обнаружении приближения к rate limit,
достижении критического уровня, или получении 429 (rate limited), а также отправку
уведомлений о восстановлении.

Функционал:
- Callback для предупреждения о приближении к лимиту -> создание AlertInstance -> отправка уведомлений
- Callback для критического уровня -> создание AlertInstance -> отправка уведомлений
- Callback для получения 429 -> создание AlertInstance -> отправка уведомлений
- Callback для восстановления -> создание resolved AlertInstance -> отправка уведомлений
- Группировка алертов для предотвращения спама
- Использование существующих AlertRule для api_rate_limit

Использование:
    integration = ApiRateLimitAlertIntegrationService()
    await integration.initialize()
    # Теперь проблемы с rate limits автоматически создают алерты
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
from src.services.monitors.api_rate_limit_monitor import (
    ApiRateLimitMonitor,
    get_api_rate_limit_monitor,
)
from src.models.alert import AlertRule

logger = logging.getLogger(__name__)


class ApiRateLimitAlertIntegrationService:
    """
    Интеграционный сервис для связывания мониторинга API rate limits с алертами.

    Настраивает callbacks в ApiRateLimitMonitor для автоматического
    создания алертов через AlertTriggerService.
    """

    def __init__(self):
        self.rate_limit_monitor: Optional[ApiRateLimitMonitor] = None
        self._db_session_factory = None
        self._initialized = False

    def initialize(self) -> None:
        """Инициализировать интеграцию.

        Настраивает callbacks в ApiRateLimitMonitor для создания алертов.
        """
        if self._initialized:
            logger.warning("ApiRateLimitAlertIntegrationService already initialized")
            return

        try:
            # Создать factory для сессий БД
            engine = create_engine(settings.DATABASE_URL)
            self._db_session_factory = sessionmaker(bind=engine)

            # Получить монитор rate limits
            self.rate_limit_monitor = get_api_rate_limit_monitor()

            # Настроить callbacks
            self.rate_limit_monitor.on_warning_callback = self._on_warning_threshold
            self.rate_limit_monitor.on_critical_callback = self._on_critical_threshold
            self.rate_limit_monitor.on_rate_limited_callback = self._on_rate_limited
            self.rate_limit_monitor.on_recovery_callback = self._on_rate_limit_recovery

            self._initialized = True
            logger.info("ApiRateLimitAlertIntegrationService initialized successfully")

        except Exception as exc:
            logger.exception(f"Failed to initialize ApiRateLimitAlertIntegrationService: {exc}")
            raise

    def _get_db_session(self) -> Session:
        """Получить сессию БД."""
        if not self._db_session_factory:
            raise RuntimeError("ApiRateLimitAlertIntegrationService not initialized")
        return self._db_session_factory()

    async def _on_warning_threshold(
        self,
        endpoint: str,
        usage_percent: float,
        remaining: int,
        limit: int,
    ) -> None:
        """Callback при достижении warning threshold.

        Создает алерт через AlertTriggerService.

        Args:
            endpoint: API endpoint
            usage_percent: Процент использования
            remaining: Оставшееся количество запросов
            limit: Лимит запросов
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для api_rate_limit
            rule = self._get_or_create_rate_limit_rule(db)

            if not rule:
                logger.error(f"Failed to get or create api_rate_limit rule for endpoint {endpoint}")
                return

            # Создать результат оценки
            evaluation_result = self._create_warning_evaluation_result(
                rule=rule,
                endpoint=endpoint,
                usage_percent=usage_percent,
                remaining=remaining,
                limit=limit,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "endpoint": endpoint,
                "host": endpoint,
                "service": "api",
                "tags": {
                    "alert_type": "rate_limit_warning",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="api_rate_limit",
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
                    f"Rate limit warning alert triggered: {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "usage_percent": usage_percent,
                        "remaining": remaining,
                        "limit": limit,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for endpoint {endpoint}")

        except Exception as exc:
            logger.exception(
                f"Error in warning_threshold callback for endpoint {endpoint}: {exc}"
            )
        finally:
            db.close()

    async def _on_critical_threshold(
        self,
        endpoint: str,
        usage_percent: float,
        remaining: int,
        limit: int,
    ) -> None:
        """Callback при достижении critical threshold.

        Создает алерт через AlertTriggerService.

        Args:
            endpoint: API endpoint
            usage_percent: Процент использования
            remaining: Оставшееся количество запросов
            limit: Лимит запросов
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для api_rate_limit
            rule = self._get_or_create_rate_limit_rule(db)

            if not rule:
                logger.error(f"Failed to get or create api_rate_limit rule for endpoint {endpoint}")
                return

            # Создать результат оценки
            evaluation_result = self._create_critical_evaluation_result(
                rule=rule,
                endpoint=endpoint,
                usage_percent=usage_percent,
                remaining=remaining,
                limit=limit,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "endpoint": endpoint,
                "host": endpoint,
                "service": "api",
                "tags": {
                    "alert_type": "rate_limit_critical",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="api_rate_limit",
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
                    f"Rate limit critical alert triggered: {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "usage_percent": usage_percent,
                        "remaining": remaining,
                        "limit": limit,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for endpoint {endpoint}")

        except Exception as exc:
            logger.exception(
                f"Error in critical_threshold callback for endpoint {endpoint}: {exc}"
            )
        finally:
            db.close()

    async def _on_rate_limited(
        self,
        endpoint: str,
        retry_after: Optional[int],
        reset_time: Optional[datetime],
    ) -> None:
        """Callback при получении 429 (rate limited).

        Создает алерт через AlertTriggerService.

        Args:
            endpoint: API endpoint
            retry_after: Количество секунд до восстановления
            reset_time: Время сброса лимита
        """
        db = self._get_db_session()
        try:
            # Найти или создать правило для api_rate_limit
            rule = self._get_or_create_rate_limit_rule(db)

            if not rule:
                logger.error(f"Failed to get or create api_rate_limit rule for endpoint {endpoint}")
                return

            # Создать результат оценки
            evaluation_result = self._create_rate_limited_evaluation_result(
                rule=rule,
                endpoint=endpoint,
                retry_after=retry_after,
                reset_time=reset_time,
            )

            # Найти или создать группу алертов
            grouping_service = AlertGroupingService(db)
            context = {
                "endpoint": endpoint,
                "host": endpoint,
                "service": "api",
                "tags": {
                    "alert_type": "rate_limited",
                },
            }

            group, created = grouping_service.find_or_create_group(
                rule=rule,
                context=context,
                alert_type="api_rate_limit",
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
                    f"Rate limited alert triggered: {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                        "retry_after": retry_after,
                        "reset_time": reset_time.isoformat() if reset_time else None,
                    },
                )
            else:
                logger.error(f"Failed to trigger alert for endpoint {endpoint}")

        except Exception as exc:
            logger.exception(
                f"Error in rate_limited callback for endpoint {endpoint}: {exc}"
            )
        finally:
            db.close()

    async def _on_rate_limit_recovery(self, endpoint: str) -> None:
        """Callback при восстановлении rate limit.

        Создает алерт восстановления через AlertTriggerService.

        Args:
            endpoint: API endpoint
        """
        db = self._get_db_session()
        try:
            # Найти правило для api_rate_limit
            rule = self._get_rate_limit_rule(db)

            if not rule or not rule.notify_on_recovery:
                logger.debug(f"Recovery notifications disabled for endpoint {endpoint}")
                return

            # Найти активную группу для этого endpoint
            grouping_service = AlertGroupingService(db)
            active_groups = grouping_service.get_active_groups_for_rule(rule_id=rule.id)

            # Найти группу для этого endpoint
            group = None
            for active_group in active_groups:
                if active_group.context and active_group.context.get("endpoint") == endpoint:
                    group = active_group
                    break

            # Запустить алерт восстановления
            trigger_service = AlertTriggerService(db)
            context = {
                "endpoint": endpoint,
                "host": endpoint,
                "service": "api",
            }

            instance = trigger_service.trigger_recovery_alert(
                rule=rule,
                group_id=group.id if group else None,
                context=context,
            )

            if instance:
                logger.info(
                    f"Rate limit recovery alert triggered: {endpoint}",
                    extra={
                        "endpoint": endpoint,
                        "instance_id": str(instance.id),
                        "group_id": str(group.id) if group else None,
                    },
                )

                # Разрешить группу
                if group:
                    grouping_service.resolve_group(group)

        except Exception as exc:
            logger.exception(
                f"Error in rate_limit_recovery callback for endpoint {endpoint}: {exc}"
            )
        finally:
            db.close()

    def _get_or_create_rate_limit_rule(self, db: Session) -> Optional[AlertRule]:
        """Найти или создать правило алерта для API rate limits.

        Args:
            db: Сессия БД

        Returns:
            AlertRule для api_rate_limit
        """
        # Сначала пытаемся найти существующее правило
        rule = self._get_rate_limit_rule(db)

        if rule:
            return rule

        # Создать новое правило
        try:
            alert_service = AlertService(db)

            from src.schemas.alerts import AlertRuleCreate

            rule_data = AlertRuleCreate(
                name="API Rate Limit Alert",
                description="Automatic alert triggered when API rate limit thresholds are approached or exceeded",
                alert_type="api_rate_limit",
                severity="warning",
                enabled=True,
                conditions={
                    "metric": "api_rate_limit_usage",
                    "operator": "gte",
                    "threshold": 80.0,
                    "critical_threshold": 95.0,
                },
                notification_channels={},  # Будет заполнено администратором
                cooldown_sec=300,  # 5 минут
                notify_on_recovery=True,
                grouping_window_sec=300,  # 5 минут
            )

            rule = alert_service.create_rule(rule_data)
            logger.info(f"Created default api_rate_limit rule: {rule.id}")
            return rule

        except Exception as exc:
            logger.exception(f"Failed to create api_rate_limit rule: {exc}")
            return None

    def _get_rate_limit_rule(self, db: Session) -> Optional[AlertRule]:
        """Найти правило алерта для API rate limits.

        Args:
            db: Сессия БД

        Returns:
            AlertRule для api_rate_limit или None
        """
        try:
            from src.models.alert import AlertRule

            rule = (
                db.query(AlertRule)
                .filter(
                    AlertRule.alert_type == "api_rate_limit",
                    AlertRule.enabled == True,
                )
                .order_by(AlertRule.created_at.desc())
                .first()
            )

            return rule

        except Exception as exc:
            logger.exception(f"Failed to query api_rate_limit rule: {exc}")
            return None

    def _create_warning_evaluation_result(
        self,
        rule: AlertRule,
        endpoint: str,
        usage_percent: float,
        remaining: int,
        limit: int,
    ) -> EvaluationResult:
        """Создать результат оценки для warning threshold.

        Args:
            rule: Правило алерта
            endpoint: API endpoint
            usage_percent: Процент использования
            remaining: Оставшееся количество запросов
            limit: Лимит запросов

        Returns:
            EvaluationResult
        """
        trigger_value = {
            "metric": "api_rate_limit_usage",
            "current_value": usage_percent,
            "threshold": 80.0,
            "operator": "gte",
            "remaining": remaining,
            "limit": limit,
        }

        context = {
            "endpoint": endpoint,
            "host": endpoint,
            "service": "api",
            "tags": {
                "alert_type": "rate_limit_warning",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="api_rate_limit",
            severity="warning",
            trigger_value=trigger_value,
            context=context,
            reason=f"API rate limit usage at {usage_percent:.1f}% ({remaining}/{limit} remaining)",
            should_cooldown=False,
            consecutive_failures_met=True,
        )

    def _create_critical_evaluation_result(
        self,
        rule: AlertRule,
        endpoint: str,
        usage_percent: float,
        remaining: int,
        limit: int,
    ) -> EvaluationResult:
        """Создать результат оценки для critical threshold.

        Args:
            rule: Правило алерта
            endpoint: API endpoint
            usage_percent: Процент использования
            remaining: Оставшееся количество запросов
            limit: Лимит запросов

        Returns:
            EvaluationResult
        """
        trigger_value = {
            "metric": "api_rate_limit_usage",
            "current_value": usage_percent,
            "threshold": 95.0,
            "operator": "gte",
            "remaining": remaining,
            "limit": limit,
        }

        context = {
            "endpoint": endpoint,
            "host": endpoint,
            "service": "api",
            "tags": {
                "alert_type": "rate_limit_critical",
            },
        }

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="api_rate_limit",
            severity="critical",
            trigger_value=trigger_value,
            context=context,
            reason=f"API rate limit usage at {usage_percent:.1f}% - CRITICAL ({remaining}/{limit} remaining)",
            should_cooldown=False,
            consecutive_failures_met=True,
        )

    def _create_rate_limited_evaluation_result(
        self,
        rule: AlertRule,
        endpoint: str,
        retry_after: Optional[int],
        reset_time: Optional[datetime],
    ) -> EvaluationResult:
        """Создать результат оценки для получения 429.

        Args:
            rule: Правило алерта
            endpoint: API endpoint
            retry_after: Количество секунд до восстановления
            reset_time: Время сброса лимита

        Returns:
            EvaluationResult
        """
        trigger_value = {
            "metric": "api_rate_limit_status",
            "current_value": "rate_limited",
            "operator": "eq",
            "retry_after": retry_after,
            "reset_time": reset_time.isoformat() if reset_time else None,
        }

        context = {
            "endpoint": endpoint,
            "host": endpoint,
            "service": "api",
            "tags": {
                "alert_type": "rate_limited",
            },
        }

        reason = f"API rate limit exceeded for {endpoint}"
        if retry_after:
            reason += f" - retry after {retry_after}s"
        if reset_time:
            reason += f" - reset at {reset_time.isoformat()}"

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type="api_rate_limit",
            severity="critical",
            trigger_value=trigger_value,
            context=context,
            reason=reason,
            should_cooldown=False,
            consecutive_failures_met=True,
        )


# Singleton instance
_api_rate_limit_alert_integration: Optional[ApiRateLimitAlertIntegrationService] = None


def get_api_rate_limit_alert_integration() -> ApiRateLimitAlertIntegrationService:
    """Получить singleton экземпляр ApiRateLimitAlertIntegrationService."""
    global _api_rate_limit_alert_integration
    if _api_rate_limit_alert_integration is None:
        _api_rate_limit_alert_integration = ApiRateLimitAlertIntegrationService()
    return _api_rate_limit_alert_integration


async def initialize_api_rate_limit_alert_integration() -> None:
    """Инициализировать интеграцию мониторинга API rate limits с алертами.

    Эта функция должна быть вызвана при старте приложения для настройки
    автоматического создания алертов при обнаружении проблем с rate limits.
    """
    integration = get_api_rate_limit_alert_integration()
    integration.initialize()
    logger.info("API rate limit alert integration initialized")
