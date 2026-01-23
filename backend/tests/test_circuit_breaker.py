"""Unit tests for CircuitBreaker service.

Tests the Circuit Breaker pattern implementation for preventing cascading
failures in stream recovery operations.
"""

import time
import pytest

from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerState,
    CircuitBreakerConfig,
)


class TestCircuitBreakerInitialization:
    """Test CircuitBreaker initialization and default state."""

    def test_default_initialization(self):
        """Test circuit breaker initializes with default config."""
        cb = CircuitBreaker("test-circuit")

        assert cb.name == "test-circuit"
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.open_until is None

    def test_custom_config_initialization(self):
        """Test circuit breaker with custom configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=5,
            timeout=30,
            window_size=600
        )
        cb = CircuitBreaker("custom-circuit", config)

        assert cb.config.failure_threshold == 3
        assert cb.config.success_threshold == 5
        assert cb.config.timeout == 30
        assert cb.config.window_size == 600

    def test_repr(self):
        """Test string representation of circuit breaker."""
        cb = CircuitBreaker("test-circuit")
        repr_str = repr(cb)

        assert "CircuitBreaker" in repr_str
        assert "test-circuit" in repr_str
        assert "CLOSED" in repr_str


class TestAllowRequest:
    """Test allow_request() method behavior in different states."""

    def test_allow_request_when_closed(self):
        """Test requests are allowed when circuit is closed."""
        cb = CircuitBreaker("test-circuit")

        assert cb.allow_request() is True

    def test_allow_request_when_open(self):
        """Test requests are blocked when circuit is open."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=60)
        cb = CircuitBreaker("test-circuit", config)

        # Trip the circuit to OPEN state
        cb.record_failure()
        cb.record_failure()

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.allow_request() is False

    def test_allow_request_when_half_open(self):
        """Test requests are allowed when circuit is half open (testing recovery)."""
        cb = CircuitBreaker("test-circuit")

        # Manually set to HALF_OPEN for testing
        cb._transition_to(CircuitBreakerState.HALF_OPEN)

        assert cb.state == CircuitBreakerState.HALF_OPEN
        assert cb.allow_request() is True


class TestRecordFailure:
    """Test record_failure() method and state transitions."""

    def test_record_failure_increments_count(self):
        """Test recording failures increments failure count."""
        cb = CircuitBreaker("test-circuit")

        cb.record_failure()
        assert cb.failure_count == 1

        cb.record_failure()
        assert cb.failure_count == 2

    def test_failure_threshold_opens_circuit(self):
        """Test reaching failure threshold transitions to OPEN state."""
        config = CircuitBreakerConfig(failure_threshold=3, timeout=60)
        cb = CircuitBreaker("test-circuit", config)

        # Record failures up to threshold
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED

        # This failure should trip the circuit
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.open_until is not None

    def test_failure_in_half_open_reopens_circuit(self):
        """Test failure in HALF_OPEN state immediately returns to OPEN."""
        config = CircuitBreakerConfig(failure_threshold=2, success_threshold=2, timeout=10)
        cb = CircuitBreaker("test-circuit", config)

        # Trip to OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Transition to HALF_OPEN (simulate timeout)
        cb._transition_to(CircuitBreakerState.HALF_OPEN)

        # Failure in HALF_OPEN should return to OPEN
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.open_until is not None


class TestRecordSuccess:
    """Test record_success() method and state transitions."""

    def test_success_in_closed_state_resets_failures(self):
        """Test success in CLOSED state resets failure count."""
        cb = CircuitBreaker("test-circuit")

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0

    def test_success_threshold_closes_circuit(self):
        """Test reaching success threshold in HALF_OPEN closes circuit."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=3,
            timeout=60
        )
        cb = CircuitBreaker("test-circuit", config)

        # Trip circuit to OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Transition to HALF_OPEN (simulate timeout)
        cb._transition_to(CircuitBreakerState.HALF_OPEN)

        # Record successes up to threshold
        cb.record_success()
        assert cb.success_count == 1
        assert cb.state == CircuitBreakerState.HALF_OPEN

        cb.record_success()
        assert cb.success_count == 2
        assert cb.state == CircuitBreakerState.HALF_OPEN

        # This success should close the circuit
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0


class TestStateTransitions:
    """Test state machine transitions and timing."""

    def test_open_to_half_open_after_timeout(self):
        """Test circuit transitions from OPEN to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=1, success_threshold=2)
        cb = CircuitBreaker("test-circuit", config)

        # Trip circuit to OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout to expire
        time.sleep(1.1)

        # Accessing state property should trigger transition
        current_state = cb.state
        assert current_state == CircuitBreakerState.HALF_OPEN

    def test_state_auto_transition_on_property_access(self):
        """Test state property auto-transitions from OPEN to HALF_OPEN."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=1)
        cb = CircuitBreaker("test-circuit", config)

        # Trip circuit to OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(1.1)

        # Accessing state should trigger transition
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_open_until_timestamp(self):
        """Test open_until property returns correct timestamp."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=10)
        cb = CircuitBreaker("test-circuit", config)

        # Trip circuit to OPEN
        cb.record_failure()
        cb.record_failure()

        assert cb.open_until is not None
        expected_time = cb._opened_at + cb.config.timeout
        assert abs(cb.open_until - expected_time) < 0.1  # Allow small timing diff

    def test_open_until_none_when_not_open(self):
        """Test open_until is None when circuit is not OPEN."""
        cb = CircuitBreaker("test-circuit")

        assert cb.open_until is None

        cb.record_failure()
        assert cb.open_until is None  # Still CLOSED

        # Trip to OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.open_until is not None

        # Transition to CLOSED
        cb.reset()
        assert cb.open_until is None


