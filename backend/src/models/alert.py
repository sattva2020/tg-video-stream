"""
Feature 013: Alerting and Notification System

AlertRule model for defining alert conditions and thresholds.
"""

import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class AlertRule(Base):
    """
    AlertRule defines conditions for triggering alerts.

    Supports various alert types:
    - Stream quality degradation
    - Service health issues
    - Resource thresholds
    - Custom metrics

    Example conditions:
    - Alert when stream quality < "high" for 3 consecutive checks
    - Alert when CPU usage > 90% for 5 minutes
    - Alert when error rate > 5% in 10 minute window
    """
    __tablename__ = "alert_rules"
    __table_args__ = (
        UniqueConstraint("name", name="uq_alert_rule_name"),
    )

    # Primary key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)

    # Alert classification
    alert_type = Column(String(50), nullable=False)  # stream_quality, service_health, resource, custom
    severity = Column(String(32), nullable=False, default="warning")  # critical, warning, info
    category = Column(String(100), nullable=True)  # Optional categorization

    # Alert conditions (JSONB for flexible threshold definitions)
    conditions = Column(JSONB, nullable=False, default=dict)
    # Example: {
    #   "metric": "stream_quality",
    #   "operator": "lt",
    #   "threshold": "high",
    #   "consecutive_failures": 3,
    #   "evaluation_window_sec": 300
    # }

    # Cooldown and rate limiting
    cooldown_sec = Column(BigInteger, nullable=False, default=300)  # Minimum time between alerts
    rate_limit_minutes = Column(Integer, nullable=True)  # Max alerts per time window
    rate_limit_count = Column(Integer, nullable=True)  # Number of alerts allowed

    # Notification settings
    notification_channels = Column(JSONB, nullable=True)
    # Example: {
    #   "telegram": [123, 456],
    #   "email": ["admin@example.com"],
    #   "webhook": ["https://example.com/alert"]
    # }

    # Alert behavior
    notify_on_recovery = Column(Boolean, nullable=False, default=False)  # Send recovery notification
    auto_resolve = Column(Boolean, nullable=False, default=False)  # Auto-resolve when condition clears
    escalation_enabled = Column(Boolean, nullable=False, default=False)
    escalation_rules = Column(JSONB, nullable=True)

    # Scheduling and silencing
    active_windows = Column(JSONB, nullable=True)  # Time windows when rule is active
    silence_windows = Column(JSONB, nullable=True)  # Maintenance windows to suppress alerts

    # Tracking fields
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    last_resolved_at = Column(DateTime(timezone=True), nullable=True)
    trigger_count = Column(BigInteger, nullable=False, default=0)
    consecutive_triggers = Column(BigInteger, nullable=False, default=0)

    # Metadata (timezone-aware timestamps)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    instances = relationship("AlertInstance", back_populates="rule", cascade="all, delete-orphan")
    groups = relationship("AlertGroup", back_populates="rule", cascade="all, delete-orphan")


class AlertInstance(Base):
    """
    AlertInstance tracks individual alert occurrences (fired alerts).

    Each time an AlertRule conditions are met, an AlertInstance is created
    to record the event. This provides a complete history of when alerts fired,
    their context, and their resolution status.

    Example:
    - AlertRule: "CPU usage > 90%"
    - AlertInstance #1: Fired at 10:00 AM, value=95%, resolved at 10:15 AM
    - AlertInstance #2: Fired at 11:00 AM, value=92%, still firing
    """
    __tablename__ = "alert_instances"

    # Primary key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Reference to the rule that created this instance
    rule_id = Column(GUID(), ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False)
    rule = relationship("AlertRule", back_populates="instances")

    # Alert details
    alert_type = Column(String(50), nullable=False)  # stream_quality, service_health, resource, custom
    severity = Column(String(32), nullable=False, default="warning")  # critical, warning, info
    status = Column(String(32), nullable=False, default="firing")  # firing, resolved, acknowledged, suppressed

    # Alert context (what triggered the alert)
    trigger_value = Column(JSONB, nullable=True)
    # Example: {
    #   "metric": "cpu_usage",
    #   "current_value": 95.2,
    #   "threshold": 90,
    #   "operator": "gt"
    # }

    # Alert metadata
    context = Column(JSONB, nullable=True)
    # Additional context about the alert:
    # {
    #   "host": "server-1",
    #   "service": "api",
    #   "tags": ["production", "critical"],
    #   "consecutive_failures": 3
    # }

    # Notification tracking
    notification_sent = Column(Boolean, nullable=False, default=False)
    notification_channels = Column(JSONB, nullable=True)
    # Example: {
    #   "telegram": [123, 456],
    #   "email": ["admin@example.com"],
    #   "success": true,
    #   "errors": []
    # }

    # Alert grouping (optional - will be populated by AlertGroupingService)
    group_id = Column(GUID(), ForeignKey("alert_groups.id", ondelete="SET NULL"), nullable=True)
    group = relationship("AlertGroup", back_populates="instances", foreign_keys=[group_id])

    # Resolution tracking
    fired_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Duration tracking (how long the alert was firing)
    duration_sec = Column(BigInteger, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Indexes for common queries
    __table_args__ = (
        Index("ix_alert_instances_rule_id", "rule_id"),
        Index("ix_alert_instances_status", "status"),
        Index("ix_alert_instances_fired_at", "fired_at"),
        Index("ix_alert_instances_severity", "severity"),
        Index("ix_alert_instances_alert_type", "alert_type"),
    )
