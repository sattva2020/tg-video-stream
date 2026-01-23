"""
API Key Management Endpoints
Spec: 026-api-webhook-ecosystem

Endpoints for creating, listing, updating, and revoking API keys.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from src.database import get_db
from src.models.user import User
from src.models.api_key import APIKey
from src.schemas.api_key import APIKeyCreate, APIKeyResponse, APIKeyUpdate
from src.services.api_key_service import APIKeyService
from src.api.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=list[APIKeyResponse])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all API keys owned by the current user.

    Returns a list of API keys with their metadata.
    The actual key value is never included in list responses.
    """
    service = APIKeyService(db)
    keys = service.list_keys(owner_id=current_user.id)

    # Convert to response format (key field is None for list)
    result = []
    for key in keys:
        key_dict = {
            "id": key.id,
            "owner_id": key.owner_id,
            "name": key.name,
            "scopes": key.scopes,
            "rate_limit": key.rate_limit,
            "is_active": key.is_active,
            "expires_at": key.expires_at,
            "last_used": key.last_used,
            "created_at": key.created_at,
            "updated_at": key.updated_at,
            "key": None,  # Never include key in list
        }
        result.append(APIKeyResponse(**key_dict))

    return result


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    key_data: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new API key.

    The API key value is returned only once in the response.
    Make sure to save it securely, as it cannot be retrieved again.
    """
    service = APIKeyService(db)

    # Create the key
    api_key, raw_key = service.create_key(current_user.id, key_data)

    # Build response with the raw key (only time it's returned)
    response_data = {
        "id": api_key.id,
        "owner_id": api_key.owner_id,
        "name": api_key.name,
        "scopes": api_key.scopes,
        "rate_limit": api_key.rate_limit,
        "is_active": api_key.is_active,
        "expires_at": api_key.expires_at,
        "last_used": api_key.last_used,
        "created_at": api_key.created_at,
        "updated_at": api_key.updated_at,
        "key": raw_key,  # Include key only on creation
    }

    logger.info(f"User {current_user.id} created API key {api_key.id}")
    return APIKeyResponse(**response_data)


@router.get("/{key_id}", response_model=APIKeyResponse)
def get_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific API key by ID.

    Returns the key metadata but not the actual key value.
    """
    service = APIKeyService(db)
    api_key = service.get_key(key_id)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Verify ownership
    if api_key.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Build response without the key value
    response_data = {
        "id": api_key.id,
        "owner_id": api_key.owner_id,
        "name": api_key.name,
        "scopes": api_key.scopes,
        "rate_limit": api_key.rate_limit,
        "is_active": api_key.is_active,
        "expires_at": api_key.expires_at,
        "last_used": api_key.last_used,
        "created_at": api_key.created_at,
        "updated_at": api_key.updated_at,
        "key": None,  # Never return key value in GET
    }

    return APIKeyResponse(**response_data)


@router.patch("/{key_id}", response_model=APIKeyResponse)
def update_api_key(
    key_id: uuid.UUID,
    key_update: APIKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an API key.

    Can update name, scopes, rate_limit, is_active, and expires_at.
    The actual key value cannot be changed.
    """
    service = APIKeyService(db)

    # First verify ownership
    api_key = service.get_key(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    if api_key.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update the key
    updated_key = service.update_key(key_id, key_update)
    if not updated_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Build response without the key value
    response_data = {
        "id": updated_key.id,
        "owner_id": updated_key.owner_id,
        "name": updated_key.name,
        "scopes": updated_key.scopes,
        "rate_limit": updated_key.rate_limit,
        "is_active": updated_key.is_active,
        "expires_at": updated_key.expires_at,
        "last_used": updated_key.last_used,
        "created_at": updated_key.created_at,
        "updated_at": updated_key.updated_at,
        "key": None,
    }

    logger.info(f"User {current_user.id} updated API key {key_id}")
    return APIKeyResponse(**response_data)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete an API key permanently.

    This action cannot be undone. The key will immediately stop working.
    """
    service = APIKeyService(db)

    # First verify ownership
    api_key = service.get_key(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    if api_key.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Delete the key
    success = service.delete_key(key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    logger.info(f"User {current_user.id} deleted API key {key_id}")
    return None


@router.post("/{key_id}/revoke", response_model=APIKeyResponse)
def revoke_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke an API key.

    Sets is_active to False. The key will immediately stop working.
    This is safer than delete as it can be reversed by re-activating.
    """
    service = APIKeyService(db)

    # First verify ownership
    api_key = service.get_key(key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    if api_key.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Revoke the key
    revoked_key = service.revoke_key(key_id)
    if not revoked_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )

    # Build response without the key value
    response_data = {
        "id": revoked_key.id,
        "owner_id": revoked_key.owner_id,
        "name": revoked_key.name,
        "scopes": revoked_key.scopes,
        "rate_limit": revoked_key.rate_limit,
        "is_active": revoked_key.is_active,
        "expires_at": revoked_key.expires_at,
        "last_used": revoked_key.last_used,
        "created_at": revoked_key.created_at,
        "updated_at": revoked_key.updated_at,
        "key": None,
    }

    logger.info(f"User {current_user.id} revoked API key {key_id}")
    return APIKeyResponse(**response_data)
