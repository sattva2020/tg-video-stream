"""
SAML Configuration Management Endpoints
Spec: 025-advanced-security-compliance-features

CRUD endpoints for managing SAML/SSO Identity Provider configurations.
Admin-only access.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from api.auth import require_admin
from src.models.user import User
from src.models.saml_config import SAMLConfig
from database import get_db
from src.services.activity_service import ActivityService

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class SAMLConfigCreate(BaseModel):
    """Schema for creating a new SAML configuration."""
    name: str
    enabled: bool = False

    # Identity Provider (IdP) settings
    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert: str
    idp_slo_url: Optional[str] = None
    idp_metadata_url: Optional[str] = None

    # Service Provider (SP) settings
    sp_entity_id: str
    sp_acs_url: str
    sp_slo_url: Optional[str] = None

    # Security settings
    name_id_format: Optional[str] = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
    security_config: Optional[dict] = None

    # User provisioning and role mapping
    attribute_mapping: Optional[dict] = None
    role_mapping: Optional[dict] = None


class SAMLConfigUpdate(BaseModel):
    """Schema for updating an existing SAML configuration."""
    name: Optional[str] = None
    enabled: Optional[bool] = None

    # Identity Provider (IdP) settings
    idp_entity_id: Optional[str] = None
    idp_sso_url: Optional[str] = None
    idp_x509_cert: Optional[str] = None
    idp_slo_url: Optional[str] = None
    idp_metadata_url: Optional[str] = None

    # Service Provider (SP) settings
    sp_entity_id: Optional[str] = None
    sp_acs_url: Optional[str] = None
    sp_slo_url: Optional[str] = None

    # Security settings
    name_id_format: Optional[str] = None
    security_config: Optional[dict] = None

    # User provisioning and role mapping
    attribute_mapping: Optional[dict] = None
    role_mapping: Optional[dict] = None


class SAMLConfigResponse(BaseModel):
    """Schema for SAML configuration response."""
    id: str
    name: str
    enabled: bool

    # Identity Provider (IdP) settings
    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: Optional[str] = None
    idp_metadata_url: Optional[str] = None

    # Service Provider (SP) settings
    sp_entity_id: str
    sp_acs_url: str
    sp_slo_url: Optional[str] = None

    # Security settings
    name_id_format: Optional[str] = None
    security_config: Optional[dict] = None

    # User provisioning and role mapping
    attribute_mapping: Optional[dict] = None
    role_mapping: Optional[dict] = None

    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("/configs", response_model=List[SAMLConfigResponse])
def list_saml_configs(
    enabled_only: bool = Query(False, description="Filter only enabled configurations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List all SAML configurations.

    Returns a list of all SAML IdP configurations with optional filtering.
    """
    query = db.query(SAMLConfig)

    if enabled_only:
        query = query.filter(SAMLConfig.enabled == True)

    configs = query.order_by(SAMLConfig.created_at.desc()).all()

    return [
        SAMLConfigResponse(
            id=str(config.id),
            name=config.name,
            enabled=config.enabled,
            idp_entity_id=config.idp_entity_id,
            idp_sso_url=config.idp_sso_url,
            idp_slo_url=config.idp_slo_url,
            idp_metadata_url=config.idp_metadata_url,
            sp_entity_id=config.sp_entity_id,
            sp_acs_url=config.sp_acs_url,
            sp_slo_url=config.sp_slo_url,
            name_id_format=config.name_id_format,
            security_config=config.security_config,
            attribute_mapping=config.attribute_mapping,
            role_mapping=config.role_mapping,
            created_at=config.created_at.isoformat() if config.created_at else None,
            updated_at=config.updated_at.isoformat() if config.updated_at else None,
        )
        for config in configs
    ]


