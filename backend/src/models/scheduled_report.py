"""
Scheduled Report models for email report generation and delivery.
Feature: 012-comprehensive-analytics-dashboard
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, BigInteger, DateTime, String, Boolean, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class ReportFrequency(str, PyEnum):
    """Frequency for scheduled report generation."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportType(str, PyEnum):
    """Types of available reports."""
    SUMMARY = "summary"
    LISTENERS = "listeners"
    TOP_TRACKS = "top_tracks"
    ENGAGEMENT = "engagement"
    STREAM_PERFORMANCE = "stream_performance"
    CONTENT_INSIGHTS = "content_insights"


class ReportStatus(str, PyEnum):
    """Status of scheduled report execution."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class ScheduledReport(Base):
    """
    Scheduled report configuration for automatic email delivery.
    Admins can schedule reports to be generated and sent via email.
    """
    __tablename__ = "scheduled_reports"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Report configuration
    report_type = Column(String(50), nullable=False, index=True)
    frequency = Column(String(20), nullable=False, default="weekly")
    period = Column(String(10), nullable=False, default="7d")  # 7d, 30d, 90d, all

    # Email delivery
    email = Column(String(255), nullable=False)
    email_subject = Column(String(500), nullable=True)  # Custom subject (optional)

    # Scheduling
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)

    # Execution tracking
    last_status = Column(String(20), nullable=True)  # pending, sent, failed
    last_error = Column(String(1000), nullable=True)
    total_runs = Column(BigInteger, nullable=False, default=0)
    successful_runs = Column(BigInteger, nullable=False, default=0)
    failed_runs = Column(BigInteger, nullable=False, default=0)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    # Indexes for performance
    __table_args__ = (
        Index('idx_scheduled_reports_active', 'is_active'),
        Index('idx_scheduled_reports_next_run', 'next_run_at'),
        Index('idx_scheduled_reports_type', 'report_type'),
    )

    def __repr__(self):
        return f"<ScheduledReport(id={self.id}, type={self.report_type}, frequency={self.frequency}, email={self.email})>"
