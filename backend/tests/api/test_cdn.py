"""
Feature 024: Global CDN Integration - API Tests
Tests for CDN management endpoints (configuration, status, cache control)
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.api.routes.cdn import router
from src.models.cdn_config import CDNConfig
from src.models.user import User


@pytest.fixture
def app():
    """Create test FastAPI app"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_admin_user():
    """Mock admin user"""
    user = MagicMock(spec=User)
    user.id = "test-admin-id"
    user.username = "admin"
    user.is_admin = True
    return user


@pytest.fixture
def mock_regular_user():
    """Mock regular user"""
    user = MagicMock(spec=User)
    user.id = "test-user-id"
    user.username = "user"
    user.is_admin = False
    return user


@pytest.fixture
def mock_cdn_provider_dict():
    """Mock CDN provider dictionary"""
    return {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "provider": "cloudflare",
        "name": "Primary CDN",
        "enabled": True,
        "priority": 1,
        "health_status": "healthy",
        "last_health_check": datetime.now(timezone.utc).isoformat(),
        "last_error": None,
        "zone_id": "test-zone-id",
        "distribution_id": None,
        "service_id": None,
        "account_id": "test-account-id",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "api_token": "test_token...1234"
    }


@pytest.fixture
def mock_health_status_response():
    """Mock health status response"""
    return {
        "overall_status": "healthy",
        "providers": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Primary CDN",
                "provider": "cloudflare",
                "status": "healthy",
                "response_time_ms": 45,
                "last_check": datetime.now(timezone.utc).isoformat(),
                "edge_nodes_healthy": 200,
                "edge_nodes_total": 200,
                "error": None
            }
        ],
        "last_check": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def mock_edge_locations():
    """Mock edge locations list"""
    return [
        {
            "provider": "cloudflare",
            "provider_id": "550e8400-e29b-41d4-a716-446655440000",
            "code": "AMS",
            "city": "Amsterdam",
            "country": "Netherlands",
            "region": "Europe",
            "latitude": 52.37,
            "longitude": 4.89,
            "active": True
        },
        {
            "provider": "cloudflare",
            "provider_id": "550e8400-e29b-41d4-a716-446655440000",
            "code": "SFO",
            "city": "San Francisco",
            "country": "United States",
            "region": "North America",
            "latitude": 37.77,
            "longitude": -122.45,
            "active": True
        }
    ]


@pytest.fixture
def mock_purge_response():
    """Mock cache purge response"""
    return {
        "success": True,
        "purged_urls": ["https://example.com/video1.mp4"],
        "providers": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Primary CDN",
                "provider": "cloudflare",
                "success": True,
                "error": None
            }
        ],
        "errors": []
    }


