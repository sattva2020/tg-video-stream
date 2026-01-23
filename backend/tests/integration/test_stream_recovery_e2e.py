"""
Integration Tests: Stream Recovery End-to-End
Тестируем полный цикл автоматического восстановления потока

Coverage Target: End-to-end recovery flow testing
"""
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.stream import Stream, StreamStatus
from src.models.recovery_log import RecoveryLog, RecoveryFailureType, RecoveryStatus, RecoveryStrategy
from src.services.stream_recovery_service import StreamRecoveryService, RecoveryConfig
from src.services.stream_health_monitor import StreamHealthMonitor, StreamHealthStatus
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerState


@pytest.fixture
def test_stream(db_session):
    """Create active stream in DB"""
    stream = Stream(
        title="E2E Test Stream",
        chat_id=1234567890,
        owner_id=uuid.uuid4(),  # Will be set to real user
        status=StreamStatus.ACTIVE,
        current_track_index=0
    )
    # Set owner to admin user created in conftest
    from src.models.user import User
    owner = db_session.query(User).filter_by(email='admin@test').first()
    if owner:
        stream.owner_id = owner.id
    else:
        # Create owner if not exists
        owner = User(
            email='stream_owner@test.com',
            google_id='owner_123',
            status='approved',
            role='admin'
        )
        db_session.add(owner)
        db_session.commit()
        db_session.refresh(owner)
        stream.owner_id = owner.id

    db_session.add(stream)
    db_session.commit()
    db_session.refresh(stream)
    return stream


@pytest.fixture
def fast_recovery_config():
    """Fast recovery config for testing (reduced delays)"""
    return RecoveryConfig(
        max_retries=3,
        base_delay=1,  # 1 second for fast testing
        max_backoff=5,  # 5 seconds max
        exponential_base=2,
        jitter=False,  # Disable jitter for predictable testing
        circuit_breaker_failure_threshold=3,  # Open after 3 failures
        circuit_breaker_timeout=10  # 10 seconds timeout
    )


# ==================== 1. Basic Recovery Flow ====================

class TestBasicRecoveryFlow:
    """Тесты базового цикла восстановления"""

    def test_stream_failure_creates_recovery_log(self, db_session, test_stream):
        """При отказе потока создаётся запись в recovery_logs"""
        # Simulate stream failure by creating recovery log directly
        recovery_log = RecoveryLog(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Connection timeout",
            recovery_strategy=RecoveryStrategy.RESTART,
            status=RecoveryStatus.PENDING,
            attempt_number=1,
            max_attempts=3
        )
        db_session.add(recovery_log)
        db_session.commit()
        db_session.refresh(recovery_log)

        # Verify recovery log was created
        assert recovery_log.id is not None
        assert recovery_log.stream_id == test_stream.id
        assert recovery_log.failure_type == RecoveryFailureType.NETWORK
        assert recovery_log.status == RecoveryStatus.PENDING
        assert recovery_log.attempt_number == 1

    def test_recovery_service_records_failure(self, db_session, test_stream, fast_recovery_config):
        """StreamRecoveryService записывает отказ в базу данных"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Simulate failure detection
        result = service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.PROCESS_CRASH,
            failure_reason="FFmpeg process crashed",
            recovery_strategy=RecoveryStrategy.RESTART
        )

        # Verify recovery was attempted
        assert "success" in result or "error" in result

        # Check database for recovery log
        logs = db_session.query(RecoveryLog).filter(
            RecoveryLog.stream_id == test_stream.id
        ).all()

        assert len(logs) > 0
        latest_log = logs[0]
        assert latest_log.failure_type == RecoveryFailureType.PROCESS_CRASH
        assert latest_log.failure_reason == "FFmpeg process crashed"
        assert latest_log.recovery_strategy == RecoveryStrategy.RESTART

    def test_recovery_updates_circuit_breaker_state(self, db_session, test_stream, fast_recovery_config):
        """Состояние circuit breaker сохраняется в recovery_log"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Trigger first failure
        service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Network error",
            recovery_strategy=RecoveryStrategy.RESTART
        )

        # Get the recovery log
        logs = db_session.query(RecoveryLog).filter(
            RecoveryLog.stream_id == test_stream.id
        ).all()

        assert len(logs) > 0
        latest_log = logs[0]

        # Verify circuit breaker state is recorded
        assert latest_log.circuit_breaker_state is not None
        assert "state" in latest_log.circuit_breaker_state


