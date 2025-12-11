"""
Базовый сервис уведомлений: CRUD для каналов, шаблонов, получателей, правил и логов доставки.
"""
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from src.models.notifications import (
    NotificationChannel,
    NotificationTemplate,
    NotificationRecipient,
    NotificationRule,
    DeliveryLog,
    notification_rule_channels,
)
from src.schemas.notifications import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
    NotificationRecipientCreate,
    NotificationRecipientUpdate,
    NotificationRuleCreate,
    NotificationRuleUpdate,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис работы с сущностями уведомлений."""

    def __init__(self, db: Session):
        self.db = db

    # --- Channels ---
    def list_channels(self, enabled: Optional[bool] = None, types: Optional[List[str]] = None) -> List[NotificationChannel]:
        query = self.db.query(NotificationChannel)
        if enabled is not None:
            query = query.filter(NotificationChannel.enabled == enabled)
        if types:
            query = query.filter(NotificationChannel.type.in_(types))
        return query.order_by(NotificationChannel.created_at.desc()).all()

    def get_channel(self, channel_id: UUID) -> Optional[NotificationChannel]:
        return self.db.get(NotificationChannel, channel_id)

    def create_channel(self, data: NotificationChannelCreate) -> NotificationChannel:
        channel = NotificationChannel(**data.model_dump())
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        return channel

    def update_channel(self, channel_id: UUID, data: NotificationChannelUpdate) -> Optional[NotificationChannel]:
        channel = self.get_channel(channel_id)
        if not channel:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(channel, field, value)
        self.db.commit()
        self.db.refresh(channel)
        return channel

    def delete_channel(self, channel_id: UUID) -> bool:
        channel = self.get_channel(channel_id)
        if not channel:
            return False
        self.db.delete(channel)
        self.db.commit()
        return True

    # --- Templates ---
    def list_templates(self, locale: Optional[str] = None) -> List[NotificationTemplate]:
        query = self.db.query(NotificationTemplate)
        if locale:
            query = query.filter(NotificationTemplate.locale == locale)
        return query.order_by(NotificationTemplate.created_at.desc()).all()

    def get_template(self, template_id: UUID) -> Optional[NotificationTemplate]:
        return self.db.get(NotificationTemplate, template_id)

    def create_template(self, data: NotificationTemplateCreate) -> NotificationTemplate:
        template = NotificationTemplate(**data.model_dump())
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def update_template(self, template_id: UUID, data: NotificationTemplateUpdate) -> Optional[NotificationTemplate]:
        template = self.get_template(template_id)
        if not template:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(template, field, value)
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete_template(self, template_id: UUID) -> bool:
        template = self.get_template(template_id)
        if not template:
            return False
        self.db.delete(template)
        self.db.commit()
        return True

    # --- Recipients ---
    def list_recipients(self, status: Optional[str] = None, r_type: Optional[str] = None) -> List[NotificationRecipient]:
        query = self.db.query(NotificationRecipient)
        if status:
            query = query.filter(NotificationRecipient.status == status)
        if r_type:
            query = query.filter(NotificationRecipient.type == r_type)
        return query.order_by(NotificationRecipient.created_at.desc()).all()

    def get_recipient(self, recipient_id: UUID) -> Optional[NotificationRecipient]:
        return self.db.get(NotificationRecipient, recipient_id)

    def create_recipient(self, data: NotificationRecipientCreate) -> NotificationRecipient:
        recipient = NotificationRecipient(**data.model_dump())
        self.db.add(recipient)
        self.db.commit()
        self.db.refresh(recipient)
        return recipient

    def update_recipient(self, recipient_id: UUID, data: NotificationRecipientUpdate) -> Optional[NotificationRecipient]:
        recipient = self.get_recipient(recipient_id)
        if not recipient:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(recipient, field, value)
        self.db.commit()
        self.db.refresh(recipient)
        return recipient

    def delete_recipient(self, recipient_id: UUID) -> bool:
        recipient = self.get_recipient(recipient_id)
        if not recipient:
            return False
        self.db.delete(recipient)
        self.db.commit()
        return True

    # --- Rules ---
    def list_rules(self, enabled: Optional[bool] = None) -> List[NotificationRule]:
        query = self.db.query(NotificationRule)
        if enabled is not None:
            query = query.filter(NotificationRule.enabled == enabled)
        return query.order_by(NotificationRule.created_at.desc()).all()

    def get_rule(self, rule_id: UUID) -> Optional[NotificationRule]:
        return self.db.get(NotificationRule, rule_id)

    def create_rule(self, data: NotificationRuleCreate) -> NotificationRule:
        payload = data.model_dump(exclude={"recipient_ids", "channel_ids"}, exclude_none=True)
        rule = NotificationRule(**payload)
        self.db.add(rule)
        self._set_rule_relations(rule, data.recipient_ids, data.channel_ids)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update_rule(self, rule_id: UUID, data: NotificationRuleUpdate) -> Optional[NotificationRule]:
        rule = self.get_rule(rule_id)
        if not rule:
            return None
        updates = data.model_dump(exclude_unset=True, exclude={"recipient_ids", "channel_ids"})
        for field, value in updates.items():
            setattr(rule, field, value)
        if data.recipient_ids is not None or data.channel_ids is not None:
            recipient_ids = data.recipient_ids if data.recipient_ids is not None else [r.id for r in rule.recipients]
            channel_ids = data.channel_ids if data.channel_ids is not None else [c.id for c in rule.channels]
            self._set_rule_relations(rule, recipient_ids, channel_ids)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: UUID) -> bool:
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        self.db.delete(rule)
        self.db.commit()
        return True

    # --- Delivery Logs ---
    def log_delivery(
        self,
        *,
        event_id: str,
        status: str,
        rule_id: Optional[UUID] = None,
        channel_id: Optional[UUID] = None,
        recipient_id: Optional[UUID] = None,
        attempt: int = 1,
        latency_ms: Optional[int] = None,
        response_code: Optional[int] = None,
        response_body: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> DeliveryLog:
        entry = DeliveryLog(
            event_id=event_id,
            status=status,
            rule_id=rule_id,
            channel_id=channel_id,
            recipient_id=recipient_id,
            attempt=attempt,
            latency_ms=latency_ms,
            response_code=response_code,
            response_body=response_body,
            error_message=error_message,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def get_log(self, log_id: UUID) -> Optional[DeliveryLog]:
        return self.db.get(DeliveryLog, log_id)

    def list_logs(
        self,
        *,
        rule_id: Optional[UUID] = None,
        channel_id: Optional[UUID] = None,
        recipient_id: Optional[UUID] = None,
        event_id: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        created_from: Optional[datetime] = None,
        created_to: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[DeliveryLog]:
        query = self.db.query(DeliveryLog)
        if rule_id:
            query = query.filter(DeliveryLog.rule_id == rule_id)
        if channel_id:
            query = query.filter(DeliveryLog.channel_id == channel_id)
        if recipient_id:
            query = query.filter(DeliveryLog.recipient_id == recipient_id)
        if event_id:
            query = query.filter(DeliveryLog.event_id == event_id)
        if statuses:
            query = query.filter(DeliveryLog.status.in_(statuses))
        if created_from:
            query = query.filter(DeliveryLog.created_at >= created_from)
        if created_to:
            query = query.filter(DeliveryLog.created_at <= created_to)
        return query.order_by(DeliveryLog.created_at.desc()).limit(limit).all()

    # --- Helpers ---
    def _set_rule_relations(self, rule: NotificationRule, recipient_ids: List[UUID], channel_ids: List[UUID]) -> None:
        recipients = (
            self.db.query(NotificationRecipient)
            .filter(NotificationRecipient.id.in_(recipient_ids))
            .all()
            if recipient_ids
            else []
        )
        channels = (
            self.db.query(NotificationChannel)
            .filter(NotificationChannel.id.in_(channel_ids))
            .all()
            if channel_ids
            else []
        )
        rule.recipients = recipients
        rule.channels = channels
        self.db.flush()
        # Обновляем порядок каналов в таблице связей
        for priority, channel in enumerate(channels):
            stmt = (
                update(notification_rule_channels)
                .where(
                    notification_rule_channels.c.rule_id == rule.id,
                    notification_rule_channels.c.channel_id == channel.id,
                )
                .values(priority=priority)
            )
            self.db.execute(stmt)
