"""
Viewer Count Monitor Service

Сервис для мониторинга количества зрителей и обнаружения аномалий.

Функционал:
- Периодическая проверка количества зрителей
- Обнаружение низкого количества зрителей
- Отслеживание резкого падения количества зрителей
- Хранение истории просмотров в Redis
- Callbacks для событий алертов

Storage: Redis Hash (viewer_count:{stream_id}) для хранения метрик,
         Redis List (viewer_count:{stream_id}:history) для истории

Использование:
    monitor = ViewerCountMonitor()
    await monitor.check_viewer_count(stream_id, current_count)  # Проверить
    status = await monitor.get_viewer_status(stream_id)  # Получить статус
    await monitor.start_monitoring(stream_id)  # Запустить фоновый мониторинг
"""

import asyncio
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable, Any, Dict, List

import redis.asyncio as redis

from src.config import settings

log = logging.getLogger(__name__)


class ViewerCountMonitorError(Exception):
    """Базовое исключение для ошибок ViewerCountMonitor."""
    pass


@dataclass
class ViewerCountStatus:
    """Статус количества зрителей потока."""
    stream_id: str
    current_count: int
    last_check: datetime
    is_below_threshold: bool
    threshold: Optional[int] = None
    consecutive_below_threshold: int = 0
    peak_count: int = 0
    peak_time: Optional[datetime] = None
    average_count: float = 0.0
    drop_percent: float = 0.0
    last_drop_time: Optional[datetime] = None
    total_checks: int = 0
    trend: str = "stable"  # rising, falling, stable

    def to_redis_dict(self) -> dict:
        """Конвертировать в dict для Redis."""
        data = asdict(self)
        # Конвертируем datetime в isoformat
        if data.get('last_check'):
            data['last_check'] = data['last_check'].isoformat()
        if data.get('peak_time'):
            data['peak_time'] = data['peak_time'].isoformat()
        if data.get('last_drop_time'):
            data['last_drop_time'] = data['last_drop_time'].isoformat()
        return {k: v for k, v in data.items() if v is not None}

    @classmethod
    def from_redis_dict(cls, data: dict) -> 'ViewerCountStatus':
        """Создать из dict из Redis."""
        if data.get('last_check'):
            data['last_check'] = datetime.fromisoformat(data['last_check'])
        if data.get('peak_time'):
            data['peak_time'] = datetime.fromisoformat(data['peak_time'])
        if data.get('last_drop_time'):
            data['last_drop_time'] = datetime.fromisoformat(data['last_drop_time'])
        return cls(**data)


@dataclass
class ViewerCountConfig:
    """Конфигурация мониторинга количества зрителей."""
    check_interval_seconds: int = 60          # Интервал автоматических проверок
    low_threshold: int = 10                   # Порог для low viewer alert
    drop_threshold_percent: float = 50.0      # Порог для drop rate alert (%)
    history_size: int = 100                   # Размер истории для расчета среднего
    below_threshold_trigger: int = 3          # Количество проверок для алерта
    drop_window_seconds: int = 300            # Окно для расчета drop rate (секунды)
    alert_cooldown_seconds: int = 600         # Минимальное время между алертами


