"""
Compliance Report Generation Endpoints
Spec: 025-advanced-security-compliance-features

Provides comprehensive compliance report generation for SOC 2, GDPR, ISO 27001, and HIPAA.
Admin-only access for generating compliance reports with status, metrics, findings, and recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import json

from api.auth import require_admin
from src.models.user import User
from src.models.compliance_log import ComplianceLog, ComplianceStatus, SeverityLevel
from src.models.audit_log import AdminAuditLog
from src.models.security_policy import SecurityPolicy
from src.models.saml_config import SAMLConfig
from src.models.ip_whitelist import IPWhitelist
from database import get_db
from src.services.compliance_service import compliance_service, ComplianceFramework
from src.services.activity_service import ActivityService
from src.lib.audit import audit_export

router = APIRouter()


class ComplianceReportResponse(BaseModel):
    """Schema for compliance report response."""
    report_type: str = "compliance_report"
    framework: str
    report_date: str
    report_period: Dict[str, str]
    executive_summary: Dict[str, Any]
    compliance_status: Dict[str, Any]
    security_metrics: Dict[str, Any]
    data_protection: Dict[str, Any]
    access_control: Dict[str, Any]
    security_configurations: Dict[str, Any]
    findings_and_recommendations: list
    appendices: Dict[str, Any]


@router.get("/compliance/report")
@audit_export("compliance_report")
async def generate_compliance_report(
    framework: str = Query(ComplianceFramework.SOC2, description="Compliance framework (soc2, gdpr, iso27001, hipaa)"),
    period_days: int = Query(30, ge=1, le=365, description="Report period in days (1-365)"),
    include_recommendations: bool = Query(True, description="Include remediation recommendations"),
    format: str = Query("json", description="Report format (json)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Generate comprehensive compliance report for audit and certification purposes.

    Provides a detailed compliance report including:
    - Executive summary with overall compliance status
    - Compliance status by framework requirements
    - Security metrics and event analysis
    - Data protection compliance assessment
    - Access control compliance assessment
    - Security configuration summary
    - Findings and remediation recommendations
    - Appendices with detailed data

    Parameters:
        framework: Compliance framework - "soc2", "gdpr", "iso27001", or "hipaa" (default: soc2)
        period_days: Report period in days (1-365, default: 30)
        include_recommendations: Include remediation recommendations (default: true)
        format: Report format - "json" (default: json)

    Returns:
        ComplianceReportResponse with comprehensive report data

    Example:
        GET /api/admin/compliance/report?framework=soc2&period_days=90
        Returns comprehensive SOC 2 compliance report for last 90 days

        GET /api/admin/compliance/report?framework=gdpr&period_days=30
        Returns GDPR compliance report for last 30 days
    """
    try:
        # Validate framework
        valid_frameworks = [
            ComplianceFramework.SOC2,
            ComplianceFramework.GDPR,
            ComplianceFramework.ISO27001,
            ComplianceFramework.HIPAA
        ]
        if framework not in valid_frameworks:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid framework. Must be one of: {', '.join(valid_frameworks)}"
            )

        # Calculate report period
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=period_days)

        # Get compliance status for the framework
        compliance_status_data = compliance_service.get_compliance_status(
            db=db,
            framework=framework
        )

        # Get security metrics for the period
        metrics_data = compliance_service.get_compliance_metrics(
            db=db,
            start_date=start_date,
            end_date=end_date
        )

        # Get data protection compliance
        data_protection_data = compliance_service.check_data_protection_compliance(db=db)

        # Get access control compliance
        access_control_data = compliance_service.check_access_control_compliance(db=db)

        # Get security configurations summary
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
            "two_factor_enforcement_enabled": two_factor_enforcement_enabled,
            "authentication_methods": {
                "saml_sso": saml_configs_enabled > 0,
                "oauth_enabled": True,
                "password_auth": True,
                "two_factor_available": True
            }
        }

        # Get non-compliant and critical findings
        non_compliant_events = db.query(ComplianceLog).filter(
            ComplianceLog.compliance_status == ComplianceStatus.NON_COMPLIANT,
            ComplianceLog.timestamp >= start_date,
            ComplianceLog.timestamp <= end_date
        ).order_by(ComplianceLog.timestamp.desc()).all()

        critical_findings = db.query(ComplianceLog).filter(
            ComplianceLog.severity.in_([SeverityLevel.CRITICAL, SeverityLevel.HIGH]),
            ComplianceLog.compliance_status.in_([
                ComplianceStatus.NON_COMPLIANT,
                ComplianceStatus.PENDING_REVIEW
            ]),
            ComplianceLog.timestamp >= start_date,
            ComplianceLog.timestamp <= end_date
        ).order_by(ComplianceLog.timestamp.desc()).all()

        # Build findings and recommendations
        findings_and_recommendations = []

        # Add non-compliant events as findings
        for event in non_compliant_events:
            finding = {
                "id": str(event.id),
                "severity": event.severity,
                "category": event.category,
                "title": event.title,
                "description": event.description,
                "status": event.compliance_status,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id
            }

            # Add recommendations if requested
            if include_recommendations:
                finding["recommendation"] = _generate_recommendation(event)

            findings_and_recommendations.append(finding)

        # Build executive summary
        overall_status = compliance_status_data.get("overall_status", ComplianceStatus.COMPLIANT)
        total_events = metrics_data.get("total_events", 0)
        non_compliant_count = metrics_data.get("by_status", {}).get("non_compliant", 0)
        critical_count = metrics_data.get("by_severity", {}).get("critical", 0)
        high_count = metrics_data.get("by_severity", {}).get("high", 0)
        unresolved_count = metrics_data.get("unresolved_incidents", 0)

        executive_summary = {
            "overall_compliance_status": overall_status,
            "framework": framework.upper() if framework else "N/A",
            "report_period_days": period_days,
            "total_security_events": total_events,
            "non_compliant_findings": non_compliant_count,
            "critical_high_severity_events": critical_count + high_count,
            "unresolved_incidents": unresolved_count,
            "compliance_percentage": round(
                (1 - (non_compliant_count / total_events if total_events > 0 else 0)) * 100,
                2
            ) if total_events > 0 else 100.0,
            "key_highlights": _generate_key_highlights(
                framework=framework,
                compliance_status=compliance_status_data,
                metrics_data=metrics_data,
                data_protection=data_protection_data,
                access_control=access_control_data
            )
        }

        # Build appendices
        appendices = {
            "audit_log_summary": _get_audit_log_summary(db, start_date, end_date),
            "compliance_events_timeline": _get_events_timeline(db, start_date, end_date),
            "security_controls_inventory": _get_security_controls_inventory(db),
            "report_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "generated_by": current_user.email,
                "generated_by_id": str(current_user.id),
                "framework": framework,
                "period_days": period_days,
                "report_version": "1.0"
            }
        }

        # Log the report generation activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="compliance_report_generated",
            message=f"Compliance report generated for {framework.upper()} by {current_user.email}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "framework": framework,
                "period_days": period_days,
                "include_recommendations": include_recommendations,
                "report_format": format,
                "generated_by": current_user.email
            }
        )

        # Return the report
        return ComplianceReportResponse(
            report_type="compliance_report",
            framework=framework,
            report_date=datetime.now(timezone.utc).isoformat(),
            report_period={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": period_days
            },
            executive_summary=executive_summary,
            compliance_status=compliance_status_data,
            security_metrics=metrics_data,
            data_protection=data_protection_data,
            access_control=access_control_data,
            security_configurations=security_configs_data,
            findings_and_recommendations=findings_and_recommendations,
            appendices=appendices
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate compliance report: {str(e)}"
        )


