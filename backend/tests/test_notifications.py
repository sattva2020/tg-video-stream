import os
from tasks.notifications import notify_admins_async


def test_notify_admins_dev_mode(monkeypatch):
    # Ensure no broker configured
    monkeypatch.delenv('CELERY_BROKER_URL', raising=False)
    result = notify_admins_async('fake-user-id')
    assert result is True


def test_notify_admins_when_broker_present_but_celery_missing(monkeypatch):
    # If broker set but Celery not installed, notify_admins should gracefully return True
    monkeypatch.setenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    # Force CELERY_AVAILABLE to False to simulate missing celery package
    import importlib
    mod = importlib.import_module('tasks.notifications')
    monkeypatch.setattr(mod, 'CELERY_AVAILABLE', False)
    res = notify_admins_async('u-123')
    assert res is True
