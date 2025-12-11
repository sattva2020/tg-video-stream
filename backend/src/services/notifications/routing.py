"""Сервис маршрутизации и эскалаций для событий уведомлений."""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.notifications import NotificationRule, notification_rule_channels
from src.services.notifications.base import NotificationService

logger = logging.getLogger(__name__)


@dataclass
class EventPayload:
    event_id: str
    severity: Optional[str] = None
    tags: Optional[Dict] = None
    host: Optional[str] = None
    context: Optional[Dict] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class NotificationRoutingService:
    """Подбор правил и построение плана доставки по эскалациям."""

    def __init__(self, db: Session):
        self.db = db
        self.service = NotificationService(db)

    def _ordered_channel_ids(self, rule_id: UUID) -> List[UUID]:
        return (
            self.db.execute(
                select(notification_rule_channels.c.channel_id)
                .where(notification_rule_channels.c.rule_id == rule_id)
                .order_by(notification_rule_channels.c.priority.asc())
            )
            .scalars()
            .all()
        )

    def _rule_matches(self, rule: NotificationRule, *, severity: Optional[str], tags: Optional[Dict], host: Optional[str]) -> bool:
        if rule.enabled is False:
            return False

        if rule.severity_filter:
            allowed = rule.severity_filter.get("include") if isinstance(rule.severity_filter, dict) else rule.severity_filter
            if allowed and severity not in allowed:
                return False

        if rule.host_filter:
            hosts = rule.host_filter.get("include") if isinstance(rule.host_filter, dict) else rule.host_filter
            if hosts and host not in hosts:
                return False

        if rule.tag_filter and tags:
            for key, expected in rule.tag_filter.items():
                value = tags.get(key)
                if isinstance(expected, list):
                    if value not in expected:
                        return False
                else:
                    if value != expected:
                        return False

        return True

    def match_rules(self, *, severity: Optional[str], tags: Optional[Dict], host: Optional[str]) -> List[NotificationRule]:
        rules = self.service.list_rules(enabled=True)
        return [rule for rule in rules if self._rule_matches(rule, severity=severity, tags=tags, host=host)]

    def build_delivery_plan(self, event: EventPayload) -> List[Dict]:
        plan: List[Dict] = []
        matched_rules = self.match_rules(severity=event.severity, tags=event.tags, host=event.host)

        for rule in matched_rules:
            channel_ids = self._ordered_channel_ids(rule.id)
            if not channel_ids:
                logger.info("rule has no channels, skip", extra={"rule_id": str(rule.id)})
                continue

            recipients = rule.recipients
            if not recipients:
                logger.info("rule has no recipients, skip", extra={"rule_id": str(rule.id)})
                continue

            for recipient in recipients:
                plan.append(
                    {
                        "event_id": event.event_id,
                        "rule_id": rule.id,
                        "recipient_id": recipient.id,
                        "channel_ids": channel_ids,
                        "failover_timeout_sec": rule.failover_timeout_sec,
                        "context": event.context or {},
                        "subject": event.subject,
                        "body": event.body,
                    }
                )

        return plan
