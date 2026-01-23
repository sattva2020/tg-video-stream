"""
Celery tasks для CDN operations.

Включает:
- Проверка здоровья CDN провайдеров
- Очистка кэша CDN
- Сбор метрик производительности CDN
"""
import os
import logging
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy Celery import
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    CELERY_AVAILABLE = False


def _get_celery_app():
    """Получает или создаёт Celery приложение."""
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        return None
    return Celery('tg_video_streamer', broker=broker)


def _run_async(coro):
    """
    Запускает асинхронную корутину в синхронном контексте.

    Args:
        coro: Асинхронная корутина для выполнения

    Returns:
        Результат выполнения корутины
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


def check_cdn_health_sync(provider_id: Optional[str] = None) -> dict:
    """
    Синхронная обёртка для проверки здоровья CDN.

    Args:
        provider_id: Опциональный ID CDN конфигурации для проверки

    Returns:
        dict с результатом проверки:
        {
            "success": bool,
            "overall_status": str,
            "providers_checked": int,
            "healthy_count": int,
            "error": Optional[str]
        }
    """
    try:
        from src.services.cdn_service import CDNService
        from src.database import SessionLocal

        db = SessionLocal()
        try:
            cdn_service = CDNService(db_session=db)
            result = _run_async(cdn_service.get_health_status(
                provider_id=provider_id,
                use_cache=False  # Всегда свежая проверка для задачи
            ))

            # Подсчитываем статистику
            providers = result.get("providers", [])
            healthy_count = sum(
                1 for p in providers
                if p.get("status") == "healthy"
            )

            return {
                "success": True,
                "overall_status": result.get("overall_status"),
                "providers_checked": len(providers),
                "healthy_count": healthy_count,
                "degraded_count": sum(
                    1 for p in providers
                    if p.get("status") == "degraded"
                ),
                "unhealthy_count": sum(
                    1 for p in providers
                    if p.get("status") == "unhealthy"
                ),
                "last_check": result.get("last_check")
            }

        finally:
            db.close()

    except Exception as e:
        logger.exception(f"Error in check_cdn_health_sync")
        return {
            "success": False,
            "error": str(e),
            "providers_checked": 0,
            "healthy_count": 0
        }


def purge_cdn_cache_sync(
    urls: Optional[List[str]] = None,
    provider_id: Optional[str] = None,
    purge_all: bool = False
) -> dict:
    """
    Синхронная обёртка для очистки кэша CDN.

    Args:
        urls: Список URL для очистки (опционально)
        provider_id: Опциональный ID CDN конфигурации для очистки
        purge_all: Если True, очищает весь кэш

    Returns:
        dict с результатом очистки:
        {
            "success": bool,
            "purged_urls": List[str],
            "providers": List[dict],
            "errors": List[str]
        }
    """
    try:
        from src.services.cdn_service import CDNService
        from src.database import SessionLocal

        db = SessionLocal()
        try:
            cdn_service = CDNService(db_session=db)
            result = _run_async(cdn_service.purge_cache(
                urls=urls or [],
                provider_id=provider_id,
                purge_all=purge_all
            ))

            return result

        finally:
            db.close()

    except Exception as e:
        logger.exception(f"Error in purge_cdn_cache_sync")
        return {
            "success": False,
            "purged_urls": urls or [],
            "providers": [],
            "errors": [str(e)]
        }


def collect_cdn_metrics_sync() -> dict:
    """
    Синхронная обёртка для сбора метрик CDN производительности.

    Собирает и обновляет Prometheus метрики для:
    - Статуса здоровья CDN провайдеров
    - Количество активных провайдеров
    - Распределение статусов (healthy/degraded/unhealthy)
    - Время ответа от провайдеров

    Returns:
        dict с результатом сбора метрик:
        {
            "success": bool,
            "metrics_collected": dict,
            "providers_count": int,
            "timestamp": str,
            "error": Optional[str]
        }
    """
    try:
        from src.services.cdn_service import CDNService
        from src.database import SessionLocal

        db = SessionLocal()
        try:
            cdn_service = CDNService(db_session=db)

            # Получаем статус здоровья всех провайдеров
            health_result = _run_async(cdn_service.get_health_status(
                provider_id=None,
                use_cache=True  # Используем кэш для производительности
            ))

            providers = health_result.get("providers", [])
            overall_status = health_result.get("overall_status", "unknown")
            last_check = health_result.get("last_check")

            # Подсчитываем статистику по статусам
            healthy_count = sum(1 for p in providers if p.get("status") == "healthy")
            degraded_count = sum(1 for p in providers if p.get("status") == "degraded")
            unhealthy_count = sum(1 for p in providers if p.get("status") == "unhealthy")
            total_count = len(providers)

            # Собираем метрики по каждому провайдеру
            providers_metrics = []
            for provider in providers:
                provider_id = provider.get("config_id", "unknown")
                provider_name = provider.get("name", "unknown")
                provider_type = provider.get("provider", "unknown")
                status = provider.get("status", "unknown")
                response_time = provider.get("response_time_ms", 0)
                last_error = provider.get("last_error")

                providers_metrics.append({
                    "provider_id": provider_id,
                    "name": provider_name,
                    "type": provider_type,
                    "status": status,
                    "response_time_ms": response_time,
                    "last_error": last_error
                })

            # Обновляем Prometheus метрики если доступно
            try:
                from src.services.prometheus_metrics import (
                    CDN_PROVIDERS_TOTAL,
                    CDN_PROVIDERS_HEALTHY,
                    CDN_PROVIDERS_DEGRADED,
                    CDN_PROVIDERS_UNHEALTHY,
                    CDN_PROVIDER_STATUS,
                    CDN_PROVIDER_RESPONSE_TIME,
                )

                # Обновляем счётчики провайдеров
                CDN_PROVIDERS_TOTAL.set(total_count)
                CDN_PROVIDERS_HEALTHY.set(healthy_count)
                CDN_PROVIDERS_DEGRADED.set(degraded_count)
                CDN_PROVIDERS_UNHEALTHY.set(unhealthy_count)

                # Обновляем метрики по каждому провайдеру
                for provider in providers:
                    provider_id = provider.get("config_id", "unknown")
                    provider_type = provider.get("provider", "unknown")
                    status = provider.get("status", "unknown")
                    response_time = provider.get("response_time_ms", 0) / 1000.0  # Конвертируем в секунды

                    # Статус провайдера (1 если healthy, 0 иначе)
                    is_healthy = 1 if status == "healthy" else 0
                    CDN_PROVIDER_STATUS.labels(
                        provider_id=provider_id,
                        provider_type=provider_type
                    ).set(is_healthy)

                    # Время ответа
                    if response_time > 0:
                        CDN_PROVIDER_RESPONSE_TIME.labels(
                            provider_id=provider_id,
                            provider_type=provider_type
                        ).observe(response_time)

            except ImportError:
                # Prometheus метрики недоступны, продолжаем без них
                logger.debug("Prometheus metrics not available, skipping metrics update")

            metrics_summary = {
                "total_providers": total_count,
                "healthy_count": healthy_count,
                "degraded_count": degraded_count,
                "unhealthy_count": unhealthy_count,
                "overall_status": overall_status,
                "last_health_check": last_check,
                "providers": providers_metrics
            }

            return {
                "success": True,
                "metrics_collected": metrics_summary,
                "providers_count": total_count,
                "timestamp": datetime.utcnow().isoformat()
            }

        finally:
            db.close()

    except Exception as e:
        logger.exception(f"Error in collect_cdn_metrics_sync")
        return {
            "success": False,
            "error": str(e),
            "providers_count": 0,
            "timestamp": datetime.utcnow().isoformat()
        }


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

# Task function reference (will be set to Celery task if available, None otherwise)
check_cdn_health = None

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(
        name='tasks.check_cdn_health',
        bind=True,
        max_retries=3,
        default_retry_delay=60
    )
    def _check_cdn_health_task(self, provider_id: Optional[str] = None):
        """
        Celery task: проверяет здоровье CDN провайдеров.

        Обновляет статус в базе данных и кэше Redis.
        Может быть запущена для конкретного провайдера или для всех включённых.

        Args:
            provider_id: Опциональный ID CDN конфигурации для проверки

        Returns:
            dict с результатом проверки здоровья

        Retry policy:
            - Максимально 3 повтора
            - Задержка 60 секунд между попытками
            - Ретрай при временных ошибках сети
        """
        logger.info(f"[worker] check_cdn_health task called for provider: {provider_id or 'all'}")

        try:
            result = check_cdn_health_sync(provider_id)

            if not result.get("success"):
                error = result.get("error", "Unknown error")
                logger.warning(f"CDN health check failed: {error}")

                # Ретрай на временных ошибках
                if any(err in error.lower() for err in ["timeout", "connection", "network", "temporary"]):
                    raise self.retry(countdown=60 * (self.request.retries + 1))

                return result

            logger.info(
                f"CDN health check completed: {result['healthy_count']}/{result['providers_checked']} healthy, "
                f"status: {result['overall_status']}"
            )

            return result

        except Exception as e:
            logger.exception(f"Unhandled error in check_cdn_health task")
            raise self.retry(exc=e, countdown=60)

    # Export the task
    check_cdn_health = _check_cdn_health_task


# Task function reference (will be set to Celery task if available, None otherwise)
purge_cdn_cache = None

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(
        name='tasks.purge_cdn_cache',
        bind=True,
        max_retries=3,
        default_retry_delay=60
    )
    def _purge_cdn_cache_task(
        self,
        urls: Optional[List[str]] = None,
        provider_id: Optional[str] = None,
        purge_all: bool = False
    ):
        """
        Celery task: очищает кэш CDN провайдеров.

        Очищает кэш для указанных URL или весь кэш.
        Может быть запущена для конкретного провайдера или для всех включённых.

        Args:
            urls: Список URL для очистки (опционально)
            provider_id: Опциональный ID CDN конфигурации для очистки
            purge_all: Если True, очищает весь кэш

        Returns:
            dict с результатом очистки кэша

        Retry policy:
            - Максимально 3 повтора
            - Задержка 60 секунд между попытками
            - Ретрай при временных ошибках сети или API
        """
        logger.info(
            f"[worker] purge_cdn_cache task called for provider: {provider_id or 'all'}, "
            f"purge_all: {purge_all}, urls_count: {len(urls) if urls else 0}"
        )

        try:
            result = purge_cdn_cache_sync(urls, provider_id, purge_all)

            if not result.get("success"):
                errors = result.get("errors", [])
                logger.warning(f"CDN cache purge failed: {errors}")

                # Ретрай на временных ошибках
                error_str = " ".join(errors).lower()
                if any(err in error_str for err in ["timeout", "connection", "network", "temporary", "rate limit"]):
                    raise self.retry(countdown=60 * (self.request.retries + 1))

                return result

            provider_count = len(result.get("providers", []))
            purged_count = len(result.get("purged_urls", []))
            logger.info(
                f"CDN cache purge completed: {provider_count} providers, "
                f"{purged_count} URLs purged, purge_all: {purge_all}"
            )

            return result

        except Exception as e:
            logger.exception(f"Unhandled error in purge_cdn_cache task")
            raise self.retry(exc=e, countdown=60)

    # Export the task
    purge_cdn_cache = _purge_cdn_cache_task


# Task function reference (will be set to Celery task if available, None otherwise)
collect_cdn_metrics = None

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(
        name='tasks.collect_cdn_metrics',
        bind=True,
        max_retries=3,
        default_retry_delay=60
    )
    def _collect_cdn_metrics_task(self):
        """
        Celery task: собирает метрики производительности CDN провайдеров.

        Обновляет Prometheus метрики со статистикой по:
        - Общее количество провайдеров
        - Распределение статусов здоровья
        - Время ответа от провайдеров
        - Последние ошибки

        Returns:
            dict с результатом сбора метрик

        Retry policy:
            - Максимально 3 повтора
            - Задержка 60 секунд между попытками
            - Ретрай при временных ошибках сети или базы данных
        """
        logger.info("[worker] collect_cdn_metrics task called")

        try:
            result = collect_cdn_metrics_sync()

            if not result.get("success"):
                error = result.get("error", "Unknown error")
                logger.warning(f"CDN metrics collection failed: {error}")

                # Ретрай на временных ошибках
                if any(err in error.lower() for err in ["timeout", "connection", "network", "temporary", "database"]):
                    raise self.retry(countdown=60 * (self.request.retries + 1))

                return result

            metrics = result.get("metrics_collected", {})
            logger.info(
                f"CDN metrics collected: {metrics.get('healthy_count', 0)}/{metrics.get('total_providers', 0)} healthy, "
                f"overall status: {metrics.get('overall_status', 'unknown')}"
            )

            return result

        except Exception as e:
            logger.exception(f"Unhandled error in collect_cdn_metrics task")
            raise self.retry(exc=e, countdown=60)

    # Export the task
    collect_cdn_metrics = _collect_cdn_metrics_task


# ============================================================================
# Public API
# ============================================================================

def check_cdn_health_async(provider_id: Optional[str] = None) -> bool:
    """
    Запускает асинхронную проверку здоровья CDN.

    Использует Celery если доступен, иначе выполняет синхронно.

    Args:
        provider_id: Опциональный ID CDN конфигурации для проверки

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.check_cdn_health', args=[provider_id])
            logger.info(f"Enqueued CDN health check for provider: {provider_id or 'all'}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Checking CDN health synchronously for provider: {provider_id or 'all'}")
    result = check_cdn_health_sync(provider_id)
    return result.get("success", False)


