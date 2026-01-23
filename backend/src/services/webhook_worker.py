"""
Каркас Celery-воркера для доставки вебхуков с политикой повторных попыток.
Обеспечивает доставку вебхук-уведомлений с подписью HMAC-SHA256 и экспоненциальной задержкой.
"""
import asyncio
import hashlib
import hmac
import httpx
import json
import logging
import time
from typing import Dict, Optional
from uuid import UUID

from src.celery_app import celery_app
from src.core.config import settings
from src.database import SessionLocal
from src.services.webhook_service import WebhookService
from src.models.webhook import Webhook
from src.models.webhook_event import WebhookEvent

logger = logging.getLogger(__name__)

# Webhook delivery settings
WEBHOOK_TIMEOUT_SEC = getattr(settings, "WEBHOOK_TIMEOUT_SEC", 10)
WEBHOOK_MAX_RETRIES = getattr(settings, "WEBHOOK_MAX_RETRIES", 5)
WEBHOOK_RETRY_INITIAL_DELAY = getattr(settings, "WEBHOOK_RETRY_INITIAL_DELAY", 60)
WEBHOOK_RETRY_BACKOFF_MULTIPLIER = getattr(settings, "WEBHOOK_RETRY_BACKOFF_MULTIPLIER", 2)

# HTTP headers
WEBHOOK_USER_AGENT = getattr(settings, "WEBHOOK_USER_AGENT", "Sattva-Webhook/1.0")
WEBHOOK_SIGNATURE_HEADER = getattr(settings, "WEBHOOK_SIGNATURE_HEADER", "X-Sattva-Signature")
WEBHOOK_EVENT_ID_HEADER = getattr(settings, "WEBHOOK_EVENT_ID_HEADER", "X-Sattva-Event-ID")
WEBHOOK_DELIVERY_ID_HEADER = getattr(settings, "WEBHOOK_DELIVERY_ID_HEADER", "X-Sattva-Delivery-ID")


def calculate_retry_delay(attempt: int) -> int:
    """
    Calculate exponential backoff delay for retry attempts.

    Args:
        attempt: The attempt number (1-based)

    Returns:
        Delay in seconds
    """
    delay = WEBHOOK_RETRY_INITIAL_DELAY * (WEBHOOK_RETRY_BACKOFF_MULTIPLIER ** (attempt - 1))
    # Cap the delay at 1 hour
    return min(delay, 3600)


async def is_duplicate_event(event_id: str, webhook_id: UUID) -> bool:
    """
    Проверка на дубликат события через Redis.

    Args:
        event_id: Уникальный идентификатор события
        webhook_id: Идентификатор вебхука

    Returns:
        True, если событие уже было обработано (дубликат)
    """
    try:
        from src.core.redis_client import get_redis

        redis = await get_redis()
        if not redis:
            return False

        key = f"webhook:delivered:{webhook_id}:{event_id}"
        exists = await redis.exists(key)

        if not exists:
            # Mark as delivered with TTL of 24 hours
            await redis.setex(key, 86400, "1")

        return exists
    except Exception as exc:
        logger.warning("Deduplication check failed (Redis unavailable)", exc_info=True)
        return False


def build_webhook_payload(event_type: str, event_data: Dict, event_id: Optional[str]) -> Dict:
    """
    Формирование полезной нагрузки вебхука.

    Args:
        event_type: Тип события
        event_data: Данные события
        event_id: Уникальный идентификатор события

    Returns:
        Словарь с полезной нагрузкой
    """
    payload = {
        "event_type": event_type,
        "data": event_data,
        "timestamp": time.time(),
    }

    if event_id:
        payload["event_id"] = event_id

    return payload


def generate_signature_headers(webhook: Webhook, payload: Dict) -> Dict[str, str]:
    """
    Генерация заголовков подписи для вебхука.

    Args:
        webhook: Объект вебхука
        payload: Полезная нагрузка

    Returns:
        Словарь с HTTP-заголовками
    """
    service = WebhookService(None)  # DB session not needed for signature generation
    signature = service.generate_signature(webhook, payload)

    return {
        WEBHOOK_SIGNATURE_HEADER: f"sha256={signature}",
        "Content-Type": "application/json",
        "User-Agent": WEBHOOK_USER_AGENT,
    }