class TestListCDNProviders:
    """Tests for GET /api/v1/cdn/providers"""

    @pytest.mark.asyncio
    async def test_list_providers_success(self, client, mock_cdn_provider_dict):
        """Test successful provider list retrieval"""
        with patch(
            'src.services.cdn_service.CDNService.list_providers',
            new_callable=AsyncMock,
            return_value=[mock_cdn_provider_dict]
        ):
            response = client.get('/api/v1/cdn/providers?enabled_only=true')
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 1
            assert len(data['providers']) == 1
            assert data['providers'][0]['provider'] == 'cloudflare'
            assert data['providers'][0]['enabled'] is True

    @pytest.mark.asyncio
    async def test_list_providers_all(self, client, mock_cdn_provider_dict):
        """Test listing all providers including disabled"""
        with patch(
            'src.services.cdn_service.CDNService.list_providers',
            new_callable=AsyncMock,
            return_value=[mock_cdn_provider_dict]
        ) as mock_list:
            response = client.get('/api/v1/cdn/providers?enabled_only=false')
            assert response.status_code == 200
            mock_list.assert_called_once_with(enabled_only=False)

    @pytest.mark.asyncio
    async def test_list_providers_empty(self, client):
        """Test listing providers when none exist"""
        with patch(
            'src.services.cdn_service.CDNService.list_providers',
            new_callable=AsyncMock,
            return_value=[]
        ):
            response = client.get('/api/v1/cdn/providers?enabled_only=true')
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 0
            assert len(data['providers']) == 0

    @pytest.mark.asyncio
    async def test_list_providers_multiple(self, client):
        """Test listing multiple CDN providers"""
        provider1 = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "provider": "cloudflare",
            "name": "Primary CDN",
            "enabled": True,
            "priority": 1,
            "health_status": "healthy",
            "last_health_check": None,
            "last_error": None,
            "zone_id": "zone1",
            "distribution_id": None,
            "service_id": None,
            "account_id": "account1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "api_token": "token1...1234"
        }
        provider2 = {
            "id": "650e8400-e29b-41d4-a716-446655440001",
            "provider": "cloudfront",
            "name": "Backup CDN",
            "enabled": True,
            "priority": 2,
            "health_status": "healthy",
            "last_health_check": None,
            "last_error": None,
            "zone_id": None,
            "distribution_id": "dist1",
            "service_id": None,
            "account_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "api_token": "token2...5678"
        }

        with patch(
            'src.services.cdn_service.CDNService.list_providers',
            new_callable=AsyncMock,
            return_value=[provider1, provider2]
        ):
            response = client.get('/api/v1/cdn/providers?enabled_only=true')
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 2
            assert data['providers'][0]['provider'] == 'cloudflare'
            assert data['providers'][1]['provider'] == 'cloudfront'


class TestGetCDNProvider:
    """Tests for GET /api/v1/cdn/providers/{provider_id}"""

    @pytest.mark.asyncio
    async def test_get_provider_success(self, client, mock_cdn_provider_dict):
        """Test successful provider retrieval"""
        provider_id = "550e8400-e29b-41d4-a716-446655440000"
        with patch(
            'src.services.cdn_service.CDNService.get_provider',
            new_callable=AsyncMock,
            return_value=mock_cdn_provider_dict
        ):
            response = client.get(f'/api/v1/cdn/providers/{provider_id}')
            assert response.status_code == 200
            data = response.json()
            assert data['id'] == provider_id
            assert data['provider'] == 'cloudflare'
            assert data['name'] == 'Primary CDN'

    @pytest.mark.asyncio
    async def test_get_provider_not_found(self, client):
        """Test getting non-existent provider"""
        provider_id = "non-existent-id"
        with patch(
            'src.services.cdn_service.CDNService.get_provider',
            new_callable=AsyncMock,
            return_value=None
        ):
            response = client.get(f'/api/v1/cdn/providers/{provider_id}')
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_provider_invalid_uuid(self, client):
        """Test getting provider with invalid UUID"""
        response = client.get('/api/v1/cdn/providers/invalid-uuid')
        # Should either 404 or validation error
        assert response.status_code in [404, 422]