class TestReset:
    """Test manual reset functionality."""

    def test_reset_returns_to_closed(self):
        """Test reset() returns circuit to CLOSED state."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=60)
        cb = CircuitBreaker("test-circuit", config)

        # Trip circuit to OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Reset
        cb.reset()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0
        assert cb.open_until is None

    def test_reset_from_half_open(self):
        """Test reset() from HALF_OPEN state."""
        cb = CircuitBreaker("test-circuit")

        # Manually transition to HALF_OPEN
        cb._transition_to(CircuitBreakerState.HALF_OPEN)
        cb._success_count = 2

        # Reset
        cb.reset()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
        assert cb.success_count == 0


class TestGetStateInfo:
    """Test state information retrieval for monitoring."""

    def test_get_state_info_returns_complete_info(self):
        """Test get_state_info() returns all required fields."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=60
        )
        cb = CircuitBreaker("test-circuit", config)

        info = cb.get_state_info()

        assert info["name"] == "test-circuit"
        assert info["state"] == "closed"
        assert info["failure_count"] == 0
        assert info["success_count"] == 0
        assert info["failure_threshold"] == 3
        assert info["success_threshold"] == 2
        assert "last_failure_time" in info
        assert "last_state_change" in info
        assert "open_until" in info
        assert "time_until_half_open" in info

    def test_get_state_info_after_failures(self):
        """Test state info reflects recorded failures."""
        config = CircuitBreakerConfig(failure_threshold=3, timeout=60)
        cb = CircuitBreaker("test-circuit", config)

        cb.record_failure()
        cb.record_failure()

        info = cb.get_state_info()

        assert info["failure_count"] == 2
        assert info["state"] == "closed"
        assert info["last_failure_time"] is not None

    def test_get_state_info_when_open(self):
        """Test state info when circuit is OPEN."""
        config = CircuitBreakerConfig(failure_threshold=2, timeout=60)
        cb = CircuitBreaker("test-circuit", config)

        cb.record_failure()
        cb.record_failure()

        info = cb.get_state_info()

        assert info["state"] == "open"
        assert info["open_until"] is not None
        assert info["time_until_half_open"] > 0


class TestCustomConfigurations:
    """Test circuit breaker with various custom configurations."""

    def test_low_failure_threshold(self):
        """Test circuit breaker with low failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout=60)
        cb = CircuitBreaker("sensitive-circuit", config)

        cb.record_failure()

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.allow_request() is False

    def test_high_failure_threshold(self):
        """Test circuit breaker with high failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=10, timeout=60)
        cb = CircuitBreaker("tolerant-circuit", config)

        for _ in range(5):
            cb.record_failure()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 5

    def test_low_success_threshold(self):
        """Test circuit closes quickly with low success threshold."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=1,
            timeout=60
        )
        cb = CircuitBreaker("test-circuit", config)

        # Trip to OPEN
        cb.record_failure()
        cb.record_failure()

        # Transition to HALF_OPEN
        cb._transition_to(CircuitBreakerState.HALF_OPEN)

        # Single success should close
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_high_success_threshold(self):
        """Test circuit requires multiple successes to close."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            success_threshold=5,
            timeout=60
        )
        cb = CircuitBreaker("test-circuit", config)

        # Trip to OPEN then HALF_OPEN
        cb.record_failure()
        cb.record_failure()
        cb._transition_to(CircuitBreakerState.HALF_OPEN)

        # Record 4 successes (should stay HALF_OPEN)
        for _ in range(4):
            cb.record_success()
        assert cb.state == CircuitBreakerState.HALF_OPEN
        assert cb.success_count == 4

        # 5th success closes circuit
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiple_circuits_independent(self):
        """Test multiple circuit breakers maintain independent state."""
        cb1 = CircuitBreaker("circuit-1")
        cb2 = CircuitBreaker("circuit-2")

        # Trip first circuit
        cb1.record_failure()
        cb1.record_failure()
        cb1.record_failure()

        # Second circuit should remain closed
        assert cb1.state == CircuitBreakerState.OPEN
        assert cb2.state == CircuitBreakerState.CLOSED

    def test_success_does_not_affect_closed_circuit(self):
        """Test recording success in CLOSED state doesn't cause issues."""
        cb = CircuitBreaker("test-circuit")

        # Record multiple successes without any failures
        cb.record_success()
        cb.record_success()
        cb.record_success()

        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_transition_preserves_last_state_change(self):
        """Test last_state_change is updated on transitions."""
        cb = CircuitBreaker("test-circuit")
        initial_change = cb._last_state_change

        time.sleep(0.1)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()  # Trip to OPEN

        assert cb._last_state_change > initial_change

    def test_failure_count_not_reset_on_open_to_half_open(self):
        """Test failure count persists through OPEN->HALF_OPEN transition."""
        config = CircuitBreakerConfig(failure_threshold=3, timeout=1, success_threshold=2)
        cb = CircuitBreaker("test-circuit", config)

        # Trip to OPEN with 3 failures
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 3

        # Wait for timeout and transition to HALF_OPEN
        time.sleep(1.1)
        _ = cb.state  # Trigger transition

        assert cb.state == CircuitBreakerState.HALF_OPEN
        assert cb.failure_count == 3  # Should still be 3

        # Success should reset
        cb.record_success()
        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0


class TestReprAndStringMethods:
    """Test string representation methods."""

    def test_repr_includes_all_key_info(self):
        """Test __repr__ includes name, state, and counts."""
        cb = CircuitBreaker("test-circuit")

        cb.record_failure()
        cb.record_failure()

        repr_str = repr(cb)
        assert "test-circuit" in repr_str
        assert "CLOSED" in repr_str
        assert "2" in repr_str  # failure count
