"""
Celery tasks для мониторинга использования лимитов Telegram API.

Включает:
- Периодическую проверку использования лимитов для всех аккаунтов
- Предсказание времени достижения лимитов
- Автоматические оповещения при приближении к пороговым значениям
- Интеграцию с RateLimitPredictor и MultiAccountRateLimiter
"""
import os
import logging
from typing import Optional, Dict, Any, List

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


def check_account_rate_limits_sync(account_id: str) -> Dict[str, Any]:
    """
    Проверяет использование лимитов для аккаунта (sync wrapper для async).

    Args:
        account_id: ID аккаунта Telegram

    Returns:
        dict с результатами проверки: usage_percent, predictions, alert_triggered, etc.
    """
    try:
        from src.services.rate_limit_predictor import rate_limit_predictor

        # Получаем статус аккаунта
        account_status = _run_async(rate_limit_predictor.get_account_status(account_id))

        return {
            "success": True,
            "account_id": account_id,
            "status": account_status.get("status"),
            "max_usage_percent": account_status.get("max_usage_percent"),
            "predictions": account_status.get("predictions", []),
            "usage_summary": account_status.get("usage_summary", {}),
            "updated_at": account_status.get("updated_at"),
        }

    except Exception as e:
        logger.exception(f"Error checking rate limits for account {account_id}")
        return {
            "success": False,
            "account_id": account_id,
            "error": str(e),
            "status": "error"
        }


def check_all_rate_limits_sync() -> Dict[str, Any]:
    """
    Проверяет использование лимитов для всех аккаунтов (sync wrapper).

    Returns:
        dict с глобальной статистикой и деталями по каждому аккаунту
    """
    try:
        from src.services.rate_limit_predictor import rate_limit_predictor
        from src.services.multi_account_rate_limiter import MultiAccountRateLimiter

        # Получаем глобальный статус
        global_status = _run_async(rate_limit_predictor.get_global_status())

        # Получаем список всех аккаунтов
        limiter = MultiAccountRateLimiter()
        accounts = _run_async(limiter.get_all_accounts())

        account_details = []
        for account in accounts:
            account_id = account.get("account_id")
            if account_id:
                account_check = check_account_rate_limits_sync(account_id)
                account_details.append(account_check)

        return {
            "success": True,
            "global_status": global_status,
            "accounts": account_details,
            "total_accounts": len(account_details),
        }

    except Exception as e:
        logger.exception("Error checking all rate limits")
        return {
            "success": False,
            "error": str(e),
            "total_accounts": 0,
            "accounts": []
        }


