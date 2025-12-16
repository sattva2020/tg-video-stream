"""
Feature 022 Phase 3: Stream Quality Trends and Alerts - Tests

Unit tests for quality trends service and API endpoints
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.services.quality_trends_service import QualityTrendsService
from src.schemas.stream_quality import (
    QualityTrendData,
    QualityAlertConfigUpdate,
    QualityAlertConfigResponse,
    QualityAlertEvent,
)
from src.models.stream_quality import (
    StreamQualityHistory,
    QualityAlertConfig,
    QualityTrendSnapshot,
)


@pytest.fixture
def app():
    """Create test FastAPI app"""
    app = FastAPI()
    return app


@pytest.fixture
def trends_service():
    """Get singleton trends service"""
    return QualityTrendsService()


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy session"""
    db = MagicMock()
    return db


class TestQualityTrendsService:
    """Tests for QualityTrendsService"""

    @pytest.mark.asyncio
    async def test_record_quality_analysis_success(self, trends_service, mock_db):
        """Test recording successful quality analysis"""
        result = await trends_service.record_quality_analysis(
            db=mock_db,
            stream_url="http://stream.local/video",
            stream_name="Test Stream",
            audio_codec="aac",
            audio_bitrate_kbps=128,
            audio_sample_rate_hz=48000,
            audio_channels=2,
            audio_quality="high",
            video_codec="h264",
            video_bitrate_kbps=2500,
            video_resolution="1920x1080",
            video_fps=30,
            video_quality="high",
            overall_quality="high",
            is_audio_only=False,
            is_video_only=False,
            analysis_duration_ms=1500,
            success=True,
        )
        
        # Verify record was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_quality_analysis_with_error(self, trends_service, mock_db):
        """Test recording failed quality analysis"""
        result = await trends_service.record_quality_analysis(
            db=mock_db,
            stream_url="http://invalid.stream",
            overall_quality="unknown",
            success=False,
            error_message="Connection timeout",
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_quality_trend_with_history(self, trends_service, mock_db):
        """Test getting quality trend with historical data"""
        # Mock database query
        now = datetime.utcnow()
        mock_histories = [
            MagicMock(
                analyzed_at=now - timedelta(hours=i),
                overall_quality="high",
                audio_quality="high",
                audio_bitrate_kbps=128,
                video_quality="high",
                video_bitrate_kbps=2500,
                video_resolution="1920x1080",
                video_fps=30,
                success=True,
                stream_name="Test Stream",
            )
            for i in range(5)
        ]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            mock_histories
        )
        mock_db.query.return_value.filter.return_value.count.return_value = 5

        trend = await trends_service.get_quality_trend(
            db=mock_db,
            stream_url="http://stream.local",
            hours=24,
        )

        assert trend.stream_url == "http://stream.local"
        assert len(trend.history) == 5
        assert trend.average_quality == "high"
        assert trend.samples_count == 5

    @pytest.mark.asyncio
    async def test_get_quality_trend_no_data(self, trends_service, mock_db):
        """Test getting quality trend with no data"""
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = (
            []
        )

        trend = await trends_service.get_quality_trend(
            db=mock_db,
            stream_url="http://unknown.stream",
            hours=24,
        )

        assert trend.stream_url == "http://unknown.stream"
        assert trend.history == []
        assert trend.samples_count == 0

    @pytest.mark.asyncio
    async def test_set_alert_config_create_new(self, trends_service, mock_db):
        """Test creating new alert configuration"""
        config_update = QualityAlertConfigUpdate(
            stream_url="http://stream.local",
            stream_name="Test Stream",
            min_overall_quality="high",
            min_audio_bitrate_kbps=128,
            consecutive_failures=3,
            enabled=True,
        )

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await trends_service.set_alert_config(db=mock_db, config_update=config_update)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_alert_config_update_existing(self, trends_service, mock_db):
        """Test updating existing alert configuration"""
        config_update = QualityAlertConfigUpdate(
            stream_url="http://stream.local",
            min_overall_quality="high",
        )

        existing_config = MagicMock(
            stream_url="http://stream.local",
            stream_name="Test Stream",
            min_overall_quality="medium",
        )
        mock_db.query.return_value.filter.return_value.first.return_value = existing_config

        result = await trends_service.set_alert_config(db=mock_db, config_update=config_update)

        # Verify update
        assert existing_config.min_overall_quality == "high"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_alert_config_exists(self, trends_service, mock_db):
        """Test getting existing alert configuration"""
        existing_config = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_config

        result = await trends_service.get_alert_config(
            db=mock_db,
            stream_url="http://stream.local",
        )

        assert result is not None
        mock_db.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_alert_config_not_found(self, trends_service, mock_db):
        """Test getting non-existent alert configuration"""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await trends_service.get_alert_config(
            db=mock_db,
            stream_url="http://unknown.stream",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_quality_to_number_conversion(self):
        """Test quality level to number conversion"""
        assert QualityTrendsService._quality_to_number("low") == 1
        assert QualityTrendsService._quality_to_number("medium") == 2
        assert QualityTrendsService._quality_to_number("high") == 3
        assert QualityTrendsService._quality_to_number("lossless") == 4
        assert QualityTrendsService._quality_to_number("ultra") == 5
        assert QualityTrendsService._quality_to_number("unknown") == 0

    @pytest.mark.asyncio
    async def test_number_to_quality_conversion(self):
        """Test number to quality level conversion"""
        assert QualityTrendsService._number_to_quality(0.5) == "low"
        assert QualityTrendsService._number_to_quality(1.5) == "medium"
        assert QualityTrendsService._number_to_quality(2.5) == "high"
        assert QualityTrendsService._number_to_quality(3.5) == "lossless"
        assert QualityTrendsService._number_to_quality(4.5) == "ultra"


class TestTrendsAPIEndpoints:
    """Tests for Phase 3 API endpoints"""

    @pytest.mark.asyncio
    async def test_get_quality_trend_endpoint(self, client: TestClient):
        """Test GET /api/admin/stream/quality/trend endpoint"""
        with patch("src.api.admin.get_quality_trends_service") as mock_service:
            mock_trends_service = AsyncMock()
            mock_service.return_value = mock_trends_service

            mock_trend_data = MagicMock(spec=QualityTrendData)
            mock_trends_service.get_quality_trend.return_value = mock_trend_data

            # Note: This is a placeholder since we need actual client fixture
            # In real tests, we'd use TestClient from fastapi.testclient

    @pytest.mark.asyncio
    async def test_set_quality_alert_config_endpoint(self):
        """Test POST /api/admin/stream/quality/alert/config endpoint"""
        config_update = {
            "stream_url": "http://stream.local",
            "stream_name": "Test Stream",
            "min_overall_quality": "high",
            "enabled": True,
        }

        # In real tests with TestClient:
        # response = client.post("/api/admin/stream/quality/alert/config", json=config_update)
        # assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_quality_alert_config_endpoint(self):
        """Test GET /api/admin/stream/quality/alert/config endpoint"""
        # In real tests:
        # response = client.get("/api/admin/stream/quality/alert/config/http://stream.local")
        # assert response.status_code == 200


class TestAlertTriggering:
    """Tests for alert trigger logic"""

    @pytest.mark.asyncio
    async def test_alert_triggered_on_quality_degradation(self, trends_service, mock_db):
        """Test alert is triggered when quality degrades"""
        config = MagicMock()
        config.enabled = True
        config.min_overall_quality = "high"
        config.consecutive_failures = 3
        config.consecutive_failures_count = 2
        config.stream_name = "Test Stream"
        config.notify_on_degradation = True

        mock_db.query.return_value.filter.return_value.first.return_value = config

        alert = await trends_service._check_and_trigger_alerts(
            db=mock_db,
            stream_url="http://stream.local",
            current_quality="medium",  # Below threshold
        )

        # Third consecutive failure should trigger alert
        assert config.consecutive_failures_count == 3

    @pytest.mark.asyncio
    async def test_alert_triggered_on_recovery(self, trends_service, mock_db):
        """Test alert is triggered when quality recovers"""
        config = MagicMock()
        config.enabled = True
        config.min_overall_quality = "high"
        config.consecutive_failures_count = 3
        config.stream_name = "Test Stream"
        config.notify_on_recovery = True

        mock_db.query.return_value.filter.return_value.first.return_value = config

        alert = await trends_service._check_and_trigger_alerts(
            db=mock_db,
            stream_url="http://stream.local",
            current_quality="high",  # Above threshold
        )

        # Should reset counter
        assert config.consecutive_failures_count == 0

    @pytest.mark.asyncio
    async def test_alert_disabled(self, trends_service, mock_db):
        """Test alerts are not triggered when disabled"""
        config = MagicMock()
        config.enabled = False

        mock_db.query.return_value.filter.return_value.first.return_value = config

        alert = await trends_service._check_and_trigger_alerts(
            db=mock_db,
            stream_url="http://stream.local",
            current_quality="low",
        )

        assert alert is None


class TestQualityHistoryPersistence:
    """Tests for quality history persistence"""

    @pytest.mark.asyncio
    async def test_history_records_all_metrics(self, trends_service, mock_db):
        """Test that history records all quality metrics"""
        await trends_service.record_quality_analysis(
            db=mock_db,
            stream_url="http://stream.local",
            stream_name="Test",
            audio_codec="aac",
            audio_bitrate_kbps=128,
            audio_sample_rate_hz=48000,
            audio_channels=2,
            audio_quality="high",
            video_codec="h264",
            video_bitrate_kbps=2500,
            video_resolution="1920x1080",
            video_fps=30,
            video_quality="high",
            overall_quality="high",
            analysis_duration_ms=1500,
        )

        # Verify all fields were set
        call_args = mock_db.add.call_args
        history = call_args[0][0]

        assert history.audio_codec == "aac"
        assert history.video_resolution == "1920x1080"
        assert history.overall_quality == "high"

    @pytest.mark.asyncio
    async def test_history_with_raw_data_backup(self, trends_service, mock_db):
        """Test history includes raw data backup"""
        raw_data = {
            "format": "audio",
            "bitrate": "128k",
            "duration": "3600",
        }

        await trends_service.record_quality_analysis(
            db=mock_db,
            stream_url="http://stream.local",
            overall_quality="high",
            raw_data=raw_data,
        )

        call_args = mock_db.add.call_args
        history = call_args[0][0]

        assert history.raw_data == raw_data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
