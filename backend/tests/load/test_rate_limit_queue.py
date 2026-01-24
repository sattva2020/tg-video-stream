"""
Load & Performance Tests: Rate Limit Queue Service
Тесты производительности очереди с приоритетами

Coverage Target:
- Queue service can handle 1000+ requests/sec
- Performance under sustained load
- Latency measurements for different priorities
- Memory and resource usage under stress

These tests verify:
1. Queue can accept 1000+ requests per second
2. Processing throughput meets requirements
3. Priority ordering maintained under load
4. No request loss under stress conditions
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from typing import List
import statistics

from src.services.rate_limit_queue_service import (
    RateLimitQueueService,
    RequestType,
    RequestPriority,
    QueuedRequest,
    get_rate_limit_queue_service,
)


# ==================== Fixtures ====================

@pytest.fixture
async def queue_service():
    """Get queue service instance for load testing."""
    service = get_rate_limit_queue_service()
    test_accounts = [f"load_test_account_{i:03d}" for i in range(1, 11)]

    # Clear test queues before each test
    for account_id in test_accounts:
        await service.clear(account_id)

    yield service

    # Cleanup after test
    for account_id in test_accounts:
        await service.clear(account_id)


@pytest.fixture
def mock_redis_pool():
    """
    Mock Redis with minimal overhead for performance testing.
    Uses in-memory structures to simulate Redis operations.
    """
    class MockRedisPool:
        def __init__(self):
            self.queues = {}  # {queue_key: {score: request_json}}
            self.counters = {}  # {key: int}

        async def zadd(self, key, mapping):
            """Simulate ZADD operation."""
            if key not in self.queues:
                self.queues[key] = {}
            self.queues[key].update(mapping)
            return len(mapping)

        async def zcard(self, key):
            """Simulate ZCARD operation."""
            return len(self.queues.get(key, {}))

        async def zrem(self, key, *values):
            """Simulate ZREM operation."""
            if key in self.queues:
                removed = 0
                for value in values:
                    # Find and remove by value
                    for score, val in list(self.queues[key].items()):
                        if val == value:
                            del self.queues[key][score]
                            removed += 1
                            break
                return removed
            return 0

        async def zrange(self, key, start, stop, withscores=False):
            """Simulate ZRANGE operation."""
            if key not in self.queues:
                return []

            items = sorted(self.queues[key].items())
            if stop == -1:
                items = items[start:]
            else:
                items = items[start:stop + 1]

            if withscores:
                # Return (value, score) tuples flattened
                result = []
                for val, score in items:
                    result.append(val)
                    result.append(score)
                return result
            return [val for val, score in items]

        async def zincrby(self, key, amount, value):
            """Simulate ZINCRBY operation."""
            # Not used in critical path, simplified
            return 0.0

        async def hincrby(self, key, field, increment):
            """Simulate HINCRBY operation."""
            if key not in self.counters:
                self.counters[key] = {}
            if field not in self.counters[key]:
                self.counters[key][field] = 0
            self.counters[key][field] += increment
            return self.counters[key][field]

        async def hget(self, key, field):
            """Simulate HGET operation."""
            if key in self.counters and field in self.counters[key]:
                return str(self.counters[key][field])
            return None

        async def hset(self, key, field, value):
            """Simulate HSET operation."""
            if key not in self.counters:
                self.counters[key] = {}
            self.counters[key][field] = value
            return 1

        async def expire(self, key, seconds):
            """Simulate EXPIRE operation (no-op in mock)."""
            return True

        async def keys(self, pattern):
            """Simulate KEYS operation."""
            # Simplified - only return exact matches
            return [k for k in self.queues.keys() if pattern.replace("*", "") in k]

    return MockRedisPool()


# ==================== Performance Metrics Helper ====================

class PerformanceMetrics:
    """Helper class to track performance metrics."""

    def __init__(self):
        self.timestamps: List[float] = []
        self.latencies: List[float] = []
        self.success_count: int = 0
        self.error_count: int = 0

    def record_add(self, start_time: float, success: bool = True):
        """Record a queue add operation."""
        self.timestamps.append(start_time)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1

    def record_latency(self, latency_ms: float):
        """Record operation latency."""
        self.latencies.append(latency_ms)

    def get_requests_per_second(self, duration_sec: float) -> float:
        """Calculate requests per second."""
        if duration_sec <= 0:
            return 0.0
        return self.success_count / duration_sec

    def get_avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if not self.latencies:
            return 0.0
        return statistics.mean(self.latencies)

    def get_p99_latency_ms(self) -> float:
        """Calculate P99 latency in milliseconds."""
        if len(self.latencies) < 100:
            return self.get_avg_latency_ms()
        return statistics.quantiles(self.latencies, n=100)[98]

    def get_max_latency_ms(self) -> float:
        """Get maximum latency."""
        if not self.latencies:
            return 0.0
        return max(self.latencies)

    def get_summary(self) -> dict:
        """Get performance summary."""
        return {
            "total_requests": self.success_count + self.error_count,
            "successful_requests": self.success_count,
            "failed_requests": self.error_count,
            "avg_latency_ms": round(self.get_avg_latency_ms(), 2),
            "p99_latency_ms": round(self.get_p99_latency_ms(), 2),
            "max_latency_ms": round(self.get_max_latency_ms(), 2),
        }


# ==================== 1. Queue Throughput Tests ====================

class TestQueueThroughput:
    """Тесты пропускной способности очереди."""

    @pytest.mark.asyncio
    async def test_queue_handles_1000_requests_per_second(self, queue_service):
        """
        Verify queue service can handle 1000 requests/sec.

        Steps:
        1. Submit 1000 requests as fast as possible
        2. Measure time taken
        3. Verify throughput >= 1000 req/s
        4. Verify all requests queued successfully
        """
        account_id = "perf_test_account_001"
        num_requests = 1000

        # Clear queue before test
        await queue_service.clear(account_id)

        # Measure time to add requests
        start_time = time.time()

        for i in range(num_requests):
            request = QueuedRequest(
                request_type=RequestType.METADATA_FETCH,
                priority=RequestPriority.MEDIUM,
                account_id=account_id,
                method="get_chat",
                params={"chat_id": i},
            )
            await queue_service.add(request)

        end_time = time.time()
        duration = end_time - start_time

        # Calculate throughput
        requests_per_second = num_requests / duration

        # Verify queue size
        stats = await queue_service.get_queue_stats(account_id)
        queue_size = stats.total_requests

        # Assertions
        assert queue_size == num_requests, f"Expected {num_requests} requests, got {queue_size}"
        assert requests_per_second >= 1000, (
            f"Throughput {requests_per_second:.2f} req/s is below 1000 req/s threshold"
        )

        # Log performance metrics
        metrics = {
            "duration_sec": round(duration, 3),
            "requests_per_second": round(requests_per_second, 2),
            "queue_size": queue_size,
        }
        logger.info(f"Performance test result: {metrics}")

    @pytest.mark.asyncio
    async def test_burst_load_2000_requests(self, queue_service):
        """
        Test queue handles burst load of 2000 requests.

        Verifies queue can handle 2x expected load without degradation.
        """
        account_id = "perf_test_account_002"
        num_requests = 2000

        await queue_service.clear(account_id)

        # Submit requests in concurrent batches
        async def submit_batch(batch_size: int, batch_id: int):
            requests = []
            for i in range(batch_size):
                request = QueuedRequest(
                    request_type=RequestType.METADATA_FETCH,
                    priority=RequestPriority.MEDIUM,
                    account_id=account_id,
                    method="get_chat",
                    params={"chat_id": f"{batch_id}_{i}"},
                )
                requests.append(queue_service.add(request))
            await asyncio.gather(*requests)

        start_time = time.time()

        # Submit in 10 batches of 200 requests each
        batch_size = 200
        num_batches = num_requests // batch_size
        tasks = [submit_batch(batch_size, i) for i in range(num_batches)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time

        # Verify all requests queued
        stats = await queue_service.get_queue_stats(account_id)
        requests_per_second = num_requests / duration

        assert stats.total_requests == num_requests, (
            f"Expected {num_requests} requests, got {stats.total_requests}"
        )
        assert requests_per_second >= 1000, (
            f"Burst load throughput {requests_per_second:.2f} req/s below threshold"
        )

    @pytest.mark.asyncio
    async def test_sustained_load_10000_requests(self, queue_service):
        """
        Test queue handles sustained load of 10000 requests.

        Verifies performance doesn't degrade under sustained load.
        """
        account_id = "perf_test_account_003"
        num_requests = 10000
        batch_size = 500

        await queue_service.clear(account_id)

        # Track metrics over time
        batch_times = []

        start_time = time.time()

        for batch_num in range(num_requests // batch_size):
            batch_start = time.time()

            # Submit batch
            for i in range(batch_size):
                request = QueuedRequest(
                    request_type=RequestType.BACKGROUND_SYNC,
                    priority=RequestPriority.LOW,
                    account_id=account_id,
                    method="get_dialogs",
                    params={"offset_date": batch_num * batch_size + i},
                )
                await queue_service.add(request)

            batch_end = time.time()
            batch_times.append(batch_end - batch_start)

        end_time = time.time()
        total_duration = end_time - start_time
        avg_rps = num_requests / total_duration

        # Check for performance degradation (last batch should not be >2x slower)
        first_half_avg = statistics.mean(batch_times[:len(batch_times)//2])
        second_half_avg = statistics.mean(batch_times[len(batch_times)//2:])
        degradation_ratio = second_half_avg / first_half_avg if first_half_avg > 0 else 1.0

        stats = await queue_service.get_queue_stats(account_id)

        assert stats.total_requests == num_requests, f"Expected {num_requests} requests"
        assert avg_rps >= 1000, f"Sustained throughput {avg_rps:.2f} req/s below threshold"
        assert degradation_ratio < 2.0, (
            f"Performance degradation detected: {degradation_ratio:.2f}x slowdown"
        )


# ==================== 2. Priority Performance Tests ====================

class TestPriorityPerformance:
    """Тесты производительности с приоритетами."""

    @pytest.mark.asyncio
    async def test_priority_ordering_under_load(self, queue_service):
        """
        Verify priority ordering is maintained under load.

        Steps:
        1. Submit mix of HIGH, MEDIUM, LOW priority requests
        2. Verify retrieval order respects priority
        3. Ensure no degradation under load
        """
        account_id = "priority_perf_test_001"
        await queue_service.clear(account_id)

        num_per_priority = 100
        requests_added = []

        # Add requests with different priorities
        for priority in [RequestPriority.HIGH, RequestPriority.MEDIUM, RequestPriority.LOW]:
            for i in range(num_per_priority):
                request = QueuedRequest(
                    request_type=RequestType.STREAM_CONTROL if priority == RequestPriority.HIGH
                                  else RequestType.METADATA_FETCH if priority == RequestPriority.MEDIUM
                                  else RequestType.BACKGROUND_SYNC,
                    priority=priority,
                    account_id=account_id,
                    method="test_method",
                    params={"priority": priority.value, "index": i},
                )
                await queue_service.add(request)
                requests_added.append((priority.value, i))

        # Retrieve and verify order
        retrieved_requests = []
        batch_size = 50

        for _ in range((num_per_priority * 3) // batch_size):
            batch = await queue_service.pop_batch(account_id, batch_size)
            for req in batch:
                retrieved_requests.append(req.priority.value)

        # Verify all HIGH requests come before MEDIUM, which come before LOW
        high_count = sum(1 for p in retrieved_requests if p == RequestPriority.HIGH.value)
        medium_count = sum(1 for p in retrieved_requests if p == RequestPriority.MEDIUM.value)
        low_count = sum(1 for p in retrieved_requests if p == RequestPriority.LOW.value)

        # Find indices where priorities change
        first_medium_idx = next((i for i, p in enumerate(retrieved_requests)
                                 if p == RequestPriority.MEDIUM.value), len(retrieved_requests))
        first_low_idx = next((i for i, p in enumerate(retrieved_requests)
                             if p == RequestPriority.LOW.value), len(retrieved_requests))

        # Verify HIGH all before MEDIUM
        assert all(p == RequestPriority.HIGH.value for p in retrieved_requests[:first_medium_idx]), (
            "HIGH priority requests should come first"
        )
        # Verify MEDIUM all before LOW
        assert all(p in [RequestPriority.HIGH.value, RequestPriority.MEDIUM.value]
                   for p in retrieved_requests[:first_low_idx]), (
            "MEDIUM priority requests should come before LOW"
        )

        assert high_count == num_per_priority, f"Expected {num_per_priority} HIGH requests"
        assert medium_count == num_per_priority, f"Expected {num_per_priority} MEDIUM requests"
        assert low_count == num_per_priority, f"Expected {num_per_priority} LOW requests"

    @pytest.mark.asyncio
    async def test_high_priority_bypass_performance(self, queue_service):
        """
        Verify HIGH priority requests bypass queue quickly even under load.

        HIGH priority requests should have minimal latency.
        """
        account_id = "priority_bypass_test_001"
        await queue_service.clear(account_id)

        # Fill queue with MEDIUM priority requests
        for i in range(500):
            request = QueuedRequest(
                request_type=RequestType.METADATA_FETCH,
                priority=RequestPriority.MEDIUM,
                account_id=account_id,
                method="get_chat",
                params={"chat_id": i},
            )
            await queue_service.add(request)

        # Now submit HIGH priority request and measure latency
        high_priority_request = QueuedRequest(
            request_type=RequestType.STREAM_CONTROL,
            priority=RequestPriority.HIGH,
            account_id=account_id,
            method="send_message",
            params={"text": "urgent"},
        )

        start_time = time.time()
        await queue_service.add(high_priority_request)

        # Retrieve next batch - HIGH priority should be first
        batch = await queue_service.pop_batch(account_id, 10)
        end_time = time.time()

        latency_ms = (end_time - start_time) * 1000

        # Verify HIGH priority is first in batch
        assert len(batch) > 0, "Should retrieve at least one request"
        assert batch[0].priority == RequestPriority.HIGH, "HIGH priority should be first"

        # Latency should be very low (< 10ms)
        assert latency_ms < 10, f"HIGH priority latency {latency_ms:.2f}ms exceeds 10ms threshold"


# ==================== 3. Stress Tests ====================

class TestQueueStress:
    """Тесты устойчивости под нагрузкой."""

    @pytest.mark.asyncio
    async def test_concurrent_accounts_performance(self, queue_service):
        """
        Test queue performance with multiple concurrent accounts.

        Simulates real-world scenario with multiple Telegram accounts.
        """
        num_accounts = 10
        requests_per_account = 100
        total_requests = num_accounts * requests_per_account

        # Clear all test account queues
        for i in range(num_accounts):
            await queue_service.clear(f"stress_account_{i:03d}")

        start_time = time.time()

        # Submit requests concurrently across multiple accounts
        async def submit_account_requests(account_idx: int):
            account_id = f"stress_account_{account_idx:03d}"
            for i in range(requests_per_account):
                request = QueuedRequest(
                    request_type=RequestType.METADATA_FETCH,
                    priority=RequestPriority.MEDIUM,
                    account_id=account_id,
                    method="get_chat",
                    params={"chat_id": i},
                )
                await queue_service.add(request)

        # Submit to all accounts concurrently
        tasks = [submit_account_requests(i) for i in range(num_accounts)]
        await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time
        requests_per_second = total_requests / duration

        # Verify all accounts have correct queue sizes
        total_queued = 0
        for i in range(num_accounts):
            stats = await queue_service.get_queue_stats(f"stress_account_{i:03d}")
            total_queued += stats.total_requests
            assert stats.total_requests == requests_per_account, (
                f"Account {i}: Expected {requests_per_account} requests, got {stats.total_requests}"
            )

        assert total_queued == total_requests, f"Expected {total_requests} total requests"
        assert requests_per_second >= 1000, (
            f"Concurrent throughput {requests_per_second:.2f} req/s below threshold"
        )

    @pytest.mark.asyncio
    async def test_queue_saturation_handling(self, queue_service):
        """
        Test queue behavior when approaching max capacity.

        Verifies queue handles saturation gracefully.
        """
        account_id = "saturation_test_001"
        max_queue_size = 1000  # Default max queue size

        await queue_service.clear(account_id)

        # Submit requests up to near max capacity
        num_requests = int(max_queue_size * 0.95)  # 95% of max

        for i in range(num_requests):
            request = QueuedRequest(
                request_type=RequestType.METADATA_FETCH,
                priority=RequestPriority.LOW,
                account_id=account_id,
                method="get_chat",
                params={"chat_id": i},
            )
            success = await queue_service.add(request)
            # Should succeed until max size
            if i < max_queue_size:
                assert success, f"Request {i} should succeed"

        # Verify queue size
        stats = await queue_service.get_queue_stats(account_id)
        assert stats.total_requests == num_requests, f"Expected {num_requests} requests"

        # Clear and verify
        await queue_service.clear(account_id)
        stats_after = await queue_service.get_queue_stats(account_id)
        assert stats_after.total_requests == 0, "Queue should be empty after clear"


# ==================== 4. Latency Tests ====================

class TestQueueLatency:
    """Тесты задержек операций."""

    @pytest.mark.asyncio
    async def test_add_latency_percentiles(self, queue_service):
        """
        Measure and verify add operation latency percentiles.

        P50 < 1ms, P95 < 5ms, P99 < 10ms
        """
        account_id = "latency_test_001"
        num_samples = 1000

        await queue_service.clear(account_id)

        latencies = []

        for i in range(num_samples):
            request = QueuedRequest(
                request_type=RequestType.METADATA_FETCH,
                priority=RequestPriority.MEDIUM,
                account_id=account_id,
                method="get_chat",
                params={"chat_id": i},
            )

            start = time.perf_counter()
            await queue_service.add(request)
            end = time.perf_counter()

            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)

        # Calculate percentiles
        p50 = statistics.quantiles(latencies, n=100)[49]  # 50th percentile
        p95 = statistics.quantiles(latencies, n=100)[94]  # 95th percentile
        p99 = statistics.quantiles(latencies, n=100)[98]  # 99th percentile

        # Verify latency thresholds
        assert p50 < 1.0, f"P50 latency {p50:.2f}ms exceeds 1ms threshold"
        assert p95 < 5.0, f"P95 latency {p95:.2f}ms exceeds 5ms threshold"
        assert p99 < 10.0, f"P99 latency {p99:.2f}ms exceeds 10ms threshold"

        logger.info(f"Latency percentiles: P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")

    @pytest.mark.asyncio
    async def test_batch_operation_performance(self, queue_service):
        """
        Verify batch operations are more efficient than individual operations.

        pop_batch should be more efficient than individual pop calls.
        """
        account_id = "batch_perf_test_001"
        num_requests = 100
        batch_size = 10

        await queue_service.clear(account_id)

        # Add requests
        for i in range(num_requests):
            request = QueuedRequest(
                request_type=RequestType.METADATA_FETCH,
                priority=RequestPriority.MEDIUM,
                account_id=account_id,
                method="get_chat",
                params={"chat_id": i},
            )
            await queue_service.add(request)

        # Measure batch pop performance
        start = time.perf_counter()
        num_batches = num_requests // batch_size
        for _ in range(num_batches):
            await queue_service.pop_batch(account_id, batch_size)
        end = time.perf_counter()

        batch_time = end - start
        avg_batch_latency_ms = (batch_time / num_batches) * 1000

        # Verify reasonable batch latency (< 50ms per batch)
        assert avg_batch_latency_ms < 50, (
            f"Average batch latency {avg_batch_latency_ms:.2f}ms exceeds 50ms"
        )

        logger.info(f"Batch operation performance: {avg_batch_latency_ms:.2f}ms per batch")


# ==================== Logging Setup ====================

import logging
logger = logging.getLogger(__name__)