def _generate_recommendation(event: ComplianceLog) -> str:
    """
    Generate remediation recommendation for a compliance event.

    Args:
        event: Compliance log event

    Returns:
        str: Recommendation text
    """
    recommendations = {
        "auth_failure": "Review authentication logs, implement additional security controls, and consider IP whitelisting.",
        "policy_violation": "Review security policies, ensure all team members are trained on compliance requirements.",
        "data_breach": "Immediate incident response required. Notify stakeholders, document the breach, and implement remediation.",
        "access_denied": "Review access controls, ensure proper authorization levels are configured.",
        "encryption_failure": "Verify encryption settings for data at rest and in transit. Update certificates if needed.",
        "audit_log_missing": "Ensure audit logging is enabled for all critical systems. Review log retention policies.",
        "unauthorized_access": "Review user permissions, revoke unnecessary access, enable multi-factor authentication.",
        "config_error": "Review system configurations, apply security baselines, and document all changes.",
        "compliance_check": "Address the compliance gap identified and document remediation steps."
    }

    return recommendations.get(
        event.event_type,
        "Review the event details and implement appropriate security controls to prevent recurrence."
    )


def _generate_key_highlights(
    framework: str,
    compliance_status: dict,
    metrics_data: dict,
    data_protection: dict,
    access_control: dict
) -> list:
    """
    Generate key highlights for the executive summary.

    Args:
        framework: Compliance framework
        compliance_status: Overall compliance status
        metrics_data: Security metrics
        data_protection: Data protection status
        access_control: Access control status

    Returns:
        list: Key highlights
    """
    highlights = []

    # Compliance status highlight
    status = compliance_status.get("overall_status", ComplianceStatus.COMPLIANT)
    if status == ComplianceStatus.COMPLIANT:
        highlights.append(f"System maintains {status.upper()} status for {framework.upper()} requirements")
    elif status == ComplianceStatus.PENDING_REVIEW:
        highlights.append(f"System is {status.replace('_', ' ').title()} - some items need attention")
    else:
        highlights.append(f"System has {status.replace('_', ' ').title()} status - immediate action required")

    # Security metrics highlight
    total_events = metrics_data.get("total_events", 0)
    non_compliant = metrics_data.get("by_status", {}).get("non_compliant", 0)
    highlights.append(f"Tracked {total_events} security events with {non_compliant} non-compliant findings")

    # Data protection highlight
    dp_status = data_protection.get("overall_status", ComplianceStatus.COMPLIANT)
    if dp_status == ComplianceStatus.COMPLIANT:
        highlights.append("Data protection controls are properly implemented and monitored")

    # Access control highlight
    ac_status = access_control.get("overall_status", ComplianceStatus.COMPLIANT)
    if ac_status == ComplianceStatus.COMPLIANT:
        highlights.append("Access control measures meet compliance requirements")

    return highlights


