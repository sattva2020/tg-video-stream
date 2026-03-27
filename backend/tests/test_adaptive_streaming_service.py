"""
Unit tests for AdaptiveStreamingService
Feature 009 Phase 2: Adaptive Bitrate Streaming

Test coverage:
- Quality selection based on bandwidth thresholds
- Device type detection from user agents
- Quality decision making with hysteresis
- Confidence calculation based on network conditions
- Quality history tracking and logging
- Error handling and edge cases
- Bandwidth threshold selection
- Device rule application
- Config-based quality constraints
"""
import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch, AsyncMock
from enum import Enum

import pytest
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.adaptive_streaming_service import (
    AdaptiveStreamingService,
    QualityChangeReason,
    QualityDecision,
    get_adaptive_streaming_service,
)
from src.schemas.adaptive_streaming import (
    QualityLevel,
    DeviceType,
    QualityProfile,
)
from src.services.bandwidth_monitor import (
    BandwidthStatus,
    NetworkCondition,
    BandwidthMonitor,
)


# ======================== FIXTURES ========================

@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy async session."""
    session = MagicMock(spec=AsyncSession)

    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    return session


@pytest.fixture
def mock_bandwidth_monitor():
    """Mock BandwidthMonitor."""
    monitor = MagicMock(spec=BandwidthMonitor)

    # Mock bandwidth status
    mock_status = BandwidthStatus(
        stream_id="test-stream",
        current_bandwidth_kbps=5000.0,
        smoothed_bandwidth_kbps=4800.0,
        network_condition=NetworkCondition.STABLE,
        last_measurement=datetime.now(timezone.utc),
        measurements_count=10,
        min_bandwidth_kbps=4500.0,
        max_bandwidth_kbps=5200.0,
        avg_bandwidth_kbps=4800.0,
        avg_latency_ms=50.0,
    )
    monitor.get_bandwidth_status = AsyncMock(return_value=mock_status)
    monitor.measure_bandwidth = AsyncMock(return_value=mock_status)

    return monitor


@pytest.fixture
def mock_adaptive_config():
    """Mock AdaptiveStreamConfig."""
    config = MagicMock()
    config.id = 1
    config.stream_id = "test-stream-id"
    config.enabled = True
    config.default_quality = "high"
    config.min_quality = "low"
    config.max_quality = "ultra"
    config.bandwidth_threshold_low_kbps = 1000
    config.bandwidth_threshold_medium_kbps = 2500
    config.bandwidth_threshold_high_kbps = 5000
    config.bandwidth_threshold_ultra_kbps = 8000
    config.adaptation_interval_seconds = 30
    config.bandwidth_smoothing_factor = 0.3
    config.consecutive_measurements_required = 3
    config.device_rules = {
        "mobile": {"max_quality": "medium", "bandwidth_multiplier": 0.7},
        "desktop": {"max_quality": "ultra", "bandwidth_multiplier": 1.0},
    }
    config.quality_profiles = {}
    config.enable_bandwidth_monitoring = True
    config.enable_quality_logging = True
    config.statistics = {}
    config.created_at = datetime.now(timezone.utc)
    config.updated_at = datetime.now(timezone.utc)
    config.stream = None

    return config


@pytest.fixture
def adaptive_streaming_service(mock_bandwidth_monitor):
    """AdaptiveStreamingService instance with mocked dependencies."""
    service = AdaptiveStreamingService()
    service._bandwidth_monitor = mock_bandwidth_monitor
    return service


# ======================== TEST CLASSES ========================

class TestAdaptiveStreamingServiceInit:
    """Test service initialization and singleton pattern."""

    def test_singleton_pattern(self):
        """Test that service follows singleton pattern."""
        service1 = AdaptiveStreamingService()
        service2 = AdaptiveStreamingService()
        assert service1 is service2

    def test_get_adaptive_streaming_service(self):
        """Test dependency injection function."""
        service = get_adaptive_streaming_service()
        assert isinstance(service, AdaptiveStreamingService)

    def test_initialization(self):
        """Test service initialization."""
        service = AdaptiveStreamingService()
        assert service._bandwidth_monitor is None
        assert service._quality_history == {}
        assert service._current_quality == {}


class TestDetectDeviceType:
    """Test device type detection from user agents."""

    @pytest.mark.parametrize("user_agent,expected_device", [
        ("Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)", DeviceType.MOBILE),
        ("Mozilla/5.0 (Linux; Android 10)", DeviceType.MOBILE),
        ("Mozilla/5.0 (iPod; CPU iPhone OS 13_0 like Mac OS X)", DeviceType.MOBILE),
        ("Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)", DeviceType.TABLET),
        ("Mozilla/5.0 (Tablet; Android 10)", DeviceType.TABLET),
        ("Mozilla/5.0 (SmartTV; Linux)", DeviceType.TV),
        ("Mozilla/5.0 ( Television;)", DeviceType.TV),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64)", DeviceType.DESKTOP),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)", DeviceType.DESKTOP),
        ("Mozilla/5.0 (X11; Linux x86_64)", DeviceType.DESKTOP),
        ("Unknown Browser", DeviceType.UNKNOWN),
    ])
    def test_detect_device_type(self, adaptive_streaming_service, user_agent, expected_device):
        """Test device type detection from various user agents."""
        result = adaptive_streaming_service._detect_device_type(user_agent)
        assert result == expected_device

    def test_detect_device_type_case_insensitive(self, adaptive_streaming_service):
        """Test that detection is case insensitive."""
        user_agent = "Mozilla/5.0 (ANDROID 10)"
        result = adaptive_streaming_service._detect_device_type(user_agent)
        assert result == DeviceType.MOBILE


class TestSelectQualityByBandwidth:
    """Test quality selection based on bandwidth thresholds."""

    @pytest.mark.parametrize("bandwidth,expected_quality", [
        (500, QualityLevel.LOW),      # Below low threshold
        (1500, QualityLevel.LOW),     # At low threshold
        (2000, QualityLevel.MEDIUM),  # At medium threshold
        (3500, QualityLevel.MEDIUM),  # Between medium and high
        (5000, QualityLevel.HIGH),    # At high threshold
        (7000, QualityLevel.HIGH),    # Between high and ultra
        (8000, QualityLevel.ULTRA),   # At ultra threshold
        (10000, QualityLevel.ULTRA),  # Above ultra threshold
    ])
    def test_select_quality_by_bandwidth(
        self,
        adaptive_streaming_service,
        mock_adaptive_config,
        bandwidth,
        expected_quality
    ):
        """Test quality selection at various bandwidth levels."""
        result = adaptive_streaming_service._select_quality_by_bandwidth(
            bandwidth_kbps=bandwidth,
            config=mock_adaptive_config,
            min_quality=QualityLevel.LOW,
            max_quality=QualityLevel.ULTRA
        )
        assert result == expected_quality

    def test_select_quality_with_min_constraint(self, adaptive_streaming_service, mock_adaptive_config):
        """Test quality selection with minimum quality constraint."""
        result = adaptive_streaming_service._select_quality_by_bandwidth(
            bandwidth_kbps=500,
            config=mock_adaptive_config,
            min_quality=QualityLevel.MEDIUM,
            max_quality=QualityLevel.ULTRA
        )
        # Should return min_quality when bandwidth is too low
        assert result == QualityLevel.MEDIUM

    def test_select_quality_with_max_constraint(self, adaptive_streaming_service, mock_adaptive_config):
        """Test quality selection with maximum quality constraint."""
        result = adaptive_streaming_service._select_quality_by_bandwidth(
            bandwidth_kbps=10000,
            config=mock_adaptive_config,
            min_quality=QualityLevel.LOW,
            max_quality=QualityLevel.HIGH
        )
        # Should return max_quality even if bandwidth supports higher
        assert result == QualityLevel.HIGH

    def test_select_quality_narrow_range(self, adaptive_streaming_service, mock_adaptive_config):
        """Test quality selection with narrow quality range."""
        result = adaptive_streaming_service._select_quality_by_bandwidth(
            bandwidth_kbps=10000,
            config=mock_adaptive_config,
            min_quality=QualityLevel.MEDIUM,
            max_quality=QualityLevel.HIGH
        )
        # Should select highest within range
        assert result == QualityLevel.HIGH


class TestMakeQualityDecision:
    """Test quality decision making logic."""

    @pytest.mark.asyncio
    async def test_decision_with_bandwidth_data(
        self,
        adaptive_streaming_service,
        mock_adaptive_config,
        mock_bandwidth_monitor
    ):
        """Test quality decision when bandwidth data is available."""
        mock_status = BandwidthStatus(
            stream_id="test",
            current_bandwidth_kbps=6000.0,
            smoothed_bandwidth_kbps=5800.0,
            network_condition=NetworkCondition.STABLE,
            last_measurement=datetime.now(timezone.utc),
            measurements_count=10,
        )

        decision = adaptive_streaming_service._make_quality_decision(
            stream_id="test-stream",
            config=mock_adaptive_config,
            bandwidth_kbps=6000.0,
            device_type=DeviceType.DESKTOP,
            bandwidth_status=mock_status
        )

        assert decision.quality in [QualityLevel.HIGH, QualityLevel.ULTRA]
        assert decision.bandwidth_kbps == 6000.0
        assert decision.device_type == DeviceType.DESKTOP
        assert decision.confidence > 0.5

    @pytest.mark.asyncio
    async def test_decision_without_bandwidth_data(
        self,
        adaptive_streaming_service,
        mock_adaptive_config
    ):
        """Test quality decision when bandwidth data is not available."""
        decision = adaptive_streaming_service._make_quality_decision(
            stream_id="test-stream",
            config=mock_adaptive_config,
            bandwidth_kbps=None,
            device_type=DeviceType.DESKTOP,
            bandwidth_status=None
        )

        assert decision.quality == QualityLevel.HIGH  # Default quality
        assert decision.reason == QualityChangeReason.STARTUP
        assert decision.confidence == 0.5
        assert decision.bandwidth_kbps is None

    @pytest.mark.asyncio
    async def test_decision_with_bandwidth_monitoring_disabled(
        self,
        adaptive_streaming_service,
        mock_adaptive_config
    ):
        """Test decision when bandwidth monitoring is disabled."""
        mock_adaptive_config.enable_bandwidth_monitoring = False

        decision = adaptive_streaming_service._make_quality_decision(
            stream_id="test-stream",
            config=mock_adaptive_config,
            bandwidth_kbps=6000.0,
            device_type=DeviceType.DESKTOP,
            bandwidth_status=None
        )

        assert decision.quality == QualityLevel.HIGH  # Default quality
        assert decision.reason == QualityChangeReason.STARTUP

    @pytest.mark.asyncio
    async def test_decision_with_poor_network(
        self,
        adaptive_streaming_service,
        mock_adaptive_config
    ):
        """Test decision when network condition is poor."""
        adaptive_streaming_service._current_quality["test-stream"] = QualityLevel.HIGH

        mock_status = BandwidthStatus(
            stream_id="test",
            current_bandwidth_kbps=500.0,
            smoothed_bandwidth_kbps=500.0,
            network_condition=NetworkCondition.POOR,
            last_measurement=datetime.now(timezone.utc),
            measurements_count=5,
        )

        decision = adaptive_streaming_service._make_quality_decision(
            stream_id="test-stream",
            config=mock_adaptive_config,
            bandwidth_kbps=500.0,
            device_type=DeviceType.DESKTOP,
            bandwidth_status=mock_status
        )

        # Should keep current quality to prevent jumps
        assert decision.quality == QualityLevel.HIGH
        assert decision.reason == QualityChangeReason.BANDWIDTH

    @pytest.mark.asyncio
    async def test_decision_with_device_rules(
        self,
        adaptive_streaming_service,
        mock_adaptive_config
    ):
        """Test that device rules are applied correctly."""
        decision = adaptive_streaming_service._make_quality_decision(
            stream_id="test-stream",
            config=mock_adaptive_config,
            bandwidth_kbps=10000.0,
            device_type=DeviceType.MOBILE,
            bandwidth_status=None
        )

        # Mobile should be limited to medium quality per device rules
        assert decision.quality == QualityLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_decision_bandwidth_multiplier(
        self,
        adaptive_streaming_service,
        mock_adaptive_config,
        mock_bandwidth_monitor
    ):
        """Test that bandwidth multiplier is applied for devices."""
        mock_status = BandwidthStatus(
            stream_id="test",
            current_bandwidth_kbps=6000.0,
            smoothed_bandwidth_kbps=5800.0,
            network_condition=NetworkCondition.STABLE,
            last_measurement=datetime.now(timezone.utc),
            measurements_count=10,
        )

        # Mobile has 0.7 multiplier
        decision = adaptive_streaming_service._make_quality_decision(
            stream_id="test-stream",
            config=mock_adaptive_config,
            bandwidth_kbps=6000.0,
            device_type=DeviceType.MOBILE,
            bandwidth_status=mock_status
        )

        # 6000 * 0.7 = 4200, should be HIGH quality
        assert decision.quality == QualityLevel.HIGH


class TestCalculateConfidence:
    """Test confidence calculation logic."""

    @pytest.mark.asyncio
    async def test_confidence_with_stable_network(self, adaptive_streaming_service, mock_adaptive_config):
        """Test confidence calculation with stable network."""
        mock_status = BandwidthStatus(
            stream_id="test",
            current_bandwidth_kbps=5000.0,
            smoothed_bandwidth_kbps=4800.0,
            network_condition=NetworkCondition.STABLE,
            last_measurement=datetime.now(timezone.utc),
            measurements_count=10,
        )

        confidence = adaptive_streaming_service._calculate_confidence(
            bandwidth_status=mock_status,
            config=mock_adaptive_config
        )

        # Base (0.5) + stable (0.3) + measurements (0.2) = 1.0
        assert confidence == 1.0

    @pytest.mark.asyncio
    async def test_confidence_with_poor_network(self, adaptive_streaming_service, mock_adaptive_config):
        """Test confidence calculation with poor network."""
        mock_status = BandwidthStatus(
            stream_id="test",
            current_bandwidth_kbps=500.0,
            smoothed_bandwidth_kbps=500.0,
            network_condition=NetworkCondition.POOR,
            last_measurement=datetime.now(timezone.utc),
            measurements_count=10,
        )

        confidence = adaptive_streaming_service._calculate_confidence(
            bandwidth_status=mock_status,
            config=mock_adaptive_config
        )

        # Base (0.5) - poor (0.2) + measurements (0.2) = 0.5
        assert confidence == 0.5

    @pytest.mark.asyncio
    async def test_confidence_with_insufficient_measurements(
        self,
        adaptive_streaming_service,
        mock_adaptive_config
    ):
        """Test confidence with insufficient measurements."""
        mock_status = BandwidthStatus(
            stream_id="test",
            current_bandwidth_kbps=5000.0,
            smoothed_bandwidth_kbps=4800.0,
            network_condition=NetworkCondition.STABLE,
            last_measurement=datetime.now(timezone.utc),
            measurements_count=1,  # Less than required (3)
        )

        confidence = adaptive_streaming_service._calculate_confidence(
            bandwidth_status=mock_status,
            config=mock_adaptive_config
        )

        # Base (0.5) + stable (0.3) = 0.8
        assert confidence == 0.8

    @pytest.mark.asyncio
    async def test_confidence_without_status(self, adaptive_streaming_service, mock_adaptive_config):
        """Test confidence without bandwidth status."""
        confidence = adaptive_streaming_service._calculate_confidence(
            bandwidth_status=None,
            config=mock_adaptive_config
        )

        assert confidence == 0.5

    @pytest.mark.asyncio
    async def test_confidence_bounds(self, adaptive_streaming_service, mock_adaptive_config):
        """Test that confidence is bounded between 0 and 1."""
        # Test lower bound
        mock_status_poor = BandwidthStatus(
            stream_id="test",
            current_bandwidth_kbps=100.0,
            smoothed_bandwidth_kbps=100.0,
            network_condition=NetworkCondition.POOR,
            last_measurement=datetime.now(timezone.utc),
            measurements_count=1,
        )

        confidence_low = adaptive_streaming_service._calculate_confidence(
            bandwidth_status=mock_status_poor,
            config=mock_adaptive_config
        )
        assert 0.0 <= confidence_low <= 1.0

        # Test upper bound
        mock_status_good = BandwidthStatus(
            stream_id="test",
            current_bandwidth_kbps=10000.0,
            smoothed_bandwidth_kbps=10000.0,
            network_condition=NetworkCondition.STABLE,
            last_measurement=datetime.now(timezone.utc),
            measurements_count=10,
        )

        confidence_high = adaptive_streaming_service._calculate_confidence(
            bandwidth_status=mock_status_good,
            config=mock_adaptive_config
        )
        assert 0.0 <= confidence_high <= 1.0


class TestQualityDecision:
    """Test QualityDecision dataclass."""

    def test_quality_decision_creation(self):
        """Test creating a quality decision."""
        decision = QualityDecision(
            quality=QualityLevel.HIGH,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=5000.0,
            device_type=DeviceType.DESKTOP,
            confidence=0.9
        )

        assert decision.quality == QualityLevel.HIGH
        assert decision.reason == QualityChangeReason.BANDWIDTH
        assert decision.bandwidth_kbps == 5000.0
        assert decision.device_type == DeviceType.DESKTOP
        assert decision.confidence == 0.9

    def test_quality_decision_to_dict(self):
        """Test converting decision to dictionary."""
        decision = QualityDecision(
            quality=QualityLevel.HIGH,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=5000.0,
            device_type=DeviceType.DESKTOP,
            confidence=0.9
        )

        result = decision.to_dict()

        assert result["quality"] == "high"
        assert result["reason"] == "bandwidth"
        assert result["bandwidth_kbps"] == 5000.0
        assert result["device_type"] == "desktop"
        assert result["confidence"] == 0.9


class TestSelectQualityForStream:
    """Test select_quality_for_stream method."""

    @pytest.mark.asyncio
    async def test_select_quality_basic(
        self,
        adaptive_streaming_service,
        mock_db_session,
        mock_adaptive_config,
        mock_bandwidth_monitor
    ):
        """Test basic quality selection for a stream."""
        # Mock database to return config
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_adaptive_config
        mock_db_session.execute.return_value = mock_result

        decision = await adaptive_streaming_service.select_quality_for_stream(
            stream_id="test-stream",
            device_type=DeviceType.DESKTOP,
            db=mock_db_session
        )

        assert decision.quality in [QualityLevel.HIGH, QualityLevel.ULTRA]
        assert decision.device_type == DeviceType.DESKTOP
        assert adaptive_streaming_service._current_quality["test-stream"] == decision.quality

    @pytest.mark.asyncio
    async def test_select_quality_with_user_agent(
        self,
        adaptive_streaming_service,
        mock_db_session,
        mock_adaptive_config
    ):
        """Test quality selection with user agent detection."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_adaptive_config
        mock_db_session.execute.return_value = mock_result

        decision = await adaptive_streaming_service.select_quality_for_stream(
            stream_id="test-stream",
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0)",
            db=mock_db_session
        )

        assert decision.device_type == DeviceType.MOBILE
        # Should be limited to medium for mobile
        assert decision.quality == QualityLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_select_quality_force_measurement(
        self,
        adaptive_streaming_service,
        mock_db_session,
        mock_adaptive_config,
        mock_bandwidth_monitor
    ):
        """Test quality selection with forced bandwidth measurement."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_adaptive_config
        mock_db_session.execute.return_value = mock_result

        decision = await adaptive_streaming_service.select_quality_for_stream(
            stream_id="test-stream",
            device_type=DeviceType.DESKTOP,
            db=mock_db_session,
            force_measurement=True
        )

        # Verify that measure_bandwidth was called
        mock_bandwidth_monitor.measure_bandwidth.assert_called_once_with("test-stream")
        assert decision.quality is not None

    @pytest.mark.asyncio
    async def test_select_quality_without_db(
        self,
        adaptive_streaming_service,
        mock_bandwidth_monitor
    ):
        """Test quality selection without database session."""
        decision = await adaptive_streaming_service.select_quality_for_stream(
            stream_id="test-stream",
            device_type=DeviceType.DESKTOP,
            db=None
        )

        # Should return default quality without config
        assert decision.quality == QualityLevel.HIGH
        assert decision.reason == QualityChangeReason.STARTUP


class TestGetDefaultQualityProfiles:
    """Test default quality profiles."""

    def test_get_default_quality_profiles(self, adaptive_streaming_service):
        """Test retrieving default quality profiles."""
        profiles = adaptive_streaming_service.get_default_quality_profiles()

        assert "low" in profiles
        assert "medium" in profiles
        assert "high" in profiles
        assert "ultra" in profiles

        # Verify profile structure
        low_profile = profiles["low"]
        assert isinstance(low_profile, QualityProfile)
        assert low_profile.resolution == "640x360"
        assert low_profile.video_bitrate_kbps == 500
        assert low_profile.fps == 24.0

        # Test quality progression
        assert profiles["low"].video_bitrate_kbps < profiles["medium"].video_bitrate_kbps
        assert profiles["medium"].video_bitrate_kbps < profiles["high"].video_bitrate_kbps
        assert profiles["high"].video_bitrate_kbps < profiles["ultra"].video_bitrate_kbps


class TestQualityHistory:
    """Test quality history tracking and logging."""

    @pytest.mark.asyncio
    async def test_log_quality_change(
        self,
        adaptive_streaming_service,
        mock_adaptive_config
    ):
        """Test logging quality changes."""
        decision = QualityDecision(
            quality=QualityLevel.HIGH,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=5000.0,
            device_type=DeviceType.DESKTOP,
            confidence=0.9
        )

        await adaptive_streaming_service._log_quality_change(
            stream_id="test-stream",
            decision=decision,
            config=mock_adaptive_config
        )

        assert "test-stream" in adaptive_streaming_service._quality_history
        assert len(adaptive_streaming_service._quality_history["test-stream"]) == 1

        event = adaptive_streaming_service._quality_history["test-stream"][0]
        assert event["quality"] == "high"
        assert event["reason"] == "bandwidth"
        assert event["bandwidth_kbps"] == 5000.0

    @pytest.mark.asyncio
    async def test_log_quality_change_disabled(self, adaptive_streaming_service, mock_adaptive_config):
        """Test that logging is disabled when config says so."""
        mock_adaptive_config.enable_quality_logging = False

        decision = QualityDecision(
            quality=QualityLevel.HIGH,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=5000.0,
        )

        await adaptive_streaming_service._log_quality_change(
            stream_id="test-stream",
            decision=decision,
            config=mock_adaptive_config
        )

        assert "test-stream" not in adaptive_streaming_service._quality_history

    @pytest.mark.asyncio
    async def test_quality_history_limit(self, adaptive_streaming_service, mock_adaptive_config):
        """Test that history is limited to max size."""
        decision = QualityDecision(
            quality=QualityLevel.HIGH,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=5000.0,
        )

        # Add more than max (100) events
        for i in range(150):
            await adaptive_streaming_service._log_quality_change(
                stream_id="test-stream",
                decision=decision,
                config=mock_adaptive_config
            )

        # Should be limited to 100
        assert len(adaptive_streaming_service._quality_history["test-stream"]) == 100

    @pytest.mark.asyncio
    async def test_get_quality_history(self, adaptive_streaming_service, mock_adaptive_config):
        """Test retrieving quality history."""
        decision = QualityDecision(
            quality=QualityLevel.HIGH,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=5000.0,
        )

        # Add 5 events
        for i in range(5):
            await adaptive_streaming_service._log_quality_change(
                stream_id="test-stream",
                decision=decision,
                config=mock_adaptive_config
            )

        history = await adaptive_streaming_service.get_quality_history("test-stream")

        assert len(history) == 5
        assert all("timestamp" in event for event in history)
        assert all("quality" in event for event in history)

    @pytest.mark.asyncio
    async def test_get_quality_history_with_limit(self, adaptive_streaming_service, mock_adaptive_config):
        """Test retrieving quality history with limit."""
        decision = QualityDecision(
            quality=QualityLevel.HIGH,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=5000.0,
        )

        # Add 10 events
        for i in range(10):
            await adaptive_streaming_service._log_quality_change(
                stream_id="test-stream",
                decision=decision,
                config=mock_adaptive_config
            )

        history = await adaptive_streaming_service.get_quality_history("test-stream", limit=5)

        assert len(history) == 5

    @pytest.mark.asyncio
    async def test_clear_quality_history(self, adaptive_streaming_service, mock_adaptive_config):
        """Test clearing quality history."""
        decision = QualityDecision(
            quality=QualityLevel.HIGH,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=5000.0,
        )

        await adaptive_streaming_service._log_quality_change(
            stream_id="test-stream",
            decision=decision,
            config=mock_adaptive_config
        )

        assert len(adaptive_streaming_service._quality_history["test-stream"]) == 1

        await adaptive_streaming_service.clear_stream_history("test-stream")

        assert len(adaptive_streaming_service._quality_history["test-stream"]) == 0


class TestGetRecommendedAction:
    """Test recommended action generation."""

    def test_recommended_action_quality_increase(self, adaptive_streaming_service):
        """Test recommended action when quality should increase."""
        decision = QualityDecision(
            quality=QualityLevel.ULTRA,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=10000.0,
        )

        action = adaptive_streaming_service._get_recommended_action(
            decision=decision,
            current_quality=QualityLevel.HIGH
        )

        assert action is not None
        assert "Increase" in action
        assert "ultra" in action

    def test_recommended_action_quality_decrease(self, adaptive_streaming_service):
        """Test recommended action when quality should decrease."""
        decision = QualityDecision(
            quality=QualityLevel.LOW,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=500.0,
        )

        action = adaptive_streaming_service._get_recommended_action(
            decision=decision,
            current_quality=QualityLevel.HIGH
        )

        assert action is not None
        assert "Decrease" in action
        assert "low" in action

    def test_recommended_action_no_change(self, adaptive_streaming_service):
        """Test recommended action when quality is the same."""
        decision = QualityDecision(
            quality=QualityLevel.HIGH,
            reason=QualityChangeReason.BANDWIDTH,
            bandwidth_kbps=5000.0,
        )

        action = adaptive_streaming_service._get_recommended_action(
            decision=decision,
            current_quality=QualityLevel.HIGH
        )

        assert action is None


class TestGetStreamConfig:
    """Test getting stream configuration from database."""

    @pytest.mark.asyncio
    async def test_get_stream_config_found(self, adaptive_streaming_service, mock_db_session, mock_adaptive_config):
        """Test retrieving existing stream config."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_adaptive_config
        mock_db_session.execute.return_value = mock_result

        config = await adaptive_streaming_service.get_stream_config("test-stream", mock_db_session)

        assert config is not None
        assert config.stream_id == "test-stream"

    @pytest.mark.asyncio
    async def test_get_stream_config_not_found(self, adaptive_streaming_service, mock_db_session):
        """Test when stream config doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        config = await adaptive_streaming_service.get_stream_config("test-stream", mock_db_session)

        assert config is None

    @pytest.mark.asyncio
    async def test_get_stream_config_error_handling(self, adaptive_streaming_service, mock_db_session):
        """Test error handling in get_stream_config."""
        mock_db_session.execute.side_effect = Exception("Database error")

        with patch.object(adaptive_streaming_service, '__class__') as mock_logger:
            config = await adaptive_streaming_service.get_stream_config("test-stream", mock_db_session)

            assert config is None


class TestUpdateStreamStatistics:
    """Test updating stream statistics."""

    @pytest.mark.asyncio
    async def test_update_stream_statistics(
        self,
        adaptive_streaming_service,
        mock_db_session,
        mock_adaptive_config,
        mock_bandwidth_monitor
    ):
        """Test updating stream statistics in database."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_adaptive_config
        mock_db_session.execute.return_value = mock_result

        # Set some quality history
        adaptive_streaming_service._current_quality["test-stream"] = QualityLevel.HIGH
        adaptive_streaming_service._quality_history["test-stream"] = [
            {"timestamp": datetime.now(timezone.utc).isoformat()}
        ]

        await adaptive_streaming_service.update_stream_statistics("test-stream", mock_db_session)

        # Verify commit was called
        mock_db_session.commit.assert_called_once()
        assert mock_adaptive_config.statistics is not None

    @pytest.mark.asyncio
    async def test_update_stream_statistics_no_config(self, adaptive_streaming_service, mock_db_session):
        """Test updating statistics when config doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        # Should not raise error
        await adaptive_streaming_service.update_stream_statistics("test-stream", mock_db_session)

        # Commit should not be called
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_stream_statistics_error_handling(
        self,
        adaptive_streaming_service,
        mock_db_session,
        mock_adaptive_config
    ):
        """Test error handling in update_stream_statistics."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_adaptive_config
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit.side_effect = Exception("Commit error")

        # Should not raise error
        await adaptive_streaming_service.update_stream_statistics("test-stream", mock_db_session)

        # Rollback should be called
        mock_db_session.rollback.assert_called_once()


