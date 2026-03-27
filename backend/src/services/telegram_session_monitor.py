"""
Telegram Session Monitor Service

Сервис для мониторинга здоровья Telegram сессий и обнаружения проблем.

Функционал:
- Периодическая проверка здоровья Telegram сессий
- Обнаружение истекающих и истекших сессий
- Обнаружение необходимости 2FA
- Интеграция с CircuitBreaker для предотвращения rate limits
- Хранение состояния здоровья в Redis
- Callbacks для событий (session_expiring, session_expired, 2fa_required)

Storage: Redis Hash (session_health:{account_id}) для хранения метрик здоровья

Использование:
    monitor = TelegramSessionMonitor()
    await monitor.check_account_health(account_id)  # Проверить здоровье
    health = await monitor.get_account_health(account_id)  # Получить статус
    await monitor.start_monitoring(account_id)  # Запустить фоновый мониторинг
"""

import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable, Any, Dict

import redis.asyncio as redis

from src.config import settings
from src.models.telegram import TelegramAccount, SessionHealthStatus
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

log = logging.getLogger(__name__)


class TelegramSessionMonitorError(Exception):
    """Базовое исключение для ошибок TelegramSessionMonitor."""
    pass


@dataclass
class TelegramSessionHealth:
    """Статус здоровья Telegram сессии."""
    account_id: str
    is_healthy: bool
    health_status: SessionHealthStatus
    last_check: datetime
    consecutive_failures: int
    last_failure_type: Optional[str] = None
    last_failure_time: Optional[datetime] = None
    last_error_message: Optional[str] = None
    session_expires_at: Optional[datetime] = None
    time_until_expiry: Optional[int] = None  # в секундах
    total_checks: int = 0
    failed_checks: int = 0

    def to_redis_dict(self) -> dict:
        """Конвертировать в dict для Redis."""
        data = asdict(self)
        # Конвертируем datetime в isoformat
        if data.get('last_check'):
            data['last_check'] = data['last_check'].isoformat()
        if data.get('last_failure_time'):
            data['last_failure_time'] = data['last_failure_time'].isoformat()
        if data.get('session_expires_at'):
            data['session_expires_at'] = data['session_expires_at'].isoformat()
        # Конвертируем enum в строку
        if isinstance(data.get('health_status'), SessionHealthStatus):
            data['health_status'] = data['health_status'].value
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_redis_dict(cls, data: dict) -> 'TelegramSessionHealth':
        """Создать из dict из Redis."""
        if data.get('last_check'):
            data['last_check'] = datetime.fromisoformat(data['last_check'])
        if data.get('last_failure_time'):
            data['last_failure_time'] = datetime.fromisoformat(data['last_failure_time'])
        if data.get('session_expires_at'):
            data['session_expires_at'] = datetime.fromisoformat(data['session_expires_at'])
        # Конвертируем строку обратно в enum
        if data.get('health_status') and isinstance(data['health_status'], str):
            try:
                data['health_status'] = SessionHealthStatus(data['health_status'])
            except ValueError:
                data['health_status'] = SessionHealthStatus.ERROR
        return cls(**data)


@dataclass
class SessionMonitorConfig:
    """Конфигурация мониторинга сессий."""
    check_interval_seconds: int = 3600        # Интервал автоматических проверок (1 час)
    failure_threshold: int = 3                # Количество отказов для signaling failure
    session_timeout_seconds: int = 30         # Таймаут проверок сессии
    expiring_soon_threshold_hours: int = 24   # Порог для "истекает скоро" (часы)

    # Circuit Breaker settings
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    circuit_breaker_success_threshold: int = 2