class TestGetCDNStatus:
    """Tests for GET /api/v1/cdn/status"""

    @pytest.mark.asyncio
    async def test_get_status_success(self, client, mock_health_status_response):
        """Test successful health status retrieval"""
        with patch(
            'src.services.cdn_service.CDNService.get_health_status',
            new_callable=AsyncMock,
            return_value=mock_health_status_response
        ):
            response = client.get('/api/v1/cdn/status?use_cache=true')
            assert response.status_code == 200
            data = response.json()
            assert data['overall_status'] == 'healthy'
            assert len(data['providers']) == 1
            assert data['providers'][0]['status'] == 'healthy'

    @pytest.mark.asyncio
    async def test_get_status_no_cache(self, client, mock_health_status_response):
        """Test health status with cache disabled"""
        with patch(
            'src.services.cdn_service.CDNService.get_health_status',
            new_callable=AsyncMock,
            return_value=mock_health_status_response
        ) as mock_status:
            response = client.get('/api/v1/cdn/status?use_cache=false')
            assert response.status_code == 200
            mock_status.assert_called_once_with(provider_id=None, use_cache=False)

    @pytest.mark.asyncio
    async def test_get_status_degraded(self, client):
        """Test degraded health status"""
        degraded_response = {
            "overall_status": "degraded",
            "providers": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Primary CDN",
                    "provider": "cloudflare",
                    "status": "degraded",
                    "response_time_ms": 250,
                    "last_check": datetime.now(timezone.utc).isoformat(),
                    "edge_nodes_healthy": 180,
                    "edge_nodes_total": 200,
                    "error": "High latency"
                }
            ],
            "last_check": datetime.now(timezone.utc).isoformat()
        }
        with patch(
            'src.services.cdn_service.CDNService.get_health_status',
            new_callable=AsyncMock,
            return_value=degraded_response
        ):
            response = client.get('/api/v1/cdn/status')
            assert response.status_code == 200
            data = response.json()
            assert data['overall_status'] == 'degraded'

    @pytest.mark.asyncio
    async def test_get_status_specific_provider(self, client, mock_health_status_response):
        """Test health status for specific provider"""
        provider_id = "550e8400-e29b-41d4-a716-446655440000"
        with patch(
            'src.services.cdn_service.CDNService.get_health_status',
            new_callable=AsyncMock,
            return_value=mock_health_status_response
        ) as mock_status:
            response = client.get(f'/api/v1/cdn/status?provider_id={provider_id}')
            assert response.status_code == 200
            mock_status.assert_called_once_with(provider_id=provider_id, use_cache=True)

    @pytest.mark.asyncio
    async def test_get_status_unhealthy(self, client):
        """Test unhealthy status"""
        unhealthy_response = {
            "overall_status": "unhealthy",
            "providers": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Primary CDN",
                    "provider": "cloudflare",
                    "status": "unhealthy",
                    "response_time_ms": 0,
                    "last_check": None,
                    "error": "Connection failed"
                }
            ],
            "last_check": datetime.now(timezone.utc).isoformat()
        }
        with patch(
            'src.services.cdn_service.CDNService.get_health_status',
            new_callable=AsyncMock,
            return_value=unhealthy_response
        ):
            response = client.get('/api/v1/cdn/status')
            assert response.status_code == 200
            data = response.json()
            assert data['overall_status'] == 'unhealthy'


