import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    Text,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Index,
    Table,
    func,
)
from sqlalchemy.orm import relationship
from src.database import Base, GUID


notification_rule_recipients = Table(
    "notification_rule_recipients",
    Base.metadata,
    Column("rule_id", GUID(), ForeignKey("notification_rules.id", ondelete="CASCADE"), primary_key=True),
    Column("recipient_id", GUID(), ForeignKey("notification_recipients.id", ondelete="CASCADE"), primary_key=True),
)


notification_rule_channels = Table(
    "notification_rule_channels",
    Base.metadata,
    Column("rule_id", GUID(), ForeignKey("notification_rules.id", ondelete="CASCADE"), primary_key=True),
    Column("channel_id", GUID(), ForeignKey("notification_channels.id", ondelete="CASCADE"), primary_key=True),
    Column("priority", Integer, nullable=False, default=0),
    Index("ix_notification_rule_channels_order", "rule_id", "priority"),
)


class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    __table_args__ = (
        UniqueConstraint("name", name="uq_notification_channel_name"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    enabled = Column(Boolean, nullable=False, default=True)
    status = Column(String(32), nullable=False, default="ok")
    test_at = Column(DateTime(timezone=True), nullable=True)
    concurrency_limit = Column(Integer, nullable=True)
    retry_attempts = Column(Integer, nullable=False, default=3)
    retry_interval_sec = Column(Integer, nullable=False, default=30)
    timeout_sec = Column(Integer, nullable=False, default=10)
    is_primary = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    templates = relationship("NotificationTemplate", back_populates="channel", cascade="all, delete")
    delivery_logs = relationship("DeliveryLog", back_populates="channel", cascade="all, delete-orphan")
    rules = relationship(
        "NotificationRule",
        secondary=notification_rule_channels,
        back_populates="channels",
    )


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"
    __table_args__ = (
        UniqueConstraint("name", name="uq_notification_template_name"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    locale = Column(String(5), nullable=False, default="en")
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    variables = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    channel_id = Column(GUID(), ForeignKey("notification_channels.id", ondelete="SET NULL"), nullable=True)
    channel = relationship("NotificationChannel", back_populates="templates")
    rules = relationship("NotificationRule", back_populates="template")


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"
    __table_args__ = (
        UniqueConstraint("type", "address", name="uq_notification_recipient_address"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)
    address = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    silence_windows = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rules = relationship(
        "NotificationRule",
        secondary=notification_rule_recipients,
        back_populates="recipients",
    )
    delivery_logs = relationship("DeliveryLog", back_populates="recipient")


class NotificationRule(Base):
    __tablename__ = "notification_rules"
    __table_args__ = (
        UniqueConstraint("name", name="uq_notification_rule_name"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    severity_filter = Column(JSON, nullable=True)
    tag_filter = Column(JSON, nullable=True)
    host_filter = Column(JSON, nullable=True)
    failover_timeout_sec = Column(Integer, nullable=False, default=30)
    silence_windows = Column(JSON, nullable=True)
    rate_limit = Column(JSON, nullable=True)
    dedup_window_sec = Column(Integer, nullable=False, default=0)
    template_id = Column(GUID(), ForeignKey("notification_templates.id", ondelete="SET NULL"), nullable=True)
    test_channel_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    template = relationship("NotificationTemplate", back_populates="rules")
    recipients = relationship(
        "NotificationRecipient",
        secondary=notification_rule_recipients,
        back_populates="rules",
    )
    channels = relationship(
        "NotificationChannel",
        secondary=notification_rule_channels,
        back_populates="rules",
    )
    delivery_logs = relationship("DeliveryLog", back_populates="rule")


class DeliveryLog(Base):
    __tablename__ = "notification_delivery_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(255), nullable=False)
    rule_id = Column(GUID(), ForeignKey("notification_rules.id", ondelete="SET NULL"), nullable=True)
    channel_id = Column(GUID(), ForeignKey("notification_channels.id", ondelete="SET NULL"), nullable=True)
    recipient_id = Column(GUID(), ForeignKey("notification_recipients.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), nullable=False)
    attempt = Column(Integer, nullable=False, default=1)
    latency_ms = Column(Integer, nullable=True)
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    rule = relationship("NotificationRule", back_populates="delivery_logs")
    channel = relationship("NotificationChannel", back_populates="delivery_logs")
    recipient = relationship("NotificationRecipient", back_populates="delivery_logs")

    __table_args__ = (
        Index("ix_notification_delivery_logs_event", "event_id"),
        Index("ix_notification_delivery_logs_status", "status"),
    )
