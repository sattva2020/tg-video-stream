"""
Security Dashboard Endpoints
Spec: 025-advanced-security-compliance-features

Provides security compliance overview with metrics, status, and
aggregated security events for the admin dashboard.
Admin-only access.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone

from api.auth import require_admin
from src.models.user import User
from src.models.compliance_log import ComplianceLog, ComplianceStatus, SeverityLevel
from src.models.audit_log import AdminAuditLog
from src.models.security_policy import SecurityPolicy
from src.models.saml_config import SAMLConfig
from src.models.ip_whitelist import IPWhitelist
from database import get_db
from src.services.compliance_service import compliance_service, ComplianceFramework

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class ComplianceStatusSummary(BaseModel):
    """Schema for compliance status summary."""
    framework: str
    overall_status: str
    non_compliant_events_last_30_days: int
    requirements: list
    last_checked: str


class SecurityMetrics(BaseModel):
    """Schema for security metrics."""
    total_events: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    unresolved_incidents: int
    period: Dict[str, str]


class DataProtectionStatus(BaseModel):
    """Schema for data protection compliance status."""
    overall_status: str
    checks: Dict[str, Dict[str, str]]
    last_checked: str


class AccessControlStatus(BaseModel):
    """Schema for access control compliance status."""
    overall_status: str
    checks: Dict[str, Dict[str, str]]
    last_checked: str


class SecurityConfigSummary(BaseModel):
    """Schema for security configuration summary."""
    saml_configs_enabled: int
    saml_configs_total: int
    security_policies_enabled: int
    security_policies_total: int
    ip_whitelist_entries: int
    two_factor_enforcement_enabled: bool


class SecurityDashboardResponse(BaseModel):
    """Schema for security dashboard response."""
    compliance_status: ComplianceStatusSummary
    security_metrics: SecurityMetrics
    data_protection: DataProtectionStatus
    access_control: AccessControlStatus
    security_configs: SecurityConfigSummary
    recent_critical_events: list
    generated_at: str


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.get("/dashboard", response_model=SecurityDashboardResponse)
def get_security_dashboard(
    framework: str = Query(ComplianceFramework.SOC2, description="Compliance framework (soc2, gdpr)"),
    days: int = Query(30, ge=1, le=365, description="Number of days for metrics"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get security dashboard with compliance status overview.

    Returns aggregated security metrics, compliance status, and
    recent critical events for the admin dashboard.
    """
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Get compliance status
    compliance_status_data = compliance_service.get_compliance_status(
        db=db,
        framework=framework
    )

    # Get security metrics
    metrics_data = compliance_service.get_compliance_metrics(
        db=db,
        start_date=start_date,
        end_date=end_date
    )

    # Get data protection status
    data_protection_data = compliance_service.check_data_protection_compliance(db=db)

    # Get access control status
    access_control_data = compliance_service.check_access_control_compliance(db=db)

    # Get security configuration summary
    saml_configs_total = db.query(SAMLConfig).count()
    saml_configs_enabled = db.query(SAMLConfig).filter(SAMLConfig.enabled == True).count()

    security_policies_total = db.query(SecurityPolicy).count()
    security_policies_enabled = db.query(SecurityPolicy).filter(SecurityPolicy.enabled == True).count()

    ip_whitelist_entries = db.query(IPWhitelist).filter(IPWhitelist.enabled == True).count()

    # Check if 2FA enforcement is enabled
    two_factor_policy = db.query(SecurityPolicy).filter(
        SecurityPolicy.policy_type == "two_factor_enforcement",
        SecurityPolicy.enabled == True
    ).first()
    two_factor_enforcement_enabled = two_factor_policy is not None

    security_configs_data = {
        "saml_configs_enabled": saml_configs_enabled,
        "saml_configs_total": saml_configs_total,
        "security_policies_enabled": security_policies_enabled,
        "security_policies_total": security_policies_total,
        "ip_whitelist_entries": ip_whitelist_entries,
        "two_factor_enforcement_enabled": two_factor_enforcement_enabled
    }

    # Get recent critical events
    recent_critical_events = db.query(ComplianceLog).filter(
        ComplianceLog.severity.in_([SeverityLevel.CRITICAL, SeverityLevel.HIGH]),
        ComplianceLog.compliance_status.in_([
            ComplianceStatus.NON_COMPLIANT,
            ComplianceStatus.PENDING_REVIEW
        ])
    ).order_by(ComplianceLog.timestamp.desc()).limit(10).all()

    recent_events_list = [
        {
            "id": str(event.id),
            "event_type": event.event_type,
            "category": event.category,
            "severity": event.severity,
            "compliance_status": event.compliance_status,
            "title": event.title,
            "description": event.description,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None
        }
        for event in recent_critical_events
    ]

    return SecurityDashboardResponse(
        compliance_status=ComplianceStatusSummary(**compliance_status_data),
        security_metrics=SecurityMetrics(**metrics_data),
        data_protection=DataProtectionStatus(**data_protection_data),
        access_control=AccessControlStatus(**access_control_data),
        security_configs=SecurityConfigSummary(**security_configs_data),
        recent_critical_events=recent_events_list,
        generated_at=datetime.now(timezone.utc).isoformat()
    )


