"""
Celery tasks для проверки здоровья Telegram сессий и автоматического обновления.

Включает:
- Периодическую проверку здоровья всех активных Telegram сессий
- Автоматический запуск обновления при обнаружении проблем
- Интеграцию с TelegramSessionMonitor и TelegramSessionService
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
    return Celery('telegram_broadcast', broker=broker)


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


def check_session_health_sync(account_id: str) -> Dict[str, Any]:
    """
    Проверяет здоровье Telegram сессии (sync wrapper для async).

    Args:
        account_id: ID аккаунта Telegram

    Returns:
        dict с результатами проверки: is_healthy, health_status, error_message, etc.
    """
    try:
        from src.services.telegram_session_monitor import get_telegram_session_monitor

        monitor = get_telegram_session_monitor()
        health_status = _run_async(monitor.check_account_health(account_id))

        return {
            "success": True,
            "account_id": account_id,
            "is_healthy": health_status.is_healthy,
            "health_status": health_status.health_status.value if hasattr(health_status.health_status, 'value') else str(health_status.health_status),
            "consecutive_failures": health_status.consecutive_failures,
            "last_failure_type": health_status.last_failure_type,
            "last_error_message": health_status.last_error_message,
            "last_check": health_status.last_check.isoformat() if health_status.last_check else None,
            "session_expires_at": health_status.session_expires_at.isoformat() if health_status.session_expires_at else None,
            "time_until_expiry": health_status.time_until_expiry,
        }

    except Exception as e:
        logger.exception(f"Error checking health for Telegram session {account_id}")
        return {
            "success": False,
            "account_id": account_id,
            "error": str(e),
            "is_healthy": False
        }


def get_active_telegram_accounts() -> List[Dict[str, Any]]:
    """
    Получает список всех активных Telegram аккаунтов из базы данных.

    Returns:
        Список dict с id и phone активных аккаунтов
    """
    try:
        from database import SessionLocal
        from src.models.telegram import TelegramAccount

        db = SessionLocal()
        try:
            accounts = db.query(TelegramAccount).filter(
                TelegramAccount.is_active == True
            ).all()

            return [
                {
                    "id": str(account.id),
                    "phone": account.phone or f"Account {account.id}",
                    "username": account.username,
                    "is_active": account.is_active
                }
                for account in accounts
            ]

        finally:
            db.close()

    except Exception as e:
        logger.exception("Error getting active Telegram accounts")
        return []


def get_expiring_sessions() -> List[Dict[str, Any]]:
    """
    Получает список Telegram сессий, требующих обновления.

    Returns:
        Список dict с информацией о сессиях, требующих обновления
    """
    try:
        from database import SessionLocal
        from src.models.telegram import TelegramAccount, SessionHealthStatus

        db = SessionLocal()
        try:
            # Находим аккаунты с включенным auto_refresh и статусами HEALTHY или EXPIRING
            accounts = db.query(TelegramAccount).filter(
                TelegramAccount.is_active == True,
                TelegramAccount.auto_refresh_enabled == True,
                TelegramAccount.session_health_status.in_([
                    SessionHealthStatus.HEALTHY,
                    SessionHealthStatus.EXPIRING
                ])
            ).all()

            expiring_accounts = []
            for account in accounts:
                # Проверяем нужно ли обновление (через should_auto_refresh)
                if account.should_auto_refresh():
                    expiring_accounts.append({
                        "id": str(account.id),
                        "phone": account.phone or f"Account {account.id}",
                        "username": account.username,
                        "session_expires_at": account.session_expires_at.isoformat() if account.session_expires_at else None,
                        "health_status": account.session_health_status.value if hasattr(account.session_health_status, 'value') else str(account.session_health_status)
                    })

            return expiring_accounts

        finally:
            db.close()

    except Exception as e:
        logger.exception("Error getting expiring sessions")
        return []


def backup_single_session_sync(account_id: str) -> Dict[str, Any]:
    """
    Создает backup одной Telegram сессии с шифрованием (sync wrapper для async).

    Args:
        account_id: ID аккаунта Telegram

    Returns:
        dict с результатами backup: success, backup_path, file_size, etc.
    """
    try:
        from database import SessionLocal
        from src.services.telegram_session_service import get_telegram_session_service
        from src.services.encryption import encryption_service
        from pathlib import Path
        import json
        from datetime import datetime

        db = SessionLocal()
        try:
            service = get_telegram_session_service()

            # Получаем аккаунт из БД
            from src.models.telegram import TelegramAccount
            account = db.query(TelegramAccount).filter(
                TelegramAccount.id == account_id
            ).first()

            if not account:
                return {
                    "success": False,
                    "account_id": account_id,
                    "error": "Account not found"
                }

            # Создаем структуру backup данных
            backup_data = {
                "account_id": str(account.id),
                "phone": account.phone,
                "username": account.username,
                "encrypted_session": account.encrypted_session,
                "totp_secret": account.totp_secret,
                "created_at": datetime.now().isoformat(),
                "session_expires_at": account.session_expires_at.isoformat() if account.session_expires_at else None,
                "health_status": account.session_health_status.value if hasattr(account.session_health_status, 'value') else str(account.session_health_status)
            }

            # Сериализуем в JSON
            json_data = json.dumps(backup_data, indent=2)

            # Шифруем данные
            encrypted_data = encryption_service.encrypt(json_data)

            # Создаем имя файла: telegram_session_{account_id}_{timestamp}.enc
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"telegram_session_{account_id}_{timestamp}.enc"

            # Получаем путь для backup из settings
            from src.config import settings
            backup_dir = Path(settings.SESSION_BACKUP_PATH)
            backup_dir.mkdir(parents=True, exist_ok=True)

            backup_file_path = backup_dir / filename

            # Записываем зашифрованный backup
            with open(backup_file_path, 'wb') as f:
                f.write(encrypted_data.encode('utf-8'))

            file_size = backup_file_path.stat().st_size

            logger.info(f"Created encrypted backup for account {account_id}: {backup_file_path}")

            return {
                "success": True,
                "account_id": account_id,
                "phone": account.phone,
                "username": account.username,
                "backup_path": str(backup_file_path),
                "filename": filename,
                "file_size_bytes": file_size,
                "created_at": timestamp
            }

        finally:
            db.close()

    except Exception as e:
        logger.exception(f"Error creating backup for Telegram session {account_id}")
        return {
            "success": False,
            "account_id": account_id,
            "error": str(e)
        }


def backup_all_sessions_sync() -> Dict[str, Any]:
    """
    Создает backup всех активных Telegram сессий с шифрованием (sync wrapper для async).

    Returns:
        dict с результатами backup: success, total, backed_up, failed, etc.
    """
    try:
        from database import SessionLocal

        # Получаем все активные аккаунты
        active_accounts = get_active_telegram_accounts()
        total_sessions = len(active_accounts)

        if total_sessions == 0:
            logger.info("No active Telegram accounts found, backup complete")
            return {
                "success": True,
                "total_sessions": 0,
                "backed_up": 0,
                "failed": 0,
                "sessions": []
            }

        logger.info(f"Backing up {total_sessions} Telegram sessions")

        results = {
            "success": True,
            "total_sessions": total_sessions,
            "backed_up": 0,
            "failed": 0,
            "sessions": []
        }

        # Бэкапим каждую сессию
        for account_info in active_accounts:
            account_id = account_info["id"]

            try:
                backup_result = backup_single_session_sync(account_id)

                if backup_result.get("success"):
                    results["backed_up"] += 1
                    logger.info(f"Successfully backed up session for account {account_id}")

                    results["sessions"].append({
                        "account_id": account_id,
                        "phone": account_info.get("phone"),
                        "username": account_info.get("username"),
                        "backed_up": True,
                        "backup_path": backup_result.get("backup_path"),
                        "file_size_bytes": backup_result.get("file_size_bytes")
                    })
                else:
                    results["failed"] += 1
                    logger.error(f"Failed to back up session for account {account_id}: {backup_result.get('error')}")

                    results["sessions"].append({
                        "account_id": account_id,
                        "phone": account_info.get("phone"),
                        "username": account_info.get("username"),
                        "backed_up": False,
                        "error": backup_result.get("error")
                    })

            except Exception as e:
                results["failed"] += 1
                logger.error(f"Exception backing up session for account {account_id}: {e}")

                results["sessions"].append({
                    "account_id": account_id,
                    "phone": account_info.get("phone"),
                    "username": account_info.get("username"),
                    "backed_up": False,
                    "error": str(e)
                })

        logger.info(
            f"Session backup complete: {results['backed_up']} backed up, "
            f"{results['failed']} failed"
        )

        return results

    except Exception as e:
        logger.exception("Error in backup_all_sessions_sync")
        return {
            "success": False,
            "total_sessions": 0,
            "backed_up": 0,
            "failed": 0,
            "error": str(e)
        }


def refresh_expiring_sessions_sync() -> Dict[str, Any]:
    """
    Обновляет все Telegram сессии, требующие обновления (sync wrapper для async).

    Returns:
        dict с результатами обновления: success, total, refreshed, failed, etc.
    """
    try:
        from database import SessionLocal
        from src.services.telegram_session_service import get_telegram_session_service

        # Получаем список сессий для обновления
        expiring_sessions = get_expiring_sessions()
        total_sessions = len(expiring_sessions)

        if total_sessions == 0:
            logger.info("No sessions require refresh")
            return {
                "success": True,
                "total_sessions": 0,
                "refreshed": 0,
                "failed": 0,
                "sessions": []
            }

        logger.info(f"Refreshing {total_sessions} Telegram sessions")

        service = get_telegram_session_service()
        db = SessionLocal()

        results = {
            "success": True,
            "total_sessions": total_sessions,
            "refreshed": 0,
            "failed": 0,
            "sessions": []
        }

        try:
            for session_info in expiring_sessions:
                account_id = session_info["id"]

                try:
                    # Вызываем async refresh_session через sync wrapper
                    _run_async(service.refresh_session(db, account_id))

                    results["refreshed"] += 1
                    logger.info(f"Successfully refreshed session for account {account_id}")

                    results["sessions"].append({
                        "account_id": account_id,
                        "phone": session_info.get("phone"),
                        "username": session_info.get("username"),
                        "refreshed": True,
                        "success": True
                    })

                except Exception as e:
                    results["failed"] += 1
                    logger.error(f"Failed to refresh session for account {account_id}: {e}")

                    results["sessions"].append({
                        "account_id": account_id,
                        "phone": session_info.get("phone"),
                        "username": session_info.get("username"),
                        "refreshed": False,
                        "success": False,
                        "error": str(e)
                    })

            logger.info(
                f"Session refresh complete: {results['refreshed']} refreshed, "
                f"{results['failed']} failed"
            )

            return results

        finally:
            db.close()

    except Exception as e:
        logger.exception("Error in refresh_expiring_sessions_sync")
        return {
            "success": False,
            "total_sessions": 0,
            "refreshed": 0,
            "failed": 0,
            "error": str(e)
        }


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.check_all_telegram_sessions_health', bind=True, max_retries=3)
    def check_all_telegram_sessions_health_task(self):
        """
        Celery task: проверяет здоровье всех активных Telegram сессий.

        Для каждой сессии:
        1. Проверяет здоровье через TelegramSessionMonitor
        2. Логирует результаты
        3. Сохраняет метрики в Redis

        Автоматически повторяется при ошибке (до 3 раз с экспоненциальной задержкой).
        """
        logger.info("[worker] check_all_telegram_sessions_health_task started")

        try:
            # Получаем все активные Telegram аккаунты
            active_accounts = get_active_telegram_accounts()
            total_accounts = len(active_accounts)

            if total_accounts == 0:
                logger.info("No active Telegram accounts found, health check complete")
                return {
                    "success": True,
                    "total_accounts": 0,
                    "healthy_accounts": 0,
                    "unhealthy_accounts": 0,
                    "accounts": []
                }

            logger.info(f"Checking health for {total_accounts} active Telegram accounts")

            results = {
                "success": True,
                "total_accounts": total_accounts,
                "healthy_accounts": 0,
                "unhealthy_accounts": 0,
                "accounts": []
            }

            # Проверяем здоровье каждой сессии
            for account_info in active_accounts:
                account_id = account_info["id"]

                health_result = check_session_health_sync(account_id)

                if not health_result.get("success"):
                    logger.error(f"Failed to check health for Telegram account {account_id}")
                    continue

                is_healthy = health_result.get("is_healthy", True)

                if is_healthy:
                    results["healthy_accounts"] += 1
                    logger.debug(f"Telegram session {account_id} is healthy")
                else:
                    results["unhealthy_accounts"] += 1
                    health_status = health_result.get("health_status", "unknown")
                    error_message = health_result.get("last_error_message", "Unknown error")

                    logger.warning(
                        f"Telegram session {account_id} is unhealthy: "
                        f"{health_status} - {error_message}"
                    )

                    results["accounts"].append({
                        "account_id": account_id,
                        "phone": account_info.get("phone"),
                        "username": account_info.get("username"),
                        "is_healthy": False,
                        "health_status": health_status,
                        "error_message": error_message,
                        "session_expires_at": health_result.get("session_expires_at"),
                        "time_until_expiry": health_result.get("time_until_expiry")
                    })

            logger.info(
                f"Telegram session health check complete: {results['healthy_accounts']} healthy, "
                f"{results['unhealthy_accounts']} unhealthy"
            )

            return results

        except Exception as e:
            logger.exception("Unhandled error in check_all_telegram_sessions_health_task")
            # Retry на recoverable errors
            if "database" in str(e).lower() or "connection" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "error": str(e),
                "total_accounts": 0,
                "healthy_accounts": 0,
                "unhealthy_accounts": 0
            }

    @celery_app.task(name='tasks.check_telegram_session_health', bind=True, max_retries=3)
    def check_single_session_health_task(self, account_id: str):
        """
        Celery task: проверяет здоровье конкретной Telegram сессии.

        Args:
            account_id: ID аккаунта Telegram для проверки

        Returns:
            dict с результатом проверки здоровья
        """
        logger.info(f"[worker] check_single_session_health_task for Telegram account {account_id}")

        try:
            health_result = check_session_health_sync(account_id)

            if not health_result.get("is_healthy"):
                health_status = health_result.get("health_status", "unknown")
                error_message = health_result.get("last_error_message", "Unknown error")

                logger.warning(
                    f"Telegram session {account_id} is unhealthy: "
                    f"{health_status} - {error_message}"
                )
            else:
                logger.info(f"Telegram session {account_id} is healthy")

            return health_result

        except Exception as e:
            logger.exception(f"Error in check_single_session_health_task for {account_id}")
            # Retry на recoverable errors
            if "database" in str(e).lower() or "connection" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "account_id": account_id,
                "error": str(e),
                "is_healthy": False
            }

    @celery_app.task(name='tasks.refresh_expiring_sessions', bind=True, max_retries=3)
    def refresh_expiring_sessions_task(self):
        """
        Celery task: обновляет все Telegram сессии, требующие обновления.

        Для каждой сессии:
        1. Проверяет требуется ли обновление (через should_auto_refresh)
        2. Если требуется - обновляет через TelegramSessionService
        3. Логирует результаты

        Автоматически повторяется при ошибке (до 3 раз с экспоненциальной задержкой).
        """
        logger.info("[worker] refresh_expiring_sessions_task started")

        try:
            refresh_result = refresh_expiring_sessions_sync()

            if refresh_result.get("success"):
                total = refresh_result.get("total_sessions", 0)
                refreshed = refresh_result.get("refreshed", 0)
                failed = refresh_result.get("failed", 0)

                logger.info(
                    f"Refresh task completed: {total} sessions, "
                    f"{refreshed} refreshed, {failed} failed"
                )
            else:
                logger.error(f"Refresh task failed: {refresh_result.get('error')}")

            return refresh_result

        except Exception as e:
            logger.exception("Unhandled error in refresh_expiring_sessions_task")
            # Retry на recoverable errors
            if "database" in str(e).lower() or "connection" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "error": str(e),
                "total_sessions": 0,
                "refreshed": 0,
                "failed": 0
            }

    @celery_app.task(name='tasks.backup_all_sessions', bind=True, max_retries=3)
    def backup_all_sessions_task(self):
        """
        Celery task: создает backup всех активных Telegram сессий с шифрованием.

        Для каждой сессии:
        1. Собирает данные сессии (encrypted_session, totp_secret, metadata)
        2. Шифрует данные с помощью EncryptionService
        3. Сохраняет в файл с именем telegram_session_{account_id}_{timestamp}.enc
        4. Логирует результаты

        Файлы сохраняются в settings.SESSION_BACKUP_PATH

        Автоматически повторяется при ошибке (до 3 раз с экспоненциальной задержкой).
        """
        logger.info("[worker] backup_all_sessions_task started")

        try:
            backup_result = backup_all_sessions_sync()

            if backup_result.get("success"):
                total = backup_result.get("total_sessions", 0)
                backed_up = backup_result.get("backed_up", 0)
                failed = backup_result.get("failed", 0)

                logger.info(
                    f"Backup task completed: {total} sessions, "
                    f"{backed_up} backed up, {failed} failed"
                )
            else:
                logger.error(f"Backup task failed: {backup_result.get('error')}")

            return backup_result

        except Exception as e:
            logger.exception("Unhandled error in backup_all_sessions_task")
            # Retry на recoverable errors
            if "database" in str(e).lower() or "connection" in str(e).lower() or "io" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "error": str(e),
                "total_sessions": 0,
                "backed_up": 0,
                "failed": 0
            }

    @celery_app.task(name='tasks.backup_single_session', bind=True, max_retries=3)
    def backup_single_session_task(self, account_id: str):
        """
        Celery task: создает backup конкретной Telegram сессии с шифрованием.

        Args:
            account_id: ID аккаунта Telegram для backup

        Для сессии:
        1. Собирает данные сессии (encrypted_session, totp_secret, metadata)
        2. Шифрует данные с помощью EncryptionService
        3. Сохраняет в файл с именем telegram_session_{account_id}_{timestamp}.enc
        4. Логирует результаты

        Файлы сохраняются в settings.SESSION_BACKUP_PATH

        Автоматически повторяется при ошибке (до 3 раз с экспоненциальной задержкой).
        """
        logger.info(f"[worker] backup_single_session_task for Telegram account {account_id}")

        try:
            backup_result = backup_single_session_sync(account_id)

            if backup_result.get("success"):
                backup_path = backup_result.get("backup_path")
                file_size = backup_result.get("file_size_bytes")

                logger.info(
                    f"Backup created for account {account_id}: "
                    f"path={backup_path}, size={file_size} bytes"
                )
            else:
                logger.error(
                    f"Backup failed for account {account_id}: "
                    f"{backup_result.get('error')}"
                )

            return backup_result

        except Exception as e:
            logger.exception(f"Error in backup_single_session_task for {account_id}")
            # Retry на recoverable errors
            if "database" in str(e).lower() or "connection" in str(e).lower() or "io" in str(e).lower():
                raise self.retry(countdown=30 * (self.request.retries + 1))
            return {
                "success": False,
                "account_id": account_id,
                "error": str(e)
            }


# ============================================================================
# Public API
# ============================================================================

def check_all_telegram_sessions_async() -> bool:
    """
    Запускает асинхронную проверку здоровья всех Telegram сессий.

    Использует Celery если доступен, иначе выполняет синхронно.

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.check_all_telegram_sessions_health')
            logger.info("Enqueued health check for all Telegram sessions")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info("Checking Telegram session health synchronously")
    try:
        task = check_all_telegram_sessions_health_task()
        return task.get("success", False)
    except Exception:
        logger.exception("Failed to check Telegram session health synchronously")
        return False


