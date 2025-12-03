"""
Integration tests for Equalizer API endpoints.

Tests:
- GET /api/v1/playback/equalizer - Get current state
- PUT /api/v1/playback/equalizer/preset - Set preset
- PUT /api/v1/playback/equalizer/custom - Set custom bands
"""
import pytest
from httpx import AsyncClient
from fastapi import status

from src.main import app
from src.models import User


@pytest.mark.asyncio
class TestEqualizerAPI:
    """Test equalizer REST API endpoints."""
    
    async def test_get_equalizer_state(self, async_client: AsyncClient, test_user: User):
        """Test GET /api/v1/playback/equalizer - returns current state."""
        response = await async_client.get(
            "/api/v1/playback/equalizer",
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "preset" in data
        assert "bands" in data
        assert "available_presets" in data
        assert len(data["bands"]) == 10
        assert "standard" in data["available_presets"]
        assert "meditation" in data["available_presets"]
    
    async def test_set_equalizer_preset_meditation(self, async_client: AsyncClient, test_user: User):
        """Test PUT /api/v1/playback/equalizer/preset - set meditation preset."""
        response = await async_client.put(
            "/api/v1/playback/equalizer/preset",
            json={"preset_name": "meditation"},
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["preset"] == "meditation"
        assert data["display_name"] == "Медитация"
        assert "description" in data
        assert len(data["bands"]) == 10
    
    async def test_set_equalizer_preset_rock(self, async_client: AsyncClient, test_user: User):
        """Test PUT /api/v1/playback/equalizer/preset - set rock preset."""
        response = await async_client.put(
            "/api/v1/playback/equalizer/preset",
            json={"preset_name": "rock"},
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["preset"] == "rock"
        assert data["display_name"] == "Rock"
    
    async def test_set_equalizer_preset_invalid(self, async_client: AsyncClient, test_user: User):
        """Test PUT /api/v1/playback/equalizer/preset - invalid preset name."""
        response = await async_client.put(
            "/api/v1/playback/equalizer/preset",
            json={"preset_name": "invalid_preset"},
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Unknown preset" in response.json()["detail"]
    
    async def test_set_equalizer_custom_valid(self, async_client: AsyncClient, test_user: User):
        """Test PUT /api/v1/playback/equalizer/custom - valid custom bands."""
        custom_bands = [3, 2, 1, 0, -1, -2, -1, 0, 1, 2]
        
        response = await async_client.put(
            "/api/v1/playback/equalizer/custom",
            json={"bands": custom_bands},
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["success"] is True
        assert data["preset"] == "custom"
        assert data["bands"] == custom_bands
    
    async def test_set_equalizer_custom_invalid_length(self, async_client: AsyncClient, test_user: User):
        """Test PUT /api/v1/playback/equalizer/custom - invalid band count."""
        response = await async_client.put(
            "/api/v1/playback/equalizer/custom",
            json={"bands": [0, 0, 0]},  # Only 3 bands instead of 10
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_set_equalizer_custom_out_of_range(self, async_client: AsyncClient, test_user: User):
        """Test PUT /api/v1/playback/equalizer/custom - values out of range."""
        response = await async_client.put(
            "/api/v1/playback/equalizer/custom",
            json={"bands": [0, 0, 0, 0, 0, 30, 0, 0, 0, 0]},  # 30 dB exceeds max 12
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "out of range" in response.json()["detail"]
    
    async def test_equalizer_preset_persistence(self, async_client: AsyncClient, test_user: User):
        """Test equalizer state persistence after preset change."""
        # Set meditation preset
        await async_client.put(
            "/api/v1/playback/equalizer/preset",
            json={"preset_name": "meditation"},
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        # Verify state
        response = await async_client.get(
            "/api/v1/playback/equalizer",
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        data = response.json()
        assert data["preset"] == "meditation"
        
        # Set custom bands
        custom_bands = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        await async_client.put(
            "/api/v1/playback/equalizer/custom",
            json={"bands": custom_bands},
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        # Verify custom state
        response = await async_client.get(
            "/api/v1/playback/equalizer",
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        data = response.json()
        assert data["preset"] == "custom"
        assert data["bands"] == custom_bands


@pytest.mark.asyncio
class TestEqualizerAPIMultiChannel:
    """Test multi-channel equalizer support."""
    
    async def test_different_channels_different_states(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test that different channels maintain separate equalizer states."""
        # Set meditation for channel 1
        await async_client.put(
            "/api/v1/playback/equalizer/preset",
            json={"preset_name": "meditation", "channel_id": 1},
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        # Set rock for channel 2
        await async_client.put(
            "/api/v1/playback/equalizer/preset",
            json={"preset_name": "rock", "channel_id": 2},
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        
        # Verify channel 1
        response_ch1 = await async_client.get(
            "/api/v1/playback/equalizer?channel_id=1",
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        assert response_ch1.json()["preset"] == "meditation"
        
        # Verify channel 2
        response_ch2 = await async_client.get(
            "/api/v1/playback/equalizer?channel_id=2",
            headers={"Authorization": f"Bearer {test_user.id}"}
        )
        assert response_ch2.json()["preset"] == "rock"