@router.get("/dashboard/metrics", response_model=SecurityMetrics)
def get_security_dashboard_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days for metrics"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get security metrics for the dashboard.

    Returns event counts, severity breakdown, and category breakdown.
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    metrics_data = compliance_service.get_compliance_metrics(
        db=db,
        start_date=start_date,
        end_date=end_date
    )

    return SecurityMetrics(**metrics_data)


@router.get("/dashboard/compliance/{framework}", response_model=ComplianceStatusSummary)
def get_compliance_status(
    framework: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get compliance status for a specific framework.

    Supports SOC 2, GDPR, ISO 27001, and HIPAA frameworks.
    """
    compliance_status_data = compliance_service.get_compliance_status(
        db=db,
        framework=framework
    )

    return ComplianceStatusSummary(**compliance_status_data)


@router.get("/dashboard/data-protection", response_model=DataProtectionStatus)
def get_data_protection_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get data protection compliance status.

    Checks encryption, audit logging, access control, and data retention.
    """
    data_protection_data = compliance_service.check_data_protection_compliance(db=db)

    return DataProtectionStatus(**data_protection_data)


@router.get("/dashboard/access-control", response_model=AccessControlStatus)
def get_access_control_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get access control compliance status.

    Checks authentication, authorization, session management, and IP whitelisting.
    """
    access_control_data = compliance_service.check_access_control_compliance(db=db)

    return AccessControlStatus(**access_control_data)


@router.get("/dashboard/security-configs", response_model=SecurityConfigSummary)
def get_security_config_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get summary of security configurations.

    Returns counts of enabled/total SAML configs, security policies, and IP whitelist entries.
    """
    saml_configs_total = db.query(SAMLConfig).count()
    saml_configs_enabled = db.query(SAMLConfig).filter(SAMLConfig.enabled == True).count()

    security_policies_total = db.query(SecurityPolicy).count()
    security_policies_enabled = db.query(SecurityPolicy).filter(SecurityPolicy.enabled == True).count()

    ip_whitelist_entries = db.query(IPWhitelist).filter(IPWhitelist.enabled == True).count()

    # Check if 2FA enforcement is enabled
    two_factor_policy = db.query(SecurityPolicy).filter(
        SecurityPolicy.policy_type == "two_factor_enforcement",
        SecurityPolicy.enabled == True
    ).first()
    two_factor_enforcement_enabled = two_factor_policy is not None

    return SecurityConfigSummary(
        saml_configs_enabled=saml_configs_enabled,
        saml_configs_total=saml_configs_total,
        security_policies_enabled=security_policies_enabled,
        security_policies_total=security_policies_total,
        ip_whitelist_entries=ip_whitelist_entries,
        two_factor_enforcement_enabled=two_factor_enforcement_enabled
    )


@router.get("/dashboard/recent-events")
def get_recent_critical_events(
    limit: int = Query(10, ge=1, le=100, description="Number of events to return"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get recent critical security events.

    Returns the most recent critical and high-severity events that require attention.
    """
    query = db.query(ComplianceLog).filter(
        ComplianceLog.compliance_status.in_([
            ComplianceStatus.NON_COMPLIANT,
            ComplianceStatus.PENDING_REVIEW
        ])
    )

    if severity:
        query = query.filter(ComplianceLog.severity == severity)
    else:
        # Default to critical and high severity
        query = query.filter(
            ComplianceLog.severity.in_([SeverityLevel.CRITICAL, SeverityLevel.HIGH])
        )

    events = query.order_by(ComplianceLog.timestamp.desc()).limit(limit).all()

    return {
        "total": len(events),
        "events": [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "category": event.category,
                "severity": event.severity,
                "compliance_status": event.compliance_status,
                "title": event.title,
                "description": event.description,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None
            }
            for event in events
        ]
    }