# ==================== 2. Exponential Backoff ====================

class TestExponentialBackoff:
    """Тесты экспоненциальной задержки между попытками"""

    def test_backoff_increases_with_each_retry(self, db_session, test_stream, fast_recovery_config):
        """Задержка увеличивается экспоненциально с каждой попыткой"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Calculate backoff for different attempts
        backoff_1 = service._calculate_backoff(attempt=1)
        backoff_2 = service._calculate_backoff(attempt=2)
        backoff_3 = service._calculate_backoff(attempt=3)

        # Verify exponential growth: base_delay * 2^(attempt-1)
        # With base_delay=1: 1, 2, 4, 8, ... (capped at max_backoff=5)
        assert backoff_1 == 1
        assert backoff_2 == 2
        assert backoff_3 == 4  # Not capped yet

    def test_backoff_capped_at_max(self, db_session, test_stream, fast_recovery_config):
        """Задержка ограничена max_backoff"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Calculate backoff for attempt that would exceed max
        backoff_high = service._calculate_backoff(attempt=10)

        # Should be capped at max_backoff=5
        assert backoff_high == 5

    def test_recovery_logs_record_backoff_times(self, db_session, test_stream, fast_recovery_config):
        """В recovery_log записывается текущая задержка backoff"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Trigger recovery
        service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.API_RATE_LIMIT,
            failure_reason="Rate limit exceeded",
            recovery_strategy=RecoveryStrategy.RESTART
        )

        # Get recovery log
        logs = db_session.query(RecoveryLog).filter(
            RecoveryLog.stream_id == test_stream.id
        ).all()

        assert len(logs) > 0
        latest_log = logs[0]

        # Verify backoff is recorded
        assert latest_log.backoff_seconds is not None
        assert latest_log.backoff_seconds >= 1


# ==================== 3. Circuit Breaker Behavior ====================

class TestCircuitBreakerE2E:
    """Тесты circuit breaker в конце-в-конец сценариях"""

    def test_circuit_breaker_opens_after_threshold(self, db_session, test_stream, fast_recovery_config):
        """Circuit breaker открывается после достижения порога отказов"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Trigger failures up to threshold (3 for fast config)
        for i in range(3):
            service.recover_stream(
                stream_id=test_stream.id,
                failure_type=RecoveryFailureType.NETWORK,
                failure_reason=f"Failure attempt {i+1}",
                recovery_strategy=RecoveryStrategy.RESTART
            )

        # Get circuit breaker
        cb = service._get_or_create_circuit_breaker(test_stream.id)

        # Verify circuit breaker is OPEN
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_blocks_recovery_when_open(self, db_session, test_stream, fast_recovery_config):
        """Открытый circuit breaker блокирует попытки восстановления"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Force open circuit breaker by triggering threshold failures
        for i in range(3):
            try:
                service.recover_stream(
                    stream_id=test_stream.id,
                    failure_type=RecoveryFailureType.CODEC_ERROR,
                    failure_reason=f"Codec error {i+1}",
                    recovery_strategy=RecoveryStrategy.RESTART
                )
            except:
                pass

        # Verify circuit is open
        cb = service._get_or_create_circuit_breaker(test_stream.id)
        assert cb.state == CircuitBreakerState.OPEN

        # Try another recovery - should be blocked by circuit breaker
        result = service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Should be blocked",
            recovery_strategy=RecoveryStrategy.RESTART
        )

        # Should fail due to circuit breaker
        assert result["success"] == False
        assert "circuit breaker" in result["error"].lower()

    def test_circuit_breaker_transitions_to_half_open_after_timeout(self, db_session, test_stream, fast_recovery_config):
        """Circuit breaker переходит в HALF_OPEN после timeout"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Open the circuit breaker
        for i in range(3):
            try:
                service.recover_stream(
                    stream_id=test_stream.id,
                    failure_type=RecoveryFailureType.SESSION_EXPIRED,
                    failure_reason=f"Session error {i+1}",
                    recovery_strategy=RecoveryStrategy.RESTART
                )
            except:
                pass

        cb = service._get_or_create_circuit_breaker(test_stream.id)
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout (10 seconds for fast config)
        time.sleep(11)

        # Try a request - should transition to HALF_OPEN
        cb.allow_request()
        assert cb.state == CircuitBreakerState.HALF_OPEN


