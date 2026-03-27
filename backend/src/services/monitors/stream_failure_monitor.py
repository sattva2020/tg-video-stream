"""
Stream Failure Alert Monitor Service

Сервис для мониторинга отказов потоков и генерации алертов.

Функционал:
- Мониторинг здоровья потоков через StreamHealthMonitor
- Генерация алертов при обнаружении отказов
- Отслеживание типов отказов (network, API, codec, session)
- Оповещения о восстановлении потоков
- Хранение истории отказов в Redis
- Callbacks для событий алертов

Storage: Redis Hash (stream_failure_alerts:{stream_id}) для хранения метрик отказов

Использование:
    monitor = StreamFailureAlertMonitor()
    await monitor.check_stream_failures(stream_id)  # Проверить отказы
    status = await monitor.get_failure_status(stream_id)  # Получить статус
    await monitor.start_monitoring(stream_id)  # Запустить фоновый мониторинг
"""

import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable, Any, Dict, List

import redis.asyncio as redis

from src.config import settings
from src.services.stream_health_monitor import StreamHealthMonitor, StreamHealthStatus

log = logging.getLogger(__name__)


class StreamFailureAlertMonitorError(Exception):
    """Базовое исключение для ошибок StreamFailureAlertMonitor."""
    pass


@dataclass
class StreamFailureAlertStatus:
    """Статус алертов отказа потока."""
    stream_id: str
    last_check: datetime
    is_failing: bool
    consecutive_failures: int
    total_failure_events: int = 0
    last_failure_type: Optional[str] = None
    last_failure_time: Optional[datetime] = None
    last_failure_message: Optional[str] = None
    last_recovery_time: Optional[datetime] = None
    total_recoveries: int = 0
    current_failure_streak: int = 0
    longest_failure_streak: int = 0
    alert_cooldown_until: Optional[datetime] = None

    def to_redis_dict(self) -> dict:
        """Конвертировать в dict для Redis."""
        data = asdict(self)
        # Конвертируем datetime в isoformat
        if data.get('last_check'):
            data['last_check'] = data['last_check'].isoformat()
        if data.get('last_failure_time'):
            data['last_failure_time'] = data['last_failure_time'].isoformat()
        if data.get('last_recovery_time'):
            data['last_recovery_time'] = data['last_recovery_time'].isoformat()
        if data.get('alert_cooldown_until'):
            data['alert_cooldown_until'] = data['alert_cooldown_until'].isoformat()
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_redis_dict(cls, data: dict) -> 'StreamFailureAlertStatus':
        """Создать из dict из Redis."""
        if data.get('last_check'):
            data['last_check'] = datetime.fromisoformat(data['last_check'])
        if data.get('last_failure_time'):
            data['last_failure_time'] = datetime.fromisoformat(data['last_failure_time'])
        if data.get('last_recovery_time'):
            data['last_recovery_time'] = datetime.fromisoformat(data['last_recovery_time'])
        if data.get('alert_cooldown_until'):
            data['alert_cooldown_until'] = datetime.fromisoformat(data['alert_cooldown_until'])
        return cls(**data)


@dataclass
class StreamFailureAlertConfig:
    """Конфигурация мониторинга отказов потоков."""
    check_interval_seconds: int = 30          # Интервал автоматических проверок
    alert_cooldown_seconds: int = 300         # Минимальное время между алертами (5 минут)
    failure_threshold: int = 3                # Количество отказов для алерта
    recovery_notification: bool = True        # Отправлять уведомление о восстановлении
    include_health_details: bool = True       # Включать детали здоровья в алерт