class TestGetStreamStatus:
    """Test getting complete stream status."""

    @pytest.mark.asyncio
    async def test_get_stream_status(
        self,
        adaptive_streaming_service,
        mock_db_session,
        mock_adaptive_config,
        mock_bandwidth_monitor
    ):
        """Test retrieving complete stream status."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_adaptive_config
        mock_db_session.execute.return_value = mock_result

        # Set current quality
        adaptive_streaming_service._current_quality["test-stream"] = QualityLevel.HIGH

        status = await adaptive_streaming_service.get_stream_status(
            stream_id="test-stream",
            db=mock_db_session,
            device_type=DeviceType.DESKTOP
        )

        assert status.stream_id == "test-stream"
        assert status.current_quality == QualityLevel.HIGH
        assert status.config is not None
        assert status.adaptive_enabled is True
        assert status.monitoring_enabled is True

    @pytest.mark.asyncio
    async def test_get_stream_status_no_config(
        self,
        adaptive_streaming_service,
        mock_db_session,
        mock_bandwidth_monitor
    ):
        """Test stream status when config doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        status = await adaptive_streaming_service.get_stream_status(
            stream_id="test-stream",
            db=mock_db_session,
            device_type=DeviceType.DESKTOP
        )

        assert status.stream_id == "test-stream"
        assert status.config is None
        assert status.adaptive_enabled is False
