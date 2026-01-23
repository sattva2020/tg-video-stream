"""Unit tests for StreamRecoveryService.

Tests the intelligent auto-recovery system for stream failures with:
- Exponential backoff retry logic
- Circuit breaker integration
- Multiple recovery strategies
- Recovery log tracking
"""

import uuid
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.services.stream_recovery_service import (
    StreamRecoveryService,
    RecoveryConfig,
    get_stream_recovery_service,
)
from src.services.circuit_breaker import CircuitBreakerState
from src.models.recovery_log import (
    RecoveryFailureType,
    RecoveryStrategy,
    RecoveryStatus,
)
from src.models.stream import Stream


# ======================== FIXTURES ========================

@pytest.fixture
def mock_stream_controller():
    """Mock StreamController for testing."""
    controller = MagicMock()
    controller.start_stream.return_value = True
    controller.stop_stream.return_value = True
    controller.restart_stream.return_value = True
    return controller


@pytest.fixture
def recovery_config():
    """RecoveryConfig with fast values for testing."""
    return RecoveryConfig(
        max_retries=2,  # Reduce for faster tests
        base_delay=1,  # 1 second for testing
        max_backoff=5,  # 5 seconds max
        exponential_base=2,
        jitter=False,  # Disable for deterministic tests
        circuit_breaker_failure_threshold=3,
        circuit_breaker_timeout=10,
    )


@pytest.fixture
def stream_recovery_service(db_session, mock_stream_controller, recovery_config):
    """StreamRecoveryService instance with mocked dependencies."""
    return StreamRecoveryService(
        db_session=db_session,
        config=recovery_config,
        stream_controller=mock_stream_controller,
    )


