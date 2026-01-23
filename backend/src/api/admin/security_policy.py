"""
Security Policy Management Endpoints
Spec: 025-advanced-security-compliance-features

CRUD endpoints for managing security policies including 2FA enforcement rules.
Admin-only access.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from api.auth import require_admin
from src.models.user import User
from src.models.security_policy import SecurityPolicy, PolicyType, EnforcementLevel
from database import get_db
from src.services.activity_service import ActivityService

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class SecurityPolicyCreate(BaseModel):
    """Schema for creating a new security policy."""
    name: str
    policy_type: str = PolicyType.TWO_FACTOR_ENFORCEMENT.value
    enabled: bool = False

    # Enforcement settings
    enforcement_level: str = EnforcementLevel.OPTIONAL.value
    affected_roles: Optional[List[str]] = None  # None = all roles

    # 2FA-specific settings
    grace_period_hours: Optional[int] = 0
    allow_exempt_alternative_auth: bool = False

    # Additional policy-specific configuration
    policy_config: Optional[dict] = None
    description: Optional[str] = None


class SecurityPolicyUpdate(BaseModel):
    """Schema for updating an existing security policy."""
    name: Optional[str] = None
    policy_type: Optional[str] = None
    enabled: Optional[bool] = None

    # Enforcement settings
    enforcement_level: Optional[str] = None
    affected_roles: Optional[List[str]] = None

    # 2FA-specific settings
    grace_period_hours: Optional[int] = None
    allow_exempt_alternative_auth: Optional[bool] = None

    # Additional policy-specific configuration
    policy_config: Optional[dict] = None
    description: Optional[str] = None


class SecurityPolicyResponse(BaseModel):
    """Schema for security policy response."""
    id: str
    name: str
    policy_type: str
    enabled: bool

    # Enforcement settings
    enforcement_level: str
    affected_roles: Optional[List[str]] = None

    # 2FA-specific settings
    grace_period_hours: Optional[int] = None
    allow_exempt_alternative_auth: bool = False

    # Additional policy-specific configuration
    policy_config: Optional[dict] = None
    description: Optional[str] = None

    # Metadata
    created_by_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class SecurityPolicyInfo(BaseModel):
    """Schema for security policy summary information."""
    total_policies: int
    enabled_policies: int
    disabled_policies: int
    mandatory_policies: int
    optional_policies: int
    audit_only_policies: int
    policies_by_type: dict


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("/policies", response_model=List[SecurityPolicyResponse])
def list_security_policies(
    enabled_only: bool = Query(False, description="Filter only enabled policies"),
    policy_type: Optional[str] = Query(None, description="Filter by policy type"),
    enforcement_level: Optional[str] = Query(None, description="Filter by enforcement level"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List all security policies.

    Returns a list of all security policies with optional filtering.
    """
    query = db.query(SecurityPolicy)

    if enabled_only:
        query = query.filter(SecurityPolicy.enabled == True)

    if policy_type:
        query = query.filter(SecurityPolicy.policy_type == policy_type)

    if enforcement_level:
        query = query.filter(SecurityPolicy.enforcement_level == enforcement_level)

    policies = query.order_by(SecurityPolicy.created_at.desc()).all()

    return [
        SecurityPolicyResponse(
            id=str(policy.id),
            name=policy.name,
            policy_type=policy.policy_type,
            enabled=policy.enabled,
            enforcement_level=policy.enforcement_level,
            affected_roles=policy.affected_roles,
            grace_period_hours=policy.grace_period_hours,
            allow_exempt_alternative_auth=policy.allow_exempt_alternative_auth,
            policy_config=policy.policy_config,
            description=policy.description,
            created_by_id=str(policy.created_by_id) if policy.created_by_id else None,
            created_at=policy.created_at.isoformat() if policy.created_at else None,
            updated_at=policy.updated_at.isoformat() if policy.updated_at else None,
        )
        for policy in policies
    ]