class TestPurgeCDNCache:
    """Tests for POST /api/v1/cdn/purge"""

    @pytest.mark.asyncio
    async def test_purge_cache_success(self, client, mock_purge_response):
        """Test successful cache purge"""
        purge_data = {
            "urls": ["https://example.com/video1.mp4"],
            "provider_id": None,
            "purge_all": False
        }
        with patch(
            'src.services.cdn_service.CDNService.purge_cache',
            new_callable=AsyncMock,
            return_value=mock_purge_response
        ):
            response = client.post('/api/v1/cdn/purge', json=purge_data)
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert len(data['purged_urls']) == 1
            assert data['providers'][0]['success'] is True

    @pytest.mark.asyncio
    async def test_purge_cache_multiple_urls(self, client, mock_purge_response):
        """Test cache purge with multiple URLs"""
        purge_data = {
            "urls": [
                "https://example.com/video1.mp4",
                "https://example.com/video2.mp4",
                "https://example.com/audio1.mp3"
            ],
            "provider_id": None,
            "purge_all": False
        }
        response_data = {
            "success": True,
            "purged_urls": purge_data["urls"],
            "providers": [],
            "errors": []
        }
        with patch(
            'src.services.cdn_service.CDNService.purge_cache',
            new_callable=AsyncMock,
            return_value=response_data
        ):
            response = client.post('/api/v1/cdn/purge', json=purge_data)
            assert response.status_code == 200
            data = response.json()
            assert len(data['purged_urls']) == 3

    @pytest.mark.asyncio
    async def test_purge_cache_all(self, client):
        """Test purging entire cache"""
        purge_data = {
            "urls": [],
            "provider_id": None,
            "purge_all": True
        }
        response_data = {
            "success": True,
            "purged_urls": [],
            "providers": [{"id": "test", "name": "CDN", "provider": "cloudflare", "success": True, "error": None}],
            "errors": []
        }
        with patch(
            'src.services.cdn_service.CDNService.purge_cache',
            new_callable=AsyncMock,
            return_value=response_data
        ) as mock_purge:
            response = client.post('/api/v1/cdn/purge', json=purge_data)
            assert response.status_code == 200
            mock_purge.assert_called_once()
            call_kwargs = mock_purge.call_args[1]
            assert call_kwargs['purge_all'] is True

    @pytest.mark.asyncio
    async def test_purge_cache_specific_provider(self, client, mock_purge_response):
        """Test cache purge for specific provider"""
        provider_id = "550e8400-e29b-41d4-a716-446655440000"
        purge_data = {
            "urls": ["https://example.com/video1.mp4"],
            "provider_id": provider_id,
            "purge_all": False
        }
        with patch(
            'src.services.cdn_service.CDNService.purge_cache',
            new_callable=AsyncMock,
            return_value=mock_purge_response
        ) as mock_purge:
            response = client.post('/api/v1/cdn/purge', json=purge_data)
            assert response.status_code == 200
            mock_purge.assert_called_once()
            call_kwargs = mock_purge.call_args[1]
            assert call_kwargs['provider_id'] == provider_id

    @pytest.mark.asyncio
    async def test_purge_cache_partial_failure(self, client):
        """Test cache purge with partial failures"""
        purge_data = {
            "urls": ["https://example.com/video1.mp4"],
            "provider_id": None,
            "purge_all": False
        }
        response_data = {
            "success": False,
            "purged_urls": [],
            "providers": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Primary CDN",
                    "provider": "cloudflare",
                    "success": False,
                    "error": "Authentication failed"
                }
            ],
            "errors": ["Primary CDN: Authentication failed"]
        }
        with patch(
            'src.services.cdn_service.CDNService.purge_cache',
            new_callable=AsyncMock,
            return_value=response_data
        ):
            response = client.post('/api/v1/cdn/purge', json=purge_data)
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is False
            assert len(data['errors']) > 0

    @pytest.mark.asyncio
    async def test_purge_cache_empty_urls(self, client):
        """Test cache purge validation (empty URLs without purge_all)"""
        purge_data = {
            "urls": [],
            "provider_id": None,
            "purge_all": False
        }
        response = client.post('/api/v1/cdn/purge', json=purge_data)
        # Should fail validation
        assert response.status_code == 422