@pytest.fixture
def test_stream(db_session):
    """Create a test stream in the database."""
    from src.models.user import User, UserRole, UserStatus

    # Create owner user
    user = User(
        email="stream_owner@test.com",
        hashed_password="x",
        role=UserRole.ADMIN,
        status=UserStatus.APPROVED,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create stream
    stream = Stream(
        owner_id=user.id,
        chat_id=123456789,
        title="Test Stream",
        status=Stream.StreamStatus.ACTIVE,
    )
    db_session.add(stream)
    db_session.commit()
    db_session.refresh(stream)

    return stream


# ======================== INITIALIZATION TESTS ========================

class TestStreamRecoveryServiceInit:
    """Test StreamRecoveryService initialization."""

    def test_init_with_default_config(self, db_session):
        """Test initialization with default RecoveryConfig."""
        with patch("src.services.stream_recovery_service.get_stream_controller") as mock_get_controller:
            mock_controller = MagicMock()
            mock_get_controller.return_value = mock_controller

            service = StreamRecoveryService(db_session=db_session)

            assert service.db is db_session
            assert service.config.max_retries == 3
            assert service.config.base_delay == 60
            assert service.config.max_backoff == 600
            assert service.stream_controller is mock_controller
            assert len(service._circuit_breakers) == 0

    def test_init_with_custom_config(self, db_session, mock_stream_controller, recovery_config):
        """Test initialization with custom RecoveryConfig."""
        service = StreamRecoveryService(
            db_session=db_session,
            config=recovery_config,
            stream_controller=mock_stream_controller,
        )

        assert service.config is recovery_config
        assert service.config.max_retries == 2
        assert service.config.base_delay == 1
        assert service.stream_controller is mock_stream_controller

    def test_circuit_breaker_per_stream(self, stream_recovery_service):
        """Test that each stream gets its own circuit breaker."""
        stream_id_1 = uuid.uuid4()
        stream_id_2 = uuid.uuid4()

        cb_1 = stream_recovery_service._get_circuit_breaker(stream_id_1)
        cb_2 = stream_recovery_service._get_circuit_breaker(stream_id_2)

        assert cb_1 is not cb_2
        assert cb_1.name == f"stream-{stream_id_1}"
        assert cb_2.name == f"stream-{stream_id_2}"


# ======================== CIRCUIT BREAKER INTEGRATION TESTS ========================

class TestCircuitBreakerIntegration:
    """Test circuit breaker integration in recovery flow."""

    def test_circuit_breaker_blocks_recovery(self, stream_recovery_service, test_stream):
        """Test that open circuit breaker blocks recovery attempts."""
        stream_id = test_stream.id

        # Trip the circuit breaker
        cb = stream_recovery_service._get_circuit_breaker(stream_id)
        for _ in range(cb.config.failure_threshold):
            cb.record_failure()

        assert cb.state == CircuitBreakerState.OPEN

        # Try to recover - should be blocked
        result = stream_recovery_service.recover_stream(
            stream_id=stream_id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Test failure",
        )

        assert result["success"] is False
        assert result["circuit_breaker_open"] is True
        assert "Circuit breaker is OPEN" in result["error"]
        assert result["attempt_number"] == 0
        assert result["total_attempts"] == 0

    def test_circuit_breaker_records_success(self, stream_recovery_service, test_stream):
        """Test that successful recovery records success in circuit breaker."""
        stream_id = test_stream.id

        # Record some failures first
        cb = stream_recovery_service._get_circuit_breaker(stream_id)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        # Successful recovery
        result = stream_recovery_service.recover_stream(
            stream_id=stream_id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Connection lost",
        )

        assert result["success"] is True
        assert cb.failure_count == 0  # Should be reset

    def test_circuit_breaker_records_failure(self, stream_recovery_service, test_stream, mock_stream_controller):
        """Test that failed recovery records failure in circuit breaker."""
        stream_id = test_stream.id

        # Make stream controller fail
        mock_stream_controller.stop_stream.return_value = False

        # Failed recovery
        result = stream_recovery_service.recover_stream(
            stream_id=stream_id,
            failure_type=RecoveryFailureType.PROCESS_CRASH,
            failure_reason="Process crashed",
        )

        assert result["success"] is False

        # Check circuit breaker recorded the failures
        cb = stream_recovery_service._get_circuit_breaker(stream_id)
        assert cb.failure_count > 0


# ======================== RECOVER_STREAM TESTS ========================

class TestRecoverStream:
    """Test recover_stream method with various scenarios."""

    def test_recover_stream_success_on_first_attempt(self, stream_recovery_service, test_stream):
        """Test successful recovery on first attempt."""
        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Connection timeout",
        )

        assert result["success"] is True
        assert result["attempt_number"] == 1
        assert result["total_attempts"] == 1
        assert result["circuit_breaker_open"] is False
        assert "recovery_log_id" in result
        assert "duration_ms" in result

        # Verify recovery log was created
        logs = (
            stream_recovery_service.db.query(RecoveryLog)
            .filter(RecoveryLog.stream_id == test_stream.id)
            .all()
        )
        assert len(logs) == 1
        assert logs[0].status == RecoveryStatus.SUCCESS
        assert logs[0].attempt_number == 1

    def test_recover_stream_with_retry_success(self, stream_recovery_service, test_stream, mock_stream_controller):
        """Test recovery succeeds after initial failure."""
        # Make first attempt fail, second succeed
        call_count = [0]

        def side_effect_stop():
            call_count[0] += 1
            return call_count[0] > 1  # Fail first, succeed second

        mock_stream_controller.stop_stream.side_effect = side_effect_stop

        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.CODEC_ERROR,
            failure_reason="Codec initialization failed",
        )

        assert result["success"] is True
        assert result["attempt_number"] == 2
        assert result["total_attempts"] == 2

        # Verify two recovery logs were created
        logs = (
            stream_recovery_service.db.query(RecoveryLog)
            .filter(RecoveryLog.stream_id == test_stream.id)
            .all()
        )
        assert len(logs) == 2
        assert logs[0].status == RecoveryStatus.FAILED
        assert logs[1].status == RecoveryStatus.SUCCESS

    def test_recover_stream_abandoned_after_max_retries(self, stream_recovery_service, test_stream, mock_stream_controller):
        """Test recovery is abandoned after max retries."""
        # Always fail
        mock_stream_controller.stop_stream.return_value = False

        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.API_RATE_LIMIT,
            failure_reason="API rate limit exceeded",
        )

        assert result["success"] is False
        assert result["attempt_number"] == 2  # max_retries in fixture
        assert result["total_attempts"] == 2
        assert "abandoned" in result["error"].lower() or "failed after" in result["error"].lower()

        # Verify last log is ABANDONED
        logs = (
            stream_recovery_service.db.query(RecoveryLog)
            .filter(RecoveryLog.stream_id == test_stream.id)
            .order_by(RecoveryLog.started_at.desc())
            .first()
        )
        assert logs.status == RecoveryStatus.ABANDONED

    def test_recover_stream_not_found(self, stream_recovery_service):
        """Test recovery with non-existent stream ID."""
        non_existent_id = uuid.uuid4()

        result = stream_recovery_service.recover_stream(
            stream_id=non_existent_id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Test",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["attempt_number"] == 0

    def test_recover_stream_with_all_parameters(self, stream_recovery_service, test_stream):
        """Test recovery with all optional parameters."""
        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.SESSION_EXPIRED,
            failure_reason="Session expired",
            strategy=RecoveryStrategy.RECONNECT,
            error_code="AUTH_001",
            error_details={"traceback": "..."},
            recovery_metadata={"environment": "production"},
        )

        assert result["success"] is True

        # Verify log contains all details
        log = (
            stream_recovery_service.db.query(RecoveryLog)
            .filter(RecoveryLog.stream_id == test_stream.id)
            .first()
        )
        assert log.error_code == "AUTH_001"
        assert log.error_details == {"traceback": "..."}
        assert log.recovery_metadata == {"environment": "production"}
        assert log.recovery_strategy == RecoveryStrategy.RECONNECT


