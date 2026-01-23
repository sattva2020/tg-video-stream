"""
Celery tasks для транскодирования видео.

Включает:
- Транскодирование видео в форматы, совместимые с Telegram
- Конвертация кодеков (h264, h265, aac, mp3, opus)
- Коррекция ориентации видео
- Профили качества (low, medium, high, ultra)
"""
import os
import logging
from typing import Optional, Dict, Any
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


def perform_transcode(
    source_url: str,
    video_codec: str = "h264",
    audio_codec: str = "aac",
    output_format: str = "mp4",
    quality: str = "medium",
    orientation: Optional[int] = None,
    bitrate: Optional[int] = None,
    audio_bitrate: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[float] = None,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Выполняет транскодирование видео через VideoTranscoder.

    Args:
        source_url: URL исходного видео
        video_codec: Целевой видео кодек (h264, h265)
        audio_codec: Целевой аудио кодек (aac, mp3, opus)
        output_format: Выходной формат (mp4, mkv, webm)
        quality: Профиль качества (low, medium, high, ultra)
        orientation: Ориентация для коррекции (0, 90, 180, 270)
        bitrate: Переопределить битрейт видео (kbps)
        audio_bitrate: Переопределить битрейт аудио (kbps)
        width: Переопределить ширину
        height: Переопределить высоту
        fps: Целевой FPS
        output_path: Путь для сохранения выходного файла

    Returns:
        dict с результатом транскодирования:
        - success: bool
        - output_path: str or None
        - duration: float or None
        - file_size: int or None
        - error: str or None
        - metadata: dict с информацией о transcoding
    """
    try:
        from streamer.video_transcoder import VideoTranscoder, QualityProfile, VideoTranscodeRequest
    except ImportError:
        logger.error("VideoTranscoder not available")
        return {"success": False, "error": "VideoTranscoder not available"}

    try:
        # Конвертируем качество в QualityProfile enum
        quality_profile = QualityProfile.MEDIUM
        if quality == "low":
            quality_profile = QualityProfile.LOW
        elif quality == "high":
            quality_profile = QualityProfile.HIGH
        elif quality == "ultra":
            quality_profile = QualityProfile.ULTRA

        # Создаём запрос на транскодирование
        request = VideoTranscodeRequest(
            source_url=source_url,
            video_codec=video_codec,
            audio_codec=audio_codec,
            format=output_format,
            quality=quality_profile,
            orientation=orientation,
            bitrate=bitrate,
            audio_bitrate=audio_bitrate,
            width=width,
            height=height,
            fps=fps
        )

        logger.info(f"Starting transcoding: {source_url} -> {video_codec}/{audio_codec} @ {quality}")

        # Выполняем транскодирование
        import asyncio

        if output_path:
            # Транскодирование в файл
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                output_file = loop.run_until_complete(
                    VideoTranscoder.transcode_to_file(request, output_path)
                )
            finally:
                loop.close()

            if output_file is None:
                return {
                    "success": False,
                    "error": "Transcoding failed - no output file generated"
                }

            # Получаем размер файла
            file_size = None
            try:
                file_size = os.path.getsize(output_file)
            except Exception:
                pass

            return {
                "success": True,
                "output_path": output_file,
                "file_size": file_size,
                "metadata": request.to_dict()
            }
        else:
            # Транскодирование в поток (в память)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                output_data = loop.run_until_complete(
                    VideoTranscoder.transcode(request)
                )
            finally:
                loop.close()

            # Собираем данные из потока
            chunks = []
            async def collect_chunks():
                async for chunk in output_data:
                    chunks.append(chunk)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(collect_chunks())
            finally:
                loop.close()

            total_size = sum(len(chunk) for chunk in chunks)

            return {
                "success": True,
                "output_path": None,
                "stream_size": total_size,
                "chunks_count": len(chunks),
                "metadata": request.to_dict()
            }

    except Exception as e:
        logger.exception(f"Error during transcoding of {source_url}")
        return {"success": False, "error": str(e)}


def update_transcoding_result(
    transcode_id: str,
    result: Dict[str, Any],
    item_id: Optional[str] = None
) -> bool:
    """
    Обновляет результат транскодирования в БД.

    Args:
        transcode_id: UUID операции транскодирования
        result: dict с результатом от perform_transcode
        item_id: Опциональный ID playlist item для обновления

    Returns:
        True если успешно, False если ошибка
    """
    if not result.get("success"):
        logger.warning(f"Cannot update transcode {transcode_id}: {result.get('error')}")
        return False

    from database import SessionLocal

    db = SessionLocal()
    try:
        # Если указан item_id, обновляем его
        if item_id:
            from src.models.playlist import PlaylistItem
            item = db.query(PlaylistItem).filter(PlaylistItem.id == item_id).first()
            if item:
                # Обновляем путь к transcoded файлу если есть
                if result.get("output_path") and hasattr(item, 'transcoded_path'):
                    item.transcoded_path = result["output_path"]

                if hasattr(item, 'transcoded_at'):
                    item.transcoded_at = datetime.utcnow()

                db.commit()
                logger.info(f"Updated transcoding result for item {item_id}")

        db.commit()
        return True

    except Exception as e:
        logger.exception(f"Error updating transcoding result for {transcode_id}")
        db.rollback()
        return False
    finally:
        db.close()


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.transcode_video', bind=True, max_retries=3)
    def transcode_video_task(
        self,
        transcode_id: str,
        source_url: str,
        video_codec: str = "h264",
        audio_codec: str = "aac",
        output_format: str = "mp4",
        quality: str = "medium",
        orientation: Optional[int] = None,
        bitrate: Optional[int] = None,
        audio_bitrate: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        output_path: Optional[str] = None,
        item_id: Optional[str] = None
    ):
        """
        Celery task: транскодирует видео в формат, совместимый с Telegram.

        Автоматически повторяет при ошибке (до 3 раз с экспоненциальной задержкой).

        Args:
            transcode_id: UUID операции транскодирования
            source_url: URL исходного видео
            video_codec: Целевой видео кодек (h264, h265)
            audio_codec: Целевой аудио кодек (aac, mp3, opus)
            output_format: Выходной формат (mp4, mkv, webm)
            quality: Профиль качества (low, medium, high, ultra)
            orientation: Ориентация для коррекции (0, 90, 180, 270)
            bitrate: Переопределить битрейт видео (kbps)
            audio_bitrate: Переопределить битрейт аудио (kbps)
            width: Переопределить ширину
            height: Переопределить высоту
            fps: Целевой FPS
            output_path: Путь для сохранения выходного файла
            item_id: Опциональный ID playlist item для обновления

        Returns:
            dict с результатом транскодирования
        """
        logger.info(
            f"[worker] transcode_video_task for {transcode_id}, "
            f"url: {source_url}, codecs: {video_codec}/{audio_codec}"
        )

        try:
            result = perform_transcode(
                source_url=source_url,
                video_codec=video_codec,
                audio_codec=audio_codec,
                output_format=output_format,
                quality=quality,
                orientation=orientation,
                bitrate=bitrate,
                audio_bitrate=audio_bitrate,
                width=width,
                height=height,
                fps=fps,
                output_path=output_path
            )

            if result.get("error"):
                # Retry на временных ошибках
                error_msg = result["error"].lower()
                if any(err in error_msg for err in ["timeout", "network", "connection", "temporarily"]):
                    raise self.retry(countdown=60 * (self.request.retries + 1))
                logger.warning(f"Non-retryable error for {transcode_id}: {result['error']}")
                return {"success": False, "transcode_id": transcode_id, "error": result["error"]}

            # Обновляем результат в БД
            update_transcoding_result(transcode_id, result, item_id)

            # Notify WebSocket clients о завершении транскодирования
            if item_id:
                try:
                    _notify_transcoding_completed(item_id, result)
                except Exception:
                    logger.exception("Failed to notify transcoding completion")

            return {
                "success": True,
                "transcode_id": transcode_id,
                "output_path": result.get("output_path"),
                "metadata": result.get("metadata")
            }

        except Exception as e:
            logger.exception(f"Unhandled error in transcode_video_task for {transcode_id}")
            raise self.retry(exc=e, countdown=120)


def _notify_transcoding_completed(item_id: str, result: Dict[str, Any]):
    """Уведомляет WebSocket клиентов о завершении транскодирования."""
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
                    loop.run_until_complete(
                        ws_module.notify_item_updated(item, channel_id)
                    )
                finally:
                    loop.close()
        finally:
            db.close()
    except ImportError:
        pass


# ============================================================================
# Public API
# ============================================================================

def transcode_video_async(
    transcode_id: str,
    source_url: str,
    video_codec: str = "h264",
    audio_codec: str = "aac",
    output_format: str = "mp4",
    quality: str = "medium",
    orientation: Optional[int] = None,
    bitrate: Optional[int] = None,
    audio_bitrate: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[float] = None,
    output_path: Optional[str] = None,
    item_id: Optional[str] = None
) -> bool:
    """
    Запускает асинхронное транскодирование видео.

    Использует Celery если доступен, иначе выполняет синхронно.

    Args:
        transcode_id: UUID операции транскодирования
        source_url: URL исходного видео
        video_codec: Целевой видео кодек (h264, h265)
        audio_codec: Целевой аудио кодек (aac, mp3, opus)
        output_format: Выходной формат (mp4, mkv, webm)
        quality: Профиль качества (low, medium, high, ultra)
        orientation: Ориентация для коррекции (0, 90, 180, 270)
        bitrate: Переопределить битрейт видео (kbps)
        audio_bitrate: Переопределить битрейт аудио (kbps)
        width: Переопределить ширину
        height: Переопределить высоту
        fps: Целевой FPS
        output_path: Путь для сохранения выходного файла
        item_id: Опциональный ID playlist item для обновления

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task(
                'tasks.transcode_video',
                args=[
                    transcode_id,
                    source_url,
                    video_codec,
                    audio_codec,
                    output_format,
                    quality,
                    orientation,
                    bitrate,
                    audio_bitrate,
                    width,
                    height,
                    fps,
                    output_path,
                    item_id
                ]
            )
            logger.info(f"Enqueued transcoding for {transcode_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Transcoding video synchronously for {transcode_id}")
    result = perform_transcode(
        source_url=source_url,
        video_codec=video_codec,
        audio_codec=audio_codec,
        output_format=output_format,
        quality=quality,
        orientation=orientation,
        bitrate=bitrate,
        audio_bitrate=audio_bitrate,
        width=width,
        height=height,
        fps=fps,
        output_path=output_path
    )
    return update_transcoding_result(transcode_id, result, item_id)
