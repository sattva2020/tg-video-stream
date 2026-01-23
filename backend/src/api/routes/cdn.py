"""
API routes for CDN management (configuration, status, cache control).

Endpoints:
  GET /api/v1/cdn/providers - List CDN provider configurations
  GET /api/v1/cdn/providers/{id} - Get specific CDN provider
  GET /api/v1/cdn/status - Get CDN health status
  POST /api/v1/cdn/purge - Purge CDN cache
  GET /api/v1/cdn/locations - List edge locations
  PUT /api/v1/cdn/cache-rules - Configure cache rules
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_user, require_admin
from ...models.user import User
from ...database import get_db
from ...services.cdn_service import CDNService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/cdn", tags=["cdn"])


# Request/Response Models

class CDNProviderInfo(BaseModel):
    """CDN provider configuration information."""
    id: str
    provider: str
    name: str
    enabled: bool
    priority: int
    health_status: str
    last_health_check: Optional[str] = None
    last_error: Optional[str] = None
    zone_id: Optional[str] = None
    distribution_id: Optional[str] = None
    service_id: Optional[str] = None
    account_id: Optional[str] = None
    created_at: Optional[str] = None
    api_token: Optional[str] = None


class CDNProviderListResponse(BaseModel):
    """Response listing CDN providers."""
    providers: List[CDNProviderInfo]
    total: int


class PurgeCacheRequest(BaseModel):
    """Request to purge CDN cache."""
    urls: List[str] = Field(..., min_length=1, description="List of URLs to purge from cache")
    provider_id: Optional[str] = Field(None, description="Optional CDN provider ID (purges from all if not specified)")
    purge_all: bool = Field(False, description="If True, purge entire cache")


class PurgeCacheResponse(BaseModel):
    """Response after cache purge."""
    success: bool
    purged_urls: List[str]
    providers: List[dict]
    errors: List[str]


class HealthCheckInfo(BaseModel):
    """Health check information for a provider."""
    id: str
    name: str
    provider: str
    status: str
    response_time_ms: int
    last_check: Optional[str] = None
    edge_nodes_healthy: Optional[int] = None
    edge_nodes_total: Optional[int] = None
    error: Optional[str] = None


class CDNHealthStatusResponse(BaseModel):
    """CDN health status response."""
    overall_status: str
    providers: List[HealthCheckInfo]
    last_check: str
    error: Optional[str] = None


class EdgeLocation(BaseModel):
    """Edge location information."""
    provider: str
    provider_id: str
    code: str
    city: str
    country: str
    region: str
    latitude: float
    longitude: float
    active: bool


class EdgeLocationsResponse(BaseModel):
    """Response with edge locations list."""
    locations: List[EdgeLocation]
    total: int


class CacheRule(BaseModel):
    """Cache rule configuration."""
    pattern: str = Field(..., description="URL pattern to match")
    ttl: int = Field(..., ge=0, description="Time to live in seconds")
    priority: int = Field(1, ge=1, description="Rule priority (higher = more specific)")


class ConfigureCacheRulesRequest(BaseModel):
    """Request to configure cache rules."""
    rules: List[CacheRule] = Field(..., min_length=1, description="List of cache rules")
    provider_id: str = Field(..., description="CDN provider ID")


class ConfigureCacheRulesResponse(BaseModel):
    """Response after configuring cache rules."""
    success: bool
    applied_rules: int
    error: Optional[str] = None


# Dependency to get CDN service

def get_cdn_service():
    """Dependency to get CDN service instance."""
    return CDNService()


# Route Handlers

@router.get("/providers", response_model=CDNProviderListResponse, status_code=200)
async def list_cdn_providers(
    enabled_only: bool = True,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    cdn_service: CDNService = Depends(get_cdn_service)
):
    """
    List all CDN provider configurations.

    **Permission**: Admin only

    **Rate Limit**: 100 requests/minute per user (Standard)

    **Query Parameters**:
    - `enabled_only`: If True, only return enabled providers (default: True)

    **Example Response**:
    ```json
    {
      "providers": [
        {
          "id": "uuid",
          "provider": "cloudflare",
          "name": "Primary CDN",
          "enabled": true,
          "priority": 1,
          "health_status": "healthy"
        }
      ],
      "total": 1
    }
    ```
    """
    try:
        providers = await cdn_service.list_providers(enabled_only=enabled_only)

        return CDNProviderListResponse(
            providers=[CDNProviderInfo(**p) for p in providers],
            total=len(providers)
        )
    except Exception as e:
        logger.error(f"Error listing CDN providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list CDN providers"
        )


@router.get("/providers/{provider_id}", response_model=CDNProviderInfo, status_code=200)
async def get_cdn_provider(
    provider_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    cdn_service: CDNService = Depends(get_cdn_service)
):
    """
    Get specific CDN provider configuration.

    **Permission**: Admin only

    **Rate Limit**: 200 requests/minute per user (Elevated)

    **Path Parameters**:
    - `provider_id`: CDN configuration UUID
    """
    try:
        provider = await cdn_service.get_provider(provider_id)

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"CDN provider {provider_id} not found"
            )

        return CDNProviderInfo(**provider)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CDN provider {provider_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get CDN provider"
        )


@router.get("/status", response_model=CDNHealthStatusResponse, status_code=200)
async def get_cdn_status(
    provider_id: Optional[str] = None,
    use_cache: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    cdn_service: CDNService = Depends(get_cdn_service)
):
    """
    Get CDN health status for monitoring.

    **Permission**: Authenticated users

    **Rate Limit**: 200 requests/minute per user (Elevated)

    **Query Parameters**:
    - `provider_id`: Optional CDN provider ID (checks all if not specified)
    - `use_cache`: Whether to use cached health status (default: True)

    **Example Response**:
    ```json
    {
      "overall_status": "healthy",
      "providers": [
        {
          "id": "uuid",
          "name": "Primary CDN",
          "provider": "cloudflare",
          "status": "healthy",
          "response_time_ms": 45
        }
      ],
      "last_check": "2024-01-15T10:30:00Z"
    }
    ```
    """
    try:
        health_data = await cdn_service.get_health_status(
            provider_id=provider_id,
            use_cache=use_cache
        )

        return CDNHealthStatusResponse(**health_data)
    except Exception as e:
        logger.error(f"Error getting CDN status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get CDN status"
        )


@router.post("/purge", response_model=PurgeCacheResponse, status_code=200)
async def purge_cdn_cache(
    request: PurgeCacheRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    cdn_service: CDNService = Depends(get_cdn_service)
):
    """
    Purge CDN cache for specified URLs.

    **Permission**: Admin only

    **Rate Limit**: 50 requests/minute per user (Strict)

    **Example**:
    ```json
    {
      "urls": ["https://example.com/video1.mp4"],
      "provider_id": null,
      "purge_all": false
    }
    ```
    """
    try:
        result = await cdn_service.purge_cache(
            urls=request.urls,
            provider_id=request.provider_id,
            purge_all=request.purge_all
        )

        logger.info(
            f"Cache purge requested by user {current_user.id}: "
            f"success={result['success']}, urls={len(request.urls)}"
        )

        return PurgeCacheResponse(**result)
    except Exception as e:
        logger.error(f"Error purging CDN cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to purge CDN cache"
        )


@router.get("/locations", response_model=EdgeLocationsResponse, status_code=200)
async def list_edge_locations(
    provider_id: Optional[str] = None,
    use_cache: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    cdn_service: CDNService = Depends(get_cdn_service)
):
    """
    List available edge locations for CDN providers.

    **Permission**: Authenticated users

    **Rate Limit**: 100 requests/minute per user (Standard)

    **Query Parameters**:
    - `provider_id`: Optional CDN provider ID (gets all if not specified)
    - `use_cache`: Whether to use cached locations (default: True)

    **Example Response**:
    ```json
    {
      "locations": [
        {
          "provider": "cloudflare",
          "code": "AMS",
          "city": "Amsterdam",
          "country": "Netherlands",
          "region": "Europe",
          "latitude": 52.37,
          "longitude": 4.89,
          "active": true
        }
      ],
      "total": 1
    }
    ```
    """
    try:
        locations = await cdn_service.list_edge_locations(
            provider_id=provider_id,
            use_cache=use_cache
        )

        return EdgeLocationsResponse(
            locations=[EdgeLocation(**loc) for loc in locations],
            total=len(locations)
        )
    except Exception as e:
        logger.error(f"Error listing edge locations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list edge locations"
        )


@router.put("/cache-rules", response_model=ConfigureCacheRulesResponse, status_code=200)
async def configure_cache_rules(
    request: ConfigureCacheRulesRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    cdn_service: CDNService = Depends(get_cdn_service)
):
    """
    Configure cache rules for a CDN provider.

    **Permission**: Admin only

    **Rate Limit**: 50 requests/minute per user (Strict)

    **Example**:
    ```json
    {
      "rules": [
        {
          "pattern": "*.mp4",
          "ttl": 86400,
          "priority": 1
        }
      ],
      "provider_id": "uuid"
    }
    ```
    """
    try:
        # Convert Pydantic models to dicts for service
        rules_dict = [rule.model_dump() for rule in request.rules]

        result = await cdn_service.configure_cache_rules(
            rules=rules_dict,
            provider_id=request.provider_id
        )

        logger.info(
            f"Cache rules configured by user {current_user.id}: "
            f"provider={request.provider_id}, applied={result.get('applied_rules', 0)}"
        )

        return ConfigureCacheRulesResponse(**result)
    except Exception as e:
        logger.error(f"Error configuring cache rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to configure cache rules"
        )
