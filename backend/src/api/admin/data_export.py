"""
Data Export Endpoints for GDPR Compliance
Spec: 025-advanced-security-compliance-features

Provides data export functionality for GDPR right to data portability.
Admin-only access for exporting user data in portable formats.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from api.auth import require_admin
from src.models.user import User
from database import get_db
from src.services.activity_service import ActivityService

router = APIRouter()


class UserDataExport(BaseModel):
    """Schema for user data export response."""
    export_date: str
    export_type: str = "user_data"
    users: List[dict]


@router.get("/data-export", response_model=UserDataExport)
@audit_export("user")
async def export_user_data(
    user_id: Optional[UUID] = Query(None, description="Export specific user data (omit for all users)"),
    include_sensitive: bool = Query(False, description="Include sensitive fields like hashed_password, totp_secret"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Export user data for GDPR right to data portability.

    Exports user account data in a structured JSON format.
    This endpoint supports GDPR compliance by allowing data portability.

    Parameters:
        user_id: Optional UUID of specific user to export. If omitted, exports all users.
        include_sensitive: Include sensitive fields (passwords, 2FA secrets). Use with caution.

    Returns:
        UserDataExport with user data in portable format

    Example:
        GET /api/admin/data-export
        Returns all non-sensitive user data

        GET /api/admin/data-export?user_id=123e4567-e89b-12d3-a456-426614174000
        Returns specific user data

        GET /api/admin/data-export?include_sensitive=true
        Returns all data including sensitive fields
    """
    try:
        # Build query
        query = db.query(User)

        # Filter by user_id if provided
        if user_id:
            query = query.filter(User.id == user_id)

        users = query.order_by(User.created_at.desc()).all()

        # Export user data
        exported_users = []
        for user in users:
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "status": user.status,
                "email_verified": user.email_verified,
                "profile_picture_url": user.profile_picture_url,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                # OAuth identifiers
                "google_id": user.google_id,
                "telegram_id": user.telegram_id,
                "telegram_username": user.telegram_username,
                # SAML identifiers
                "saml_name_id": user.saml_name_id,
                "saml_config_id": str(user.saml_config_id) if user.saml_config_id else None,
            }

            # Include sensitive fields only if requested
            if include_sensitive:
                user_data.update({
                    "hashed_password": user.hashed_password,
                    "totp_secret": user.totp_secret,
                    "totp_enabled": user.totp_enabled,
                })

            exported_users.append(user_data)

        # Log the export activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="data_export",
            message=f"User data exported by {current_user.email}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "export_type": "user_data",
                "user_id": str(user_id) if user_id else "all_users",
                "include_sensitive": include_sensitive,
                "user_count": len(exported_users),
                "exported_by": current_user.email
            }
        )

        return UserDataExport(
            export_date=datetime.utcnow().isoformat(),
            export_type="user_data",
            users=exported_users
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export data: {str(e)}"
        )


@router.get("/data-export/audit-logs")
@audit_export("audit_log")
async def export_audit_logs(
    user_id: Optional[UUID] = Query(None, description="Filter logs by user"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records to export"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Export audit logs for compliance reporting.

    Exports audit log entries for compliance and security monitoring purposes.

    Parameters:
        user_id: Optional UUID to filter logs for specific user
        limit: Maximum number of records (1-10000)

    Returns:
        JSON response with audit log data
    """
    try:
        from src.models.audit_log import AuditLog

        # Build query
        query = db.query(AuditLog)

        # Filter by user if specified
        if user_id:
            query = query.filter(AuditLog.user_id == str(user_id))

        # Get recent logs
        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()

        # Export log data
        exported_logs = []
        for log in logs:
            exported_logs.append({
                "id": str(log.id),
                "user_id": log.user_id,
                "user_email": log.user_email,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "success": log.success,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            })

        # Log the export activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="audit_log_export",
            message=f"Audit logs exported by {current_user.email}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "export_type": "audit_logs",
                "user_id": str(user_id) if user_id else "all_users",
                "limit": limit,
                "record_count": len(exported_logs),
                "exported_by": current_user.email
            }
        )

        return {
            "export_date": datetime.utcnow().isoformat(),
            "export_type": "audit_logs",
            "total_records": len(exported_logs),
            "logs": exported_logs
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export audit logs: {str(e)}"
        )