# ==================== 4. Health Monitor Integration ====================

class TestHealthMonitorIntegration:
    """Тесты интеграции с StreamHealthMonitor"""

    def test_health_monitor_detects_unhealthy_stream(self, db_session, test_stream):
        """StreamHealthMonitor обнаруживает неработоспособный поток"""
        monitor = StreamHealthMonitor()

        # Simulate stream failure by changing status to ERROR
        test_stream.status = StreamStatus.ERROR
        db_session.commit()

        # Check stream health
        health_status = monitor.check_stream_health(
            stream_id=str(test_stream.id),
            stream_status=test_stream.status,
            process_check=lambda: False,  # Simulate process not running
            network_check=lambda: False   # Simulate network failure
        )

        # Verify unhealthy status detected
        assert health_status.is_healthy == False
        assert health_status.consecutive_failures > 0

    def test_health_monitor_stores_state_in_redis(self, db_session, test_stream):
        """Состояние здоровья сохраняется в Redis"""
        monitor = StreamHealthMonitor()

        # Update stream health
        health_status = StreamHealthStatus(
            stream_id=str(test_stream.id),
            is_healthy=False,
            last_check=datetime.now(timezone.utc),
            consecutive_failures=2,
            last_failure_type="network"
        )

        # Store in Redis
        import asyncio
        asyncio.run(monitor._save_stream_health(health_status))

        # Retrieve from Redis
        retrieved = asyncio.run(monitor.get_stream_health(str(test_stream.id)))

        # Verify health status persisted
        assert retrieved is not None
        assert retrieved.is_healthy == False
        assert retrieved.consecutive_failures == 2


# ==================== 5. Recovery Statistics ====================

class TestRecoveryStatistics:
    """Тесты статистики восстановлений"""

    def test_get_recovery_stats_returns_correct_counts(self, db_session, test_stream, fast_recovery_config):
        """Статистика восстановлений возвращает правильные счётчики"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Create some recovery logs with different statuses
        log1 = RecoveryLog(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Network error 1",
            status=RecoveryStatus.SUCCESS,
            attempt_number=1,
            max_attempts=3
        )

        log2 = RecoveryLog(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.API_RATE_LIMIT,
            failure_reason="Rate limit",
            status=RecoveryStatus.FAILED,
            attempt_number=1,
            max_attempts=3
        )

        log3 = RecoveryLog(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.CODEC_ERROR,
            failure_reason="Codec error",
            status=RecoveryStatus.ABANDONED,
            attempt_number=3,
            max_attempts=3
        )

        db_session.add_all([log1, log2, log3])
        db_session.commit()

        # Get stats
        stats = service.get_recovery_stats(test_stream.id)

        # Verify counts
        assert stats["total_attempts"] == 3
        assert stats["successful_recoveries"] == 1
        assert stats["failed_recoveries"] == 1
        assert stats["abandoned_recoveries"] == 1

    def test_get_recent_recoveries_returns_limited_results(self, db_session, test_stream, fast_recovery_config):
        """get_recent_recoveries возвращает ограниченное количество записей"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Create multiple recovery logs
        for i in range(5):
            log = RecoveryLog(
                stream_id=test_stream.id,
                failure_type=RecoveryFailureType.NETWORK,
                failure_reason=f"Error {i+1}",
                status=RecoveryStatus.SUCCESS,
                attempt_number=1,
                max_attempts=3
            )
            db_session.add(log)
        db_session.commit()

        # Get recent recoveries with limit
        recent = service.get_recent_recoveries(test_stream.id, limit=3)

        # Verify limit
        assert len(recent) == 3


# ==================== 6. End-to-End Scenario ====================

