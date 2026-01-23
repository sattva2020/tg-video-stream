"""
Celery tasks for processing live stream recordings.

Включает:
- Запуск и остановка записи
- Пост-обработка (транскодинг, создание превью)
- Очистка старых записей
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


def _process_recording_file(file_path: str, format: str) -> dict:
    """
    Обрабатывает файл записи после окончания стрима.

    Args:
        file_path: Путь к файлу записи
        format: Формат записи (mp4, webm, etc.)

    Returns:
        dict с метаданными: duration, file_size, thumbnail_url, preview_url
    """
    from pathlib import Path

    result = {
        "success": False,
        "duration": None,
        "file_size": None,
        "thumbnail_url": None,
        "preview_url": None,
        "error": None
    }

    try:
        file_path_obj = Path(file_path)

        # Check if file exists
        if not file_path_obj.exists():
            result["error"] = f"Recording file not found: {file_path}"
            return result

        # Get file size
        result["file_size"] = file_path_obj.stat().st_size

        # Get duration using ffprobe (if available)
        try:
            import subprocess
            ffprobe_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(file_path_obj)
            ]
            duration_output = subprocess.check_output(ffprobe_cmd, stderr=subprocess.DEVNULL, timeout=10)
            if duration_output:
                result["duration"] = int(float(duration_output.decode().strip()))
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError) as e:
            logger.warning(f"Failed to get duration using ffprobe: {e}")

        # Generate thumbnail (if ffmpeg available)
        try:
            import subprocess
            thumbnail_path = file_path_obj.parent / f"{file_path_obj.stem}_thumb.jpg"
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", str(file_path_obj),
                "-ss", "00:00:01",  # Thumbnail from 1 second mark
                "-vframes", "1",
                "-q:v", "2",
                str(thumbnail_path),
                "-y"  # Overwrite
            ]
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=30)

            # Return relative URL for thumbnail
            thumbnail_filename = thumbnail_path.name
            result["thumbnail_url"] = f"/recordings/{thumbnail_filename}"
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Failed to generate thumbnail: {e}")

        # TODO: Generate preview video clip (short excerpt)
        # This requires more complex ffmpeg processing

        result["success"] = True

    except Exception as e:
        logger.exception(f"Error processing recording file {file_path}")
        result["error"] = str(e)

    return result


def _update_recording_status(recording_id: str, status: str, **kwargs) -> bool:
    """
    Обновляет статус записи в БД.

    Args:
        recording_id: UUID записи
        status: Новый статус (processing, ready, error)
        **kwargs: Дополнительные поля для обновления

    Returns:
        True если успешно, False если ошибка
    """
    from database import SessionLocal
    from src.models.recording import Recording, RecordingStatus

    db = SessionLocal()
    try:
        recording = db.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            logger.warning(f"Recording {recording_id} not found")
            return False

        # Update status
        recording.status = RecordingStatus(status)

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(recording, key):
                setattr(recording, key, value)

        # Update timestamp
        recording.updated_at = datetime.utcnow()

        db.commit()
        logger.info(f"Updated recording {recording_id} status to {status}")
        return True

    except Exception as e:
        logger.exception(f"Error updating recording {recording_id}")
        db.rollback()
        return False
    finally:
        db.close()


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.start_recording', bind=True, max_retries=3)
    def start_recording_task(self, live_stream_id: str, format: str = "mp4"):
        """
        Celery task: запускает запись live stream.

        Создаёт объект Recording в БД и обновляет LiveStream.
        """
        logger.info(f"[worker] start_recording_task for live stream {live_stream_id}")

        try:
            from database import SessionLocal
            from src.services.recording_service import RecordingService
            from src.models.recording import RecordingFormat

            db = SessionLocal()
            try:
                service = RecordingService(db)

                # Convert string format to enum
                recording_format = RecordingFormat(format)

                # Start recording
                recording = service.start_recording(
                    live_stream_id=live_stream_id,
                    format=recording_format
                )

                logger.info(f"Recording {recording.id} started for live stream {live_stream_id}")
                return {
                    "success": True,
                    "recording_id": str(recording.id),
                    "file_path": recording.file_path
                }

            finally:
                db.close()

        except Exception as e:
            logger.exception(f"Error in start_recording_task for {live_stream_id}")
            raise self.retry(exc=e, countdown=10)

    @celery_app.task(name='tasks.stop_recording', bind=True, max_retries=3)
    def stop_recording_task(self, recording_id: str):
        """
        Celery task: останавливает запись и запускает пост-обработку.

        Останавливает запись, получает метаданные файла и обновляет статус.
        """
        logger.info(f"[worker] stop_recording_task for recording {recording_id}")

        try:
            from database import SessionLocal
            from src.services.recording_service import RecordingService

            db = SessionLocal()
            try:
                service = RecordingService(db)

                # Get recording details
                recording = service.get_recording(recording_id)
                if not recording:
                    logger.warning(f"Recording {recording_id} not found")
                    return {"success": False, "error": "Recording not found"}

                # Process recording file
                process_result = _process_recording_file(recording.file_path, recording.format.value)

                if not process_result["success"]:
                    # Mark as failed
                    service.mark_recording_failed(recording_id, process_result.get("error", "Processing failed"))
                    return {
                        "success": False,
                        "error": process_result.get("error"),
                        "recording_id": recording_id
                    }

                # Stop recording with metadata
                service.stop_recording(
                    recording_id=recording_id,
                    final_duration=process_result.get("duration"),
                    final_file_size=process_result.get("file_size")
                )

                # Mark as ready with file URL
                file_url = f"/recordings/{Path(recording.file_path).name}"
                service.mark_recording_ready(
                    recording_id=recording_id,
                    file_url=file_url,
                    duration=process_result.get("duration", 0),
                    file_size=process_result.get("file_size", 0),
                    thumbnail_url=process_result.get("thumbnail_url"),
                    preview_url=process_result.get("preview_url")
                )

                logger.info(f"Recording {recording_id} processed successfully")
                return {
                    "success": True,
                    "recording_id": recording_id,
                    "file_url": file_url,
                    "duration": process_result.get("duration"),
                    "file_size": process_result.get("file_size")
                }

            finally:
                db.close()

        except Exception as e:
            logger.exception(f"Error in stop_recording_task for {recording_id}")
            raise self.retry(exc=e, countdown=10)

    @celery_app.task(name='tasks.cleanup_old_recordings')
    def cleanup_old_recordings_task(days: int = 30):
        """
        Celery task: удаляет старые записи.

        Удаляет записи старше указанного количества дней.
        """
        logger.info(f"[worker] cleanup_old_recordings_task for recordings older than {days} days")

        try:
            from database import SessionLocal
            from src.services.recording_service import RecordingService

            db = SessionLocal()
            try:
                service = RecordingService(db)
                deleted_count = service.cleanup_old_recordings(days=days)

                logger.info(f"Cleaned up {deleted_count} old recordings")
                return {
                    "success": True,
                    "deleted_count": deleted_count
                }

            finally:
                db.close()

        except Exception as e:
            logger.exception("Error in cleanup_old_recordings_task")
            return {
                "success": False,
                "error": str(e)
            }


# ============================================================================
# Public API
# ============================================================================

def start_recording_async(live_stream_id: str, format: str = "mp4") -> bool:
    """
    Запускает асинхронную запись live stream.

    Использует Celery если доступен, иначе выполняет синхронно.

    Args:
        live_stream_id: UUID live stream
        format: Формат записи (mp4, webm, etc.)

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.start_recording', args=[str(live_stream_id), format])
            logger.info(f"Enqueued recording start for live stream {live_stream_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Starting recording synchronously for live stream {live_stream_id}")
    try:
        from database import SessionLocal
        from src.services.recording_service import RecordingService
        from src.models.recording import RecordingFormat

        db = SessionLocal()
        try:
            service = RecordingService(db)
            recording_format = RecordingFormat(format)
            service.start_recording(
                live_stream_id=live_stream_id,
                format=recording_format
            )
            return True
        finally:
            db.close()
    except Exception:
        logger.exception(f"Failed to start recording for {live_stream_id}")
        return False


