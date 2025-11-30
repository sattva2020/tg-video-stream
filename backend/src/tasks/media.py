"""
Celery tasks для работы с медиа-контентом.

Включает:
- Получение метаданных видео через yt-dlp
- Обновление playlist items
"""
import os
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy Celery import
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    CELERY_AVAILABLE = False


def _get_celery_app():
    """Получает или создаёт Celery приложение."""
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        return None
    return Celery('tg_video_streamer', broker=broker)


def extract_video_metadata(url: str, extract_audio_only: bool = False) -> dict:
    """
    Извлекает метаданные видео/аудио через yt-dlp.
    
    Args:
        url: URL видео (YouTube, etc.)
        extract_audio_only: Если True, извлекает только аудио форматы
        
    Returns:
        dict с метаданными: title, duration, thumbnail, uploader, etc.
    """
    try:
        import yt_dlp
    except ImportError:
        logger.error("yt-dlp not installed")
        return {"error": "yt-dlp not installed"}
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'skip_download': True,
        # Не загружаем видео, только метаданные
        'format': 'bestaudio/best' if extract_audio_only else 'best',
        # Таймаут на извлечение
        'socket_timeout': 30,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                return {"error": "Could not extract video info"}
            
            # Обработка плейлистов
            if info.get('_type') == 'playlist':
                entries = info.get('entries', [])
                return {
                    "is_playlist": True,
                    "playlist_title": info.get('title'),
                    "playlist_id": info.get('id'),
                    "entries_count": len(entries),
                    "entries": [
                        {
                            "url": entry.get('url') or entry.get('webpage_url'),
                            "title": entry.get('title'),
                            "duration": entry.get('duration'),
                            "thumbnail": entry.get('thumbnail'),
                            "uploader": entry.get('uploader'),
                        }
                        for entry in entries[:50]  # Лимит на первые 50
                    ]
                }
            
            # Одиночное видео
            return {
                "is_playlist": False,
                "url": info.get('webpage_url') or url,
                "title": info.get('title'),
                "duration": info.get('duration'),
                "thumbnail": info.get('thumbnail'),
                "uploader": info.get('uploader'),
                "uploader_url": info.get('uploader_url'),
                "view_count": info.get('view_count'),
                "like_count": info.get('like_count'),
                "upload_date": info.get('upload_date'),
                "description": info.get('description', '')[:500],  # Ограничиваем описание
                "channel": info.get('channel'),
                "extractor": info.get('extractor'),
            }
            
    except Exception as e:
        logger.exception(f"Error extracting metadata for {url}")
        return {"error": str(e)}


def update_playlist_item_metadata(item_id: str, metadata: dict) -> bool:
    """
    Обновляет playlist item в БД с полученными метаданными.
    
    Args:
        item_id: UUID playlist item
        metadata: dict с метаданными от extract_video_metadata
        
    Returns:
        True если успешно, False если ошибка
    """
    if metadata.get("error"):
        logger.warning(f"Cannot update item {item_id}: {metadata['error']}")
        return False
        
    from database import SessionLocal
    from src.models.playlist import PlaylistItem
    
    db = SessionLocal()
    try:
        item = db.query(PlaylistItem).filter(PlaylistItem.id == item_id).first()
        if not item:
            logger.warning(f"Playlist item {item_id} not found")
            return False
        
        # Обновляем поля
        if metadata.get("title") and not item.title:
            item.title = metadata["title"]
        
        if metadata.get("duration"):
            item.duration = int(metadata["duration"])
        
        # Дополнительные поля (если есть в модели)
        if hasattr(item, 'thumbnail') and metadata.get("thumbnail"):
            item.thumbnail = metadata["thumbnail"]
        
        if hasattr(item, 'uploader') and metadata.get("uploader"):
            item.uploader = metadata["uploader"]
            
        if hasattr(item, 'metadata_fetched_at'):
            item.metadata_fetched_at = datetime.utcnow()
        
        db.commit()
        logger.info(f"Updated metadata for playlist item {item_id}")
        return True
        
    except Exception as e:
        logger.exception(f"Error updating playlist item {item_id}")
        db.rollback()
        return False
    finally:
        db.close()


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.fetch_video_metadata', bind=True, max_retries=3)
    def fetch_video_metadata_task(self, item_id: str, url: str, audio_only: bool = False):
        """
        Celery task: получает метаданные видео и обновляет playlist item.
        
        Автоматически повторяет при ошибке (до 3 раз с экспоненциальной задержкой).
        """
        logger.info(f"[worker] fetch_video_metadata_task for item {item_id}, url: {url}")
        
        try:
            metadata = extract_video_metadata(url, extract_audio_only=audio_only)
            
            if metadata.get("error"):
                # Retry на recoverable errors
                if "timeout" in metadata["error"].lower() or "network" in metadata["error"].lower():
                    raise self.retry(countdown=30 * (self.request.retries + 1))
                logger.warning(f"Non-retryable error for {item_id}: {metadata['error']}")
                return {"success": False, "error": metadata["error"]}
            
            success = update_playlist_item_metadata(item_id, metadata)
            
            # Notify WebSocket clients about metadata update
            if success:
                try:
                    _notify_metadata_updated(item_id)
                except Exception:
                    logger.exception("Failed to notify metadata update")
            
            return {"success": success, "metadata": metadata}
            
        except Exception as e:
            logger.exception(f"Unhandled error in fetch_video_metadata_task for {item_id}")
            raise self.retry(exc=e, countdown=60)

    @celery_app.task(name='tasks.fetch_playlist_metadata')
    def fetch_playlist_metadata_task(playlist_url: str, channel_id: Optional[str] = None):
        """
        Celery task: извлекает все видео из YouTube плейлиста и добавляет их в очередь.
        """
        logger.info(f"[worker] fetch_playlist_metadata_task for {playlist_url}")
        
        metadata = extract_video_metadata(playlist_url)
        
        if metadata.get("error"):
            return {"success": False, "error": metadata["error"]}
        
        if not metadata.get("is_playlist"):
            return {"success": False, "error": "URL is not a playlist"}
        
        entries = metadata.get("entries", [])
        added_count = 0
        
        from database import SessionLocal
        from src.models.playlist import PlaylistItem
        
        db = SessionLocal()
        try:
            # Получаем последнюю позицию
            last_item = db.query(PlaylistItem).order_by(PlaylistItem.position.desc()).first()
            position = (last_item.position + 1) if last_item else 0
            
            for entry in entries:
                if not entry.get("url"):
                    continue
                    
                new_item = PlaylistItem(
                    url=entry["url"],
                    title=entry.get("title") or entry["url"],
                    type="youtube",
                    position=position,
                    duration=entry.get("duration"),
                    channel_id=channel_id,
                )
                db.add(new_item)
                position += 1
                added_count += 1
            
            db.commit()
            logger.info(f"Added {added_count} items from playlist {playlist_url}")
            
            return {
                "success": True,
                "playlist_title": metadata.get("playlist_title"),
                "added_count": added_count,
            }
            
        except Exception as e:
            logger.exception(f"Error adding playlist items")
            db.rollback()
            return {"success": False, "error": str(e)}
        finally:
            db.close()