@router.get("/configs/{config_id}", response_model=SAMLConfigResponse)
def get_saml_config(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get a specific SAML configuration by ID.
    """
    config = db.query(SAMLConfig).filter(SAMLConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SAML configuration not found")

    return SAMLConfigResponse(
        id=str(config.id),
        name=config.name,
        enabled=config.enabled,
        idp_entity_id=config.idp_entity_id,
        idp_sso_url=config.idp_sso_url,
        idp_slo_url=config.idp_slo_url,
        idp_metadata_url=config.idp_metadata_url,
        sp_entity_id=config.sp_entity_id,
        sp_acs_url=config.sp_acs_url,
        sp_slo_url=config.sp_slo_url,
        name_id_format=config.name_id_format,
        security_config=config.security_config,
        attribute_mapping=config.attribute_mapping,
        role_mapping=config.role_mapping,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
    )


@router.post("/configs", response_model=SAMLConfigResponse, status_code=201)
def create_saml_config(
    config_data: SAMLConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Create a new SAML configuration.

    Creates a new Identity Provider configuration for SSO authentication.
    """
    # Check if config with same name already exists
    existing = db.query(SAMLConfig).filter(SAMLConfig.name == config_data.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="SAML configuration with this name already exists"
        )

    # Create new configuration
    new_config = SAMLConfig(
        name=config_data.name,
        enabled=config_data.enabled,
        idp_entity_id=config_data.idp_entity_id,
        idp_sso_url=config_data.idp_sso_url,
        idp_x509_cert=config_data.idp_x509_cert,
        idp_slo_url=config_data.idp_slo_url,
        idp_metadata_url=config_data.idp_metadata_url,
        sp_entity_id=config_data.sp_entity_id,
        sp_acs_url=config_data.sp_acs_url,
        sp_slo_url=config_data.sp_slo_url,
        name_id_format=config_data.name_id_format,
        security_config=config_data.security_config,
        attribute_mapping=config_data.attribute_mapping,
        role_mapping=config_data.role_mapping,
    )

    db.add(new_config)
    db.commit()
    db.refresh(new_config)

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="saml_config_created",
        message=f"SAML configuration created: {new_config.name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "config_id": str(new_config.id),
            "config_name": new_config.name,
            "enabled": new_config.enabled
        }
    )

    return SAMLConfigResponse(
        id=str(new_config.id),
        name=new_config.name,
        enabled=new_config.enabled,
        idp_entity_id=new_config.idp_entity_id,
        idp_sso_url=new_config.idp_sso_url,
        idp_slo_url=new_config.idp_slo_url,
        idp_metadata_url=new_config.idp_metadata_url,
        sp_entity_id=new_config.sp_entity_id,
        sp_acs_url=new_config.sp_acs_url,
        sp_slo_url=new_config.sp_slo_url,
        name_id_format=new_config.name_id_format,
        security_config=new_config.security_config,
        attribute_mapping=new_config.attribute_mapping,
        role_mapping=new_config.role_mapping,
        created_at=new_config.created_at.isoformat() if new_config.created_at else None,
        updated_at=new_config.updated_at.isoformat() if new_config.updated_at else None,
    )