class TelegramSessionMonitor:
    """
    Сервис мониторинга здоровья Telegram сессий.

    Использует Redis для хранения состояния и Circuit Breaker для предотвращения rate limits.

    Attributes:
        config: Конфигурация мониторинга
        on_session_expiring_callback: Callback при обнаружении истекающей сессии (account_id, time_until_expiry)
        on_session_expired_callback: Callback при обнаружении истекшей сессии (account_id, reason)
        on_2fa_required_callback: Callback при обнаружении необходимости 2FA (account_id, reason)
    """

    # Redis key patterns
    HEALTH_KEY_PREFIX = "session_health"
    MONITOR_TASKS_PREFIX = "session_monitor_tasks"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        config: Optional[SessionMonitorConfig] = None,
        on_session_expiring_callback: Optional[Callable[[str, int], Awaitable[None]]] = None,
        on_session_expired_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
        on_2fa_required_callback: Optional[Callable[[str, str], Awaitable[None]]] = None
    ):
        """
        Инициализация TelegramSessionMonitor.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            config: Конфигурация мониторинга
            on_session_expiring_callback: Callback при обнаружении истекающей сессии (account_id, hours_until_expiry)
            on_session_expired_callback: Callback при обнаружении истекшей сессии (account_id, reason)
            on_2fa_required_callback: Callback при обнаружении необходимости 2FA (account_id, reason)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.config = config or SessionMonitorConfig()
        self.on_session_expiring_callback = on_session_expiring_callback
        self.on_session_expired_callback = on_session_expired_callback
        self.on_2fa_required_callback = on_2fa_required_callback

        self._redis: Optional[redis.Redis] = None
        self._monitor_tasks: Dict[str, asyncio.Task] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        log.info(
            f"TelegramSessionMonitor initialized: check_interval={self.config.check_interval_seconds}s, "
            f"failure_threshold={self.config.failure_threshold}"
        )

    async def _get_redis(self) -> redis.Redis:
        """Получение Redis клиента."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis

    def _get_circuit_breaker(self, account_id: str) -> CircuitBreaker:
        """Получить или создать Circuit Breaker для аккаунта."""
        if account_id not in self._circuit_breakers:
            cb_config = CircuitBreakerConfig(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                success_threshold=self.config.circuit_breaker_success_threshold,
                timeout=self.config.circuit_breaker_timeout
            )
            self._circuit_breakers[account_id] = CircuitBreaker(
                name=f"telegram-session-{account_id}",
                config=cb_config
            )
        return self._circuit_breakers[account_id]

    @staticmethod
    def _get_health_key(account_id: str) -> str:
        """Генерация Redis ключа для статуса здоровья."""
        return f"{TelegramSessionMonitor.HEALTH_KEY_PREFIX}:{account_id}"

    @staticmethod
    def _get_monitor_task_key(account_id: str) -> str:
        """Генерация Redis ключа для мониторинговой задачи."""
        return f"{TelegramSessionMonitor.MONITOR_TASKS_PREFIX}:{account_id}"

    async def close(self) -> None:
        """Закрытие соединений и задач."""
        # Отменить все мониторы
        for task in self._monitor_tasks.values():
            task.cancel()
        self._monitor_tasks.clear()

        if self._redis is not None:
            await self._redis.close()
            self._redis = None

        self._circuit_breakers.clear()

    # ========== Health Check Operations ==========

    async def check_account_health(
        self,
        account_id: str,
        check_validity: bool = True,
        check_expiration: bool = True,
        check_2fa: bool = True
    ) -> TelegramSessionHealth:
        """
        Проверить здоровье сессии Telegram аккаунта.

        Args:
            account_id: ID аккаунта
            check_validity: Проверять валидность сессии
            check_expiration: Проверять истечение сессии
            check_2fa: Проверять требование 2FA

        Returns:
            TelegramSessionHealth с результатами проверки
        """
        r = await self._get_redis()
        key = self._get_health_key(account_id)

        # Получить текущий статус
        current_status = await self.get_account_health(account_id)

        # Инициализировать новый статус если не существует
        if current_status is None:
            current_status = TelegramSessionHealth(
                account_id=account_id,
                is_healthy=True,
                health_status=SessionHealthStatus.HEALTHY,
                last_check=datetime.now(timezone.utc),
                consecutive_failures=0,
                total_checks=0,
                failed_checks=0
            )

        # Выполнить проверки
        is_healthy = True
        health_status = SessionHealthStatus.HEALTHY
        failure_type = None
        error_message = None
        session_expires_at = None
        time_until_expiry = None

        try:
            # Проверка 1: Circuit Breaker
            cb = self._get_circuit_breaker(account_id)
            if not cb.allow_request():
                failure_type = "rate_limited"
                error_message = f"Circuit breaker is OPEN (will try again at {cb.open_until})"
                is_healthy = False
                health_status = SessionHealthStatus.ERROR
                log.warning(f"Account {account_id}: Circuit breaker OPEN, blocking health check")
            else:
                # Проверка 2: Валидность сессии
                if check_validity and is_healthy:
                    valid, valid_error = await self._check_session_validity(account_id)
                    if not valid:
                        failure_type = "invalid_session"
                        error_message = valid_error
                        is_healthy = False
                        health_status = SessionHealthStatus.ERROR

                # Проверка 3: Истечение сессии
                if check_expiration and is_healthy:
                    expires_data = await self._check_session_expiration(account_id)
                    if expires_data['is_expiring']:
                        session_expires_at = expires_data.get('expires_at')
                        time_until_expiry = expires_data.get('seconds_until_expiry')

                        if expires_data.get('is_expired'):
                            failure_type = "session_expired"
                            error_message = f"Session expired at {session_expires_at}"
                            is_healthy = False
                            health_status = SessionHealthStatus.EXPIRED
                        else:
                            # Сессия истекает скоро, но еще активна
                            health_status = SessionHealthStatus.EXPIRING
                            log.warning(
                                f"Account {account_id}: Session expiring soon "
                                f"({expires_data.get('hours_until_expiry'):.1f} hours left)"
                            )

                # Проверка 4: Требование 2FA
                if check_2fa and is_healthy:
                    requires_2fa, twofa_error = await self._check_2fa_required(account_id)
                    if requires_2fa:
                        failure_type = "2fa_required"
                        error_message = twofa_error
                        is_healthy = False
                        health_status = SessionHealthStatus.NEEDS_2FA

                # Записать результат в Circuit Breaker
                if is_healthy or health_status == SessionHealthStatus.EXPIRING:
                    # EXPIRING считается "успехом" для Circuit Breaker (сессия еще работает)
                    cb.record_success()
                else:
                    cb.record_failure()

        except Exception as exc:
            log.error(f"Error checking health for account {account_id}: {exc}")
            is_healthy = False
            health_status = SessionHealthStatus.ERROR
            failure_type = "check_exception"
            error_message = f"Health check exception: {str(exc)}"
            cb.record_failure()

        # Обновить статус
        now = datetime.now(timezone.utc)
        current_status.last_check = now
        current_status.total_checks += 1
        current_status.health_status = health_status
        current_status.session_expires_at = session_expires_at
        current_status.time_until_expiry = time_until_expiry

        if is_healthy or health_status == SessionHealthStatus.EXPIRING:
            # EXPIRING не считается ошибкой для consecutive_failures
            if health_status == SessionHealthStatus.EXPIRING:
                current_status.is_healthy = True
                current_status.consecutive_failures = 0

                # Callback для истекающей сессии
                if time_until_expiry is not None:
                    hours_until_expiry = time_until_expiry // 3600
                    log.warning(
                        f"Account {account_id}: Session expiring in {hours_until_expiry} hours"
                    )
                    if self.on_session_expiring_callback:
                        try:
                            await self.on_session_expiring_callback(account_id, hours_until_expiry)
                        except Exception as e:
                            log.error(f"Error in session_expiring callback: {e}")
            else:
                current_status.is_healthy = True
                current_status.consecutive_failures = 0

                # Callback при восстановлении
                if current_status.consecutive_failures >= self.config.failure_threshold:
                    log.info(f"Account {account_id} session recovered after failures")
                    # TODO: Добавить on_recovery_callback если потребуется
        else:
            current_status.failed_checks += 1
            current_status.consecutive_failures += 1
            current_status.is_healthy = current_status.consecutive_failures < self.config.failure_threshold
            current_status.last_failure_type = failure_type
            current_status.last_failure_time = now
            current_status.last_error_message = error_message

            # Callback при обнаружении проблемы
            if current_status.consecutive_failures >= self.config.failure_threshold:
                log.error(
                    f"Account {account_id} session problem detected: "
                    f"status={health_status.value}, type={failure_type}, "
                    f"consecutive={current_status.consecutive_failures}"
                )

                # Вызываем соответствующий callback
                if health_status == SessionHealthStatus.EXPIRED and self.on_session_expired_callback:
                    try:
                        await self.on_session_expired_callback(
                            account_id,
                            error_message or "Session expired"
                        )
                    except Exception as e:
                        log.error(f"Error in session_expired callback: {e}")
                elif health_status == SessionHealthStatus.NEEDS_2FA and self.on_2fa_required_callback:
                    try:
                        await self.on_2fa_required_callback(
                            account_id,
                            error_message or "2FA required"
                        )
                    except Exception as e:
                        log.error(f"Error in 2fa_required callback: {e}")

        # Сохранить в Redis
        await r.hset(key, mapping=current_status.to_redis_dict())
        await r.expire(key, 86400)  # TTL: 24 часа

        return current_status

    async def _check_session_validity(self, account_id: str) -> tuple[bool, Optional[str]]:
        """
        Проверить валидность сессии Telegram аккаунта.

        Args:
            account_id: ID аккаунта

        Returns:
            (is_valid, error_message)
        """
        # TODO: Implement actual session validity check
        # В реальной имплементации здесь будет проверка:
        # - Pyrogram client is_authorized()
        # - Проверка подключения к Telegram серверам
        # - Валидация session файла
        from sqlalchemy import select
        from src.database import get_db

        try:
            async for db in get_db():
                result = await db.execute(
                    select(TelegramAccount).where(TelegramAccount.id == account_id)
                )
                account = result.scalar_one_or_none()

                if not account:
                    return False, "Account not found in database"

                # Проверка: encrypted_session существует
                if not account.encrypted_session:
                    return False, "No encrypted session found"

                # TODO: Добавить проверку через Pyrogram client.is_authorized()
                # Для сейчас считаем сессию валидной если она есть в БД
                return True, None
        except Exception as exc:
            log.error(f"Error checking session validity for {account_id}: {exc}")
            return False, f"Session validity check failed: {str(exc)}"

    async def _check_session_expiration(self, account_id: str) -> dict:
        """
        Проверить истечение сессии Telegram аккаунта.

        Args:
            account_id: ID аккаунта

        Returns:
            dict с полями:
            - is_expiring: bool - истекает ли сессия
            - is_expired: bool - истекла ли сессия
            - expires_at: Optional[datetime] - время истечения
            - seconds_until_expiry: Optional[int] - секунд до истечения
            - hours_until_expiry: Optional[float] - часов до истечения
        """
        from sqlalchemy import select
        from src.database import get_db

        try:
            async for db in get_db():
                result = await db.execute(
                    select(TelegramAccount).where(TelegramAccount.id == account_id)
                )
                account = result.scalar_one_or_none()

                if not account or not account.session_expires_at:
                    return {
                        'is_expiring': False,
                        'is_expired': False,
                        'expires_at': None,
                        'seconds_until_expiry': None,
                        'hours_until_expiry': None
                    }

                now = datetime.now(timezone.utc)
                expires_at = account.session_expires_at
                seconds_until = int((expires_at - now).total_seconds())
                hours_until = seconds_until / 3600

                is_expired = seconds_until <= 0
                is_expiring = seconds_until <= (self.config.expiring_soon_threshold_hours * 3600)

                return {
                    'is_expiring': is_expiring,
                    'is_expired': is_expired,
                    'expires_at': expires_at,
                    'seconds_until_expiry': max(0, seconds_until),
                    'hours_until_expiry': max(0, hours_until)
                }
        except Exception as exc:
            log.error(f"Error checking session expiration for {account_id}: {exc}")
            return {
                'is_expiring': False,
                'is_expired': False,
                'expires_at': None,
                'seconds_until_expiry': None,
                'hours_until_expiry': None
            }

    async def _check_2fa_required(self, account_id: str) -> tuple[bool, Optional[str]]:
        """
        Проверить требуется ли 2FA для сессии.

        Args:
            account_id: ID аккаунта

        Returns:
            (requires_2fa, error_message)
        """
        # TODO: Implement actual 2FA requirement check
        # В реальной имплементации здесь будет проверка:
        # - Попытка авторизации через Pyrogram
        # - Ловля ошибки о требовании 2FA кода
        # - Проверка флага в базе данных

        # Для сейчас считаем, что 2FA не требуется если не указан totp_secret
        from sqlalchemy import select
        from src.database import get_db

        try:
            async for db in get_db():
                result = await db.execute(
                    select(TelegramAccount).where(TelegramAccount.id == account_id)
                )
                account = result.scalar_one_or_none()

                if not account:
                    return False, None

                # Если есть TOTP secret, считаем что 2FA может потребоваться при refresh
                if account.totp_secret:
                    # Но пока не считаем это ошибкой - это просто информация
                    # для автоматического refresh
                    return False, None

                return False, None
        except Exception as exc:
            log.error(f"Error checking 2FA requirement for {account_id}: {exc}")
            return False, f"2FA check failed: {str(exc)}"

    async def get_account_health(self, account_id: str) -> Optional[TelegramSessionHealth]:
        """
        Получить статус здоровья сессии аккаунта.

        Args:
            account_id: ID аккаунта

        Returns:
            TelegramSessionHealth или None если нет данных
        """
        r = await self._get_redis()
        key = self._get_health_key(account_id)

        data = await r.hgetall(key)
        if not data:
            return None

        try:
            return TelegramSessionHealth.from_redis_dict(data)
        except Exception as e:
            log.error(f"Error parsing health data for account {account_id}: {e}")
            return None

    async def is_account_healthy(self, account_id: str) -> bool:
        """
        Проверить здорова ли сессия аккаунта (упрощенная проверка).

        Args:
            account_id: ID аккаунта

        Returns:
            True если сессия здорова
        """
        status = await self.get_account_health(account_id)
        return status is not None and status.is_healthy

    # ========== Background Monitoring ==========

    async def start_monitoring(self, account_id: str) -> None:
        """
        Запустить фоновый мониторинг сессии аккаунта.

        Args:
            account_id: ID аккаунта
        """
        # Остановить существующий монитор
        await self.stop_monitoring(account_id)

        # Создать новую задачу
        task = asyncio.create_task(self._monitor_loop(account_id))
        self._monitor_tasks[account_id] = task

        # Сохранить информацию о задаче в Redis
        r = await self._get_redis()
        monitor_key = self._get_monitor_task_key(account_id)
        await r.set(monitor_key, "1", ex=86400)  # TTL: 24 часа

        log.info(f"Started background monitoring for account {account_id}")

    async def stop_monitoring(self, account_id: str) -> None:
        """
        Остановить мониторинг сессии аккаунта.

        Args:
            account_id: ID аккаунта
        """
        task = self._monitor_tasks.pop(account_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            log.info(f"Stopped monitoring for account {account_id}")

        # Удалить информацию о задаче из Redis
        r = await self._get_redis()
        monitor_key = self._get_monitor_task_key(account_id)
        await r.delete(monitor_key)

    async def _monitor_loop(self, account_id: str) -> None:
        """Фоновый цикл мониторинга."""
        try:
            while True:
                await self.check_account_health(account_id)
                await asyncio.sleep(self.config.check_interval_seconds)
        except asyncio.CancelledError:
            # Очистить Redis при отмене
            r = await self._get_redis()
            monitor_key = self._get_monitor_task_key(account_id)
            await r.delete(monitor_key)
            pass
        except Exception as e:
            log.error(f"Monitor loop error for account {account_id}: {e}")
            # Очистить Redis при ошибке
            r = await self._get_redis()
            monitor_key = self._get_monitor_task_key(account_id)
            await r.delete(monitor_key)

    async def is_monitoring(self, account_id: str) -> bool:
        """
        Проверить запущен ли мониторинг для аккаунта.

        Args:
            account_id: ID аккаунта

        Returns:
            True если мониторинг активен
        """
        # Проверить in-memory задачи
        if account_id in self._monitor_tasks:
            task = self._monitor_tasks[account_id]
            if not task.done():
                return True

        # Проверить Redis
        r = await self._get_redis()
        monitor_key = self._get_monitor_task_key(account_id)
        exists = await r.exists(monitor_key)
        return exists > 0

    # ========== Health Metrics ==========

    async def get_all_unhealthy_accounts(self) -> list[TelegramSessionHealth]:
        """
        Получить все нездоровые сессии.

        Returns:
            Список статусов нездоровых сессий
        """
        r = await self._get_redis()
        pattern = f"{self.HEALTH_KEY_PREFIX}:*"
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)

        unhealthy = []
        for key in keys:
            data = await r.hgetall(key)
            if data:
                try:
                    status = TelegramSessionHealth.from_redis_dict(data)
                    if not status.is_healthy:
                        unhealthy.append(status)
                except Exception as e:
                    log.error(f"Error parsing health data from {key}: {e}")

        return unhealthy

    async def reset_account_health(self, account_id: str) -> bool:
        """
        Сбросить статус здоровья сессии (после ручного вмешательства).

        Args:
            account_id: ID аккаунта

        Returns:
            True если статус был сброшен
        """
        r = await self._get_redis()
        key = self._get_health_key(account_id)

        # Удалить из Redis
        deleted = await r.delete(key)

        # Сбросить Circuit Breaker
        if account_id in self._circuit_breakers:
            self._circuit_breakers[account_id].reset()

        if deleted:
            log.info(f"Reset health status for account {account_id}")
        else:
            log.warning(f"No health status to reset for account {account_id}")

        return deleted > 0

    def get_circuit_breaker_info(self, account_id: str) -> Optional[dict]:
        """
        Получить информацию о Circuit Breaker для аккаунта.

        Args:
            account_id: ID аккаунта

        Returns:
            Словарь с информацией о Circuit Breaker или None
        """
        cb = self._circuit_breakers.get(account_id)
        if cb:
            return cb.get_state_info()
        return None


# Singleton instance
_telegram_session_monitor: Optional[TelegramSessionMonitor] = None


def get_telegram_session_monitor() -> TelegramSessionMonitor:
    """Получить singleton экземпляр TelegramSessionMonitor."""
    global _telegram_session_monitor
    if _telegram_session_monitor is None:
        _telegram_session_monitor = TelegramSessionMonitor()
    return _telegram_session_monitor


async def shutdown_telegram_session_monitor() -> None:
    """Закрыть TelegramSessionMonitor при завершении приложения."""
    global _telegram_session_monitor
    if _telegram_session_monitor is not None:
        await _telegram_session_monitor.close()
        _telegram_session_monitor = None