def verify_webhook_signature(payload: Dict, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature for a webhook payload.

    This function verifies that a received signature matches the expected
    signature for the given payload and secret. It uses constant-time
    comparison to prevent timing attacks.

    Args:
        payload: The payload data to verify
        signature: The signature to verify (with or without "sha256=" prefix)
        secret: The webhook secret used for signature generation

    Returns:
        True if signature is valid, False otherwise
    """
    # Strip "sha256=" prefix if present
    if signature.startswith("sha256="):
        signature = signature[7:]

    # Convert payload to JSON string with same format used for generation
    payload_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)

    # Generate the expected signature
    expected_signature = hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature)


async def deliver_webhook_http(
    webhook: Webhook,
    payload: Dict,
    signature_headers: Dict[str, str],
    delivery_id: int,
) -> tuple[bool, Optional[int], Optional[str], Optional[int]]:
    """
    Выполнение HTTP POST запроса на URL вебхука.

    Args:
        webhook: Объект вебхука
        payload: Полезная нагрузка
        signature_headers: Заголовки с подписью
        delivery_id: ID записи о доставке

    Returns:
        Кортеж (success, status_code, response_body, duration_ms)
    """
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SEC) as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers={
                    **signature_headers,
                    WEBHOOK_EVENT_ID_HEADER: payload.get("event_id", ""),
                    WEBHOOK_DELIVERY_ID_HEADER: str(delivery_id),
                },
            )

            duration_ms = int((time.time() - start_time) * 1000)
            response_body = response.text[:1000] if response.text else None

            # Consider 2xx status codes as success
            success = 200 <= response.status_code < 300

            return success, response.status_code, response_body, duration_ms

    except httpx.TimeoutException:
        duration_ms = int((time.time() - start_time) * 1000)
        return False, None, "Request timeout", duration_ms

    except httpx.RequestError as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        return False, None, str(exc), duration_ms


def log_webhook_delivery(
    db,
    webhook_event: WebhookEvent,
    success: bool,
    status_code: Optional[int],
    response_body: Optional[str],
    duration_ms: Optional[int],
    should_retry: bool = False,
    next_retry_at: Optional[time.time] = None,
):
    """
    Логирование результата доставки вебхука.

    Args:
        db: Сессия базы данных
        webhook_event: Запись о событии вебхука
        success: Успешность доставки
        status_code: HTTP статус код
        response_body: Тело ответа
        duration_ms: Длительность запроса
        should_retry: Нужно ли повторить попытку
        next_retry_at: Время следующей попытки
    """
    try:
        if success:
            webhook_event.mark_success(status_code, response_body, duration_ms)
        else:
            webhook_event.mark_failure(
                status_code=status_code,
                response_body=response_body,
                should_retry=should_retry,
                next_retry_at=next_retry_at,
                duration_ms=duration_ms,
            )

        db.commit()
        db.refresh(webhook_event)

    except Exception as exc:
        logger.error(f"Failed to log webhook delivery: {exc}", exc_info=True)


if celery_app:
    @celery_app.task(
        name="webhook.deliver",
        bind=True,
        max_retries=WEBHOOK_MAX_RETRIES,
        default_retry_delay=WEBHOOK_RETRY_INITIAL_DELAY,
    )
    def deliver_webhook(self, payload: Dict):
        """
        Celery task для доставки вебхука с политикой повторных попыток.

        Args:
            payload: Словарь с параметрами:
                - webhook_event_id: ID записи WebhookEvent
                - event_type: Тип события
                - event_data: Данные события
                - event_id: Уникальный ID события (опционально)

        Returns:
            True если доставка успешна, False в противном случае
        """
        webhook_event_id = payload.get("webhook_event_id")
        event_type = payload.get("event_type")
        event_data = payload.get("event_data", {})
        event_id = payload.get("event_id")

        if not webhook_event_id:
            logger.error("Missing webhook_event_id in payload")
            return False

        db = SessionLocal()
        service = WebhookService(db)

        try:
            # Get webhook event record
            webhook_event = db.get(WebhookEvent, webhook_event_id)
            if not webhook_event:
                logger.error(f"WebhookEvent {webhook_event_id} not found")
                return False

            # Get webhook subscription
            webhook = db.get(Webhook, webhook_event.webhook_id)
            if not webhook:
                logger.error(f"Webhook {webhook_event.webhook_id} not found")
                webhook_event.mark_failure(status_code=None, response_body="Webhook not found")
                db.commit()
                return False

            # Check if webhook is still active
            if not webhook.is_active:
                logger.info(f"Webhook {webhook.id} is disabled, skipping delivery")
                webhook_event.mark_failure(status_code=None, response_body="Webhook disabled")
                db.commit()
                return False

            # Check for duplicate events (deduplication)
            if event_id:
                is_duplicate = asyncio.run(is_duplicate_event(event_id, webhook.id))
                if is_duplicate:
                    logger.info(f"Duplicate event {event_id} for webhook {webhook.id}, skipping")
                    webhook_event.mark_failure(status_code=None, response_body="Duplicate event")
                    db.commit()
                    return True

            # Build webhook payload
            webhook_payload = build_webhook_payload(event_type, event_data, event_id)

            # Generate signature headers
            signature_headers = generate_signature_headers(webhook, webhook_payload)

            # Deliver webhook via HTTP
            success, status_code, response_body, duration_ms = asyncio.run(
                deliver_webhook_http(webhook, webhook_payload, signature_headers, webhook_event.id)
            )

            # Log delivery result
            if success:
                # Update webhook statistics
                webhook.update_success()

                log_webhook_delivery(
                    db,
                    webhook_event,
                    success=True,
                    status_code=status_code,
                    response_body=response_body,
                    duration_ms=duration_ms,
                )

                logger.info(
                    f"Webhook {webhook.id} delivered successfully "
                    f"(status={status_code}, duration={duration_ms}ms)"
                )
                return True

            else:
                # Update webhook failure statistics
                webhook.update_failure()

                # Determine if we should retry
                attempt_number = webhook_event.attempt_number or 1
                should_retry = attempt_number < WEBHOOK_MAX_RETRIES

                # Calculate next retry time if needed
                next_retry_at = None
                if should_retry:
                    retry_delay = calculate_retry_delay(attempt_number)
                    from datetime import datetime, timezone, timedelta
                    next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=retry_delay)

                    # Schedule retry via Celery
                    try:
                        self.retry(countdown=retry_delay)
                    except Exception as exc:
                        logger.warning(f"Failed to schedule retry: {exc}")

                log_webhook_delivery(
                    db,
                    webhook_event,
                    success=False,
                    status_code=status_code,
                    response_body=response_body,
                    duration_ms=duration_ms,
                    should_retry=should_retry,
                    next_retry_at=next_retry_at,
                )

                logger.warning(
                    f"Webhook {webhook.id} delivery failed "
                    f"(status={status_code}, attempt={attempt_number}, "
                    f"should_retry={should_retry})"
                )

                # Raise exception to trigger Celery retry
                if should_retry:
                    raise self.retry(exc=Exception("Webhook delivery failed, retrying"))

                return False

        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Webhook delivery processing failed: {exc}")

            # Log failure if we haven't already
            try:
                webhook_event = db.get(WebhookEvent, webhook_event_id)
                if webhook_event and webhook_event.status not in ("success", "failed"):
                    webhook.update_failure()
                    webhook_event.mark_failure(
                        status_code=None,
                        response_body=str(exc),
                        should_retry=self.request.retries < WEBHOOK_MAX_RETRIES,
                    )
                    db.commit()
            except Exception:
                logger.error("Failed to log webhook delivery error", exc_info=True)

            # Re-raise for Celery retry logic
            raise self.retry(exc=exc)

        finally:
            db.close()


if celery_app:
    @celery_app.task(name="webhook.send_test")
    def send_test_webhook(payload: Dict) -> bool:
        """
        Отправка тестового вебхука для проверки подписки.

        Args:
            payload: Словарь с параметрами:
                - webhook_id: ID вебхука
                - test_data: Тестовые данные (опционально)

        Returns:
            True если отправка успешна, False в противном случае
        """
        webhook_id = payload.get("webhook_id")
        test_data = payload.get("test_data", {"test": True})

        if not webhook_id:
            logger.error("Missing webhook_id in test payload")
            return False

        db = SessionLocal()
        service = WebhookService(db)

        try:
            webhook = db.get(Webhook, webhook_id)
            if not webhook:
                logger.error(f"Webhook {webhook_id} not found")
                return False

            if not webhook.is_active:
                logger.error(f"Webhook {webhook_id} is not active")
                return False

            # Build test payload
            webhook_payload = build_webhook_payload(
                "webhook.test",
                test_data,
                event_id=f"test-{int(time.time())}"
            )

            # Generate signature
            signature_headers = generate_signature_headers(webhook, webhook_payload)

            # Create webhook event record
            webhook_event = WebhookEvent(
                webhook_id=webhook.id,
                event_type="webhook.test",
                event_id=webhook_payload.get("event_id"),
                status="pending",
                attempt_number=1,
            )
            db.add(webhook_event)
            db.commit()
            db.refresh(webhook_event)

            # Deliver test webhook
            success, status_code, response_body, duration_ms = asyncio.run(
                deliver_webhook_http(webhook, webhook_payload, signature_headers, webhook_event.id)
            )

            # Log result
            if success:
                webhook.update_success()
                webhook_event.mark_success(status_code, response_body, duration_ms)
                logger.info(f"Test webhook {webhook_id} sent successfully")
            else:
                webhook.update_failure()
                webhook_event.mark_failure(status_code, response_body, duration_ms)
                logger.error(f"Test webhook {webhook_id} failed: {response_body}")

            db.commit()
            return success

        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Test webhook failed: {exc}")
            return False

        finally:
            db.close()


else:
    # Fallback when Celery is not configured
    def deliver_webhook(payload: Dict) -> bool:
        logger.warning("Celery app not configured; webhook delivery skipped", extra={"payload": payload})
        return False

    def send_test_webhook(payload: Dict) -> bool:
        logger.warning("Celery app not configured; test webhook skipped", extra={"payload": payload})
        return False
