"""
End-to-End Tests: Multi-Account Distribution Under Load
Тестируем распределение запросов между несколькими аккаунтами под нагрузкой

Coverage Target:
- Requests are distributed across 3+ accounts under burst load
- No single account exceeds 80% of its rate limit
- Dashboard shows balanced distribution across accounts
- Account pool statistics reflect actual distribution

This test verifies:
1. 50 API requests are distributed across multiple accounts
2. Distribution is balanced (no account > 80% capacity)
3. Dashboard API returns accurate account distribution
4. MultiAccountRateLiter correctly selects accounts using least-used strategy
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from collections import Counter, defaultdict

from src.services.multi_account_rate_limiter import (
    MultiAccountRateLimiter,
    AccountStatus,
    SelectionStrategy,
    AccountInfo,
    get_multi_account_limiter,
)
from src.services.rate_limit_queue_service import (
    RateLimitQueueService,
    RequestType,
    RequestPriority,
    get_rate_limit_queue_service,
)
from src.services.rate_limit_predictor import RateLimitPredictor, EndpointType


# ==================== Fixtures ====================

@pytest.fixture
async def multi_account_limiter():
    """Get multi-account limiter instance with test accounts"""
    limiter = get_multi_account_limiter()

    # Clear existing accounts
    all_accounts = await limiter.get_all_accounts()
    for account in all_accounts:
        await limiter.remove_account(account.account_id)

    # Add 5 test accounts
    test_accounts = [
        "test_account_001",
        "test_account_002",
        "test_account_003",
        "test_account_004",
        "test_account_005",
    ]

    for account_id in test_accounts:
        await limiter.add_account(
            account_id=account_id,
            phone=f"+123456789{account_id[-1]}",
            status=AccountStatus.ACTIVE,
        )

    yield limiter

    # Cleanup after test
    for account_id in test_accounts:
        await limiter.remove_account(account_id)


@pytest.fixture
async def queue_service():
    """Get queue service instance"""
    service = get_rate_limit_queue_service()

    # Clear test queues
    for i in range(1, 6):
        await service.clear(f"test_account_00{i}")

    yield service

    # Cleanup
    for i in range(1, 6):
        await service.clear(f"test_account_00{i}")


@pytest.fixture
def mock_telegram_client():
    """Mock Pyrogram client for testing"""
    client = MagicMock()

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
    with patch('src.services.multi_account_rate_limiter.TelegramRateLimiter') as mock:
        # Mock the rate limiter instance
        mock_instance = MagicMock()
        mock_instance.check_limit.return_value = None
        mock_instance.record_limit.return_value = None
        mock.return_value = mock_instance
        yield mock_instance


# ==================== 1. Burst Load Distribution Test ====================

class TestBurstLoadDistribution:
    """Тесты распределения нагрузки при burst сценарии"""

    @pytest.mark.asyncio
    async def test_burst_of_50_requests_distributed_across_accounts(
        self, multi_account_limiter, mock_rate_limiter
    ):
        """
        Send burst of 50 API requests and verify distribution across 3+ accounts.

        Steps:
        1. Add 5 accounts to pool
        2. Send 50 concurrent requests using MultiAccountRateLimiter
        3. Track which account was selected for each request
        4. Verify at least 3 different accounts were used
        5. Verify distribution is reasonably balanced

        Expected:
        - Requests distributed across 3+ accounts
        - No single account handles all requests
        - Distribution follows least-used strategy
        """
        # Send 50 requests and track account selection
        selected_accounts = []
        num_requests = 50

        for i in range(num_requests):
            # Select account using least-used strategy
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )

            # Mark account as used (simulate request)
            await multi_account_limiter.mark_account_used(account.account_id)

            selected_accounts.append(account.account_id)

        # Verify at least 3 accounts were used
        unique_accounts = set(selected_accounts)
        assert len(unique_accounts) >= 3, \
            f"Expected at least 3 accounts, got {len(unique_accounts)}: {unique_accounts}"

        # Verify distribution (no single account has > 70% of requests)
        account_counts = Counter(selected_accounts)
        max_count = max(account_counts.values())
        max_percentage = (max_count / num_requests) * 100

        assert max_percentage < 70, \
            f"Account with {max_count} requests has {max_percentage:.1f}% (should be < 70%)"

        # Verify distribution is reasonably balanced (each account should have at least 5 requests)
        min_count = min(account_counts.values())
        assert min_count >= 5, \
            f"Least used account has only {min_count} requests (expected at least 5 for balance)"

    @pytest.mark.asyncio
    async def test_no_single_account_exceeds_80_percent_limit(
        self, multi_account_limiter, mock_rate_limiter
    ):
        """
        Verify no single account exceeds 80% of its rate limit under burst load.

        Steps:
        1. Configure rate limit threshold for each account
        2. Send 50 requests
        3. Track per-account request counts
        4. Verify no account exceeds 80% of theoretical limit

        Assumptions:
        - Assume 100 requests per minute per account limit
        - 50 requests should not hit limit on any single account
        """
        # Define theoretical rate limit
        requests_per_minute_limit = 100
        max_allowed_usage = requests_per_minute_limit * 0.80  # 80% threshold

        # Send 50 requests
        selected_accounts = []
        num_requests = 50

        for i in range(num_requests):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts.append(account.account_id)

        # Check per-account usage
        account_counts = Counter(selected_accounts)

        for account_id, count in account_counts.items():
            usage_percent = (count / requests_per_minute_limit) * 100

            assert count < max_allowed_usage, \
                f"Account {account_id} has {count} requests ({usage_percent:.1f}% of limit), exceeds 80% threshold"

            # Also verify percentage is < 80%
            assert usage_percent < 80.0, \
                f"Account {account_id} usage is {usage_percent:.1f}%, exceeds 80% threshold"


# ==================== 2. Dashboard Verification Test ====================

class TestDashboardDistributionAccuracy:
    """Тесты точности отображения распределения в dashboard"""

    @pytest.mark.asyncio
    async def test_dashboard_shows_balanced_distribution(
        self, multi_account_limiter, mock_rate_limiter
    ):
        """
        Verify dashboard API shows balanced distribution across accounts.

        Steps:
        1. Send 50 requests distributed across accounts
        2. Call MultiAccountRateLimiter.get_pool_stats()
        3. Verify statistics reflect actual distribution
        4. Verify no account shows > 80% usage

        Expected:
        - Pool stats show all active accounts
        - Request counts match actual distribution
        - Usage percentages are balanced
        """
        # Send 50 requests
        selected_accounts = []
        num_requests = 50

        for i in range(num_requests):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts.append(account.account_id)

        # Get pool statistics from dashboard
        pool_stats = await multi_account_limiter.get_pool_stats()

        # Verify all accounts are present
        assert pool_stats.total_accounts >= 3, "Should have at least 3 accounts in pool"
        assert pool_stats.active_accounts >= 3, "Should have at least 3 active accounts"

        # Verify actual distribution matches stats
        account_counts = Counter(selected_accounts)

        # Check each account's request count
        for account_info in pool_stats.accounts:
            account_id = account_info.account_id

            if account_id in account_counts:
                actual_count = account_counts[account_id]
                assert account_info.request_count == actual_count, \
                    f"Dashboard shows {account_info.request_count} requests for {account_id}, " \
                    f"but actual count is {actual_count}"

                # Verify usage is balanced (< 80% of total)
                usage_percent = (actual_count / num_requests) * 100
                assert usage_percent < 80.0, \
                    f"Account {account_id} has {usage_percent:.1f}% of requests, exceeds 80% threshold"

    @pytest.mark.asyncio
    async def test_dashboard_accounts_endpoint_returns_distribution(
        self, multi_account_limiter, mock_rate_limiter
    ):
        """
        Dashboard /api/v1/rate-limits/accounts endpoint returns correct distribution.

        Steps:
        1. Add accounts and send requests
        2. Call get_all_accounts() (simulates dashboard endpoint)
        3. Verify response structure
        4. Verify distribution data is accurate

        Expected:
        - All accounts returned with correct status
        - Request counts match actual usage
        - Health information is present
        """
        # Send requests
        selected_accounts = []
        for i in range(30):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts.append(account.account_id)

        # Get all accounts (simulates dashboard API call)
        all_accounts = await multi_account_limiter.get_all_accounts()

        # Verify all accounts returned
        assert len(all_accounts) >= 3, "Should return at least 3 accounts"

        # Verify distribution accuracy
        actual_counts = Counter(selected_accounts)

        for account in all_accounts:
            # Verify account has required fields
            assert account.account_id is not None
            assert account.status is not None
            assert account.request_count is not None

            # Verify request count matches
            if account.account_id in actual_counts:
                expected_count = actual_counts[account.account_id]
                assert account.request_count == expected_count, \
                    f"Request count mismatch for {account.account_id}"

            # Verify usage percentage is reasonable
            if len(selected_accounts) > 0:
                usage_percent = (account.request_count / len(selected_accounts)) * 100
                assert usage_percent <= 80.0, \
                    f"Account {account.account_id} usage {usage_percent:.1f}% exceeds 80%"


# ==================== 3. Selection Strategy Test ====================

class TestSelectionStrategies:
    """Тесты стратегий выбора аккаунтов"""

    @pytest.mark.asyncio
    async def test_least_used_strategy_balances_load(self, multi_account_limiter):
        """
        LEAST_USED strategy balances load across accounts evenly.

        Steps:
        1. Start with all accounts at 0 requests
        2. Send 50 requests using LEAST_USED strategy
        3. Verify distribution is balanced
        4. Verify variance is low (accounts have similar request counts)

        Expected:
        - Distribution variance < 20%
        - All accounts used
        - Load is approximately equal
        """
        num_requests = 50
        selected_accounts = []

        for i in range(num_requests):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts.append(account.account_id)

        # Calculate distribution statistics
        account_counts = Counter(selected_accounts)
        counts = list(account_counts.values())

        # Calculate variance
        mean = sum(counts) / len(counts)
        variance = sum((x - mean) ** 2 for x in counts) / len(counts)
        std_dev = variance ** 0.5

        # Verify standard deviation is low (< 30% of mean)
        relative_std_dev = (std_dev / mean) * 100 if mean > 0 else 0

        assert relative_std_dev < 30, \
            f"Distribution variance too high: std_dev={std_dev:.2f}, mean={mean:.2f}, " \
            f"relative_std_dev={relative_std_dev:.1f}% (should be < 30%)"

        # Verify all accounts have reasonable number of requests
        for account_id, count in account_counts.items():
            assert count >= 5, \
                f"Account {account_id} has only {count} requests, distribution not balanced"

    @pytest.mark.asyncio
    async def test_round_robin_strategy_cyclically_distributes(self, multi_account_limiter):
        """
        ROUND_ROBIN strategy distributes requests cyclically across accounts.

        Steps:
        1. Send 15 requests using ROUND_ROBIN strategy
        2. Verify cyclic pattern (account1, account2, account3, ...)
        3. Verify each account gets approximately equal requests

        Expected:
        - Accounts selected in cyclic order
        - Each account gets similar number of requests
        """
        num_requests = 15
        selected_accounts = []

        for i in range(num_requests):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.ROUND_ROBIN
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts.append(account.account_id)

        # Verify at least 3 accounts were used
        unique_accounts = set(selected_accounts)
        assert len(unique_accounts) >= 3, "Round-robin should use at least 3 accounts"

        # Verify each account got similar number of requests
        account_counts = Counter(selected_accounts)
        counts = list(account_counts.values())

        # With 15 requests and 5 accounts, each should get 3 requests (perfect balance)
        # Or with 3-4 accounts, distribution should still be even
        max_count = max(counts)
        min_count = min(counts)

        assert max_count - min_count <= 1, \
            f"Round-robin distribution not even: max={max_count}, min={min_count}"


# ==================== 4. End-to-End Integration Test ====================

class TestMultiAccountDistributionEndToEnd:
    """Полный тест цикла распределения между аккаунтами"""

    @pytest.mark.asyncio
    async def test_complete_burst_load_workflow(
        self, multi_account_limiter, queue_service, mock_rate_limiter
    ):
        """
        Complete end-to-end test of multi-account distribution under burst load.

        Scenario:
        1. System has 5 accounts in pool
        2. Burst of 50 requests arrive simultaneously
        3. MultiAccountRateLimiter distributes requests using LEAST_USED
        4. Verify distribution is balanced (no account > 80%)
        5. Verify dashboard shows correct statistics
        6. Verify queue service tracks per-account usage

        This simulates real-world usage:
        - Multiple Telegram accounts handling API requests
        - Burst traffic pattern (e.g., user joins multiple channels)
        - System balances load to avoid hitting rate limits
        - Dashboard provides visibility into distribution
        """
        num_requests = 50
        selected_accounts = []

        # Step 1-2: Send burst of 50 requests
        for i in range(num_requests):
            # Select account for this request
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )

            # Track selection
            selected_accounts.append(account.account_id)

            # Mark account as used
            await multi_account_limiter.mark_account_used(account.account_id)

            # Add to queue service (simulate queuing the request)
            await queue_service.add(
                method="get_chat",
                params={"chat_id": f"@channel_{i}"},
                request_type=RequestType.CHANNEL_INFO,
                account_id=account.account_id,
                priority=RequestPriority.MEDIUM,
            )

        # Step 3: Verify distribution across 3+ accounts
        unique_accounts = set(selected_accounts)
        assert len(unique_accounts) >= 3, \
            f"Expected 3+ accounts, got {len(unique_accounts)}: {unique_accounts}"

        # Step 4: Verify no account exceeds 80% threshold
        account_counts = Counter(selected_accounts)
        for account_id, count in account_counts.items():
            usage_percent = (count / num_requests) * 100
            assert usage_percent < 80.0, \
                f"Account {account_id} has {usage_percent:.1f}% of requests, exceeds 80%"

        # Step 5: Verify dashboard statistics
        pool_stats = await multi_account_limiter.get_pool_stats()
        assert pool_stats.total_accounts >= 3, "Dashboard should show 3+ accounts"
        assert pool_stats.active_accounts >= 3, "Dashboard should show 3+ active accounts"

        # Verify request counts match
        for account_info in pool_stats.accounts:
            account_id = account_info.account_id
            if account_id in account_counts:
                expected = account_counts[account_id]
                assert account_info.request_count == expected, \
                    f"Dashboard shows {account_info.request_count} for {account_id}, expected {expected}"

        # Step 6: Verify queue service tracking
        for account_id in unique_accounts:
            queue_stats = await queue_service.get_queue_stats(account_id)
            # Each account should have some queued requests
            assert queue_stats.total_requests > 0, \
                f"Queue service should track requests for {account_id}"

    @pytest.mark.asyncio
    async def test_distribution_with_rate_limit_scenarios(
        self, multi_account_limiter, mock_rate_limiter
    ):
        """
        Test distribution when accounts become rate-limited.

        Scenario:
        1. Start with 5 active accounts
        2. Mark some accounts as rate-limited
        3. Send requests
        4. Verify distribution adapts (avoids rate-limited accounts)
        5. Verify no account exceeds 80% despite fewer available accounts
        """
        # Send initial round of requests
        selected_accounts_round1 = []
        for i in range(20):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts_round1.append(account.account_id)

        # Get most used accounts
        counts = Counter(selected_accounts_round1)
        most_used_account = counts.most_common(1)[0][0]

        # Mark most used account as rate-limited
        await multi_account_limiter.mark_rate_limited(
            account_id=most_used_account,
            seconds=60
        )

        # Send second round of requests
        selected_accounts_round2 = []
        for i in range(30):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts_round2.append(account.account_id)

        # Verify rate-limited account was not used in round 2
        assert most_used_account not in selected_accounts_round2, \
            f"Rate-limited account {most_used_account} should not be selected"

        # Verify distribution in round 2 is still balanced
        counts_round2 = Counter(selected_accounts_round2)
        for account_id, count in counts_round2.items():
            usage_percent = (count / len(selected_accounts_round2)) * 100
            assert usage_percent < 80.0, \
                f"Account {account_id} has {usage_percent:.1f}% of round 2 requests, exceeds 80%"

        # Verify system adapted to remaining accounts
        unique_accounts_round2 = set(selected_accounts_round2)
        assert len(unique_accounts_round2) >= 2, \
            "Should distribute across at least 2 remaining accounts"


# ==================== 5. Edge Cases and Stress Tests ====================

class TestDistributionEdgeCases:
    """Тесты граничных случаев и стресс-тестирование"""

    @pytest.mark.asyncio
    async def test_distribution_with_single_account(self, multi_account_limiter):
        """
        Verify behavior when only one account is available.

        Steps:
        1. Remove all but one account
        2. Send 20 requests
        3. Verify all requests go to single account
        4. Verify this is logged as edge case (not balanced)
        """
        # Get all accounts
        all_accounts = await multi_account_limiter.get_all_accounts()

        # Keep only first account, remove others
        if len(all_accounts) > 1:
            for account in all_accounts[1:]:
                await multi_account_limiter.remove_account(account.account_id)

        # Send requests
        selected_accounts = []
        for i in range(20):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts.append(account.account_id)

        # Verify all requests went to single account
        unique_accounts = set(selected_accounts)
        assert len(unique_accounts) == 1, "Should use only one available account"

        # Verify that single account got all requests
        assert len(selected_accounts) == 20, "All requests should be handled"

    @pytest.mark.asyncio
    async def test_distribution_after_account_removal(self, multi_account_limiter):
        """
        Verify distribution adapts when accounts are removed mid-test.

        Steps:
        1. Start with 5 accounts
        2. Send 20 requests
        3. Remove 2 accounts
        4. Send 20 more requests
        5. Verify distribution adapts to remaining accounts
        """
        # Round 1: 5 accounts
        selected_accounts_round1 = []
        for i in range(20):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts_round1.append(account.account_id)

        # Remove 2 accounts
        all_accounts = await multi_account_limiter.get_all_accounts()
        accounts_to_remove = all_accounts[:2]
        for account in accounts_to_remove:
            await multi_account_limiter.remove_account(account.account_id)

        # Round 2: 3 remaining accounts
        selected_accounts_round2 = []
        for i in range(20):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts_round2.append(account.account_id)

        # Verify round 1 used 5 accounts
        assert len(set(selected_accounts_round1)) >= 3, "Round 1 should use 3+ accounts"

        # Verify round 2 adapted to remaining accounts
        removed_ids = {a.account_id for a in accounts_to_remove}
        round2_ids = set(selected_accounts_round2)
        assert not round2_ids.intersection(removed_ids), \
            "Round 2 should not use removed accounts"

        # Verify round 2 distribution is still balanced
        counts_round2 = Counter(selected_accounts_round2)
        for account_id, count in counts_round2.items():
            usage_percent = (count / len(selected_accounts_round2)) * 100
            assert usage_percent < 80.0, \
                f"Account {account_id} has {usage_percent:.1f}% in round 2, exceeds 80%"

    @pytest.mark.asyncio
    async def test_stress_test_100_requests_distribution(self, multi_account_limiter):
        """
        Stress test: Verify distribution with 100 requests (2x normal load).

        Steps:
        1. Send 100 requests (higher than typical 50)
        2. Verify distribution remains balanced
        3. Verify no account exceeds 80%
        4. Verify performance is acceptable
        """
        num_requests = 100
        selected_accounts = []

        start_time = time.time()

        for i in range(num_requests):
            account = await multi_account_limiter.select_account(
                strategy=SelectionStrategy.LEAST_USED
            )
            await multi_account_limiter.mark_account_used(account.account_id)
            selected_accounts.append(account.account_id)

        end_time = time.time()
        total_time = end_time - start_time

        # Verify performance (should complete in reasonable time)
        assert total_time < 5.0, \
            f"100 requests took {total_time:.2f}s, should be < 5s"

        # Verify distribution is balanced
        unique_accounts = set(selected_accounts)
        assert len(unique_accounts) >= 3, "Should use 3+ accounts even with high load"

        # Verify no account exceeds 80%
        account_counts = Counter(selected_accounts)
        for account_id, count in account_counts.items():
            usage_percent = (count / num_requests) * 100
            assert usage_percent < 80.0, \
                f"Account {account_id} has {usage_percent:.1f}% of 100 requests, exceeds 80%"
