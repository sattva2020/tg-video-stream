import asyncio
import logging
import os
from typing import List, Optional, Dict, Any
from collections import deque
import json

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

try:
    from streamer.utils import expand_playlist, best_stream_url
    from streamer import audio_utils
except ImportError:
    from utils import expand_playlist, best_stream_url
    import audio_utils

log = logging.getLogger("tg_video_streamer")

# Redis ключи
QUEUE_KEY_PREFIX = "stream_queue:"
STATE_KEY_PREFIX = "stream_state:"


class StreamQueue:
    """
    Очередь стрима с поддержкой Redis синхронизации.
    
    Redis sync позволяет бэкенду и стримеру видеть одну и ту же очередь.
    При добавлении/удалении элементов изменения отражаются в Redis.
    """
    
    def __init__(self, max_buffer_size: int = 3, channel_id: int = None):
        self.queue = asyncio.Queue(maxsize=max_buffer_size)
        self.playlist_items = deque()
        self.current_item: Optional[Dict[str, Any]] = None
        self.is_running = False
        self.buffer_task: Optional[asyncio.Task] = None
        self.channel_id = channel_id
        self.redis: Optional[Any] = None
        self._redis_sync_enabled = False

    async def init_redis(self, redis_url: str = None):
        """Инициализация Redis подключения для синхронизации."""
        if aioredis is None:
            log.warning("redis.asyncio not available, Redis sync disabled")
            return False
        
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis = aioredis.from_url(url, decode_responses=True)
            await self.redis.ping()
            self._redis_sync_enabled = True
            log.info(f"Redis sync enabled for channel {self.channel_id}")
            return True
        except Exception as e:
            log.warning(f"Redis connection failed, sync disabled: {e}")
            self.redis = None
            self._redis_sync_enabled = False
            return False

    async def close_redis(self):
        """Закрытие Redis подключения."""
        if self.redis:
            await self.redis.close()
            self.redis = None
            self._redis_sync_enabled = False

    def _queue_key(self) -> str:
        """Redis ключ для очереди канала."""
        return f"{QUEUE_KEY_PREFIX}{self.channel_id}"
    
    def _state_key(self) -> str:
        """Redis ключ для состояния стрима."""
        return f"{STATE_KEY_PREFIX}{self.channel_id}"

    async def _sync_to_redis(self):
        """Синхронизация локальной очереди в Redis."""
        if not self._redis_sync_enabled or not self.redis:
            return
        
        try:
            key = self._queue_key()
            # Сериализуем все элементы playlist_items
            items = [json.dumps(item) for item in self.playlist_items]
            
            # Атомарно заменяем список
            async with self.redis.pipeline() as pipe:
                await pipe.delete(key)
                if items:
                    await pipe.rpush(key, *items)
                await pipe.execute()
                
            log.debug(f"Synced {len(items)} items to Redis for channel {self.channel_id}")
        except Exception as e:
            log.error(f"Redis sync error: {e}")

    async def _sync_from_redis(self):
        """Синхронизация из Redis в локальную очередь."""
        if not self._redis_sync_enabled or not self.redis:
            return
        
        try:
            key = self._queue_key()
            items = await self.redis.lrange(key, 0, -1)
            
            self.playlist_items.clear()
            for item_json in items:
                try:
                    item = json.loads(item_json)
                    self.playlist_items.append(item)
                except json.JSONDecodeError:
                    log.warning(f"Invalid JSON in Redis queue: {item_json}")
                    
            log.debug(f"Synced {len(self.playlist_items)} items from Redis for channel {self.channel_id}")
        except Exception as e:
            log.error(f"Redis sync from error: {e}")

    async def _update_state(self, **kwargs):
        """Обновление состояния стрима в Redis."""
        if not self._redis_sync_enabled or not self.redis:
            return
        
        try:
            key = self._state_key()
            state_updates = {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                           for k, v in kwargs.items()}
            await self.redis.hset(key, mapping=state_updates)
        except Exception as e:
            log.error(f"Redis state update error: {e}")

    async def add_items(self, items: List[Dict[str, Any]]):
        """Adds items to the internal playlist to be processed."""
        for item in items:
            self.playlist_items.append(item)
        
        # Sync to Redis
        await self._sync_to_redis()
        
        if not self.is_running:
            self.start_buffering()

    def start_buffering(self):
        """Starts the background buffering task."""
        if self.is_running:
            return
        self.is_running = True
        self.buffer_task = asyncio.create_task(self._buffer_loop())
        log.info("StreamQueue buffering started")

    async def stop(self):
        """Stops the buffering task."""
        self.is_running = False
        if self.buffer_task:
            self.buffer_task.cancel()
            try:
                await self.buffer_task
            except asyncio.CancelledError:
                pass
        log.info("StreamQueue buffering stopped")

    async def _buffer_loop(self):
        """Background loop that prepares items and puts them into the async queue."""
        while self.is_running:
            if not self.playlist_items:
                # No more items to process, wait a bit
                await asyncio.sleep(1)
                continue

            if self.queue.full():
                await asyncio.sleep(1)
                continue

            item = self.playlist_items.popleft()
            track_url = item.get("url")
            track_id = item.get("id")

            if not track_url:
                log.warning("Skipping playlist entry without URL: %s", item)
                continue

            try:
                log.debug(f"Buffering item: {track_url}")
                expanded = await expand_playlist([track_url])
                
                if not expanded:
                    log.warning("Playlist item produced no playable URLs: %s", track_url)
                    continue

                for link in expanded:
                    # Resolve the direct link
                    direct = await best_stream_url(link)
                    
                    # Detect content type if audio
                    content_type = None
                    profile = None
                    
                    if audio_utils.is_audio_file(direct):
                        try:
                            content_type = await audio_utils.detect_content_type(direct)
                        except Exception:
                            pass
                        profile = audio_utils.get_transcoding_profile(direct, content_type=content_type)

                    prepared_item = {
                        "original_item": item,
                        "direct_url": direct,
                        "link": link,
                        "is_audio": audio_utils.is_audio_file(direct),
                        "profile": profile,
                        "track_id": track_id
                    }
                    
                    await self.queue.put(prepared_item)
                    log.info(f"Buffered item: {link}")

            except Exception as e:
                log.error(f"Error buffering item {track_url}: {e}")
                await asyncio.sleep(1)

    async def get_next(self):
        """Retrieves the next prepared item from the queue."""
        item = await self.queue.get()
        self.current_item = item
        
        # Update state in Redis
        await self._update_state(
            current_track=item.get("original_item", {}),
            is_playing=True
        )
        
        return item

    async def on_track_end(self, track_id: str = None, reason: str = "completed"):
        """
        Handler вызываемый при завершении трека.
        
        Args:
            track_id: ID завершённого трека
            reason: Причина завершения (completed, skipped, error)
        """
        log.info(f"Track ended: {track_id}, reason: {reason}")
        
        # Очистка current_item
        self.current_item = None
        
        # Sync state
        await self._update_state(
            current_track=None,
            last_track_id=track_id,
            last_track_reason=reason
        )
        
        # Sync queue (элемент удалён)
        await self._sync_to_redis()
        
        # Callback для внешних обработчиков
        if hasattr(self, '_on_track_end_callback') and self._on_track_end_callback:
            try:
                await self._on_track_end_callback(track_id, reason)
            except Exception as e:
                log.error(f"Track end callback error: {e}")

    def set_on_track_end_callback(self, callback):
        """Устанавливает callback для события завершения трека."""
        self._on_track_end_callback = callback

    async def skip_current(self) -> bool:
        """
        Пропуск текущего трека.
        
        Returns:
            True если трек был пропущен
        """
        if self.current_item:
            track_id = self.current_item.get("track_id")
            await self.on_track_end(track_id, reason="skipped")
            return True
        return False

    async def remove_item(self, track_id: str) -> bool:
        """
        Удаление элемента из очереди по ID.
        
        Args:
            track_id: ID трека для удаления
            
        Returns:
            True если элемент был удалён
        """
        # Ищем в playlist_items
        for i, item in enumerate(self.playlist_items):
            if item.get("id") == track_id:
                del self.playlist_items[i]
                await self._sync_to_redis()
                log.info(f"Removed track {track_id} from queue")
                return True
        return False

    async def move_item(self, track_id: str, new_position: int) -> bool:
        """
        Перемещение элемента на новую позицию.
        
        Args:
            track_id: ID трека
            new_position: Новая позиция (0-based)
            
        Returns:
            True если элемент был перемещён
        """
        # Ищем элемент
        item_to_move = None
        old_position = -1
        
        for i, item in enumerate(self.playlist_items):
            if item.get("id") == track_id:
                item_to_move = item
                old_position = i
                break
        
        if item_to_move is None:
            return False
        
        # Удаляем и вставляем на новую позицию
        del self.playlist_items[old_position]
        
        # Корректируем позицию
        new_position = max(0, min(new_position, len(self.playlist_items)))
        self.playlist_items.insert(new_position, item_to_move)
        
        await self._sync_to_redis()
        log.info(f"Moved track {track_id} from {old_position} to {new_position}")
        return True

    async def priority_add(self, item: Dict[str, Any]) -> bool:
        """
        Добавление элемента в начало очереди (приоритетное).
        
        Args:
            item: Элемент для добавления
            
        Returns:
            True если элемент добавлен
        """
        self.playlist_items.appendleft(item)
        await self._sync_to_redis()
        log.info(f"Priority added track: {item.get('id')}")
        return True

    async def get_queue_items(self) -> List[Dict[str, Any]]:
        """
        Получение всех элементов очереди.
        
        Returns:
            Список элементов очереди
        """
        return list(self.playlist_items)

    async def get_current_track(self) -> Optional[Dict[str, Any]]:
        """
        Получение текущего воспроизводимого трека.
        
        Returns:
            Текущий трек или None
        """
        return self.current_item

    def empty(self):
        return self.queue.empty() and not self.playlist_items


