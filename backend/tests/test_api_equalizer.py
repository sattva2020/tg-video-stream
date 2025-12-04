"""
Integration tests for Equalizer API endpoints.

Tests cover:
- GET /api/v1/playback/equalizer - Get current state + catalog metadata
- GET /api/v1/playback/equalizer/presets - List presets grouped with metadata
- PUT /api/v1/playback/equalizer - Apply preset or custom bands
"""
import pytest
from httpx import AsyncClient
from fastapi import status

from src.main import app
from src.models import User


@pytest.mark.asyncio
class TestEqualizerAPI:
    """Test equalizer REST API endpoints."""
    
    async def test_get_equalizer_state(self, async_client: AsyncClient, test_user: User, user_auth_headers):
        """Test GET /api/v1/playback/equalizer - returns current state."""
        response = await async_client.get(
            "/api/v1/playback/equalizer",
            headers=user_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "preset" in data
        assert "bands" in data
        assert "available_presets" in data
        assert "preset_catalog" in data
        assert "band_frequencies" not in data  # kept in presets endpoint
        assert len(data["bands"]) == 10
        assert "standard" in data["available_presets"]
        assert "meditation" in data["available_presets"]
        assert data["preset_catalog"]["total"] >= 1
        assert data["preset_catalog"]["categories"]
        assert data["preset_catalog"]["categories"][0]["presets"]

    async def test_list_equalizer_presets(self, async_client: AsyncClient, test_user: User, user_auth_headers):
        """Test GET /api/v1/playback/equalizer/presets - metadata payload."""

        response = await async_client.get(
            "/api/v1/playback/equalizer/presets",
            headers=user_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        payload = response.json()

        assert payload["total"] >= 12
        assert payload["band_frequencies"]
        assert payload["categories"]
        first_category = payload["categories"][0]
        assert {"id", "label", "presets"}.issubset(first_category.keys())
        assert first_category["presets"]
    
    async def test_set_equalizer_preset_meditation(self, async_client: AsyncClient, test_user: User, user_auth_headers):
        """Test PUT /api/v1/playback/equalizer - set meditation preset."""
        response = await async_client.put(
            "/api/v1/playback/equalizer",
            json={"preset_name": "meditation"},
            headers=user_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["preset"] == "meditation"
        assert data["display_name"] == "Медитация"
        assert "description" in data
        assert len(data["bands"]) == 10
    
    async def test_set_equalizer_preset_rock(self, async_client: AsyncClient, test_user: User, user_auth_headers):
        """Test PUT /api/v1/playback/equalizer - set rock preset."""
        response = await async_client.put(
            "/api/v1/playback/equalizer",
            json={"preset_name": "rock"},
            headers=user_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["preset"] == "rock"
        assert data["display_name"] == "Рок"
    
    async def test_set_equalizer_preset_invalid(self, async_client: AsyncClient, test_user: User, user_auth_headers):
        """Test PUT /api/v1/playback/equalizer - invalid preset name."""
        response = await async_client.put(
            "/api/v1/playback/equalizer",
            json={"preset_name": "invalid_preset"},
            headers=user_auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unknown preset" in response.json()["detail"]
    
    async def test_set_equalizer_custom_valid(self, async_client: AsyncClient, test_user: User, user_auth_headers):
        """Test PUT /api/v1/playback/equalizer - valid custom bands payload."""
        custom_bands = [3, 2, 1, 0, -1, -2, -1, 0, 1, 2]
        
        response = await async_client.put(
            "/api/v1/playback/equalizer",
            json={"bands": custom_bands},
            headers=user_auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["preset"] == "custom"
        assert data["bands"] == custom_bands
    
    async def test_set_equalizer_custom_invalid_length(self, async_client: AsyncClient, test_user: User, user_auth_headers):
        """Test PUT /api/v1/playback/equalizer - invalid band count."""
        response = await async_client.put(
            "/api/v1/playback/equalizer",
            json={"bands": [0, 0, 0]},  # Only 3 bands instead of 10
            headers=user_auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_set_equalizer_custom_out_of_range(self, async_client: AsyncClient, test_user: User, user_auth_headers):
        """Test PUT /api/v1/playback/equalizer - values out of range."""
        response = await async_client.put(
            "/api/v1/playback/equalizer",
            json={"bands": [0, 0, 0, 0, 0, 30, 0, 0, 0, 0]},  # 30 dB exceeds max 12
            headers=user_auth_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "out of range" in response.json()["detail"]
    
    async def test_equalizer_preset_persistence(self, async_client: AsyncClient, test_user: User, user_auth_headers):
        """Test equalizer state persistence after preset change."""
        # Set meditation preset
        await async_client.put(
            "/api/v1/playback/equalizer",
            json={"preset_name": "meditation"},
            headers=user_auth_headers
        )
        
        # Verify state
        response = await async_client.get(
            "/api/v1/playback/equalizer",
            headers=user_auth_headers
        )
        
        data = response.json()
        assert data["preset"] == "meditation"
        
        # Set custom bands
        custom_bands = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        await async_client.put(
            "/api/v1/playback/equalizer",
            json={"bands": custom_bands},
            headers=user_auth_headers
        )
        
        # Verify custom state
        response = await async_client.get(
            "/api/v1/playback/equalizer",
            headers=user_auth_headers
        )
        
        data = response.json()
        assert data["preset"] == "custom"
        assert data["bands"] == custom_bands


@pytest.mark.asyncio
class TestEqualizerAPIMultiChannel:
    """Test multi-channel equalizer support."""
    
    async def test_different_channels_different_states(
        self, async_client: AsyncClient, test_user: User, user_auth_headers
    ):
        """Test that different channels maintain separate equalizer states."""
        # Set meditation for channel 1
        await async_client.put(
            "/api/v1/playback/equalizer",
            json={"preset_name": "meditation", "channel_id": 1},
            headers=user_auth_headers
        )
        
        # Set rock for channel 2
        await async_client.put(
            "/api/v1/playback/equalizer",
            json={"preset_name": "rock", "channel_id": 2},
            headers=user_auth_headers
        )
        
        # Verify channel 1
        response_ch1 = await async_client.get(
            "/api/v1/playback/equalizer?channel_id=1",
            headers=user_auth_headers
        )
        assert response_ch1.json()["preset"] == "meditation"
        
        # Verify channel 2
        response_ch2 = await async_client.get(
            "/api/v1/playback/equalizer?channel_id=2",
            headers=user_auth_headers
        )
        assert response_ch2.json()["preset"] == "rock"
