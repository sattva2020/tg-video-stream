from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from api.auth import get_current_user
from database import get_db
from src.models.user import User
from src.models.organization import Organization
from src.services.activity_service import ActivityService
from src.services.organization_service import organization_service

router = APIRouter()


class OrganizationCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    custom_domain: Optional[str] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    custom_domain: Optional[str] = None
    is_active: Optional[bool] = None


class PaginatedOrganizationsResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: Optional[str]
    logo_url: Optional[str]
    primary_color: Optional[str]
    secondary_color: Optional[str]
    custom_domain: Optional[str]
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]


class AddMemberRequest(BaseModel):
    user_id: str
    role_id: Optional[str] = None


@router.post("", response_model=OrganizationResponse)
def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new organization.
    Requires admin or superadmin role.
    """
    # Check permissions - only admin/superadmin can create organizations
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can create organizations"
        )

    try:
        organization = organization_service.create_organization(
            db=db,
            name=org_data.name,
            slug=org_data.slug,
            logo_url=org_data.logo_url,
            primary_color=org_data.primary_color,
            secondary_color=org_data.secondary_color,
            custom_domain=org_data.custom_domain,
            created_by_user_id=str(current_user.id)
        )

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="organization_created",
            message=f"Создана новая организация: {organization.name}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": str(organization.id),
                "organization_name": organization.name,
                "organization_slug": organization.slug
            }
        )

        return OrganizationResponse(
            id=str(organization.id),
            name=organization.name,
            slug=organization.slug,
            logo_url=organization.logo_url,
            primary_color=organization.primary_color,
            secondary_color=organization.secondary_color,
            custom_domain=organization.custom_domain,
            is_active=organization.is_active,
            created_at=organization.created_at.isoformat() if organization.created_at else None,
            updated_at=organization.updated_at.isoformat() if organization.updated_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create organization: {str(e)}")


@router.get("", response_model=PaginatedOrganizationsResponse)
def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    include_inactive: bool = Query(False, description="Include inactive organizations"),
    search: Optional[str] = Query(None, description="Search by name or slug"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List organizations with pagination.
    Requires admin or superadmin role.
    """
    # Check permissions
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can list organizations"
        )

    query = db.query(Organization)

    # Apply filters
    if not include_inactive:
        query = query.filter(Organization.is_active == True)
    if search:
        query = query.filter(
            (Organization.name.ilike(f"%{search}%")) |
            (Organization.slug.ilike(f"%{search}%"))
        )

    # Get total count
    total = query.count()

    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size

    # Get paginated results
    organizations = query.order_by(Organization.created_at.desc()).offset(offset).limit(page_size).all()

    return PaginatedOrganizationsResponse(
        items=[{
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "logo_url": org.logo_url,
            "primary_color": org.primary_color,
            "secondary_color": org.secondary_color,
            "custom_domain": org.custom_domain,
            "is_active": org.is_active,
            "created_at": org.created_at.isoformat() if org.created_at else None,
            "updated_at": org.updated_at.isoformat() if org.updated_at else None
        } for org in organizations],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get organization by ID.
    Requires admin or superadmin role, or membership in the organization.
    """
    # Check permissions
    user_role = getattr(current_user, 'role', '').lower()
    user_org_id = str(getattr(current_user, 'organization_id', ''))

    # Admins/superadmins can access any organization
    # Regular users can only access their own organization
    if user_role not in ['admin', 'superadmin'] and user_org_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to access this organization"
        )

    try:
        organization = organization_service.get_organization(db, organization_id)
        return OrganizationResponse(
            id=str(organization.id),
            name=organization.name,
            slug=organization.slug,
            logo_url=organization.logo_url,
            primary_color=organization.primary_color,
            secondary_color=organization.secondary_color,
            custom_domain=organization.custom_domain,
            is_active=organization.is_active,
            created_at=organization.created_at.isoformat() if organization.created_at else None,
            updated_at=organization.updated_at.isoformat() if organization.updated_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get organization: {str(e)}")


@router.put("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: str,
    org_data: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update organization details.
    Requires admin or superadmin role.
    """
    # Check permissions
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can update organizations"
        )

    try:
        organization = organization_service.update_organization(
            db=db,
            organization_id=organization_id,
            name=org_data.name,
            logo_url=org_data.logo_url,
            primary_color=org_data.primary_color,
            secondary_color=org_data.secondary_color,
            custom_domain=org_data.custom_domain,
            is_active=org_data.is_active
        )

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="organization_updated",
            message=f"Организация обновлена: {organization.name}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": str(organization.id),
                "organization_name": organization.name
            }
        )

        return OrganizationResponse(
            id=str(organization.id),
            name=organization.name,
            slug=organization.slug,
            logo_url=organization.logo_url,
            primary_color=organization.primary_color,
            secondary_color=organization.secondary_color,
            custom_domain=organization.custom_domain,
            is_active=organization.is_active,
            created_at=organization.created_at.isoformat() if organization.created_at else None,
            updated_at=organization.updated_at.isoformat() if organization.updated_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update organization: {str(e)}")


@router.post("/{organization_id}/deactivate", response_model=OrganizationResponse)
def deactivate_organization(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Deactivate an organization (soft delete).
    Requires superadmin role.
    """
    # Check permissions - only superadmin can deactivate organizations
    user_role = getattr(current_user, 'role', '').lower()
    if user_role != 'superadmin':
        raise HTTPException(
            status_code=403,
            detail="Only superadmin can deactivate organizations"
        )

    try:
        organization = organization_service.deactivate_organization(db, organization_id)

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="organization_deactivated",
            message=f"Организация деактивирована: {organization.name}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": str(organization.id),
                "organization_name": organization.name
            }
        )

        return OrganizationResponse(
            id=str(organization.id),
            name=organization.name,
            slug=organization.slug,
            logo_url=organization.logo_url,
            primary_color=organization.primary_color,
            secondary_color=organization.secondary_color,
            custom_domain=organization.custom_domain,
            is_active=organization.is_active,
            created_at=organization.created_at.isoformat() if organization.created_at else None,
            updated_at=organization.updated_at.isoformat() if organization.updated_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to deactivate organization: {str(e)}")


@router.delete("/{organization_id}")
def delete_organization(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Permanently delete an organization.
    WARNING: This will cascade delete all related data.
    Requires superadmin role.
    """
    # Check permissions - only superadmin can delete organizations
    user_role = getattr(current_user, 'role', '').lower()
    if user_role != 'superadmin':
        raise HTTPException(
            status_code=403,
            detail="Only superadmin can delete organizations"
        )

    try:
        # Get organization details for logging before deletion
        organization = organization_service.get_organization(db, organization_id)
        org_name = organization.name

        organization_service.delete_organization(db, organization_id)

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="organization_deleted",
            message=f"Организация удалена: {org_name}",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": organization_id,
                "organization_name": org_name
            }
        )

        return {"status": "ok", "message": "Organization deleted", "id": organization_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete organization: {str(e)}")


@router.post("/{organization_id}/members")
def add_member(
    organization_id: str,
    member_data: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a user to an organization.
    Requires admin or superadmin role.
    """
    # Check permissions
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can add members to organizations"
        )

    try:
        org_user = organization_service.add_member(
            db=db,
            organization_id=organization_id,
            user_id=member_data.user_id,
            role_id=member_data.role_id,
            invited_by=str(current_user.id)
        )

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="organization_member_added",
            message=f"Пользователь добавлен в организацию",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": organization_id,
                "user_id": member_data.user_id,
                "role_id": member_data.role_id
            }
        )

        return {
            "status": "ok",
            "message": "Member added successfully",
            "organization_user_id": str(org_user.id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add member: {str(e)}")


@router.delete("/{organization_id}/members/{user_id}")
def remove_member(
    organization_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a user from an organization.
    Requires admin or superadmin role.
    """
    # Check permissions
    user_role = getattr(current_user, 'role', '').lower()
    if user_role not in ['admin', 'superadmin']:
        raise HTTPException(
            status_code=403,
            detail="Only admins can remove members from organizations"
        )

    try:
        organization_service.remove_member(
            db=db,
            organization_id=organization_id,
            user_id=user_id
        )

        # Log activity
        activity_service = ActivityService(db)
        activity_service.log_event(
            event_type="organization_member_removed",
            message=f"Пользователь удален из организации",
            user_id=current_user.id,
            user_email=current_user.email,
            details={
                "organization_id": organization_id,
                "user_id": user_id
            }
        )

        return {
            "status": "ok",
            "message": "Member removed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove member: {str(e)}")


@router.get("/{organization_id}/slug-available/{slug}")
def check_slug_availability(
    organization_id: str,
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check if a slug is available for an organization.
    """
    try:
        is_available = organization_service.is_slug_available(
            db=db,
            slug=slug,
            exclude_id=organization_id
        )
        return {"available": is_available}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check slug availability: {str(e)}")
