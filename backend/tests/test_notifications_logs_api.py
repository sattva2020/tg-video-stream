"""Тесты API журналов доставки уведомлений."""
from datetime import datetime, timedelta, timezone
import uuid

import pytest

# Импортируем модели до поднятия тестовой БД, чтобы таблицы создались в Base.metadata
from src.models import notifications as _notifications_models  # noqa: F401
from src.services.notifications.base import NotificationService
from src.schemas.notifications import (
    NotificationChannelCreate,
    NotificationRecipientCreate,
    NotificationRuleCreate,
)


def _parse_ts(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


@pytest.fixture()
def notification_entities(db_session):
    service = NotificationService(db_session)
    channel = service.create_channel(
        NotificationChannelCreate(name="Email", type="email", config={"from": "noreply@example.com"})
    )
    recipient = service.create_recipient(
        NotificationRecipientCreate(type="email", address="user@example.com", status="active")
    )
    rule = service.create_rule(
        NotificationRuleCreate(
            name="Critical alerts",
            recipient_ids=[recipient.id],
            channel_ids=[channel.id],
            dedup_window_sec=0,
        )
    )
    return service, rule, channel, recipient


def test_list_logs_flattens_statuses_and_respects_created_from(client, db_session, notification_entities):
    service, rule, channel, recipient = notification_entities
    now = datetime.now(timezone.utc)

    # Создаём логи с разными статусами для одного события
    log_success = service.log_delivery(
        event_id="evt-123",
        status="success",
        rule_id=rule.id,
        channel_id=channel.id,
        recipient_id=recipient.id,
    )
    log_deduped = service.log_delivery(
        event_id="evt-123",
        status="deduped",
        rule_id=rule.id,
        channel_id=channel.id,
        recipient_id=recipient.id,
    )
    log_suppressed = service.log_delivery(
        event_id="evt-123",
        status="suppressed",
        rule_id=rule.id,
        channel_id=channel.id,
        recipient_id=recipient.id,
    )

    # Сдвигаем suppressed в прошлое, чтобы отфильтровать по created_from
    log_suppressed.created_at = now - timedelta(hours=2)
    db_session.commit()

    created_from_dt = now - timedelta(hours=1)
    created_from = created_from_dt.isoformat()
    response = client.get(
        "/api/notifications/logs",
        params={"event_id": "evt-123", "statuses": "success, deduped", "created_from": created_from},
    )

    assert response.status_code == 200
    payload = response.json()
    assert {entry["id"] for entry in payload} == {str(log_success.id), str(log_deduped.id)}
    assert {entry["status"] for entry in payload} == {"success", "deduped"}
    assert all(_parse_ts(entry["created_at"]) >= created_from_dt for entry in payload)


def test_list_logs_respects_limit(client, db_session, notification_entities):
    service, rule, channel, recipient = notification_entities
    base_time = datetime.now(timezone.utc)

    # Создаём три лога с разными created_at, ожидаем что limit=2 вернёт два самых поздних
    logs = []
    for idx in range(3):
        log = service.log_delivery(
            event_id="evt-limit",
            status="success",
            rule_id=rule.id,
            channel_id=channel.id,
            recipient_id=recipient.id,
            attempt=idx + 1,
        )
        log.created_at = base_time - timedelta(minutes=5 - idx)
        logs.append(log)
    db_session.commit()

    response = client.get(
        "/api/notifications/logs",
        params={"event_id": "evt-limit", "limit": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    attempts = {entry["attempt"] for entry in payload}
    assert attempts == {2, 3}


def test_get_delivery_log_not_found(client):
    unknown_id = uuid.uuid4()
    response = client.get(f"/api/notifications/logs/{unknown_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Log not found"