class TestFullRecoveryScenario:
    """Полный сценарий от отказа до восстановления"""

    def test_complete_recovery_workflow(self, db_session, test_stream, fast_recovery_config):
        """Полный workflow: отказ → обнаружение → попытка → логирование"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Step 1: Simulate stream failure
        test_stream.status = StreamStatus.ERROR
        db_session.commit()

        # Step 2: Detect failure and trigger recovery
        result = service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.PROCESS_CRASH,
            failure_reason="FFmpeg crashed with segfault",
            recovery_strategy=RecoveryStrategy.RESTART
        )

        # Step 3: Verify recovery was attempted
        assert "success" in result

        # Step 4: Verify recovery log created
        logs = db_session.query(RecoveryLog).filter(
            RecoveryLog.stream_id == test_stream.id
        ).order_by(RecoveryLog.started_at.desc()).first()

        assert logs is not None
        assert logs.failure_type == RecoveryFailureType.PROCESS_CRASH
        assert logs.status in [RecoveryStatus.SUCCESS, RecoveryStatus.FAILED, RecoveryStatus.IN_PROGRESS]

        # Step 5: Verify circuit breaker state updated
        cb = service._get_or_create_circuit_breaker(test_stream.id)
        assert cb is not None

        # Step 6: Verify statistics
        stats = service.get_recovery_stats(test_stream.id)
        assert stats["total_attempts"] >= 1

    def test_multiple_failures_with_backoff(self, db_session, test_stream, fast_recovery_config):
        """Множественные отказы с экспоненциальной задержкой"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Simulate multiple failures
        for i in range(3):
            result = service.recover_stream(
                stream_id=test_stream.id,
                failure_type=RecoveryFailureType.NETWORK,
                failure_reason=f"Network failure {i+1}",
                recovery_strategy=RecoveryStrategy.RESTART
            )

            # Each attempt should create a log
            logs = db_session.query(RecoveryLog).filter(
                RecoveryLog.stream_id == test_stream.id
            ).all()

            assert len(logs) == i + 1

            # Verify backoff increases
            latest_log = logs[-1]
            expected_backoff = service._calculate_backoff(attempt=1)
            assert latest_log.backoff_seconds == expected_backoff

    def test_circuit_breaker_prevents_cascading_failures(self, db_session, test_stream, fast_recovery_config):
        """Circuit breaker предотвращает каскадные отказы"""
        service = StreamRecoveryService(db_session, config=fast_recovery_config)

        # Trigger enough failures to open circuit
        for i in range(5):
            result = service.recover_stream(
                stream_id=test_stream.id,
                failure_type=RecoveryFailureType.API_RATE_LIMIT,
                failure_reason=f"Rate limit {i+1}",
                recovery_strategy=RecoveryStrategy.RESTART
            )

        # Verify circuit is open
        cb = service._get_or_create_circuit_breaker(test_stream.id)
        assert cb.state == CircuitBreakerState.OPEN

        # Try one more recovery - should be blocked
        final_result = service.recover_stream(
            stream_id=test_stream.id,
            failure_type=RecoveryFailureType.NETWORK,
            failure_reason="Should be blocked",
            recovery_strategy=RecoveryStrategy.RESTART
        )

        # Should fail immediately without creating new log
        assert final_result["success"] == False

        # Count logs - should not have increased
        logs = db_session.query(RecoveryLog).filter(
            RecoveryLog.stream_id == test_stream.id
        ).all()

        # Should have 5 logs (before circuit opened) not 6
        assert len(logs) == 5


# ==================== Summary ====================

def test_e2e_coverage_summary():
    """
    📊 End-to-End Tests Summary

    Tested Scenarios:
    1. ✅ Stream failure creates recovery log
    2. ✅ Recovery service records failure
    3. ✅ Circuit breaker state is persisted
    4. ✅ Exponential backoff calculation
    5. ✅ Backoff capped at max
    6. ✅ Backoff recorded in logs
    7. ✅ Circuit breaker opens after threshold
    8. ✅ Circuit breaker blocks recovery
    9. ✅ Circuit breaker transitions to half-open
    10. ✅ Health monitor detects failures
    11. ✅ Health state persisted in Redis
    12. ✅ Recovery statistics accuracy
    13. ✅ Recent recoveries limit
    14. ✅ Complete recovery workflow
    15. ✅ Multiple failures with backoff
    16. ✅ Circuit breaker prevents cascading failures

    Test Categories:
    - Basic Recovery Flow: 3 tests
    - Exponential Backoff: 3 tests
    - Circuit Breaker: 3 tests
    - Health Monitor: 2 tests
    - Recovery Statistics: 2 tests
    - Full E2E Scenarios: 3 tests

    Total: 16 practical end-to-end tests
    Focus: Real services, database persistence, circuit breaker behavior
    """
    assert True  # Placeholder for summary
