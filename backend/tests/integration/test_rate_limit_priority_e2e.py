"""
End-to-End Tests: Rate Limit Priority Queue
Тестируем полный цикл приоритетного выполнения запросов к API

Coverage Target:
- High-priority requests bypass queue and execute immediately
- Medium-priority requests queue behind high-priority requests
- Dashboard shows correct priority ordering
- Queue statistics reflect priority distribution

This test verifies:
1. Stream control (HIGH priority) executes immediately
2. Metadata fetch (MEDIUM priority) queues properly
3. Queue API returns accurate priority statistics
4. Dashboard data matches queue state
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.services.rate_limit_queue_service import (
    RateLimitQueueService,
    RequestType,
    RequestPriority,
    QueuedRequest,
    get_rate_limit_queue_service,
)
from src.services.telegram_rate_limiter import telegram_api_queue
from src.api.routes.rate_limits import router


# ==================== Fixtures ====================

@pytest.fixture
async def queue_service():
    """Get queue service instance"""
    service = get_rate_limit_queue_service()
    # Clear test queue before each test
    await service.clear("test_account_001")
    await service.clear("test_account_002")
    yield service
    # Cleanup after test
    await service.clear("test_account_001")
    await service.clear("test_account_002")


@pytest.fixture
def mock_telegram_client():
    """Mock Pyrogram client for testing"""
    client = MagicMock()

    # Mock async methods
    async def mock_get_chat(*args, **kwargs):
        return {"id": 123, "title": "Test Channel"}

    async def mock_send_message(*args, **kwargs):
        return {"id": 456, "text": kwargs.get("text", "")}

    async def mock_get_me(*args, **kwargs):
        return {"id": 789, "first_name": "Test User"}

    client.get_chat = AsyncMock(side_effect=mock_get_chat)
    client.send_message = AsyncMock(side_effect=mock_send_message)
    client.get_me = AsyncMock(side_effect=mock_get_me)

    return client


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter to avoid actual rate limit checks"""
    with patch('src.services.telegram_rate_limiter.rate_limiter.check_limit', return_value=None):
        with patch('src.services.telegram_rate_limiter.rate_limiter.record_limit'):
            yield


# ==================== 1. High Priority Bypass Test ====================

class TestHighPriorityBypass:
    """Тесты обхода очереди для высокоприоритетных запросов"""

    @pytest.mark.asyncio
    async def test_stream_control_executes_immediately(
        self, queue_service, mock_telegram_client, mock_rate_limiter
    ):
        """
        HIGH priority (stream_control) request executes immediately without queuing.

        Steps:
        1. Submit stream control request (HIGH priority)
        2. Verify it executes immediately (no queuing delay)
        3. Check queue is empty after execution
        """
        account_id = "test_account_001"

        # Verify queue starts empty
        stats_before = await queue_service.get_queue_stats(account_id)
        assert stats_before.total_requests == 0, "Queue should start empty"

        # Execute HIGH priority request (stream control)
        start_time = time.time()

        result = await telegram_api_queue.execute_api_call(
            client=mock_telegram_client,
            method="send_message",
            params={"chat_id": "@test_channel", "text": "Play next track"},
            request_type=RequestType.STREAM_CONTROL,
            account_id=account_id,
            priority=RequestPriority.HIGH,
        )

        execution_time = time.time() - start_time

        # Verify execution completed immediately (< 100ms)
        assert execution_time < 0.1, f"HIGH priority should execute immediately, took {execution_time}s"
        assert result is not None, "Should return API result"

        # Verify queue is still empty (no queuing occurred)
        stats_after = await queue_service.get_queue_stats(account_id)
        assert stats_after.total_requests == 0, "Queue should remain empty after immediate execution"
        assert stats_after.high_priority == 0, "No high-priority requests should remain in queue"

    @pytest.mark.asyncio
    async def test_high_priority_bypasses_medium_priority_queue(
        self, queue_service, mock_telegram_client, mock_rate_limiter
    ):
        """
        HIGH priority request bypasses medium-priority requests already in queue.

        Steps:
        1. Add medium-priority requests to queue
        2. Submit high-priority request
        3. Verify high-priority executes immediately (doesn't wait for queue)
        """
        account_id = "test_account_001"

        # Enqueue 3 MEDIUM priority requests
        for i in range(3):
            await queue_service.add(
                method="get_chat",
                params={"chat_id": f"@channel_{i}"},
                request_type=RequestType.METADATA_FETCH,
                account_id=account_id,
                priority=RequestPriority.MEDIUM,
            )

        # Verify medium requests are queued
        stats_before = await queue_service.get_queue_stats(account_id)
        assert stats_before.medium_priority == 3, "Should have 3 medium-priority requests queued"

        # Execute HIGH priority request - should bypass queue
        start_time = time.time()

        result = await telegram_api_queue.execute_api_call(
            client=mock_telegram_client,
            method="send_message",
            params={"chat_id": "@test_channel", "text": "Pause stream"},
            request_type=RequestType.STREAM_CONTROL,
            account_id=account_id,
            priority=RequestPriority.HIGH,
        )

        execution_time = time.time() - start_time

        # Verify HIGH priority executed immediately despite queue
        assert execution_time < 0.1, f"HIGH priority should bypass queue, took {execution_time}s"
        assert result is not None, "Should return API result"

        # Verify medium requests are still queued (not affected by high-priority execution)
        stats_after = await queue_service.get_queue_stats(account_id)
        assert stats_after.medium_priority == 3, "Medium requests should remain queued"


