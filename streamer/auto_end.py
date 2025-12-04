"""
Auto-End Handler for Streamer

Модуль для отслеживания слушателей и автоматического завершения стрима.

Интеграция с PyTgCalls для получения событий on_participants_change.

Использование:
    auto_end = AutoEndHandler(pytg, chat_id)
    await auto_end.start()  # Начать мониторинг
    await auto_end.stop()   # Остановить
    
    # Или через декоратор
    @pytg.on_participants_change()
    async def handler(client, update):
        await auto_end.on_participants_change(update)
"""

import os
import asyncio
import logging
from typing import Optional, Union, Callable, Awaitable
from datetime import datetime, timezone, timedelta

log = logging.getLogger("tg_video_streamer.auto_end")

# Попытка импорта pytgcalls
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import Update
    from pytgcalls.types.groups import GroupCallParticipant
    PYTG_AVAILABLE = True
except ImportError:
    PYTG_AVAILABLE = False
    log.warning("pytgcalls not available — AutoEndHandler disabled")

# Попытка импорта Redis
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    log.warning("redis.asyncio not available — using local timer only")


class AutoEndHandler:
    """
    Обработчик автоматического завершения стрима.
    
    Отслеживает количество слушателей через PyTgCalls и
    запускает таймер завершения при отсутствии слушателей.
    
    Attributes:
        pytg: Экземпляр PyTgCalls
        chat_id: ID чата/канала
        timeout_minutes: Таймаут до завершения
        is_running: Флаг активного мониторинга
    """
    
    # Redis ключи
    TIMER_KEY_PREFIX = "auto_end_timer"
    STATE_KEY_PREFIX = "auto_end_state"
    
    def __init__(
        self,
        pytg: Optional["PyTgCalls"],
        chat_id: Union[int, str],
        timeout_minutes: Optional[int] = None,
        on_auto_end_callback: Optional[Callable[[], Awaitable[None]]] = None,
        on_warning_callback: Optional[Callable[[int], Awaitable[None]]] = None,
        redis_url: Optional[str] = None
    ):
        """
        Инициализация AutoEndHandler.
        
        Args:
            pytg: Экземпляр PyTgCalls
            chat_id: ID чата для мониторинга
            timeout_minutes: Таймаут в минутах (из env если не указан)
            on_auto_end_callback: Callback при срабатывании auto-end
            on_warning_callback: Callback для предупреждений (секунды до завершения)
            redis_url: URL Redis для синхронизации (опционально)
        """
        self.pytg = pytg
        self.chat_id = chat_id
        self.timeout_minutes = timeout_minutes or self._get_default_timeout()
        self.on_auto_end_callback = on_auto_end_callback
        self.on_warning_callback = on_warning_callback
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
        
        self._is_running = False
        self._timer_task: Optional[asyncio.Task] = None
        self._timer_started_at: Optional[datetime] = None
        self._timer_timeout_at: Optional[datetime] = None
        self._listeners_count = 0
        self._redis: Optional["aioredis.Redis"] = None
        self._stop_event = asyncio.Event()
        
        # Интервалы предупреждений (секунды до завершения)
        self._warning_intervals = [60, 30, 10]
        self._sent_warnings: set[int] = set()
    
    @staticmethod
    def _get_default_timeout() -> int:
        """Получить таймаут из env переменной."""
        return int(os.getenv("AUTO_END_TIMEOUT_MINUTES", "5"))
    
    @property
    def is_running(self) -> bool:
        """Активен ли мониторинг."""
        return self._is_running
    
    @property
    def is_timer_active(self) -> bool:
        """Активен ли таймер."""
        return self._timer_task is not None and not self._timer_task.done()
    
    @property
    def remaining_seconds(self) -> Optional[int]:
        """Оставшееся время до auto-end в секундах."""
        if not self.is_timer_active or self._timer_timeout_at is None:
            return None
        
        now = datetime.now(timezone.utc)
        remaining = (self._timer_timeout_at - now).total_seconds()
        return max(0, int(remaining))
    
    @property
    def listeners_count(self) -> int:
        """Текущее количество слушателей."""
        return self._listeners_count
    
    async def _get_redis(self) -> Optional["aioredis.Redis"]:
        """Получить Redis клиент."""
        if not REDIS_AVAILABLE:
            return None
        
        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
            except Exception as e:
                log.warning(f"Failed to connect to Redis: {e}")
                return None
        
        return self._redis
    
    async def _close_redis(self) -> None:
        """Закрыть Redis соединение."""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
    
    def _get_timer_key(self) -> str:
        """Получить Redis ключ для таймера."""
        return f"{self.TIMER_KEY_PREFIX}:{self.chat_id}"
    
    # ========== Lifecycle ==========
    
    async def start(self) -> None:
        """Начать мониторинг слушателей."""
        if self._is_running:
            log.debug("AutoEndHandler already running")
            return
        
        self._is_running = True
        self._stop_event.clear()
        
        # Получить начальное количество слушателей
        await self._update_listeners_count()
        
        log.info(
            f"AutoEndHandler started: chat_id={self.chat_id}, "
            f"timeout={self.timeout_minutes}min, listeners={self._listeners_count}"
        )
        
        # Если нет слушателей сразу — запустить таймер
        if self._listeners_count == 0:
            await self._start_timer()
    
    async def stop(self) -> None:
        """Остановить мониторинг."""
        if not self._is_running:
            return
        
        self._is_running = False
        self._stop_event.set()
        
        # Остановить таймер
        await self._cancel_timer()
        
        # Закрыть Redis
        await self._close_redis()
        
        log.info(f"AutoEndHandler stopped: chat_id={self.chat_id}")
    
    # ========== Timer Management ==========
    
    async def _start_timer(self) -> None:
        """Запустить таймер auto-end."""
        if self.is_timer_active:
            log.debug("Timer already active, skipping")
            return
        
        self._timer_started_at = datetime.now(timezone.utc)
        self._timer_timeout_at = self._timer_started_at + timedelta(
            minutes=self.timeout_minutes
        )
        self._sent_warnings.clear()
        
        self._timer_task = asyncio.create_task(self._timer_loop())
        
        # Сохранить в Redis
        await self._save_timer_to_redis()
        
        log.info(
            f"Auto-end timer started: chat_id={self.chat_id}, "
            f"timeout_at={self._timer_timeout_at.isoformat()}"
        )
    
    async def _cancel_timer(self) -> None:
        """Отменить таймер."""
        if self._timer_task is not None:
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass
            self._timer_task = None
        
        self._timer_started_at = None
        self._timer_timeout_at = None
        self._sent_warnings.clear()
        
        # Удалить из Redis
        await self._delete_timer_from_redis()
        
        log.info(f"Auto-end timer cancelled: chat_id={self.chat_id}")
    
    async def _timer_loop(self) -> None:
        """Цикл таймера с отправкой предупреждений."""
        try:
            while not self._stop_event.is_set():
                remaining = self.remaining_seconds
                
                if remaining is None:
                    break
                
                if remaining <= 0:
                    # Таймер истек — триггерим auto-end
                    await self._trigger_auto_end("timeout")
                    break
                
                # Проверка интервалов предупреждений
                for interval in self._warning_intervals:
                    if remaining <= interval and interval not in self._sent_warnings:
                        await self._send_warning(remaining)
                        self._sent_warnings.add(interval)
                
                # Ожидание
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Timer loop error: {e}")
    
    async def _trigger_auto_end(self, reason: str) -> None:
        """Сработать auto-end."""
        log.info(f"Auto-end triggered: chat_id={self.chat_id}, reason={reason}")
        
        # Очистить таймер
        self._timer_task = None
        self._timer_started_at = None
        self._timer_timeout_at = None
        
        # Удалить из Redis
        await self._delete_timer_from_redis()
        
        # Вызвать callback
        if self.on_auto_end_callback:
            try:
                await self.on_auto_end_callback()
            except Exception as e:
                log.error(f"Error in auto-end callback: {e}")
    
    async def _send_warning(self, remaining_seconds: int) -> None:
        """Отправить предупреждение."""
        log.info(
            f"Auto-end warning: chat_id={self.chat_id}, "
            f"remaining={remaining_seconds}s"
        )
        
        if self.on_warning_callback:
            try:
                await self.on_warning_callback(remaining_seconds)
            except Exception as e:
                log.error(f"Error in warning callback: {e}")
    
    # ========== Redis Persistence ==========
    
    async def _save_timer_to_redis(self) -> None:
        """Сохранить данные таймера в Redis."""
        redis_client = await self._get_redis()
        if redis_client is None:
            return
        
        try:
            key = self._get_timer_key()
            timeout_seconds = self.timeout_minutes * 60
            
            import json
            data = {
                "chat_id": str(self.chat_id),
                "started_at": self._timer_started_at.isoformat() if self._timer_started_at else None,
                "timeout_at": self._timer_timeout_at.isoformat() if self._timer_timeout_at else None,
                "timeout_minutes": self.timeout_minutes
            }
            
            await redis_client.set(key, json.dumps(data), ex=timeout_seconds)
            
        except Exception as e:
            log.warning(f"Failed to save timer to Redis: {e}")
    
    async def _delete_timer_from_redis(self) -> None:
        """Удалить таймер из Redis."""
        redis_client = await self._get_redis()
        if redis_client is None:
            return
        
        try:
            key = self._get_timer_key()
            await redis_client.delete(key)
        except Exception as e:
            log.warning(f"Failed to delete timer from Redis: {e}")
    
    # ========== Listeners Monitoring ==========
    
    async def _update_listeners_count(self) -> None:
        """Обновить количество слушателей."""
        if not PYTG_AVAILABLE or self.pytg is None:
            return
        
        try:
            # Получить участников голосового чата
            call = self.pytg.get_call(self.chat_id)
            if call is None:
                self._listeners_count = 0
                return
            
            # Получить количество участников (исключая бота)
            # Примечание: в реальном PyTgCalls это может требовать других методов
            # Здесь используем приблизительный подход
            self._listeners_count = 0  # TODO: Реализовать получение участников
            
        except Exception as e:
            log.warning(f"Failed to get listeners count: {e}")
            self._listeners_count = 0
    
    async def on_participants_change(
        self,
        chat_id: Union[int, str],
        participants_count: int
    ) -> None:
        """
        Обработчик изменения количества участников.
        
        Вызывается из PyTgCalls on_participants_change.
        
        Args:
            chat_id: ID чата
            participants_count: Новое количество участников
        """
        if str(chat_id) != str(self.chat_id):
            return
        
        old_count = self._listeners_count
        # Вычитаем 1 (бота) из общего количества
        self._listeners_count = max(0, participants_count - 1)
        
        log.debug(
            f"Participants change: chat_id={chat_id}, "
            f"old={old_count}, new={self._listeners_count}"
        )
        
        if old_count > 0 and self._listeners_count == 0:
            # Были слушатели, теперь нет — запустить таймер
            await self._start_timer()
            
        elif old_count == 0 and self._listeners_count > 0:
            # Не было слушателей, появились — отменить таймер
            await self._cancel_timer()


