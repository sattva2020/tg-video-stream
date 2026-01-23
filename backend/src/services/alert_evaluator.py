"""Сервис оценки условий алертов для проверки триггеров."""
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.alert import AlertRule, AlertInstance

logger = logging.getLogger(__name__)


@dataclass
class EvaluationContext:
    """Контекст оценки алерта с метаданными."""
    metric_value: Any
    timestamp: datetime
    host: Optional[str] = None
    service: Optional[str] = None
    tags: Optional[Dict] = None
    additional_context: Optional[Dict] = None


@dataclass
class EvaluationResult:
    """Результат оценки условия алерта."""
    triggered: bool
    rule_id: UUID
    rule_name: str
    alert_type: str
    severity: str
    trigger_value: Dict
    context: Dict
    reason: Optional[str] = None
    should_cooldown: bool = False
    consecutive_failures_met: bool = False


class AlertEvaluator:
    """Оценка условий алертов и проверка триггеров.

    Проверяет условия правил алертов по метрикам, применяет операторы сравнения,
    отслеживает последовательные срабатывания и периоды коолдауна.
    """

    # Операторы сравнения
    OPERATORS = {
        "lt": lambda a, b: a < b,
        "lte": lambda a, b: a <= b,
        "gt": lambda a, b: a > b,
        "gte": lambda a, b: a >= b,
        "eq": lambda a, b: a == b,
        "ne": lambda a, b: a != b,
        "in": lambda a, b: a in b if isinstance(b, (list, tuple, set)) else False,
        "not_in": lambda a, b: a not in b if isinstance(b, (list, tuple, set)) else True,
        "contains": lambda a, b: b in a if isinstance(a, (str, list, tuple, dict)) else False,
        "not_contains": lambda a, b: b not in a if isinstance(a, (str, list, tuple, dict)) else True,
        "is_null": lambda a, b: a is None,
        "is_not_null": lambda a, b: a is not None,
        "regex": lambda a, b: bool(re.match(b, a)) if isinstance(a, str) and isinstance(b, str) else False,
    }

    def __init__(self, db: Session):
        self.db = db

    def evaluate_rule(
        self,
        rule: AlertRule,
        context: EvaluationContext,
    ) -> Optional[EvaluationResult]:
        """Оценить правило алерта по контексту.

        Args:
            rule: Правило алерта для оценки
            context: Контекст с метриками и метаданными

        Returns:
            EvaluationResult или None если правило не применимо
        """
        # Проверка что правило включено
        if not rule.enabled:
            logger.debug("Rule is disabled", extra={"rule_id": str(rule.id), "rule_name": rule.name})
            return None

        # Проверка периода коолдауна
        if self._is_in_cooldown(rule):
            logger.debug("Rule is in cooldown", extra={"rule_id": str(rule.id), "rule_name": rule.name})
            return None

        # Проверка окон активности и тишины
        if not self._is_within_active_window(rule):
            logger.debug("Rule is outside active window", extra={"rule_id": str(rule.id)})
            return None

        if self._is_in_silence_window(rule):
            logger.debug("Rule is in silence window", extra={"rule_id": str(rule.id)})
            return None

        # Проверка rate limiting
        if self._is_rate_limited(rule):
            logger.debug("Rule is rate limited", extra={"rule_id": str(rule.id)})
            return None

        # Оценка условий
        conditions = rule.conditions
        triggered, reason = self._evaluate_conditions(conditions, context)

        if not triggered:
            return None

        # Проверка последовательных срабатываний
        consecutive_failures_met = self._check_consecutive_failures(rule, context)

        # Формирование результата
        trigger_value = {
            "metric": conditions.get("metric", "unknown"),
            "current_value": context.metric_value,
            "threshold": conditions.get("threshold"),
            "operator": conditions.get("operator", "eq"),
        }

        result_context = {
            "host": context.host,
            "service": context.service,
            "tags": context.tags or {},
        }
        if context.additional_context:
            result_context.update(context.additional_context)

        return EvaluationResult(
            triggered=True,
            rule_id=rule.id,
            rule_name=rule.name,
            alert_type=rule.alert_type,
            severity=rule.severity,
            trigger_value=trigger_value,
            context=result_context,
            reason=reason,
            should_cooldown=False,
            consecutive_failures_met=consecutive_failures_met,
        )

    def _evaluate_conditions(
        self,
        conditions: Dict,
        context: EvaluationContext,
    ) -> tuple[bool, Optional[str]]:
        """Оценить условия по контексту.

        Args:
            conditions: Словарь с условиями из AlertRule
            context: Контекст оценки

        Returns:
            (triggered: bool, reason: Optional[str])
        """
        metric_name = conditions.get("metric")
        if not metric_name:
            return False, "No metric specified in conditions"

        # Значение метрики из контекста
        if metric_name == "value" or metric_name == "metric_value":
            value = context.metric_value
        else:
            # Попытка получить вложенное значение
            value = self._get_nested_value(context.metric_value, metric_name)
            if value is None and context.additional_context:
                value = self._get_nested_value(context.additional_context, metric_name)

        operator = conditions.get("operator", "eq")
        threshold = conditions.get("threshold")

        # Применение оператора
        triggered = self._apply_operator(value, operator, threshold)

        if triggered:
            reason = f"Metric '{metric_name}' with value '{value}' {operator} '{threshold}'"
        else:
            reason = None

        return triggered, reason

    def _apply_operator(self, value: Any, operator: str, threshold: Any) -> bool:
        """Применить оператор сравнения.

        Args:
            value: Текущее значение
            operator: Оператор из AlertEvaluator.OPERATORS
            threshold: Пороговое значение

        Returns:
            bool: Результат сравнения
        """
        operator_func = self.OPERATORS.get(operator)
        if not operator_func:
            logger.warning("Unknown operator", extra={"operator": operator})
            return False

        try:
            return operator_func(value, threshold)
        except Exception as e:
            logger.error("Operator evaluation failed", extra={"operator": operator, "error": str(e)})
            return False

    def _get_nested_value(self, data: Any, path: str) -> Any:
        """Получить вложенное значение по пути (например, 'cpu.usage')."""
        if not isinstance(data, dict):
            return None

        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value

    def _is_in_cooldown(self, rule: AlertRule) -> bool:
        """Проверить, находится ли правило в периоде коолдауна."""
        if not rule.last_triggered_at:
            return False

        cooldown_end = rule.last_triggered_at + timedelta(seconds=rule.cooldown_sec)
        return datetime.utcnow() < cooldown_end

    def _check_consecutive_failures(self, rule: AlertRule, context: EvaluationContext) -> bool:
        """Проверить условие на последовательные срабатывания.

        Args:
            rule: Правило алерта
            context: Контекст оценки

        Returns:
            bool: True если условие выполнено
        """
        conditions = rule.conditions
        required_consecutive = conditions.get("consecutive_failures", 1)

        if required_consecutive <= 1:
            return True

        # Проверка текущего счетчика
        current_consecutive = rule.consecutive_triggers
        return current_consecutive >= required_consecutive

    def _is_within_active_window(self, rule: AlertRule) -> bool:
        """Проверить, находимся ли мы в окне активности правила."""
        if not rule.active_windows:
            return True

        now = datetime.utcnow()
        current_time = now.time()
        current_weekday = now.weekday()

        windows = rule.active_windows
        if not isinstance(windows, dict):
            return True

        # Проверка дней недели
        allowed_days = windows.get("days_of_week")  # 0=Monday, 6=Sunday
        if allowed_days is not None:
            if isinstance(allowed_days, list):
                if current_weekday not in allowed_days:
                    return False

        # Проверка времени
        time_ranges = windows.get("time_ranges")
        if time_ranges and isinstance(time_ranges, list):
            for time_range in time_ranges:
                start_str = time_range.get("start")
                end_str = time_range.get("end")

                if start_str and end_str:
                    try:
                        start = datetime.strptime(start_str, "%H:%M").time()
                        end = datetime.strptime(end_str, "%H:%M").time()

                        if start <= current_time <= end:
                            return True
                    except ValueError:
                        logger.warning("Invalid time format in active_windows")
            return False

        return True

    def _is_in_silence_window(self, rule: AlertRule) -> bool:
        """Проверить, находимся ли мы в окне тишины (maintenance window)."""
        if not rule.silence_windows:
            return False

        now = datetime.utcnow()
        current_time = now.time()
        current_weekday = now.weekday()

        windows = rule.silence_windows
        if not isinstance(windows, dict):
            return False

        # Проверка дней недели
        silence_days = windows.get("days_of_week")
        if silence_days is not None:
            if isinstance(silence_days, list):
                if current_weekday in silence_days:
                    return True

        # Проверка времени
        time_ranges = windows.get("time_ranges")
        if time_ranges and isinstance(time_ranges, list):
            for time_range in time_ranges:
                start_str = time_range.get("start")
                end_str = time_range.get("end")

                if start_str and end_str:
                    try:
                        start = datetime.strptime(start_str, "%H:%M").time()
                        end = datetime.strptime(end_str, "%H:%M").time()

                        if start <= current_time <= end:
                            return True
                    except ValueError:
                        logger.warning("Invalid time format in silence_windows")

        return False

    def _is_rate_limited(self, rule: AlertRule) -> bool:
        """Проверить rate limiting для правила."""
        if not rule.rate_limit_minutes or not rule.rate_limit_count:
            return False

        # Подсчет алертов за последние N минут
        time_threshold = datetime.utcnow() - timedelta(minutes=rule.rate_limit_minutes)

        recent_count = (
            self.db.execute(
                select(AlertInstance.id)
                .where(
                    AlertInstance.rule_id == rule.id,
                    AlertInstance.fired_at >= time_threshold,
                )
            )
            .scalars()
            .all()
        )

        return len(recent_count) >= rule.rate_limit_count

    def get_rules_for_evaluation(
        self,
        alert_type: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[AlertRule]:
        """Получить правила для оценки.

        Args:
            alert_type: Опциональный фильтр по типу алерта
            enabled_only: Только включенные правила

        Returns:
            List[AlertRule]: Список правил для оценки
        """
        query = self.db.query(AlertRule)

        if enabled_only:
            query = query.filter(AlertRule.enabled == True)

        if alert_type:
            query = query.filter(AlertRule.alert_type == alert_type)

        return query.all()
