"""CRUD и worker-тесты для уведомлений (T029/T035)."""
import uuid
from importlib import reload
from typing import Callable, Dict, Tuple

import pytest

from src.services.notifications.base import NotificationService
from src.schemas.notifications import (
    NotificationChannelCreate,
    NotificationRecipientCreate,
    NotificationRuleCreate,
    NotificationTemplateCreate,
)


@pytest.fixture
def worker_task(monkeypatch):
    """Возвращает (control, run, module) для вызова Celery-задачи напрямую без брокера."""

    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost/0")
    import src.services.notifications.worker as worker_module

    reload(worker_module)

    result = {"success": True}

    class FakeApprise:
        def __init__(self):
            self.urls = []

        def add(self, url: str):
            self.urls.append(url)

        def notify(self, body: str, title=None):
            return result["success"]

    # Переопределяем Apprise и таймаутный вызов
    monkeypatch.setattr(worker_module, "Apprise", FakeApprise)

    def fake_notify_with_timeout(app, *, body: str, title: str, timeout: int):
        return app.notify(body, title)

    monkeypatch.setattr(worker_module, "_notify_with_timeout", fake_notify_with_timeout)

    def run(payload: Dict):
        return worker_module.process_notification.run(payload)

    return result, run, worker_module


@pytest.fixture
def seeded_entities(db_session):
    service = NotificationService(db_session)
    channel = service.create_channel(
        NotificationChannelCreate(
            name="Email-" + uuid.uuid4().hex[:6],
            type="email",
            config={"apprise_url": "mailto://user:pass@mail.test"},
        )
    )
    recipient = service.create_recipient(
        NotificationRecipientCreate(type="email", address="user@example.com", status="active")
    )
    template = service.create_template(
        NotificationTemplateCreate(name="T1", locale="en", body="Hi {name}")
    )
    rule = service.create_rule(
        NotificationRuleCreate(
            name="R1-" + uuid.uuid4().hex[:4],
            recipient_ids=[recipient.id],
            channel_ids=[channel.id],
            template_id=template.id,
            dedup_window_sec=0,
        )
    )
    return service, channel, recipient, template, rule


def test_channels_templates_rules_crud_flow(client, db_session):
    service = NotificationService(db_session)

    # Канал
    channel_resp = client.post(
        "/api/notifications/channels",
        json={"name": "Webhook-" + uuid.uuid4().hex[:4], "type": "webhook", "config": {"url": "http://t"}},
    )
    assert channel_resp.status_code == 201
    channel_id = channel_resp.json()["id"]

    # Обновление включенности
    upd = client.patch(f"/api/notifications/channels/{channel_id}", json={"enabled": False})
    assert upd.status_code == 200
    assert upd.json()["enabled"] is False

    # Шаблон
    template_resp = client.post(
        "/api/notifications/templates",
        json={"name": "AlertTpl", "locale": "ru", "body": "Привет"},
    )
    assert template_resp.status_code == 201
    template_id = template_resp.json()["id"]

    # Получатель
    recipient = service.create_recipient(
        NotificationRecipientCreate(type="email", address="flow@example.com", status="active")
    )

    # Правило
    rule_resp = client.post(
        "/api/notifications/rules",
        json={
            "name": "Rule-" + uuid.uuid4().hex[:4],
            "recipient_ids": [str(recipient.id)],
            "channel_ids": [channel_id],
            "template_id": template_id,
            "dedup_window_sec": 0,
            "failover_timeout_sec": 0,
        },
    )
    assert rule_resp.status_code == 201
    rule_id = rule_resp.json()["id"]
    assert rule_resp.json()["channel_ids"] == [channel_id]
    assert rule_resp.json()["recipient_ids"] == [str(recipient.id)]

    # Удаление
    del_rule = client.delete(f"/api/notifications/rules/{rule_id}")
    del_tpl = client.delete(f"/api/notifications/templates/{template_id}")
    del_channel = client.delete(f"/api/notifications/channels/{channel_id}")
    assert del_rule.status_code == 204
    assert del_tpl.status_code == 204
    assert del_channel.status_code == 204


def _last_status(service: NotificationService, event_id: str):
    logs = service.list_logs(event_id=event_id, limit=5)
    return logs[0].status if logs else None


def test_worker_success_and_fail(monkeypatch, db_session, seeded_entities, worker_task):
    control, run_task, worker_module = worker_task
    service, channel, recipient, template, rule = seeded_entities

    event_id_ok = "evt-success"
    payload = {
        "event_id": event_id_ok,
        "rule_id": str(rule.id),
        "channel_id": str(channel.id),
        "recipient_id": str(recipient.id),
        "context": {"name": "Alice"},
    }
    control["success"] = True
    assert run_task(payload) is True
    assert _last_status(service, event_id_ok) == "success"

    # Ошибка доставки
    event_id_fail = "evt-fail"
    control["success"] = False
    payload["event_id"] = event_id_fail
    assert run_task(payload) is False
    assert _last_status(service, event_id_fail) == "fail"


def test_worker_suppressed_and_dedup(monkeypatch, db_session, worker_task):
    control, run_task, worker_module = worker_task
    service = NotificationService(db_session)

    channel = service.create_channel(
        NotificationChannelCreate(
            name="CH-suppressed",
            type="email",
            enabled=False,
            config={"apprise_url": "mailto://user:pass@mail.test"},
        )
    )
    recipient = service.create_recipient(
        NotificationRecipientCreate(type="email", address="user@example.com", status="active")
    )
    rule = service.create_rule(
        NotificationRuleCreate(
            name="Rule-s",
            recipient_ids=[recipient.id],
            channel_ids=[channel.id],
            dedup_window_sec=10,
        )
    )

    payload = {
        "event_id": "evt-suppressed",
        "rule_id": str(rule.id),
        "channel_id": str(channel.id),
        "recipient_id": str(recipient.id),
    }

    # Канал выключен -> suppressed
    assert run_task(payload) is True
    assert _last_status(service, "evt-suppressed") == "suppressed"

    # Включаем канал и проверяем дедупликацию
    channel.enabled = True
    db_session.commit()
    payload["event_id"] = "evt-dedup"
    control["success"] = True
    assert run_task(payload) is True  # первая отправка
    assert _last_status(service, "evt-dedup") == "success"
    assert run_task(payload) is True  # дедуп, лог без повторной отправки
    assert _last_status(service, "evt-dedup") == "deduped"


def test_worker_rate_limited(monkeypatch, db_session, worker_task):
    control, run_task, worker_module = worker_task
    service = NotificationService(db_session)

    channel = service.create_channel(
        NotificationChannelCreate(
            name="CH-rate",
            type="email",
            config={"apprise_url": "mailto://user:pass@mail.test"},
        )
    )
    recipient = service.create_recipient(
        NotificationRecipientCreate(type="email", address="r@example.com", status="active")
    )
    rule = service.create_rule(
        NotificationRuleCreate(
            name="Rule-rate",
            recipient_ids=[recipient.id],
            channel_ids=[channel.id],
            rate_limit={"limit": 1, "window_sec": 120},
            dedup_window_sec=0,
        )
    )

    payload = {
        "event_id": "evt-rate",
        "rule_id": str(rule.id),
        "channel_id": str(channel.id),
        "recipient_id": str(recipient.id),
    }

    control["success"] = True
    assert run_task(payload) is True
    assert _last_status(service, "evt-rate") == "success"
    assert run_task(payload) is True
    assert _last_status(service, "evt-rate") == "rate-limited"