# ======================== RECOVERY STRATEGIES TESTS ========================

class TestRecoveryStrategies:
    """Test different recovery strategies."""

    def test_strategy_restart(self, stream_recovery_service, test_stream, mock_stream_controller):
        """Test RESTART strategy (default)."""
        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.PROCESS_CRASH,
            failure_reason="Process crashed",
            strategy=RecoveryStrategy.RESTART,
        )

        assert result["success"] is True
        # Verify stop and start were called
        mock_stream_controller.stop_stream.assert_called()
        mock_stream_controller.start_stream.assert_called()

    def test_strategy_reconnect_falls_back_to_restart(self, stream_recovery_service, test_stream):
        """Test RECONNECT strategy falls back to RESTART."""
        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Connection lost",
            strategy=RecoveryStrategy.RECONNECT,
        )

        # RECONNECT should work (falls back to restart internally)
        assert result["success"] is True

    def test_strategy_fallback_not_implemented(self, stream_recovery_service, test_stream):
        """Test FALLBACK strategy returns not implemented error."""
        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.CODEC_ERROR,
            failure_reason="Codec failed",
            strategy=RecoveryStrategy.FALLBACK,
        )

        assert result["success"] is False
        assert "not implemented" in result["error"].lower()

    def test_strategy_manual(self, stream_recovery_service, test_stream):
        """Test MANUAL strategy returns manual intervention required."""
        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.UNKNOWN,
            failure_reason="Unknown error",
            strategy=RecoveryStrategy.MANUAL,
        )

        assert result["success"] is False
        assert "manual intervention" in result["error"].lower()


# ======================== EXPONENTIAL BACKOFF TESTS ========================

