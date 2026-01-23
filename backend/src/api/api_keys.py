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


@router.get(
    "/",
    response_model=list[APIKeyResponse],
    summary="List all API keys",
    description="""
Retrieves all API keys owned by the currently authenticated user.

**Important:** The actual API key value is NEVER included in list responses for security reasons.
The key value is only returned once when you create a new API key.

**Response includes:**
- Key metadata (id, name, scopes, rate_limit, is_active)
- Usage statistics (last_used, created_at, updated_at)
- Expiration information (expires_at)

**Authentication:** Requires valid JWT token or session cookie
    """,
    responses={
        200: {
            "description": "List of API keys owned by the user",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                            "name": "Production Integration",
                            "scopes": ["read:streams", "write:playlists"],
                            "rate_limit": {"requests": 100, "window": 60},
                            "is_active": True,
                            "expires_at": "2025-12-31T23:59:59Z",
                            "last_used": "2025-01-15T10:30:00Z",
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2025-01-15T10:30:00Z",
                            "key": None
                        }
                    ]
                }
            }
        }
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.get(
    "http://localhost:8000/api/api-keys/",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)
api_keys = response.json()
print(api_keys)
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/api-keys/', {
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN'
    }
});
const apiKeys = await response.json();
console.log(apiKeys);
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X GET "http://localhost:8000/api/api-keys/" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
                """
            }
        ]
    }
)
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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


@router.post(
    "/",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description="""
Creates a new API key for the authenticated user.

**⚠️ IMPORTANT:** The API key value is returned ONLY ONCE in this response.
Make sure to save it securely, as it cannot be retrieved again.

**Scopes:**
API keys can be granted specific scopes to limit their access:
- `read:streams` - View stream information
- `write:streams` - Start/stop streams
- `read:playlists` - View playlists
- `write:playlists` - Modify playlists
- `read:channels` - View channels
- `write:channels` - Manage channels
- `read:analytics` - View analytics data
- `read:webhooks` - View webhooks
- `write:webhooks` - Manage webhooks

**Rate Limiting:**
You can optionally set a custom rate limit per API key.
If not specified, the default rate limit applies.

**Expiration:**
Optionally set an expiration date. Keys without expiration remain active indefinitely.

**Authentication:** Requires valid JWT token or session cookie
    """,
    responses={
        201: {
            "description": "API key created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                        "name": "Production Integration",
                        "scopes": ["read:streams", "write:playlists"],
                        "rate_limit": {"requests": 100, "window": 60},
                        "is_active": True,
                        "expires_at": "2025-12-31T23:59:59Z",
                        "last_used": None,
                        "created_at": "2025-01-15T10:30:00Z",
                        "updated_at": "2025-01-15T10:30:00Z",
                        "key": "sbpa_prod_abc123xyz456"
                    }
                }
            }
        }
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.post(
    "http://localhost:8000/api/api-keys/",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"},
    json={
        "name": "Production Integration",
        "scopes": ["read:streams", "write:playlists"],
        "rate_limit": {"requests": 100, "window": 60}
    }
)
api_key = response.json()
print(f"API Key (save this!): {api_key['key']}")
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/api-keys/', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        name: 'Production Integration',
        scopes: ['read:streams', 'write:playlists'],
        rate_limit: { requests: 100, window: 60 }
    })
});
const apiKey = await response.json();
console.log('API Key (save this!):', apiKey.key);
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X POST "http://localhost:8000/api/api-keys/" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Production Integration",
    "scopes": ["read:streams", "write:playlists"],
    "rate_limit": {"requests": 100, "window": 60}
  }'
                """
            }
        ]
    }
)
def create_api_key(
    key_data: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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


@router.get(
    "/{key_id}",
    response_model=APIKeyResponse,
    summary="Get API key details",
    description="""
Retrieves detailed information about a specific API key.

**Note:** This endpoint does NOT return the actual API key value.
Only the metadata and usage statistics are returned.

**Authentication:** Requires valid JWT token or session cookie
**Authorization:** User must own the API key
    """,
    responses={
        200: {
            "description": "API key details",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                        "name": "Production Integration",
                        "scopes": ["read:streams", "write:playlists"],
                        "rate_limit": {"requests": 100, "window": 60},
                        "is_active": True,
                        "expires_at": "2025-12-31T23:59:59Z",
                        "last_used": "2025-01-15T10:30:00Z",
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-15T10:30:00Z",
                        "key": None
                    }
                }
            }
        },
        404: {"description": "API key not found"},
        403: {"description": "Access denied - you don't own this key"}
    }
)
def get_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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