class ViewerCountMonitor:
    """
    Сервис мониторинга количества зрителей.

    Использует Redis для хранения состояния и истории просмотров.

    Attributes:
        config: Конфигурация мониторинга
        on_low_viewers_callback: Callback при низком количестве зрителей (stream_id, count, threshold)
        on_viewers_drop_callback: Callback при резком падении (stream_id, current, previous, drop_percent)
        on_recovery_callback: Callback при восстановлении (stream_id)
    """

    # Redis key patterns
    COUNT_KEY_PREFIX = "viewer_count"
    HISTORY_KEY_SUFFIX = "history"
    ALERT_LAST_SENT_PREFIX = "viewer_alert_last"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        config: Optional[ViewerCountConfig] = None,
        on_low_viewers_callback: Optional[Callable[[str, int, int], Awaitable[None]]] = None,
        on_viewers_drop_callback: Optional[Callable[[str, int, int, float], Awaitable[None]]] = None,
        on_recovery_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ):
        """
        Инициализация ViewerCountMonitor.

        Args:
            redis_url: URL Redis (по умолчанию из settings)
            config: Конфигурация мониторинга
            on_low_viewers_callback: Callback при низком количестве зрителей (stream_id, count, threshold)
            on_viewers_drop_callback: Callback при резком падении (stream_id, current, previous, drop_percent)
            on_recovery_callback: Callback при восстановлении (stream_id)
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.config = config or ViewerCountConfig()
        self.on_low_viewers_callback = on_low_viewers_callback
        self.on_viewers_drop_callback = on_viewers_drop_callback
        self.on_recovery_callback = on_recovery_callback

        self._redis: Optional[redis.Redis] = None
        self._monitor_tasks: Dict[str, asyncio.Task] = {}

        log.info(
            f"ViewerCountMonitor initialized: check_interval={self.config.check_interval_seconds}s, "
            f"low_threshold={self.config.low_threshold}, drop_threshold={self.config.drop_threshold_percent}%"
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
    def _get_count_key(stream_id: str) -> str:
        """Генерация Redis ключа для статуса количества зрителей."""
        return f"{ViewerCountMonitor.COUNT_KEY_PREFIX}:{stream_id}"

    @staticmethod
    def _get_history_key(stream_id: str) -> str:
        """Генерация Redis ключа для истории просмотров."""
        return f"{ViewerCountMonitor.COUNT_KEY_PREFIX}:{stream_id}:{ViewerCountMonitor.HISTORY_KEY_SUFFIX}"

    @staticmethod
    def _get_alert_last_sent_key(stream_id: str, alert_type: str) -> str:
        """Генерация Redis ключа для времени последнего алерта."""
        return f"{ViewerCountMonitor.ALERT_LAST_SENT_PREFIX}:{stream_id}:{alert_type}"

    async def close(self) -> None:
        """Закрытие соединений и задач."""
        # Отменить все мониторы
        for task in self._monitor_tasks.values():
            task.cancel()
        self._monitor_tasks.clear()

        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    # ========== Viewer Count Operations ==========

    async def check_viewer_count(
        self,
        stream_id: str,
        current_count: int,
        threshold: Optional[int] = None
    ) -> ViewerCountStatus:
        """
        Проверить количество зрителей потока.

        Args:
            stream_id: ID потока
            current_count: Текущее количество зрителей
            threshold: Порог для алерта (по умолчанию из config)

        Returns:
            ViewerCountStatus с результатами проверки
        """
        if current_count < 0:
            raise ViewerCountMonitorError("Viewer count cannot be negative")

        r = await self._get_redis()
        key = self._get_count_key(stream_id)
        history_key = self._get_history_key(stream_id)
        threshold = threshold or self.config.low_threshold

        # Получить текущий статус
        current_status = await self.get_viewer_status(stream_id)

        # Инициализировать новый статус если не существует
        if current_status is None:
            current_status = ViewerCountStatus(
                stream_id=stream_id,
                current_count=current_count,
                last_check=datetime.now(timezone.utc),
                is_below_threshold=current_count < threshold,
                threshold=threshold,
                consecutive_below_threshold=0,
                peak_count=current_count,
                peak_time=datetime.now(timezone.utc),
                average_count=float(current_count),
                drop_percent=0.0,
                total_checks=0,
                trend="stable"
            )

        # Добавить в историю
        await r.lpush(history_key, f"{current_count}:{int(datetime.now(timezone.utc).timestamp())}")
        await r.ltrim(history_key, 0, self.config.history_size - 1)
        await r.expire(history_key, 86400)  # TTL: 24 часа

        # Получить историю для расчетов
        history_data = await r.lrange(history_key, 0, self.config.history_size - 1)
        history_counts = []
        for item in history_data:
            try:
                count_str = item.split(':')[0]
                history_counts.append(int(count_str))
            except (ValueError, IndexError):
                continue

        # Расчет метрик
        previous_count = current_status.current_count
        avg_count = sum(history_counts) / len(history_counts) if history_counts else float(current_count)
        peak_count = max(history_counts) if history_counts else current_count

        # Определить время пика
        peak_time = current_status.peak_time
        if peak_count != current_status.peak_count:
            # Найти время пика в истории
            for item in history_data:
                try:
                    count_str, timestamp_str = item.split(':')
                    if int(count_str) == peak_count:
                        peak_time = datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc)
                        break
                except (ValueError, IndexError):
                    continue

        # Расчет drop percentage
        drop_percent = 0.0
        if peak_count > 0 and current_count < peak_count:
            drop_percent = ((peak_count - current_count) / peak_count) * 100

        # Определение тренда
        if len(history_counts) >= 3:
            recent = history_counts[:3]
            if recent[0] > recent[1] > recent[2]:
                trend = "rising"
            elif recent[0] < recent[1] < recent[2]:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Обновить статус
        now = datetime.now(timezone.utc)
        current_status.current_count = current_count
        current_status.last_check = now
        current_status.total_checks += 1
        current_status.average_count = avg_count
        current_status.peak_count = peak_count
        current_status.peak_time = peak_time
        current_status.drop_percent = drop_percent
        current_status.trend = trend

        # Проверка условий для алертов
        was_below_threshold = current_status.is_below_threshold

        # Условие 1: Низкое количество зрителей
        is_below_threshold = current_count < threshold
        current_status.is_below_threshold = is_below_threshold

        if is_below_threshold:
            current_status.consecutive_below_threshold += 1
        else:
            current_status.consecutive_below_threshold = 0

        # Условие 2: Резкое падение
        is_significant_drop = (
            drop_percent >= self.config.drop_threshold_percent and
            current_count > 0  # Исключаем падение до 0
        )

        # Callback при низком количестве зрителей
        if is_below_threshold and not was_below_threshold:
            # Только начало падения ниже порога
            if current_status.consecutive_below_threshold >= self.config.below_threshold_trigger:
                if await self._can_send_alert(stream_id, "low_viewers"):
                    log.warning(
                        f"Stream {stream_id}: Low viewers detected: {current_count} < {threshold}"
                    )
                    if self.on_low_viewers_callback:
                        try:
                            await self.on_low_viewers_callback(stream_id, current_count, threshold)
                            await self._mark_alert_sent(stream_id, "low_viewers")
                        except Exception as e:
                            log.error(f"Error in low_viewers callback: {e}")

        # Callback при резком падении
        if is_significant_drop:
            if await self._can_send_alert(stream_id, "viewers_drop"):
                log.warning(
                    f"Stream {stream_id}: Significant viewer drop: "
                    f"{current_count} from {peak_count} ({drop_percent:.1f}%)"
                )
                if self.on_viewers_drop_callback:
                    try:
                        await self.on_viewers_drop_callback(
                            stream_id, current_count, peak_count, drop_percent
                        )
                        await self._mark_alert_sent(stream_id, "viewers_drop")
                        current_status.last_drop_time = now
                    except Exception as e:
                        log.error(f"Error in viewers_drop callback: {e}")

        # Callback при восстановлении
        if was_below_threshold and not is_below_threshold:
            if current_status.consecutive_below_threshold == 0:
                log.info(f"Stream {stream_id}: Viewer count recovered to {current_count}")
                if self.on_recovery_callback:
                    try:
                        await self.on_recovery_callback(stream_id)
                    except Exception as e:
                        log.error(f"Error in recovery callback: {e}")

        # Сохранить в Redis
        await r.hset(key, mapping=current_status.to_redis_dict())
        await r.expire(key, 86400)  # TTL: 24 часа

        return current_status

    async def get_viewer_status(self, stream_id: str) -> Optional[ViewerCountStatus]:
        """
        Получить статус количества зрителей потока.

        Args:
            stream_id: ID потока

        Returns:
            ViewerCountStatus или None если нет данных
        """
        r = await self._get_redis()
        key = self._get_count_key(stream_id)

        data = await r.hgetall(key)
        if not data:
            return None

        try:
            return ViewerCountStatus.from_redis_dict(data)
        except Exception as e:
            log.error(f"Error parsing viewer status data for stream {stream_id}: {e}")
            return None

    async def get_viewer_history(
        self,
        stream_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Получить историю количества зрителей.

        Args:
            stream_id: ID потока
            limit: Максимальное количество записей

        Returns:
            Список словарей с данными о количестве зрителей
        """
        r = await self._get_redis()
        history_key = self._get_history_key(stream_id)

        history_data = await r.lrange(history_key, 0, limit - 1)
        history = []

        for item in history_data:
            try:
                count_str, timestamp_str = item.split(':')
                history.append({
                    'count': int(count_str),
                    'timestamp': datetime.fromtimestamp(int(timestamp_str), tz=timezone.utc)
                })
            except (ValueError, IndexError):
                continue

        return history

    # ========== Background Monitoring ==========

    async def start_monitoring(
        self,
        stream_id: str,
        get_current_count: Callable[[], Awaitable[int]]
    ) -> None:
        """
        Запустить фоновый мониторинг количества зрителей.

        Args:
            stream_id: ID потока
            get_current_count: Async функция для получения текущего количества зрителей
        """
        # Остановить существующий монитор
        await self.stop_monitoring(stream_id)

        # Создать новую задачу
        task = asyncio.create_task(self._monitor_loop(stream_id, get_current_count))
        self._monitor_tasks[stream_id] = task

        log.info(f"Started background viewer count monitoring for stream {stream_id}")

    async def stop_monitoring(self, stream_id: str) -> None:
        """
        Остановить мониторинг количества зрителей.

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
            log.info(f"Stopped viewer count monitoring for stream {stream_id}")

    async def _monitor_loop(
        self,
        stream_id: str,
        get_current_count: Callable[[], Awaitable[int]]
    ) -> None:
        """Фоновый цикл мониторинга."""
        try:
            while True:
                try:
                    current_count = await get_current_count()
                    await self.check_viewer_count(stream_id, current_count)
                except Exception as e:
                    log.error(f"Error checking viewer count for stream {stream_id}: {e}")

                await asyncio.sleep(self.config.check_interval_seconds)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Monitor loop error for stream {stream_id}: {e}")

    # ========== Alert Cooldown ==========

    async def _can_send_alert(self, stream_id: str, alert_type: str) -> bool:
        """
        Проверить можно ли отправить алерт (cooldown).

        Args:
            stream_id: ID потока
            alert_type: Тип алерта (low_viewers, viewers_drop)

        Returns:
            True если можно отправить алерт
        """
        r = await self._get_redis()
        key = self._get_alert_last_sent_key(stream_id, alert_type)

        last_sent_str = await r.get(key)
        if not last_sent_str:
            return True

        try:
            last_sent = datetime.fromtimestamp(int(last_sent_str), tz=timezone.utc)
            cooldown_expiry = last_sent + timedelta(seconds=self.config.alert_cooldown_seconds)
            return datetime.now(timezone.utc) >= cooldown_expiry
        except (ValueError, OSError):
            return True

    async def _mark_alert_sent(self, stream_id: str, alert_type: str) -> None:
        """
        Отметить что алерт был отправлен.

        Args:
            stream_id: ID потока
            alert_type: Тип алерта
        """
        r = await self._get_redis()
        key = self._get_alert_last_sent_key(stream_id, alert_type)

        now_timestamp = int(datetime.now(timezone.utc).timestamp())
        await r.set(key, now_timestamp, ex=self.config.alert_cooldown_seconds)

    # ========== Statistics ==========

    async def get_all_streams_below_threshold(self) -> List[ViewerCountStatus]:
        """
        Получить все потоки с количеством зрителей ниже порога.

        Returns:
            Список статусов потоков с низким количеством зрителей
        """
        r = await self._get_redis()
        pattern = f"{self.COUNT_KEY_PREFIX}:*"
        keys = []

        async for key in r.scan_iter(match=pattern):
            # Исключаем ключи истории
            if not key.endswith(f":{self.HISTORY_KEY_SUFFIX}"):
                keys.append(key)

        below_threshold = []
        for key in keys:
            data = await r.hgetall(key)
            if data:
                try:
                    status = ViewerCountStatus.from_redis_dict(data)
                    if status.is_below_threshold:
                        below_threshold.append(status)
                except Exception as e:
                    log.error(f"Error parsing viewer data from {key}: {e}")

        return below_threshold

    async def reset_viewer_status(self, stream_id: str) -> bool:
        """
        Сбросить статус количества зрителей потока.

        Args:
            stream_id: ID потока

        Returns:
            True если статус был сброшен
        """
        r = await self._get_redis()
        count_key = self._get_count_key(stream_id)
        history_key = self._get_history_key(stream_id)

        # Удалить из Redis
        deleted_count = await r.delete(count_key)
        deleted_history = await r.delete(history_key)

        if deleted_count or deleted_history:
            log.info(f"Reset viewer count status for stream {stream_id}")
            return True
        else:
            log.warning(f"No viewer count status to reset for stream {stream_id}")
            return False


# Singleton instance
_viewer_count_monitor: Optional[ViewerCountMonitor] = None


def get_viewer_count_monitor() -> ViewerCountMonitor:
    """Получить singleton экземпляр ViewerCountMonitor."""
    global _viewer_count_monitor
    if _viewer_count_monitor is None:
        _viewer_count_monitor = ViewerCountMonitor()
    return _viewer_count_monitor


async def shutdown_viewer_count_monitor() -> None:
    """Закрыть ViewerCountMonitor при завершении приложения."""
    global _viewer_count_monitor
    if _viewer_count_monitor is not None:
        await _viewer_count_monitor.close()
        _viewer_count_monitor = None