def stop_recording_async(recording_id: str) -> bool:
    """
    Запускает асинхронную остановку записи с пост-обработкой.

    Использует Celery если доступен, иначе выполняет синхронно.

    Args:
        recording_id: UUID записи

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.stop_recording', args=[str(recording_id)])
            logger.info(f"Enqueued recording stop for {recording_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info(f"Stopping recording synchronously for {recording_id}")
    try:
        from database import SessionLocal
        from src.services.recording_service import RecordingService

        db = SessionLocal()
        try:
            service = RecordingService(db)

            # Get recording
            recording = service.get_recording(recording_id)
            if not recording:
                logger.warning(f"Recording {recording_id} not found")
                return False

            # Process file
            process_result = _process_recording_file(recording.file_path, recording.format.value)

            if process_result["success"]:
                # Stop and mark ready
                service.stop_recording(
                    recording_id=recording_id,
                    final_duration=process_result.get("duration"),
                    final_file_size=process_result.get("file_size")
                )
                file_url = f"/recordings/{Path(recording.file_path).name}"
                service.mark_recording_ready(
                    recording_id=recording_id,
                    file_url=file_url,
                    duration=process_result.get("duration", 0),
                    file_size=process_result.get("file_size", 0),
                    thumbnail_url=process_result.get("thumbnail_url")
                )
            else:
                # Mark as failed
                service.mark_recording_failed(recording_id, process_result.get("error", "Processing failed"))

            return True
        finally:
            db.close()
    except Exception:
        logger.exception(f"Failed to stop recording {recording_id}")
        return False


def schedule_cleanup_old_recordings(days: int = 30) -> bool:
    """
    Планирует очистку старых записей.

    Args:
        days: Количество дней для сохранения записей

    Returns:
        True если задача поставлена в очередь
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.cleanup_old_recordings', args=[days])
            logger.info(f"Scheduled cleanup for recordings older than {days} days")
            return True
        except Exception:
            logger.exception("Failed to enqueue cleanup task")
            return False

    logger.warning("Celery not available, cleanup not scheduled")
    return False
