"""
Redis-хелперы для дедупликации, rate-limit и окон тишины.
"""
import asyncio
import logging
from datetime import datetime, time
from typing import List, Optional, Tuple

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover - среда без Redis
    redis = None

from src.core.config import settings

logger = logging.getLogger(__name__)


class NotificationControls:
    """Хелперы подавления уведомлений (дедуп, rate-limit, окна тишины)."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL

    async def _get_redis(self):
        if not redis:
            raise RuntimeError("redis.asyncio недоступен")
        return await redis.from_url(self.redis_url, decode_responses=True)

    async def is_deduplicated(self, *, event_id: str, rule_id: str, recipient_id: str, ttl_sec: int) -> bool:
        """Проверка и установка ключа дедупликации. Возвращает True, если событие уже было обработано."""
        if ttl_sec <= 0:
            return False
        key = f"notif:dedup:{event_id}:{rule_id}:{recipient_id}"
        async with await self._get_redis() as r:
            # set nx returns True if key set (not duplicate)
            created = await r.set(key, "1", ex=ttl_sec, nx=True)
            return created is None  # None -> уже существовал

    async def check_rate_limit(
        self,
        *,
        scope: str,
        limit: int,
        window_sec: int,
    ) -> Tuple[bool, int]:
        """Инкрементирует счётчик. Возвращает (разрешено, текущее значение)."""
        if limit <= 0 or window_sec <= 0:
            return True, 0
        key = f"notif:rl:{scope}"
        async with await self._get_redis() as r:
            pipe = r.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_sec)
            count, _ = await pipe.execute()
            allowed = count <= limit
            return allowed, count

    @staticmethod
    def _time_in_windows(now: datetime, windows: List[dict]) -> bool:
        """Проверяет принадлежность времени окну тишины. Окна: [{"start":"HH:MM","end":"HH:MM"}]."""
        current = now.time()
        for window in windows:
            try:
                start = datetime.strptime(window.get("start", "00:00"), "%H:%M").time()
                end = datetime.strptime(window.get("end", "23:59"), "%H:%M").time()
            except Exception:
                logger.warning("Некорректное окно тишины: %s", window)
                continue
            if start <= end:
                if start <= current <= end:
                    return True
            else:  # Перекрывает полночь
                if current >= start or current <= end:
                    return True
        return False

    async def is_silenced(self, *, recipient_id: Optional[str], windows: Optional[List[dict]], cache_ttl: int = 300) -> bool:
        """Проверяет окна тишины. Кэширует результат в Redis для стабильного ответа."""
        if not windows:
            return False
        now = datetime.utcnow()
        key = f"notif:silence:{recipient_id or 'global'}:{now.strftime('%Y%m%d%H')}"
        # Попытка прочитать кешированный флаг
        try:
            async with await self._get_redis() as r:
                cached = await r.get(key)
                if cached is not None:
                    return cached == "1"
                active = self._time_in_windows(now, windows)
                await r.set(key, "1" if active else "0", ex=cache_ttl)
                return active
        except Exception:
            logger.warning("Проверка окон тишины без Redis, fallback", exc_info=True)
            return self._time_in_windows(now, windows)

    async def close(self):
        # Совместимость: отдельного состояния нет
        await asyncio.sleep(0)