class AutoEndManager:
    """
    Менеджер AutoEndHandler для управления несколькими каналами.
    
    Использование:
        manager = AutoEndManager(pytg)
        await manager.start_monitoring(channel_id)
        await manager.stop_monitoring(channel_id)
    """
    
    def __init__(
        self,
        pytg: Optional["PyTgCalls"],
        on_auto_end_callback: Optional[Callable[[Union[int, str]], Awaitable[None]]] = None
    ):
        self.pytg = pytg
        self.on_auto_end_callback = on_auto_end_callback
        self._handlers: dict[Union[int, str], AutoEndHandler] = {}
    
    def get_handler(self, chat_id: Union[int, str]) -> Optional[AutoEndHandler]:
        """Получить handler для канала."""
        return self._handlers.get(chat_id)
    
    async def start_monitoring(
        self,
        chat_id: Union[int, str],
        timeout_minutes: Optional[int] = None
    ) -> AutoEndHandler:
        """
        Начать мониторинг для канала.
        
        Args:
            chat_id: ID канала
            timeout_minutes: Таймаут (опционально)
            
        Returns:
            AutoEndHandler для канала
        """
        # Остановить существующий, если есть
        if chat_id in self._handlers:
            await self.stop_monitoring(chat_id)
        
        async def on_end():
            if self.on_auto_end_callback:
                await self.on_auto_end_callback(chat_id)
        
        handler = AutoEndHandler(
            pytg=self.pytg,
            chat_id=chat_id,
            timeout_minutes=timeout_minutes,
            on_auto_end_callback=on_end
        )
        
        await handler.start()
        self._handlers[chat_id] = handler
        
        return handler
    
    async def stop_monitoring(self, chat_id: Union[int, str]) -> None:
        """Остановить мониторинг для канала."""
        handler = self._handlers.pop(chat_id, None)
        if handler:
            await handler.stop()
    
    async def on_participants_change(
        self,
        chat_id: Union[int, str],
        participants_count: int
    ) -> None:
        """
        Глобальный обработчик изменения участников.
        
        Вызывается из PyTgCalls on_participants_change.
        """
        handler = self._handlers.get(chat_id)
        if handler:
            await handler.on_participants_change(chat_id, participants_count)
    
    async def stop_all(self) -> None:
        """Остановить все обработчики."""
        for chat_id in list(self._handlers.keys()):
            await self.stop_monitoring(chat_id)


# Singleton manager instance
_auto_end_manager: Optional[AutoEndManager] = None


def get_auto_end_manager(
    pytg: Optional["PyTgCalls"] = None,
    on_auto_end_callback: Optional[Callable[[Union[int, str]], Awaitable[None]]] = None
) -> AutoEndManager:
    """Получить singleton экземпляр AutoEndManager."""
    global _auto_end_manager
    if _auto_end_manager is None:
        _auto_end_manager = AutoEndManager(pytg, on_auto_end_callback)
    return _auto_end_manager
