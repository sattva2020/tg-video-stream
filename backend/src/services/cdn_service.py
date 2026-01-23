"""
CDNService for managing CDN providers and caching logic.

Manages:
- Multiple CDN provider configurations (Cloudflare, CloudFront, Fastly)
- Cache purging across providers
- Health status monitoring
- Edge location management
- Provider failover and priority routing

Uses CDNConfig model from src.models.cdn_config
Database fields: id (UUID), provider, name, api_token, zone_id, distribution_id,
                service_id, account_id, enabled, priority, health_status
"""

import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from src.models import CDNConfig
from src.database import get_db
from src.application.ports.i_cdn_provider import ICDNProvider, CDNHealthStatus

# Dynamic imports for CDN clients
try:
    from src.infrastructure.external.cloudflare_client import CloudflareCDNClient
except ImportError:
    CloudflareCDNClient = None

try:
    from src.infrastructure.external.cloudfront_client import CloudFrontCDNClient
except ImportError:
    CloudFrontCDNClient = None

try:
    from src.infrastructure.external.fastly_client import FastlyCDNClient
except ImportError:
    FastlyCDNClient = None

from src.domain.errors import (
    CDNConnectionError,
    CDNAuthenticationError,
    CDNPurgeError
)

logger = logging.getLogger(__name__)

# Redis keys for CDN status caching
CDN_HEALTH_KEY = "cdn:health:{config_id}"
CDN_HEALTH_TTL = 300  # 5 minutes
CDN_LOCATIONS_KEY = "cdn:locations:{provider}"
CDN_LOCATIONS_TTL = 3600  # 1 hour