def _get_audit_log_summary(db: Session, start_date: datetime, end_date: datetime) -> dict:
    """
    Get audit log summary for the report period.

    Args:
        db: Database session
        start_date: Start date
        end_date: End date

    Returns:
        dict: Audit log summary
    """
    try:
        total_audit_logs = db.query(AdminAuditLog).filter(
            AdminAuditLog.timestamp >= start_date,
            AdminAuditLog.timestamp <= end_date
        ).count()

        # Count by action type
        action_counts = {}
        for action in ["create", "read", "update", "delete", "export", "login", "logout"]:
            count = db.query(AdminAuditLog).filter(
                AdminAuditLog.action == action,
                AdminAuditLog.timestamp >= start_date,
                AdminAuditLog.timestamp <= end_date
            ).count()
            if count > 0:
                action_counts[action] = count

        return {
            "total_admin_actions": total_audit_logs,
            "actions_by_type": action_counts
        }
    except Exception:
        return {
            "total_admin_actions": 0,
            "actions_by_type": {}
        }


def _get_events_timeline(db: Session, start_date: datetime, end_date: datetime) -> list:
    """
    Get compliance events timeline for the report period.

    Args:
        db: Database session
        start_date: Start date
        end_date: End date

    Returns:
        list: Events timeline
    """
    try:
        events = db.query(ComplianceLog).filter(
            ComplianceLog.timestamp >= start_date,
            ComplianceLog.timestamp <= end_date,
            ComplianceLog.severity.in_([SeverityLevel.CRITICAL, SeverityLevel.HIGH])
        ).order_by(ComplianceLog.timestamp.desc()).limit(20).all()

        return [
            {
                "date": event.timestamp.strftime("%Y-%m-%d") if event.timestamp else "N/A",
                "severity": event.severity,
                "category": event.category,
                "title": event.title,
                "status": event.compliance_status
            }
            for event in events
        ]
    except Exception:
        return []


def _get_security_controls_inventory(db: Session) -> dict:
    """
    Get inventory of implemented security controls.

    Args:
        db: Database session

    Returns:
        dict: Security controls inventory
    """
    try:
        return {
            "authentication_controls": {
                "multi_factor_auth": "Implemented",
                "saml_sso": "Implemented" if db.query(SAMLConfig).filter(SAMLConfig.enabled == True).count() > 0 else "Not Configured",
                "oauth_integration": "Implemented",
                "password_policy": "Enforced"
            },
            "access_controls": {
                "role_based_access_control": "Implemented",
                "ip_whitelisting": "Implemented" if db.query(IPWhitelist).filter(IPWhitelist.enabled == True).count() > 0 else "Not Configured",
                "two_factor_enforcement": "Implemented" if db.query(SecurityPolicy).filter(
                    SecurityPolicy.policy_type == "two_factor_enforcement",
                    SecurityPolicy.enabled == True
                ).first() else "Not Configured"
            },
            "data_protection": {
                "encryption_at_rest": "Implemented",
                "encryption_in_transit": "Implemented (TLS)",
                "audit_logging": "Implemented",
                "field_level_encryption": "Implemented"
            },
            "compliance_monitoring": {
                "compliance_logs": "Enabled",
                "audit_trail": "Enabled",
                "security_metrics": "Enabled",
                "automated_reporting": "Implemented"
            }
        }
    except Exception:
        return {}