@router.patch(
    "/{key_id}",
    response_model=APIKeyResponse,
    summary="Update an API key",
    description="""
Updates an existing API key.

**Editable fields:**
- `name` - Display name for the key
- `scopes` - List of granted permissions
- `rate_limit` - Custom rate limit configuration
- `is_active` - Enable or disable the key
- `expires_at` - Expiration date

**Note:** The actual API key value CANNOT be changed.
If you need a new key value, delete and recreate the key.

**Authentication:** Requires valid JWT token or session cookie
**Authorization:** User must own the API key
    """,
    responses={
        200: {
            "description": "API key updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                        "name": "Updated Name",
                        "scopes": ["read:streams"],
                        "rate_limit": {"requests": 50, "window": 60},
                        "is_active": False,
                        "expires_at": "2025-12-31T23:59:59Z",
                        "last_used": "2025-01-15T10:30:00Z",
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-16T14:20:00Z",
                        "key": None
                    }
                }
            }
        },
        404: {"description": "API key not found"},
        403: {"description": "Access denied"}
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.patch(
    "http://localhost:8000/api/api-keys/{key_id}",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"},
    json={
        "name": "Updated Name",
        "scopes": ["read:streams"],
        "is_active": False
    }
)
updated_key = response.json()
print(updated_key)
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/api-keys/{key_id}', {
    method: 'PATCH',
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        name: 'Updated Name',
        scopes: ['read:streams'],
        is_active: false
    })
});
const updatedKey = await response.json();
console.log(updatedKey);
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X PATCH "http://localhost:8000/api/api-keys/{key_id}" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Updated Name",
    "scopes": ["read:streams"],
    "is_active": false
  }'
                """
            }
        ]
    }
)
def update_api_key(
    key_id: uuid.UUID,
    key_update: APIKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an API key",
    description="""
Permanently deletes an API key.

**⚠️ WARNING:** This action cannot be undone.
The deleted API key will immediately stop working for any API requests.

**Alternative:** Consider using `/revoke` if you want to disable the key
temporarily without deleting it.

**Authentication:** Requires valid JWT token or session cookie
**Authorization:** User must own the API key
    """,
    responses={
        204: {"description": "API key deleted successfully"},
        404: {"description": "API key not found"},
        403: {"description": "Access denied"}
    },
    openapi_extra={
        "x-codeSamples": [
            {
                "lang": "Python",
                "source": """
import requests

response = requests.delete(
    "http://localhost:8000/api/api-keys/{key_id}",
    headers={"Authorization": "Bearer YOUR_JWT_TOKEN"}
)

if response.status_code == 204:
    print("API key deleted successfully")
                """
            },
            {
                "lang": "JavaScript",
                "source": """
const response = await fetch('http://localhost:8000/api/api-keys/{key_id}', {
    method: 'DELETE',
    headers: {
        'Authorization': 'Bearer YOUR_JWT_TOKEN'
    }
});

if (response.status === 204) {
    console.log('API key deleted successfully');
}
                """
            },
            {
                "lang": "cURL",
                "source": """
curl -X DELETE "http://localhost:8000/api/api-keys/{key_id}" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
                """
            }
        ]
    }
)
def delete_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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


@router.post(
    "/{key_id}/revoke",
    response_model=APIKeyResponse,
    summary="Revoke an API key",
    description="""
Revokes an API key by setting `is_active` to `False`.

The key will immediately stop working for API requests.

**Benefits over deletion:**
- Reversible: You can reactivate the key by updating `is_active` to `True`
- Auditable: The key remains in the database for audit purposes
- Safer: Less destructive than permanent deletion

**Authentication:** Requires valid JWT token or session cookie
**Authorization:** User must own the API key
    """,
    responses={
        200: {
            "description": "API key revoked successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "owner_id": "550e8400-e29b-41d4-a716-446655440001",
                        "name": "Production Integration",
                        "scopes": ["read:streams", "write:playlists"],
                        "rate_limit": {"requests": 100, "window": 60},
                        "is_active": False,
                        "expires_at": "2025-12-31T23:59:59Z",
                        "last_used": "2025-01-15T10:30:00Z",
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-16T15:00:00Z",
                        "key": None
                    }
                }
            }
        },
        404: {"description": "API key not found"},
        403: {"description": "Access denied"}
    }
)
def revoke_api_key(
    key_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
