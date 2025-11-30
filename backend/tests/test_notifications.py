import os
from tasks.notifications import notify_admins_async
from unittest.mock import patch

def test_notify_admins_dev_mode(monkeypatch):
    # Ensure no broker configured
    monkeypatch.delenv('CELERY_BROKER_URL', raising=False)
    
    # Mock the sync function to avoid DB access
    with patch('tasks.notifications.send_admin_notification_sync') as mock_sync:
        mock_sync.return_value = True
        result = notify_admins_async('fake-user-id')
        assert result is True
        mock_sync.assert_called_once_with('fake-user-id')


def test_notify_admins_when_broker_present_but_celery_missing(monkeypatch):
    # If broker set but Celery not installed, notify_admins should gracefully return True
    monkeypatch.setenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    # Force CELERY_AVAILABLE to False to simulate missing celery package
    import importlib
    mod = importlib.import_module('tasks.notifications')
    monkeypatch.setattr(mod, 'CELERY_AVAILABLE', False)
    
    # Mock the sync function to avoid DB access
    with patch('tasks.notifications.send_admin_notification_sync') as mock_sync:
        mock_sync.return_value = True
        res = notify_admins_async('u-123')
        assert res is True
        mock_sync.assert_called_once_with('u-123')


def test_send_admin_notification_for_user_sends(monkeypatch):
    # Simulate env for email and telegram
    monkeypatch.setenv('ADMIN_NOTIFICATION_EMAILS', 'admin1@example.com, admin2@example.com')
    monkeypatch.setenv('SMTP_HOST', 'smtp.test')
    monkeypatch.setenv('SMTP_USER', 'u')
    monkeypatch.setenv('SMTP_PASS', 'p')
    monkeypatch.setenv('SMTP_FROM', 'no-reply@test')
    monkeypatch.setenv('SMTP_PORT', '1025')
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'fake-token')
    monkeypatch.setenv('TELEGRAM_ADMIN_CHAT_IDS', '111,222')

    # Mock FastMail send_message
    class DummyFM:
        def __init__(self, config):
            self.config = config

        def send_message(self, message):
            # pretend to send
            return True

    import sys
    import types
    fastapi_mail = types.SimpleNamespace(FastMail=lambda config: DummyFM(config), MessageSchema=lambda **kwargs: kwargs)
    monkeypatch.setitem(sys.modules, 'fastapi_mail', fastapi_mail)

    # Mock requests.post
    import requests
    def fake_post(url, json=None):
        class R:
            status_code = 200

        return R()

    monkeypatch.setattr('requests.post', fake_post)

    # Build a fake user object
    user = types.SimpleNamespace(email='new@example.com', id='u-42')
    from tasks.notifications import send_admin_notification_for_user

    res = send_admin_notification_for_user(user)
    assert res is True