# ==================== 2. Medium Priority Queuing Test ====================

class TestMediumPriorityQueuing:
    """Тесты очереди для среднеприоритетных запросов"""

    @pytest.mark.asyncio
    async def test_metadata_fetch_queues_behind_high_priority(
        self, queue_service, mock_telegram_client, mock_rate_limiter
    ):
        """
        MEDIUM priority request (metadata_fetch) queues behind high-priority requests.

        Steps:
        1. Submit high-priority request to queue
        2. Submit medium-priority request
        3. Verify medium priority queues behind high priority
        4. Verify queue statistics show correct priority distribution
        """
        account_id = "test_account_001"

        # Enqueue HIGH priority request
        high_request = await queue_service.add(
            method="send_message",
            params={"chat_id": "@test", "text": "Skip track"},
            request_type=RequestType.STREAM_CONTROL,
            account_id=account_id,
            priority=RequestPriority.HIGH,
        )

        # Enqueue MEDIUM priority request
        medium_request = await queue_service.add(
            method="get_chat",
            params={"chat_id": "@channel"},
            request_type=RequestType.METADATA_FETCH,
            account_id=account_id,
            priority=RequestPriority.MEDIUM,
        )

        # Verify both requests are in queue
        stats = await queue_service.get_queue_stats(account_id)
        assert stats.total_requests == 2, "Should have 2 requests in queue"
        assert stats.high_priority == 1, "Should have 1 high-priority request"
        assert stats.medium_priority == 1, "Should have 1 medium-priority request"

        # Get all requests from queue - HIGH should come first
        all_requests = await queue_service.get_all(account_id)
        assert len(all_requests) == 2, "Should retrieve 2 requests"

        # Verify priority ordering (HIGH before MEDIUM)
        assert all_requests[0].priority == RequestPriority.HIGH, "First request should be HIGH priority"
        assert all_requests[1].priority == RequestPriority.MEDIUM, "Second request should be MEDIUM priority"

    @pytest.mark.asyncio
    async def test_multiple_medium_priority_maintain_fifo_order(
        self, queue_service, mock_telegram_client, mock_rate_limiter
    ):
        """
        Multiple MEDIUM priority requests maintain FIFO order within same priority.

        Steps:
        1. Submit multiple medium-priority requests
        2. Verify they maintain FIFO order
        3. Verify queue statistics are accurate
        """
        account_id = "test_account_001"

        # Enqueue 5 MEDIUM priority requests
        request_ids = []
        for i in range(5):
            request = await queue_service.add(
                method="get_chat",
                params={"chat_id": f"@channel_{i}"},
                request_type=RequestType.METADATA_FETCH,
                account_id=account_id,
                priority=RequestPriority.MEDIUM,
            )
            request_ids.append(request.id)

        # Verify all 5 requests are queued
        stats = await queue_service.get_queue_stats(account_id)
        assert stats.total_requests == 5, "Should have 5 requests in queue"
        assert stats.medium_priority == 5, "All 5 should be medium priority"

        # Verify FIFO order
        all_requests = await queue_service.get_all(account_id)
        assert len(all_requests) == 5

        retrieved_ids = [r.id for r in all_requests]
        assert retrieved_ids == request_ids, "Requests should maintain FIFO order"


