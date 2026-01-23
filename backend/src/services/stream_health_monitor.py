"""
Stream Health Monitor Service

Сервис для мониторинга здоровья потоков и обнаружения отказов.

Функционал:
- Периодическая проверка здоровья стримов
- Обнаружение различных типов отказов (network, API, codec, session)
- Интеграция с CircuitBreaker для предотвращения каскадных сбоев
- Хранение состояния здоровья в Redis
- Callbacks для событий обнаружения отказов

Storage: Redis Hash (stream_health:{stream_id}) для хранения метрик здоровья

Использование:
    monitor = StreamHealthMonitor()
    await monitor.check_stream_health(stream_id)  # Проверить здоровье
    health = await monitor.get_stream_health(stream_id)  # Получить статус
    await monitor.start_monitoring(stream_id)  # Запустить фоновый мониторинг
"""

import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Callable, Awaitable, Dict

import redis.asyncio as redis

from src.config import settings
from src.models.recovery_log import RecoveryFailureType
from src.services.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

log = logging.getLogger(__name__)


class StreamHealthMonitorError(Exception):
    """Базовое исключение для ошибок StreamHealthMonitor."""
    pass


@dataclass
class StreamHealthStatus:
    """Статус здоровья потока."""
    stream_id: str
    is_healthy: bool
    last_check: datetime
    consecutive_failures: int
    last_failure_type: Optional[str] = None
    last_failure_time: Optional[datetime] = None
    last_error_message: Optional[str] = None
    uptime_seconds: Optional[int] = None
    total_checks: int = 0
    failed_checks: int = 0

    def to_redis_dict(self) -> dict:
        """Конвертировать в dict для Redis."""
        data = asdict(self)
        # Конвертируем datetime в isoformat
        if data['last_check']:
            data['last_check'] = data['last_check'].isoformat()
        if data['last_failure_time']:
            data['last_failure_time'] = data['last_failure_time'].isoformat()
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_redis_dict(cls, data: dict) -> 'StreamHealthStatus':
        """Создать из dict из Redis."""
        if data.get('last_check'):
            data['last_check'] = datetime.fromisoformat(data['last_check'])
        if data.get('last_failure_time'):
            data['last_failure_time'] = datetime.fromisoformat(data['last_failure_time'])
        return cls(**data)


@dataclass
class HealthCheckConfig:
    """Конфигурация проверок здоровья."""
    check_interval_seconds: int = 30         # Интервал автоматических проверок
    failure_threshold: int = 3               # Количество отказов для signaling failure
    network_timeout_seconds: int = 10        # Таймаут сетевых проверок
    process_timeout_seconds: int = 5         # Таймаут проверок процесса
    uptime_alert_threshold: int = 300        # Порог для предупреждения о uptime (секунды)

    # Circuit Breaker settings
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    circuit_breaker_success_threshold: int = 2