class QueueManager:
    """
    Менеджер очередей для нескольких каналов.
    
    Управляет StreamQueue для каждого канала и обеспечивает
    единую точку доступа к очередям.
    """
    
    def __init__(self):
        self._queues: Dict[int, StreamQueue] = {}
        self._redis_url: Optional[str] = None

    async def init(self, redis_url: str = None):
        """Инициализация с Redis."""
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        log.info("QueueManager initialized")

    async def get_queue(self, channel_id: int) -> StreamQueue:
        """
        Получение или создание очереди для канала.
        
        Args:
            channel_id: ID канала
            
        Returns:
            StreamQueue для канала
        """
        if channel_id not in self._queues:
            queue = StreamQueue(channel_id=channel_id)
            if self._redis_url:
                await queue.init_redis(self._redis_url)
            self._queues[channel_id] = queue
            log.info(f"Created queue for channel {channel_id}")
        
        return self._queues[channel_id]

    async def remove_queue(self, channel_id: int):
        """Удаление очереди канала."""
        if channel_id in self._queues:
            queue = self._queues[channel_id]
            await queue.stop()
            await queue.close_redis()
            del self._queues[channel_id]
            log.info(f"Removed queue for channel {channel_id}")

    async def close_all(self):
        """Закрытие всех очередей."""
        for channel_id in list(self._queues.keys()):
            await self.remove_queue(channel_id)
        log.info("All queues closed")

    def get_active_channels(self) -> List[int]:
        """Список активных каналов."""
        return list(self._queues.keys())