class TestListEdgeLocations:
    """Tests for GET /api/v1/cdn/locations"""

    @pytest.mark.asyncio
    async def test_list_locations_success(self, client, mock_edge_locations):
        """Test successful edge locations list"""
        with patch(
            'src.services.cdn_service.CDNService.list_edge_locations',
            new_callable=AsyncMock,
            return_value=mock_edge_locations
        ):
            response = client.get('/api/v1/cdn/locations?use_cache=true')
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 2
            assert len(data['locations']) == 2
            assert data['locations'][0]['code'] == 'AMS'
            assert data['locations'][1]['code'] == 'SFO'

    @pytest.mark.asyncio
    async def test_list_locations_no_cache(self, client, mock_edge_locations):
        """Test edge locations with cache disabled"""
        with patch(
            'src.services.cdn_service.CDNService.list_edge_locations',
            new_callable=AsyncMock,
            return_value=mock_edge_locations
        ) as mock_list:
            response = client.get('/api/v1/cdn/locations?use_cache=false')
            assert response.status_code == 200
            mock_list.assert_called_once_with(provider_id=None, use_cache=False)

    @pytest.mark.asyncio
    async def test_list_locations_specific_provider(self, client, mock_edge_locations):
        """Test edge locations for specific provider"""
        provider_id = "550e8400-e29b-41d4-a716-446655440000"
        with patch(
            'src.services.cdn_service.CDNService.list_edge_locations',
            new_callable=AsyncMock,
            return_value=mock_edge_locations
        ) as mock_list:
            response = client.get(f'/api/v1/cdn/locations?provider_id={provider_id}')
            assert response.status_code == 200
            mock_list.assert_called_once_with(provider_id=provider_id, use_cache=True)

    @pytest.mark.asyncio
    async def test_list_locations_empty(self, client):
        """Test edge locations when none available"""
        with patch(
            'src.services.cdn_service.CDNService.list_edge_locations',
            new_callable=AsyncMock,
            return_value=[]
        ):
            response = client.get('/api/v1/cdn/locations')
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 0
            assert len(data['locations']) == 0

    @pytest.mark.asyncio
    async def test_list_locations_multiple_providers(self, client):
        """Test edge locations from multiple providers"""
        locations = [
            {
                "provider": "cloudflare",
                "provider_id": "550e8400-e29b-41d4-a716-446655440000",
                "code": "AMS",
                "city": "Amsterdam",
                "country": "Netherlands",
                "region": "Europe",
                "latitude": 52.37,
                "longitude": 4.89,
                "active": True
            },
            {
                "provider": "cloudfront",
                "provider_id": "650e8400-e29b-41d4-a716-446655440001",
                "code": "FRA",
                "city": "Frankfurt",
                "country": "Germany",
                "region": "Europe",
                "latitude": 50.11,
                "longitude": 8.68,
                "active": True
            }
        ]
        with patch(
            'src.services.cdn_service.CDNService.list_edge_locations',
            new_callable=AsyncMock,
            return_value=locations
        ):
            response = client.get('/api/v1/cdn/locations')
            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 2
            assert data['locations'][0]['provider'] == 'cloudflare'
            assert data['locations'][1]['provider'] == 'cloudfront'


