"""
EdgeRoutingService for latency-based CDN routing and failover.

Manages:
- Latency-based routing to optimal edge locations
- Geographic proximity calculations
- Health-based failover between CDN regions
- Performance metrics collection
- Routing decisions based on real-time data

Uses EdgeLocation and EdgeHealthStatus from domain value objects
Integrates with CDNService for provider management
"""

import logging
import os
import math
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import and_

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from src.domain.value_objects.edge_location import EdgeLocation, EdgeHealthStatus
from src.domain.value_objects.cdn_config import CDNProviderType
from src.models import CDNConfig
from src.services.cdn_service import CDNService
from src.application.ports.i_cdn_provider import CDNHealthStatus as ProviderHealthStatus

logger = logging.getLogger(__name__)

# Redis keys for edge routing cache
EDGE_LATENCY_KEY = "edge:latency:{from_location}:{to_location}"
EDGE_HEALTH_KEY = "edge:health:{provider}:{location_code}"
EDGE_ROUTING_DECISION_KEY = "edge:decision:{client_location}"
EDGE_METRICS_KEY = "edge:metrics:{provider}:{location_code}"

# TTL values
LATENCY_TTL = 300  # 5 minutes - latency measurements change frequently
HEALTH_TTL = 60  # 1 minute - health status needs to be fresh
ROUTING_DECISION_TTL = 600  # 10 minutes - routing decisions can be cached
METRICS_TTL = 3600  # 1 hour - metrics are historical


@dataclass
class RoutingDecision:
    """
    Represents a routing decision for a client request.

    **Attributes**:
    - provider: CDN provider to use
    - location: Edge location to route to
    - reason: Why this routing decision was made
    - score: Routing score (higher is better)
    - confidence: Confidence level (0-1)
    """
    provider: str
    location: EdgeLocation
    reason: str
    score: float
    confidence: float


@dataclass
class LatencyMeasurement:
    """
    Represents a latency measurement between two points.

    **Attributes**:
    - from_location: Origin location (IATA code or "client")
    - to_location: Destination edge location
    - latency_ms: Measured latency in milliseconds
    - timestamp: When the measurement was taken
    - sample_size: Number of measurements averaged
    """
    from_location: str
    to_location: str
    latency_ms: float
    timestamp: str
    sample_size: int = 1


