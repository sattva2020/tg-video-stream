"""
Auto-End Service

Сервис для автоматического завершения стрима при отсутствии слушателей.

Функционал:
- Запуск таймера при listeners_count = 0
- Отмена таймера при появлении слушателей
- Отправка WebSocket предупреждений
- Логирование причин завершения

Storage: Redis String с TTL (auto_end_timer:{channel_id})

Использование:
    auto_end = AutoEndService()
    await auto_end.start_timer(channel_id)  # Запустить таймер
    await auto_end.cancel_timer(channel_id)  # Отменить таймер
    await auto_end.check_timer(channel_id)   # Проверить статус
"""

import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Awaitable, Any

import redis.asyncio as redis

from src.config import settings
from src.models.stream_state import AutoEndTimer, AutoEndWarning
from src.services.prometheus_metrics import (
    record_auto_end,
    set_auto_end_timer,
)

log = logging.getLogger(__name__)


class AutoEndServiceError(Exception):
    """Базовое исключение для ошибок AutoEndService."""
    pass


class AutoEndService:
    """
    Сервис управления auto-end таймерами.
    
    Использует Redis TTL для автоматического срабатывания таймера.
    
    Attributes:
        timeout_minutes: Таймаут до завершения (по умолчанию из .env)
        warning_intervals: Интервалы предупреждений в секундах
    """
    
    # Redis key patterns
    TIMER_KEY_PREFIX = "auto_end_timer"
    STATE_KEY_PREFIX = "auto_end_state"
    REDIS_KEY_PREFIX = TIMER_KEY_PREFIX  # Legacy alias for older tests
    
    # Интервалы предупреждений (в секундах до завершения)
    DEFAULT_WARNING_INTERVALS = [60, 30, 10]
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        timeout_minutes: Optional[int] = None,
        warning_intervals: Optional[list[int]] = None,
        on_auto_end_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
        on_warning_callback: Optional[Callable[[int, int, str], Awaitable[None]]] = None
    ):
        """
        Инициализация AutoEndService.
        
        Args:
            redis_url: URL Redis (по умолчанию из settings)
            timeout_minutes: Таймаут в минутах
            warning_intervals: Интервалы предупреждений
            on_auto_end_callback: Callback при срабатывании (channel_id, reason)
            on_warning_callback: Callback для предупреждений (channel_id, remaining, timeout_at)
        """
        self.redis_url = redis_url or settings.REDIS_URL

        resolved_timeout = timeout_minutes if timeout_minutes is not None else self._get_default_timeout()
        self.timeout_minutes = max(1, min(60, resolved_timeout))

        intervals = warning_intervals or self.DEFAULT_WARNING_INTERVALS
        sanitized = []
        for interval in intervals:
            try:
                value = int(interval)
            except (TypeError, ValueError):
                continue
            if value > 0:
                sanitized.append(value)
        self.warning_intervals = sanitized or self.DEFAULT_WARNING_INTERVALS.copy()
        
        self.on_auto_end_callback = on_auto_end_callback
        self.on_warning_callback = on_warning_callback
        
        self._redis: Optional[redis.Redis] = None
        self._monitor_tasks: dict[int, asyncio.Task] = {}
    
    @staticmethod
    def _get_default_timeout() -> int:
        """Получить таймаут из env переменной."""
        return int(os.getenv("AUTO_END_TIMEOUT_MINUTES", "5"))
    
    async def _get_redis(self) -> redis.Redis:
        """Получение Redis клиента."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis
    
    async def close(self) -> None:
        """Закрытие соединений и задач."""
        # Отменить все мониторы
        for task in self._monitor_tasks.values():
            task.cancel()
        self._monitor_tasks.clear()
        
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
    
    @staticmethod
    def _get_timer_key(channel_id: int) -> str:
        """Генерация Redis ключа для таймера."""
        return AutoEndTimer.get_redis_key(channel_id)
    
    @staticmethod
    def _get_state_key(channel_id: int) -> str:
        """Генерация Redis ключа для состояния."""
        return f"auto_end_state:{channel_id}"
    
    # ========== Timer Operations ==========
    
    async def start_timer(
        self,
        channel_id: int,
        timeout_minutes: Optional[int] = None
    ) -> AutoEndTimer:
        """
        Запустить auto-end таймер для канала.
        
        Args:
            channel_id: ID канала
            timeout_minutes: Таймаут (опционально, иначе default)
            
        Returns:
            AutoEndTimer с данными таймера
        """
        r = await self._get_redis()
        key = self._get_timer_key(channel_id)
        
        timeout = timeout_minutes or self.timeout_minutes
        timeout_seconds = timeout * 60
        
        now = datetime.now(timezone.utc)
        timeout_at = now + timedelta(minutes=timeout)
        
        timer = AutoEndTimer(
            channel_id=channel_id,
            started_at=now,
            timeout_at=timeout_at,
            timeout_minutes=timeout
        )
        
        # Сохранить данные таймера
        await r.setex(key, timeout_seconds, timer.to_redis_json())
        
        # Обновить метрику
        set_auto_end_timer(channel_id, True)
        
        # Запустить мониторинг для предупреждений
        await self._start_monitor(channel_id, timer)
        
        log.info(
            f"Auto-end timer started: channel={channel_id}, "
            f"timeout={timeout}min, timeout_at={timeout_at.isoformat()}"
        )
        
        return timer
    
    def _log_action(self, action: str, channel_id: int, **extra: Any) -> None:
        """Единообразное логирование действий AutoEndService."""

        payload = {k: v for k, v in extra.items() if v is not None}
        log.info(
            "Auto-end action=%s channel=%s payload=%s",
            action,
            channel_id,
            payload or {},
        )

    async def cancel_timer(self, channel_id: int, reason: str = "manual") -> bool:
        """
        Отменить auto-end таймер.
        
        Args:
            channel_id: ID канала
            reason: Причина отмены (для логов)
            
        Returns:
            True если таймер был отменен
        """
        r = await self._get_redis()
        key = self._get_timer_key(channel_id)
        
        # Удалить таймер
        deleted = await r.delete(key)
        
        # Остановить монитор
        await self._stop_monitor(channel_id)
        
        # Обновить метрику
        set_auto_end_timer(channel_id, False)
        
        if deleted:
            self._log_action("cancel_timer", channel_id, reason=reason)
            log.info(f"Auto-end timer cancelled: channel={channel_id}")
            
            # Отправить WebSocket уведомление
            await self._notify_cancelled(channel_id)
        else:
            self._log_action("cancel_timer_noop", channel_id, reason=reason)
        
        return deleted > 0
    
    async def check_timer(self, channel_id: int) -> Optional[AutoEndTimer]:
        """Проверить состояние таймера и вернуть данные, если он активен."""
        r = await self._get_redis()
        key = self._get_timer_key(channel_id)

        ttl = await r.ttl(key)
        if ttl is None or ttl <= 0:
            return None

        timer_json = await r.get(key)
        if timer_json is None:
            return None

        try:
            timer = AutoEndTimer.from_redis_json(timer_json)
            self._log_action("check_timer", channel_id, ttl=ttl)
            return timer
        except Exception as exc:
            log.error(f"Error parsing timer data for channel {channel_id}: {exc}")
            return None

    async def get_timer(self, channel_id: int) -> Optional[AutoEndTimer]:
        """
        Получить данные таймера.
        
        Args:
            channel_id: ID канала
            
        Returns:
            AutoEndTimer или None если таймер не активен
        """
        r = await self._get_redis()
        key = self._get_timer_key(channel_id)
        
        timer_json = await r.get(key)
        if timer_json is None:
            return None
        
        try:
            return AutoEndTimer.from_redis_json(timer_json)
        except Exception as e:
            log.error(f"Error parsing timer data: {e}")
            return None
    
    async def get_remaining_seconds(self, channel_id: int) -> Optional[int]:
        """
        Получить оставшееся время до auto-end.
        
        Args:
            channel_id: ID канала
            
        Returns:
            Секунды до auto-end или None если таймер не активен
        """
        timer = await self.get_timer(channel_id)
        if timer is None:
            return None
        
        return timer.remaining_seconds
    
    async def is_timer_active(self, channel_id: int) -> bool:
        """Проверить, активен ли таймер на основе TTL."""
        r = await self._get_redis()
        key = self._get_timer_key(channel_id)
        ttl = await r.ttl(key)
        return ttl is not None and ttl > 0
    
    async def extend_timer(
        self,
        channel_id: int,
        additional_minutes: int
    ) -> Optional[AutoEndTimer]:
        """
        Продлить таймер на дополнительное время.
        
        Args:
            channel_id: ID канала
            additional_minutes: Дополнительные минуты
            
        Returns:
            Обновленный AutoEndTimer или None
        """
        timer = await self.get_timer(channel_id)
        if timer is None:
            return None
        
        # Рассчитать новый таймаут
        remaining = timer.remaining_seconds or 0
        new_timeout_seconds = remaining + (additional_minutes * 60)
        
        r = await self._get_redis()
        key = self._get_timer_key(channel_id)
        
        # Обновить данные таймера и TTL
        new_timeout_at = datetime.now(timezone.utc) + timedelta(seconds=new_timeout_seconds)
        timer.timeout_at = new_timeout_at
        
        await r.setex(key, new_timeout_seconds, timer.to_redis_json())
        
        log.info(
            f"Auto-end timer extended: channel={channel_id}, "
            f"additional={additional_minutes}min"
        )
        
        return timer
    
    # ========== Auto-End Trigger ==========
    
    async def trigger_auto_end(self, channel_id: int, reason: str = "timeout") -> None:
        """
        Сработать auto-end для канала.
        
        Args:
            channel_id: ID канала
            reason: Причина (timeout, no_listeners, manual)
        """
        # Записать метрику
        record_auto_end(channel_id, reason)
        
        # Очистить таймер
        await self.cancel_timer(channel_id)
        
        log.info(f"Auto-end triggered: channel={channel_id}, reason={reason}")
        
        # Вызвать callback
        if self.on_auto_end_callback:
            try:
                await self.on_auto_end_callback(channel_id, reason)
            except Exception as e:
                log.error(f"Error in auto-end callback: {e}")
        
        # Отправить WebSocket уведомление
        await self._notify_triggered(channel_id, reason)
    
    # ========== Monitor for Warnings ==========
    
    async def _start_monitor(self, channel_id: int, timer: AutoEndTimer) -> None:
        """Запустить фоновый мониторинг для предупреждений."""
        # Остановить существующий монитор
        await self._stop_monitor(channel_id)
        
        # Создать новую задачу
        task = asyncio.create_task(self._monitor_loop(channel_id, timer))
        self._monitor_tasks[channel_id] = task
    
    async def _stop_monitor(self, channel_id: int) -> None:
        """Остановить мониторинг."""
        task = self._monitor_tasks.pop(channel_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, channel_id: int, timer: AutoEndTimer) -> None:
        """Цикл мониторинга для отправки предупреждений."""
        sent_warnings = set()
        
        try:
            while True:
                remaining = timer.remaining_seconds
                
                if remaining is None or remaining <= 0:
                    # Таймер истек — триггерим auto-end
                    await self.trigger_auto_end(channel_id, "timeout")
                    break
                
                # Проверка интервалов предупреждений
                for interval in self.warning_intervals:
                    if remaining <= interval and interval not in sent_warnings:
                        await self._send_warning(channel_id, remaining, timer.timeout_at)
                        sent_warnings.add(interval)
                
                # Ожидание до следующей проверки
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"Monitor error for channel {channel_id}: {e}")
    
    async def _send_warning(
        self,
        channel_id: int,
        remaining_seconds: int,
        timeout_at: datetime
    ) -> None:
        """Отправить предупреждение о скором auto-end."""
        log.info(
            f"Auto-end warning: channel={channel_id}, "
            f"remaining={remaining_seconds}s"
        )
        
        # Вызвать callback
        if self.on_warning_callback:
            try:
                await self.on_warning_callback(
                    channel_id,
                    remaining_seconds,
                    timeout_at.isoformat()
                )
            except Exception as e:
                log.error(f"Error in warning callback: {e}")
        
        # Отправить WebSocket уведомление
        await self._notify_warning(channel_id, remaining_seconds, timeout_at)
    
    # ========== WebSocket Notifications ==========
    
    async def _notify_warning(
        self,
        channel_id: int,
        remaining_seconds: int,
        timeout_at: datetime
    ) -> None:
        """Отправить WebSocket уведомление о предупреждении."""
        try:
            from src.api.websocket import notify_auto_end_warning
            await notify_auto_end_warning(
                channel_id=channel_id,
                remaining_seconds=remaining_seconds,
                timeout_at=timeout_at.isoformat()
            )
        except ImportError:
            log.debug("WebSocket module not available")
        except Exception as e:
            log.warning(f"Failed to send warning notification: {e}")
    
    async def _notify_cancelled(self, channel_id: int) -> None:
        """Отправить WebSocket уведомление об отмене."""
        try:
            from src.api.websocket import notify_auto_end_cancelled
            await notify_auto_end_cancelled(channel_id)
        except ImportError:
            pass
        except Exception as e:
            log.warning(f"Failed to send cancelled notification: {e}")
    
    async def _notify_triggered(self, channel_id: int, reason: str) -> None:
        """Отправить WebSocket уведомление о срабатывании."""
        try:
            from src.api.websocket import notify_auto_end_triggered
            await notify_auto_end_triggered(channel_id, reason)
        except ImportError:
            pass
        except Exception as e:
            log.warning(f"Failed to send triggered notification: {e}")
    
    # ========== Listeners Integration ==========
    
    async def on_listeners_update(
        self,
        channel_id: int,
        listeners_count: int
    ) -> None:
        """
        Обработчик изменения количества слушателей.
        
        Вызывается из PyTgCalls on_participants_change.
        
        Args:
            channel_id: ID канала
            listeners_count: Новое количество слушателей
        """
        is_active = await self.is_timer_active(channel_id)
        
        if listeners_count <= 0:
            # Нет слушателей — запустить таймер (если не активен)
            if not is_active:
                await self.start_timer(channel_id)
                self._log_action("listeners_zero_start", channel_id)
                log.info(
                    f"No listeners, auto-end timer started: channel={channel_id}"
                )
        else:
            # Есть слушатели — отменить таймер (если активен)
            if is_active:
                await self.cancel_timer(channel_id, reason="listener_joined")
                self._log_action(
                    "listeners_present_cancel",
                    channel_id,
                    listeners=listeners_count,
                )
                log.info(
                    f"Listeners present ({listeners_count}), "
                    f"auto-end timer cancelled: channel={channel_id}"
                )

    async def on_listeners_change(
        self,
        channel_id: int,
        listeners_count: int
    ) -> None:
        """Поддерживаем старое название обработчика для совместимости."""

        await self.on_listeners_update(channel_id, listeners_count)

    async def get_warning(self, channel_id: int) -> Optional[AutoEndWarning]:
        """Вернуть предупреждение о скором завершении, если таймер близок к срабатыванию."""

        timer = await self.get_timer(channel_id)
        if timer is None:
            return None

        r = await self._get_redis()
        ttl = await r.ttl(self._get_timer_key(channel_id))
        if ttl is None or ttl <= 0:
            return None

        threshold = max(self.warning_intervals) if self.warning_intervals else 60
        if ttl > threshold:
            return None

        warning = AutoEndWarning.from_timer(timer, remaining_seconds=ttl)
        self._log_action("timer_warning", channel_id, remaining_seconds=ttl)
        return warning

    async def log_stream_end(
        self,
        channel_id: int,
        reason: str = "manual",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Зафиксировать причину завершения стрима в логах и метриках."""

        metadata = metadata or {}
        self._log_action("stream_end", channel_id, reason=reason, metadata=metadata)
        log.info(
            "Stream ended: channel=%s, reason=%s, metadata=%s",
            channel_id,
            reason,
            metadata,
        )


# Singleton instance
_auto_end_service: Optional[AutoEndService] = None


def get_auto_end_service() -> AutoEndService:
    """Получить singleton экземпляр AutoEndService."""
    global _auto_end_service
    if _auto_end_service is None:
        _auto_end_service = AutoEndService()
    return _auto_end_service


async def shutdown_auto_end_service() -> None:
    """Закрыть AutoEndService при завершении приложения."""
    global _auto_end_service
    if _auto_end_service is not None:
        await _auto_end_service.close()
        _auto_end_service = None
