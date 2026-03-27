"""
Базовый сервис алертов: CRUD для правил, экземпляров и групп алертов.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.alert import (
    AlertRule,
    AlertInstance,
    AlertGroup,
)
from src.schemas.alerts import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertInstanceCreate,
    AlertInstanceUpdate,
    AlertGroupCreate,
    AlertGroupUpdate,
)

logger = logging.getLogger(__name__)


class AlertService:
    """Сервис работы с сущностями алертов."""

    def __init__(self, db: Session):
        self.db = db

    # --- Alert Rules ---
    def list_rules(
        self,
        enabled: Optional[bool] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> List[AlertRule]:
        """Получить список правил алертов с опциональной фильтрацией."""
        query = self.db.query(AlertRule)
        if enabled is not None:
            query = query.filter(AlertRule.enabled == enabled)
        if alert_type:
            query = query.filter(AlertRule.alert_type == alert_type)
        if severity:
            query = query.filter(AlertRule.severity == severity)
        return query.order_by(AlertRule.created_at.desc()).all()

    def get_rule(self, rule_id: UUID) -> Optional[AlertRule]:
        """Получить правило алерта по ID."""
        return self.db.get(AlertRule, rule_id)

    def get_rule_by_name(self, name: str) -> Optional[AlertRule]:
        """Получить правило алерта по имени."""
        return self.db.query(AlertRule).filter(AlertRule.name == name).first()

    def create_rule(self, data: AlertRuleCreate) -> AlertRule:
        """Создать новое правило алерта."""
        rule = AlertRule(**data.model_dump())
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Created alert rule: {rule.name} ({rule.id})")
        return rule

    def update_rule(self, rule_id: UUID, data: AlertRuleUpdate) -> Optional[AlertRule]:
        """Обновить правило алерта."""
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        self.db.commit()
        self.db.refresh(rule)
        logger.info(f"Updated alert rule: {rule.name} ({rule.id})")
        return rule

    def delete_rule(self, rule_id: UUID) -> bool:
        """Удалить правило алерта."""
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        logger.info(f"Deleted alert rule: {rule.name} ({rule_id})")
        return True

    def increment_trigger_count(self, rule_id: UUID) -> Optional[AlertRule]:
        """Увеличить счетчик срабатываний правила."""
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        rule.trigger_count += 1
        rule.consecutive_triggers += 1
        rule.last_triggered_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def reset_consecutive_triggers(self, rule_id: UUID) -> Optional[AlertRule]:
        """Сбросить счетчик последовательных срабатываний."""
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        rule.consecutive_triggers = 0
        rule.last_resolved_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(rule)
        return rule

    # --- Alert Instances ---
    def list_instances(
        self,
        rule_id: Optional[UUID] = None,
        status: Optional[str] = None,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        group_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[AlertInstance]:
        """Получить список экземпляров алертов с опциональной фильтрацией."""
        query = self.db.query(AlertInstance)
        if rule_id:
            query = query.filter(AlertInstance.rule_id == rule_id)
        if status:
            query = query.filter(AlertInstance.status == status)
        if alert_type:
            query = query.filter(AlertInstance.alert_type == alert_type)
        if severity:
            query = query.filter(AlertInstance.severity == severity)
        if group_id:
            query = query.filter(AlertInstance.group_id == group_id)
        return query.order_by(AlertInstance.fired_at.desc()).limit(limit).all()

    def get_instance(self, instance_id: UUID) -> Optional[AlertInstance]:
        """Получить экземпляр алерта по ID."""
        return self.db.get(AlertInstance, instance_id)

    def create_instance(self, data: AlertInstanceCreate) -> AlertInstance:
        """Создать новый экземпляр алерта."""
        instance = AlertInstance(**data.model_dump())
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        logger.info(
            f"Created alert instance: rule_id={instance.rule_id}, "
            f"type={instance.alert_type}, severity={instance.severity}"
        )
        return instance

    def update_instance(self, instance_id: UUID, data: AlertInstanceUpdate) -> Optional[AlertInstance]:
        """Обновить экземпляр алерта."""
        instance = self.get_instance(instance_id)
        if not instance:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(instance, field, value)
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"Updated alert instance: {instance_id}")
        return instance

    def delete_instance(self, instance_id: UUID) -> bool:
        """Удалить экземпляр алерта."""
        instance = self.get_instance(instance_id)
        if not instance:
            return False
        self.db.delete(instance)
        self.db.commit()
        logger.info(f"Deleted alert instance: {instance_id}")
        return True

    def resolve_instance(self, instance_id: UUID) -> Optional[AlertInstance]:
        """Пометить экземпляр алерта как решенный."""
        instance = self.get_instance(instance_id)
        if not instance:
            return None
        instance.status = "resolved"
        instance.resolved_at = datetime.utcnow()
        if instance.fired_at:
            duration = datetime.utcnow() - instance.fired_at
            instance.duration_sec = int(duration.total_seconds())
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"Resolved alert instance: {instance_id}")
        return instance

    def acknowledge_instance(self, instance_id: UUID, acknowledged_by: UUID) -> Optional[AlertInstance]:
        """Пометить экземпляр алерта как подтвержденный."""
        instance = self.get_instance(instance_id)
        if not instance:
            return None
        instance.status = "acknowledged"
        instance.acknowledged_at = datetime.utcnow()
        instance.acknowledged_by = acknowledged_by
        self.db.commit()
        self.db.refresh(instance)
        logger.info(f"Acknowledged alert instance: {instance_id} by {acknowledged_by}")
        return instance

    # --- Alert Groups ---
    def list_groups(
        self,
        rule_id: Optional[UUID] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[AlertGroup]:
        """Получить список групп алертов с опциональной фильтрацией."""
        query = self.db.query(AlertGroup)
        if rule_id:
            query = query.filter(AlertGroup.rule_id == rule_id)
        if status:
            query = query.filter(AlertGroup.status == status)
        if severity:
            query = query.filter(AlertGroup.severity == severity)
        return query.order_by(AlertGroup.created_at.desc()).limit(limit).all()

    def get_group(self, group_id: UUID) -> Optional[AlertGroup]:
        """Получить группу алерта по ID."""
        return self.db.get(AlertGroup, group_id)

    def get_group_by_key(self, rule_id: UUID, group_key: str) -> Optional[AlertGroup]:
        """Получить группу алерта по правилу и ключу группы."""
        return (
            self.db.query(AlertGroup)
            .filter(AlertGroup.rule_id == rule_id, AlertGroup.group_key == group_key)
            .first()
        )

    def create_group(self, data: AlertGroupCreate) -> AlertGroup:
        """Создать новую группу алерта."""
        group = AlertGroup(**data.model_dump())
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        logger.info(f"Created alert group: {group.group_key} ({group.id})")
        return group

    def update_group(self, group_id: UUID, data: AlertGroupUpdate) -> Optional[AlertGroup]:
        """Обновить группу алерта."""
        group = self.get_group(group_id)
        if not group:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(group, field, value)
        self.db.commit()
        self.db.refresh(group)
        logger.info(f"Updated alert group: {group_id}")
        return group

    def delete_group(self, group_id: UUID) -> bool:
        """Удалить группу алерта."""
        group = self.get_group(group_id)
        if not group:
            return False
        self.db.delete(group)
        self.db.commit()
        logger.info(f"Deleted alert group: {group_id}")
        return True

    def add_instance_to_group(self, group_id: UUID, instance_id: UUID) -> Optional[AlertGroup]:
        """Добавить экземпляр алерта в группу."""
        group = self.get_group(group_id)
        instance = self.get_instance(instance_id)
        if not group or not instance:
            return None
        instance.group_id = group_id
        group.alert_count += 1
        group.last_alert_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(group)
        logger.info(f"Added instance {instance_id} to group {group_id}")
        return group

    def resolve_group(self, group_id: UUID, resolved_by: Optional[UUID] = None) -> Optional[AlertGroup]:
        """Пометить группу алерта как решенную."""
        group = self.get_group(group_id)
        if not group:
            return None
        group.status = "resolved"
        group.resolved_at = datetime.utcnow()
        group.resolved_by = resolved_by
        self.db.commit()
        self.db.refresh(group)
        logger.info(f"Resolved alert group: {group_id}")
        return group
