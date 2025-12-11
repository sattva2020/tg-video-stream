"""
Каркас Celery-воркера для уведомлений и фабрика клиентов Apprise/SDK.
Логика отправки преднамеренно упрощена для базового фундамента; расширяется в задачах US1/US2.
"""
import asyncio
import logging
from typing import Dict, List, Optional
from uuid import UUID

from apprise import Apprise

from src.celery_app import celery_app
from src.core.config import settings
from src.database import SessionLocal
from src.services.notifications.base import NotificationService
from src.services.notifications.controls import NotificationControls

logger = logging.getLogger(__name__)
STORM_BATCH_SIZE = getattr(settings, "NOTIF_STORM_BATCH_SIZE", 10)
STORM_WINDOW_FALLBACK = getattr(settings, "NOTIF_STORM_WINDOW_SEC", 120)


def build_apprise_urls(channel_config: Dict, channel_type: str, recipient_address: str) -> List[str]:
    """Формирует список Apprise URL для заданного канала/получателя."""
    urls: List[str] = []
    explicit = channel_config.get("apprise_url")
    if explicit:
        if isinstance(explicit, list):
            urls.extend(explicit)
        else:
            urls.append(str(explicit))
        return urls

    if channel_type == "email":
        host = channel_config.get("host")
        user = channel_config.get("user")
        password = channel_config.get("password")
        port = channel_config.get("port", 587)
        sender = channel_config.get("from") or user
        if host and user and password and sender:
            urls.append(f"mailto://{user}:{password}@{host}:{port}/?from={sender}&to={recipient_address}")
    elif channel_type == "telegram":
        token = channel_config.get("bot_token")
        chat_id = channel_config.get("chat_id") or recipient_address
        if token and chat_id:
            urls.append(f"tgram://{token}/{chat_id}")
    elif channel_type in {"webhook", "http", "https"}:
        url = channel_config.get("url") or recipient_address
        if url:
            urls.append(url)
    elif channel_type == "slack":
        webhook = channel_config.get("webhook") or channel_config.get("url")
        if webhook:
            urls.append(webhook)
    elif channel_type == "sms":
        # Ожидаем apprise совместимый url, например twilio://
        sms_url = channel_config.get("twilio_url") or channel_config.get("apprise_sms_url")
        if sms_url:
            urls.append(sms_url)

    return urls


def render_body(template_body: str, context: Dict[str, str]) -> str:
    try:
        return template_body.format(**context)
    except Exception:
        return template_body


def render_subject(subject: Optional[str], context: Dict[str, str]) -> Optional[str]:
    if subject is None:
        return None
    try:
        return subject.format(**context)
    except Exception:
        return subject


def _notify_with_timeout(app: Apprise, *, body: str, title: Optional[str], timeout: int) -> bool:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(asyncio.wait_for(loop.run_in_executor(None, app.notify, body, title), timeout=timeout))
    finally:
        loop.close()


async def aggregate_storm_event(
    *,
    controls: NotificationControls,
    service: NotificationService,
    rule_id: Optional[str],
    recipient_id: Optional[str],
    event_id: str,
    window_sec: int,
):
    """Накопление шторма одинаковых событий и периодическая запись в лог."""
    if not rule_id or not recipient_id or not event_id or window_sec <= 0:
        return
    try:
        async with await controls._get_redis() as r:  # noqa: SLF001 - контролируем прямой вызов
            key = f"notif:storm:{rule_id}:{recipient_id}:{event_id}"
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, window_sec)
    except Exception:
        logger.warning("Storm aggregation skipped (no Redis)", exc_info=True)
        return

    if count and count % STORM_BATCH_SIZE == 0:
        try:
            service.log_delivery(
                event_id=event_id,
                rule_id=UUID(rule_id),
                recipient_id=UUID(recipient_id),
                status="deduped",
                error_message=f"storm aggregated count={count} window={window_sec}s",
            )
        except Exception:
            logger.exception("Failed to log storm aggregation")


