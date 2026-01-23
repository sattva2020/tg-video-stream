"""
IP Whitelist Management Endpoints
Spec: 025-advanced-security-compliance-features

CRUD endpoints for managing IP whitelist entries.
Admin-only access.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from api.auth import require_admin
from src.models.user import User
from src.models.ip_whitelist import IPWhitelist
from database import get_db
from src.services.activity_service import ActivityService
from src.services.ip_whitelist_service import ip_whitelist_service

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class IPWhitelistCreate(BaseModel):
    """Schema for creating a new IP whitelist entry."""
    cidr: str
    description: Optional[str] = None
    is_active: bool = True


class IPWhitelistUpdate(BaseModel):
    """Schema for updating an existing IP whitelist entry."""
    description: Optional[str] = None
    is_active: Optional[bool] = None


class IPWhitelistResponse(BaseModel):
    """Schema for IP whitelist entry response."""
    id: str
    cidr: str
    description: Optional[str] = None
    is_active: bool
    is_ipv4: bool
    is_ipv6: bool
    created_by_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class IPWhitelistInfo(BaseModel):
    """Schema for IP whitelist summary information."""
    total_entries: int
    active_entries: int
    inactive_entries: int
    ipv4_entries: int
    ipv6_entries: int


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("/entries", response_model=List[IPWhitelistResponse])
def list_ip_whitelist_entries(
    active_only: bool = Query(False, description="Filter only active entries"),
    ipv4_only: bool = Query(False, description="Filter only IPv4 entries"),
    ipv6_only: bool = Query(False, description="Filter only IPv6 entries"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List all IP whitelist entries.

    Returns a list of all IP whitelist entries with optional filtering.
    """
    include_ipv4 = not ipv6_only
    include_ipv6 = not ipv4_only

    entries = ip_whitelist_service.get_all_whitelist_entries(
        db,
        active_only=active_only,
        include_ipv4=include_ipv4,
        include_ipv6=include_ipv6
    )

    return [
        IPWhitelistResponse(
            id=str(entry.id),
            cidr=entry.cidr,
            description=entry.description,
            is_active=entry.is_active,
            is_ipv4=entry.is_ipv4,
            is_ipv6=entry.is_ipv6,
            created_by_id=str(entry.created_by_id) if entry.created_by_id else None,
            created_at=entry.created_at.isoformat() if entry.created_at else None,
            updated_at=entry.updated_at.isoformat() if entry.updated_at else None,
        )
        for entry in entries
    ]


@router.get("/entries/info", response_model=IPWhitelistInfo)
def get_ip_whitelist_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get summary information about the IP whitelist.

    Returns statistics about total, active, inactive, IPv4, and IPv6 entries.
    """
    info = ip_whitelist_service.get_whitelist_info(db)
    return IPWhitelistInfo(**info)


@router.get("/entries/{entry_id}", response_model=IPWhitelistResponse)
def get_ip_whitelist_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get a specific IP whitelist entry by ID.
    """
    entry = ip_whitelist_service.get_whitelist_entry(db, str(entry_id))

    return IPWhitelistResponse(
        id=str(entry.id),
        cidr=entry.cidr,
        description=entry.description,
        is_active=entry.is_active,
        is_ipv4=entry.is_ipv4,
        is_ipv6=entry.is_ipv6,
        created_by_id=str(entry.created_by_id) if entry.created_by_id else None,
        created_at=entry.created_at.isoformat() if entry.created_at else None,
        updated_at=entry.updated_at.isoformat() if entry.updated_at else None,
    )


