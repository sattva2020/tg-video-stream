"""
Feature 024: Global CDN Integration - Service Tests
Tests for CDN service operations including cache purging, health monitoring, and provider management.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.services.cdn_service import CDNService
from src.models.cdn_config import CDNConfig, CDNProviderType
from src.application.ports.i_cdn_provider import ICDNProvider, CDNHealthStatus
from src.domain.errors import (
    CDNConnectionError,
    CDNAuthenticationError,
    CDNPurgeError
)


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.query = MagicMock()
    session.commit = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def cdn_service(mock_db_session):
    """Create CDNService instance with mocked database."""
    service = CDNService(db_session=mock_db_session)
    yield service
    service.close()


@pytest.fixture
def mock_cloudflare_config():
    """Mock Cloudflare CDNConfig."""
    config = MagicMock(spec=CDNConfig)
    config.id = "123e4567-e89b-12d3-a456-426614174000"
    config.provider = CDNProviderType.CLOUDFLARE.value
    config.name = "Cloudflare CDN"
    config.api_token = "test_token_12345678901234567890"
    config.zone_id = "test_zone_id"
    config.account_id = "test_account_id"
    config.distribution_id = None
    config.service_id = None
    config.enabled = True
    config.priority = 1
    config.health_status = CDNHealthStatus.HEALTHY
    config.last_health_check = datetime.now(timezone.utc)
    config.last_error = None
    config.created_at = datetime.now(timezone.utc)
    config.updated_at = None
    return config


@pytest.fixture
def mock_cloudfront_config():
    """Mock CloudFront CDNConfig."""
    config = MagicMock(spec=CDNConfig)
    config.id = "223e4567-e89b-12d3-a456-426614174001"
    config.provider = CDNProviderType.CLOUDFRONT.value
    config.name = "CloudFront CDN"
    config.api_token = "test_access_key"
    config.zone_id = None
    config.account_id = None
    config.distribution_id = "test_distribution_id"
    config.service_id = None
    config.enabled = True
    config.priority = 2
    config.health_status = CDNHealthStatus.HEALTHY
    config.last_health_check = datetime.now(timezone.utc)
    config.last_error = None
    config.created_at = datetime.now(timezone.utc)
    config.updated_at = None
    return config


@pytest.fixture
def mock_cdn_client():
    """Mock CDN client."""
    client = AsyncMock(spec=ICDNProvider)

    # Configure async context manager support
    async def mock_enter():
        return client

    async def mock_exit(*args):
        pass

    client.__aenter__ = mock_enter
    client.__aexit__ = mock_exit

    return client


class TestListProviders:
    """Tests for list_providers method."""

    @pytest.mark.asyncio
    async def test_list_enabled_providers(self, cdn_service, mock_db_session, mock_cloudflare_config):
        """Test listing enabled CDN providers."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config]

        providers = await cdn_service.list_providers(enabled_only=True)

        assert len(providers) == 1
        assert providers[0]["provider"] == CDNProviderType.CLOUDFLARE.value
        assert providers[0]["name"] == "Cloudflare CDN"
        assert providers[0]["enabled"] is True
        assert providers[0]["api_token"].startswith("test_tok")
        assert providers[0]["api_token"].endswith("3456")

    @pytest.mark.asyncio
    async def test_list_all_providers(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cloudfront_config):
        """Test listing all CDN providers including disabled."""
        mock_cloudfront_config.enabled = False

        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config, mock_cloudfront_config]

        providers = await cdn_service.list_providers(enabled_only=False)

        assert len(providers) == 2
        assert providers[0]["provider"] == CDNProviderType.CLOUDFLARE.value
        assert providers[1]["provider"] == CDNProviderType.CLOUDFRONT.value

    @pytest.mark.asyncio
    async def test_list_providers_empty(self, cdn_service, mock_db_session):
        """Test listing providers when none exist."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []

        providers = await cdn_service.list_providers()

        assert providers == []


class TestGetProvider:
    """Tests for get_provider method."""

    @pytest.mark.asyncio
    async def test_get_provider_success(self, cdn_service, mock_db_session, mock_cloudflare_config):
        """Test getting a specific provider by ID."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_cloudflare_config

        provider = await cdn_service.get_provider(str(mock_cloudflare_config.id))

        assert provider is not None
        assert provider["id"] == mock_cloudflare_config.id
        assert provider["provider"] == CDNProviderType.CLOUDFLARE.value
        assert provider["name"] == "Cloudflare CDN"

    @pytest.mark.asyncio
    async def test_get_provider_not_found(self, cdn_service, mock_db_session):
        """Test getting a non-existent provider."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        provider = await cdn_service.get_provider("non-existent-id")

        assert provider is None


class TestPurgeCache:
    """Tests for purge_cache method."""

    @pytest.mark.asyncio
    async def test_purge_cache_single_provider(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cdn_client):
        """Test purging cache from a single provider."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config]

        mock_cdn_client.purge_cache.return_value = {
            "success": True,
            "purged_urls": ["https://example.com/video1.mp4"],
            "error": None
        }

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            result = await cdn_service.purge_cache(
                urls=["https://example.com/video1.mp4"],
                provider_id=str(mock_cloudflare_config.id)
            )

        assert result["success"] is True
        assert len(result["providers"]) == 1
        assert result["providers"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_purge_cache_all_providers(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cloudfront_config, mock_cdn_client):
        """Test purging cache from all enabled providers."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config, mock_cloudfront_config]

        mock_cdn_client.purge_cache.return_value = {
            "success": True,
            "purged_urls": ["https://example.com/video1.mp4"],
            "error": None
        }

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            result = await cdn_service.purge_cache(
                urls=["https://example.com/video1.mp4"]
            )

        assert result["success"] is True
        assert len(result["providers"]) == 2

    @pytest.mark.asyncio
    async def test_purge_cache_all(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cdn_client):
        """Test purging entire cache."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config]

        mock_cdn_client.purge_cache.return_value = {
            "success": True,
            "purged_urls": [],
            "error": None
        }

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            result = await cdn_service.purge_cache(
                urls=[],
                purge_all=True
            )

        assert result["success"] is True
        mock_cdn_client.purge_cache.assert_called_with([], purge_all=True)

    @pytest.mark.asyncio
    async def test_purge_cache_partial_failure(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cloudfront_config, mock_cdn_client):
        """Test purge cache with some providers failing."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config, mock_cloudfront_config]

        # First call succeeds, second fails
        mock_cdn_client.purge_cache.side_effect = [
            {"success": True, "purged_urls": ["https://example.com/video1.mp4"], "error": None},
            {"success": False, "error": "Authentication failed"}
        ]

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            result = await cdn_service.purge_cache(
                urls=["https://example.com/video1.mp4"]
            )

        assert result["success"] is False
        assert len(result["providers"]) == 2
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_purge_cache_no_providers(self, cdn_service, mock_db_session):
        """Test purging cache when no providers are configured."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        result = await cdn_service.purge_cache(
            urls=["https://example.com/video1.mp4"]
        )

        assert result["success"] is False
        assert "No enabled CDN providers found" in result["errors"]


