"""Circuit Breaker Service.

Implements the Circuit Breaker pattern for preventing cascading failures
in stream recovery operations.

**Purpose**: Automatically detect and prevent repeated failures
**Layer**: Service (domain logic)
**States**: CLOSED (normal), OPEN (failing), HALF_OPEN (testing)
"""

import enum
import logging
import time
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class CircuitBreakerState(str, enum.Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Failing, requests are blocked
    HALF_OPEN = "half_open" # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5        # Failures before opening
    success_threshold: int = 2        # Successes to close after half-open
    timeout: int = 60                 # Seconds before trying half-open
    window_size: int = 300            # Seconds to consider failures


class CircuitBreaker:
    """Circuit Breaker implementation for stream recovery.

    **State Machine**:
    - CLOSED -> OPEN: When failure threshold is reached
    - OPEN -> HALF_OPEN: After timeout expires
    - HALF_OPEN -> CLOSED: When success threshold is reached
    - HALF_OPEN -> OPEN: On any failure

    **Usage**:
        cb = CircuitBreaker("stream-123")
        if cb.allow_request():
            try:
                # Attempt operation
                cb.record_success()
            except Exception:
                cb.record_failure()
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize circuit breaker.

        Args:
            name: Unique identifier for this circuit breaker
            config: Optional custom configuration
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()

        # State tracking
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_state_change: float = time.time()
        self._opened_at: Optional[float] = None

        logger.info(
            f"CircuitBreaker '{name}' initialized with state={self._state}, "
            f"failure_threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout}s"
        )

    @property
    def state(self) -> CircuitBreakerState:
        """Get current state."""
        # Auto-transition from OPEN to HALF_OPEN if timeout has passed
        if self._state == CircuitBreakerState.OPEN:
            if self._opened_at and (time.time() - self._opened_at) >= self.config.timeout:
                self._transition_to(CircuitBreakerState.HALF_OPEN)
                logger.info(
                    f"CircuitBreaker '{self.name}' transitioned "
                    f"OPEN -> HALF_OPEN (timeout expired)"
                )

        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    @property
    def success_count(self) -> int:
        """Get current success count."""
        return self._success_count

    @property
    def open_until(self) -> Optional[float]:
        """Get timestamp when circuit will transition to HALF_OPEN."""
        if self._state == CircuitBreakerState.OPEN and self._opened_at:
            return self._opened_at + self.config.timeout
        return None

    def allow_request(self) -> bool:
        """Check if request should be allowed through circuit.

        Returns:
            True if request is allowed, False if circuit is open
        """
        current_state = self.state

        if current_state == CircuitBreakerState.CLOSED:
            return True

        if current_state == CircuitBreakerState.OPEN:
            logger.debug(
                f"CircuitBreaker '{self.name}' is OPEN, "
                f"request blocked (will try again at {self.open_until})"
            )
            return False

        # HALF_OPEN state - allow limited requests for testing
        return True

    def record_success(self):
        """Record a successful operation.

        May trigger state transition:
        - HALF_OPEN -> CLOSED: When success threshold is reached
        """
        current_state = self.state

        if current_state == CircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            logger.debug(
                f"CircuitBreaker '{self.name}' recorded success "
                f"({self._success_count}/{self.config.success_threshold} in HALF_OPEN)"
            )

            if self._success_count >= self.config.success_threshold:
                self._transition_to(CircuitBreakerState.CLOSED)
                logger.info(
                    f"CircuitBreaker '{self.name}' transitioned "
                    f"HALF_OPEN -> CLOSED (success threshold reached)"
                )
        elif current_state == CircuitBreakerState.CLOSED:
            # Reset failure count on successful operation in CLOSED state
            self._failure_count = 0
            logger.debug(f"CircuitBreaker '{self.name}' reset failure count in CLOSED state")

    def record_failure(self):
        """Record a failed operation.

        May trigger state transitions:
        - CLOSED -> OPEN: When failure threshold is reached
        - HALF_OPEN -> OPEN: Immediately on any failure
        """
        current_state = self.state

        self._failure_count += 1
        self._last_failure_time = time.time()

        if current_state == CircuitBreakerState.CLOSED:
            logger.debug(
                f"CircuitBreaker '{self.name}' recorded failure "
                f"({self._failure_count}/{self.config.failure_threshold})"
            )

            if self._failure_count >= self.config.failure_threshold:
                self._transition_to(CircuitBreakerState.OPEN)
                logger.warning(
                    f"CircuitBreaker '{self.name}' transitioned "
                    f"CLOSED -> OPEN (failure threshold reached: "
                    f"{self._failure_count} failures)"
                )

        elif current_state == CircuitBreakerState.HALF_OPEN:
            self._transition_to(CircuitBreakerState.OPEN)
            logger.warning(
                f"CircuitBreaker '{self.name}' transitioned "
                f"HALF_OPEN -> OPEN (failed during testing)"
            )

    def reset(self):
        """Manually reset circuit breaker to CLOSED state.

        Useful for manual intervention or after known fixes.
        """
        self._transition_to(CircuitBreakerState.CLOSED)
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._opened_at = None
        logger.info(f"CircuitBreaker '{self.name}' manually reset to CLOSED")

    def _transition_to(self, new_state: CircuitBreakerState):
        """Internal method to transition to a new state.

        Args:
            new_state: Target state
        """
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()

        if new_state == CircuitBreakerState.OPEN:
            self._opened_at = time.time()
            self._success_count = 0
        elif new_state == CircuitBreakerState.HALF_OPEN:
            self._success_count = 0
        elif new_state == CircuitBreakerState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            self._opened_at = None

        logger.debug(
            f"CircuitBreaker '{self.name}' state transition: "
            f"{old_state} -> {new_state}"
        )

    def __repr__(self) -> str:
        return (
            f"<CircuitBreaker(name={self.name}, state={self.state}, "
            f"failures={self._failure_count}, successes={self._success_count})>"
        )

    def get_state_info(self) -> dict:
        """Get detailed state information for monitoring.

        Returns:
            Dictionary with current circuit breaker state
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.config.failure_threshold,
            "success_threshold": self.config.success_threshold,
            "last_failure_time": self._last_failure_time,
            "last_state_change": self._last_state_change,
            "open_until": self.open_until,
            "time_until_half_open": (
                max(0, self.open_until - time.time()) if self.open_until else 0
            ),
        }