class TestExponentialBackoff:
    """Test exponential backoff calculation."""

    def test_backoff_calculation_no_jitter(self, stream_recovery_service):
        """Test backoff calculation without jitter."""
        # base_delay=1, exponential_base=2
        # Attempt 1: 1 * 2^0 = 1
        # Attempt 2: 1 * 2^1 = 2
        # Attempt 3: 1 * 2^2 = 4 (capped at max_backoff=5)

        assert stream_recovery_service._calculate_backoff(1) == 1
        assert stream_recovery_service._calculate_backoff(2) == 2
        assert stream_recovery_service._calculate_backoff(3) == 4
        assert stream_recovery_service._calculate_backoff(10) == 5  # Capped at max_backoff

    def test_backoff_with_jitter(self, db_session, mock_stream_controller):
        """Test backoff with jitter enabled."""
        config = RecoveryConfig(
            max_retries=2,
            base_delay=10,
            max_backoff=100,
            jitter=True,
            jitter_factor=0.1,
        )
        service = StreamRecoveryService(
            db_session=db_session,
            config=config,
            stream_controller=mock_stream_controller,
        )

        # With jitter, value should be within ±10% of base delay
        backoff = service._calculate_backoff(1)
        assert 9 <= backoff <= 11  # 10 ± 1

    def test_backoff_minimum_one_second(self, db_session, mock_stream_controller):
        """Test backoff is never less than 1 second."""
        config = RecoveryConfig(
            max_retries=2,
            base_delay=0,
            max_backoff=100,
            jitter=False,
        )
        service = StreamRecoveryService(
            db_session=db_session,
            config=config,
            stream_controller=mock_stream_controller,
        )

        # Even with base_delay=0, should return at least 1
        assert service._calculate_backoff(1) >= 1


# ======================== RECOVERY STATS TESTS ========================

class TestRecoveryStats:
    """Test recovery statistics retrieval."""

    def test_get_recovery_stats_no_logs(self, stream_recovery_service, test_stream):
        """Test stats when no recovery logs exist."""
        stats = stream_recovery_service.get_recovery_stats(test_stream.id)

        assert stats["stream_id"] == str(test_stream.id)
        assert stats["total_attempts"] == 0
        assert stats["successful_recoveries"] == 0
        assert stats["failed_recoveries"] == 0
        assert stats["abandoned_recoveries"] == 0
        assert stats["last_recovery"] is None
        assert "circuit_breaker" in stats

    def test_get_recovery_stats_with_logs(self, stream_recovery_service, test_stream):
        """Test stats with recovery logs."""
        # Create some recovery logs
        log1 = RecoveryLog(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Test",
            recovery_strategy=RecoveryStrategy.RESTART,
            status=RecoveryStatus.SUCCESS,
            attempt_number=1,
            max_attempts=2,
            backoff_seconds=1,
        )
        log2 = RecoveryLog(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.API_RATE_LIMIT,
            failure_reason="Rate limit",
            recovery_strategy=RecoveryStrategy.RESTART,
            status=RecoveryStatus.FAILED,
            attempt_number=1,
            max_attempts=2,
            backoff_seconds=2,
        )

        stream_recovery_service.db.add(log1)
        stream_recovery_service.db.add(log2)
        stream_recovery_service.db.commit()

        stats = stream_recovery_service.get_recovery_stats(test_stream.id)

        assert stats["total_attempts"] == 2
        assert stats["successful_recoveries"] == 1
        assert stats["failed_recoveries"] == 1
        assert stats["last_recovery"] is not None
        assert stats["last_recovery"]["failure_type"] == "api_rate_limit"

    def test_reset_circuit_breaker(self, stream_recovery_service, test_stream):
        """Test manual circuit breaker reset."""
        stream_id = test_stream.id

        # Trip the circuit breaker
        cb = stream_recovery_service._get_circuit_breaker(stream_id)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Reset it
        stream_recovery_service.reset_circuit_breaker(stream_id)

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0


# ======================== RECENT RECOVERIES TESTS ========================