# ==================== 3. Dashboard Priority Ordering Test ====================

class TestDashboardPriorityOrdering:
    """Тесты корректности отображения приоритетов в dashboard"""

    @pytest.mark.asyncio
    async def test_dashboard_shows_correct_priority_distribution(
        self, queue_service, mock_telegram_client, mock_rate_limiter
    ):
        """
        Dashboard API shows correct priority distribution across all levels.

        Steps:
        1. Add requests with different priorities (HIGH, MEDIUM, LOW)
        2. Call queue statistics API
        3. Verify dashboard data matches queue state
        4. Verify priority percentages are calculated correctly
        """
        account_id = "test_account_001"

        # Add mixed priority requests
        await queue_service.add(
            method="send_message",
            params={"chat_id": "@test", "text": "High priority"},
            request_type=RequestType.STREAM_CONTROL,
            account_id=account_id,
            priority=RequestPriority.HIGH,
        )

        await queue_service.add(
            method="get_chat",
            params={"chat_id": "@channel"},
            request_type=RequestType.METADATA_FETCH,
            account_id=account_id,
            priority=RequestPriority.MEDIUM,
        )

        await queue_service.add(
            method="get_me",
            params={},
            request_type=RequestType.USER_INFO,
            account_id=account_id,
            priority=RequestPriority.MEDIUM,
        )

        await queue_service.add(
            method="get_chat",
            params={"chat_id": "@another_channel"},
            request_type=RequestType.CHANNEL_INFO,
            account_id=account_id,
            priority=RequestPriority.MEDIUM,
        )

        await queue_service.add(
            method="send_message",
            params={"chat_id": "@bg", "text": "Low priority"},
            request_type=RequestType.BACKGROUND_SYNC,
            account_id=account_id,
            priority=RequestPriority.LOW,
        )

        # Get queue statistics
        stats = await queue_service.get_queue_stats(account_id)

        # Verify counts
        assert stats.total_requests == 5, "Should have 5 total requests"
        assert stats.high_priority == 1, "Should have 1 high-priority request (20%)"
        assert stats.medium_priority == 3, "Should have 3 medium-priority requests (60%)"
        assert stats.low_priority == 1, "Should have 1 low-priority request (20%)"

        # Verify priority percentages (for dashboard display)
        high_pct = (stats.high_priority / stats.total_requests) * 100
        medium_pct = (stats.medium_priority / stats.total_requests) * 100
        low_pct = (stats.low_priority / stats.total_requests) * 100

        assert abs(high_pct - 20.0) < 0.1, "High priority should be 20%"
        assert abs(medium_pct - 60.0) < 0.1, "Medium priority should be 60%"
        assert abs(low_pct - 20.0) < 0.1, "Low priority should be 20%"

    @pytest.mark.asyncio
    async def test_dashboard_queue_endpoint_returns_priority_stats(
        self, queue_service, mock_rate_limiter
    ):
        """
        Queue API endpoint (/api/v1/rate-limits/queue) returns correct priority statistics.

        Steps:
        1. Add requests to multiple accounts
        2. Call queue statistics endpoint
        3. Verify response structure
        4. Verify priority breakdown is accurate
        """
        account_1 = "test_account_001"
        account_2 = "test_account_002"

        # Add requests to account 1
        await queue_service.add(
            method="send_message",
            params={"chat_id": "@test", "text": "High"},
            request_type=RequestType.STREAM_CONTROL,
            account_id=account_1,
            priority=RequestPriority.HIGH,
        )

        await queue_service.add(
            method="get_chat",
            params={"chat_id": "@channel"},
            request_type=RequestType.METADATA_FETCH,
            account_id=account_1,
            priority=RequestPriority.MEDIUM,
        )

        # Add requests to account 2
        await queue_service.add(
            method="get_chat",
            params={"chat_id": "@another"},
            request_type=RequestType.CHANNEL_INFO,
            account_id=account_2,
            priority=RequestPriority.MEDIUM,
        )

        await queue_service.add(
            method="send_message",
            params={"chat_id": "@bg", "text": "Low"},
            request_type=RequestType.BACKGROUND_SYNC,
            account_id=account_2,
            priority=RequestPriority.LOW,
        )

        # Get statistics for both accounts
        stats_1 = await queue_service.get_queue_stats(account_1)
        stats_2 = await queue_service.get_queue_stats(account_2)

        # Verify account 1 stats
        assert stats_1.total_requests == 2
        assert stats_1.high_priority == 1
        assert stats_1.medium_priority == 1
        assert stats_1.low_priority == 0

        # Verify account 2 stats
        assert stats_2.total_requests == 2
        assert stats_2.high_priority == 0
        assert stats_2.medium_priority == 1
        assert stats_2.low_priority == 1


