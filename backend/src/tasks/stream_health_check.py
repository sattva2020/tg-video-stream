"""
Celery tasks для проверки здоровья потоков и автоматического восстановления.

Включает:
- Периодическую проверку здоровья всех активных потоков
- Автоматический запуск восстановления при обнаружении проблем
- Интеграцию с StreamHealthMonitor и StreamRecoveryService
"""
import os
import logging
import uuid
from typing import Dict, Any, List

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
    broker = os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')
    if not broker:
        return None
    return Celery('tg_video_streamer', broker=broker)


def _run_async(coro):
    """
    Запускает async функцию в sync контексте.

    Используется в Celery tasks для вызова async функций.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


def check_stream_health_sync(stream_id: str) -> Dict[str, Any]:
    """
    Проверяет здоровье потока (sync wrapper для async).

    Args:
        stream_id: UUID потока

    Returns:
        dict с результатами проверки: is_healthy, failure_type, error_message, etc.
    """
    try:
        from src.services.stream_health_monitor import get_stream_health_monitor

        monitor = get_stream_health_monitor()
        health_status = _run_async(monitor.check_stream_health(stream_id))

        return {
            "success": True,
            "stream_id": stream_id,
            "is_healthy": health_status.is_healthy,
            "consecutive_failures": health_status.consecutive_failures,
            "last_failure_type": health_status.last_failure_type,
            "last_error_message": health_status.last_error_message,
            "last_check": health_status.last_check.isoformat() if health_status.last_check else None,
        }

    except Exception as e:
        logger.exception(f"Error checking health for stream {stream_id}")
        return {
            "success": False,
            "stream_id": stream_id,
            "error": str(e),
            "is_healthy": False
        }


def trigger_recovery_sync(
    stream_id: str,
    failure_type: str,
    failure_reason: str
) -> Dict[str, Any]:
    """
    Запускает восстановление потока (sync wrapper для async).

    Args:
        stream_id: UUID потока
        failure_type: Тип отказа (network, api_rate_limit, codec_error, etc.)
        failure_reason: Описание причины отказа

    Returns:
        dict с результатом восстановления
    """
    try:
        from database import SessionLocal
        from src.models.recovery_log import RecoveryFailureType, RecoveryStrategy
        from src.services.stream_recovery_service import get_stream_recovery_service

        db = SessionLocal()
        try:
            service = get_stream_recovery_service(db)

            # Конвертируем string failure_type в enum
            try:
                failure_type_enum = RecoveryFailureType(failure_type)
            except ValueError:
                logger.warning(f"Invalid failure_type '{failure_type}', defaulting to UNKNOWN")
                failure_type_enum = RecoveryFailureType.UNKNOWN

            result = service.recover_stream(
                stream_id=uuid.UUID(stream_id),
                failure_type=failure_type_enum,
                failure_reason=failure_reason,
                strategy=RecoveryStrategy.RESTART
            )

            return {
                "success": result.get("success", False),
                "stream_id": stream_id,
                "recovery_attempted": True,
                "recovery_result": result
            }

        finally:
            db.close()

    except Exception as e:
        logger.exception(f"Error triggering recovery for stream {stream_id}")
        return {
            "success": False,
            "stream_id": stream_id,
            "recovery_attempted": True,
            "error": str(e)
        }


def get_active_streams() -> List[Dict[str, Any]]:
    """
    Получает список всех активных потоков из базы данных.

    Returns:
        Список dict с id и title активных потоков
    """
    try:
        from database import SessionLocal
        from src.models.stream import Stream, StreamStatus

        db = SessionLocal()
        try:
            streams = db.query(Stream).filter(
                Stream.status == StreamStatus.ACTIVE
            ).all()

            return [
                {
                    "id": str(stream.id),
                    "title": stream.title or f"Stream {stream.id}",
                    "status": stream.status
                }
                for stream in streams
            ]

        finally:
            db.close()

    except Exception as e:
        logger.exception("Error getting active streams")
        return []


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.check_all_streams_health', bind=True, max_retries=3)
    def check_all_streams_health_task(self):
        """
        Celery task: проверяет здоровье всех активных потоков и запускает восстановление.

        Для каждого потока:
        1. Проверяет здоровье через StreamHealthMonitor
        2. Если поток нездоров - запускает восстановление через StreamRecoveryService
        3. Логирует результаты

        Автоматически повторяется при ошибке (до 3 раз с экспоненциальной задержкой).
        """
        logger.info("[worker] check_all_streams_health_task started")

        try:
            # Получаем все активные потоки
            active_streams = get_active_streams()
            total_streams = len(active_streams)

            if total_streams == 0:
                logger.info("No active streams found, health check complete")
                return {
                    "success": True,
                    "total_streams": 0,
                    "healthy_streams": 0,
                    "unhealthy_streams": 0,
                    "recovery_triggered": 0,
                    "streams": []
                }

            logger.info(f"Checking health for {total_streams} active streams")

            results = {
                "success": True,
                "total_streams": total_streams,
                "healthy_streams": 0,
                "unhealthy_streams": 0,
                "recovery_triggered": 0,
                "streams": []
            }

            # Проверяем здоровье каждого потока
            for stream_info in active_streams:
                stream_id = stream_info["id"]

                health_result = check_stream_health_sync(stream_id)

                if not health_result.get("success"):
                    logger.error(f"Failed to check health for stream {stream_id}")
                    continue

                is_healthy = health_result.get("is_healthy", True)

                if is_healthy:
                    results["healthy_streams"] += 1
                    logger.debug(f"Stream {stream_id} is healthy")
                else:
                    results["unhealthy_streams"] += 1
                    failure_type = health_result.get("last_failure_type", "unknown")
                    error_message = health_result.get("last_error_message", "Unknown error")

                    logger.warning(
                        f"Stream {stream_id} is unhealthy: "
                        f"{failure_type} - {error_message}"
                    )

                    # Запускаем восстановление
                    recovery_result = trigger_recovery_sync(
                        stream_id=stream_id,
                        failure_type=failure_type,
                        failure_reason=error_message
                    )

                    if recovery_result.get("recovery_attempted"):
                        results["recovery_triggered"] += 1
                        logger.info(f"Recovery triggered for stream {stream_id}")

                    results["streams"].append({
                        "stream_id": stream_id,
                        "title": stream_info.get("title"),
                        "is_healthy": False,
                        "failure_type": failure_type,
                        "error_message": error_message,
                        "recovery_triggered": True,
                        "recovery_success": recovery_result.get("success", False)
                    })

            logger.info(
                f"Health check complete: {results['healthy_streams']} healthy, "
                f"{results['unhealthy_streams']} unhealthy, "
                f"{results['recovery_triggered']} recoveries triggered"
            )

            return results

        except Exception as e:
            logger.exception("Unhandled error in check_all_streams_health_task")
            # Retry на recoverable errors
            if "database" in str(e).lower() or "connection" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "error": str(e),
                "total_streams": 0,
                "healthy_streams": 0,
                "unhealthy_streams": 0,
                "recovery_triggered": 0
            }

    @celery_app.task(name='tasks.stream_health_check', bind=True, max_retries=3)
    def check_single_stream_health_task(self, stream_id: str):
        """
        Celery task: проверяет здоровье конкретного потока.

        Args:
            stream_id: UUID потока для проверки

        Returns:
            dict с результатом проверки здоровья
        """
        logger.info(f"[worker] check_single_stream_health_task for stream {stream_id}")

        try:
            health_result = check_stream_health_sync(stream_id)

            if not health_result.get("is_healthy"):
                # Поток нездоров - запускаем восстановление
                failure_type = health_result.get("last_failure_type", "unknown")
                error_message = health_result.get("last_error_message", "Unknown error")

                logger.warning(
                    f"Stream {stream_id} is unhealthy, triggering recovery: "
                    f"{failure_type} - {error_message}"
                )

                recovery_result = trigger_recovery_sync(
                    stream_id=stream_id,
                    failure_type=failure_type,
                    failure_reason=error_message
                )

                health_result["recovery_triggered"] = True
                health_result["recovery_result"] = recovery_result
            else:
                health_result["recovery_triggered"] = False
                logger.info(f"Stream {stream_id} is healthy")

            return health_result

        except Exception as e:
            logger.exception(f"Error in check_single_stream_health_task for {stream_id}")
            # Retry на recoverable errors
            if "database" in str(e).lower() or "connection" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "stream_id": stream_id,
                "error": str(e),
                "is_healthy": False,
                "recovery_triggered": False
            }


# ============================================================================
# Public API
# ============================================================================

def check_all_streams_async() -> bool:
    """
    Запускает асинхронную проверку здоровья всех потоков.

    Использует Celery если доступен, иначе выполняет синхронно.

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.check_all_streams_health')
            logger.info("Enqueued health check for all streams")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info("Checking stream health synchronously")
    try:
        task = check_all_streams_health_task()
        return task.get("success", False)
    except Exception:
        logger.exception("Failed to check stream health synchronously")
        return False


def check_stream_async(stream_id: str) -> bool:
    """
    Запускает асинхронную проверку здоровья конкретного потока.

    Args:
        stream_id: UUID потока

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.stream_health_check', args=[str(stream_id)])
            logger.info(f"Enqueued health check for stream {stream_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Checking stream health synchronously for {stream_id}")
    try:
        task = check_single_stream_health_task(str(stream_id))
        return task.get("success", False)
    except Exception:
        logger.exception(f"Failed to check stream health synchronously for {stream_id}")
        return False
