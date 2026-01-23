"""
Audit Log Export Endpoints for Compliance Reporting
Spec: 025-advanced-security-compliance-features

Provides audit log export functionality in CSV/JSON formats for compliance reporting.
Admin-only access for exporting administrative action logs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
import csv
import json
import io

from api.auth import require_admin
from src.models.user import User
from src.models.audit_log import AdminAuditLog
from database import get_db
from src.services.activity_service import ActivityService
from src.lib.audit import audit_export

router = APIRouter()


class AuditLogExportResponse(BaseModel):
    """Schema for audit log export response (JSON format)."""
    export_date: str
    export_type: str = "audit_logs"
    format: str
    total_records: int
    date_range: dict
    logs: List[dict]


@router.get("/audit-logs/export")
@audit_export("audit_log")
async def export_audit_logs(
    format: str = Query("json", description="Export format: csv or json"),
    start_date: Optional[str] = Query(None, description="Start date (ISO 8601 format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO 8601 format)"),
    user_id: Optional[UUID] = Query(None, description="Filter logs by user"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of records to export"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Export audit logs for compliance reporting in CSV or JSON format.

    Provides comprehensive audit trail export for SOC 2, GDPR, ISO 27001, and HIPAA compliance.
    Supports filtering by date range, user, action, and resource type.

    Parameters:
        format: Export format - "csv" or "json" (default: json)
        start_date: Optional start date in ISO 8601 format (e.g., 2024-01-01T00:00:00Z)
        end_date: Optional end date in ISO 8601 format
        user_id: Optional UUID to filter logs for specific user
        action: Optional action filter (create, read, update, delete, export, login, logout, etc.)
        resource_type: Optional resource type filter (user, channel, track, playlist, etc.)
        limit: Maximum number of records to export (1-10000, default: 1000)

    Returns:
        CSV file download or JSON response with audit log data

    Example:
        GET /api/admin/audit-logs/export?format=csv&start_date=2024-01-01T00:00:00Z
        Returns CSV file download

        GET /api/admin/audit-logs/export?format=json&action=delete&limit=500
        Returns JSON with delete action logs
    """
    try:
        # Build query
        query = db.query(AdminAuditLog)

        # Parse and apply date range filter
        start_dt = None
        end_dt = None

        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(AdminAuditLog.timestamp >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid start_date format. Use ISO 8601 format (e.g., 2024-01-01T00:00:00Z)"
                )

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(AdminAuditLog.timestamp <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid end_date format. Use ISO 8601 format (e.g., 2024-01-31T23:59:59Z)"
                )

        # Filter by user if specified
        if user_id:
            query = query.filter(AdminAuditLog.user_id == user_id)

        # Filter by action if specified
        if action:
            query = query.filter(AdminAuditLog.action == action.lower())

        # Filter by resource type if specified
        if resource_type:
            query = query.filter(AdminAuditLog.resource_type == resource_type.lower())

        # Order by timestamp descending and limit
        logs = query.order_by(AdminAuditLog.timestamp.desc()).limit(limit).all()

        # Get actual date range from results
        if logs:
            actual_start = logs[-1].timestamp if len(logs) > 0 else None
            actual_end = logs[0].timestamp if len(logs) > 0 else None
        else:
            actual_start = None
            actual_end = None

        # Export based on format
        if format.lower() == "csv":
            return _export_audit_logs_as_csv(
                logs=logs,
                start_date=start_dt or actual_start,
                end_date=end_dt or actual_end,
                current_user=current_user,
                db=db
            )
        elif format.lower() == "json":
            return _export_audit_logs_as_json(
                logs=logs,
                start_date=start_dt or actual_start,
                end_date=end_dt or actual_end,
                current_user=current_user,
                db=db
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid format. Must be 'csv' or 'json'"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export audit logs: {str(e)}"
        )


def _export_audit_logs_as_csv(
    logs: List[AdminAuditLog],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    current_user: User,
    db: Session
) -> StreamingResponse:
    """
    Export audit logs as CSV file.

    Args:
        logs: List of audit log entries
        start_date: Start date of the export range
        end_date: End date of the export range
        current_user: Current admin user
        db: Database session

    Returns:
        StreamingResponse with CSV file
    """
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    header = [
        "Timestamp",
        "User ID",
        "User Email",
        "Action",
        "Resource Type",
        "Resource ID",
        "IP Address",
        "User Agent",
        "Details"
    ]
    writer.writerow(header)

    # Write data rows
    for log in logs:
        # Parse details JSON if available
        details_dict = {}
        if log.details:
            try:
                details_dict = json.loads(log.details)
            except json.JSONDecodeError:
                details_dict = {"raw": log.details}

        user_email = details_dict.get("user_email", "")
        # Get user email from relationship if not in details
        if not user_email and log.user:
            user_email = getattr(log.user, 'email', '')

        row = [
            log.timestamp.isoformat() if log.timestamp else "",
            str(log.user_id) if log.user_id else "",
            user_email,
            log.action or "",
            log.resource_type or "",
            log.resource_id or "",
            log.ip_address or "",
            log.user_agent or "",
            log.details or ""
        ]
        writer.writerow(row)

    # Prepare CSV content
    csv_content = output.getvalue()
    output.close()

    # Log the export activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="audit_log_export",
        message=f"Audit logs exported (CSV) by {current_user.email}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "export_format": "csv",
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "record_count": len(logs),
            "exported_by": current_user.email
        }
    )

    # Generate filename with timestamp
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    # Return CSV file as streaming response
    return StreamingResponse(
        io.BytesIO(csv_content.encode('utf-8')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


def _export_audit_logs_as_json(
    logs: List[AdminAuditLog],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    current_user: User,
    db: Session
) -> AuditLogExportResponse:
    """
    Export audit logs as JSON.

    Args:
        logs: List of audit log entries
        start_date: Start date of the export range
        end_date: End date of the export range
        current_user: Current admin user
        db: Database session

    Returns:
        AuditLogExportResponse with log data
    """
    # Export log data
    exported_logs = []
    for log in logs:
        # Parse details JSON if available
        details_dict = {}
        if log.details:
            try:
                details_dict = json.loads(log.details)
            except json.JSONDecodeError:
                details_dict = {"raw": log.details}

        user_email = details_dict.get("user_email", "")
        # Get user email from relationship if not in details
        if not user_email and log.user:
            user_email = getattr(log.user, 'email', '')

        exported_logs.append({
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "user_id": str(log.user_id) if log.user_id else None,
            "user_email": user_email,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "details": details_dict
        })

    # Log the export activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="audit_log_export",
        message=f"Audit logs exported (JSON) by {current_user.email}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "export_format": "json",
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "record_count": len(exported_logs),
            "exported_by": current_user.email
        }
    )

    return AuditLogExportResponse(
        export_date=datetime.utcnow().isoformat(),
        export_type="audit_logs",
        format="json",
        total_records=len(exported_logs),
        date_range={
            "start": start_date.isoformat() if start_date else None,
            "end": end_date.isoformat() if end_date else None
        },
        logs=exported_logs
    )
