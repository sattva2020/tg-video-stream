import uuid
from enum import Enum as PyEnum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, func, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class SubscriptionStatus(str, PyEnum):
    """Subscription statuses."""
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class PlanType(str, PyEnum):
    """Subscription plan types."""
    TRIAL = "trial"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Subscription(Base):
    """Subscription model for managing organization billing and plans."""
    __tablename__ = "subscriptions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(GUID(), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, unique=True)
    plan_type = Column(String(50), nullable=False)
    status = Column(String(32), nullable=False, default=SubscriptionStatus.TRIALING.value, server_default="'trialing'")
    billing_email = Column(String(255), nullable=True)
    billing_address = Column(JSONB, nullable=True)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False, server_default='false')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship(
        "Organization",
        back_populates="subscription",
        uselist=False,
        lazy="select"
    )

    def __repr__(self):
        return f"<Subscription(id='{self.id}', org_id='{self.organization_id}', plan='{self.plan_type}', status='{self.status}')>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is active."""
        return self.status in (
            SubscriptionStatus.ACTIVE.value,
            SubscriptionStatus.TRIALING.value,
        )

    @property
    def is_trial(self) -> bool:
        """Check if subscription is in trial period."""
        if self.status != SubscriptionStatus.TRIALING.value:
            return False
        if not self.trial_ends_at:
            return True
        return self.trial_ends_at > datetime.now(timezone.utc)

    @property
    def trial_days_remaining(self) -> int | None:
        """Get remaining trial days."""
        if not self.trial_ends_at:
            return None
        delta = self.trial_ends_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    @property
    def is_past_due(self) -> bool:
        """Check if subscription is past due."""
        return self.status == SubscriptionStatus.PAST_DUE.value

    @property
    def is_canceled(self) -> bool:
        """Check if subscription is canceled."""
        return self.status == SubscriptionStatus.CANCELED.value

    def cancel(self, at_period_end: bool = True) -> None:
        """Cancel subscription."""
        if at_period_end:
            self.cancel_at_period_end = True
        else:
            self.status = SubscriptionStatus.CANCELED.value

    def activate(self) -> None:
        """Activate subscription."""
        self.status = SubscriptionStatus.ACTIVE.value
        self.cancel_at_period_end = False

    def update_status(self, new_status: SubscriptionStatus) -> None:
        """Update subscription status."""
        self.status = new_status.value
