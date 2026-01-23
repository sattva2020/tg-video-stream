"""
API Rate Limit Monitor Service

Сервис для мониторинга API rate limits и предупреждения о приближении к лимитам.

Функционал:
- Отслеживание количества запросов к API
- Проверка заголовков rate limit (X-RateLimit-Remaining, Retry-After)
- Предупреждения при приближении к лимиту (настраиваемый процент)
- Отслеживание времени сброса лимитов
- Хранение состояния в Redis
- Callbacks для событий предупреждений и ограничений

Storage: Redis Hash (api_rate_limit:{endpoint}:{window}) для хранения метрик

Использование:
    monitor = ApiRateLimitMonitor()
    await monitor.record_api_call(endpoint, remaining, limit)  # Записать вызов
    status = await monitor.get_rate_limit_status(endpoint)  # Получить статус
    await monitor.check_rate_limit(endpoint)  # Проверить лимит
"""

import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable, Any, Dict, List

import redis.asyncio as redis

from src.config import settings

log = logging.getLogger(__name__)


class ApiRateLimitMonitorError(Exception):
    """Базовое исключение для ошибок ApiRateLimitMonitor."""
    pass


@dataclass
class ApiRateLimitStatus:
    """Статус rate limit для endpoint."""
    endpoint: str
    window: str  # hour, minute, day, etc.
    total_requests: int
    remaining_requests: Optional[int]
    limit: Optional[int]
    reset_time: Optional[datetime]
    last_check: datetime
    usage_percentage: float
    is_warning_threshold: bool
    is_critical_threshold: bool
    is_rate_limited: bool
    consecutive_rate_limited: int = 0
    total_windows_checked: int = 0
    request_rate_per_minute: float = 0.0
    last_rate_limit_time: Optional[datetime] = None
    estimated_limit_reset: Optional[datetime] = None

    def to_redis_dict(self) -> dict:
        """Конвертировать в dict для Redis."""
        data = asdict(self)
        # Конвертируем datetime в isoformat
        if data.get('last_check'):
            data['last_check'] = data['last_check'].isoformat()
        if data.get('reset_time'):
            data['reset_time'] = data['reset_time'].isoformat()
        if data.get('last_rate_limit_time'):
            data['last_rate_limit_time'] = data['last_rate_limit_time'].isoformat()
        if data.get('estimated_limit_reset'):
            data['estimated_limit_reset'] = data['estimated_limit_reset'].isoformat()
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_redis_dict(cls, data: dict) -> 'ApiRateLimitStatus':
        """Создать из dict из Redis."""
        if data.get('last_check'):
            data['last_check'] = datetime.fromisoformat(data['last_check'])
        if data.get('reset_time'):
            data['reset_time'] = datetime.fromisoformat(data['reset_time'])
        if data.get('last_rate_limit_time'):
            data['last_rate_limit_time'] = datetime.fromisoformat(data['last_rate_limit_time'])
        if data.get('estimated_limit_reset'):
            data['estimated_limit_reset'] = datetime.fromisoformat(data['estimated_limit_reset'])
        return cls(**data)


@dataclass
class ApiRateLimitConfig:
    """Конфигурация мониторинга API rate limits."""
    check_interval_seconds: int = 30          # Интервал автоматических проверок
    warning_threshold_percent: float = 80.0    # Порог для предупреждения (%)
    critical_threshold_percent: float = 95.0   # Порог для критического (%)
    rate_limit_trigger_count: int = 3         # Количество rate limits для алерта
    alert_cooldown_seconds: int = 300         # Минимальное время между алертами
    default_limit: int = 100                  # Лимит по умолчанию (если не указан в headers)
    sliding_window_size: int = 60             # Размер скользящего окна (секунды)
    history_size: int = 1000                  # Размер истории запросов