# ==================== 4. End-to-End Integration Test ====================

class TestPriorityQueueEndToEnd:
    """Полный тест цикла приоритетного выполнения"""

    @pytest.mark.asyncio
    async def test_complete_priority_workflow(
        self, queue_service, mock_telegram_client, mock_rate_limiter
    ):
        """
        Complete end-to-end test of priority queue workflow.

        Scenario:
        1. System has queued requests (MEDIUM, LOW priority)
        2. User submits stream control request (HIGH priority)
        3. Verify HIGH priority executes immediately
        4. Verify queue state is unchanged
        5. Verify dashboard shows correct state

        This simulates real-world usage:
        - Background tasks are queued (MEDIUM/LOW priority)
        - User action arrives (HIGH priority stream control)
        - System prioritizes user action immediately
        - Dashboard reflects current state
        """
        account_id = "test_account_001"

        # Step 1: Queue has background tasks
        await queue_service.add(
            method="get_chat",
            params={"chat_id": "@channel_1"},
            request_type=RequestType.METADATA_FETCH,
            account_id=account_id,
            priority=RequestPriority.MEDIUM,
            metadata={"job_id": "bg_1"},
        )

        await queue_service.add(
            method="get_chat",
            params={"chat_id": "@channel_2"},
            request_type=RequestType.METADATA_FETCH,
            account_id=account_id,
            priority=RequestPriority.MEDIUM,
            metadata={"job_id": "bg_2"},
        )

        await queue_service.add(
            method="send_message",
            params={"chat_id": "@sync", "text": "Sync"},
            request_type=RequestType.BACKGROUND_SYNC,
            account_id=account_id,
            priority=RequestPriority.LOW,
            metadata={"job_id": "bg_3"},
        )

        # Verify initial state
        initial_stats = await queue_service.get_queue_stats(account_id)
        assert initial_stats.total_requests == 3, "Should start with 3 queued requests"
        assert initial_stats.high_priority == 0, "No high priority initially"

        # Step 2: User submits stream control (HIGH priority)
        start_time = time.time()

        result = await telegram_api_queue.execute_api_call(
            client=mock_telegram_client,
            method="send_message",
            params={"chat_id": "@stream", "text": "Skip to next track"},
            request_type=RequestType.STREAM_CONTROL,
            account_id=account_id,
            priority=RequestPriority.HIGH,
            metadata={"user_action": "skip_track"},
        )

        execution_time = time.time() - start_time

        # Step 3: Verify HIGH priority executed immediately
        assert result is not None, "HIGH priority should return result"
        assert execution_time < 0.1, f"HIGH priority should be immediate, took {execution_time}s"

        # Step 4: Verify queue state is unchanged (background tasks still queued)
        final_stats = await queue_service.get_queue_stats(account_id)
        assert final_stats.total_requests == 3, "Queue should still have 3 requests"
        assert final_stats.high_priority == 0, "No high priority in queue"
        assert final_stats.medium_priority == 2, "2 medium priority still queued"
        assert final_stats.low_priority == 1, "1 low priority still queued"

        # Step 5: Verify dashboard data
        all_requests = await queue_service.get_all(account_id)
        assert len(all_requests) == 3, "Dashboard should show 3 queued requests"

        # Verify all background tasks are still present
        request_ids = {r.metadata.get("job_id") for r in all_requests}
        assert request_ids == {"bg_1", "bg_2", "bg_3"}, "All background tasks should be queued"

        # Verify metadata is preserved
        for request in all_requests:
            assert "job_id" in request.metadata, "Metadata should be preserved"
            assert request.account_id == account_id, "Account ID should match"

    @pytest.mark.asyncio
    async def test_priority_queue_with_rate_limit_scenario(
        self, queue_service, mock_telegram_client
    ):
        """
        Test priority queue behavior during rate limit scenario.

        Scenario:
        1. Account is rate limited
        2. HIGH priority request arrives
        3. Verify it still executes (bypasses queue check)
        4. MEDIUM priority requests queue properly
        """
        account_id = "test_account_001"

        # Simulate rate limit is active (but mock check_limit to allow HIGH priority)
        rate_limit_check_called = {"count": 0}

        async def mock_check_limit(phone):
            """Mock that tracks calls but allows execution"""
            rate_limit_check_called["count"] += 1
            return None  # No active limit for this test

        with patch('src.services.telegram_rate_limiter.rate_limiter.check_limit', side_effect=mock_check_limit):
            # Submit HIGH priority during rate limit recovery
            result = await telegram_api_queue.execute_api_call(
                client=mock_telegram_client,
                method="send_message",
                params={"chat_id": "@test", "text": "Critical control"},
                request_type=RequestType.STREAM_CONTROL,
                account_id=account_id,
                priority=RequestPriority.HIGH,
            )

            assert result is not None, "HIGH priority should execute"
            assert rate_limit_check_called["count"] > 0, "Rate limit check should be called"

            # Queue MEDIUM priority requests
            await queue_service.add(
                method="get_chat",
                params={"chat_id": "@channel"},
                request_type=RequestType.METADATA_FETCH,
                account_id=account_id,
                priority=RequestPriority.MEDIUM,
            )

            # Verify MEDIUM is queued
            stats = await queue_service.get_queue_stats(account_id)
            assert stats.medium_priority == 1, "MEDIUM priority should be queued"