class TestRecentRecoveries:
    """Test retrieval of recent recovery logs."""

    def test_get_recent_recoveries_all(self, stream_recovery_service, test_stream):
        """Test getting all recent recoveries."""
        # Create multiple logs
        for i in range(3):
            log = RecoveryLog(
                stream_id=test_stream.id,
                failure_type=RecoveryFailureType.NETWORK,
                failure_reason=f"Test failure {i}",
                recovery_strategy=RecoveryStrategy.RESTART,
                status=RecoveryStatus.SUCCESS,
                attempt_number=1,
                max_attempts=2,
                backoff_seconds=1,
            )
            stream_recovery_service.db.add(log)
        stream_recovery_service.db.commit()

        recoveries = stream_recovery_service.get_recent_recoveries(limit=10)

        assert len(recoveries) == 3
        assert all("id" in r for r in recoveries)
        assert all("stream_id" in r for r in recoveries)
        assert all("failure_type" in r for r in recoveries)
        assert all("status" in r for r in recoveries)

    def test_get_recent_recoveries_filtered_by_stream(self, stream_recovery_service, test_stream, db_session):
        """Test filtering recoveries by stream ID."""
        # Create logs for two streams
        from src.models.user import User, UserRole, UserStatus

        user = User(
            email="user2@test.com",
            hashed_password="x",
            role=UserRole.USER,
            status=UserStatus.APPROVED,
        )
        db_session.add(user)
        db_session.commit()

        stream2 = Stream(
            owner_id=user.id,
            chat_id=987654321,
            title="Test Stream 2",
            status=Stream.StreamStatus.ACTIVE,
        )
        db_session.add(stream2)
        db_session.commit()

        # Add logs for both streams
        log1 = RecoveryLog(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Stream 1 failure",
            recovery_strategy=RecoveryStrategy.RESTART,
            status=RecoveryStatus.SUCCESS,
            attempt_number=1,
            max_attempts=2,
            backoff_seconds=1,
        )
        log2 = RecoveryLog(
            stream_id=stream2.id,
            failure_type=RecoveryFailureType.API_RATE_LIMIT,
            failure_reason="Stream 2 failure",
            recovery_strategy=RecoveryStrategy.RECONNECT,
            status=RecoveryStatus.FAILED,
            attempt_number=1,
            max_attempts=2,
            backoff_seconds=2,
        )

        stream_recovery_service.db.add(log1)
        stream_recovery_service.db.add(log2)
        stream_recovery_service.db.commit()

        # Get all logs
        all_recoveries = stream_recovery_service.get_recent_recoveries(limit=10)
        assert len(all_recoveries) == 2

        # Filter by stream
        stream_recoveries = stream_recovery_service.get_recent_recoveries(
            stream_id=test_stream.id, limit=10
        )
        assert len(stream_recoveries) == 1
        assert stream_recoveries[0]["stream_id"] == str(test_stream.id)

    def test_get_recent_recoveries_limit(self, stream_recovery_service, test_stream):
        """Test limit parameter for recent recoveries."""
        # Create 5 logs
        for i in range(5):
            log = RecoveryLog(
                stream_id=test_stream.id,
                failure_type=RecoveryFailureType.NETWORK,
                failure_reason=f"Failure {i}",
                recovery_strategy=RecoveryStrategy.RESTART,
                status=RecoveryStatus.SUCCESS,
                attempt_number=1,
                max_attempts=2,
                backoff_seconds=1,
            )
            stream_recovery_service.db.add(log)
        stream_recovery_service.db.commit()

        # Get with limit
        recoveries = stream_recovery_service.get_recent_recoveries(limit=3)
        assert len(recoveries) == 3


# ======================== FACTORY FUNCTION TESTS ========================

class TestFactoryFunction:
    """Test get_stream_recovery_service factory function."""

    def test_get_stream_recovery_service_singleton(self, db_session):
        """Test factory returns singleton instance."""
        with patch("src.services.stream_recovery_service.get_stream_controller") as mock_get_controller:
            mock_controller = MagicMock()
            mock_get_controller.return_value = mock_controller

            # Reset singleton
            import src.services.stream_recovery_service
            src.services.stream_recovery_service._recovery_service_instance = None

            service1 = get_stream_recovery_service(db_session)
            service2 = get_stream_recovery_service(db_session)

            assert service1 is service2

    def test_get_stream_recovery_service_creates_new_instance(self, db_session):
        """Test factory creates new StreamRecoveryService instance."""
        with patch("src.services.stream_recovery_service.get_stream_controller") as mock_get_controller:
            mock_controller = MagicMock()
            mock_get_controller.return_value = mock_controller

            # Reset singleton
            import src.services.stream_recovery_service
            src.services.stream_recovery_service._recovery_service_instance = None

            service = get_stream_recovery_service(db_session)

            assert isinstance(service, StreamRecoveryService)
            assert service.db is db_session