class StreamHealthMonitor:
    """
    Сервис мониторинга здоровья потоков.

    Использует Redis для хранения состояния и Circuit Breaker для предотвращения каскадных сбоев.

    Attributes:
        config: Конфигурация проверок здоровья
        on_failure_callback: Callback при обнаружении отказа (stream_id, failure_type, reason)
        on_recovery_callback: Callback при восстановлении (stream_id)
    """

    # Redis key patterns
    HEALTH_KEY_PREFIX = "stream_health"
    MONITOR_TASKS_PREFIX = "monitor_tasks"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        config: Optional[HealthCheckConfig] = None,
        on_failure_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        on_recovery_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        """
        Инициализация StreamHealthMonitor.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            config: Конфигурация проверок здоровья
            on_failure_callback: Callback при обнаружении отказа (stream_id, failure_type, reason)
            on_recovery_callback: Callback при восстановлении (stream_id)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.config = config or HealthCheckConfig()
        self.on_failure_callback = on_failure_callback
        self.on_recovery_callback = on_recovery_callback

        self._redis: Optional[redis.Redis] = None
        self._monitor_tasks: Dict[str, asyncio.Task] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        log.info(
            f"StreamHealthMonitor initialized: check_interval={self.config.check_interval_seconds}s, "
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

    def _get_circuit_breaker(self, stream_id: str) -> CircuitBreaker:
        """Получить или создать Circuit Breaker для потока."""
        if stream_id not in self._circuit_breakers:
            cb_config = CircuitBreakerConfig(
                failure_threshold=self.config.circuit_breaker_failure_threshold,
                success_threshold=self.config.circuit_breaker_success_threshold,
                timeout=self.config.circuit_breaker_timeout
            )
            self._circuit_breakers[stream_id] = CircuitBreaker(
                name=f"stream-{stream_id}",
                config=cb_config
            )
        return self._circuit_breakers[stream_id]

    @staticmethod
    def _get_health_key(stream_id: str) -> str:
        """Генерация Redis ключа для статуса здоровья."""
        return f"{StreamHealthMonitor.HEALTH_KEY_PREFIX}:{stream_id}"

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

    async def check_stream_health(
        self,
        stream_id: str,
        check_network: bool = True,
        check_process: bool = True,
        check_session: bool = True
    ) -> StreamHealthStatus:
        """
        Проверить здоровье потока.

        Args:
            stream_id: ID потока
            check_network: Проверять сетевое соединение
            check_process: Проверять процесс стрима
            check_session: Проверять Telegram сессию

        Returns:
            StreamHealthStatus с результатами проверки
        """
        r = await self._get_redis()
        key = self._get_health_key(stream_id)

        # Получить текущий статус
        current_status = await self.get_stream_health(stream_id)

        # Инициализировать новый статус если не существует
        if current_status is None:
            current_status = StreamHealthStatus(
                stream_id=stream_id,
                is_healthy=True,
                last_check=datetime.now(timezone.utc),
                consecutive_failures=0,
                total_checks=0,
                failed_checks=0
            )

        # Выполнить проверки
        is_healthy = True
        failure_type = None
        error_message = None

        try:
            # Проверка 1: Circuit Breaker
            cb = self._get_circuit_breaker(stream_id)
            if not cb.allow_request():
                failure_type = RecoveryFailureType.NETWORK.value
                error_message = f"Circuit breaker is OPEN (will try again at {cb.open_until})"
                is_healthy = False
                log.warning(f"Stream {stream_id}: Circuit breaker OPEN, blocking health check")
            else:
                # Проверка 2: Сеть
                if check_network and is_healthy:
                    network_healthy, network_error = await self._check_network(stream_id)
                    if not network_healthy:
                        failure_type = RecoveryFailureType.NETWORK.value
                        error_message = network_error
                        is_healthy = False

                # Проверка 3: Процесс
                if check_process and is_healthy:
                    process_healthy, process_error = await self._check_process(stream_id)
                    if not process_healthy:
                        failure_type = RecoveryFailureType.PROCESS_CRASH.value
                        error_message = process_error
                        is_healthy = False

                # Проверка 4: Сессия
                if check_session and is_healthy:
                    session_healthy, session_error = await self._check_session(stream_id)
                    if not session_healthy:
                        failure_type = RecoveryFailureType.SESSION_EXPIRED.value
                        error_message = session_error
                        is_healthy = False

                # Записать результат в Circuit Breaker
                if is_healthy:
                    cb.record_success()
                else:
                    cb.record_failure()

        except Exception as exc:
            log.error(f"Error checking health for stream {stream_id}: {exc}")
            is_healthy = False
            failure_type = RecoveryFailureType.UNKNOWN.value
            error_message = f"Health check exception: {str(exc)}"
            cb.record_failure()

        # Обновить статус
        now = datetime.now(timezone.utc)
        current_status.last_check = now
        current_status.total_checks += 1

        if is_healthy:
            current_status.is_healthy = True
            current_status.consecutive_failures = 0

            # Callback при восстановлении
            if current_status.consecutive_failures >= self.config.failure_threshold:
                log.info(f"Stream {stream_id} recovered after failures")
                if self.on_recovery_callback:
                    try:
                        await self.on_recovery_callback(stream_id)
                    except Exception as e:
                        log.error(f"Error in recovery callback: {e}")
        else:
            current_status.failed_checks += 1
            current_status.consecutive_failures += 1
            current_status.is_healthy = current_status.consecutive_failures < self.config.failure_threshold
            current_status.last_failure_type = failure_type
            current_status.last_failure_time = now
            current_status.last_error_message = error_message

            # Callback при обнаружении отказа
            if current_status.consecutive_failures >= self.config.failure_threshold:
                log.error(
                    f"Stream {stream_id} failure detected: "
                    f"type={failure_type}, consecutive={current_status.consecutive_failures}"
                )
                if self.on_failure_callback:
                    try:
                        await self.on_failure_callback(
                            stream_id,
                            failure_type or RecoveryFailureType.UNKNOWN.value,
                            error_message or "Unknown error"
                        )
                    except Exception as e:
                        log.error(f"Error in failure callback: {e}")

        # Сохранить в Redis
        await r.hset(key, mapping=current_status.to_redis_dict())
        await r.expire(key, 86400)  # TTL: 24 часа

        return current_status

    async def _check_network(self, stream_id: str) -> tuple[bool, Optional[str]]:
        """
        Проверить сетевое соединение потока.

        Returns:
            (is_healthy, error_message)
        """
        # TODO: Implement actual network check
        # Для начала просто возвращаем True
        # В реальной имплементации здесь будет проверка:
        # - TCP соединение с RTMP сервером
        # - Пинг Telegram серверов
        # - Проверка доступности источника медиа
        return True, None

    async def _check_process(self, stream_id: str) -> tuple[bool, Optional[str]]:
        """
        Проверить что процесс стрима запущен.

        Returns:
            (is_healthy, error_message)
        """
        # TODO: Implement actual process check
        # Для начала просто возвращаем True
        # В реальной имплементации здесь будет проверка:
        # - FFmpeg процесс запущен
        # - PyTgCalls процесс активен
        # - Docker контейнер работает (если используется Docker)
        return True, None

    async def _check_session(self, stream_id: str) -> tuple[bool, Optional[str]]:
        """
        Проверить валидность Telegram сессии.

        Returns:
            (is_healthy, error_message)
        """
        # TODO: Implement actual session check
        # Для начала просто возвращаем True
        # В реальной имплементации здесь будет проверка:
        # - Telegram session файл валиден
        # - API credentials не истекли
        # - Нет ошибок авторизации
        return True, None

    async def get_stream_health(self, stream_id: str) -> Optional[StreamHealthStatus]:
        """
        Получить статус здоровья потока.

        Args:
            stream_id: ID потока

        Returns:
            StreamHealthStatus или None если нет данных
        """
        r = await self._get_redis()
        key = self._get_health_key(stream_id)

        data = await r.hgetall(key)
        if not data:
            return None

        try:
            return StreamHealthStatus.from_redis_dict(data)
        except Exception as e:
            log.error(f"Error parsing health data for stream {stream_id}: {e}")
            return None

    async def is_stream_healthy(self, stream_id: str) -> bool:
        """
        Проверить здоров ли поток (упрощенная проверка).

        Args:
            stream_id: ID потока

        Returns:
            True если поток здоров
        """
        status = await self.get_stream_health(stream_id)
        return status is not None and status.is_healthy

    # ========== Background Monitoring ==========

    async def start_monitoring(self, stream_id: str) -> None:
        """
        Запустить фоновый мониторинг потока.

        Args:
            stream_id: ID потока
        """
        # Остановить существующий монитор
        await self.stop_monitoring(stream_id)

        # Создать новую задачу
        task = asyncio.create_task(self._monitor_loop(stream_id))
        self._monitor_tasks[stream_id] = task

        log.info(f"Started background monitoring for stream {stream_id}")

    async def stop_monitoring(self, stream_id: str) -> None:
        """
        Остановить мониторинг потока.

        Args:
            stream_id: ID потока
        """
        task = self._monitor_tasks.pop(stream_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                # Expected exception when monitoring task is cancelled during shutdown
                pass
            log.info(f"Stopped monitoring for stream {stream_id}")

    async def _monitor_loop(self, stream_id: str) -> None:
        """Фоновый цикл мониторинга."""
        try:
            while True:
                await self.check_stream_health(stream_id)
                await asyncio.sleep(self.config.check_interval_seconds)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Monitor loop error for stream {stream_id}: {e}")

    # ========== Health Metrics ==========

    async def get_all_unhealthy_streams(self) -> list[StreamHealthStatus]:
        """
        Получить все нездоровые потоки.

        Returns:
            Список статусов нездоровых потоков
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
                    status = StreamHealthStatus.from_redis_dict(data)
                    if not status.is_healthy:
                        unhealthy.append(status)
                except Exception as e:
                    log.error(f"Error parsing health data from {key}: {e}")

        return unhealthy

    async def reset_stream_health(self, stream_id: str) -> bool:
        """
        Сбросить статус здоровья потока (после ручного вмешательства).

        Args:
            stream_id: ID потока

        Returns:
            True если статус был сброшен
        """
        r = await self._get_redis()
        key = self._get_health_key(stream_id)

        # Удалить из Redis
        deleted = await r.delete(key)

        # Сбросить Circuit Breaker
        if stream_id in self._circuit_breakers:
            self._circuit_breakers[stream_id].reset()

        if deleted:
            log.info(f"Reset health status for stream {stream_id}")
        else:
            log.warning(f"No health status to reset for stream {stream_id}")

        return deleted > 0

    def get_circuit_breaker_info(self, stream_id: str) -> Optional[dict]:
        """
        Получить информацию о Circuit Breaker для потока.

        Args:
            stream_id: ID потока

        Returns:
            Словарь с информацией о Circuit Breaker или None
        """
        cb = self._circuit_breakers.get(stream_id)
        if cb:
            return cb.get_state_info()
        return None


# Singleton instance
_stream_health_monitor: Optional[StreamHealthMonitor] = None


def get_stream_health_monitor() -> StreamHealthMonitor:
    """Получить singleton экземпляр StreamHealthMonitor."""
    global _stream_health_monitor
    if _stream_health_monitor is None:
        _stream_health_monitor = StreamHealthMonitor()
    return _stream_health_monitor


async def shutdown_stream_health_monitor() -> None:
    """Закрыть StreamHealthMonitor при завершении приложения."""
    global _stream_health_monitor
    if _stream_health_monitor is not None:
        await _stream_health_monitor.close()
        _stream_health_monitor = None