def purge_cdn_cache_async(
    urls: Optional[List[str]] = None,
    provider_id: Optional[str] = None,
    purge_all: bool = False
) -> bool:
    """
    Запускает асинхронную очистку кэша CDN.

    Использует Celery если доступен, иначе выполняет синхронно.

    Args:
        urls: Список URL для очистки (опционально)
        provider_id: Опциональный ID CDN конфигурации для очистки
        purge_all: Если True, очищает весь кэш

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.purge_cdn_cache', args=[urls, provider_id, purge_all])
            logger.info(
                f"Enqueued CDN cache purge for provider: {provider_id or 'all'}, "
                f"purge_all: {purge_all}, urls_count: {len(urls) if urls else 0}"
            )
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(
        f"Purging CDN cache synchronously for provider: {provider_id or 'all'}, "
        f"purge_all: {purge_all}"
    )
    result = purge_cdn_cache_sync(urls, provider_id, purge_all)
    return result.get("success", False)


def collect_cdn_metrics_async() -> bool:
    """
    Запускает асинхронный сбор метрик CDN производительности.

    Использует Celery если доступен, иначе выполняет синхронно.

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.collect_cdn_metrics')
            logger.info("Enqueued CDN metrics collection")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info("Collecting CDN metrics synchronously")
    result = collect_cdn_metrics_sync()
    return result.get("success", False)