def trigger_alert_sync(
    account_id: str,
    alert_type: str,
    usage_percent: float,
    endpoint_type: str,
    predicted_breach_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Запускает оповещение о приближении к лимиту (sync wrapper для async).

    Args:
        account_id: ID аккаунта
        alert_type: Тип оповещения (warning, critical)
        usage_percent: Процент использования
        endpoint_type: Тип запроса
        predicted_breach_time: Предсказанное время достижения лимита

    Returns:
        dict с результатом отправки оповещения
    """
    try:
        from src.services.notifications.worker import send_admin_notification

        # Формируем сообщение
        alert_level = "🔴 CRITICAL" if alert_type == "critical" else "⚠️ WARNING"
        message = (
            f"{alert_level}: Rate Limit Alert\n\n"
            f"Account: {account_id}\n"
            f"Endpoint: {endpoint_type}\n"
            f"Usage: {usage_percent:.1f}%\n"
        )

        if predicted_breach_time:
            message += f"Predicted breach: {predicted_breach_time}\n"

        message += "\nPlease take action to avoid rate limit violations."

        # Отправляем уведомление
        notification_result = _run_async(send_admin_notification(
            title=f"Rate Limit {alert_type.upper()}",
            message=message,
            notification_type="rate_limit_alert"
        ))

        return {
            "success": True,
            "account_id": account_id,
            "alert_type": alert_type,
            "notification_sent": True,
            "notification_result": notification_result
        }

    except Exception as e:
        logger.exception(f"Error triggering alert for account {account_id}")
        return {
            "success": False,
            "account_id": account_id,
            "alert_type": alert_type,
            "notification_sent": False,
            "error": str(e)
        }


def update_predictions_for_account_sync(account_id: str) -> Dict[str, Any]:
    """
    Обновляет предсказания для аккаунта (sync wrapper).

    Args:
        account_id: ID аккаунта

    Returns:
        dict с обновлёнными предсказаниями
    """
    try:
        from src.services.rate_limit_predictor import rate_limit_predictor

        predictions = _run_async(rate_limit_predictor.update_predictions(account_id))

        return {
            "success": True,
            "account_id": account_id,
            "predictions_updated": len(predictions),
            "predictions": [p.to_dict() for p in predictions]
        }

    except Exception as e:
        logger.exception(f"Error updating predictions for account {account_id}")
        return {
            "success": False,
            "account_id": account_id,
            "predictions_updated": 0,
            "error": str(e)
        }


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.rate_limit_monitor', bind=True, max_retries=3)
    def rate_limit_monitor_task(self):
        """
        Celery task: проверяет использование лимитов для всех аккаунтов и запускает оповещения.

        Для каждого аккаунта:
        1. Обновляет предсказания через RateLimitPredictor
        2. Проверяет использование лимитов
        3. Если превышен порог - запускает оповещение
        4. Логирует результаты

        Автоматически повторяется при ошибке (до 3 раз с экспоненциальной задержкой).
        """
        logger.info("[worker] rate_limit_monitor_task started")

        try:
            # Получаем глобальный статус
            check_result = check_all_rate_limits_sync()

            if not check_result.get("success"):
                logger.error("Failed to check rate limits")
                return {
                    "success": False,
                    "error": check_result.get("error"),
                    "alerts_triggered": 0
                }

            global_status = check_result.get("global_status", {})
            accounts = check_result.get("accounts", [])

            logger.info(
                f"Checking rate limits for {len(accounts)} accounts: "
                f"{global_status.get('ok_accounts', 0)} OK, "
                f"{global_status.get('warning_accounts', 0)} WARNING, "
                f"{global_status.get('critical_accounts', 0)} CRITICAL"
            )

            results = {
                "success": True,
                "total_accounts": len(accounts),
                "ok_accounts": global_status.get("ok_accounts", 0),
                "warning_accounts": global_status.get("warning_accounts", 0),
                "critical_accounts": global_status.get("critical_accounts", 0),
                "alerts_triggered": 0,
                "accounts_checked": []
            }

            # Проверяем каждый аккаунт
            for account_check in accounts:
                if not account_check.get("success"):
                    logger.error(f"Failed to check account {account_check.get('account_id')}")
                    continue

                account_id = account_check.get("account_id")
                status = account_check.get("status")
                predictions = account_check.get("predictions", [])

                # Обновляем предсказания
                update_result = update_predictions_for_account_sync(account_id)
                if not update_result.get("success"):
                    logger.warning(f"Failed to update predictions for account {account_id}")

                # Проверяем предупреждения
                for pred in predictions:
                    usage_percent = pred.get("usage_percent", 0)
                    endpoint_type = pred.get("endpoint_type", "unknown")
                    predicted_breach = pred.get("predicted_breach_time")
                    alert_triggered = pred.get("alert_triggered", False)

                    # Отправляем оповещение при необходимости
                    if alert_triggered or usage_percent >= 75:
                        alert_type = "critical" if usage_percent >= 90 else "warning"

                        alert_result = trigger_alert_sync(
                            account_id=account_id,
                            alert_type=alert_type,
                            usage_percent=usage_percent,
                            endpoint_type=endpoint_type,
                            predicted_breach_time=predicted_breach
                        )

                        if alert_result.get("notification_sent"):
                            results["alerts_triggered"] += 1
                            logger.warning(
                                f"Alert triggered for account {account_id}, "
                                f"endpoint {endpoint_type}: {usage_percent:.1f}%"
                            )

                results["accounts_checked"].append({
                    "account_id": account_id,
                    "status": status,
                    "max_usage_percent": account_check.get("max_usage_percent"),
                    "predictions_count": len(predictions)
                })

            logger.info(
                f"Rate limit monitor complete: "
                f"{results['alerts_triggered']} alerts triggered"
            )

            return results

        except Exception as e:
            logger.exception("Unhandled error in rate_limit_monitor_task")
            # Retry на recoverable errors
            if "redis" in str(e).lower() or "connection" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "error": str(e),
                "total_accounts": 0,
                "alerts_triggered": 0
            }

    @celery_app.task(name='tasks.rate_limit_check_account', bind=True, max_retries=3)
    def rate_limit_check_account_task(self, account_id: str):
        """
        Celery task: проверяет использование лимитов для конкретного аккаунта.

        Args:
            account_id: ID аккаунта для проверки

        Returns:
            dict с результатом проверки
        """
        logger.info(f"[worker] rate_limit_check_account_task for account {account_id}")

        try:
            # Обновляем предсказания
            update_result = update_predictions_for_account_sync(account_id)

            # Проверяем статус
            account_check = check_account_rate_limits_sync(account_id)

            if not account_check.get("success"):
                logger.error(f"Failed to check account {account_id}")
                return {
                    "success": False,
                    "account_id": account_id,
                    "error": account_check.get("error")
                }

            status = account_check.get("status")
            predictions = account_check.get("predictions", [])
            alerts_triggered = 0

            # Проверяем предупреждения
            for pred in predictions:
                usage_percent = pred.get("usage_percent", 0)
                endpoint_type = pred.get("endpoint_type", "unknown")
                predicted_breach = pred.get("predicted_breach_time")
                alert_triggered = pred.get("alert_triggered", False)

                if alert_triggered or usage_percent >= 75:
                    alert_type = "critical" if usage_percent >= 90 else "warning"

                    alert_result = trigger_alert_sync(
                        account_id=account_id,
                        alert_type=alert_type,
                        usage_percent=usage_percent,
                        endpoint_type=endpoint_type,
                        predicted_breach_time=predicted_breach
                    )

                    if alert_result.get("notification_sent"):
                        alerts_triggered += 1
                        logger.warning(
                            f"Alert triggered for account {account_id}, "
                            f"endpoint {endpoint_type}: {usage_percent:.1f}%"
                        )

            logger.info(
                f"Account {account_id} check complete: "
                f"status={status}, alerts={alerts_triggered}"
            )

            return {
                "success": True,
                "account_id": account_id,
                "status": status,
                "max_usage_percent": account_check.get("max_usage_percent"),
                "predictions_count": len(predictions),
                "alerts_triggered": alerts_triggered,
                "predictions_updated": update_result.get("predictions_updated", 0)
            }

        except Exception as e:
            logger.exception(f"Error in rate_limit_check_account_task for {account_id}")
            # Retry на recoverable errors
            if "redis" in str(e).lower() or "connection" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "account_id": account_id,
                "error": str(e),
                "alerts_triggered": 0
            }

    @celery_app.task(name='tasks.rate_limit_update_predictions', bind=True, max_retries=3)
    def rate_limit_update_predictions_task(self, account_id: Optional[str] = None):
        """
        Celery task: обновляет предсказания для аккаунта или всех аккаунтов.

        Args:
            account_id: ID аккаунта (опционально, если None - обновляет все)

        Returns:
            dict с результатом обновления
        """
        logger.info(f"[worker] rate_limit_update_predictions_task for account {account_id or 'all'}")

        try:
            from src.services.multi_account_rate_limiter import MultiAccountRateLimiter

            limiter = MultiAccountRateLimiter()

            if account_id:
                # Обновляем один аккаунт
                result = update_predictions_for_account_sync(account_id)
                return result
            else:
                # Обновляем все аккаунты
                accounts = _run_async(limiter.get_all_accounts())
                results = {
                    "success": True,
                    "total_accounts": len(accounts),
                    "updated_accounts": 0,
                    "failed_accounts": 0,
                    "accounts": []
                }

                for account in accounts:
                    acc_id = account.get("account_id")
                    if acc_id:
                        result = update_predictions_for_account_sync(acc_id)
                        results["accounts"].append(result)

                        if result.get("success"):
                            results["updated_accounts"] += 1
                        else:
                            results["failed_accounts"] += 1

                logger.info(
                    f"Updated predictions for {results['updated_accounts']} accounts, "
                    f"{results['failed_accounts']} failed"
                )

                return results

        except Exception as e:
            logger.exception("Error in rate_limit_update_predictions_task")
            # Retry на recoverable errors
            if "redis" in str(e).lower() or "connection" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "error": str(e),
                "updated_accounts": 0
            }


# ============================================================================
# Public API
# ============================================================================

def monitor_rate_limits_async() -> bool:
    """
    Запускает асинхронную проверку лимитов для всех аккаунтов.

    Использует Celery если доступен, иначе выполняет синхронно.

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.rate_limit_monitor')
            logger.info("Enqueued rate limit monitor for all accounts")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info("Checking rate limits synchronously")
    try:
        task = rate_limit_monitor_task()
        return task.get("success", False)
    except Exception:
        logger.exception("Failed to check rate limits synchronously")
        return False


def check_account_rate_limits_async(account_id: str) -> bool:
    """
    Запускает асинхронную проверку лимитов для конкретного аккаунта.

    Args:
        account_id: ID аккаунта

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.rate_limit_check_account', args=[str(account_id)])
            logger.info(f"Enqueued rate limit check for account {account_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Checking rate limits synchronously for account {account_id}")
    try:
        task = rate_limit_check_account_task(str(account_id))
        return task.get("success", False)
    except Exception:
        logger.exception(f"Failed to check rate limits synchronously for account {account_id}")
        return False


def update_predictions_async(account_id: Optional[str] = None) -> bool:
    """
    Запускает асинхронное обновление предсказаний.

    Args:
        account_id: ID аккаунта (опционально)

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.rate_limit_update_predictions', args=[account_id])
            logger.info(f"Enqueued predictions update for account {account_id or 'all'}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Updating predictions synchronously for account {account_id or 'all'}")
    try:
        task = rate_limit_update_predictions_task(account_id)
        return task.get("success", False)
    except Exception:
        logger.exception("Failed to update predictions synchronously")
        return False