@router.post("/entries", response_model=IPWhitelistResponse, status_code=201)
def create_ip_whitelist_entry(
    entry_data: IPWhitelistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new IP whitelist entry.

    Creates a new IP address or CIDR range whitelist entry.
    """
    # Normalize CIDR before creating
    try:
        normalized_cidr = ip_whitelist_service.normalize_cidr(entry_data.cidr)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CIDR format: {str(e)}"
        )

    # Create new whitelist entry
    new_entry = ip_whitelist_service.create_whitelist_entry(
        db,
        cidr=normalized_cidr,
        description=entry_data.description,
        created_by=current_user,
        is_active=entry_data.is_active
    )

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="ip_whitelist_created",
        message=f"IP whitelist entry created: {new_entry.cidr}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "entry_id": str(new_entry.id),
            "cidr": new_entry.cidr,
            "description": new_entry.description,
            "is_active": new_entry.is_active
        }
    )

    return IPWhitelistResponse(
        id=str(new_entry.id),
        cidr=new_entry.cidr,
        description=new_entry.description,
        is_active=new_entry.is_active,
        is_ipv4=new_entry.is_ipv4,
        is_ipv6=new_entry.is_ipv6,
        created_by_id=str(new_entry.created_by_id) if new_entry.created_by_id else None,
        created_at=new_entry.created_at.isoformat() if new_entry.created_at else None,
        updated_at=new_entry.updated_at.isoformat() if new_entry.updated_at else None,
    )


@router.put("/entries/{entry_id}", response_model=IPWhitelistResponse)
def update_ip_whitelist_entry(
    entry_id: UUID,
    entry_data: IPWhitelistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update an existing IP whitelist entry.

    Allows updating description and active status.
    """
    # Get current entry for logging changes
    entry = ip_whitelist_service.get_whitelist_entry(db, str(entry_id))

    # Track changes for logging
    changes = {}

    # Update entry
    updated_entry = ip_whitelist_service.update_whitelist_entry(
        db,
        str(entry_id),
        description=entry_data.description,
        is_active=entry_data.is_active
    )

    # Track changes
    if entry_data.description is not None and entry.description != entry_data.description:
        changes["old_description"] = entry.description
        changes["new_description"] = entry_data.description

    if entry_data.is_active is not None and entry.is_active != entry_data.is_active:
        changes["old_is_active"] = entry.is_active
        changes["new_is_active"] = entry_data.is_active

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="ip_whitelist_updated",
        message=f"IP whitelist entry updated: {updated_entry.cidr}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "entry_id": str(updated_entry.id),
            "cidr": updated_entry.cidr,
            "changes": changes
        }
    )

    return IPWhitelistResponse(
        id=str(updated_entry.id),
        cidr=updated_entry.cidr,
        description=updated_entry.description,
        is_active=updated_entry.is_active,
        is_ipv4=updated_entry.is_ipv4,
        is_ipv6=updated_entry.is_ipv6,
        created_by_id=str(updated_entry.created_by_id) if updated_entry.created_by_id else None,
        created_at=updated_entry.created_at.isoformat() if updated_entry.created_at else None,
        updated_at=updated_entry.updated_at.isoformat() if updated_entry.updated_at else None,
    )


@router.delete("/entries/{entry_id}")
def delete_ip_whitelist_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete an IP whitelist entry.
    """
    # Get entry for logging
    entry = ip_whitelist_service.get_whitelist_entry(db, str(entry_id))
    entry_cidr = entry.cidr

    # Delete entry
    ip_whitelist_service.delete_whitelist_entry(db, str(entry_id))

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="ip_whitelist_deleted",
        message=f"IP whitelist entry deleted: {entry_cidr}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "entry_id": str(entry_id),
            "cidr": entry_cidr
        }
    )

    return {
        "status": "ok",
        "message": "IP whitelist entry deleted",
        "id": str(entry_id)
    }


@router.post("/entries/{entry_id}/activate")
def activate_ip_whitelist_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Activate an IP whitelist entry.
    """
    entry = ip_whitelist_service.get_whitelist_entry(db, str(entry_id))

    if entry.is_active:
        return {"status": "ok", "message": "Entry already active", "id": str(entry.id)}

    activated_entry = ip_whitelist_service.activate_whitelist_entry(db, str(entry_id))

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="ip_whitelist_activated",
        message=f"IP whitelist entry activated: {activated_entry.cidr}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "entry_id": str(activated_entry.id),
            "cidr": activated_entry.cidr
        }
    )

    return {
        "status": "ok",
        "message": "IP whitelist entry activated",
        "id": str(activated_entry.id),
        "is_active": True
    }


@router.post("/entries/{entry_id}/deactivate")
def deactivate_ip_whitelist_entry(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Deactivate an IP whitelist entry.
    """
    entry = ip_whitelist_service.get_whitelist_entry(db, str(entry_id))

    if not entry.is_active:
        return {"status": "ok", "message": "Entry already inactive", "id": str(entry.id)}

    deactivated_entry = ip_whitelist_service.deactivate_whitelist_entry(db, str(entry_id))

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="ip_whitelist_deactivated",
        message=f"IP whitelist entry deactivated: {deactivated_entry.cidr}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "entry_id": str(deactivated_entry.id),
            "cidr": deactivated_entry.cidr
        }
    )

    return {
        "status": "ok",
        "message": "IP whitelist entry deactivated",
        "id": str(deactivated_entry.id),
        "is_active": False
    }


@router.post("/check")
def check_ip_whitelist(
    ip: str = Query(..., description="IP address to check"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Check if an IP address is whitelisted.

    Useful for testing and verification purposes.
    """
    is_whitelisted = ip_whitelist_service.is_ip_whitelisted(db, ip)

    return {
        "ip": ip,
        "is_whitelisted": is_whitelisted
    }