class CDNService:
    """
    Service for managing CDN providers and caching operations.

    Uses CDNConfig model with fields:
    - id: UUID primary key
    - provider: cloudflare/cloudfront/fastly
    - name: Configuration name
    - api_token: API authentication token
    - zone_id: Cloudflare zone ID
    - distribution_id: CloudFront distribution ID
    - service_id: Fastly service ID
    - account_id: Cloudflare account ID
    - enabled: Whether the configuration is active
    - priority: Failover priority order
    - health_status: Current health state
    """

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize CDN service.

        Args:
            db_session: SQLAlchemy database session (optional, will use get_db if not provided)
        """
        self._db = db_session
        self._owns_db = db_session is None
        self._redis: Optional[Any] = None
        self._client_cache: Dict[str, ICDNProvider] = {}
        self.logger = logger

    @property
    def db(self) -> Session:
        """Get database session. Auto-creates if needed."""
        if self._db is None:
            from src.database import SessionLocal
            self._db = SessionLocal()
            self._owns_db = True
        return self._db

    def close(self):
        """Close database session and cleanup resources if we own them."""
        if self._owns_db and self._db is not None:
            try:
                self._db.close()
            except Exception:
                pass
            self._db = None
            self._owns_db = False

        # Close cached CDN clients
        for client in self._client_cache.values():
            if hasattr(client, 'session') and client.session:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(client.session.close())
                except Exception:
                    pass
        self._client_cache.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
        return False

    async def _get_redis(self):
        """Get or create Redis connection for caching."""
        if aioredis is None:
            return None

        if self._redis is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                self._redis = aioredis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception as e:
                self.logger.warning(f"Redis connection failed: {e}")
                self._redis = None

        return self._redis

    def _create_client(self, config: CDNConfig) -> Optional[ICDNProvider]:
        """
        Create CDN client instance for configuration.

        Args:
            config: CDN configuration model

        Returns:
            CDN client instance or None if provider not available

        Raises:
            ValueError: If configuration is invalid
        """
        provider = config.provider.lower()

        if provider == "cloudflare" and CloudflareCDNClient:
            return CloudflareCDNClient(
                api_token=config.api_token,
                zone_id=config.zone_id,
                account_id=config.account_id
            )
        elif provider == "cloudfront" and CloudFrontCDNClient:
            return CloudFrontCDNClient(
                api_key=config.api_token,
                distribution_id=config.distribution_id
            )
        elif provider == "fastly" and FastlyCDNClient:
            return FastlyCDNClient(
                api_key=config.api_token,
                service_id=config.service_id
            )
        else:
            self.logger.error(f"Unsupported CDN provider: {provider}")
            return None

    async def _get_client(self, config: CDNConfig) -> Optional[ICDNProvider]:
        """
        Get or create CDN client for configuration with caching.

        Args:
            config: CDN configuration model

        Returns:
            CDN client instance or None
        """
        config_id = str(config.id)

        # Return cached client if available
        if config_id in self._client_cache:
            return self._client_cache[config_id]

        # Create new client
        client = self._create_client(config)
        if client:
            self._client_cache[config_id] = client

        return client

    async def list_providers(
        self,
        enabled_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all CDN provider configurations.

        Args:
            enabled_only: If True, filter by enabled=True

        Returns:
            List of CDN configuration dictionaries
        """
        try:
            query = self.db.query(CDNConfig)

            if enabled_only:
                query = query.filter(CDNConfig.enabled == True)

            # Order by priority (lower number = higher priority)
            query = query.order_by(CDNConfig.priority.asc(), CDNConfig.created_at.desc())

            configs = query.all()

            result = []
            for config in configs:
                config_dict = {
                    "id": str(config.id),
                    "provider": config.provider,
                    "name": config.name,
                    "enabled": config.enabled,
                    "priority": config.priority,
                    "health_status": config.health_status,
                    "last_health_check": config.last_health_check.isoformat() if config.last_health_check else None,
                    "last_error": config.last_error,
                    "zone_id": config.zone_id,
                    "distribution_id": config.distribution_id,
                    "service_id": config.service_id,
                    "account_id": config.account_id,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    # Hide most of the API token
                    "api_token": f"{config.api_token[:8]}...{config.api_token[-4:]}" if config.api_token else None
                }

                result.append(config_dict)

            self.logger.debug(f"Listed {len(result)} CDN providers")
            return result

        except Exception as e:
            self.logger.error(f"Error listing CDN providers: {e}", exc_info=True)
            return []

    async def get_provider(self, config_id: str) -> Optional[Dict[str, Any]]:
        """
        Get CDN provider configuration by ID.

        Args:
            config_id: CDN configuration UUID

        Returns:
            CDN configuration dictionary or None if not found
        """
        try:
            config = self.db.query(CDNConfig).filter(
                CDNConfig.id == config_id
            ).first()

            if not config:
                return None

            return {
                "id": str(config.id),
                "provider": config.provider,
                "name": config.name,
                "enabled": config.enabled,
                "priority": config.priority,
                "health_status": config.health_status,
                "last_health_check": config.last_health_check.isoformat() if config.last_health_check else None,
                "last_error": config.last_error,
                "zone_id": config.zone_id,
                "distribution_id": config.distribution_id,
                "service_id": config.service_id,
                "account_id": config.account_id,
                "created_at": config.created_at.isoformat() if config.created_at else None,
                # Hide most of the API token
                "api_token": f"{config.api_token[:8]}...{config.api_token[-4:]}" if config.api_token else None
            }

        except Exception as e:
            self.logger.error(f"Error getting CDN provider {config_id}: {e}", exc_info=True)
            return None

    async def purge_cache(
        self,
        urls: List[str],
        provider_id: Optional[str] = None,
        purge_all: bool = False
    ) -> Dict[str, Any]:
        """
        Purge CDN cache for specified URLs.

        Args:
            urls: List of URLs to purge from cache
            provider_id: Optional CDN configuration ID (if None, purges from all enabled providers)
            purge_all: If True, purge entire cache

        Returns:
            Dict with purge results:
            {
                "success": bool,
                "purged_urls": List[str],
                "providers": List[dict],
                "errors": List[str]
            }
        """
        results = {
            "success": True,
            "purged_urls": urls if not purge_all else [],
            "providers": [],
            "errors": []
        }

        try:
            # Get configs to purge from
            if provider_id:
                configs = self.db.query(CDNConfig).filter(
                    and_(CDNConfig.id == provider_id, CDNConfig.enabled == True)
                ).all()
            else:
                configs = self.db.query(CDNConfig).filter(
                    CDNConfig.enabled == True
                ).all()

            if not configs:
                results["success"] = False
                results["errors"].append("No enabled CDN providers found")
                return results

            # Purge from each provider
            for config in configs:
                try:
                    client = await self._get_client(config)
                    if not client:
                        results["errors"].append(f"Could not create client for {config.name}")
                        continue

                    # Use async context manager if available
                    if hasattr(client, '__aenter__'):
                        async with client:
                            purge_result = await client.purge_cache(urls, purge_all=purge_all)
                    else:
                        purge_result = await client.purge_cache(urls, purge_all=purge_all)

                    results["providers"].append({
                        "id": str(config.id),
                        "name": config.name,
                        "provider": config.provider,
                        "success": purge_result.get("success", False),
                        "error": purge_result.get("error")
                    })

                    if not purge_result.get("success"):
                        results["success"] = False
                        results["errors"].append(f"{config.name}: {purge_result.get('error')}")

                except (CDNConnectionError, CDNAuthenticationError, CDNPurgeError) as e:
                    self.logger.error(f"Error purging cache from {config.name}: {e}")
                    results["success"] = False
                    results["errors"].append(f"{config.name}: {str(e)}")
                    results["providers"].append({
                        "id": str(config.id),
                        "name": config.name,
                        "provider": config.provider,
                        "success": False,
                        "error": str(e)
                    })

            self.logger.info(f"Cache purge completed: success={results['success']}, providers={len(results['providers'])}")
            return results

        except Exception as e:
            self.logger.error(f"Unexpected error during cache purge: {e}", exc_info=True)
            results["success"] = False
            results["errors"].append(f"Unexpected error: {str(e)}")
            return results

    async def get_health_status(
        self,
        provider_id: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get health status of CDN providers.

        Args:
            provider_id: Optional CDN configuration ID (if None, checks all enabled providers)
            use_cache: Whether to use cached health status

        Returns:
            Dict with health status:
            {
                "overall_status": "healthy" | "degraded" | "unhealthy",
                "providers": List[dict],
                "last_check": datetime
            }
        """
        result = {
            "overall_status": CDNHealthStatus.HEALTHY,
            "providers": [],
            "last_check": datetime.now(timezone.utc).isoformat()
        }

        try:
            # Get configs to check
            if provider_id:
                configs = self.db.query(CDNConfig).filter(
                    and_(CDNConfig.id == provider_id, CDNConfig.enabled == True)
                ).all()
            else:
                configs = self.db.query(CDNConfig).filter(
                    CDNConfig.enabled == True
                ).order_by(CDNConfig.priority.asc()).all()

            if not configs:
                result["overall_status"] = CDNHealthStatus.UNHEALTHY
                return result

            redis = await self._get_redis() if use_cache else None
            unhealthy_count = 0
            degraded_count = 0

            for config in configs:
                config_id = str(config.id)
                health_info = {
                    "id": config_id,
                    "name": config.name,
                    "provider": config.provider,
                    "status": CDNHealthStatus.UNHEALTHY,
                    "response_time_ms": 0,
                    "last_check": None
                }

                # Try to get from cache first
                if redis and use_cache:
                    try:
                        cached_health = await redis.get(f"{CDN_HEALTH_KEY}:{config_id}")
                        if cached_health:
                            import json
                            health_info.update(json.loads(cached_health))
                            result["providers"].append(health_info)

                            if health_info["status"] == CDNHealthStatus.UNHEALTHY:
                                unhealthy_count += 1
                            elif health_info["status"] == CDNHealthStatus.DEGRADED:
                                degraded_count += 1

                            continue
                    except Exception as e:
                        self.logger.warning(f"Error reading health from cache: {e}")

                # Fetch health from provider
                try:
                    client = await self._get_client(config)
                    if not client:
                        health_info["status"] = CDNHealthStatus.UNHEALTHY
                        health_info["error"] = "Could not create client"
                    else:
                        if hasattr(client, '__aenter__'):
                            async with client:
                                provider_health = await client.get_health_status()
                        else:
                            provider_health = await client.get_health_status()

                        health_info["status"] = provider_health.get("status", CDNHealthStatus.UNHEALTHY)
                        health_info["response_time_ms"] = provider_health.get("response_time_ms", 0)
                        health_info["last_check"] = provider_health.get("last_check")
                        health_info["edge_nodes_healthy"] = provider_health.get("edge_nodes_healthy", 0)
                        health_info["edge_nodes_total"] = provider_health.get("edge_nodes_total", 0)

                        # Update database
                        config.update_health_status(health_info["status"])
                        self.db.commit()

                        # Cache the result
                        if redis:
                            try:
                                import json
                                await redis.setex(
                                    f"{CDN_HEALTH_KEY}:{config_id}",
                                    CDN_HEALTH_TTL,
                                    json.dumps(health_info)
                                )
                            except Exception as e:
                                self.logger.warning(f"Error caching health status: {e}")

                except (CDNConnectionError, CDNAuthenticationError) as e:
                    self.logger.error(f"Error checking health for {config.name}: {e}")
                    health_info["status"] = CDNHealthStatus.UNHEALTHY
                    health_info["error"] = str(e)

                    # Update database as unhealthy
                    config.mark_as_unhealthy(str(e))
                    self.db.commit()

                result["providers"].append(health_info)

                if health_info["status"] == CDNHealthStatus.UNHEALTHY:
                    unhealthy_count += 1
                elif health_info["status"] == CDNHealthStatus.DEGRADED:
                    degraded_count += 1

            # Determine overall status
            total = len(result["providers"])
            if unhealthy_count == total:
                result["overall_status"] = CDNHealthStatus.UNHEALTHY
            elif unhealthy_count > 0 or degraded_count > 0:
                result["overall_status"] = CDNHealthStatus.DEGRADED
            else:
                result["overall_status"] = CDNHealthStatus.HEALTHY

            self.logger.debug(f"Health check completed: {result['overall_status']}, providers={total}")
            return result

        except Exception as e:
            self.logger.error(f"Error checking health status: {e}", exc_info=True)
            result["overall_status"] = CDNHealthStatus.UNHEALTHY
            result["error"] = str(e)
            return result

    async def list_edge_locations(
        self,
        provider_id: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List available edge locations for CDN providers.

        Args:
            provider_id: Optional CDN configuration ID (if None, gets from all enabled providers)
            use_cache: Whether to use cached edge locations

        Returns:
            List of edge location dictionaries:
            [
                {
                    "provider": str,
                    "code": "AMS",
                    "city": "Amsterdam",
                    "country": "Netherlands",
                    "region": "Europe",
                    "latitude": float,
                    "longitude": float,
                    "active": bool
                }
            ]
        """
        all_locations = []

        try:
            # Get configs
            if provider_id:
                configs = self.db.query(CDNConfig).filter(
                    and_(CDNConfig.id == provider_id, CDNConfig.enabled == True)
                ).all()
            else:
                configs = self.db.query(CDNConfig).filter(
                    CDNConfig.enabled == True
                ).all()

            if not configs:
                return []

            redis = await self._get_redis() if use_cache else None

            for config in configs:
                # Try cache first
                if redis and use_cache:
                    try:
                        cache_key = f"{CDN_LOCATIONS_KEY}:{config.provider}"
                        cached_locations = await redis.get(cache_key)
                        if cached_locations:
                            import json
                            locations = json.loads(cached_locations)
                            all_locations.extend(locations)
                            continue
                    except Exception as e:
                        self.logger.warning(f"Error reading locations from cache: {e}")

                # Fetch from provider
                try:
                    client = await self._get_client(config)
                    if not client:
                        continue

                    if hasattr(client, '__aenter__'):
                        async with client:
                            locations = await client.list_edge_locations()
                    else:
                        locations = await client.list_edge_locations()

                    # Add provider info to each location
                    for loc in locations:
                        loc["provider"] = config.provider
                        loc["provider_id"] = str(config.id)

                    all_locations.extend(locations)

                    # Cache the results
                    if redis:
                        try:
                            import json
                            cache_key = f"{CDN_LOCATIONS_KEY}:{config.provider}"
                            await redis.setex(
                                cache_key,
                                CDN_LOCATIONS_TTL,
                                json.dumps(locations)
                            )
                        except Exception as e:
                            self.logger.warning(f"Error caching edge locations: {e}")

                except (CDNConnectionError, CDNAuthenticationError) as e:
                    self.logger.error(f"Error getting edge locations from {config.name}: {e}")

            self.logger.debug(f"Retrieved {len(all_locations)} edge locations")
            return all_locations

        except Exception as e:
            self.logger.error(f"Error listing edge locations: {e}", exc_info=True)
            return []

    async def get_active_provider(self) -> Optional[CDNConfig]:
        """
        Get the highest priority active CDN provider.

        Returns:
            CDNConfig with highest priority (lowest priority number) that is enabled and healthy

        """
        try:
            config = self.db.query(CDNConfig).filter(
                and_(
                    CDNConfig.enabled == True,
                    CDNConfig.health_status == CDNHealthStatus.HEALTHY
                )
            ).order_by(CDNConfig.priority.asc()).first()

            return config

        except Exception as e:
            self.logger.error(f"Error getting active provider: {e}", exc_info=True)
            return None

    async def configure_cache_rules(
        self,
        rules: List[Dict[str, Any]],
        provider_id: str
    ) -> Dict[str, Any]:
        """
        Configure cache rules for a CDN provider.

        Args:
            rules: List of cache rule dictionaries
            provider_id: CDN configuration ID

        Returns:
            Dict with configuration result
        """
        result = {
            "success": False,
            "applied_rules": 0,
            "error": None
        }

        try:
            config = self.db.query(CDNConfig).filter(
                CDNConfig.id == provider_id
            ).first()

            if not config:
                result["error"] = "CDN configuration not found"
                return result

            client = await self._get_client(config)
            if not client:
                result["error"] = "Could not create CDN client"
                return result

            if hasattr(client, '__aenter__'):
                async with client:
                    config_result = await client.configure_cache_rules(rules)
            else:
                config_result = await client.configure_cache_rules(rules)

            result.update(config_result)

            self.logger.info(f"Configured {result.get('applied_rules', 0)} cache rules for {config.name}")
            return result

        except Exception as e:
            self.logger.error(f"Error configuring cache rules: {e}", exc_info=True)
            result["error"] = str(e)
            return result