@router.get("/policies/info", response_model=SecurityPolicyInfo)
def get_security_policy_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get summary information about security policies.

    Returns statistics about total, enabled, disabled, and policies by enforcement level.
    """
    all_policies = db.query(SecurityPolicy).all()

    enabled_policies = [p for p in all_policies if p.enabled]
    disabled_policies = [p for p in all_policies if not p.enabled]

    mandatory_policies = [p for p in all_policies if p.enforcement_level == EnforcementLevel.MANDATORY.value]
    optional_policies = [p for p in all_policies if p.enforcement_level == EnforcementLevel.OPTIONAL.value]
    audit_only_policies = [p for p in all_policies if p.enforcement_level == EnforcementLevel.AUDIT_ONLY.value]

    # Count by policy type
    policies_by_type = {}
    for ptype in PolicyType:
        count = len([p for p in all_policies if p.policy_type == ptype.value])
        policies_by_type[ptype.value] = count

    return SecurityPolicyInfo(
        total_policies=len(all_policies),
        enabled_policies=len(enabled_policies),
        disabled_policies=len(disabled_policies),
        mandatory_policies=len(mandatory_policies),
        optional_policies=len(optional_policies),
        audit_only_policies=len(audit_only_policies),
        policies_by_type=policies_by_type
    )


@router.get("/policies/{policy_id}", response_model=SecurityPolicyResponse)
def get_security_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get a specific security policy by ID.
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Security policy not found")

    return SecurityPolicyResponse(
        id=str(policy.id),
        name=policy.name,
        policy_type=policy.policy_type,
        enabled=policy.enabled,
        enforcement_level=policy.enforcement_level,
        affected_roles=policy.affected_roles,
        grace_period_hours=policy.grace_period_hours,
        allow_exempt_alternative_auth=policy.allow_exempt_alternative_auth,
        policy_config=policy.policy_config,
        description=policy.description,
        created_by_id=str(policy.created_by_id) if policy.created_by_id else None,
        created_at=policy.created_at.isoformat() if policy.created_at else None,
        updated_at=policy.updated_at.isoformat() if policy.updated_at else None,
    )


@router.post("/policies", response_model=SecurityPolicyResponse, status_code=201)
def create_security_policy(
    policy_data: SecurityPolicyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new security policy.

    Creates a new security policy for managing access and authentication rules.
    """
    # Check if policy with same name already exists
    existing = db.query(SecurityPolicy).filter(SecurityPolicy.name == policy_data.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Security policy with this name already exists"
        )

    # Validate policy type
    valid_policy_types = [pt.value for pt in PolicyType]
    if policy_data.policy_type not in valid_policy_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid policy type. Must be one of: {', '.join(valid_policy_types)}"
        )

    # Validate enforcement level
    valid_enforcement_levels = [el.value for el in EnforcementLevel]
    if policy_data.enforcement_level not in valid_enforcement_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid enforcement level. Must be one of: {', '.join(valid_enforcement_levels)}"
        )

    # Create new policy
    new_policy = SecurityPolicy(
        name=policy_data.name,
        policy_type=policy_data.policy_type,
        enabled=policy_data.enabled,
        enforcement_level=policy_data.enforcement_level,
        affected_roles=policy_data.affected_roles,
        grace_period_hours=policy_data.grace_period_hours,
        allow_exempt_alternative_auth=policy_data.allow_exempt_alternative_auth,
        policy_config=policy_data.policy_config,
        description=policy_data.description,
        created_by_id=current_user.id,
    )

    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="security_policy_created",
        message=f"Security policy created: {new_policy.name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "policy_id": str(new_policy.id),
            "policy_name": new_policy.name,
            "policy_type": new_policy.policy_type,
            "enabled": new_policy.enabled
        }
    )

    return SecurityPolicyResponse(
        id=str(new_policy.id),
        name=new_policy.name,
        policy_type=new_policy.policy_type,
        enabled=new_policy.enabled,
        enforcement_level=new_policy.enforcement_level,
        affected_roles=new_policy.affected_roles,
        grace_period_hours=new_policy.grace_period_hours,
        allow_exempt_alternative_auth=new_policy.allow_exempt_alternative_auth,
        policy_config=new_policy.policy_config,
        description=new_policy.description,
        created_by_id=str(new_policy.created_by_id) if new_policy.created_by_id else None,
        created_at=new_policy.created_at.isoformat() if new_policy.created_at else None,
        updated_at=new_policy.updated_at.isoformat() if new_policy.updated_at else None,
    )