def _notify_metadata_updated(item_id: str):
    """Уведомляет WebSocket клиентов об обновлении метаданных."""
    try:
        from api import websocket as ws_module
        from database import SessionLocal
        from src.models.playlist import PlaylistItem
        
        db = SessionLocal()
        try:
            item = db.query(PlaylistItem).filter(PlaylistItem.id == item_id).first()
            if item:
                import asyncio
                channel_id = str(item.channel_id) if item.channel_id else None
                
                # Run async notify in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(ws_module.notify_item_updated(item, channel_id))
                finally:
                    loop.close()
        finally:
            db.close()
    except ImportError:
        pass


# ============================================================================
# Public API
# ============================================================================

def fetch_metadata_async(item_id: str, url: str, audio_only: bool = False) -> bool:
    """
    Запускает асинхронное получение метаданных.
    
    Использует Celery если доступен, иначе выполняет синхронно.
    
    Args:
        item_id: UUID playlist item
        url: URL видео
        audio_only: Извлекать только аудио форматы
        
    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.fetch_video_metadata', args=[str(item_id), url, audio_only])
            logger.info(f"Enqueued metadata fetch for item {item_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")
    
    # Sync fallback
    logger.info(f"Fetching metadata synchronously for item {item_id}")
    metadata = extract_video_metadata(url, audio_only)
    return update_playlist_item_metadata(str(item_id), metadata)


def import_playlist_async(playlist_url: str, channel_id: Optional[str] = None) -> bool:
    """
    Запускает асинхронный импорт YouTube плейлиста.
    
    Args:
        playlist_url: URL YouTube плейлиста
        channel_id: Опционально - ID канала для привязки
        
    Returns:
        True если задача поставлена в очередь
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.fetch_playlist_metadata', args=[playlist_url, channel_id])
            logger.info(f"Enqueued playlist import for {playlist_url}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task")
            return False
    
    # Sync fallback (не рекомендуется для больших плейлистов)
    logger.warning("Celery not available, playlist import may be slow")
    try:
        from database import SessionLocal
        from src.models.playlist import PlaylistItem
        
        metadata = extract_video_metadata(playlist_url)
        if metadata.get("error") or not metadata.get("is_playlist"):
            return False
        
        db = SessionLocal()
        try:
            last_item = db.query(PlaylistItem).order_by(PlaylistItem.position.desc()).first()
            position = (last_item.position + 1) if last_item else 0
            
            for entry in metadata.get("entries", []):
                if not entry.get("url"):
                    continue
                new_item = PlaylistItem(
                    url=entry["url"],
                    title=entry.get("title") or entry["url"],
                    type="youtube",
                    position=position,
                    duration=entry.get("duration"),
                    channel_id=channel_id,
                )
                db.add(new_item)
                position += 1
            
            db.commit()
            return True
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to import playlist synchronously")
        return False