class TestGetHealthStatus:
    """Tests for get_health_status method."""

    @pytest.mark.asyncio
    async def test_get_health_status_single_provider(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cdn_client):
        """Test getting health status for a single provider."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config]

        mock_cdn_client.get_health_status.return_value = {
            "status": CDNHealthStatus.HEALTHY,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": 50.5,
            "edge_nodes_healthy": 250,
            "edge_nodes_total": 250
        }

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            result = await cdn_service.get_health_status(
                provider_id=str(mock_cloudflare_config.id),
                use_cache=False
            )

        assert result["overall_status"] == CDNHealthStatus.HEALTHY
        assert len(result["providers"]) == 1
        assert result["providers"][0]["status"] == CDNHealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_get_health_status_all_healthy(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cloudfront_config, mock_cdn_client):
        """Test health status when all providers are healthy."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config, mock_cloudfront_config]

        mock_cdn_client.get_health_status.return_value = {
            "status": CDNHealthStatus.HEALTHY,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": 50.0,
            "edge_nodes_healthy": 250,
            "edge_nodes_total": 250
        }

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            result = await cdn_service.get_health_status(use_cache=False)

        assert result["overall_status"] == CDNHealthStatus.HEALTHY
        assert len(result["providers"]) == 2

    @pytest.mark.asyncio
    async def test_get_health_status_degraded(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cloudfront_config, mock_cdn_client):
        """Test health status when one provider is degraded."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config, mock_cloudfront_config]

        mock_cdn_client.get_health_status.side_effect = [
            {
                "status": CDNHealthStatus.HEALTHY,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "response_time_ms": 50.0,
                "edge_nodes_healthy": 250,
                "edge_nodes_total": 250
            },
            {
                "status": CDNHealthStatus.DEGRADED,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "response_time_ms": 150.0,
                "edge_nodes_healthy": 200,
                "edge_nodes_total": 250
            }
        ]

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            result = await cdn_service.get_health_status(use_cache=False)

        assert result["overall_status"] == CDNHealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_get_health_status_unhealthy(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cdn_client):
        """Test health status when provider is unhealthy."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config]

        mock_cdn_client.get_health_status.return_value = {
            "status": CDNHealthStatus.UNHEALTHY,
            "last_check": datetime.now(timezone.utc).isoformat(),
            "response_time_ms": 0,
            "edge_nodes_healthy": 0,
            "edge_nodes_total": 250
        }

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            result = await cdn_service.get_health_status(use_cache=False)

        assert result["overall_status"] == CDNHealthStatus.UNHEALTHY