class EdgeRoutingService:
    """
    Service for intelligent edge routing and failover.

    **Core Responsibilities**:
    - Calculate optimal edge locations based on latency
    - Implement geographic proximity routing
    - Perform health-based failover
    - Collect and aggregate performance metrics
    - Make real-time routing decisions

    **Routing Strategy**:
    1. Health check: Filter out unhealthy/degraded locations
    2. Latency scoring: Prefer locations with lower latency
    3. Geographic proximity: Prefer closer locations as fallback
    4. Provider priority: Use provider priority as final tiebreaker
    """

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize edge routing service.

        Args:
            db_session: SQLAlchemy database session (optional, will use get_db if not provided)
        """
        self._db = db_session
        self._owns_db = db_session is None
        self._redis: Optional[Any] = None
        self._cdn_service: Optional[CDNService] = None
        self.logger = logger

    @property
    def db(self) -> Session:
        """Get database session. Auto-creates if needed."""
        if self._db is None:
            from src.database import SessionLocal
            self._db = SessionLocal()
            self._owns_db = True
        return self._db

    @property
    def cdn_service(self) -> CDNService:
        """Get or create CDN service instance."""
        if self._cdn_service is None:
            self._cdn_service = CDNService(self.db)
        return self._cdn_service

    def close(self):
        """Close database session and cleanup resources if we own them."""
        if self._owns_db and self._db is not None:
            try:
                self._db.close()
            except Exception:
                pass
            self._db = None
            self._owns_db = False

        if self._cdn_service is not None:
            self._cdn_service.close()
            self._cdn_service = None

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

    async def get_optimal_edge(
        self,
        client_latitude: Optional[float] = None,
        client_longitude: Optional[float] = None,
        client_region: Optional[str] = None,
        provider_id: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[RoutingDecision]:
        """
        Get optimal edge location for a client request.

        **Routing Algorithm**:
        1. Get all available edge locations from enabled CDN providers
        2. Filter out unhealthy/degraded locations
        3. Score each location based on:
           - Cached latency measurements (primary factor)
           - Geographic distance (secondary factor)
           - Provider priority (tiebreaker)
        4. Return location with highest score

        Args:
            client_latitude: Client's latitude (for geo routing)
            client_longitude: Client's longitude (for geo routing)
            client_region: Client's region (e.g., "Europe", "Asia")
            provider_id: Optional CDN provider ID to restrict routing
            use_cache: Whether to use cached routing decisions

        Returns:
            RoutingDecision with optimal edge location, or None if no healthy edges available
        """
        try:
            # Generate cache key for routing decision
            cache_key = self._generate_routing_cache_key(
                client_latitude, client_longitude, client_region, provider_id
            )

            # Try cache first
            if use_cache:
                redis = await self._get_redis()
                if redis:
                    try:
                        cached = await redis.get(cache_key)
                        if cached:
                            import json
                            decision_data = json.loads(cached)
                            location = EdgeLocation(**decision_data["location"])
                            return RoutingDecision(
                                provider=decision_data["provider"],
                                location=location,
                                reason=decision_data["reason"],
                                score=decision_data["score"],
                                confidence=decision_data["confidence"]
                            )
                    except Exception as e:
                        self.logger.warning(f"Error reading routing decision from cache: {e}")

            # Get all edge locations
            locations = await self.cdn_service.list_edge_locations(
                provider_id=provider_id,
                use_cache=True
            )

            if not locations:
                self.logger.warning("No edge locations available for routing")
                return None

            # Get health status for all providers
            health_status = await self.cdn_service.get_health_status(
                provider_id=provider_id,
                use_cache=True
            )

            # Filter healthy providers
            healthy_providers = {
                p["id"]: p for p in health_status.get("providers", [])
                if p.get("status") == ProviderHealthStatus.HEALTHY
            }

            if not healthy_providers:
                self.logger.warning("No healthy CDN providers available")
                return None

            # Score each location
            scored_locations = []
            for loc_data in locations:
                # Skip if provider is not healthy
                provider_id_loc = loc_data.get("provider_id")
                if provider_id_loc not in healthy_providers:
                    continue

                try:
                    location = EdgeLocation(
                        code=loc_data["code"],
                        city=loc_data["city"],
                        country=loc_data["country"],
                        region=loc_data["region"],
                        latitude=loc_data["latitude"],
                        longitude=loc_data["longitude"],
                        active=loc_data.get("active", True)
                    )

                    # Skip inactive locations
                    if not location.active:
                        continue

                    # Calculate score
                    score, confidence, reason = await self._score_location(
                        location,
                        client_latitude,
                        client_longitude,
                        client_region,
                        loc_data["provider"]
                    )

                    scored_locations.append((score, confidence, reason, location, loc_data["provider"]))

                except Exception as e:
                    self.logger.warning(f"Error processing location {loc_data.get('code')}: {e}")
                    continue

            if not scored_locations:
                self.logger.warning("No valid locations after filtering")
                return None

            # Sort by score (descending)
            scored_locations.sort(key=lambda x: x[0], reverse=True)

            # Get best location
            best_score, best_confidence, best_reason, best_location, best_provider = scored_locations[0]

            decision = RoutingDecision(
                provider=best_provider,
                location=best_location,
                reason=best_reason,
                score=best_score,
                confidence=best_confidence
            )

            # Cache the decision
            if use_cache:
                redis = await self._get_redis()
                if redis:
                    try:
                        import json
                        decision_data = {
                            "provider": best_provider,
                            "location": {
                                "code": best_location.code,
                                "city": best_location.city,
                                "country": best_location.country,
                                "region": best_location.region,
                                "latitude": best_location.latitude,
                                "longitude": best_location.longitude,
                                "active": best_location.active
                            },
                            "reason": best_reason,
                            "score": best_score,
                            "confidence": best_confidence,
                            "cached_at": datetime.now(timezone.utc).isoformat()
                        }
                        await redis.setex(
                            cache_key,
                            ROUTING_DECISION_TTL,
                            json.dumps(decision_data)
                        )
                    except Exception as e:
                        self.logger.warning(f"Error caching routing decision: {e}")

            self.logger.info(
                f"Routing decision: {best_provider}/{best_location.code} "
                f"(score={best_score:.2f}, reason={best_reason})"
            )

            return decision

        except Exception as e:
            self.logger.error(f"Error getting optimal edge: {e}", exc_info=True)
            return None

    async def _score_location(
        self,
        location: EdgeLocation,
        client_latitude: Optional[float],
        client_longitude: Optional[float],
        client_region: Optional[str],
        provider: str
    ) -> Tuple[float, float, str]:
        """
        Calculate routing score for a location.

        **Scoring Factors**:
        1. Latency: Lower latency = higher score (0-40 points)
        2. Geographic proximity: Closer = higher score (0-30 points)
        3. Regional match: Same region = bonus (0-20 points)
        4. Provider priority: Higher priority = bonus (0-10 points)

        Args:
            location: Edge location to score
            client_latitude: Client's latitude
            client_longitude: Client's longitude
            client_region: Client's region
            provider: CDN provider name

        Returns:
            Tuple of (score, confidence, reason)
        """
        score = 0.0
        confidence = 0.5
        reasons = []

        # 1. Latency score (primary factor, 0-40 points)
        if client_latitude is not None and client_longitude is not None:
            latency = await self._get_cached_latency(
                "client", location.code
            )
            if latency and latency > 0:
                # Lower latency = higher score
                # 0ms = 40 points, 500ms+ = 0 points
                latency_score = max(0, 40 - (latency / 12.5))
                score += latency_score
                reasons.append(f"latency={latency:.0f}ms")
                confidence = 0.8
            else:
                # No latency data, use geographic distance as proxy
                distance = location.calculate_distance(client_latitude, client_longitude)
                # Closer = higher score
                # 0km = 30 points, 10000km+ = 0 points
                geo_score = max(0, 30 - (distance / 333))
                score += geo_score
                reasons.append(f"distance={distance:.0f}km")
                confidence = 0.6

        # 2. Regional match (0-20 points)
        if client_region and location.is_in_region(client_region):
            score += 20
            reasons.append("same_region")
            confidence = min(1.0, confidence + 0.1)

        # 3. Provider priority (0-10 points)
        try:
            config = self.db.query(CDNConfig).filter(
                and_(
                    CDNConfig.provider == provider,
                    CDNConfig.enabled == True
                )
            ).order_by(CDNConfig.priority.asc()).first()

            if config:
                # Lower priority number = higher priority
                # Priority 1 = 10 points, Priority 10+ = 0 points
                priority_score = max(0, 10 - config.priority)
                score += priority_score
                reasons.append(f"priority={config.priority}")
        except Exception as e:
            self.logger.warning(f"Error getting provider priority: {e}")

        reason = ", ".join(reasons) if reasons else "default"

        return score, confidence, reason

    async def _get_cached_latency(
        self,
        from_location: str,
        to_location: str
    ) -> Optional[float]:
        """
        Get cached latency measurement between two locations.

        Args:
            from_location: Origin location code
            to_location: Destination location code

        Returns:
            Latency in milliseconds, or None if not cached
        """
        redis = await self._get_redis()
        if not redis:
            return None

        try:
            key = EDGE_LATENCY_KEY.format(
                from_location=from_location,
                to_location=to_location
            )
            data = await redis.get(key)
            if data:
                import json
                measurement = json.loads(data)
                return measurement.get("latency_ms")
        except Exception as e:
            self.logger.warning(f"Error reading latency from cache: {e}")

        return None

    async def record_latency(
        self,
        from_location: str,
        to_location: str,
        latency_ms: float,
        sample_size: int = 1
    ) -> bool:
        """
        Record a latency measurement between two locations.

        Args:
            from_location: Origin location code
            to_location: Destination location code
            latency_ms: Measured latency in milliseconds
            sample_size: Number of measurements averaged

        Returns:
            True if recording successful
        """
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            key = EDGE_LATENCY_KEY.format(
                from_location=from_location,
                to_location=to_location
            )

            measurement = LatencyMeasurement(
                from_location=from_location,
                to_location=to_location,
                latency_ms=latency_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                sample_size=sample_size
            )

            import json
            await redis.setex(
                key,
                LATENCY_TTL,
                json.dumps(measurement.__dict__)
            )

            self.logger.debug(
                f"Recorded latency: {from_location}->{to_location} = {latency_ms:.2f}ms"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error recording latency: {e}", exc_info=True)
            return False

    async def get_edge_health(
        self,
        provider: str,
        location_code: str,
        use_cache: bool = True
    ) -> Optional[EdgeHealthStatus]:
        """
        Get health status for a specific edge location.

        Args:
            provider: CDN provider name
            location_code: Edge location IATA code
            use_cache: Whether to use cached health status

        Returns:
            EdgeHealthStatus or None if not available
        """
        if use_cache:
            redis = await self._get_redis()
            if redis:
                try:
                    key = EDGE_HEALTH_KEY.format(
                        provider=provider,
                        location_code=location_code
                    )
                    data = await redis.get(key)
                    if data:
                        import json
                        health_data = json.loads(data)
                        location = EdgeLocation(**health_data["location"])
                        return EdgeHealthStatus(
                            location=location,
                            status=health_data["status"],
                            response_time_ms=health_data["response_time_ms"],
                            last_check=health_data.get("last_check"),
                            error=health_data.get("error")
                        )
                except Exception as e:
                    self.logger.warning(f"Error reading edge health from cache: {e}")

        # Fetch from CDN service
        try:
            health_info = await self.cdn_service.get_health_status(use_cache=False)

            # Find matching location
            for provider_info in health_info.get("providers", []):
                if provider_info.get("provider") == provider:
                    # Create generic health status
                    # Note: CDN service tracks provider-level health, not per-location
                    # This is a simplified implementation
                    return EdgeHealthStatus(
                        location=EdgeLocation(
                            code=location_code,
                            city=location_code,
                            country="Unknown",
                            region="Unknown",
                            latitude=0,
                            longitude=0
                        ),
                        status=provider_info.get("status", "unhealthy"),
                        response_time_ms=provider_info.get("response_time_ms", 0),
                        last_check=provider_info.get("last_check")
                    )
        except Exception as e:
            self.logger.error(f"Error getting edge health: {e}", exc_info=True)

        return None

    async def record_edge_health(
        self,
        health_status: EdgeHealthStatus,
        provider: str
    ) -> bool:
        """
        Record health status for an edge location.

        Args:
            health_status: Edge health status to record
            provider: CDN provider name

        Returns:
            True if recording successful
        """
        redis = await self._get_redis()
        if not redis:
            return False

        try:
            key = EDGE_HEALTH_KEY.format(
                provider=provider,
                location_code=health_status.location.code
            )

            import json
            health_data = {
                "location": health_status.location.__dict__,
                "status": health_status.status,
                "response_time_ms": health_status.response_time_ms,
                "last_check": health_status.last_check or datetime.now(timezone.utc).isoformat(),
                "error": health_status.error
            }

            await redis.setex(
                key,
                HEALTH_TTL,
                json.dumps(health_data)
            )

            self.logger.debug(
                f"Recorded edge health: {provider}/{health_status.location.code} = {health_status.status}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error recording edge health: {e}", exc_info=True)
            return False

    async def get_routing_metrics(
        self,
        provider: Optional[str] = None,
        location_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get routing performance metrics.

        Args:
            provider: Optional CDN provider filter
            location_code: Optional location filter

        Returns:
            Dict with routing metrics
        """
        try:
            # Get health status
            health = await self.cdn_service.get_health_status(use_cache=True)

            # Get edge locations
            locations = await self.cdn_service.list_edge_locations(
                provider_id=provider,
                use_cache=True
            )

            # Aggregate metrics
            metrics = {
                "total_locations": len(locations),
                "healthy_providers": 0,
                "degraded_providers": 0,
                "unhealthy_providers": 0,
                "locations_by_region": {},
                "locations_by_provider": {},
                "average_response_time_ms": 0.0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

            # Count provider health
            for provider_info in health.get("providers", []):
                status = provider_info.get("status")
                if status == ProviderHealthStatus.HEALTHY:
                    metrics["healthy_providers"] += 1
                elif status == ProviderHealthStatus.DEGRADED:
                    metrics["degraded_providers"] += 1
                else:
                    metrics["unhealthy_providers"] += 1

                # Collect response times
                if provider_info.get("response_time_ms"):
                    metrics["average_response_time_ms"] += provider_info["response_time_ms"]

            # Calculate average response time
            total_providers = len(health.get("providers", []))
            if total_providers > 0:
                metrics["average_response_time_ms"] /= total_providers

            # Group locations by region
            for loc in locations:
                region = loc.get("region", "Unknown")
                if region not in metrics["locations_by_region"]:
                    metrics["locations_by_region"][region] = []
                metrics["locations_by_region"][region].append(loc["code"])

                # Group by provider
                prov = loc.get("provider", "Unknown")
                if prov not in metrics["locations_by_provider"]:
                    metrics["locations_by_provider"][prov] = []
                metrics["locations_by_provider"][prov].append(loc["code"])

            return metrics

        except Exception as e:
            self.logger.error(f"Error getting routing metrics: {e}", exc_info=True)
            return {
                "error": str(e),
                "total_locations": 0,
                "healthy_providers": 0,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

    def _generate_routing_cache_key(
        self,
        client_latitude: Optional[float],
        client_longitude: Optional[float],
        client_region: Optional[str],
        provider_id: Optional[str]
    ) -> str:
        """
        Generate cache key for routing decision.

        Args:
            client_latitude: Client's latitude
            client_longitude: Client's longitude
            client_region: Client's region
            provider_id: CDN provider ID

        Returns:
            Cache key string
        """
        # Round coordinates to 2 decimal places (~1km precision)
        lat_rounded = round(client_latitude, 2) if client_latitude is not None else "none"
        lon_rounded = round(client_longitude, 2) if client_longitude is not None else "none"

        # Use region if coordinates not available
        location_key = f"{lat_rounded},{lon_rounded}" if client_latitude else client_region or "global"

        return EDGE_ROUTING_DECISION_KEY.format(
            client_location=f"{location_key}:{provider_id or 'all'}"
        )

    async def failover_to_next_provider(
        self,
        current_provider_id: str
    ) -> Optional[str]:
        """
        Perform failover to next available CDN provider.

        Args:
            current_provider_id: Current provider ID that failed

        Returns:
            Next available provider ID, or None if no alternative available
        """
        try:
            # Get current provider priority
            current_config = self.db.query(CDNConfig).filter(
                CDNConfig.id == current_provider_id
            ).first()

            if not current_config:
                self.logger.error(f"Current provider {current_provider_id} not found")
                return None

            # Get next healthy provider with higher priority number
            next_config = self.db.query(CDNConfig).filter(
                and_(
                    CDNConfig.enabled == True,
                    CDNConfig.health_status == ProviderHealthStatus.HEALTHY,
                    CDNConfig.priority > current_config.priority
                )
            ).order_by(CDNConfig.priority.asc()).first()

            if next_config:
                self.logger.info(
                    f"Failing over from {current_config.name} (priority={current_config.priority}) "
                    f"to {next_config.name} (priority={next_config.priority})"
                )
                return str(next_config.id)

            self.logger.warning("No alternative healthy provider available for failover")
            return None

        except Exception as e:
            self.logger.error(f"Error during failover: {e}", exc_info=True)
            return None

    async def test_edge_connectivity(
        self,
        provider: str,
        location_code: str
    ) -> Dict[str, Any]:
        """
        Test connectivity to an edge location.

        Args:
            provider: CDN provider name
            location_code: Edge location code

        Returns:
            Dict with test results
        """
        result = {
            "success": False,
            "latency_ms": None,
            "error": None
        }

        try:
            import time
            start_time = time.time()

            # Get health status (this will actually contact the CDN)
            health = await self.cdn_service.get_health_status(use_cache=False)

            elapsed_ms = (time.time() - start_time) * 1000

            # Check if provider is healthy
            provider_healthy = False
            for provider_info in health.get("providers", []):
                if provider_info.get("provider") == provider:
                    provider_healthy = provider_info.get("status") == ProviderHealthStatus.HEALTHY
                    break

            result["success"] = provider_healthy
            result["latency_ms"] = round(elapsed_ms, 2)

            if not provider_healthy:
                result["error"] = "Provider not healthy"

        except Exception as e:
            self.logger.error(f"Error testing edge connectivity: {e}", exc_info=True)
            result["error"] = str(e)

        return result


def get_edge_routing_service(db: Session) -> EdgeRoutingService:
    """Factory function to get edge routing service instance."""
    return EdgeRoutingService(db)
