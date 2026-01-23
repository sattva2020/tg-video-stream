"""
Subscriptions API Endpoints
Spec: 022-multi-tenant-architecture-organization-management

API endpoints for managing organization subscriptions.
Provides CRUD operations for subscription plans, billing information, and subscription status.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from uuid import UUID

from api.auth import get_current_user
from database import get_db
from src.models.user import User
from src.models.subscription import PlanType, SubscriptionStatus
from src.services.activity_service import ActivityService
from src.services.subscription_service import get_subscription_service, SubscriptionService

router = APIRouter()


class SubscriptionCreate(BaseModel):
    """Request model for creating a subscription."""
    plan_type: PlanType
    billing_email: Optional[str] = None
    billing_address: Optional[Dict[str, Any]] = None
    trial_days: Optional[int] = None


class SubscriptionUpdate(BaseModel):
    """Request model for updating subscription details."""
    plan_type: Optional[PlanType] = None
    billing_email: Optional[str] = None
    billing_address: Optional[Dict[str, Any]] = None


class SubscriptionStatusUpdate(BaseModel):
    """Request model for updating subscription status."""
    status: SubscriptionStatus


class SubscriptionCancel(BaseModel):
    """Request model for canceling subscription."""
    at_period_end: bool = True


class SubscriptionResponse(BaseModel):
    """Response model for subscription details."""
    subscription_id: str
    organization_id: str
    plan_type: str
    status: str
    is_active: bool
    is_trial: bool
    trial_ends_at: Optional[str]
    trial_days_remaining: Optional[int]
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: bool
    billing_email: Optional[str]
    billing_address: Optional[Dict[str, Any]]
    created_at: Optional[str]
    updated_at: Optional[str]


class PaginatedSubscriptionsResponse(BaseModel):
    """Response model for paginated subscriptions list."""
    items: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/organizations/{organization_id}/subscription", response_model=SubscriptionResponse)
def get_subscription(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get subscription details for an organization.

    Args:
        organization_id: UUID of the organization

    Returns:
        SubscriptionResponse with subscription details

    Raises:
        HTTPException 403: If user lacks permission
        HTTPException 404: If subscription not found
        HTTPException 500: If server error occurs
    """
    # Check permissions
    user_role = getattr(current_user, 'role', '').lower()
    user_org_id = str(getattr(current_user, 'organization_id', ''))

    # Admins/superadmins can access any subscription
    # Regular users can only access their own organization's subscription
    if user_role not in ['admin', 'superadmin'] and user_org_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this subscription"
        )

    try:
        subscription_service = get_subscription_service(db)
        subscription_info = subscription_service.get_subscription_info(UUID(organization_id))

        return SubscriptionResponse(**subscription_info)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get subscription: {str(e)}"
        )


@router.put("/organizations/{organization_id}/subscription", response_model=SubscriptionResponse)
def update_subscription(
    organization_id: str,
    sub_data: SubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update subscription details (plan type, billing info).

    Args:
        organization_id: UUID of the organization
        sub_data: SubscriptionUpdate with fields to update

    Returns:
        Updated SubscriptionResponse

    Raises:
        HTTPException 403: If user lacks permission
        HTTPException 404: If subscription not found
        HTTPException 500: If server error occurs
    """
    # Check permissions - only admin/superadmin can update subscriptions
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can update subscriptions"
        )

    try:
        subscription_service = get_subscription_service(db)
        subscription = subscription_service.update_subscription(
            organization_id=UUID(organization_id),
            plan_type=sub_data.plan_type,
            billing_email=sub_data.billing_email,
            billing_address=sub_data.billing_address
        )

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="subscription_updated",
            message=f"Подписка обновлена для организации {organization_id}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": organization_id,
                "plan_type": sub_data.plan_type.value if sub_data.plan_type else None,
                "billing_email": sub_data.billing_email
            }
        )

        subscription_info = subscription_service.get_subscription_info(UUID(organization_id))
        return SubscriptionResponse(**subscription_info)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update subscription: {str(e)}"
        )


@router.post("/organizations/{organization_id}/subscription/cancel", response_model=SubscriptionResponse)
def cancel_subscription(
    organization_id: str,
    cancel_data: SubscriptionCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel an organization's subscription.

    Args:
        organization_id: UUID of the organization
        cancel_data: SubscriptionCancel with cancellation options

    Returns:
        Updated SubscriptionResponse

    Raises:
        HTTPException 403: If user lacks permission
        HTTPException 404: If subscription not found
        HTTPException 500: If server error occurs
    """
    # Check permissions - only admin/superadmin can cancel subscriptions
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can cancel subscriptions"
        )

    try:
        subscription_service = get_subscription_service(db)
        subscription = subscription_service.cancel_subscription(
            organization_id=UUID(organization_id),
            at_period_end=cancel_data.at_period_end
        )

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="subscription_canceled",
            message=f"Подписка отменена для организации {organization_id}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": organization_id,
                "at_period_end": cancel_data.at_period_end
            }
        )

        subscription_info = subscription_service.get_subscription_info(UUID(organization_id))
        return SubscriptionResponse(**subscription_info)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@router.post("/organizations/{organization_id}/subscription/activate", response_model=SubscriptionResponse)