if celery_app:
    @celery_app.task(name="notifications.process_event", bind=True, max_retries=settings.NOTIF_RETRY_ATTEMPTS, default_retry_delay=settings.NOTIF_RETRY_INTERVAL_SEC)
    def process_notification(self, payload: Dict):
        """Базовый Celery task: отправка уведомления по каналу с учётом дедуп/rate-limit/silence."""
        event_id = payload.get("event_id")
        rule_id = payload.get("rule_id")
        channel_id = payload.get("channel_id")
        recipient_id = payload.get("recipient_id")
        context = payload.get("context", {})

        db = SessionLocal()
        controls = NotificationControls()
        service = NotificationService(db)

        try:
            rule = service.get_rule(rule_id) if rule_id else None
            channel = service.get_channel(channel_id) if channel_id else None
            recipient = service.get_recipient(recipient_id) if recipient_id else None
            template = rule.template if rule else None

            if not (event_id and rule and channel and recipient):
                service.log_delivery(
                    event_id=event_id or "unknown",
                    rule_id=rule_id,
                    channel_id=channel_id,
                    recipient_id=recipient_id,
                    status="fail",
                    error_message="Missing required entities",
                )
                return False

            # Disabled channel
            if not channel.enabled:
                service.log_delivery(
                    event_id=event_id,
                    rule_id=rule.id,
                    channel_id=channel.id,
                    recipient_id=recipient.id,
                    status="suppressed",
                    error_message="Channel disabled",
                )
                return True

            # Blocked/opt-out recipient
            recipient_status = (recipient.status or "active").lower()
            if recipient_status in {"blocked", "opt-out", "opt_out", "disabled"}:
                service.log_delivery(
                    event_id=event_id,
                    rule_id=rule.id,
                    channel_id=channel.id,
                    recipient_id=recipient.id,
                    status="suppressed",
                    error_message=f"Recipient status={recipient.status}",
                )
                return True

            # Silence windows
            if asyncio.run(controls.is_silenced(recipient_id=str(recipient.id), windows=recipient.silence_windows or rule.silence_windows)):
                service.log_delivery(event_id=event_id, rule_id=rule.id, channel_id=channel.id, recipient_id=recipient.id, status="suppressed")
                return True

            # Deduplication
            if rule.dedup_window_sec and rule.dedup_window_sec > 0:
                deduped = asyncio.run(
                    controls.is_deduplicated(
                        event_id=event_id,
                        rule_id=str(rule.id),
                        recipient_id=str(recipient.id),
                        ttl_sec=rule.dedup_window_sec,
                    )
                )
                if deduped:
                    storm_window = rule.dedup_window_sec or STORM_WINDOW_FALLBACK
                    asyncio.run(
                        aggregate_storm_event(
                            controls=controls,
                            service=service,
                            rule_id=str(rule.id),
                            recipient_id=str(recipient.id),
                            event_id=event_id,
                            window_sec=storm_window,
                        )
                    )
                    service.log_delivery(event_id=event_id, rule_id=rule.id, channel_id=channel.id, recipient_id=recipient.id, status="deduped")
                    return True

            # Rate limit
            rate_cfg = rule.rate_limit or {}
            limit = rate_cfg.get("limit")
            window = rate_cfg.get("window_sec")
            if limit and window:
                allowed, count = asyncio.run(
                    controls.check_rate_limit(
                        scope=f"{recipient.id}:{channel.type}",
                        limit=int(limit),
                        window_sec=int(window),
                    )
                )
                if not allowed:
                    service.log_delivery(
                        event_id=event_id,
                        rule_id=rule.id,
                        channel_id=channel.id,
                        recipient_id=recipient.id,
                        status="rate-limited",
                        error_message=f"count={count} limit={limit}/{window}s",
                    )
                    return True

            # Render message
            body = render_body(template.body if template else payload.get("body", ""), context)
            subject = render_subject(template.subject if template else payload.get("subject"), context)

            urls = build_apprise_urls(channel.config, channel.type, recipient.address)
            if not urls:
                service.log_delivery(
                    event_id=event_id,
                    rule_id=rule.id,
                    channel_id=channel.id,
                    recipient_id=recipient.id,
                    status="fail",
                    error_message="No Apprise URL for channel",
                )
                return False

            app = Apprise()
            for url in urls:
                app.add(url)

            timeout = channel.timeout_sec or settings.NOTIF_TIMEOUT_HTTP_SEC
            success = _notify_with_timeout(app, body=body, title=subject, timeout=timeout)

            service.log_delivery(
                event_id=event_id,
                rule_id=rule.id,
                channel_id=channel.id,
                recipient_id=recipient.id,
                status="success" if success else "fail",
            )
            return success
        except Exception as exc:  # noqa: BLE001
            logger.exception("Notification processing failed")
            try:
                service.log_delivery(
                    event_id=event_id or "unknown",
                    rule_id=rule_id,
                    channel_id=channel_id,
                    recipient_id=recipient_id,
                    status="fail",
                    error_message=str(exc),
                )
            except Exception:
                logger.error("Failed to log delivery", exc_info=True)
            raise self.retry(exc=exc)
        finally:
            db.close()


if celery_app:
    @celery_app.task(name="notifications.send_test")
    def send_test_notification(payload: Dict) -> bool:
        """Отправка тестового уведомления по конкретному каналу (без маршрутизации правил)."""
        event_id = payload.get("event_id") or "test"
        channel_id = payload.get("channel_id")
        recipient = payload.get("recipient")
        subject = payload.get("subject")
        body = payload.get("body")
        context = payload.get("context", {})

        db = SessionLocal()
        service = NotificationService(db)

        try:
            channel = service.get_channel(channel_id)
            if not channel:
                logger.error("Channel not found for test send", extra={"channel_id": channel_id})
                return False

            urls = build_apprise_urls(channel.config, channel.type, recipient)
            if not urls:
                service.log_delivery(
                    event_id=event_id,
                    channel_id=channel.id,
                    status="fail",
                    error_message="No Apprise URL for channel",
                )
                return False

            app = Apprise()
            for url in urls:
                app.add(url)

            rendered_body = render_body(body or "Test notification", context)
            rendered_subject = render_subject(subject or "Test notification", context)

            timeout = channel.timeout_sec or settings.NOTIF_TIMEOUT_HTTP_SEC
            success = _notify_with_timeout(app, body=rendered_body, title=rendered_subject, timeout=timeout)

            service.log_delivery(
                event_id=event_id,
                channel_id=channel.id,
                status="success" if success else "fail",
                error_message=None if success else "send_test failed",
            )
            return success
        except Exception as exc:  # noqa: BLE001
            logger.exception("Test notification failed")
            try:
                service.log_delivery(
                    event_id=event_id,
                    channel_id=channel_id,
                    status="fail",
                    error_message=str(exc),
                )
            except Exception:
                logger.error("Failed to log test notification", exc_info=True)
            return False
        finally:
            db.close()

else:
    def send_test_notification(payload: Dict) -> bool:
        # Лёгкий заглушечный вариант, когда Celery не поднят в dev/e2e
        logger.warning("Celery app not configured; skipping test notification", extra={"payload": payload})
        return False