class ApiRateLimitMonitor:
    """
    Сервис мониторинга API rate limits.

    Использует Redis для хранения состояния и истории запросов.

    Attributes:
        config: Конфигурация мониторинга
        on_warning_callback: Callback при достижении warning threshold (endpoint, usage_percent, remaining, limit)
        on_critical_callback: Callback при достижении critical threshold (endpoint, usage_percent, remaining, limit)
        on_rate_limited_callback: Callback при получении 429 (endpoint, retry_after, reset_time)
        on_recovery_callback: Callback при восстановлении (endpoint)
    """

    # Redis key patterns
    RATE_LIMIT_KEY_PREFIX = "api_rate_limit"
    REQUEST_HISTORY_SUFFIX = "history"
    ALERT_LAST_SENT_PREFIX = "api_rate_alert_last"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        config: Optional[ApiRateLimitConfig] = None,
        on_warning_callback: Optional[Callable[[str, float, int, int], Awaitable[None]]] = None,
        on_critical_callback: Optional[Callable[[str, float, int, int], Awaitable[None]]] = None,
        on_rate_limited_callback: Optional[Callable[[str, Optional[int], Optional[datetime]], Awaitable[None]]] = None,
        on_recovery_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        """
        Инициализация ApiRateLimitMonitor.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            config: Конфигурация мониторинга
            on_warning_callback: Callback при warning threshold (endpoint, usage_percent, remaining, limit)
            on_critical_callback: Callback при critical threshold (endpoint, usage_percent, remaining, limit)
            on_rate_limited_callback: Callback при 429 (endpoint, retry_after, reset_time)
            on_recovery_callback: Callback при восстановлении (endpoint)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.config = config or ApiRateLimitConfig()
        self.on_warning_callback = on_warning_callback
        self.on_critical_callback = on_critical_callback
        self.on_rate_limited_callback = on_rate_limited_callback
        self.on_recovery_callback = on_recovery_callback

        self._redis: Optional[redis.Redis] = None
        self._monitor_tasks: Dict[str, asyncio.Task] = {}

        log.info(
            f"ApiRateLimitMonitor initialized: check_interval={self.config.check_interval_seconds}s, "
            f"warning_threshold={self.config.warning_threshold_percent}%, "
            f"critical_threshold={self.config.critical_threshold_percent}%"
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
    def _get_rate_limit_key(endpoint: str, window: str = "default") -> str:
        """Генерация Redis ключа для статуса rate limit."""
        return f"{ApiRateLimitMonitor.RATE_LIMIT_KEY_PREFIX}:{endpoint}:{window}"

    @staticmethod
    def _get_history_key(endpoint: str, window: str = "default") -> str:
        """Генерация Redis ключа для истории запросов."""
        return f"{ApiRateLimitMonitor.RATE_LIMIT_KEY_PREFIX}:{endpoint}:{window}:{ApiRateLimitMonitor.REQUEST_HISTORY_SUFFIX}"

    @staticmethod
    def _get_alert_last_sent_key(endpoint: str, alert_type: str) -> str:
        """Генерация Redis ключа для времени последнего алерта."""
        return f"{ApiRateLimitMonitor.ALERT_LAST_SENT_PREFIX}:{endpoint}:{alert_type}"

    async def close(self) -> None:
        """Закрытие соединений и задач."""
        # Отменить все мониторы
        for task in self._monitor_tasks.values():
            task.cancel()
        self._monitor_tasks.clear()

        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    # ========== Rate Limit Operations ==========

    async def record_api_call(
        self,
        endpoint: str,
        remaining: Optional[int] = None,
        limit: Optional[int] = None,
        reset_time: Optional[datetime] = None,
        window: str = "default",
        status_code: int = 200
    ) -> ApiRateLimitStatus:
        """
        Записать вызов API и обновить статус rate limit.

        Args:
            endpoint: API endpoint (например, "telegram/api", "github/repos")
            remaining: Оставшееся количество запросов (из заголовков)
            limit: Лимит запросов (из заголовков)
            reset_time: Время сброса лимита (из заголовков)
            window: Окно rate limit (hour, minute, day, default)
            status_code: HTTP статус код ответа

        Returns:
            ApiRateLimitStatus с обновленными данными
        """
        if not endpoint:
            raise ApiRateLimitMonitorError("Endpoint cannot be empty")

        r = await self._get_redis()
        key = self._get_rate_limit_key(endpoint, window)
        history_key = self._get_history_key(endpoint, window)

        # Получить текущий статус
        current_status = await self.get_rate_limit_status(endpoint, window)

        # Инициализировать новый статус если не существует
        if current_status is None:
            current_status = ApiRateLimitStatus(
                endpoint=endpoint,
                window=window,
                total_requests=0,
                remaining_requests=remaining,
                limit=limit or self.config.default_limit,
                reset_time=reset_time,
                last_check=datetime.now(timezone.utc),
                usage_percentage=0.0,
                is_warning_threshold=False,
                is_critical_threshold=False,
                is_rate_limited=False,
                consecutive_rate_limited=0,
                total_windows_checked=0,
                request_rate_per_minute=0.0
            )

        # Добавить запись в историю
        now = datetime.now(timezone.utc)
        await r.lpush(history_key, f"{int(now.timestamp())}:{status_code}")
        await r.ltrim(history_key, 0, self.config.history_size - 1)
        await r.expire(history_key, 86400)  # TTL: 24 часа

        # Обновить счетчики
        current_status.total_requests += 1
        current_status.last_check = now

        # Обновить данные из headers если предоставлены
        if remaining is not None:
            current_status.remaining_requests = remaining
        if limit is not None:
            current_status.limit = limit
        if reset_time is not None:
            current_status.reset_time = reset_time

        # Расчет usage percentage
        if current_status.limit and current_status.limit > 0:
            if current_status.remaining_requests is not None:
                current_status.usage_percentage = (
                    (current_status.limit - current_status.remaining_requests) / current_status.limit
                ) * 100
            else:
                # Если remaining не предоставлен, оцениваем по total_requests
                current_status.usage_percentage = min(
                    (current_status.total_requests / current_status.limit) * 100,
                    100.0
                )

        # Расчет request rate per minute
        history_data = await r.lrange(history_key, 0, -1)
        if history_data:
            # Подсчет запросов за последнюю минуту
            one_minute_ago = int((now - timedelta(minutes=1)).timestamp())
            recent_requests = [
                item for item in history_data
                if int(item.split(':')[0]) >= one_minute_ago
            ]
            current_status.request_rate_per_minute = len(recent_requests)

        # Проверка на rate limit (429)
        is_rate_limited = status_code == 429
        was_rate_limited = current_status.is_rate_limited
        current_status.is_rate_limited = is_rate_limited

        if is_rate_limited:
            current_status.consecutive_rate_limited += 1
            current_status.last_rate_limit_time = now
        else:
            current_status.consecutive_rate_limited = 0

        # Проверка thresholds
        was_warning = current_status.is_warning_threshold
        was_critical = current_status.is_critical_threshold

        current_status.is_warning_threshold = (
            current_status.usage_percentage >= self.config.warning_threshold_percent
        )
        current_status.is_critical_threshold = (
            current_status.usage_percentage >= self.config.critical_threshold_percent
        )

        # Callback при достижении critical threshold
        if current_status.is_critical_threshold and not was_critical:
            if await self._can_send_alert(endpoint, "critical"):
                log.warning(
                    f"API {endpoint}: Critical rate limit threshold reached: "
                    f"{current_status.usage_percentage:.1f}% used "
                    f"({current_status.remaining_requests}/{current_status.limit} remaining)"
                )
                if self.on_critical_callback:
                    try:
                        await self.on_critical_callback(
                            endpoint,
                            current_status.usage_percentage,
                            current_status.remaining_requests or 0,
                            current_status.limit
                        )
                        await self._mark_alert_sent(endpoint, "critical")
                    except Exception as e:
                        log.error(f"Error in critical callback: {e}")

        # Callback при достижении warning threshold
        elif current_status.is_warning_threshold and not was_warning:
            if await self._can_send_alert(endpoint, "warning"):
                log.warning(
                    f"API {endpoint}: Warning rate limit threshold reached: "
                    f"{current_status.usage_percentage:.1f}% used "
                    f"({current_status.remaining_requests}/{current_status.limit} remaining)"
                )
                if self.on_warning_callback:
                    try:
                        await self.on_warning_callback(
                            endpoint,
                            current_status.usage_percentage,
                            current_status.remaining_requests or 0,
                            current_status.limit
                        )
                        await self._mark_alert_sent(endpoint, "warning")
                    except Exception as e:
                        log.error(f"Error in warning callback: {e}")

        # Callback при получении rate limit (429)
        if is_rate_limited and current_status.consecutive_rate_limited >= self.config.rate_limit_trigger_count:
            if await self._can_send_alert(endpoint, "rate_limited"):
                retry_after = None  # Можно извлечь из headers если нужно
                log.error(
                    f"API {endpoint}: Rate limited (429) - "
                    f"consecutive count: {current_status.consecutive_rate_limited}"
                )
                if self.on_rate_limited_callback:
                    try:
                        await self.on_rate_limited_callback(
                            endpoint,
                            retry_after,
                            current_status.reset_time
                        )
                        await self._mark_alert_sent(endpoint, "rate_limited")
                    except Exception as e:
                        log.error(f"Error in rate_limited callback: {e}")

        # Callback при восстановлении
        if (was_warning or was_critical or was_rate_limited) and \
           not current_status.is_warning_threshold and \
           not current_status.is_critical_threshold and \
           not is_rate_limited:
            log.info(f"API {endpoint}: Rate limit status recovered")
            if self.on_recovery_callback:
                try:
                    await self.on_recovery_callback(endpoint)
                except Exception as e:
                    log.error(f"Error in recovery callback: {e}")

        # Оценка времени сброса лимита
        if current_status.reset_time:
            current_status.estimated_limit_reset = current_status.reset_time
        elif current_status.limit and current_status.remaining_requests is not None:
            # Оцениваем на основе скорости запросов
            if current_status.request_rate_per_minute > 0:
                seconds_until_reset = (
                    current_status.remaining_requests / current_status.request_rate_per_minute
                ) * 60
                current_status.estimated_limit_reset = now + timedelta(seconds=seconds_until_reset)

        current_status.total_windows_checked += 1

        # Сохранить в Redis
        await r.hset(key, mapping=current_status.to_redis_dict())
        await r.expire(key, 86400)  # TTL: 24 часа

        return current_status

    async def check_rate_limit(
        self,
        endpoint: str,
        window: str = "default"
    ) -> ApiRateLimitStatus:
        """
        Проверить текущий статус rate limit без записи нового вызова.

        Args:
            endpoint: API endpoint
            window: Окно rate limit

        Returns:
            Текущий ApiRateLimitStatus или None если нет данных
        """
        status = await self.get_rate_limit_status(endpoint, window)
        if status is None:
            # Создать пустой статус
            status = ApiRateLimitStatus(
                endpoint=endpoint,
                window=window,
                total_requests=0,
                remaining_requests=None,
                limit=self.config.default_limit,
                reset_time=None,
                last_check=datetime.now(timezone.utc),
                usage_percentage=0.0,
                is_warning_threshold=False,
                is_critical_threshold=False,
                is_rate_limited=False,
                consecutive_rate_limited=0,
                total_windows_checked=0,
                request_rate_per_minute=0.0
            )
        return status

    async def get_rate_limit_status(
        self,
        endpoint: str,
        window: str = "default"
    ) -> Optional[ApiRateLimitStatus]:
        """
        Получить статус rate limit для endpoint.

        Args:
            endpoint: API endpoint
            window: Окно rate limit

        Returns:
            ApiRateLimitStatus или None если нет данных
        """
        r = await self._get_redis()
        key = self._get_rate_limit_key(endpoint, window)

        data = await r.hgetall(key)
        if not data:
            return None

        try:
            return ApiRateLimitStatus.from_redis_dict(data)
        except Exception as e:
            log.error(f"Error parsing rate limit data for endpoint {endpoint}: {e}")
            return None

    async def get_request_history(
        self,
        endpoint: str,
        window: str = "default",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получить историю запросов для endpoint.

        Args:
            endpoint: API endpoint
            window: Окно rate limit
            limit: Максимальное количество записей

        Returns:
            Список словарей с данными о запросах
        """
        r = await self._get_redis()
        history_key = self._get_history_key(endpoint, window)

        history_data = await r.lrange(history_key, 0, limit - 1)
        history = []

        for item in history_data:
            try:
                timestamp_str, status_code_str = item.split(':')
                history.append({
                    'timestamp': datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc),
                    'status_code': int(status_code_str)
                })
            except (ValueError, IndexError):
                continue

        return history

    # ========== Background Monitoring ==========

    async def start_monitoring(
        self,
        endpoint: str,
        window: str = "default",
        check_function: Optional[Callable[[], Awaitable[tuple]]] = None
    ) -> None:
        """
        Запустить фоновый мониторинг rate limit для endpoint.

        Args:
            endpoint: API endpoint
            window: Окно rate limit
            check_function: Async функция для проверки текущего состояния (возвращает remaining, limit, reset_time)
        """
        # Остановить существующий монитор
        await self.stop_monitoring(endpoint, window)

        # Создать новую задачу
        task = asyncio.create_task(self._monitor_loop(endpoint, window, check_function))
        monitor_key = f"{endpoint}:{window}"
        self._monitor_tasks[monitor_key] = task

        log.info(f"Started background rate limit monitoring for API {endpoint} (window: {window})")

    async def stop_monitoring(self, endpoint: str, window: str = "default") -> None:
        """
        Остановить мониторинг rate limit.

        Args:
            endpoint: API endpoint
            window: Окно rate limit
        """
        monitor_key = f"{endpoint}:{window}"
        task = self._monitor_tasks.pop(monitor_key, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            log.info(f"Stopped rate limit monitoring for API {endpoint} (window: {window})")

    async def _monitor_loop(
        self,
        endpoint: str,
        window: str,
        check_function: Optional[Callable[[], Awaitable[tuple]]]
    ) -> None:
        """Фоновый цикл мониторинга."""
        try:
            while True:
                try:
                    if check_function:
                        # Вызываем функцию для получения актуальных данных
                        remaining, limit, reset_time = await check_function()
                        await self.record_api_call(
                            endpoint,
                            remaining=remaining,
                            limit=limit,
                            reset_time=reset_time,
                            window=window
                        )
                    else:
                        # Просто проверяем текущий статус
                        await self.check_rate_limit(endpoint, window)
                except Exception as e:
                    log.error(f"Error checking rate limit for API {endpoint}: {e}")

                await asyncio.sleep(self.config.check_interval_seconds)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Monitor loop error for API {endpoint}: {e}")

    # ========== Alert Cooldown ==========

    async def _can_send_alert(self, endpoint: str, alert_type: str) -> bool:
        """
        Проверить можно ли отправить алерт (cooldown).

        Args:
            endpoint: API endpoint
            alert_type: Тип алерта (warning, critical, rate_limited)

        Returns:
            True если можно отправить алерт
        """
        r = await self._get_redis()
        key = self._get_alert_last_sent_key(endpoint, alert_type)

        last_sent_str = await r.get(key)
        if not last_sent_str:
            return True

        try:
            last_sent = datetime.fromtimestamp(int(last_sent_str), tz=timezone.utc)
            cooldown_expiry = last_sent + timedelta(seconds=self.config.alert_cooldown_seconds)
            return datetime.now(timezone.utc) >= cooldown_expiry
        except (ValueError, OSError):
            return True

    async def _mark_alert_sent(self, endpoint: str, alert_type: str) -> None:
        """
        Отметить что алерт был отправлен.

        Args:
            endpoint: API endpoint
            alert_type: Тип алерта
        """
        r = await self._get_redis()
        key = self._get_alert_last_sent_key(endpoint, alert_type)

        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        await r.set(key, now_timestamp, ex=self.config.alert_cooldown_seconds)

    # ========== Statistics ==========

    async def get_all_critical_endpoints(self) -> List[ApiRateLimitStatus]:
        """
        Получить все endpoints с критическим использованием rate limit.

        Returns:
            Список статусов endpoints с critical threshold
        """
        r = await self._get_redis()
        pattern = f"{self.RATE_LIMIT_KEY_PREFIX}:*"
        keys = []

        async for key in r.scan_iter(match=pattern):
            # Исключаем ключи истории
            if not key.endswith(f":{self.REQUEST_HISTORY_SUFFIX}"):
                keys.append(key)

        critical = []
        for key in keys:
            data = await r.hgetall(key)
            if data:
                try:
                    status = ApiRateLimitStatus.from_redis_dict(data)
                    if status.is_critical_threshold or status.is_rate_limited:
                        critical.append(status)
                except Exception as e:
                    log.error(f"Error parsing rate limit data from {key}: {e}")

        return critical

    async def reset_rate_limit_status(self, endpoint: str, window: str = "default") -> bool:
        """
        Сбросить статус rate limit для endpoint.

        Args:
            endpoint: API endpoint
            window: Окно rate limit

        Returns:
            True если статус был сброшен
        """
        r = await self._get_redis()
        rate_limit_key = self._get_rate_limit_key(endpoint, window)
        history_key = self._get_history_key(endpoint, window)

        # Удалить из Redis
        deleted_rate_limit = await r.delete(rate_limit_key)
        deleted_history = await r.delete(history_key)

        if deleted_rate_limit or deleted_history:
            log.info(f"Reset rate limit status for API {endpoint} (window: {window})")
            return True
        else:
            log.warning(f"No rate limit status to reset for API {endpoint} (window: {window})")
            return False


# Singleton instance
_api_rate_limit_monitor: Optional[ApiRateLimitMonitor] = None


def get_api_rate_limit_monitor() -> ApiRateLimitMonitor:
    """Получить singleton экземпляр ApiRateLimitMonitor."""
    global _api_rate_limit_monitor
    if _api_rate_limit_monitor is None:
        _api_rate_limit_monitor = ApiRateLimitMonitor()
    return _api_rate_limit_monitor


async def shutdown_api_rate_limit_monitor() -> None:
    """Закрыть ApiRateLimitMonitor при завершении приложения."""
    global _api_rate_limit_monitor
    if _api_rate_limit_monitor is not None:
        await _api_rate_limit_monitor.close()
        _api_rate_limit_monitor = None
