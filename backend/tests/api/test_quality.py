"""
Feature 022 Phase 2: Stream Quality Monitoring - API Tests
Tests for stream quality analysis endpoints
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.admin import router
from src.schemas.stream_quality import (
    StreamQualityResponse,
    AudioQualityMetrics,
    VideoQualityMetrics,
)
from src.services.stream_quality_service import StreamQualityService


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
def mock_quality_response():
    """Mock StreamQualityResponse"""
    return StreamQualityResponse(
        url="http://test.stream/video",
        audio=AudioQualityMetrics(
            codec="aac",
            bitrate_kbps=128,
            sample_rate_hz=48000,
            channels=2,
            duration_sec=3600,
            quality="high"
        ),
        video=VideoQualityMetrics(
            codec="h264",
            bitrate_kbps=2500,
            resolution="1920x1080",
            fps=30,
            duration_sec=3600,
            quality="high"
        ),
        is_audio_only=False,
        is_video_only=False,
        has_both=True,
        overall_quality="high"
    )


@pytest.fixture
def mock_audio_only_response():
    """Mock audio-only StreamQualityResponse"""
    return StreamQualityResponse(
        url="http://test.stream/audio",
        audio=AudioQualityMetrics(
            codec="aac",
            bitrate_kbps=192,
            sample_rate_hz=44100,
            channels=2,
            duration_sec=3600,
            quality="high"
        ),
        video=None,
        is_audio_only=True,
        is_video_only=False,
        has_both=False,
        overall_quality="high"
    )


class TestGetStreamQuality:
    """Tests for GET /api/admin/stream/quality/{stream_url:path}"""

    @pytest.mark.asyncio
    async def test_get_quality_success(self, client, mock_quality_response):
        """Test successful quality fetch"""
        with patch(
            'src.services.stream_quality_service.StreamQualityService.analyze_stream_quality',
            new_callable=AsyncMock,
            return_value=mock_quality_response.dict()
        ):
            response = client.get(
                '/api/admin/stream/quality/http://test.stream/video?timeout=10&use_cache=true'
            )
            assert response.status_code == 200
            data = response.json()
            assert data['url'] == "http://test.stream/video"
            assert data['overall_quality'] == "high"
            assert data['audio'] is not None
            assert data['video'] is not None

    @pytest.mark.asyncio
    async def test_get_quality_audio_only(self, client, mock_audio_only_response):
        """Test quality fetch for audio-only stream"""
        with patch(
            'src.services.stream_quality_service.StreamQualityService.analyze_stream_quality',
            new_callable=AsyncMock,
            return_value=mock_audio_only_response.dict()
        ):
            response = client.get(
                '/api/admin/stream/quality/http://test.stream/audio?timeout=10&use_cache=true'
            )
            assert response.status_code == 200
            data = response.json()
            assert data['is_audio_only'] is True
            assert data['is_video_only'] is False
            assert data['video'] is None
            assert data['audio'] is not None

    @pytest.mark.asyncio
    async def test_get_quality_timeout_validation(self, client):
        """Test timeout parameter validation"""
        response = client.get(
            '/api/admin/stream/quality/http://test.stream?timeout=60'
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_quality_invalid_timeout_zero(self, client):
        """Test invalid timeout (zero)"""
        response = client.get(
            '/api/admin/stream/quality/http://test.stream?timeout=0'
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_quality_no_cache(self, client, mock_quality_response):
        """Test quality fetch with caching disabled"""
        with patch(
            'src.services.stream_quality_service.StreamQualityService.analyze_stream_quality',
            new_callable=AsyncMock,
            return_value=mock_quality_response.dict()
        ) as mock_analyze:
            response = client.get(
                '/api/admin/stream/quality/http://test.stream?timeout=10&use_cache=false'
            )
            assert response.status_code == 200
            mock_analyze.assert_called_once()
            call_kwargs = mock_analyze.call_args[1]
            assert call_kwargs['use_cache'] is False

    @pytest.mark.asyncio
    async def test_get_quality_null_response(self, client):
        """Test quality fetch when analysis fails"""
        with patch(
            'src.services.stream_quality_service.StreamQualityService.analyze_stream_quality',
            new_callable=AsyncMock,
            return_value=None
        ):
            response = client.get(
                '/api/admin/stream/quality/http://test.stream?timeout=10&use_cache=true'
            )
            assert response.status_code == 200
            assert response.json() is None


class TestBatchAnalyzeStreams:
    """Tests for GET /api/admin/streams/quality/batch"""

    @pytest.mark.asyncio
    async def test_batch_analyze_success(self, client, mock_quality_response, mock_audio_only_response):
        """Test successful batch analysis"""
        batch_results = {
            "http://test.stream/video": mock_quality_response.dict(),
            "http://test.stream/audio": mock_audio_only_response.dict(),
        }
        with patch(
            'src.services.stream_quality_service.StreamQualityService.analyze_batch_streams',
            new_callable=AsyncMock,
            return_value=batch_results
        ):
            response = client.get(
                '/api/admin/streams/quality/batch?urls=http://test.stream/video&urls=http://test.stream/audio&timeout=10'
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert "http://test.stream/video" in data
            assert "http://test.stream/audio" in data
            assert data["http://test.stream/video"]['overall_quality'] == "high"
            assert data["http://test.stream/audio"]['is_audio_only'] is True

    @pytest.mark.asyncio
    async def test_batch_analyze_partial_failure(self, client, mock_quality_response):
        """Test batch analysis with some failures"""
        batch_results = {
            "http://test.stream/video": mock_quality_response.dict(),
            "http://invalid.stream": None,  # Failed analysis
        }
        with patch(
            'src.services.stream_quality_service.StreamQualityService.analyze_batch_streams',
            new_callable=AsyncMock,
            return_value=batch_results
        ):
            response = client.get(
                '/api/admin/streams/quality/batch?urls=http://test.stream/video&urls=http://invalid.stream&timeout=10'
            )
            assert response.status_code == 200
            data = response.json()
            assert data["http://test.stream/video"] is not None
            assert data["http://invalid.stream"] is None

    @pytest.mark.asyncio
    async def test_batch_analyze_empty_urls(self, client):
        """Test batch analysis with no URLs"""
        with patch(
            'src.services.stream_quality_service.StreamQualityService.analyze_batch_streams',
            new_callable=AsyncMock,
            return_value={}
        ):
            response = client.get(
                '/api/admin/streams/quality/batch?timeout=10'
            )
            assert response.status_code == 200
            assert response.json() == {}

    @pytest.mark.asyncio
    async def test_batch_analyze_timeout_validation(self, client):
        """Test timeout parameter validation in batch"""
        response = client.get(
            '/api/admin/streams/quality/batch?urls=http://test.stream&timeout=50'
        )
        assert response.status_code == 422  # Validation error


class TestClearQualityCache:
    """Tests for POST /api/admin/quality/cache/clear"""

    @pytest.mark.asyncio
    async def test_clear_all_cache(self, client):
        """Test clearing all quality cache"""
        with patch(
            'src.services.stream_quality_service.StreamQualityService.clear_cache',
            new_callable=AsyncMock
        ) as mock_clear:
            response = client.post('/api/admin/quality/cache/clear')
            assert response.status_code == 200
            data = response.json()
            assert 'status' in data or 'message' in data
            mock_clear.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_clear_specific_url_cache(self, client):
        """Test clearing cache for specific URL"""
        test_url = "http://test.stream/video"
        with patch(
            'src.services.stream_quality_service.StreamQualityService.clear_cache',
            new_callable=AsyncMock
        ) as mock_clear:
            response = client.post(
                f'/api/admin/quality/cache/clear?stream_url={test_url}'
            )
            assert response.status_code == 200
            mock_clear.assert_called_once_with(test_url)

    @pytest.mark.asyncio
    async def test_clear_cache_response_format(self, client):
        """Test cache clear response format"""
        with patch(
            'src.services.stream_quality_service.StreamQualityService.clear_cache',
            new_callable=AsyncMock
        ):
            response = client.post('/api/admin/quality/cache/clear')
            assert response.status_code == 200
            data = response.json()
            # Response should have status or message field
            assert isinstance(data, dict)


class TestStreamQualityIntegration:
    """Integration tests for stream quality features"""

    @pytest.mark.asyncio
    async def test_quality_analysis_flow(self, client, mock_quality_response):
        """Test complete quality analysis flow"""
        test_url = "http://test.stream/video"
        
        # 1. Analyze quality
        with patch(
            'src.services.stream_quality_service.StreamQualityService.analyze_stream_quality',
            new_callable=AsyncMock,
            return_value=mock_quality_response.dict()
        ):
            response1 = client.get(
                f'/api/admin/stream/quality/{test_url}?timeout=10&use_cache=true'
            )
            assert response1.status_code == 200
            assert response1.json()['overall_quality'] == 'high'

        # 2. Clear cache
        with patch(
            'src.services.stream_quality_service.StreamQualityService.clear_cache',
            new_callable=AsyncMock
        ):
            response2 = client.post(
                f'/api/admin/quality/cache/clear?stream_url={test_url}'
            )
            assert response2.status_code == 200

    @pytest.mark.asyncio
    async def test_multiple_quality_levels(self, client):
        """Test different quality levels in responses"""
        quality_levels = ['low', 'medium', 'high', 'lossless', 'ultra']
        
        for quality_level in quality_levels:
            mock_response = StreamQualityResponse(
                url="http://test.stream/video",
                audio=AudioQualityMetrics(quality=quality_level),
                video=VideoQualityMetrics(quality=quality_level),
                is_audio_only=False,
                is_video_only=False,
                has_both=True,
                overall_quality=quality_level
            )
            
            with patch(
                'src.services.stream_quality_service.StreamQualityService.analyze_stream_quality',
                new_callable=AsyncMock,
                return_value=mock_response.dict()
            ):
                response = client.get(
                    '/api/admin/stream/quality/http://test.stream/video?timeout=10'
                )
                assert response.status_code == 200
                assert response.json()['overall_quality'] == quality_level


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