# ======================== ERROR HANDLING TESTS ========================

class TestErrorHandling:
    """Test error handling in recovery operations."""

    def test_recovery_with_exception_during_execution(self, stream_recovery_service, test_stream, mock_stream_controller):
        """Test recovery handles exceptions during execution."""
        # Make stream controller raise exception
        mock_stream_controller.stop_stream.side_effect = Exception("Unexpected error")

        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.UNKNOWN,
            failure_reason="Unknown error",
        )

        assert result["success"] is False
        assert "exception" in result["error"].lower()

    def test_recovery_creates_log_on_exception(self, stream_recovery_service, test_stream, mock_stream_controller):
        """Test that recovery creates FAILED log on exception."""
        mock_stream_controller.stop_stream.side_effect = RuntimeError("Critical error")

        stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.PROCESS_CRASH,
            failure_reason="Process crash",
        )

        # Verify log was created
        logs = (
            stream_recovery_service.db.query(RecoveryLog)
            .filter(RecoveryLog.stream_id == test_stream.id)
            .all()
        )
        assert len(logs) > 0
        # At least one should be FAILED
        failed_logs = [log for log in logs if log.status == RecoveryStatus.FAILED]
        assert len(failed_logs) > 0


# ======================== EDGE CASES TESTS ========================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_recovery_with_zero_max_retries(self, db_session, mock_stream_controller, test_stream):
        """Test recovery with max_retries=0 (should not attempt)."""
        config = RecoveryConfig(max_retries=0, base_delay=1, max_backoff=5)
        service = StreamRecoveryService(
            db_session=db_session,
            config=config,
            stream_controller=mock_stream_controller,
        )

        result = service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Test",
        )

        # Should not attempt any recovery
        assert result["success"] is False
        assert result["total_attempts"] == 0

    def test_multiple_streams_independent_circuit_breakers(self, stream_recovery_service, db_session):
        """Test that multiple streams have independent circuit breakers."""
        from src.models.user import User, UserRole, UserStatus

        # Create two streams
        user = User(
            email="multi_user@test.com",
            hashed_password="x",
            role=UserRole.ADMIN,
            status=UserStatus.APPROVED,
        )
        db_session.add(user)
        db_session.commit()

        stream1 = Stream(
            owner_id=user.id, chat_id=111, title="Stream 1", status=Stream.StreamStatus.ACTIVE
        )
        stream2 = Stream(
            owner_id=user.id, chat_id=222, title="Stream 2", status=Stream.StreamStatus.ACTIVE
        )
        db_session.add(stream1)
        db_session.add(stream2)
        db_session.commit()

        # Trip circuit breaker for stream1
        cb1 = stream_recovery_service._get_circuit_breaker(stream1.id)
        cb1.record_failure()
        cb1.record_failure()
        cb1.record_failure()

        # Stream2's circuit breaker should still be closed
        cb2 = stream_recovery_service._get_circuit_breaker(stream2.id)
        assert cb1.state == CircuitBreakerState.OPEN
        assert cb2.state == CircuitBreakerState.CLOSED

    def test_recovery_log_duration_calculation(self, stream_recovery_service, test_stream):
        """Test that recovery log duration is calculated correctly."""
        start_time = datetime.now(timezone.utc)

        result = stream_recovery_service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Test",
        )

        assert result["success"] is True

        # Get the log and verify duration
        log = (
            stream_recovery_service.db.query(RecoveryLog)
            .filter(RecoveryLog.stream_id == test_stream.id)
            .first()
        )

        assert log.duration_ms is not None
        assert log.duration_ms >= 0
        # Duration should be reasonable (less than 10 seconds for fast test)
        assert log.duration_ms < 10000