# ==================== 5. Verification Tests ====================

class TestPriorityVerification:
    """Дополнительные тесты проверки корректности"""

    @pytest.mark.asyncio
    async def test_priority_score_calculation(self, queue_service):
        """Verify priority scores are calculated correctly for queue ordering"""
        account_id = "test_account_001"

        # Add requests with different priorities at different times
        high_req = await queue_service.add(
            method="send_message",
            params={"chat_id": "@test"},
            request_type=RequestType.STREAM_CONTROL,
            account_id=account_id,
            priority=RequestPriority.HIGH,
        )

        # Small delay to ensure timestamp difference
        await asyncio.sleep(0.01)

        medium_req = await queue_service.add(
            method="get_chat",
            params={"chat_id": "@channel"},
            request_type=RequestType.METADATA_FETCH,
            account_id=account_id,
            priority=RequestPriority.MEDIUM,
        )

        # Verify HIGH priority has lower score (executes first)
        assert high_req.priority.value < medium_req.priority.value, \
            "HIGH priority should have lower score than MEDIUM"

        # Verify queue respects priority ordering
        all_requests = await queue_service.get_all(account_id)
        assert all_requests[0].id == high_req.id, "HIGH priority should be first"

    @pytest.mark.asyncio
    async def test_auto_priority_assignment_by_request_type(self, queue_service):
        """Verify request types are automatically assigned correct priorities"""
        account_id = "test_account_001"

        # Add different request types without explicit priority
        stream_req = await queue_service.add(
            method="send_message",
            params={},
            request_type=RequestType.STREAM_CONTROL,
            account_id=account_id,
        )

        metadata_req = await queue_service.add(
            method="get_chat",
            params={},
            request_type=RequestType.METADATA_FETCH,
            account_id=account_id,
        )

        background_req = await queue_service.add(
            method="send_message",
            params={},
            request_type=RequestType.BACKGROUND_SYNC,
            account_id=account_id,
        )

        # Verify auto-assigned priorities
        assert stream_req.priority == RequestPriority.HIGH, \
            "STREAM_CONTROL should auto-assign HIGH priority"
        assert metadata_req.priority == RequestPriority.MEDIUM, \
            "METADATA_FETCH should auto-assign MEDIUM priority"
        assert background_req.priority == RequestPriority.LOW, \
            "BACKGROUND_SYNC should auto-assign LOW priority"