@router.put("/policies/{policy_id}", response_model=SecurityPolicyResponse)
def update_security_policy(
    policy_id: UUID,
    policy_data: SecurityPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update an existing security policy.
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Security policy not found")

    # Track changes for logging
    changes = {}

    # Update fields if provided
    if policy_data.name is not None:
        if policy.name != policy_data.name:
            changes["old_name"] = policy.name
            changes["new_name"] = policy_data.name
        policy.name = policy_data.name

    if policy_data.policy_type is not None:
        # Validate policy type
        valid_policy_types = [pt.value for pt in PolicyType]
        if policy_data.policy_type not in valid_policy_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid policy type. Must be one of: {', '.join(valid_policy_types)}"
            )
        if policy.policy_type != policy_data.policy_type:
            changes["old_policy_type"] = policy.policy_type
            changes["new_policy_type"] = policy_data.policy_type
        policy.policy_type = policy_data.policy_type

    if policy_data.enabled is not None:
        if policy.enabled != policy_data.enabled:
            changes["old_enabled"] = policy.enabled
            changes["new_enabled"] = policy_data.enabled
        policy.enabled = policy_data.enabled

    if policy_data.enforcement_level is not None:
        # Validate enforcement level
        valid_enforcement_levels = [el.value for el in EnforcementLevel]
        if policy_data.enforcement_level not in valid_enforcement_levels:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid enforcement level. Must be one of: {', '.join(valid_enforcement_levels)}"
            )
        if policy.enforcement_level != policy_data.enforcement_level:
            changes["old_enforcement_level"] = policy.enforcement_level
            changes["new_enforcement_level"] = policy_data.enforcement_level
        policy.enforcement_level = policy_data.enforcement_level

    if policy_data.affected_roles is not None:
        if policy.affected_roles != policy_data.affected_roles:
            changes["old_affected_roles"] = policy.affected_roles
            changes["new_affected_roles"] = policy_data.affected_roles
        policy.affected_roles = policy_data.affected_roles

    if policy_data.grace_period_hours is not None:
        if policy.grace_period_hours != policy_data.grace_period_hours:
            changes["old_grace_period_hours"] = policy.grace_period_hours
            changes["new_grace_period_hours"] = policy_data.grace_period_hours
        policy.grace_period_hours = policy_data.grace_period_hours

    if policy_data.allow_exempt_alternative_auth is not None:
        if policy.allow_exempt_alternative_auth != policy_data.allow_exempt_alternative_auth:
            changes["old_allow_exempt_alternative_auth"] = policy.allow_exempt_alternative_auth
            changes["new_allow_exempt_alternative_auth"] = policy_data.allow_exempt_alternative_auth
        policy.allow_exempt_alternative_auth = policy_data.allow_exempt_alternative_auth

    if policy_data.policy_config is not None:
        policy.policy_config = policy_data.policy_config

    if policy_data.description is not None:
        if policy.description != policy_data.description:
            changes["old_description"] = policy.description
            changes["new_description"] = policy_data.description
        policy.description = policy_data.description

    db.commit()
    db.refresh(policy)

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="security_policy_updated",
        message=f"Security policy updated: {policy.name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "policy_id": str(policy.id),
            "policy_name": policy.name,
            "changes": changes
        }
    )

    return SecurityPolicyResponse(
        id=str(policy.id),
        name=policy.name,
        policy_type=policy.policy_type,
        enabled=policy.enabled,
        enforcement_level=policy.enforcement_level,
        affected_roles=policy.affected_roles,
        grace_period_hours=policy.grace_period_hours,
        allow_exempt_alternative_auth=policy.allow_exempt_alternative_auth,
        policy_config=policy.policy_config,
        description=policy.description,
        created_by_id=str(policy.created_by_id) if policy.created_by_id else None,
        created_at=policy.created_at.isoformat() if policy.created_at else None,
        updated_at=policy.updated_at.isoformat() if policy.updated_at else None,
    )


@router.delete("/policies/{policy_id}")
def delete_security_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete a security policy.
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Security policy not found")

    policy_name = policy.name
    policy_type = policy.policy_type

    db.delete(policy)
    db.commit()

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="security_policy_deleted",
        message=f"Security policy deleted: {policy_name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "policy_id": str(policy_id),
            "policy_name": policy_name,
            "policy_type": policy_type
        }
    )

    return {
        "status": "ok",
        "message": "Security policy deleted",
        "id": str(policy_id)
    }


@router.post("/policies/{policy_id}/enable")
def enable_security_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Enable a security policy.
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Security policy not found")

    if policy.enabled:
        return {"status": "ok", "message": "Policy already enabled", "id": str(policy.id)}

    policy.enabled = True
    db.commit()
    db.refresh(policy)

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="security_policy_enabled",
        message=f"Security policy enabled: {policy.name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "policy_id": str(policy.id),
            "policy_name": policy.name,
            "policy_type": policy.policy_type
        }
    )

    return {"status": "ok", "message": "Security policy enabled", "id": str(policy.id), "enabled": True}


@router.post("/policies/{policy_id}/disable")
def disable_security_policy(
    policy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Disable a security policy.
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Security policy not found")

    if not policy.enabled:
        return {"status": "ok", "message": "Policy already disabled", "id": str(policy.id)}

    policy.enabled = False
    db.commit()
    db.refresh(policy)

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="security_policy_disabled",
        message=f"Security policy disabled: {policy.name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "policy_id": str(policy.id),
            "policy_name": policy.name,
            "policy_type": policy.policy_type
        }
    )

    return {"status": "ok", "message": "Security policy disabled", "id": str(policy.id), "enabled": False}


@router.post("/policies/check")
def check_policy_applies(
    policy_id: UUID,
    role: str = Query(..., description="Role to check against the policy"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Check if a security policy applies to a specific role.

    Useful for testing and verification purposes.
    """
    policy = db.query(SecurityPolicy).filter(SecurityPolicy.id == policy_id).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Security policy not found")

    applies = policy.applies_to_role(role)
    is_mandatory = policy.is_mandatory()
    is_optional = policy.is_optional()
    is_audit_only = policy.is_audit_only()

    return {
        "policy_id": str(policy.id),
        "policy_name": policy.name,
        "policy_type": policy.policy_type,
        "role": role,
        "applies": applies,
        "enabled": policy.enabled,
        "enforcement_level": policy.enforcement_level,
        "is_mandatory": is_mandatory,
        "is_optional": is_optional,
        "is_audit_only": is_audit_only,
        "affected_roles": policy.affected_roles
    }