@router.put("/configs/{config_id}", response_model=SAMLConfigResponse)
def update_saml_config(
    config_id: UUID,
    config_data: SAMLConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Update an existing SAML configuration.
    """
    config = db.query(SAMLConfig).filter(SAMLConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SAML configuration not found")

    # Track changes for logging
    changes = {}

    # Update fields if provided
    if config_data.name is not None:
        if config.name != config_data.name:
            changes["old_name"] = config.name
            changes["new_name"] = config_data.name
        config.name = config_data.name

    if config_data.enabled is not None:
        if config.enabled != config_data.enabled:
            changes["old_enabled"] = config.enabled
            changes["new_enabled"] = config_data.enabled
        config.enabled = config_data.enabled

    if config_data.idp_entity_id is not None:
        config.idp_entity_id = config_data.idp_entity_id

    if config_data.idp_sso_url is not None:
        config.idp_sso_url = config_data.idp_sso_url

    if config_data.idp_x509_cert is not None:
        config.idp_x509_cert = config_data.idp_x509_cert

    if config_data.idp_slo_url is not None:
        config.idp_slo_url = config_data.idp_slo_url

    if config_data.idp_metadata_url is not None:
        config.idp_metadata_url = config_data.idp_metadata_url

    if config_data.sp_entity_id is not None:
        config.sp_entity_id = config_data.sp_entity_id

    if config_data.sp_acs_url is not None:
        config.sp_acs_url = config_data.sp_acs_url

    if config_data.sp_slo_url is not None:
        config.sp_slo_url = config_data.sp_slo_url

    if config_data.name_id_format is not None:
        config.name_id_format = config_data.name_id_format

    if config_data.security_config is not None:
        config.security_config = config_data.security_config

    if config_data.attribute_mapping is not None:
        config.attribute_mapping = config_data.attribute_mapping

    if config_data.role_mapping is not None:
        config.role_mapping = config_data.role_mapping

    db.commit()
    db.refresh(config)

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="saml_config_updated",
        message=f"SAML configuration updated: {config.name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "config_id": str(config.id),
            "config_name": config.name,
            "changes": changes
        }
    )

    return SAMLConfigResponse(
        id=str(config.id),
        name=config.name,
        enabled=config.enabled,
        idp_entity_id=config.idp_entity_id,
        idp_sso_url=config.idp_sso_url,
        idp_slo_url=config.idp_slo_url,
        idp_metadata_url=config.idp_metadata_url,
        sp_entity_id=config.sp_entity_id,
        sp_acs_url=config.sp_acs_url,
        sp_slo_url=config.sp_slo_url,
        name_id_format=config.name_id_format,
        security_config=config.security_config,
        attribute_mapping=config.attribute_mapping,
        role_mapping=config.role_mapping,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
    )


@router.delete("/configs/{config_id}")
def delete_saml_config(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Delete a SAML configuration.
    """
    config = db.query(SAMLConfig).filter(SAMLConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SAML configuration not found")

    config_name = config.name

    db.delete(config)
    db.commit()

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="saml_config_deleted",
        message=f"SAML configuration deleted: {config_name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "config_id": str(config_id),
            "config_name": config_name
        }
    )

    return {
        "status": "ok",
        "message": "SAML configuration deleted",
        "id": str(config_id)
    }


@router.post("/configs/{config_id}/enable")
def enable_saml_config(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Enable a SAML configuration.
    """
    config = db.query(SAMLConfig).filter(SAMLConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SAML configuration not found")

    if config.enabled:
        return {"status": "ok", "message": "Configuration already enabled", "id": str(config.id)}

    config.enabled = True
    db.commit()
    db.refresh(config)

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="saml_config_enabled",
        message=f"SAML configuration enabled: {config.name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "config_id": str(config.id),
            "config_name": config.name
        }
    )

    return {"status": "ok", "message": "SAML configuration enabled", "id": str(config.id), "enabled": True}


@router.post("/configs/{config_id}/disable")
def disable_saml_config(
    config_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Disable a SAML configuration.
    """
    config = db.query(SAMLConfig).filter(SAMLConfig.id == config_id).first()

    if not config:
        raise HTTPException(status_code=404, detail="SAML configuration not found")

    if not config.enabled:
        return {"status": "ok", "message": "Configuration already disabled", "id": str(config.id)}

    config.enabled = False
    db.commit()
    db.refresh(config)

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_event(
        event_type="saml_config_disabled",
        message=f"SAML configuration disabled: {config.name}",
        user_id=current_user.id,
        user_email=current_user.email,
        details={
            "config_id": str(config.id),
            "config_name": config.name
        }
    )

    return {"status": "ok", "message": "SAML configuration disabled", "id": str(config.id), "enabled": False}
