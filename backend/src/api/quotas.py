from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID

from api.auth import get_current_user
from database import get_db
from src.models.user import User
from src.models.organization import Organization
from src.models.organization_quota import ResourceQuota, QuotaType
from src.services.activity_service import ActivityService
from src.services.quota_service import get_quota_service, QuotaService

router = APIRouter()


class QuotaResponse(BaseModel):
    quota_type: str
    limit: Optional[int]
    current_usage: int
    remaining: Optional[int]
    usage_percentage: float
    is_exceeded: bool
    period: Optional[str]
    reset_at: Optional[str]


class QuotaUpdate(BaseModel):
    limit: int
    period: Optional[str] = None


class QuotasListResponse(BaseModel):
    organization_id: str
    quotas: List[QuotaResponse]


class QuotaUsageResponse(BaseModel):
    quota_type: str
    limit: Optional[int]
    current_usage: int
    remaining: Optional[int]
    usage_percentage: float
    is_exceeded: bool
    reset_at: Optional[str]


@router.get("/organizations/{org_id}/quotas", response_model=QuotasListResponse)
def get_organization_quotas(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all quotas for an organization.
    Requires admin or superadmin role, or organization member.
    """
    # Check if organization exists
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    # Check permissions - admin/superadmin can view any org, regular users can only view their own
    user_role = getattr(current_user, 'role', '').lower()
    user_org_id = getattr(current_user, 'organization_id', None)

    if user_role not in ['admin', 'superadmin'] and user_org_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view quotas for this organization"
        )

    try:
        quota_service = get_quota_service(db)
        quotas_data = quota_service.get_all_quotas(org_id)

        quotas_response = []
        for quota in quotas_data:
            quotas_response.append(QuotaResponse(
                quota_type=quota['quota_type'],
                limit=quota['limit'],
                current_usage=quota['current_usage'],
                remaining=quota['remaining'],
                usage_percentage=quota['usage_percentage'],
                is_exceeded=quota['is_exceeded'],
                period=quota.get('period'),
                reset_at=quota.get('reset_at')
            ))

        return QuotasListResponse(
            organization_id=str(org_id),
            quotas=quotas_response
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quotas: {str(e)}")


@router.get("/organizations/{org_id}/quotas/{quota_type}", response_model=QuotaUsageResponse)
def get_quota_usage(
    org_id: UUID,
    quota_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get usage information for a specific quota type.
    Requires admin or superadmin role, or organization member.
    """
    # Check if organization exists
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    # Check permissions
    user_role = getattr(current_user, 'role', '').lower()
    user_org_id = getattr(current_user, 'organization_id', None)

    if user_role not in ['admin', 'superadmin'] and user_org_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to view quotas for this organization"
        )

    # Validate quota type
    try:
        quota_type_enum = QuotaType(quota_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid quota type. Must be one of: {', '.join([q.value for q in QuotaType])}"
        )

    try:
        quota_service = get_quota_service(db)
        usage_data = quota_service.get_quota_usage(org_id, quota_type_enum)

        return QuotaUsageResponse(
            quota_type=usage_data['quota_type'],
            limit=usage_data['limit'],
            current_usage=usage_data['current_usage'],
            remaining=usage_data['remaining'],
            usage_percentage=usage_data['usage_percentage'],
            is_exceeded=usage_data['is_exceeded'],
            reset_at=usage_data['reset_at']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quota usage: {str(e)}")


@router.put("/organizations/{org_id}/quotas/{quota_type}")
def update_quota(
    org_id: UUID,
    quota_type: str,
    quota_update: QuotaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update quota limit for an organization.
    Requires admin or superadmin role.
    """
    # Check permissions - only admin/superadmin can update quotas
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can update quotas"
        )

    # Check if organization exists
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    # Validate quota type
    try:
        quota_type_enum = QuotaType(quota_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid quota type. Must be one of: {', '.join([q.value for q in QuotaType])}"
        )

    # Validate limit
    if quota_update.limit < 0:
        raise HTTPException(
            status_code=400,
            detail="Limit must be non-negative"
        )

    # Validate period if provided
    valid_periods = ['hourly', 'daily', 'monthly', None]
    if quota_update.period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Must be one of: {', '.join([p for p in valid_periods if p])}"
        )

    try:
        # Find or create quota
        quota = db.query(ResourceQuota).filter(
            ResourceQuota.organization_id == org_id,
            ResourceQuota.quota_type == quota_type_enum.value
        ).first()

        if quota:
            old_limit = quota.limit
            quota.limit = quota_update.limit
            if quota_update.period is not None:
                quota.period = quota_update.period
        else:
            old_limit = None
            quota = ResourceQuota(
                organization_id=org_id,
                quota_type=quota_type_enum.value,
                limit=quota_update.limit,
                current_usage=0,
                period=quota_update.period
            )
            db.add(quota)

        db.commit()
        db.refresh(quota)

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="quota_updated",
            message=f"Обновлена квота {quota_type_enum.value} для организации {organization.name}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": str(org_id),
                "organization_name": organization.name,
                "quota_type": quota_type_enum.value,
                "old_limit": old_limit,
                "new_limit": quota_update.limit,
                "period": quota_update.period
            }
        )

        return {
            "status": "ok",
            "organization_id": str(org_id),
            "quota_type": quota_type_enum.value,
            "limit": quota.limit,
            "current_usage": quota.current_usage,
            "period": quota.period
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update quota: {str(e)}")


@router.post("/organizations/{org_id}/quotas/{quota_type}/reset")
def reset_quota(
    org_id: UUID,
    quota_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reset current usage for a quota.
    Requires admin or superadmin role.
    """
    # Check permissions - only admin/superadmin can reset quotas
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can reset quotas"
        )

    # Check if organization exists
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    # Validate quota type
    try:
        quota_type_enum = QuotaType(quota_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid quota type. Must be one of: {', '.join([q.value for q in QuotaType])}"
        )

    try:
        quota = db.query(ResourceQuota).filter(
            ResourceQuota.organization_id == org_id,
            ResourceQuota.quota_type == quota_type_enum.value
        ).first()

        if not quota:
            raise HTTPException(
                status_code=404,
                detail=f"Quota {quota_type_enum.value} not found for this organization"
            )

        old_usage = quota.current_usage
        quota.reset_usage()
        db.commit()
        db.refresh(quota)

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="quota_reset",
            message=f"Сброслена квота {quota_type_enum.value} для организации {organization.name}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": str(org_id),
                "organization_name": organization.name,
                "quota_type": quota_type_enum.value,
                "old_usage": old_usage,
                "new_usage": 0
            }
        )

        return {
            "status": "ok",
            "organization_id": str(org_id),
            "quota_type": quota_type_enum.value,
            "current_usage": quota.current_usage,
            "limit": quota.limit
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reset quota: {str(e)}")


@router.get("/organizations/{org_id}/quotas/check/{quota_type}")
def check_quota(
    org_id: UUID,
    quota_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if a quota is exceeded.
    Requires admin or superadmin role, or organization member.
    """
    # Check if organization exists
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=404,
            detail="Organization not found"
        )

    # Check permissions
    user_role = getattr(current_user, 'role', '').lower()
    user_org_id = getattr(current_user, 'organization_id', None)

    if user_role not in ['admin', 'superadmin'] and user_org_id != org_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to check quotas for this organization"
        )

    # Validate quota type
    try:
        quota_type_enum = QuotaType(quota_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid quota type. Must be one of: {', '.join([q.value for q in QuotaType])}"
        )

    try:
        quota_service = get_quota_service(db)
        is_available = quota_service.check_quota(org_id, quota_type_enum)

        quota = db.query(ResourceQuota).filter(
            ResourceQuota.organization_id == org_id,
            ResourceQuota.quota_type == quota_type_enum.value
        ).first()

        return {
            "status": "ok",
            "organization_id": str(org_id),
            "quota_type": quota_type_enum.value,
            "available": is_available,
            "limit": quota.limit if quota else None,
            "current_usage": quota.current_usage if quota else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check quota: {str(e)}")