def activate_subscription(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Activate or reactivate an organization's subscription.

    Args:
        organization_id: UUID of the organization

    Returns:
        Updated SubscriptionResponse

    Raises:
        HTTPException 403: If user lacks permission
        HTTPException 404: If subscription not found
        HTTPException 500: If server error occurs
    """
    # Check permissions - only admin/superadmin can activate subscriptions
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can activate subscriptions"
        )

    try:
        subscription_service = get_subscription_service(db)
        subscription = subscription_service.activate_subscription(UUID(organization_id))

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="subscription_activated",
            message=f"Подписка активирована для организации {organization_id}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": organization_id
            }
        )

        subscription_info = subscription_service.get_subscription_info(UUID(organization_id))
        return SubscriptionResponse(**subscription_info)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to activate subscription: {str(e)}"
        )


@router.put("/organizations/{organization_id}/subscription/status", response_model=SubscriptionResponse)
def update_subscription_status(
    organization_id: str,
    status_data: SubscriptionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the status of an organization's subscription.

    Args:
        organization_id: UUID of the organization
        status_data: SubscriptionStatusUpdate with new status

    Returns:
        Updated SubscriptionResponse

    Raises:
        HTTPException 403: If user lacks permission
        HTTPException 404: If subscription not found
        HTTPException 500: If server error occurs
    """
    # Check permissions - only admin/superadmin can update subscription status
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can update subscription status"
        )

    try:
        subscription_service = get_subscription_service(db)
        subscription = subscription_service.update_subscription_status(
            organization_id=UUID(organization_id),
            new_status=status_data.status
        )

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="subscription_status_updated",
            message=f"Статус подписки изменен на {status_data.status.value} для организации {organization_id}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": organization_id,
                "old_status": subscription.status if subscription else None,
                "new_status": status_data.status.value
            }
        )

        subscription_info = subscription_service.get_subscription_info(UUID(organization_id))
        return SubscriptionResponse(**subscription_info)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update subscription status: {str(e)}"
        )


@router.get("/subscriptions", response_model=PaginatedSubscriptionsResponse)
def list_subscriptions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[SubscriptionStatus] = Query(None, description="Filter by status"),
    plan: Optional[PlanType] = Query(None, description="Filter by plan type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all subscriptions with pagination and optional filtering.

    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        status: Optional filter by subscription status
        plan: Optional filter by plan type

    Returns:
        PaginatedSubscriptionsResponse with list of subscriptions

    Raises:
        HTTPException 403: If user lacks permission
        HTTPException 500: If server error occurs
    """
    # Check permissions - only admin/superadmin can list all subscriptions
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can list subscriptions"
        )

    try:
        subscription_service = get_subscription_service(db)

        # Calculate offset
        skip = (page - 1) * page_size

        # Get subscriptions with filters
        subscriptions = subscription_service.list_subscriptions(
            skip=skip,
            limit=page_size,
            status_filter=status,
            plan_filter=plan
        )

        # Get total count for pagination
        from src.models.subscription import Subscription
        total_query = db.query(Subscription)

        if status:
            total_query = total_query.filter(Subscription.status == status.value)
        if plan:
            total_query = total_query.filter(Subscription.plan_type == plan.value)

        total = total_query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        # Format response items
        items = []
        for sub in subscriptions:
            items.append({
                "subscription_id": str(sub.id),
                "organization_id": str(sub.organization_id),
                "plan_type": sub.plan_type,
                "status": sub.status,
                "is_active": sub.is_active,
                "is_trial": sub.is_trial,
                "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
                "trial_days_remaining": sub.trial_days_remaining,
                "current_period_start": sub.current_period_start.isoformat() if sub.current_period_start else None,
                "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
                "cancel_at_period_end": sub.cancel_at_period_end,
                "billing_email": sub.billing_email,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
                "updated_at": sub.updated_at.isoformat() if sub.updated_at else None
            })

        return PaginatedSubscriptionsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list subscriptions: {str(e)}"
        )


@router.get("/organizations/{organization_id}/subscription/check-access")
def check_subscription_access(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if an organization has active subscription access.

    Args:
        organization_id: UUID of the organization

    Returns:
        Dict with 'has_access' boolean and additional details

    Raises:
        HTTPException 403: If user lacks permission
        HTTPException 500: If server error occurs
    """
    # Check permissions
    user_role = getattr(current_user, 'role', '').lower()
    user_org_id = str(getattr(current_user, 'organization_id', ''))

    # Admins/superadmins can check any organization
    # Regular users can only check their own organization
    if user_role not in ['admin', 'superadmin'] and user_org_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to check this subscription"
        )

    try:
        subscription_service = get_subscription_service(db)
        has_access = subscription_service.check_subscription_access(UUID(organization_id))

        # Get additional details
        try:
            subscription_info = subscription_service.get_subscription_info(UUID(organization_id))
            return {
                "has_access": has_access,
                "subscription": subscription_info
            }
        except HTTPException:
            # No subscription found
            return {
                "has_access": False,
                "subscription": None
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check subscription access: {str(e)}"
        )