def check_telegram_session_async(account_id: str) -> bool:
    """
    Запускает асинхронную проверку здоровья конкретной Telegram сессии.

    Args:
        account_id: ID аккаунта Telegram

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.check_telegram_session_health', args=[str(account_id)])
            logger.info(f"Enqueued health check for Telegram session {account_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Checking Telegram session health synchronously for {account_id}")
    try:
        task = check_single_session_health_task(str(account_id))
        return task.get("success", False)
    except Exception:
        logger.exception(f"Failed to check Telegram session health synchronously for {account_id}")
        return False


def refresh_expiring_sessions_async() -> bool:
    """
    Запускает асинхронное обновление всех Telegram сессий, требующих обновления.

    Использует Celery если доступен, иначе выполняет синхронно.

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.refresh_expiring_sessions')
            logger.info("Enqueued refresh for all expiring Telegram sessions")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info("Refreshing Telegram sessions synchronously")
    try:
        task = refresh_expiring_sessions_task()
        return task.get("success", False)
    except Exception:
        logger.exception("Failed to refresh Telegram sessions synchronously")
        return False


def backup_all_sessions_async() -> bool:
    """
    Запускает асинхронное создание backup всех активных Telegram сессий.

    Использует Celery если доступен, иначе выполняет синхронно.

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.backup_all_sessions')
            logger.info("Enqueued backup for all active Telegram sessions")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info("Backing up Telegram sessions synchronously")
    try:
        task = backup_all_sessions_task()
        return task.get("success", False)
    except Exception:
        logger.exception("Failed to back up Telegram sessions synchronously")
        return False


def backup_single_session_async(account_id: str) -> bool:
    """
    Запускает асинхронное создание backup конкретной Telegram сессии.

    Args:
        account_id: ID аккаунта Telegram

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and (os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')):
        app = _get_celery_app()
        try:
            app.send_task('tasks.backup_single_session', args=[str(account_id)])
            logger.info(f"Enqueued backup for Telegram session {account_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Backing up Telegram session synchronously for {account_id}")
    try:
        task = backup_single_session_task(str(account_id))
        return task.get("success", False)
    except Exception:
        logger.exception(f"Failed to back up Telegram session synchronously for {account_id}")
        return False
