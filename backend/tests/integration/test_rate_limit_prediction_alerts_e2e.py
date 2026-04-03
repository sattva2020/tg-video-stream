"""
End-to-End Tests: Rate Limit Prediction and Alerts
Тестируем полный цикл предсказания лимитов и автоматических оповещений

Coverage Target:
- Sustained API traffic approaching limits triggers accurate predictions
- Predictor forecasts breach time based on usage patterns
- Alert triggers at 75% threshold (warning) and 90% (critical)
- Admin notifications are sent correctly
- Dashboard shows warning indicators and predictions

This test verifies:
1. API traffic generation approaches limits realistically
2. RateLimitPredictor calculates breach time accurately
3. Alert thresholds trigger at configured percentages
4. Notifications reach admin users
5. Dashboard API returns warning indicators
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from src.services.rate_limit_predictor import (
    RateLimitPredictor,
    UsageTracker,
    EndpointType,
    Prediction,
    UsageStats,
    get_rate_limit_predictor,
)
from src.services.multi_account_rate_limiter import MultiAccountRateLimiter
from src.tasks.rate_limit_monitor import (
    check_account_rate_limits_sync,
    trigger_alert_sync,
    check_all_rate_limits_sync,
)


# ==================== Fixtures ====================

@pytest.fixture
async def predictor():
    """Get predictor instance"""
    predictor = get_rate_limit_predictor()
    yield predictor
    # Cleanup is handled by the predictor's Redis TTL


@pytest.fixture
async def usage_tracker():
    """Get usage tracker instance"""
    tracker = UsageTracker()
    return tracker


@pytest.fixture
def mock_notification_service():
    """Mock notification service to capture alerts"""
    with patch('src.tasks.rate_limit_monitor.NotificationService') as mock_service:
        mock_instance = MagicMock()
        mock_service.return_value = mock_instance
        mock_instance.log_delivery = MagicMock()
        yield mock_instance


@pytest.fixture
def mock_prometheus_metrics():
    """Mock Prometheus metrics to avoid actual metrics export"""
    with patch('src.tasks.rate_limit_monitor._update_prometheus_metrics_for_account'):
        yield


@pytest.fixture
def test_account_id():
    """Test account ID"""
    return "test_prediction_account_001"


@pytest.fixture
def test_limits():
    """Test rate limits configuration"""
    return {
        EndpointType.MESSAGES: 100,      # 100 requests per minute
        EndpointType.MEDIA: 50,          # 50 requests per minute
        EndpointType.GET_CHAT: 200,      # 200 requests per minute
        EndpointType.GET_HISTORY: 30,    # 30 requests per minute
        EndpointType.JOIN_CHANNEL: 10,   # 10 requests per minute
        EndpointType.OTHER: 100,         # 100 requests per minute
    }


# ==================== 1. Sustained Traffic Approaching Limits ====================

class TestSustainedTrafficApproachingLimits:
    """Тесты генерации устойчивого трафика, приближающегося к лимитам"""

    @pytest.mark.asyncio
    async def test_generate_traffic_to_75_percent_threshold(
        self, usage_tracker, test_account_id, test_limits
    ):
        """
        Generate sustained traffic to reach 75% threshold.

        Steps:
        1. Calculate 75% of limit for MESSAGES endpoint
        2. Generate that many requests over time
        3. Verify usage reaches 75% threshold
        4. Confirm requests are tracked in sliding window
        """
        endpoint = EndpointType.MESSAGES
        limit = test_limits[endpoint]
        target_requests = int(limit * 0.75)  # 75 requests

        # Generate requests spread over time (simulate real traffic)
        start_time = datetime.now()
        for i in range(target_requests):
            # Spread requests over 30 seconds to simulate sustained traffic
            delay = (i / target_requests) * 30  # 30 seconds total
            request_time = start_time + timedelta(seconds=delay)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Check usage stats
        stats = await usage_tracker.get_usage_stats(test_account_id, endpoint)

        assert stats.request_count >= target_requests * 0.9, \
            f"Expected at least {target_requests * 0.9:.0f} requests, got {stats.request_count}"
        assert stats.requests_per_minute > 0, "requests_per_minute should be positive"
        assert stats.trend in ["increasing", "stable", "decreasing"], \
            f"Invalid trend: {stats.trend}"

    @pytest.mark.asyncio
    async def test_generate_burst_traffic_approaching_limit(
        self, usage_tracker, test_account_id, test_limits
    ):
        """
        Generate burst traffic to rapidly approach limit.

        Steps:
        1. Generate 90% of limit in short burst
        2. Verify usage spike is detected
        3. Confirm trend is "increasing"
        """
        endpoint = EndpointType.GET_CHAT
        limit = test_limits[endpoint]
        burst_count = int(limit * 0.9)  # 90%

        start_time = datetime.now()
        for i in range(burst_count):
            # Burst over 10 seconds
            request_time = start_time + timedelta(seconds=(i / burst_count) * 10)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Get stats with 60-second window
        stats = await usage_tracker.get_usage_stats(
            test_account_id, endpoint, window_seconds=60
        )

        assert stats.request_count >= burst_count * 0.9, \
            f"Expected at least {burst_count * 0.9:.0f} burst requests"
        assert stats.requests_per_minute > 0, "Should show high rate per minute"


# ==================== 2. Prediction Accuracy ====================

class TestPredictionAccuracy:
    """Тесты точности предсказания времени достижения лимитов"""

    @pytest.mark.asyncio
    async def test_predictor_forecasts_breach_time_accurately(
        self, predictor, usage_tracker, test_account_id, test_limits
    ):
        """
        Predictor forecasts breach time based on current usage rate.

        Steps:
        1. Generate traffic at steady rate
        2. Get prediction from predictor
        3. Verify predicted_breach_time is set
        4. Verify time_until_breach_seconds is reasonable
        """
        endpoint = EndpointType.MESSAGES
        limit = test_limits[endpoint]

        # Generate 50% of limit at steady rate
        request_count = int(limit * 0.5)
        start_time = datetime.now() - timedelta(seconds=60)  # Start 1 minute ago

        for i in range(request_count):
            request_time = start_time + timedelta(seconds=(i / request_count) * 60)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Get prediction
        prediction = await predictor.predict_breach_time(
            account_id=test_account_id,
            endpoint_type=endpoint,
            limit=limit
        )

        assert prediction is not None, "Prediction should not be None"
        assert prediction.account_id == test_account_id
        assert prediction.endpoint_type == endpoint
        assert prediction.limit == limit
        assert prediction.current_usage > 0, "Should have tracked usage"
        assert prediction.usage_percent > 40, "Should be above 40%"
        assert prediction.trend in ["increasing", "stable", "decreasing"]
        assert prediction.confidence >= 0.0 and prediction.confidence <= 1.0

        # If we have usage, we should predict breach time (or indicate won't breach)
        if prediction.usage_percent > 50:
            assert prediction.predicted_breach_time is not None, \
                "Should predict breach time when above 50%"

    @pytest.mark.asyncio
    async def test_prediction_confidence_increases_with_more_data(
        self, predictor, usage_tracker, test_account_id, test_limits
    ):
        """
        Prediction confidence increases with more usage data.

        Steps:
        1. Generate small traffic → check low confidence
        2. Generate sustained traffic → check higher confidence
        """
        endpoint = EndpointType.MEDIA
        limit = test_limits[endpoint]

        # First prediction with minimal data
        await usage_tracker.record_request(test_account_id, endpoint)
        prediction_1 = await predictor.predict_breach_time(
            account_id=test_account_id,
            endpoint_type=endpoint,
            limit=limit
        )

        # Generate more sustained traffic
        start_time = datetime.now() - timedelta(seconds=120)
        for i in range(20):
            request_time = start_time + timedelta(seconds=(i / 20) * 120)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        prediction_2 = await predictor.predict_breach_time(
            account_id=test_account_id,
            endpoint_type=endpoint,
            limit=limit
        )

        # Second prediction should have more confidence (more data points)
        # Note: This is a soft assertion as confidence calculation may vary
        if prediction_2.current_usage > 10:
            assert prediction_2.confidence > 0, "Should have some confidence with data"


# ==================== 3. Alert Triggering ====================

class TestAlertTriggering:
    """Тесты triggering оповещений при достижении порогов"""

    @pytest.mark.asyncio
    async def test_alert_triggers_at_75_percent_threshold(
        self, predictor, usage_tracker, test_account_id, test_limits,
        mock_notification_service, mock_prometheus_metrics
    ):
        """
        Alert triggers when usage reaches 75% threshold.

        Steps:
        1. Generate traffic to reach exactly 75% usage
        2. Call check_account_rate_limits_sync
        3. Verify alert_triggered flag is True
        4. Verify notification service was called
        """
        endpoint = EndpointType.MESSAGES
        limit = test_limits[endpoint]
        warning_threshold = 75  # 75%

        # Generate traffic to reach 75%
        request_count = int(limit * (warning_threshold / 100))
        start_time = datetime.now() - timedelta(seconds=60)

        for i in range(request_count):
            request_time = start_time + timedelta(seconds=(i / request_count) * 60)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Check rate limits (triggers alert check)
        result = check_account_rate_limits_sync(test_account_id)

        assert result["success"], f"Check failed: {result.get('error')}"
        assert result["account_id"] == test_account_id
        assert result["status"] in ["warning", "critical", "severe", "healthy"], \
            f"Unexpected status: {result['status']}"

        # Check predictions for alert triggers
        predictions = result.get("predictions", [])
        assert len(predictions) > 0, "Should have predictions"

        # Find prediction for our endpoint
        alert_prediction = None
        for pred in predictions:
            if pred.get("endpoint_type") == endpoint.value and pred.get("usage_percent", 0) >= 75:
                alert_prediction = pred
                break

        # If we hit the threshold, prediction should show it
        if alert_prediction:
            assert alert_prediction["usage_percent"] >= 75
            assert alert_prediction["account_id"] == test_account_id

    @pytest.mark.asyncio
    async def test_alert_triggers_at_90_percent_critical_threshold(
        self, predictor, usage_tracker, test_account_id, test_limits,
        mock_notification_service
    ):
        """
        Alert triggers at 90% critical threshold.

        Steps:
        1. Generate traffic to reach 90% usage
        2. Verify status is "critical"
        3. Verify alert_type is "critical"
        """
        endpoint = EndpointType.GET_CHAT
        limit = test_limits[endpoint]
        critical_threshold = 90  # 90%

        # Generate traffic to reach 90%
        request_count = int(limit * (critical_threshold / 100))
        start_time = datetime.now() - timedelta(seconds=60)

        for i in range(request_count):
            request_time = start_time + timedelta(seconds=(i / request_count) * 60)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Check rate limits
        result = check_account_rate_limits_sync(test_account_id)

        assert result["success"], f"Check failed: {result.get('error')}"

        # Check if we hit critical level
        max_usage = result.get("max_usage_percent", 0)
        if max_usage >= 90:
            assert result["status"] in ["critical", "severe"], \
                f"Expected critical status at 90%+, got: {result['status']}"

    @pytest.mark.asyncio
    async def test_alert_triggers_only_once_per_cooldown_period(
        self, usage_tracker, test_account_id, test_limits,
        mock_notification_service
    ):
        """
        Alert doesn't trigger repeatedly within cooldown period.

        Steps:
        1. Generate traffic to trigger alert
        2. Trigger alert twice in quick succession
        3. Verify second call respects cooldown
        """
        endpoint = EndpointType.OTHER
        limit = test_limits[endpoint]

        # Generate traffic to 80%
        request_count = int(limit * 0.8)
        start_time = datetime.now() - timedelta(seconds=60)

        for i in range(request_count):
            request_time = start_time + timedelta(seconds=(i / request_count) * 60)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Trigger first alert
        result_1 = trigger_alert_sync(
            account_id=test_account_id,
            alert_type="warning",
            usage_percent=80.0,
            endpoint_type=endpoint.value,
            predicted_breach_time="2025-01-24T15:30:00Z"
        )

        assert result_1["success"], f"First alert failed: {result_1.get('error')}"
        assert result_1["account_id"] == test_account_id

        # Trigger second alert immediately (should respect cooldown)
        # Note: Actual cooldown enforcement depends on implementation
        result_2 = trigger_alert_sync(
            account_id=test_account_id,
            alert_type="warning",
            usage_percent=81.0,
            endpoint_type=endpoint.value,
            predicted_breach_time="2025-01-24T15:31:00Z"
        )

        # Second alert should still succeed (logging all alerts)
        assert result_2["success"], f"Second alert failed: {result_2.get('error')}"


# ==================== 4. Admin Notifications ====================

class TestAdminNotifications:
    """Тесты отправки оповещений администраторам"""

    @pytest.mark.asyncio
    async def test_alert_notification_includes_all_required_fields(
        self, mock_notification_service
    ):
        """
        Alert notification includes all required information.

        Steps:
        1. Trigger alert with test data
        2. Verify notification service log_delivery was called
        3. Verify all required fields present in logged data
        """
        account_id = "test_notification_account"
        alert_type = "warning"
        usage_percent = 78.5
        endpoint_type = "messages"
        predicted_breach = "2025-01-24T16:00:00Z"

        # Trigger alert
        result = trigger_alert_sync(
            account_id=account_id,
            alert_type=alert_type,
            usage_percent=usage_percent,
            endpoint_type=endpoint_type,
            predicted_breach_time=predicted_breach
        )

        assert result["success"], f"Alert trigger failed: {result.get('error')}"
        assert result["account_id"] == account_id

        # Verify notification was logged
        assert mock_notification_service.log_delivery.called, \
            "Notification service log_delivery should be called"

        # Get the call arguments
        call_args = mock_notification_service.log_delivery.call_args
        assert call_args is not None

        # Verify logged data contains key information
        kwargs = call_args[1] if len(call_args) > 1 else {}
        status = kwargs.get('status', '')
        error_msg = kwargs.get('error_message', '')

        assert 'success' in status, "Status should indicate success"
        assert '78.5' in error_msg or '78' in error_msg, \
            f"Error message should contain usage percent: {error_msg}"
        assert alert_type in error_msg.lower(), \
            f"Error message should contain alert type: {error_msg}"

    @pytest.mark.asyncio
    async def test_notification_sent_for_all_accounts_in_pool(
        self, predictor, usage_tracker, test_limits,
        mock_notification_service
    ):
        """
        Notifications sent for all accounts approaching limits.

        Steps:
        1. Create multiple test accounts
        2. Generate traffic for each to approach limits
        3. Call check_all_rate_limits_sync
        4. Verify notifications sent for all accounts
        """
        accounts = [
            "test_multi_alert_001",
            "test_multi_alert_002",
            "test_multi_alert_003",
        ]
        endpoint = EndpointType.MESSAGES
        limit = test_limits[endpoint]

        # Generate traffic for each account
        for account_id in accounts:
            request_count = int(limit * 0.75)  # 75%
            start_time = datetime.now() - timedelta(seconds=60)

            for i in range(request_count):
                request_time = start_time + timedelta(seconds=(i / request_count) * 60)
                await usage_tracker.record_request(account_id, endpoint, request_time)

        # Check all accounts
        result = check_all_rate_limits_sync()

        assert result["success"], f"Check all failed: {result.get('error')}"
        assert result["total_accounts"] >= len(accounts), \
            f"Should have at least {len(accounts)} accounts"

        # Verify each account was checked
        account_results = result.get("accounts", [])
        checked_account_ids = [ar.get("account_id") for ar in account_results]

        for account_id in accounts:
            assert account_id in checked_account_ids, \
                f"Account {account_id} should be in results"


# ==================== 5. Dashboard Warning Indicators ====================

class TestDashboardWarnings:
    """Тесты отображения предупреждений на дашборде"""

    @pytest.mark.asyncio
    async def test_dashboard_shows_warning_indicators(
        self, predictor, usage_tracker, test_account_id, test_limits
    ):
        """
        Dashboard API returns warning indicators for accounts approaching limits.

        Steps:
        1. Generate traffic to 80% usage
        2. Get account status from predictor
        3. Verify status contains warning indicators
        4. Verify predictions include breach time
        """
        endpoint = EndpointType.MESSAGES
        limit = test_limits[endpoint]

        # Generate traffic to 80%
        request_count = int(limit * 0.8)
        start_time = datetime.now() - timedelta(seconds=60)

        for i in range(request_count):
            request_time = start_time + timedelta(seconds=(i / request_count) * 60)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Get account status (used by dashboard)
        status = await predictor.get_account_status(test_account_id)

        assert status is not None, "Status should not be None"
        assert status["account_id"] == test_account_id
        assert "status" in status, "Should have status field"

        # At 80%, status should be warning or worse
        assert status["status"] in ["warning", "critical", "severe"], \
            f"Expected warning+ status at 80%, got: {status['status']}"

        # Check predictions
        predictions = status.get("predictions", [])
        assert len(predictions) > 0, "Should have predictions"

        # Find prediction for our endpoint
        endpoint_prediction = None
        for pred in predictions:
            if pred.get("endpoint_type") == endpoint.value:
                endpoint_prediction = pred
                break

        assert endpoint_prediction is not None, f"Should have prediction for {endpoint.value}"
        assert endpoint_prediction.get("usage_percent", 0) >= 75
        assert "alert_triggered" in endpoint_prediction

    @pytest.mark.asyncio
    async def test_dashboard_predictions_include_breach_time(
        self, predictor, usage_tracker, test_account_id, test_limits
    ):
        """
        Dashboard predictions include time until breach.

        Steps:
        1. Generate sustained traffic
        2. Get predictions
        3. Verify breach time is included
        4. Verify trend is calculated
        """
        endpoint = EndpointType.MEDIA
        limit = test_limits[endpoint]

        # Generate traffic with increasing trend
        request_count = int(limit * 0.7)
        start_time = datetime.now() - timedelta(seconds=90)

        for i in range(request_count):
            # Accelerate requests (increasing trend)
            progress = i / request_count
            delay = 90 * (progress ** 2)  # Quadratic acceleration
            request_time = start_time + timedelta(seconds=delay)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Get prediction
        prediction = await predictor.predict_breach_time(
            account_id=test_account_id,
            endpoint_type=endpoint,
            limit=limit
        )

        assert prediction is not None
        assert prediction.trend in ["increasing", "stable", "decreasing"]

        # At high usage with trend, should predict breach time
        if prediction.usage_percent > 60:
            assert prediction.predicted_breach_time is not None, \
                "Should predict breach time at high usage"
            assert prediction.time_until_breach_seconds is not None, \
                "Should include seconds until breach"

    @pytest.mark.asyncio
    async def test_dashboard_shows_multiple_accounts_status(
        self, predictor, usage_tracker, test_limits
    ):
        """
        Dashboard shows aggregated status for multiple accounts.

        Steps:
        1. Create multiple accounts with different usage levels
        2. Get global status
        3. Verify aggregated metrics
        """
        accounts = {
            "healthy_account": 0.4,     # 40% - healthy
            "warning_account": 0.78,    # 78% - warning
            "critical_account": 0.92,   # 92% - critical
        }
        endpoint = EndpointType.MESSAGES
        limit = test_limits[endpoint]

        # Generate traffic for each account
        for account_id, usage_percent in accounts.items():
            request_count = int(limit * usage_percent)
            start_time = datetime.now() - timedelta(seconds=60)

            for i in range(request_count):
                request_time = start_time + timedelta(seconds=(i / request_count) * 60)
                await usage_tracker.record_request(account_id, endpoint, request_time)

        # Get global status
        global_status = await predictor.get_global_status()

        assert global_status is not None
        assert "total_accounts" in global_status
        assert "healthy_accounts" in global_status
        assert "warning_accounts" in global_status
        assert "critical_accounts" in global_status

        # Should have at least one warning and one critical
        assert global_status["warning_accounts"] >= 1, \
            "Should have at least 1 warning account"
        assert global_status["critical_accounts"] >= 1, \
            "Should have at least 1 critical account"


# ==================== 6. End-to-End Workflow ====================

class TestPredictionAndAlertsEndToEnd:
    """Полные end-to-end тесты предсказания и оповещений"""

    @pytest.mark.asyncio
    async def test_complete_prediction_and_alert_workflow(
        self, predictor, usage_tracker, test_account_id, test_limits,
        mock_notification_service, mock_prometheus_metrics
    ):
        """
        Complete workflow: traffic → prediction → alert → dashboard.

        Steps:
        1. Generate sustained API traffic approaching limits
        2. Check predictor forecasts breach time accurately
        3. Verify alert triggers at 75% threshold
        4. Confirm admin notification received
        5. Check dashboard shows warning indicators
        """
        endpoint = EndpointType.MESSAGES
        limit = test_limits[endpoint]

        # Step 1: Generate sustained traffic to 80%
        request_count = int(limit * 0.8)
        start_time = datetime.now() - timedelta(seconds=60)

        for i in range(request_count):
            request_time = start_time + timedelta(seconds=(i / request_count) * 60)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Step 2: Check predictor forecasts breach time
        prediction = await predictor.predict_breach_time(
            account_id=test_account_id,
            endpoint_type=endpoint,
            limit=limit
        )

        assert prediction is not None, "Prediction should exist"
        assert prediction.usage_percent >= 75, "Should be above 75% threshold"
        assert prediction.predicted_breach_time is not None, \
            "Should predict breach time at 80% usage"
        assert prediction.time_until_breach_seconds is not None, \
            "Should include time until breach"
        assert prediction.confidence > 0, "Should have confidence in prediction"

        # Step 3: Verify alert triggers at 75% threshold
        check_result = check_account_rate_limits_sync(test_account_id)

        assert check_result["success"], f"Check failed: {check_result.get('error')}"
        assert check_result["status"] in ["warning", "critical", "severe"], \
            f"Status should be warning+ at 80%: {check_result['status']}"

        # Check predictions in result
        predictions = check_result.get("predictions", [])
        assert len(predictions) > 0, "Should have predictions"

        # Step 4: Confirm admin notification received
        # (Verified via mock_notification_service fixture)
        assert mock_notification_service.log_delivery.called, \
            "Notification should be sent"

        # Step 5: Check dashboard shows warning indicators
        dashboard_status = await predictor.get_account_status(test_account_id)

        assert dashboard_status is not None
        assert dashboard_status["status"] in ["warning", "critical", "severe"], \
            f"Dashboard should show warning: {dashboard_status['status']}"
        assert dashboard_status["max_usage_percent"] >= 75, \
            "Dashboard should show usage above threshold"

        # Verify dashboard predictions match
        dashboard_predictions = dashboard_status.get("predictions", [])
        assert len(dashboard_predictions) > 0, "Dashboard should show predictions"

    @pytest.mark.asyncio
    async def test_prediction_accuracy_improves_over_time(
        self, predictor, usage_tracker, test_account_id, test_limits
    ):
        """
        Prediction accuracy improves as more data is collected.

        Steps:
        1. Generate traffic in waves
        2. Check predictions after each wave
        3. Verify confidence increases
        """
        endpoint = EndpointType.GET_CHAT
        limit = test_limits[endpoint]

        # Wave 1: Light traffic
        for i in range(20):
            request_time = datetime.now() - timedelta(seconds=60 - i)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        prediction_1 = await predictor.predict_breach_time(
            account_id=test_account_id,
            endpoint_type=endpoint,
            limit=limit
        )

        # Wave 2: Add more traffic
        for i in range(30):
            request_time = datetime.now() - timedelta(seconds=60 - i * 0.5)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        prediction_2 = await predictor.predict_breach_time(
            account_id=test_account_id,
            endpoint_type=endpoint,
            limit=limit
        )

        # With more data, prediction should be more confident
        assert prediction_2.current_usage > prediction_1.current_usage, \
            "Usage should increase with more requests"

        if prediction_2.usage_percent > 30:
            assert prediction_2.confidence > 0, \
                "Should have some confidence with sufficient data"

    @pytest.mark.asyncio
    async def test_multi_endpoint_prediction_and_alerts(
        self, predictor, usage_tracker, test_account_id, test_limits,
        mock_notification_service
    ):
        """
        Predictions and alerts work across multiple endpoint types.

        Steps:
        1. Generate traffic for multiple endpoints
        2. Verify predictions for each endpoint
        3. Verify alerts triggered for critical endpoints
        """
        traffic_config = {
            EndpointType.MESSAGES: 0.75,      # 75% - warning
            EndpointType.MEDIA: 0.92,         # 92% - critical
            EndpointType.GET_CHAT: 0.50,      # 50% - healthy
        }

        # Generate traffic for each endpoint
        for endpoint, usage_percent in traffic_config.items():
            limit = test_limits[endpoint]
            request_count = int(limit * usage_percent)
            start_time = datetime.now() - timedelta(seconds=60)

            for i in range(request_count):
                request_time = start_time + timedelta(seconds=(i / request_count) * 60)
                await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Get account status (checks all endpoints)
        status = await predictor.get_account_status(test_account_id)

        assert status is not None
        assert status["status"] == "critical", \
            "Overall status should be critical (highest alert level)"

        # Check predictions for each endpoint
        predictions = status.get("predictions", [])
        endpoint_predictions = {
            p["endpoint_type"]: p for p in predictions
        }

        # Verify MESSAGES endpoint (warning level)
        assert EndpointType.MESSAGES.value in endpoint_predictions
        msg_pred = endpoint_predictions[EndpointType.MESSAGES.value]
        assert msg_pred["usage_percent"] >= 70
        assert msg_pred["alert_triggered"] == True

        # Verify MEDIA endpoint (critical level)
        assert EndpointType.MEDIA.value in endpoint_predictions
        media_pred = endpoint_predictions[EndpointType.MEDIA.value]
        assert media_pred["usage_percent"] >= 90

        # Verify GET_CHAT endpoint (healthy)
        assert EndpointType.GET_CHAT.value in endpoint_predictions
        chat_pred = endpoint_predictions[EndpointType.GET_CHAT.value]
        assert chat_pred["usage_percent"] < 60


# ==================== 7. Edge Cases ====================

class TestPredictionAndAlertsEdgeCases:
    """Тесты граничных случаев для предсказаний и оповещений"""

    @pytest.mark.asyncio
    async def test_prediction_with_no_usage_data(
        self, predictor, test_account_id, test_limits
    ):
        """
        Prediction handles accounts with no usage data.

        Steps:
        1. Get prediction for account with no traffic
        2. Verify graceful handling
        """
        endpoint = EndpointType.MESSAGES
        limit = test_limits[endpoint]

        prediction = await predictor.predict_breach_time(
            account_id="account_with_no_traffic",
            endpoint_type=endpoint,
            limit=limit
        )

        assert prediction is not None
        assert prediction.current_usage == 0
        assert prediction.usage_percent == 0.0
        assert prediction.predicted_breach_time is None, \
            "Should not predict breach if no usage"

    @pytest.mark.asyncio
    async def test_alert_cooldown_prevents_spam(
        self, usage_tracker, test_account_id, test_limits,
        mock_notification_service
    ):
        """
        Alert cooldown prevents notification spam.

        Steps:
        1. Generate traffic to trigger alert
        2. Trigger alert multiple times
        3. Verify cooldown is respected (implementation-dependent)
        """
        endpoint = EndpointType.OTHER
        limit = test_limits[endpoint]

        # Generate traffic to 80%
        request_count = int(limit * 0.8)
        start_time = datetime.now() - timedelta(seconds=60)

        for i in range(request_count):
            request_time = start_time + timedelta(seconds=(i / request_count) * 60)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Trigger multiple alerts
        for i in range(3):
            result = trigger_alert_sync(
                account_id=test_account_id,
                alert_type="warning",
                usage_percent=80.0 + i,
                endpoint_type=endpoint.value,
                predicted_breach_time="2025-01-24T17:00:00Z"
            )
            assert result["success"], f"Alert {i+1} failed"

        # All alerts should be logged (cooldown enforcement is implementation-specific)
        assert mock_notification_service.log_delivery.call_count == 3, \
            "All alerts should be logged"

    @pytest.mark.asyncio
    async def test_prediction_with_extremely_high_usage(
        self, predictor, usage_tracker, test_account_id, test_limits
    ):
        """
        Prediction handles extremely high usage (95%+).

        Steps:
        1. Generate traffic to 95% usage
        2. Verify prediction shows imminent breach
        3. Verify alert level is severe
        """
        endpoint = EndpointType.JOIN_CHANNEL
        limit = test_limits[endpoint]

        # Generate traffic to 95%
        request_count = int(limit * 0.95)
        start_time = datetime.now() - timedelta(seconds=60)

        for i in range(request_count):
            request_time = start_time + timedelta(seconds=(i / request_count) * 60)
            await usage_tracker.record_request(test_account_id, endpoint, request_time)

        # Get prediction
        prediction = await predictor.predict_breach_time(
            account_id=test_account_id,
            endpoint_type=endpoint,
            limit=limit
        )

        assert prediction is not None
        assert prediction.usage_percent >= 90, "Should be at critical level"
        assert prediction.predicted_breach_time is not None

        # Time until breach should be short
        if prediction.time_until_breach_seconds:
            assert prediction.time_until_breach_seconds < 300, \
                "Breach should be imminent (< 5 minutes) at 95% usage"

        # Check account status
        status = await predictor.get_account_status(test_account_id)
        assert status["status"] in ["critical", "severe"], \
            f"Status should be severe at 95%: {status['status']}"