class StreamFailureAlertMonitor:
    """
    Сервис мониторинга отказов потоков для генерации алертов.

    Интегрируется с StreamHealthMonitor для обнаружения отказов и генерации алертов.

    Attributes:
        config: Конфигурация мониторинга отказов
        health_monitor: Экземпляр StreamHealthMonitor для проверок здоровья
        on_failure_detected_callback: Callback при обнаружении отказа (stream_id, failure_type, message, health_status)
        on_failure_recovery_callback: Callback при восстановлении (stream_id, health_status)
    """

    # Redis key patterns
    ALERT_STATUS_KEY_PREFIX = "stream_failure_alerts"
    ALERT_HISTORY_SUFFIX = "history"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        config: Optional[StreamFailureAlertConfig] = None,
        health_monitor: Optional[StreamHealthMonitor] = None,
        on_failure_detected_callback: Optional[Callable[[str, str, str, StreamHealthStatus], Awaitable[None]]] = None,
        on_failure_recovery_callback: Optional[Callable[[str, StreamHealthStatus], Awaitable[None]]] = None
    ):
        """
        Инициализация StreamFailureAlertMonitor.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            config: Конфигурация мониторинга отказов
            health_monitor: Экземпляр StreamHealthMonitor (по умолчанию singleton)
            on_failure_detected_callback: Callback при обнаружении отказа (stream_id, failure_type, message, health_status)
            on_failure_recovery_callback: Callback при восстановлении (stream_id, health_status)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.config = config or StreamFailureAlertConfig()
        self.health_monitor = health_monitor
        self.on_failure_detected_callback = on_failure_detected_callback
        self.on_failure_recovery_callback = on_failure_recovery_callback

        self._redis: Optional[redis.Redis] = None
        self._monitor_tasks: Dict[str, asyncio.Task] = {}

        # Lazy load health monitor if not provided
        if self.health_monitor is None:
            from src.services.stream_health_monitor import get_stream_health_monitor
            self.health_monitor = get_stream_health_monitor()

        log.info(
            f"StreamFailureAlertMonitor initialized: check_interval={self.config.check_interval_seconds}s, "
            f"failure_threshold={self.config.failure_threshold}, "
            f"alert_cooldown={self.config.alert_cooldown_seconds}s"
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
    def _get_alert_status_key(stream_id: str) -> str:
        """Генерация Redis ключа для статуса алерта отказа."""
        return f"{StreamFailureAlertMonitor.ALERT_STATUS_KEY_PREFIX}:{stream_id}"

    @staticmethod
    def _get_alert_history_key(stream_id: str) -> str:
        """Генерация Redis ключа для истории алертов."""
        return f"{StreamFailureAlertMonitor.ALERT_STATUS_KEY_PREFIX}:{stream_id}:{StreamFailureAlertMonitor.ALERT_HISTORY_SUFFIX}"

    async def close(self) -> None:
        """Закрытие соединений и задач."""
        # Отменить все мониторы
        for task in self._monitor_tasks.values():
            task.cancel()
        self._monitor_tasks.clear()

        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    # ========== Failure Detection Operations ==========

    async def check_stream_failures(self, stream_id: str) -> StreamFailureAlertStatus:
        """
        Проверить наличие отказов потока и генерировать алерты.

        Args:
            stream_id: ID потока

        Returns:
            StreamFailureAlertStatus с результатами проверки
        """
        r = await self._get_redis()
        key = self._get_alert_status_key(stream_id)

        # Получить статус здоровья из StreamHealthMonitor
        health_status = await self.health_monitor.get_stream_health(stream_id)

        if health_status is None:
            # Если нет данных о здоровье, считаем что поток в порядке
            # но логируем предупреждение
            log.warning(f"No health data available for stream {stream_id}")
            health_status = StreamHealthStatus(
                stream_id=stream_id,
                is_healthy=True,
                last_check=datetime.now(timezone.utc),
                consecutive_failures=0,
                total_checks=0,
                failed_checks=0
            )

        # Получить текущий статус алерта
        current_alert_status = await self.get_failure_status(stream_id)

        # Инициализировать новый статус если не существует
        if current_alert_status is None:
            current_alert_status = StreamFailureAlertStatus(
                stream_id=stream_id,
                last_check=datetime.now(timezone.utc),
                is_failing=False,
                consecutive_failures=0,
                total_failure_events=0,
                total_recoveries=0,
                current_failure_streak=0,
                longest_failure_streak=0
            )

        # Проверить состояние здоровья
        now = datetime.now(timezone.utc)
        was_failing = current_alert_status.is_failing

        # Обновить последний чек
        current_alert_status.last_check = now

        # Проверить находится ли поток в состоянии отказа
        is_healthy = health_status.is_healthy
        consecutive_health_failures = health_status.consecutive_failures

        if not is_healthy and consecutive_health_failures >= self.config.failure_threshold:
            # Поток в состоянии отказа
            current_alert_status.is_failing = True
            current_alert_status.consecutive_failures = consecutive_health_failures
            current_alert_status.last_failure_type = health_status.last_failure_type
            current_alert_status.last_failure_time = health_status.last_failure_time or now
            current_alert_status.last_failure_message = health_status.last_error_message
            current_alert_status.current_failure_streak += 1

            # Обновить самый длинный streak
            if current_alert_status.current_failure_streak > current_alert_status.longest_failure_streak:
                current_alert_status.longest_failure_streak = current_alert_status.current_failure_streak

            # Проверить cooldown и отправить алрет
            can_send_alert = await self._can_send_alert(stream_id, now)

            if can_send_alert and not was_failing:
                # Новый отказ - отправить алерт
                current_alert_status.total_failure_events += 1

                log.error(
                    f"Stream {stream_id} failure detected: "
                    f"type={health_status.last_failure_type}, "
                    f"consecutive={consecutive_health_failures}, "
                    f"message={health_status.last_error_message}"
                )

                # Сохранить в историю
                await self._save_failure_to_history(stream_id, health_status)

                # Callback при обнаружении отказа
                if self.on_failure_detected_callback:
                    try:
                        await self.on_failure_detected_callback(
                            stream_id,
                            health_status.last_failure_type or "unknown",
                            health_status.last_error_message or "Unknown error",
                            health_status
                        )
                    except Exception as e:
                        log.error(f"Error in failure_detected callback: {e}")

                # Установить cooldown
                await self._mark_alert_sent(stream_id, now)

        elif is_healthy and was_failing:
            # Поток восстановился
            current_alert_status.is_failing = False
            current_alert_status.consecutive_failures = 0
            current_alert_status.last_recovery_time = now
            current_alert_status.total_recoveries += 1
            current_alert_status.current_failure_streak = 0

            log.info(f"Stream {stream_id} recovered from failure")

            # Callback при восстановлении
            if self.config.recovery_notification and self.on_failure_recovery_callback:
                try:
                    await self.on_failure_recovery_callback(stream_id, health_status)
                except Exception as e:
                    log.error(f"Error in failure_recovery callback: {e}")

        elif is_healthy:
            # Поток здоров
            current_alert_status.is_failing = False
            current_alert_status.consecutive_failures = 0

        # Сохранить в Redis
        await r.hset(key, mapping=current_alert_status.to_redis_dict())
        await r.expire(key, 86400)  # TTL: 24 часа

        return current_alert_status

    async def _save_failure_to_history(
        self,
        stream_id: str,
        health_status: StreamHealthStatus
    ) -> None:
        """
        Сохранить информацию об отказе в историю.

        Args:
            stream_id: ID потока
            health_status: Статус здоровья потока
        """
        r = await self._get_redis()
        history_key = self._get_alert_history_key(stream_id)

        failure_data = (
            f"{health_status.last_failure_type}:"
            f"{health_status.last_error_message}:"
            f"{int(datetime.now(timezone.utc).timestamp())}:"
            f"{health_status.consecutive_failures}"
        )

        await r.lpush(history_key, failure_data)
        await r.ltrim(history_key, 0, 99)  # Хранить последние 100 отказов
        await r.expire(history_key, 604800)  # TTL: 7 дней

    async def get_failure_status(self, stream_id: str) -> Optional[StreamFailureAlertStatus]:
        """
        Получить статус алертов отказа потока.

        Args:
            stream_id: ID потока

        Returns:
            StreamFailureAlertStatus или None если нет данных
        """
        r = await self._get_redis()
        key = self._get_alert_status_key(stream_id)

        data = await r.hgetall(key)
        if not data:
            return None

        try:
            return StreamFailureAlertStatus.from_redis_dict(data)
        except Exception as e:
            log.error(f"Error parsing failure alert status for stream {stream_id}: {e}")
            return None

    async def get_failure_history(
        self,
        stream_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Получить историю отказов потока.

        Args:
            stream_id: ID потока
            limit: Максимальное количество записей

        Returns:
            Список словарей с данными об отказах
        """
        r = await self._get_redis()
        history_key = self._get_alert_history_key(stream_id)

        history_data = await r.lrange(history_key, 0, limit - 1)
        history = []

        for item in history_data:
            try:
                parts = item.split(':')
                if len(parts) >= 4:
                    failure_type = parts[0]
                    error_message = parts[1]
                    timestamp = datetime.fromtimestamp(int(parts[2]), tz=timezone.utc)
                    consecutive_failures = int(parts[3])

                    history.append({
                        'failure_type': failure_type,
                        'error_message': error_message,
                        'timestamp': timestamp,
                        'consecutive_failures': consecutive_failures
                    })
            except (ValueError, IndexError) as e:
                log.error(f"Error parsing history item: {e}")
                continue

        return history

    # ========== Background Monitoring ==========

    async def start_monitoring(self, stream_id: str) -> None:
        """
        Запустить фоновый мониторинг отказов потока.

        Args:
            stream_id: ID потока
        """
        # Остановить существующий монитор
        await self.stop_monitoring(stream_id)

        # Создать новую задачу
        task = asyncio.create_task(self._monitor_loop(stream_id))
        self._monitor_tasks[stream_id] = task

        log.info(f"Started background failure alert monitoring for stream {stream_id}")

    async def stop_monitoring(self, stream_id: str) -> None:
        """
        Остановить мониторинг отказов потока.

        Args:
            stream_id: ID потока
        """
        task = self._monitor_tasks.pop(stream_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            log.info(f"Stopped failure alert monitoring for stream {stream_id}")

    async def _monitor_loop(self, stream_id: str) -> None:
        """Фоновый цикл мониторинга."""
        try:
            while True:
                try:
                    await self.check_stream_failures(stream_id)
                except Exception as e:
                    log.error(f"Error checking failures for stream {stream_id}: {e}")

                await asyncio.sleep(self.config.check_interval_seconds)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Monitor loop error for stream {stream_id}: {e}")

    # ========== Alert Cooldown ==========

    async def _can_send_alert(self, stream_id: str, now: datetime) -> bool:
        """
        Проверить можно ли отправить алерт (cooldown).

        Args:
            stream_id: ID потока
            now: Текущее время

        Returns:
            True если можно отправить алерт
        """
        r = await self._get_redis()
        key = self._get_alert_status_key(stream_id)

        # Получить текущий статус
        data = await r.hgetall(key)
        if not data:
            return True

        try:
            cooldown_until_str = data.get('alert_cooldown_until')
            if not cooldown_until_str:
                return True

            cooldown_until = datetime.fromisoformat(cooldown_until_str)
            return now >= cooldown_until
        except (ValueError, OSError) as e:
            log.error(f"Error checking alert cooldown: {e}")
            return True

    async def _mark_alert_sent(self, stream_id: str, now: datetime) -> None:
        """
        Отметить что алерт был отправлен и установить cooldown.

        Args:
            stream_id: ID потока
            now: Текущее время
        """
        r = await self._get_redis()
        key = self._get_alert_status_key(stream_id)

        cooldown_until = now + timedelta(seconds=self.config.alert_cooldown_seconds)
        await r.hset(key, 'alert_cooldown_until', cooldown_until.isoformat())

    # ========== Statistics ==========

    async def get_all_failing_streams(self) -> List[StreamFailureAlertStatus]:
        """
        Получить все потоки с активными отказами.

        Returns:
            Список статусов потоков с отказами
        """
        r = await self._get_redis()
        pattern = f"{self.ALERT_STATUS_KEY_PREFIX}:*"
        keys = []

        async for key in r.scan_iter(match=pattern):
            # Исключаем ключи истории
            if not key.endswith(f":{self.ALERT_HISTORY_SUFFIX}"):
                keys.append(key)

        failing = []
        for key in keys:
            data = await r.hgetall(key)
            if data:
                try:
                    status = StreamFailureAlertStatus.from_redis_dict(data)
                    if status.is_failing:
                        failing.append(status)
                except Exception as e:
                    log.error(f"Error parsing failure alert data from {key}: {e}")

        return failing

    async def reset_failure_status(self, stream_id: str) -> bool:
        """
        Сбросить статус алертов отказа потока (после ручного вмешательства).

        Args:
            stream_id: ID потока

        Returns:
            True если статус был сброшен
        """
        r = await self._get_redis()
        status_key = self._get_alert_status_key(stream_id)
        history_key = self._get_alert_history_key(stream_id)

        # Удалить из Redis
        deleted_status = await r.delete(status_key)
        deleted_history = await r.delete(history_key)

        if deleted_status or deleted_history:
            log.info(f"Reset failure alert status for stream {stream_id}")
            return True
        else:
            log.warning(f"No failure alert status to reset for stream {stream_id}")
            return False


# Singleton instance
_stream_failure_alert_monitor: Optional[StreamFailureAlertMonitor] = None


def get_stream_failure_alert_monitor() -> StreamFailureAlertMonitor:
    """Получить singleton экземпляр StreamFailureAlertMonitor."""
    global _stream_failure_alert_monitor
    if _stream_failure_alert_monitor is None:
        _stream_failure_alert_monitor = StreamFailureAlertMonitor()
    return _stream_failure_alert_monitor


async def shutdown_stream_failure_alert_monitor() -> None:
    """Закрыть StreamFailureAlertMonitor при завершении приложения."""
    global _stream_failure_alert_monitor
    if _stream_failure_alert_monitor is not None:
        await _stream_failure_alert_monitor.close()
        _stream_failure_alert_monitor = None
