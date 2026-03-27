"""
Сервис группировки алертов для предотвращения спама уведомлений.

Группирует связанные алерты (например, одинаковые правила firing на одном хосте)
и отправляет уведомления только для первого алерта в группе или при изменении статуса.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.alert import AlertGroup, AlertInstance, AlertRule
from src.schemas.alerts import AlertGroupCreate, AlertGroupUpdate
from src.services.alert_service import AlertService

logger = logging.getLogger(__name__)


class AlertGroupingService:
    """Сервис группировки алертов для предотвращения спама уведомлений.

    Обеспечивает умную группировку алертов на основе:
    - Правила алерта (rule_id)
    - Контекста (host, service, tags)
    - Времени (alert_grouping_window_sec)

    Группировка позволяет отправлять одно уведомление для серии связанных алертов
    вместо спама уведомлениями для каждого отдельного события.
    """

    # Временное окно группировки по умолчанию (5 минут)
    DEFAULT_GROUPING_WINDOW_SEC = 300

    def __init__(self, db: Session):
        self.db = db
        self.alert_service = AlertService(db)

    def find_or_create_group(
        self,
        rule: AlertRule,
        context: Dict,
        alert_type: str,
        severity: str,
        grouping_window_sec: Optional[int] = None,
    ) -> Tuple[Optional[AlertGroup], bool]:
        """Найти или создать группу для алерта.

        Args:
            rule: Правило алерта
            context: Контекст алерта (host, service, tags, etc.)
            alert_type: Тип алерта
            severity: Важность алерта
            grouping_window_sec: Окно группировки в секундах

        Returns:
            (AlertGroup, created: bool) - группа и флаг создания
        """
        group_key = self._generate_group_key(rule, context)
        grouping_window = grouping_window_sec or self.DEFAULT_GROUPING_WINDOW_SEC

        # Поиск активной группы в пределах временного окна
        existing_group = self._find_active_group(
            rule_id=rule.id,
            group_key=group_key,
            window_sec=grouping_window,
        )

        if existing_group:
            logger.debug(
                f"Found existing group for alert",
                extra={
                    "rule_id": str(rule.id),
                    "group_id": str(existing_group.id),
                    "group_key": group_key,
                },
            )
            return existing_group, False

        # Создание новой группы
        group_name = self._generate_group_name(rule, context)
        group_data = AlertGroupCreate(
            rule_id=rule.id,
            group_key=group_key,
            name=group_name,
            status="active",
            severity=severity,
            context=context,
        )

        group = self.alert_service.create_group(group_data)

        logger.info(
            f"Created new alert group",
            extra={
                "group_id": str(group.id),
                "rule_id": str(rule.id),
                "group_key": group_key,
                "alert_type": alert_type,
            },
        )

        return group, True

    def add_alert_to_group(
        self,
        instance: AlertInstance,
        group: AlertGroup,
        send_notification: bool = True,
    ) -> AlertGroup:
        """Добавить алерт в группу и обновить метаданные группы.

        Args:
            instance: Экземпляр алерта
            group: Группа алертов
            send_notification: Отправлять ли уведомление

        Returns:
            Обновленная группа
        """
        # Привязка экземпляра к группе
        instance.group_id = group.id

        # Обновление счетчиков группы
        group.alert_count += 1
        group.last_alert_at = datetime.utcnow()

        # Обновление важности при эскалации
        if self._should_escalate_severity(group.severity, instance.severity):
            group.severity = instance.severity

        self.db.commit()
        self.db.refresh(group)

        logger.debug(
            f"Added alert to group",
            extra={
                "group_id": str(group.id),
                "instance_id": str(instance.id),
                "alert_count": group.alert_count,
            },
        )

        return group

    def should_send_notification(
        self,
        group: AlertGroup,
        is_new_group: bool,
        notification_interval_sec: Optional[int] = None,
    ) -> bool:
        """Определить, нужно ли отправлять уведомление для группы.

        Уведомление отправляется если:
        - Группа новая (первый алерт)
        - Прошел интервал с последнего уведомления
        - Изменилась важность (эскалация)

        Args:
            group: Группа алертов
            is_new_group: Новая ли группа
            notification_interval_sec: Интервал между уведомлениями

        Returns:
            bool: True если нужно отправить уведомление
        """
        # Всегда отправляем для новой группы
        if is_new_group:
            return True

        # Если уведомление еще не отправлялось
        if not group.notification_sent:
            return True

        # Проверка эскалации важности
        # Если группа имеет уведомление и важность изменилась, отправляем
        if group.last_notification_at:
            # Получаем первую важность из контекста или текущую
            # Эскалация: warning -> critical
            if self._has_severity_escalated(group):
                return True

        # Проверка интервала уведомлений
        if notification_interval_sec and group.last_notification_at:
            next_notification_time = group.last_notification_at + timedelta(seconds=notification_interval_sec)
            if datetime.utcnow() >= next_notification_time:
                return True

        return False

    def mark_notification_sent(self, group: AlertGroup) -> AlertGroup:
        """Отметить что уведомление для группы отправлено.

        Args:
            group: Группа алертов

        Returns:
            Обновленная группа
        """
        group.notification_sent = True
        group.last_notification_at = datetime.utcnow()
        group.notification_count += 1

        self.db.commit()
        self.db.refresh(group)

        logger.debug(
            f"Marked notification as sent for group",
            extra={
                "group_id": str(group.id),
                "notification_count": group.notification_count,
            },
        )

        return group

    def resolve_group(
        self,
        group: AlertGroup,
        resolved_by: Optional[UUID] = None,
    ) -> AlertGroup:
        """Разрешить группу алертов.

        Args:
            group: Группа алертов
            resolved_by: ID пользователя, разрешившего группу

        Returns:
            Обновленная группа
        """
        group.status = "resolved"
        group.resolved_at = datetime.utcnow()
        group.resolved_by = resolved_by

        self.db.commit()
        self.db.refresh(group)

        logger.info(
            f"Resolved alert group",
            extra={
                "group_id": str(group.id),
                "resolved_by": str(resolved_by) if resolved_by else None,
                "alert_count": group.alert_count,
            },
        )

        return group

    def get_active_groups_for_rule(
        self,
        rule_id: UUID,
        limit: int = 100,
    ) -> List[AlertGroup]:
        """Получить активные группы для правила.

        Args:
            rule_id: ID правила алерта
            limit: Максимальное количество групп

        Returns:
            Список активных групп
        """
        return self.alert_service.list_groups(
            rule_id=rule_id,
            status="active",
            limit=limit,
        )

    def cleanup_old_groups(
        self,
        older_than_days: int = 7,
        status: str = "resolved",
    ) -> int:
        """Очистить старые группы.

        Args:
            older_than_days: Удалить группы старше N дней
            status: Статус групп для очистки

        Returns:
            Количество удаленных групп
        """
        threshold = datetime.utcnow() - timedelta(days=older_than_days)

        groups = (
            self.db.query(AlertGroup)
            .filter(
                AlertGroup.status == status,
                AlertGroup.resolved_at < threshold,
            )
            .all()
        )

        count = len(groups)
        for group in groups:
            self.alert_service.delete_group(group.id)

        logger.info(f"Cleaned up {count} old alert groups (status={status})")

        return count

    def get_group_statistics(
        self,
        group_id: UUID,
    ) -> Dict:
        """Получить статистику по группе.

        Args:
            group_id: ID группы

        Returns:
            Словарь со статистикой
        """
        group = self.alert_service.get_group(group_id)
        if not group:
            return {}

        # Получение экземпляров группы
        instances = self.alert_service.list_instances(
            group_id=group_id,
            limit=1000,
        )

        # Статистика по статусам
        status_counts = {}
        for instance in instances:
            status = instance.status
            status_counts[status] = status_counts.get(status, 0) + 1

        # Длительность группы
        duration_sec = None
        if group.resolved_at and group.first_alert_at:
            duration = group.resolved_at - group.first_alert_at
            duration_sec = int(duration.total_seconds())
        elif group.first_alert_at:
            duration = datetime.utcnow() - group.first_alert_at
            duration_sec = int(duration.total_seconds())

        return {
            "group_id": str(group.id),
            "group_key": group.group_key,
            "status": group.status,
            "severity": group.severity,
            "alert_count": group.alert_count,
            "notification_count": group.notification_count,
            "first_alert_at": group.first_alert_at.isoformat() if group.first_alert_at else None,
            "last_alert_at": group.last_alert_at.isoformat() if group.last_alert_at else None,
            "resolved_at": group.resolved_at.isoformat() if group.resolved_at else None,
            "duration_sec": duration_sec,
            "status_breakdown": status_counts,
        }

    # --- Private helpers ---

    def _generate_group_key(self, rule: AlertRule, context: Dict) -> str:
        """Сгенерировать уникальный ключ группы.

        Ключ включает:
        - ID правила
        - Host (если есть)
        - Service (если есть)
        - Ключевые теги

        Args:
            rule: Правило алерта
            context: Контекст алерта

        Returns:
            Строка ключа группы
        """
        parts = [str(rule.id)]

        # Добавление host если есть
        host = context.get("host")
        if host:
            parts.append(f"host:{host}")

        # Добавление service если есть
        service = context.get("service")
        if service:
            parts.append(f"service:{service}")

        # Добавление важных тегов
        tags = context.get("tags", {})
        if isinstance(tags, dict):
            # Приоритетные теги для группировки
            priority_tags = ["environment", "region", "cluster", "instance"]
            for tag_key in priority_tags:
                if tag_key in tags:
                    parts.append(f"{tag_key}:{tags[tag_key]}")

        return "|".join(parts)

    def _generate_group_name(self, rule: AlertRule, context: Dict) -> str:
        """Сгенерировать человекочитаемое название группы.

        Args:
            rule: Правило алерта
            context: Контекст алерта

        Returns:
            Название группы
        """
        parts = [rule.name]

        host = context.get("host")
        if host:
            parts.append(f"@ {host}")

        service = context.get("service")
        if service:
            parts.append(f"({service})")

        return " ".join(parts)

    def _find_active_group(
        self,
        rule_id: UUID,
        group_key: str,
        window_sec: int,
    ) -> Optional[AlertGroup]:
        """Найти активную группу в пределах временного окна.

        Args:
            rule_id: ID правила
            group_key: Ключ группы
            window_sec: Временное окно в секундах

        Returns:
            Найденная группа или None
        """
        threshold = datetime.utcnow() - timedelta(seconds=window_sec)

        group = (
            self.db.query(AlertGroup)
            .filter(
                AlertGroup.rule_id == rule_id,
                AlertGroup.group_key == group_key,
                AlertGroup.status == "active",
                AlertGroup.last_alert_at >= threshold,
            )
            .order_by(AlertGroup.last_alert_at.desc())
            .first()
        )

        return group

    def _should_escalate_severity(self, current_severity: str, new_severity: str) -> bool:
        """Определить, нужно ли эскалировать важность.

        Args:
            current_severity: Текущая важность
            new_severity: Новая важность

        Returns:
            True если нужна эскалация
        """
        severity_order = {"info": 0, "warning": 1, "critical": 2}
        current_level = severity_order.get(current_severity, 0)
        new_level = severity_order.get(new_severity, 0)

        return new_level > current_level

    def _has_severity_escalated(self, group: AlertGroup) -> bool:
        """Проверить, эскалировала ли важность группы.

        Args:
            group: Группа алертов

        Returns:
            True если была эскалация
        """
        # Проверяем контекст на предмет эскалации
        if group.context and isinstance(group.context, dict):
            original_severity = group.context.get("original_severity")
            if original_severity and original_severity != group.severity:
                return True

        return False