class TestConfigureCacheRules:
    """Tests for PUT /api/v1/cdn/cache-rules"""

    @pytest.mark.asyncio
    async def test_configure_rules_success(self, client):
        """Test successful cache rules configuration"""
        rules_data = {
            "rules": [
                {
                    "pattern": "*.mp4",
                    "ttl": 86400,
                    "priority": 1
                },
                {
                    "pattern": "*.jpg",
                    "ttl": 3600,
                    "priority": 2
                }
            ],
            "provider_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        response_data = {
            "success": True,
            "applied_rules": 2,
            "error": None
        }
        with patch(
            'src.services.cdn_service.CDNService.configure_cache_rules',
            new_callable=AsyncMock,
            return_value=response_data
        ):
            response = client.put('/api/v1/cdn/cache-rules', json=rules_data)
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['applied_rules'] == 2

    @pytest.mark.asyncio
    async def test_configure_rules_empty(self, client):
        """Test cache rules validation (empty rules)"""
        rules_data = {
            "rules": [],
            "provider_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        response = client.put('/api/v1/cdn/cache-rules', json=rules_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_configure_rules_invalid_ttl(self, client):
        """Test cache rules with invalid TTL"""
        rules_data = {
            "rules": [
                {
                    "pattern": "*.mp4",
                    "ttl": -1,  # Invalid TTL
                    "priority": 1
                }
            ],
            "provider_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        response = client.put('/api/v1/cdn/cache-rules', json=rules_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_configure_rules_invalid_priority(self, client):
        """Test cache rules with invalid priority"""
        rules_data = {
            "rules": [
                {
                    "pattern": "*.mp4",
                    "ttl": 86400,
                    "priority": 0  # Invalid priority (must be >= 1)
                }
            ],
            "provider_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        response = client.put('/api/v1/cdn/cache-rules', json=rules_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_configure_rules_provider_not_found(self, client):
        """Test configuring rules for non-existent provider"""
        rules_data = {
            "rules": [
                {
                    "pattern": "*.mp4",
                    "ttl": 86400,
                    "priority": 1
                }
            ],
            "provider_id": "non-existent-id"
        }
        response_data = {
            "success": False,
            "applied_rules": 0,
            "error": "CDN configuration not found"
        }
        with patch(
            'src.services.cdn_service.CDNService.configure_cache_rules',
            new_callable=AsyncMock,
            return_value=response_data
        ):
            response = client.put('/api/v1/cdn/cache-rules', json=rules_data)
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is False
            assert data['error'] is not None

    @pytest.mark.asyncio
    async def test_configure_rules_partial_failure(self, client):
        """Test cache rules with partial application"""
        rules_data = {
            "rules": [
                {
                    "pattern": "*.mp4",
                    "ttl": 86400,
                    "priority": 1
                },
                {
                    "pattern": "*.jpg",
                    "ttl": 3600,
                    "priority": 2
                }
            ],
            "provider_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        response_data = {
            "success": False,
            "applied_rules": 1,
            "error": "Second rule could not be applied"
        }
        with patch(
            'src.services.cdn_service.CDNService.configure_cache_rules',
            new_callable=AsyncMock,
            return_value=response_data
        ):
            response = client.put('/api/v1/cdn/cache-rules', json=rules_data)
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is False
            assert data['applied_rules'] == 1


class TestCDNIntegration:
    """Integration tests for CDN features"""

    @pytest.mark.asyncio
    async def test_complete_cdn_workflow(self, client, mock_cdn_provider_dict, mock_health_status_response):
        """Test complete CDN workflow: list -> status -> locations"""
        # 1. List providers
        with patch(
            'src.services.cdn_service.CDNService.list_providers',
            new_callable=AsyncMock,
            return_value=[mock_cdn_provider_dict]
        ):
            response1 = client.get('/api/v1/cdn/providers')
            assert response1.status_code == 200
            providers = response1.json()['providers']
            assert len(providers) > 0

        # 2. Get health status
        with patch(
            'src.services.cdn_service.CDNService.get_health_status',
            new_callable=AsyncMock,
            return_value=mock_health_status_response
        ):
            response2 = client.get('/api/v1/cdn/status')
            assert response2.status_code == 200
            assert response2.json()['overall_status'] == 'healthy'

        # 3. List edge locations
        with patch(
            'src.services.cdn_service.CDNService.list_edge_locations',
            new_callable=AsyncMock,
            return_value=[
                {
                    "provider": "cloudflare",
                    "provider_id": "550e8400-e29b-41d4-a716-446655440000",
                    "code": "AMS",
                    "city": "Amsterdam",
                    "country": "Netherlands",
                    "region": "Europe",
                    "latitude": 52.37,
                    "longitude": 4.89,
                    "active": True
                }
            ]
        ):
            response3 = client.get('/api/v1/cdn/locations')
            assert response3.status_code == 200
            locations = response3.json()['locations']
            assert len(locations) > 0

    @pytest.mark.asyncio
    async def test_cache_management_workflow(self, client, mock_purge_response):
        """Test cache management workflow: configure rules -> purge"""
        provider_id = "550e8400-e29b-41d4-a716-446655440000"

        # 1. Configure cache rules
        rules_data = {
            "rules": [
                {
                    "pattern": "*.mp4",
                    "ttl": 86400,
                    "priority": 1
                }
            ],
            "provider_id": provider_id
        }
        with patch(
            'src.services.cdn_service.CDNService.configure_cache_rules',
            new_callable=AsyncMock,
            return_value={"success": True, "applied_rules": 1, "error": None}
        ):
            response1 = client.put('/api/v1/cdn/cache-rules', json=rules_data)
            assert response1.status_code == 200
            assert response1.json()['success'] is True

        # 2. Purge cache
        purge_data = {
            "urls": ["https://example.com/video1.mp4"],
            "provider_id": provider_id,
            "purge_all": False
        }
        with patch(
            'src.services.cdn_service.CDNService.purge_cache',
            new_callable=AsyncMock,
            return_value=mock_purge_response
        ):
            response2 = client.post('/api/v1/cdn/purge', json=purge_data)
            assert response2.status_code == 200
            assert response2.json()['success'] is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
