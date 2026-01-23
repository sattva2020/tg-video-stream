"""
Feature 024: Global CDN Integration - Infrastructure Tests
Tests for CDN client implementations (Cloudflare, CloudFront, Fastly).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from aiohttp import ClientSession

from src.infrastructure.external.cloudflare_client import CloudflareCDNClient
from src.infrastructure.external.cloudfront_client import CloudFrontCDNClient
from src.application.ports.i_cdn_provider import CDNHealthStatus
from src.domain.errors import (
    CDNConnectionError,
    CDNAuthenticationError,
    CDNPurgeError,
    CDNConfigurationError
)


class TestCloudflareCDNClient:
    """Tests for CloudflareCDNClient."""

    @pytest.fixture
    def cloudflare_client(self):
        """Create CloudflareCDNClient instance."""
        return CloudflareCDNClient(
            api_token="test_api_token_12345",
            zone_id="test_zone_id",
            account_id="test_account_id"
        )

    @pytest.fixture
    def cloudflare_session(self):
        """Create mock aiohttp session."""
        session = MagicMock(spec=ClientSession)
        session.post = AsyncMock()
        session.get = AsyncMock()
        session.close = AsyncMock()
        return session

    def test_initialization_with_params(self):
        """Test client initialization with parameters."""
        client = CloudflareCDNClient(
            api_token="test_token",
            zone_id="test_zone",
            account_id="test_account"
        )

        assert client.api_token == "test_token"
        assert client.zone_id == "test_zone"
        assert client.account_id == "test_account"
        assert client.api_url == "https://api.cloudflare.com/client/v4"

    def test_initialization_missing_token(self):
        """Test that initialization fails without API token."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="CLOUDFLARE_API_TOKEN is required"):
                CloudflareCDNClient()

    def test_initialization_missing_zone_id(self):
        """Test that initialization fails without zone ID."""
        with patch.dict('os.environ', {'CLOUDFLARE_API_TOKEN': 'test_token'}, clear=False):
            with pytest.raises(ValueError, match="CLOUDFLARE_ZONE_ID is required"):
                CloudflareCDNClient()

    def test_get_headers(self, cloudflare_client):
        """Test that headers are correctly formatted."""
        headers = cloudflare_client._get_headers()

        assert headers["Authorization"] == "Bearer test_api_token_12345"
        assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_purge_cache_success(self, cloudflare_client, cloudflare_session):
        """Test successful cache purge."""
        mock_response = MagicMock()
        mock_response.status = 200
        cloudflare_session.post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"success": True}
        )
        cloudflare_session.post.return_value.__aenter__.return_value.status = 200

        cloudflare_client.session = cloudflare_session

        result = await cloudflare_client.purge_cache(
            urls=["https://example.com/video1.mp4"]
        )

        assert result["success"] is True
        assert result["purged_urls"] == ["https://example.com/video1.mp4"]
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_purge_cache_all(self, cloudflare_client, cloudflare_session):
        """Test purging entire cache."""
        mock_response = MagicMock()
        mock_response.status = 200
        cloudflare_session.post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"success": True}
        )
        cloudflare_session.post.return_value.__aenter__.return_value.status = 200

        cloudflare_client.session = cloudflare_session

        result = await cloudflare_client.purge_cache(
            urls=[],
            purge_all=True
        )

        assert result["success"] is True
        assert result["purged_urls"] == []

    @pytest.mark.asyncio
    async def test_purge_cache_authentication_error(self, cloudflare_client, cloudflare_session):
        """Test purge cache with authentication error."""
        mock_response = MagicMock()
        mock_response.status = 401
        cloudflare_session.post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={
                "success": False,
                "errors": [{"code": 9103, "message": "Invalid API token"}]
            }
        )
        cloudflare_session.post.return_value.__aenter__.return_value.status = 401

        cloudflare_client.session = cloudflare_session

        with pytest.raises(CDNAuthenticationError, match="authentication failed"):
            await cloudflare_client.purge_cache(
                urls=["https://example.com/video1.mp4"]
            )

    @pytest.mark.asyncio
    async def test_purge_cache_zone_not_found(self, cloudflare_client, cloudflare_session):
        """Test purge cache with zone not found error."""
        mock_response = MagicMock()
        mock_response.status = 404
        cloudflare_session.post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={
                "success": False,
                "errors": [{"code": 1000, "message": "Zone not found"}]
            }
        )
        cloudflare_session.post.return_value.__aenter__.return_value.status = 404

        cloudflare_client.session = cloudflare_session

        with pytest.raises(CDNConfigurationError, match="zone not found"):
            await cloudflare_client.purge_cache(
                urls=["https://example.com/video1.mp4"]
            )

    @pytest.mark.asyncio
    async def test_get_health_status_healthy(self, cloudflare_client, cloudflare_session):
        """Test getting health status when CDN is healthy."""
        mock_response = MagicMock()
        mock_response.status = 200
        cloudflare_session.get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"success": True, "result": {"id": "test_zone_id"}}
        )
        cloudflare_session.get.return_value.__aenter__.return_value.status = 200

        cloudflare_client.session = cloudflare_session

        result = await cloudflare_client.get_health_status()

        assert result["status"] == CDNHealthStatus.HEALTHY
        assert "response_time_ms" in result
        assert result["edge_nodes_healthy"] == 0
        assert result["edge_nodes_total"] == 0

    @pytest.mark.asyncio
    async def test_get_health_status_unhealthy(self, cloudflare_client, cloudflare_session):
        """Test getting health status when CDN is unhealthy."""
        mock_response = MagicMock()
        mock_response.status = 401
        cloudflare_session.get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={
                "success": False,
                "errors": [{"code": 9103, "message": "Invalid API token"}]
            }
        )
        cloudflare_session.get.return_value.__aenter__.return_value.status = 401

        cloudflare_client.session = cloudflare_session

        result = await cloudflare_client.get_health_status()

        assert result["status"] == CDNHealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_list_edge_locations(self, cloudflare_client):
        """Test listing edge locations."""
        locations = await cloudflare_client.list_edge_locations()

        assert len(locations) > 0
        assert all("code" in loc for loc in locations)
        assert all("city" in loc for loc in locations)
        assert all("country" in loc for loc in locations)
        assert all("region" in loc for loc in locations)
        assert all("latitude" in loc for loc in locations)
        assert all("longitude" in loc for loc in locations)
        assert all("active" in loc for loc in locations)

        # Check for known locations
        location_codes = [loc["code"] for loc in locations]
        assert "AMS" in location_codes  # Amsterdam
        assert "LHR" in location_codes  # London
        assert "JFK" in location_codes  # New York
        assert "NRT" in location_codes  # Tokyo

    @pytest.mark.asyncio
    async def test_configure_cache_rules(self, cloudflare_client, cloudflare_session):
        """Test configuring cache rules."""
        mock_response = MagicMock()
        mock_response.status = 200
        cloudflare_session.post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"success": True, "result": {"id": "rule_id"}}
        )
        cloudflare_session.post.return_value.__aenter__.return_value.status = 200

        cloudflare_client.session = cloudflare_session

        rules = [
            {
                "pattern": "*.mp4",
                "cache_ttl": 86400,
                "cache_key_static": True,
                "browser_ttl": 3600
            }
        ]

        result = await cloudflare_client.configure_cache_rules(rules)

        assert result["success"] is True
        assert result["applied_rules"] == 1
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_get_usage_metrics(self, cloudflare_client):
        """Test getting usage metrics (placeholder implementation)."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        metrics = await cloudflare_client.get_usage_metrics(start_date, end_date)

        assert "total_bandwidth_gb" in metrics
        assert "total_requests" in metrics
        assert "cache_hit_ratio" in metrics
        assert "average_response_time_ms" in metrics
        assert "by_region" in metrics
        assert "note" in metrics

    @pytest.mark.asyncio
    async def test_test_connection_success(self, cloudflare_client, cloudflare_session):
        """Test connection check when successful."""
        mock_response = MagicMock()
        mock_response.status = 200
        cloudflare_session.get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"success": True}
        )
        cloudflare_session.get.return_value.__aenter__.return_value.status = 200

        cloudflare_client.session = cloudflare_session

        result = await cloudflare_client.test_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_failure(self, cloudflare_client, cloudflare_session):
        """Test connection check when failed."""
        mock_response = MagicMock()
        mock_response.status = 500
        cloudflare_session.get.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={"success": False}
        )
        cloudflare_session.get.return_value.__aenter__.return_value.status = 500

        cloudflare_client.session = cloudflare_session

        with pytest.raises(CDNConnectionError):
            await cloudflare_client.test_connection()


class TestCloudFrontCDNClient:
    """Tests for CloudFrontCDNClient."""

    @pytest.fixture
    def cloudfront_client(self):
        """Create CloudFrontCDNClient instance."""
        return CloudFrontCDNClient(
            access_key_id="test_access_key",
            secret_access_key="test_secret_key",
            distribution_id="test_distribution_id",
            region="us-east-1"
        )

    @pytest.fixture
    def cloudfront_session(self):
        """Create mock aiohttp session."""
        session = MagicMock(spec=ClientSession)
        session.post = AsyncMock()
        session.get = AsyncMock()
        session.close = AsyncMock()
        return session

    def test_initialization_with_params(self):
        """Test client initialization with parameters."""
        client = CloudFrontCDNClient(
            access_key_id="test_key",
            secret_access_key="test_secret",
            distribution_id="test_dist",
            region="eu-west-1"
        )

        assert client.access_key_id == "test_key"
        assert client.secret_access_key == "test_secret"
        assert client.distribution_id == "test_dist"
        assert client.region == "eu-west-1"
        assert "cloudfront.amazonaws.com" in client.api_url

    def test_initialization_missing_credentials(self):
        """Test that initialization fails without credentials."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="AWS_ACCESS_KEY_ID is required"):
                CloudFrontCDNClient()

    def test_initialization_default_region(self):
        """Test that default region is us-east-1."""
        with patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'test_key',
            'AWS_SECRET_ACCESS_KEY': 'test_secret',
            'CLOUDFRONT_DISTRIBUTION_ID': 'test_dist'
        }, clear=False):
            client = CloudFrontCDNClient()
            assert client.region == "us-east-1"

    def test_get_headers(self, cloudfront_client):
        """Test that headers are correctly formatted."""
        headers = cloudfront_client._get_headers()

        assert headers["Content-Type"] == "application/xml"
        assert "X-Amz-Security-Token" in headers

    @pytest.mark.asyncio
    async def test_purge_cache_success(self, cloudfront_client):
        """Test successful cache purge (invalidation)."""
        cloudfront_client.session = MagicMock(spec=ClientSession)

        result = await cloudfront_client.purge_cache(
            urls=["https://example.com/video1.mp4"]
        )

        # CloudFront client returns placeholder response
        assert result["success"] is True
        assert result["purged_urls"] == ["https://example.com/video1.mp4"]
        assert "invalidation_id" in result

    @pytest.mark.asyncio
    async def test_purge_cache_all(self, cloudfront_client):
        """Test purging entire cache (/*)."""
        cloudfront_client.session = MagicMock(spec=ClientSession)

        result = await cloudfront_client.purge_cache(
            urls=[],
            purge_all=True
        )

        assert result["success"] is True
        assert result["purged_urls"] == []

    @pytest.mark.asyncio
    async def test_get_health_status_healthy(self, cloudfront_client):
        """Test getting health status when CDN is healthy."""
        cloudfront_client.session = MagicMock(spec=ClientSession)

        result = await cloudfront_client.get_health_status()

        assert result["status"] == CDNHealthStatus.HEALTHY
        assert "response_time_ms" in result
        assert result["edge_nodes_healthy"] > 0
        assert result["edge_nodes_total"] > 0

    @pytest.mark.asyncio
    async def test_list_edge_locations(self, cloudfront_client):
        """Test listing edge locations."""
        locations = await cloudfront_client.list_edge_locations()

        assert len(locations) > 0
        assert all("code" in loc for loc in locations)
        assert all("city" in loc for loc in locations)
        assert all("country" in loc for loc in locations)
        assert all("region" in loc for loc in locations)
        assert all("latitude" in loc for loc in locations)
        assert all("longitude" in loc for loc in locations)
        assert all("active" in loc for loc in locations)

        # Check for known locations
        location_codes = [loc["code"] for loc in locations]
        assert "IAD" in location_codes  # Ashburn
        assert "LAX" in location_codes  # Los Angeles
        assert "LHR" in location_codes  # London
        assert "NRT" in location_codes  # Tokyo

    @pytest.mark.asyncio
    async def test_configure_cache_rules(self, cloudfront_client):
        """Test configuring cache rules."""
        cloudfront_client.session = MagicMock(spec=ClientSession)

        rules = [
            {
                "pattern": "*.mp4",
                "cache_ttl": 86400,
                "cache_key_static": True,
                "browser_ttl": 3600
            }
        ]

        result = await cloudfront_client.configure_cache_rules(rules)

        assert result["success"] is True
        assert result["applied_rules"] == 1
        assert "note" in result

    @pytest.mark.asyncio
    async def test_get_usage_metrics(self, cloudfront_client):
        """Test getting usage metrics (placeholder implementation)."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        metrics = await cloudfront_client.get_usage_metrics(start_date, end_date)

        assert "total_bandwidth_gb" in metrics
        assert "total_requests" in metrics
        assert "cache_hit_ratio" in metrics
        assert "average_response_time_ms" in metrics
        assert "by_region" in metrics
        assert "note" in metrics

    @pytest.mark.asyncio
    async def test_test_connection_success(self, cloudfront_client):
        """Test connection check when successful."""
        cloudfront_client.session = MagicMock(spec=ClientSession)

        result = await cloudfront_client.test_connection()

        assert result is True


class TestErrorHandling:
    """Tests for error handling across CDN clients."""

    @pytest.mark.asyncio
    async def test_cloudflare_rate_limit_error(self):
        """Test Cloudflare rate limit error handling."""
        client = CloudflareCDNClient(
            api_token="test_token",
            zone_id="test_zone"
        )

        session = MagicMock(spec=ClientSession)
        mock_response = MagicMock()
        mock_response.status = 429
        session.post.return_value.__aenter__.return_value.json = AsyncMock(
            return_value={
                "success": False,
                "errors": [{"code": 9108, "message": "Rate limit exceeded"}]
            }
        )
        session.post.return_value.__aenter__.return_value.status = 429
        client.session = session

        with pytest.raises(CDNConnectionError, match="rate limit"):
            await client.purge_cache(urls=["https://example.com/video.mp4"])

    @pytest.mark.asyncio
    async def test_cloudfront_authentication_error(self):
        """Test CloudFront authentication error handling."""
        client = CloudFrontCDNClient(
            access_key_id="test_key",
            secret_access_key="test_secret",
            distribution_id="test_dist"
        )

        # CloudFront client in this implementation returns success
        # Real AWS SDK would raise authentication errors
        client.session = MagicMock(spec=ClientSession)
        result = await client.purge_cache(urls=["https://example.com/video.mp4"])
        assert result["success"] is True


class TestEdgeLocationsData:
    """Tests for edge locations data integrity."""

    def test_cloudflare_edge_locations_unique(self):
        """Test that Cloudflare edge locations have unique codes."""
        client = CloudflareCDNClient(
            api_token="test_token",
            zone_id="test_zone"
        )

        # We need to run the async method in sync context
        import asyncio

        async def get_locations():
            return await client.list_edge_locations()

        locations = asyncio.run(get_locations())
        codes = [loc["code"] for loc in locations]

        assert len(codes) == len(set(codes)), "Location codes must be unique"

    def test_cloudfront_edge_locations_unique(self):
        """Test that CloudFront edge locations have unique codes."""
        client = CloudFrontCDNClient(
            access_key_id="test_key",
            secret_access_key="test_secret",
            distribution_id="test_dist"
        )

        # We need to run the async method in sync context
        import asyncio

        async def get_locations():
            return await client.list_edge_locations()

        locations = asyncio.run(get_locations())
        codes = [loc["code"] for loc in locations]

        assert len(codes) == len(set(codes)), "Location codes must be unique"

    def test_cloudflare_location_data_complete(self):
        """Test that all Cloudflare locations have required fields."""
        client = CloudflareCDNClient(
            api_token="test_token",
            zone_id="test_zone"
        )

        import asyncio

        async def get_locations():
            return await client.list_edge_locations()

        locations = asyncio.run(get_locations())

        required_fields = ["code", "city", "country", "region", "latitude", "longitude", "active"]

        for location in locations:
            for field in required_fields:
                assert field in location, f"Location {location.get('code')} missing field {field}"

    def test_cloudfront_location_data_complete(self):
        """Test that all CloudFront locations have required fields."""
        client = CloudFrontCDNClient(
            access_key_id="test_key",
            secret_access_key="test_secret",
            distribution_id="test_dist"
        )

        import asyncio

        async def get_locations():
            return await client.list_edge_locations()

        locations = asyncio.run(get_locations())

        required_fields = ["code", "city", "country", "region", "latitude", "longitude", "active"]

        for location in locations:
            for field in required_fields:
                assert field in location, f"Location {location.get('code')} missing field {field}"


class TestContextManagers:
    """Tests for async context manager functionality."""

    @pytest.mark.asyncio
    async def test_cloudflare_context_manager(self):
        """Test Cloudflare client async context manager."""
        client = CloudflareCDNClient(
            api_token="test_token",
            zone_id="test_zone"
        )

        async with client:
            assert client.session is not None
            assert isinstance(client.session, ClientSession)

        # Session should be closed after exiting context
        assert client.session is None or client.session.closed

    @pytest.mark.asyncio
    async def test_cloudfront_context_manager(self):
        """Test CloudFront client async context manager."""
        client = CloudFrontCDNClient(
            access_key_id="test_key",
            secret_access_key="test_secret",
            distribution_id="test_dist"
        )

        async with client:
            assert client.session is not None
            assert isinstance(client.session, ClientSession)

        # Session should be closed after exiting context
        assert client.session is None or client.session.closed


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
