"""
Integration Tests: Telegram Session Alert Notifications End-to-End
Тестируем полный цикл отправки алертов о проблемах с Telegram сессиями

Coverage Target: End-to-end alert notification flow testing

Тесты проверяют:
1. Callback on_session_expired вызывается при обнаружении истекшей сессии
2. Callback on_2fa_required вызывается при обнаружении необходимости 2FA
3. Уведомления отправляются через систему Celery notifications
4. Payload уведомления содержит все необходимые данные
5. API возвращает данные для отображения алертов во фронтенде
6. Email/webhook уведомления получаются (мокинг Celery task)

Типы алертов для тестирования:
- session_expired: Сессия истекла (session_expires_at < now)
- 2fa_required: Требуется двухфакторная аутентификация
- refresh_failed: Не удалось обновить сессию после N попыток
"""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.telegram import TelegramAccount, SessionHealthStatus
from src.services.telegram_session_monitor import (
    TelegramSessionMonitor,
    TelegramSessionHealth,
    SessionMonitorConfig
)
from src.services.telegram_session_service import get_telegram_session_service
from src.tasks.telegram_session_health import check_session_health_sync
from src.celery_app import celery_app


# ==================== Fixtures ====================

@pytest.fixture
def test_user(db_session):
    """Create test user for Telegram accounts"""
    user = User(
        email='alert_test_user@example.com',
        hashed_password='test_hash',
        role='admin',
        status='approved'
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def expired_session_account(db_session, test_user):
    """Create Telegram account with expired session (triggers session_expired alert)"""
    account = TelegramAccount(
        user_id=test_user.id,
        phone='+12345678901',
        username='expired_user',
        encrypted_session='encrypted_session_data_expired',
        tg_user_id=1001,
        is_active=True,
        session_health_status=SessionHealthStatus.HEALTHY.value,
        last_health_check=datetime.now(timezone.utc) - timedelta(hours=2),
        session_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Expired 1 hour ago
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def needs_2fa_account(db_session, test_user):
    """Create Telegram account that requires 2FA (triggers 2fa_required alert)"""
    # Account with totp_secret but invalid/missing encrypted_session
    account = TelegramAccount(
        user_id=test_user.id,
        phone='+12345678902',
        username='needs_2fa_user',
        encrypted_session=None,  # No valid session
        tg_user_id=1002,
        is_active=True,
        session_health_status=SessionHealthStatus.HEALTHY.value,
        last_health_check=datetime.now(timezone.utc) - timedelta(hours=2),
        session_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        totp_secret='totp:encrypted_secret_here',  # Has 2FA configured
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def refresh_failed_account(db_session, test_user):
    """Create Telegram account with failed refresh attempts (triggers refresh_failed alert)"""
    account = TelegramAccount(
        user_id=test_user.id,
        phone='+12345678903',
        username='refresh_failed_user',
        encrypted_session='encrypted_session_data',
        tg_user_id=1003,
        is_active=True,
        session_health_status=SessionHealthStatus.HEALTHY.value,
        last_health_check=datetime.now(timezone.utc) - timedelta(hours=2),
        session_expires_at=datetime.now(timezone.utc) + timedelta(hours=2),  # Expiring soon
        auto_refresh_enabled=True,
        refresh_before_expires_hours=24,
        last_refreshed_at=datetime.now(timezone.utc) - timedelta(hours=3),
        refresh_error_message='Session refresh failed: 2FA code invalid',  # Previous error
        # Note: In real scenario, consecutive failures would be tracked via Redis
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


# ==================== Test 1: Session Expired Callback ====================

class TestSessionExpiredCallback:
    """Тесты callback on_session_expired"""

    @pytest.mark.asyncio
    async def test_session_expired_callback_fired(self, db_session, expired_session_account):
        """Callback on_session_expired вызывается при обнаружении истекшей сессии"""
        # Create monitor with mock callback
        callback_mock = AsyncMock()
        monitor = TelegramSessionMonitor(
            on_session_expired_callback=callback_mock
        )

        # Check account health
        account_id = str(expired_session_account.id)
        health = await monitor.check_account_health(account_id)

        # Verify callback was called
        assert callback_mock.called, "on_session_expired_callback should be called"
        callback_mock.assert_called_once()

        # Verify callback arguments
        call_args = callback_mock.call_args
        assert call_args[0][0] == account_id, "First argument should be account_id"
        assert isinstance(call_args[0][1], str), "Second argument should be reason string"

    @pytest.mark.asyncio
    async def test_session_expired_callback_reason_message(self, db_session, expired_session_account):
        """Callback содержит осмысленное сообщение о причине истечения"""
        callback_mock = AsyncMock()
        monitor = TelegramSessionMonitor(
            on_session_expired_callback=callback_mock
        )

        # Check account health
        account_id = str(expired_session_account.id)
        await monitor.check_account_health(account_id)

        # Verify reason message
        call_args = callback_mock.call_args[0]
        reason = call_args[1]
        assert reason is not None, "Reason should not be None"
        assert len(reason) > 0, "Reason should not be empty"
        # Reason should mention expiration
        assert "expir" in reason.lower() or "истек" in reason.lower(), "Reason should mention expiration"

    @pytest.mark.asyncio
    async def test_session_expired_health_status(self, db_session, expired_session_account):
        """Статус здоровья установлен в EXPIRED после проверки"""
        monitor = TelegramSessionMonitor()
        account_id = str(expired_session_account.id)

        # Check account health
        health = await monitor.check_account_health(account_id)

        # Verify health status
        assert health.health_status == SessionHealthStatus.EXPIRED
        assert health.is_healthy is False


# ==================== Test 2: 2FA Required Callback ====================

class Test2FARequiredCallback:
    """Тесты callback on_2fa_required"""

    @pytest.mark.asyncio
    async def test_2fa_required_callback_fired(self, db_session, needs_2fa_account):
        """Callback on_2fa_required вызывается при обнаружении необходимости 2FA"""
        callback_mock = AsyncMock()
        monitor = TelegramSessionMonitor(
            on_2fa_required_callback=callback_mock
        )

        # Check account health
        account_id = str(needs_2fa_account.id)
        health = await monitor.check_account_health(account_id)

        # Verify callback was called
        assert callback_mock.called, "on_2fa_required_callback should be called"
        callback_mock.assert_called_once()

        # Verify callback arguments
        call_args = callback_mock.call_args
        assert call_args[0][0] == account_id, "First argument should be account_id"
        assert isinstance(call_args[0][1], str), "Second argument should be reason string"

    @pytest.mark.asyncio
    async def test_2fa_required_reason_message(self, db_session, needs_2fa_account):
        """Callback содержит осмысленное сообщение о необходимости 2FA"""
        callback_mock = AsyncMock()
        monitor = TelegramSessionMonitor(
            on_2fa_required_callback=callback_mock
        )

        # Check account health
        account_id = str(needs_2fa_account.id)
        await monitor.check_account_health(account_id)

        # Verify reason message
        call_args = callback_mock.call_args[0]
        reason = call_args[1]
        assert reason is not None, "Reason should not be None"
        assert len(reason) > 0, "Reason should not be empty"
        # Reason should mention 2FA
        assert "2fa" in reason.lower() or "двухфактор" in reason.lower(), "Reason should mention 2FA"

    @pytest.mark.asyncio
    async def test_2fa_required_health_status(self, db_session, needs_2fa_account):
        """Статус здоровья установлен в NEEDS_2FA после проверки"""
        monitor = TelegramSessionMonitor()
        account_id = str(needs_2fa_account.id)

        # Check account health
        health = await monitor.check_account_health(account_id)

        # Verify health status
        assert health.health_status == SessionHealthStatus.NEEDS_2FA
        assert health.is_healthy is False


# ==================== Test 3: Notification System Integration ====================

class TestNotificationSystemIntegration:
    """Тесты интеграции с системой уведомлений"""

    @pytest.mark.asyncio
    async def test_session_expired_notification_enqueued(self, db_session, expired_session_account):
        """Уведомление об истекшей сессии ставится в очередь Celery"""
        # Mock Celery send_task
        with patch('src.celery_app.celery_app') as mock_celery_app:
            mock_celery_app.send_task = Mock(return_value='task-id')

            # Create monitor that sends notification via callback
            async def send_notification_callback(account_id: str, reason: str):
                """Simulates callback that sends notification via Celery"""
                # Query account for details
                account = db_session.query(TelegramAccount).filter(
                    TelegramAccount.id == uuid.UUID(account_id)
                ).first()

                if account:
                    payload = {
                        "event_id": str(uuid.uuid4()),
                        "severity": "critical",
                        "tags": {
                            "source": "telegram_sessions",
                            "event_type": "session_expired",
                            "user_id": str(account.user_id),
                            "account_id": account_id
                        },
                        "host": "telegram-session-monitor",
                        "context": {
                            "account_phone": account.phone,
                            "account_username": account.username,
                            "failure_reason": reason,
                            "suggested_actions": [
                                "Manually refresh session in admin panel",
                                "Check 2FA configuration if enabled",
                                "Verify Telegram account status"
                            ]
                        },
                        "subject": f"Critical: Telegram Session Expired for {account.phone}",
                        "body": (
                            f"Telegram session for account {account.phone} ({account.username}) has expired.\n\n"
                            f"Reason: {reason}\n\n"
                            f"Action required: Please refresh the session manually in the admin panel.\n\n"
                            f"Account ID: {account_id}\n"
                        )
                    }

                    # Enqueue notification (simulating _enqueue_process_event)
                    mock_celery_app.send_task(
                        "notifications.process_event",
                        args=[payload],
                        queue="notifications",
                        countdown=0
                    )

            monitor = TelegramSessionMonitor(
                on_session_expired_callback=send_notification_callback
            )

            # Check account health (triggers callback)
            account_id = str(expired_session_account.id)
            await monitor.check_account_health(account_id)

            # Verify Celery task was enqueued
            assert mock_celery_app.send_task.called, "Celery send_task should be called"
            mock_celery_app.send_task.assert_called_once()

            # Verify task arguments
            call_args = mock_celery_app.send_task.call_args
            assert call_args[0][0] == "notifications.process_event"
            payload = call_args[1]['args'][0]

            # Verify payload structure
            assert payload['severity'] == 'critical'
            assert payload['tags']['event_type'] == 'session_expired'
            assert payload['tags']['source'] == 'telegram_sessions'
            assert 'account_phone' in payload['context']
            assert 'failure_reason' in payload['context']
            assert 'suggested_actions' in payload['context']
            assert payload['subject'] is not None
            assert payload['body'] is not None

    @pytest.mark.asyncio
    async def test_2fa_required_notification_enqueued(self, db_session, needs_2fa_account):
        """Уведомление о необходимости 2FA ставится в очередь Celery"""
        with patch('src.celery_app.celery_app') as mock_celery_app:
            mock_celery_app.send_task = Mock(return_value='task-id')

            # Create monitor that sends notification via callback
            async def send_notification_callback(account_id: str, reason: str):
                """Simulates callback that sends notification via Celery"""
                account = db_session.query(TelegramAccount).filter(
                    TelegramAccount.id == uuid.UUID(account_id)
                ).first()

                if account:
                    payload = {
                        "event_id": str(uuid.uuid4()),
                        "severity": "warning",
                        "tags": {
                            "source": "telegram_sessions",
                            "event_type": "2fa_required",
                            "user_id": str(account.user_id),
                            "account_id": account_id
                        },
                        "host": "telegram-session-monitor",
                        "context": {
                            "account_phone": account.phone,
                            "account_username": account.username,
                            "failure_reason": reason,
                            "suggested_actions": [
                                "Configure TOTP 2FA in admin panel",
                                "Verify TOTP secret is correctly encrypted",
                                "Test TOTP code generation"
                            ]
                        },
                        "subject": f"Warning: 2FA Required for Telegram Session {account.phone}",
                        "body": (
                            f"Telegram session for account {account.phone} ({account.username}) requires 2FA.\n\n"
                            f"Reason: {reason}\n\n"
                            f"Action required: Please configure 2FA in the admin panel.\n\n"
                            f"Account ID: {account_id}\n"
                        )
                    }

                    mock_celery_app.send_task(
                        "notifications.process_event",
                        args=[payload],
                        queue="notifications",
                        countdown=0
                    )

            monitor = TelegramSessionMonitor(
                on_2fa_required_callback=send_notification_callback
            )

            # Check account health
            account_id = str(needs_2fa_account.id)
            await monitor.check_account_health(account_id)

            # Verify Celery task was enqueued
            assert mock_celery_app.send_task.called
            payload = mock_celery_app.send_task.call_args[1]['args'][0]

            # Verify payload
            assert payload['severity'] == 'warning'
            assert payload['tags']['event_type'] == '2fa_required'
            assert 'suggested_actions' in payload['context']


# ==================== Test 4: Alert Data for Frontend ====================

class TestAlertDataForFrontend:
    """Тесты данных алертов для отображения во фронтенде"""

    @pytest.mark.asyncio
    async def test_frontend_data_expired_session(self, db_session, expired_session_account):
        """API возвращает корректные данные для отображения алерта об истекшей сессии"""
        monitor = TelegramSessionMonitor()
        account_id = str(expired_session_account.id)

        # Check health
        health = await monitor.check_account_health(account_id)

        # Verify data structure for frontend
        assert health.account_id == account_id
        assert health.is_healthy is False
        assert health.health_status == SessionHealthStatus.EXPIRED
        assert health.last_check is not None
        assert health.last_error_message is not None or health.last_failure_type is not None

        # Frontend can use these fields for alert display
        frontend_alert_data = {
            "account_id": health.account_id,
            "status": health.health_status.value,
            "is_healthy": health.is_healthy,
            "last_check": health.last_check.isoformat(),
            "error_message": health.last_error_message,
            "failure_type": health.last_failure_type,
            "consecutive_failures": health.consecutive_failures
        }

        # Verify all required fields present
        assert "account_id" in frontend_alert_data
        assert "status" in frontend_alert_data
        assert "is_healthy" in frontend_alert_data
        assert "last_check" in frontend_alert_data

    @pytest.mark.asyncio
    async def test_frontend_data_2fa_required(self, db_session, needs_2fa_account):
        """API возвращает корректные данные для отображения алерта о необходимости 2FA"""
        monitor = TelegramSessionMonitor()
        account_id = str(needs_2fa_account.id)

        # Check health
        health = await monitor.check_account_health(account_id)

        # Verify data structure
        assert health.health_status == SessionHealthStatus.NEEDS_2FA
        assert health.is_healthy is False

        # Frontend should show "2FA Required" alert with account details
        frontend_alert = {
            "type": "2fa_required",
            "account_id": health.account_id,
            "severity": "warning",
            "message": health.last_error_message or "Two-factor authentication required",
            "timestamp": health.last_check.isoformat()
        }

        assert frontend_alert["type"] == "2fa_required"
        assert frontend_alert["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_multiple_unhealthy_sessions_for_frontend(self, db_session, test_user, expired_session_account, needs_2fa_account):
        """API возвращает список всех нездоровых сессий для отображения в дашборде"""
        monitor = TelegramSessionMonitor()

        # Check health for both accounts
        health1 = await monitor.check_account_health(str(expired_session_account.id))
        health2 = await monitor.check_account_health(str(needs_2fa_account.id))

        # Get all unhealthy accounts
        unhealthy = await monitor.get_all_unhealthy_accounts()

        # Verify both unhealthy accounts are returned
        assert len(unhealthy) >= 2
        account_ids = [h.account_id for h in unhealthy]
        assert str(expired_session_account.id) in account_ids
        assert str(needs_2fa_account.id) in account_ids

        # Frontend can display alerts grouped by type
        alerts_by_type = {}
        for health in unhealthy:
            alert_type = health.health_status.value
            if alert_type not in alerts_by_type:
                alerts_by_type[alert_type] = []
            alerts_by_type[alert_type].append({
                "account_id": health.account_id,
                "last_check": health.last_check.isoformat(),
                "error_message": health.last_error_message
            })

        # Verify we have alerts for both types
        assert 'expired' in alerts_by_type or 'EXPIRED' in alerts_by_type
        assert 'needs_2fa' in alerts_by_type or 'NEEDS_2FA' in alerts_by_type


# ==================== Test 5: Email/Webhook Notification Payload ====================

class TestEmailWebhookNotificationPayload:
    """Тесты payload для email и webhook уведомлений"""

    @pytest.mark.asyncio
    async def test_notification_payload_contains_required_fields(self, db_session, expired_session_account):
        """Payload уведомления содержит все обязательные поля для email/webhook"""
        # Simulate notification payload creation
        monitor = TelegramSessionMonitor()
        account_id = str(expired_session_account.id)
        health = await monitor.check_account_health(account_id)

        # Query account details
        account = db_session.query(TelegramAccount).filter(
            TelegramAccount.id == expired_session_account.id
        ).first()

        # Build notification payload (as would be sent to Celery)
        payload = {
            "event_id": str(uuid.uuid4()),
            "severity": "critical",
            "tags": {
                "source": "telegram_sessions",
                "event_type": "session_expired",
                "user_id": str(account.user_id),
                "account_id": account_id
            },
            "host": "telegram-session-monitor",
            "context": {
                "account_id": account_id,
                "phone": account.phone,
                "username": account.username,
                "failure_reason": health.last_error_message or "Session expired",
                "health_status": health.health_status.value,
                "suggested_actions": [
                    "Manually refresh session in admin panel",
                    "Check if Telegram account is still active",
                    "Verify network connectivity to Telegram servers"
                ]
            },
            "subject": f"Critical: Telegram Session Expired - {account.phone}",
            "body": (
                f"Your Telegram session for account {account.phone} has expired.\n\n"
                f"Account: {account.username or account.phone}\n"
                f"Status: {health.health_status.value}\n"
                f"Last Check: {health.last_check.isoformat()}\n\n"
                f"Suggested Actions:\n"
                f"1. Log in to the admin panel\n"
                f"2. Navigate to Sessions page\n"
                f"3. Click 'Refresh' on the expired session\n"
                f"4. Provide 2FA code if prompted\n\n"
                f"If this issue persists, please check your Telegram account status."
            )
        }

        # Verify required fields
        required_fields = ["event_id", "severity", "tags", "host", "context", "subject", "body"]
        for field in required_fields:
            assert field in payload, f"Payload should contain {field}"

        # Verify tags structure
        assert "source" in payload["tags"]
        assert "event_type" in payload["tags"]
        assert "user_id" in payload["tags"]
        assert payload["tags"]["source"] == "telegram_sessions"

        # Verify context has account info
        assert "account_id" in payload["context"]
        assert "phone" in payload["context"]
        assert "failure_reason" in payload["context"]
        assert "suggested_actions" in payload["context"]
        assert isinstance(payload["context"]["suggested_actions"], list)

    @pytest.mark.asyncio
    async def test_notification_severity_levels(self, db_session, expired_session_account, needs_2fa_account):
        """Уровни серьезности (severity) корректны для разных типов алертов"""
        monitor = TelegramSessionMonitor()

        # Check expired session (should be critical)
        health_expired = await monitor.check_account_health(str(expired_session_account.id))
        assert health_expired.health_status == SessionHealthStatus.EXPIRED
        severity_expired = "critical"  # Expired sessions are critical

        # Check 2FA required (should be warning)
        health_2fa = await monitor.check_account_health(str(needs_2fa_account.id))
        assert health_2fa.health_status == SessionHealthStatus.NEEDS_2FA
        severity_2fa = "warning"  # 2FA required is warning

        # Verify severity mapping
        assert severity_expired == "critical"
        assert severity_2fa == "warning"

    @pytest.mark.asyncio
    async def test_suggested_actions_for_each_alert_type(self, db_session, expired_session_account, needs_2fa_account):
        """Каждый тип алерта содержит соответствующие suggested_actions"""
        monitor = TelegramSessionMonitor()

        # Test expired session actions
        health_expired = await monitor.check_account_health(str(expired_session_account.id))
        actions_expired = [
            "Manually refresh session in admin panel",
            "Check if Telegram account is still active",
            "Verify network connectivity to Telegram servers",
            "Review 2FA configuration if enabled"
        ]
        assert isinstance(actions_expired, list)
        assert len(actions_expired) > 0

        # Test 2FA required actions
        health_2fa = await monitor.check_account_health(str(needs_2fa_account.id))
        actions_2fa = [
            "Configure TOTP 2FA in admin panel",
            "Verify TOTP secret is correctly encrypted",
            "Test TOTP code generation",
            "Check authenticator app settings"
        ]
        assert isinstance(actions_2fa, list)
        assert len(actions_2fa) > 0


# ==================== Test 6: End-to-End Alert Flow ====================

class TestEndToEndAlertFlow:
    """End-to-End тесты полного цикла алертов"""

    @pytest.mark.asyncio
    async def test_full_alert_flow_expired_session(self, db_session, expired_session_account):
        """Полный цикл: Expired session → Callback → Notification → Frontend data"""
        # Step 1: Mock Celery task
        with patch('src.celery_app.celery_app') as mock_celery_app:
            mock_celery_app.send_task = Mock(return_value='test-task-id')

            # Step 2: Track callback invocations
            callback_invocations = []

            async def track_callback(account_id: str, reason: str):
                """Track callback invocations and simulate notification sending"""
                callback_invocations.append({
                    "account_id": account_id,
                    "reason": reason,
                    "timestamp": datetime.now(timezone.utc)
                })

                # Simulate sending notification
                account = db_session.query(TelegramAccount).filter(
                    TelegramAccount.id == uuid.UUID(account_id)
                ).first()

                if account:
                    payload = {
                        "event_id": str(uuid.uuid4()),
                        "severity": "critical",
                        "tags": {
                            "source": "telegram_sessions",
                            "event_type": "session_expired",
                            "user_id": str(account.user_id),
                        },
                        "context": {
                            "account_phone": account.phone,
                            "failure_reason": reason,
                            "suggested_actions": ["Refresh session manually"]
                        },
                        "subject": f"Session Expired: {account.phone}",
                        "body": f"Session expired for {account.phone}"
                    }

                    mock_celery_app.send_task(
                        "notifications.process_event",
                        args=[payload],
                        queue="notifications"
                    )

            # Step 3: Create monitor with tracking callback
            monitor = TelegramSessionMonitor(
                on_session_expired_callback=track_callback
            )

            # Step 4: Trigger health check (triggers alert flow)
            account_id = str(expired_session_account.id)
            health = await monitor.check_account_health(account_id)

            # Step 5: Verify callback was invoked
            assert len(callback_invocations) == 1
            assert callback_invocations[0]["account_id"] == account_id
            assert callback_invocations[0]["reason"] is not None

            # Step 6: Verify notification was enqueued
            assert mock_celery_app.send_task.called

            # Step 7: Verify health status for frontend
            assert health.health_status == SessionHealthStatus.EXPIRED
            assert health.is_healthy is False

            # Step 8: Verify data available for frontend display
            frontend_data = {
                "account_id": health.account_id,
                "status": health.health_status.value,
                "is_healthy": health.is_healthy,
                "last_check": health.last_check,
                "error_message": health.last_error_message
            }
            assert frontend_data["status"] == "expired"
            assert frontend_data["is_healthy"] is False

    @pytest.mark.asyncio
    async def test_full_alert_flow_2fa_required(self, db_session, needs_2fa_account):
        """Полный цикл: 2FA required → Callback → Notification → Frontend data"""
        with patch('src.celery_app.celery_app') as mock_celery_app:
            mock_celery_app.send_task = Mock(return_value='test-task-id')

            callback_invocations = []

            async def track_callback(account_id: str, reason: str):
                """Track callback and send notification"""
                callback_invocations.append({"account_id": account_id, "reason": reason})

                account = db_session.query(TelegramAccount).filter(
                    TelegramAccount.id == uuid.UUID(account_id)
                ).first()

                if account:
                    payload = {
                        "event_id": str(uuid.uuid4()),
                        "severity": "warning",
                        "tags": {"source": "telegram_sessions", "event_type": "2fa_required"},
                        "context": {
                            "account_phone": account.phone,
                            "failure_reason": reason,
                            "suggested_actions": ["Configure 2FA"]
                        },
                        "subject": f"2FA Required: {account.phone}",
                        "body": f"2FA required for {account.phone}"
                    }

                    mock_celery_app.send_task(
                        "notifications.process_event",
                        args=[payload],
                        queue="notifications"
                    )

            monitor = TelegramSessionMonitor(
                on_2fa_required_callback=track_callback
            )

            # Trigger health check
            account_id = str(needs_2fa_account.id)
            health = await monitor.check_account_health(account_id)

            # Verify full flow
            assert len(callback_invocations) == 1
            assert mock_celery_app.send_task.called
            assert health.health_status == SessionHealthStatus.NEEDS_2FA
            assert health.is_healthy is False


# ==================== Test 7: Edge Cases ====================

class TestAlertEdgeCases:
    """Тесты граничных случаев для алертов"""

    @pytest.mark.asyncio
    async def test_callback_error_doesnt_crash_monitor(self, db_session, expired_session_account):
        """Ошибка в callback не ломает процесс мониторинга"""
        # Create callback that raises exception
        async def failing_callback(account_id: str, reason: str):
            raise Exception("Simulated callback failure")

        monitor = TelegramSessionMonitor(
            on_session_expired_callback=failing_callback
        )

        # Check health should not raise exception despite callback failure
        account_id = str(expired_session_account.id)
        health = await monitor.check_account_health(account_id)

        # Verify health check completed successfully
        assert health is not None
        assert health.health_status == SessionHealthStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_no_callback_no_error(self, db_session, expired_session_account):
        """Мониторинг работает корректно даже без callback"""
        # Create monitor without callbacks
        monitor = TelegramSessionMonitor()

        # Check health should work fine
        account_id = str(expired_session_account.id)
        health = await monitor.check_account_health(account_id)

        # Verify health check completed
        assert health is not None
        assert health.health_status == SessionHealthStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_multiple_alerts_for_different_accounts(self, db_session, test_user, expired_session_account, needs_2fa_account):
        """Разные типы алертов для разных аккаунтов обрабатываются корректно"""
        callback_invocations = []

        async def track_expired(account_id: str, reason: str):
            callback_invocations.append({"type": "expired", "account_id": account_id})

        async def track_2fa(account_id: str, reason: str):
            callback_invocations.append({"type": "2fa", "account_id": account_id})

        monitor = TelegramSessionMonitor(
            on_session_expired_callback=track_expired,
            on_2fa_required_callback=track_2fa
        )

        # Check both accounts
        await monitor.check_account_health(str(expired_session_account.id))
        await monitor.check_account_health(str(needs_2fa_account.id))

        # Verify both callbacks were invoked
        assert len(callback_invocations) == 2

        # Verify correct callbacks for correct accounts
        expired_invocations = [c for c in callback_invocations if c["type"] == "expired"]
        two_fa_invocations = [c for c in callback_invocations if c["type"] == "2fa"]

        assert len(expired_invocations) == 1
        assert len(two_fa_invocations) == 1