class TestListEdgeLocations:
    """Tests for list_edge_locations method."""

    @pytest.mark.asyncio
    async def test_list_edge_locations_single_provider(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cdn_client):
        """Test listing edge locations for a single provider."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config]

        mock_locations = [
            {
                "code": "AMS",
                "city": "Amsterdam",
                "country": "Netherlands",
                "region": "Europe",
                "latitude": 52.3676,
                "longitude": 4.9041,
                "active": True
            }
        ]
        mock_cdn_client.list_edge_locations.return_value = mock_locations

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            locations = await cdn_service.list_edge_locations(
                provider_id=str(mock_cloudflare_config.id),
                use_cache=False
            )

        assert len(locations) == 1
        assert locations[0]["code"] == "AMS"
        assert locations[0]["provider"] == CDNProviderType.CLOUDFLARE.value

    @pytest.mark.asyncio
    async def test_list_edge_locations_all_providers(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cloudfront_config, mock_cdn_client):
        """Test listing edge locations from all providers."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_cloudflare_config, mock_cloudfront_config]

        cloudflare_locations = [
            {
                "code": "AMS",
                "city": "Amsterdam",
                "country": "Netherlands",
                "region": "Europe",
                "latitude": 52.3676,
                "longitude": 4.9041,
                "active": True
            }
        ]

        cloudfront_locations = [
            {
                "code": "LHR",
                "city": "London",
                "country": "United Kingdom",
                "region": "Europe",
                "latitude": 51.4700,
                "longitude": -0.4543,
                "active": True
            }
        ]

        mock_cdn_client.list_edge_locations.side_effect = [
            cloudflare_locations,
            cloudfront_locations
        ]

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            locations = await cdn_service.list_edge_locations(use_cache=False)

        assert len(locations) == 2

    @pytest.mark.asyncio
    async def test_list_edge_locations_empty(self, cdn_service, mock_db_session):
        """Test listing edge locations when no providers exist."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []

        locations = await cdn_service.list_edge_locations()

        assert locations == []


class TestGetActiveProvider:
    """Tests for get_active_provider method."""

    @pytest.mark.asyncio
    async def test_get_active_provider_success(self, cdn_service, mock_db_session, mock_cloudflare_config):
        """Test getting the highest priority active provider."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = mock_cloudflare_config

        provider = await cdn_service.get_active_provider()

        assert provider is not None
        assert provider.id == mock_cloudflare_config.id

    @pytest.mark.asyncio
    async def test_get_active_provider_none_available(self, cdn_service, mock_db_session):
        """Test getting active provider when none are available."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.first.return_value = None

        provider = await cdn_service.get_active_provider()

        assert provider is None


class TestConfigureCacheRules:
    """Tests for configure_cache_rules method."""

    @pytest.mark.asyncio
    async def test_configure_cache_rules_success(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cdn_client):
        """Test configuring cache rules successfully."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_cloudflare_config

        rules = [
            {
                "pattern": "*.mp4",
                "cache_ttl": 86400,
                "cache_key_static": True,
                "browser_ttl": 3600
            }
        ]

        mock_cdn_client.configure_cache_rules.return_value = {
            "success": True,
            "applied_rules": 1,
            "error": None
        }

        with patch.object(cdn_service, '_get_client', return_value=mock_cdn_client):
            result = await cdn_service.configure_cache_rules(
                rules=rules,
                provider_id=str(mock_cloudflare_config.id)
            )

        assert result["success"] is True
        assert result["applied_rules"] == 1

    @pytest.mark.asyncio
    async def test_configure_cache_rules_provider_not_found(self, cdn_service, mock_db_session):
        """Test configuring cache rules for non-existent provider."""
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        rules = [{"pattern": "*.mp4", "cache_ttl": 86400}]

        result = await cdn_service.configure_cache_rules(
            rules=rules,
            provider_id="non-existent-id"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestContextManager:
    """Tests for context manager functionality."""

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, mock_db_session):
        """Test that context manager properly closes resources."""
        async with CDNService(db_session=mock_db_session) as service:
            # Service should be usable within context
            assert service is not None

        # After exiting, db session should be closed
        mock_db_session.close.assert_called_once()


class TestClientCaching:
    """Tests for CDN client caching."""

    @pytest.mark.asyncio
    async def test_client_reuse(self, cdn_service, mock_db_session, mock_cloudflare_config, mock_cdn_client):
        """Test that CDN clients are cached and reused."""
        config_id = str(mock_cloudflare_config.id)

        with patch.object(cdn_service, '_create_client', return_value=mock_cdn_client) as mock_create:
            # First call creates client
            client1 = await cdn_service._get_client(mock_cloudflare_config)
            # Second call should reuse cached client
            client2 = await cdn_service._get_client(mock_cloudflare_config)

            # Should only create client once
            mock_create.assert_called_once()
            assert client1 is client2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
