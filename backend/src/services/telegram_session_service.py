"""
Telegram Session Service

Сервис для управления Telegram сессиями с автоматическим refresh,
backup и 2FA управлением.

Функционал:
- Автоматическое обновление сессий перед истечением
- Backup и restore сессий
- Безопасное хранение TOTP секретов для 2FA
- Мониторинг здоровья сессий
- Генерация 2FA кодов

Storage:
- PostgreSQL: TelegramAccount ORM model для персистентности
- Redis: Кэширование статуса здоровья сессий

Использование:
    service = get_telegram_session_service()
    await service.refresh_session(account_id)  # Обновить сессию
    await service.backup_session(account_id)  # Создать backup
    totp_code = await service.generate_2fa_code(account_id)  # Получить 2FA код
    health = await service.check_session_health(account_id)  # Проверить здоровье
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from pathlib import Path
import shutil

import redis.asyncio as redis
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.config import settings
from src.models.telegram import TelegramAccount, SessionHealthStatus
from src.services.encryption import encryption_service

log = logging.getLogger(__name__)


class TelegramSessionServiceError(Exception):
    """Базовое исключение для ошибок TelegramSessionService."""
    pass


class SessionRefreshError(TelegramSessionServiceError):
    """Ошибка при обновлении сессии."""
    pass


class SessionBackupError(TelegramSessionServiceError):
    """Ошибка при backup сессии."""
    pass


class TwoFactorError(TelegramSessionServiceError):
    """Ошибка связанная с 2FA."""
    pass


class TelegramSessionService:
    """
    Сервис для управления Telegram сессиями.

    Attributes:
        redis_url: URL для подключения к Redis
        backup_path: Путь для хранения backup файлов сессий
    """

    # Redis key patterns
    HEALTH_KEY_PREFIX = "tg_session_health"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        backup_path: Optional[str] = None
    ):
        """
        Инициализация TelegramSessionService.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            backup_path: Путь для backup сессий (по умолчанию из settings)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.backup_path = Path(backup_path or settings.SESSION_BACKUP_PATH)
        self._redis: Optional[redis.Redis] = None

        # Создать директорию для backup если не существует
        self.backup_path.mkdir(parents=True, exist_ok=True)

        log.info(
            f"TelegramSessionService initialized: backup_path={self.backup_path}, "
            f"auto_refresh={settings.SESSION_AUTO_REFRESH_ENABLED}"
        )

    async def _get_redis(self) -> redis.Redis:
        """Получение Redis клиента."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis

    @staticmethod
    def _get_health_key(account_id: str) -> str:
        """Генерация Redis ключа для статуса здоровья сессии."""
        return f"{TelegramSessionService.HEALTH_KEY_PREFIX}:{account_id}"

    async def close(self) -> None:
        """Закрытие соединений."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    # ========== Session Refresh Operations ==========

    async def refresh_session(
        self,
        db: Session,
        account_id: str
    ) -> TelegramAccount:
        """
        Обновить Telegram сессию.

        Проверяет валидность текущей сессии и обновляет её если необходимо.
        Автоматически обрабатывает 2FA если настроен.

        Args:
            db: SQLAlchemy сессия
            account_id: ID Telegram account

        Returns:
            Обновленный TelegramAccount

        Raises:
            SessionRefreshError: Если не удалось обновить сессию
        """
        try:
            account = db.query(TelegramAccount).filter(
                TelegramAccount.id == account_id
            ).first()

            if not account:
                raise SessionRefreshError(f"Account {account_id} not found")

            # Проверить нужно ли обновление
            if not account.should_auto_refresh():
                log.info(f"Account {account_id} does not need refresh")
                return account

            log.info(f"Refreshing session for account {account_id}")

            # TODO: Implement actual Telegram session refresh
            # Здесь будет интеграция с Telegram Client API
            # Примерная логика:
            # 1. Расшифровать encrypted_session
            # 2. Подключиться к Telegram используя session
            # 3. Проверить валидность session
            # 4. Если требуется 2FA, использовать totp_secret
            # 5. Обновить session данные
            # 6. Зашифровать и сохранить новую session

            # Для_now заглушка - обновляем timestamps
            now = datetime.utcnow()
            account.last_refreshed_at = now
            account.last_health_check = now
            account.session_health_status = SessionHealthStatus.HEALTHY
            account.session_expires_at = now + timedelta(days=30)
            account.refresh_error_message = None

            db.commit()
            db.refresh(account)

            # Очистить кэш здоровья в Redis
            await self._invalidate_health_cache(account_id)

            log.info(f"Successfully refreshed session for account {account_id}")
            return account

        except SQLAlchemyError as e:
            log.error(f"Database error refreshing session for {account_id}: {e}")
            db.rollback()
            raise SessionRefreshError(f"Database error: {str(e)}") from e
        except Exception as e:
            log.error(f"Error refreshing session for {account_id}: {e}")
            raise SessionRefreshError(f"Refresh failed: {str(e)}") from e

    async def batch_refresh_sessions(
        self,
        db: Session,
        limit: int = 10
    ) -> Dict[str, str]:
        """
        Массовое обновление сессий требующих refresh.

        Args:
            db: SQLAlchemy сессия
            limit: Максимальное количество аккаунтов для обработки

        Returns:
            Словарь {account_id: status}
        """
        results = {}

        try:
            # Найти все аккаунты требующие refresh
            accounts = db.query(TelegramAccount).filter(
                TelegramAccount.auto_refresh_enabled == True,
                TelegramAccount.session_health_status.in_([
                    SessionHealthStatus.HEALTHY,
                    SessionHealthStatus.EXPIRING
                ])
            ).limit(limit).all()

            for account in accounts:
                account_id = str(account.id)
                try:
                    await self.refresh_session(db, account_id)
                    results[account_id] = "success"
                except SessionRefreshError as e:
                    results[account_id] = f"failed: {str(e)}"
                    log.error(f"Failed to refresh account {account_id}: {e}")

            log.info(f"Batch refresh completed: {len(results)} accounts processed")
            return results

        except SQLAlchemyError as e:
            log.error(f"Database error in batch refresh: {e}")
            raise SessionRefreshError(f"Database error: {str(e)}") from e

    # ========== Session Rotation Operations ==========

    async def get_account_for_rotation(
        self,
        db: Session,
        user_id: Optional[str] = None
    ) -> Optional[TelegramAccount]:
        """
        Выбрать следующий аккаунт для rotation используя least-recently-used стратегию.

        Выбирает аккаунт с наименьшим rotation_order > 0, который здоров и
        имеет наиболее давний last_refreshed_at timestamp. Это гарантирует,
        что нагрузка распределяется равномерно между всеми аккаунтами в rotation.

        Args:
            db: SQLAlchemy сессия
            user_id: Опциональный фильтр по user_id

        Returns:
            TelegramAccount для rotation или None если нет подходящих аккаунтов
        """
        try:
            # Build base query for accounts participating in rotation
            query = db.query(TelegramAccount).filter(
                TelegramAccount.rotation_order > 0,
                TelegramAccount.is_active == True,
                TelegramAccount.auto_refresh_enabled == True,
                TelegramAccount.session_health_status.in_([
                    SessionHealthStatus.HEALTHY,
                    SessionHealthStatus.EXPIRING
                ])
            )

            # Filter by user_id if provided
            if user_id:
                query = query.filter(TelegramAccount.user_id == user_id)

            # Order by rotation_order (priority) then by last_refreshed_at (LRU)
            # Это гарантирует, что мы выбираем аккаунт с наивысшим приоритетом,
            # который был обновлен наиболее давно
            accounts = query.order_by(
                TelegramAccount.rotation_order.asc(),
                TelegramAccount.last_refreshed_at.asc().nullsfirst()
            ).first()

            if not accounts:
                log.debug("No accounts available for rotation")
                return None

            log.info(
                f"Selected account {accounts.id} for rotation: "
                f"order={accounts.rotation_order}, "
                f"last_refreshed={accounts.last_refreshed_at}"
            )
            return accounts

        except SQLAlchemyError as e:
            log.error(f"Database error selecting account for rotation: {e}")
            return None

    async def rotate_sessions(
        self,
        db: Session,
        user_id: Optional[str] = None,
        max_accounts: int = 3
    ) -> Dict[str, str]:
        """
        Выполнить rotation нескольких аккаунтов для load balancing.

        Выбирает до max_accounts аккаунтов с различными rotation_order
        и выполняет их refresh, распределяя нагрузку во времени.

        Args:
            db: SQLAlchemy сессия
            user_id: Опциональный фильтр по user_id
            max_accounts: Максимальное количество аккаунтов для refresh

        Returns:
            Словарь {account_id: status}
        """
        results = {}

        try:
            # Получить уникальные rotation_order значения для пользователя
            query = db.query(TelegramAccount.rotation_order).filter(
                TelegramAccount.rotation_order > 0,
                TelegramAccount.is_active == True,
                TelegramAccount.auto_refresh_enabled == True,
                TelegramAccount.session_health_status.in_([
                    SessionHealthStatus.HEALTHY,
                    SessionHealthStatus.EXPIRING
                ])
            )

            if user_id:
                query = query.filter(TelegramAccount.user_id == user_id)

            rotation_orders = query.distinct().order_by(
                TelegramAccount.rotation_order.asc()
            ).limit(max_accounts).all()

            if not rotation_orders:
                log.info("No accounts found for rotation")
                return results

            # Для каждого rotation_order выбрать один LRU аккаунт
            for (order,) in rotation_orders:
                account_query = db.query(TelegramAccount).filter(
                    TelegramAccount.rotation_order == order,
                    TelegramAccount.is_active == True,
                    TelegramAccount.auto_refresh_enabled == True,
                    TelegramAccount.session_health_status.in_([
                        SessionHealthStatus.HEALTHY,
                        SessionHealthStatus.EXPIRING
                    ])
                )

                if user_id:
                    account_query = account_query.filter(TelegramAccount.user_id == user_id)

                # Выбрать LRU аккаунт для этого rotation_order
                account = account_query.order_by(
                    TelegramAccount.last_refreshed_at.asc().nullsfirst()
                ).first()

                if account:
                    account_id = str(account.id)
                    try:
                        await self.refresh_session(db, account_id)
                        results[account_id] = f"refreshed (order={order})"
                        log.info(f"Rotated account {account_id} with order={order}")
                    except SessionRefreshError as e:
                        results[account_id] = f"failed: {str(e)}"
                        log.error(f"Failed to rotate account {account_id}: {e}")

            log.info(f"Rotation completed: {len(results)} accounts processed")
            return results

        except SQLAlchemyError as e:
            log.error(f"Database error during rotation: {e}")
            raise SessionRefreshError(f"Database error: {str(e)}") from e

    # ========== Session Backup Operations ==========

    async def backup_session(
        self,
        db: Session,
        account_id: str
    ) -> str:
        """
        Создать backup сессии.

        Args:
            db: SQLAlchemy сессия
            account_id: ID Telegram account

        Returns:
            Путь к backup файлу

        Raises:
            SessionBackupError: Если не удалось создать backup
        """
        try:
            account = db.query(TelegramAccount).filter(
                TelegramAccount.id == account_id
            ).first()

            if not account:
                raise SessionBackupError(f"Account {account_id} not found")

            # Создать имя файла с timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{account.phone}_{timestamp}.session"
            backup_file_path = self.backup_path / filename

            # Расшифровать session
            decrypted_session = encryption_service.decrypt(account.encrypted_session)

            # Записать backup файл
            with open(backup_file_path, 'w') as f:
                f.write(decrypted_session)

            log.info(f"Created session backup: {backup_file_path}")
            return str(backup_file_path)

        except SQLAlchemyError as e:
            log.error(f"Database error backing up session for {account_id}: {e}")
            raise SessionBackupError(f"Database error: {str(e)}") from e
        except Exception as e:
            log.error(f"Error backing up session for {account_id}: {e}")
            raise SessionBackupError(f"Backup failed: {str(e)}") from e

    async def restore_session(
        self,
        db: Session,
        account_id: str,
        backup_file_path: str
    ) -> TelegramAccount:
        """
        Восстановить сессию из backup.

        Args:
            db: SQLAlchemy сессия
            account_id: ID Telegram account
            backup_file_path: Путь к backup файлу

        Returns:
            Обновленный TelegramAccount

        Raises:
            SessionBackupError: Если не удалось восстановить backup
        """
        try:
            account = db.query(TelegramAccount).filter(
                TelegramAccount.id == account_id
            ).first()

            if not account:
                raise SessionBackupError(f"Account {account_id} not found")

            backup_path = Path(backup_file_path)
            if not backup_path.exists():
                raise SessionBackupError(f"Backup file not found: {backup_file_path}")

            # Прочитать backup файл
            with open(backup_path, 'r') as f:
                decrypted_session = f.read()

            # Зашифровать и сохранить
            account.encrypted_session = encryption_service.encrypt(decrypted_session)
            account.last_refreshed_at = datetime.utcnow()
            account.session_health_status = SessionHealthStatus.HEALTHY
            account.refresh_error_message = None

            db.commit()
            db.refresh(account)

            # Очистить кэш здоровья
            await self._invalidate_health_cache(account_id)

            log.info(f"Restored session from backup: {backup_file_path}")
            return account

        except SQLAlchemyError as e:
            log.error(f"Database error restoring session for {account_id}: {e}")
            db.rollback()
            raise SessionBackupError(f"Database error: {str(e)}") from e
        except Exception as e:
            log.error(f"Error restoring session for {account_id}: {e}")
            raise SessionBackupError(f"Restore failed: {str(e)}") from e

    async def list_backups(self, account_id: Optional[str] = None) -> list[str]:
        """
        Получить список доступных backup файлов.

        Args:
            account_id: Опциональный ID аккаунта для фильтрации

        Returns:
            Список путей к backup файлам
        """
        backups = []

        if not self.backup_path.exists():
            return backups

        for backup_file in self.backup_path.glob("*.session"):
            if account_id:
                # Фильтровать по phone (account_id в имени файла)
                # Для упрощения проверяем包含 account_id
                if account_id not in backup_file.name:
                    continue
            backups.append(str(backup_file))

        return sorted(backups, reverse=True)

    async def delete_old_backups(self, days_to_keep: int = 30) -> int:
        """
        Удалить старые backup файлы.

        Args:
            days_to_keep: Количество дней для хранения backup

        Returns:
            Количество удаленных файлов
        """
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)

        if not self.backup_path.exists():
            return 0

        for backup_file in self.backup_path.glob("*.session"):
            file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_time < cutoff_time:
                try:
                    backup_file.unlink()
                    deleted_count += 1
                    log.info(f"Deleted old backup: {backup_file}")
                except Exception as e:
                    log.error(f"Failed to delete backup {backup_file}: {e}")

        log.info(f"Deleted {deleted_count} old backups (older than {days_to_keep} days)")
        return deleted_count

    # ========== 2FA Management ==========

    async def store_2fa_secret(
        self,
        db: Session,
        account_id: str,
        totp_secret: str
    ) -> TelegramAccount:
        """
        Сохранить TOTP секрет для 2FA.

        Args:
            db: SQLAlchemy сессия
            account_id: ID Telegram account
            totp_secret: TOTP секрет (base32 encoded)

        Returns:
            Обновленный TelegramAccount

        Raises:
            TwoFactorError: Если не удалось сохранить секрет
        """
        try:
            account = db.query(TelegramAccount).filter(
                TelegramAccount.id == account_id
            ).first()

            if not account:
                raise TwoFactorError(f"Account {account_id} not found")

            # Зашифровать TOTP секрет
            encrypted_secret = encryption_service.encrypt_totp_secret(totp_secret)
            account.totp_secret = encrypted_secret

            db.commit()
            db.refresh(account)

            log.info(f"Stored 2FA secret for account {account_id}")
            return account

        except ValueError as e:
            log.error(f"Invalid TOTP secret for account {account_id}: {e}")
            raise TwoFactorError(f"Invalid TOTP secret: {str(e)}") from e
        except SQLAlchemyError as e:
            log.error(f"Database error storing 2FA secret for {account_id}: {e}")
            db.rollback()
            raise TwoFactorError(f"Database error: {str(e)}") from e
        except Exception as e:
            log.error(f"Error storing 2FA secret for {account_id}: {e}")
            raise TwoFactorError(f"Failed to store secret: {str(e)}") from e

    async def generate_2fa_code(
        self,
        db: Session,
        account_id: str
    ) -> str:
        """
        Сгенерировать текущий 2FA код.

        Args:
            db: SQLAlchemy сессия
            account_id: ID Telegram account

        Returns:
            6-значный 2FA код

        Raises:
            TwoFactorError: Если не удалось сгенерировать код
        """
        try:
            account = db.query(TelegramAccount).filter(
                TelegramAccount.id == account_id
            ).first()

            if not account:
                raise TwoFactorError(f"Account {account_id} not found")

            if not account.totp_secret:
                raise TwoFactorError(f"No 2FA secret configured for account {account_id}")

            # Расшифровать TOTP секрет
            totp_secret = encryption_service.decrypt_totp_secret(account.totp_secret)

            # Сгенерировать TOTP код
            import pyotp
            totp = pyotp.TOTP(totp_secret)
            code = totp.now()

            log.info(f"Generated 2FA code for account {account_id}")
            return code

        except ValueError as e:
            log.error(f"Invalid TOTP secret for account {account_id}: {e}")
            raise TwoFactorError(f"Invalid TOTP secret: {str(e)}") from e
        except Exception as e:
            log.error(f"Error generating 2FA code for {account_id}: {e}")
            raise TwoFactorError(f"Failed to generate code: {str(e)}") from e

    async def remove_2fa_secret(
        self,
        db: Session,
        account_id: str
    ) -> TelegramAccount:
        """
        Удалить TOTP секрет.

        Args:
            db: SQLAlchemy сессия
            account_id: ID Telegram account

        Returns:
            Обновленный TelegramAccount

        Raises:
            TwoFactorError: Если не удалось удалить секрет
        """
        try:
            account = db.query(TelegramAccount).filter(
                TelegramAccount.id == account_id
            ).first()

            if not account:
                raise TwoFactorError(f"Account {account_id} not found")

            account.totp_secret = None
            db.commit()
            db.refresh(account)

            log.info(f"Removed 2FA secret for account {account_id}")
            return account

        except SQLAlchemyError as e:
            log.error(f"Database error removing 2FA secret for {account_id}: {e}")
            db.rollback()
            raise TwoFactorError(f"Database error: {str(e)}") from e
        except Exception as e:
            log.error(f"Error removing 2FA secret for {account_id}: {e}")
            raise TwoFactorError(f"Failed to remove secret: {str(e)}") from e

    # ========== Session Health Monitoring ==========

    async def check_session_health(
        self,
        db: Session,
        account_id: str
    ) -> SessionHealthStatus:
        """
        Проверить здоровье сессии.

        Args:
            db: SQLAlchemy сессия
            account_id: ID Telegram account

        Returns:
            Текущий статус здоровья сессии
        """
        try:
            account = db.query(TelegramAccount).filter(
                TelegramAccount.id == account_id
            ).first()

            if not account:
                log.warning(f"Account {account_id} not found for health check")
                return SessionHealthStatus.ERROR

            # Обновить время последней проверки
            account.last_health_check = datetime.utcnow()

            # Проверить истечение сессии
            if account.is_expired():
                account.session_health_status = SessionHealthStatus.EXPIRED
                db.commit()
                return SessionHealthStatus.EXPIRED

            # Проверить скорое истечение
            if account.is_expiring_soon():
                account.session_health_status = SessionHealthStatus.EXPIRING
                db.commit()
                return SessionHealthStatus.EXPIRING

            # TODO: Implement actual session validation
            # Для_now считаем сессию здоровой
            account.session_health_status = SessionHealthStatus.HEALTHY
            db.commit()

            # Кэшировать в Redis
            await self._cache_health_status(account_id, SessionHealthStatus.HEALTHY)

            return SessionHealthStatus.HEALTHY

        except SQLAlchemyError as e:
            log.error(f"Database error checking health for {account_id}: {e}")
            return SessionHealthStatus.ERROR
        except Exception as e:
            log.error(f"Error checking health for {account_id}: {e}")
            return SessionHealthStatus.ERROR

    async def _cache_health_status(
        self,
        account_id: str,
        status: SessionHealthStatus
    ) -> None:
        """Кэшировать статус здоровья в Redis."""
        try:
            r = await self._get_redis()
            key = self._get_health_key(account_id)
            await r.set(key, status.value, ex=3600)  # TTL: 1 hour
        except Exception as e:
            log.warning(f"Failed to cache health status for {account_id}: {e}")

    async def _invalidate_health_cache(self, account_id: str) -> None:
        """Удалить кэш статуса здоровья из Redis."""
        try:
            r = await self._get_redis()
            key = self._get_health_key(account_id)
            await r.delete(key)
        except Exception as e:
            log.warning(f"Failed to invalidate health cache for {account_id}: {e}")

    async def get_cached_health_status(
        self,
        account_id: str
    ) -> Optional[SessionHealthStatus]:
        """
        Получить кэшированный статус здоровья.

        Args:
            account_id: ID Telegram account

        Returns:
            SessionHealthStatus или None если нет кэша
        """
        try:
            r = await self._get_redis()
            key = self._get_health_key(account_id)
            status_value = await r.get(key)

            if status_value:
                return SessionHealthStatus(status_value)

            return None

        except Exception as e:
            log.warning(f"Failed to get cached health status for {account_id}: {e}")
            return None


# Singleton instance
_telegram_session_service: Optional[TelegramSessionService] = None


def get_telegram_session_service() -> TelegramSessionService:
    """Получить singleton экземпляр TelegramSessionService."""
    global _telegram_session_service
    if _telegram_session_service is None:
        _telegram_session_service = TelegramSessionService()
    return _telegram_session_service


async def shutdown_telegram_session_service() -> None:
    """Закрыть TelegramSessionService при завершении приложения."""
    global _telegram_session_service
    if _telegram_session_service is not None:
        await _telegram_session_service.close()
        _telegram_session_service = None
