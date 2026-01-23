"""
Celery tasks для импорта контента из различных платформ.

Включает:
- Импорт YouTube плейлистов с прогрессом
- Импорт Vimeo альбомов с прогрессом
- Импорт локальных медиа-файлов с прогрессом
- Обновление прогресса в реальном времени
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone

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


def _update_job_progress(
    job_id: str,
    processed: int,
    successful: int = None,
    failed: int = None,
    skipped: int = None
) -> bool:
    """
    Обновляет прогресс импорта в БД.

    Args:
        job_id: UUID import job
        processed: Обработано элементов
        successful: Успешно импортировано
        failed: Не удалось импортировать
        skipped: Пропущено (дубликаты)

    Returns:
        True если успешно, False если ошибка
    """
    from database import SessionLocal
    from src.models.import_job import ImportJob

    db = SessionLocal()
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not job:
            logger.warning(f"Import job {job_id} not found")
            return False

        # Обновляем прогресс
        job.update_progress(
            processed=processed,
            successful=successful,
            failed=failed,
            skipped=skipped
        )

        db.commit()
        logger.info(f"Updated progress for job {job_id}: {job.progress_percentage}%")
        return True

    except Exception as e:
        logger.exception(f"Error updating progress for job {job_id}")
        db.rollback()
        return False
    finally:
        db.close()


def _notify_import_progress(job_id: str, progress_data: Dict[str, Any]):
    """
    Уведомляет WebSocket клиентов о прогрессе импорта.

    Args:
        job_id: UUID import job
        progress_data: Данные о прогрессе
    """
    try:
        from api import websocket as ws_module
        import asyncio

        # Run async notify in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                ws_module.broadcast_to_user(
                    event_type="import_progress",
                    data={"job_id": job_id, **progress_data}
                )
            )
        finally:
            loop.close()
    except Exception:
        logger.exception("Failed to notify import progress")


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.import_youtube_playlist', bind=True, max_retries=3)
    def import_youtube_playlist_task(
        self,
        job_id: str,
        playlist_url: str,
        channel_id: Optional[str] = None,
        options: Dict[str, Any] = None
    ):
        """
        Celery task: импортирует YouTube плейлист с отслеживанием прогресса.

        Обрабатывает каждый видео отдельно, обновляя прогресс в реальном времени.
        Автоматически повторяет при ошибке (до 3 раз с экспоненциальной задержкой).

        Args:
            job_id: UUID import job
            playlist_url: URL YouTube плейлиста
            channel_id: Опциональный ID канала для привязки
            options: Опции импорта (deduplicate, etc.)
        """
        logger.info(f"[worker] import_youtube_playlist_task for job {job_id}, url: {playlist_url}")

        from database import SessionLocal
        from src.models.import_job import ImportJob, ImportStatus
        from src.models.playlist import PlaylistItem
        from src.services.import_service import ImportService
        from src.services.deduplication_service import DeduplicationService
        from src.tasks.media import extract_video_metadata

        options = options or {}
        db = SessionLocal()

        try:
            # Получаем job из БД
            job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
            if not job:
                logger.error(f"Import job {job_id} not found")
                return {"success": False, "error": "Job not found"}

            # Помечаем как начатый
            job.mark_started()
            db.commit()

            # Извлекаем метаданные плейлиста
            metadata = extract_video_metadata(playlist_url)

            if metadata.get("error"):
                # Retry на recoverable errors
                if "timeout" in metadata["error"].lower() or "network" in metadata["error"].lower():
                    raise self.retry(countdown=30 * (self.request.retries + 1))
                job.mark_failed(metadata["error"])
                db.commit()
                logger.warning(f"Non-retryable error for job {job_id}: {metadata['error']}")
                return {"success": False, "error": metadata["error"]}

            # Проверяем, что это плейлист
            if not metadata.get("is_playlist"):
                # Одиночное видео - добавляем как один элемент
                entries = [{
                    "url": metadata.get("webpage_url") or playlist_url,
                    "title": metadata.get("title"),
                    "duration": metadata.get("duration"),
                    "thumbnail": metadata.get("thumbnail"),
                    "uploader": metadata.get("uploader"),
                }]
                job.metadata = {
                    "playlist_title": metadata.get("title", "Single Video"),
                    "extractor": metadata.get("extractor")
                }
            else:
                entries = metadata.get("entries", [])
                job.metadata = {
                    "playlist_title": metadata.get("playlist_title"),
                    "playlist_id": metadata.get("playlist_id"),
                    "extractor": metadata.get("extractor")
                }

            job.total_items = len(entries)
            db.commit()

            # Инициализируем сервисы
            import_service = ImportService()
            dedup_service = DeduplicationService()

            # Получаем последнюю позицию в плейлисте
            last_item = db.query(PlaylistItem).order_by(PlaylistItem.position.desc()).first()
            position = (last_item.position + 1) if last_item else 0

            # Статистика
            imported = []
            failed = []
            duplicates = []

            # Обрабатываем каждое видео
            for i, entry in enumerate(entries):
                try:
                    # Проверяем, не отменён ли job
                    db.refresh(job)
                    if job.status == ImportStatus.CANCELLED:
                        logger.info(f"Job {job_id} was cancelled")
                        return {"success": False, "cancelled": True, "imported": len(imported)}

                    # Проверяем дубликаты если включено
                    item_url = entry.get("url") or entry.get("webpage_url")
                    if not item_url:
                        logger.warning(f"Entry {i} has no URL, skipping")
                        failed.append({**entry, "error": "No URL"})
                        continue

                    if options.get("deduplicate", True):
                        is_duplicate = dedup_service.is_duplicate(
                            db,
                            item_url,
                            channel_id=str(channel_id) if channel_id else None
                        )
                        if is_duplicate:
                            logger.info(f"Duplicate detected: {item_url}")
                            duplicates.append(entry)
                            _update_job_progress(
                                job_id,
                                processed=i + 1,
                                successful=len(imported),
                                failed=len(failed),
                                skipped=len(duplicates)
                            )
                            # Notify about progress
                            _notify_import_progress(job_id, {
                                "processed": i + 1,
                                "total": len(entries),
                                "imported": len(imported),
                                "duplicates": len(duplicates),
                                "failed": len(failed)
                            })
                            continue

                    # Создаём элемент плейлиста
                    playlist_item = PlaylistItem(
                        url=item_url,
                        title=entry.get("title") or item_url,
                        duration=entry.get("duration"),
                        type="youtube",
                        position=position,
                        channel_id=channel_id,
                    )

                    # Добавляем thumbnail если есть
                    if entry.get("thumbnail") and hasattr(playlist_item, "thumbnail"):
                        playlist_item.thumbnail = entry["thumbnail"]

                    db.add(playlist_item)
                    position += 1
                    imported.append(entry)

                    # Обновляем прогресс
                    _update_job_progress(
                        job_id,
                        processed=i + 1,
                        successful=len(imported),
                        failed=len(failed),
                        skipped=len(duplicates)
                    )

                    # Notify about progress
                    _notify_import_progress(job_id, {
                        "processed": i + 1,
                        "total": len(entries),
                        "imported": len(imported),
                        "duplicates": len(duplicates),
                        "failed": len(failed),
                        "current_item": entry.get("title")
                    })

                    # Commit every N items to avoid huge transactions
                    if (i + 1) % 10 == 0:
                        db.commit()

                except Exception as e:
                    logger.warning(f"Failed to import entry {i}: {e}")
                    failed.append({**entry, "error": str(e)})

            # Финальный commit
            db.commit()

            # Сохраняем результаты
            job.results = {
                "imported": imported,
                "duplicates": duplicates,
                "failed": failed,
                "summary": {
                    "total": len(entries),
                    "imported": len(imported),
                    "duplicates": len(duplicates),
                    "failed": len(failed)
                }
            }

            # Помечаем как завершённый
            job.mark_completed()
            db.commit()

            logger.info(f"Import job {job_id} completed: "
                       f"{len(imported)} imported, {len(duplicates)} duplicates, "
                       f"{len(failed)} failed")

            # Notify about completion
            _notify_import_progress(job_id, {
                "status": "completed",
                "imported": len(imported),
                "duplicates": len(duplicates),
                "failed": len(failed)
            })

            return {
                "success": True,
                "imported": len(imported),
                "duplicates": len(duplicates),
                "failed": len(failed)
            }

        except Exception as e:
            logger.exception(f"Unhandled error in import_youtube_playlist_task for {job_id}")
            try:
                job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
                if job:
                    job.mark_failed(str(e))
                    db.commit()
            except Exception:
                pass
            raise self.retry(exc=e, countdown=60)
        finally:
            db.close()


    @celery_app.task(name='tasks.import_vimeo_album', bind=True, max_retries=3)
    def import_vimeo_album_task(
        self,
        job_id: str,
        album_url: str,
        channel_id: Optional[str] = None,
        options: Dict[str, Any] = None
    ):
        """
        Celery task: импортирует Vimeo альбом/batch с отслеживанием прогресса.

        Работает аналогично YouTube импорту, но для Vimeo контента.

        Args:
            job_id: UUID import job
            album_url: URL Vimeo альбома
            channel_id: Опциональный ID канала для привязки
            options: Опции импорта (deduplicate, etc.)
        """
        logger.info(f"[worker] import_vimeo_album_task for job {job_id}, url: {album_url}")

        from database import SessionLocal
        from src.models.import_job import ImportJob, ImportStatus
        from src.models.playlist import PlaylistItem
        from src.services.deduplication_service import DeduplicationService
        from src.tasks.media import extract_video_metadata

        options = options or {}
        db = SessionLocal()

        try:
            # Получаем job из БД
            job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
            if not job:
                logger.error(f"Import job {job_id} not found")
                return {"success": False, "error": "Job not found"}

            # Помечаем как начатый
            job.mark_started()
            db.commit()

            # Извлекаем метаданные альбома
            metadata = extract_video_metadata(album_url)

            if metadata.get("error"):
                # Retry на recoverable errors
                if "timeout" in metadata["error"].lower() or "network" in metadata["error"].lower():
                    raise self.retry(countdown=30 * (self.request.retries + 1))
                job.mark_failed(metadata["error"])
                db.commit()
                return {"success": False, "error": metadata["error"]}

            # Проверяем, что это плейлист
            if not metadata.get("is_playlist"):
                # Одиночное видео
                entries = [{
                    "url": metadata.get("webpage_url") or album_url,
                    "title": metadata.get("title"),
                    "duration": metadata.get("duration"),
                    "thumbnail": metadata.get("thumbnail"),
                    "uploader": metadata.get("uploader"),
                }]
                job.metadata = {
                    "album_title": metadata.get("title", "Single Video"),
                    "extractor": metadata.get("extractor")
                }
            else:
                entries = metadata.get("entries", [])
                job.metadata = {
                    "album_title": metadata.get("playlist_title"),
                    "album_id": metadata.get("playlist_id"),
                    "extractor": metadata.get("extractor")
                }

            job.total_items = len(entries)
            db.commit()

            # Инициализируем сервисы
            dedup_service = DeduplicationService()

            # Получаем последнюю позицию в плейлисте
            last_item = db.query(PlaylistItem).order_by(PlaylistItem.position.desc()).first()
            position = (last_item.position + 1) if last_item else 0

            # Статистика
            imported = []
            failed = []
            duplicates = []

            # Обрабатываем каждое видео
            for i, entry in enumerate(entries):
                try:
                    # Проверяем, не отменён ли job
                    db.refresh(job)
                    if job.status == ImportStatus.CANCELLED:
                        logger.info(f"Job {job_id} was cancelled")
                        return {"success": False, "cancelled": True, "imported": len(imported)}

                    # Проверяем дубликаты если включено
                    item_url = entry.get("url") or entry.get("webpage_url")
                    if not item_url:
                        logger.warning(f"Entry {i} has no URL, skipping")
                        failed.append({**entry, "error": "No URL"})
                        continue

                    if options.get("deduplicate", True):
                        is_duplicate = dedup_service.is_duplicate(
                            db,
                            item_url,
                            channel_id=str(channel_id) if channel_id else None
                        )
                        if is_duplicate:
                            logger.info(f"Duplicate detected: {item_url}")
                            duplicates.append(entry)
                            _update_job_progress(
                                job_id,
                                processed=i + 1,
                                successful=len(imported),
                                failed=len(failed),
                                skipped=len(duplicates)
                            )
                            # Notify about progress
                            _notify_import_progress(job_id, {
                                "processed": i + 1,
                                "total": len(entries),
                                "imported": len(imported),
                                "duplicates": len(duplicates),
                                "failed": len(failed)
                            })
                            continue

                    # Создаём элемент плейлиста
                    playlist_item = PlaylistItem(
                        url=item_url,
                        title=entry.get("title") or item_url,
                        duration=entry.get("duration"),
                        type="vimeo",
                        position=position,
                        channel_id=channel_id,
                    )

                    # Добавляем thumbnail если есть
                    if entry.get("thumbnail") and hasattr(playlist_item, "thumbnail"):
                        playlist_item.thumbnail = entry["thumbnail"]

                    db.add(playlist_item)
                    position += 1
                    imported.append(entry)

                    # Обновляем прогресс
                    _update_job_progress(
                        job_id,
                        processed=i + 1,
                        successful=len(imported),
                        failed=len(failed),
                        skipped=len(duplicates)
                    )

                    # Notify about progress
                    _notify_import_progress(job_id, {
                        "processed": i + 1,
                        "total": len(entries),
                        "imported": len(imported),
                        "duplicates": len(duplicates),
                        "failed": len(failed),
                        "current_item": entry.get("title")
                    })

                    # Commit every N items
                    if (i + 1) % 10 == 0:
                        db.commit()

                except Exception as e:
                    logger.warning(f"Failed to import entry {i}: {e}")
                    failed.append({**entry, "error": str(e)})

            # Финальный commit
            db.commit()

            # Сохраняем результаты
            job.results = {
                "imported": imported,
                "duplicates": duplicates,
                "failed": failed,
                "summary": {
                    "total": len(entries),
                    "imported": len(imported),
                    "duplicates": len(duplicates),
                    "failed": len(failed)
                }
            }

            # Помечаем как завершённый
            job.mark_completed()
            db.commit()

            logger.info(f"Vimeo import job {job_id} completed: "
                       f"{len(imported)} imported, {len(duplicates)} duplicates, "
                       f"{len(failed)} failed")

            # Notify about completion
            _notify_import_progress(job_id, {
                "status": "completed",
                "imported": len(imported),
                "duplicates": len(duplicates),
                "failed": len(failed)
            })

            return {
                "success": True,
                "imported": len(imported),
                "duplicates": len(duplicates),
                "failed": len(failed)
            }

        except Exception as e:
            logger.exception(f"Unhandled error in import_vimeo_album_task for {job_id}")
            try:
                job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
                if job:
                    job.mark_failed(str(e))
                    db.commit()
            except Exception:
                pass
            raise self.retry(exc=e, countdown=60)
        finally:
            db.close()


    @celery_app.task(name='tasks.import_local_library', bind=True, max_retries=2)
    def import_local_library_task(
        self,
        job_id: str,
        source_path: str,
        channel_id: Optional[str] = None,
        options: Dict[str, Any] = None
    ):
        """
        Celery task: импортирует локальные медиа-файлы с отслеживанием прогресса.

        Сканирует директорию и импортирует найденные медиа-файлы.
        Использует media_scanner для извлечения метаданных из аудиофайлов.

        Args:
            job_id: UUID import job
            source_path: Путь к файлу или директории (относительный от MUSIC_ROOT)
            channel_id: Опциональный ID канала для привязки
            options: Опции импорта (recursive, deduplicate)
        """
        logger.info(f"[worker] import_local_library_task for job {job_id}, path: {source_path}")

        from database import SessionLocal
        from src.models.import_job import ImportJob, ImportStatus
        from src.models.playlist import PlaylistItem
        from src.services.deduplication_service import DeduplicationService
        from src.services.media_scanner import scan_folder, get_file_metadata
        from pathlib import Path

        options = options or {}
        db = SessionLocal()

        try:
            # Получаем job из БД
            job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
            if not job:
                logger.error(f"Import job {job_id} not found")
                return {"success": False, "error": "Job not found"}

            # Помечаем как начатый
            job.mark_started()
            db.commit()

            # Опции сканирования
            recursive = options.get("recursive", True)

            # Используем media_scanner для сканирования папки
            try:
                media_files = scan_folder(source_path, recursive=recursive)
            except FileNotFoundError as e:
                job.mark_failed(str(e))
                db.commit()
                return {"success": False, "error": str(e)}
            except (ValueError, PermissionError) as e:
                job.mark_failed(str(e))
                db.commit()
                return {"success": False, "error": str(e)}

            if not media_files:
                job.mark_failed("No media files found in specified path")
                db.commit()
                return {"success": False, "error": "No media files found"}

            # Подготавливаем элементы для импорта
            items = []
            total_size = 0
            total_duration = 0

            for media_file in media_files:
                items.append({
                    "url": media_file.path,
                    "title": media_file.title,
                    "artist": media_file.artist,
                    "album": media_file.album,
                    "duration": media_file.duration,
                    "type": "local",
                    "file_size": media_file.size,
                    "mime_type": media_file.mime_type
                })
                total_size += media_file.size
                total_duration += media_file.duration

            # Обновляем метаданные job
            job.metadata = {
                "source_path": source_path,
                "recursive": recursive,
                "total_size_bytes": total_size,
                "total_duration": total_duration,
                "file_count": len(items)
            }
            job.total_items = len(items)
            db.commit()

            # Инициализируем сервисы
            dedup_service = DeduplicationService()

            # Получаем последнюю позицию в плейлисте
            last_item = db.query(PlaylistItem).order_by(PlaylistItem.position.desc()).first()
            position = (last_item.position + 1) if last_item else 0

            # Статистика
            imported = []
            failed = []
            duplicates = []

            # Обрабатываем каждый файл
            for i, item in enumerate(items):
                try:
                    # Проверяем, не отменён ли job
                    db.refresh(job)
                    if job.status == ImportStatus.CANCELLED:
                        logger.info(f"Job {job_id} was cancelled")
                        return {"success": False, "cancelled": True, "imported": len(imported)}

                    item_url = item["url"]

                    # Проверяем дубликаты если включено
                    if options.get("deduplicate", True):
                        is_duplicate = dedup_service.is_duplicate(
                            db,
                            item_url,
                            channel_id=str(channel_id) if channel_id else None
                        )
                        if is_duplicate:
                            logger.info(f"Duplicate detected: {item_url}")
                            duplicates.append(item)
                            _update_job_progress(
                                job_id,
                                processed=i + 1,
                                successful=len(imported),
                                failed=len(failed),
                                skipped=len(duplicates)
                            )
                            # Notify about progress
                            _notify_import_progress(job_id, {
                                "processed": i + 1,
                                "total": len(items),
                                "imported": len(imported),
                                "duplicates": len(duplicates),
                                "failed": len(failed)
                            })
                            continue

                    # Создаём элемент плейлиста с метаданными
                    playlist_item = PlaylistItem(
                        url=item_url,
                        title=item.get("title"),
                        duration=item.get("duration"),
                        type="local",
                        position=position,
                        channel_id=channel_id,
                    )

                    # Добавляем дополнительные метаданные если модель поддерживает
                    if hasattr(playlist_item, "artist") and item.get("artist"):
                        playlist_item.artist = item["artist"]
                    if hasattr(playlist_item, "album") and item.get("album"):
                        playlist_item.album = item["album"]

                    db.add(playlist_item)
                    position += 1
                    imported.append(item)

                    # Обновляем прогресс
                    _update_job_progress(
                        job_id,
                        processed=i + 1,
                        successful=len(imported),
                        failed=len(failed),
                        skipped=len(duplicates)
                    )

                    # Notify about progress
                    _notify_import_progress(job_id, {
                        "processed": i + 1,
                        "total": len(items),
                        "imported": len(imported),
                        "duplicates": len(duplicates),
                        "failed": len(failed),
                        "current_item": item.get("title")
                    })

                    # Commit every N items
                    if (i + 1) % 20 == 0:
                        db.commit()

                except Exception as e:
                    logger.warning(f"Failed to import file {item.get('url')}: {e}")
                    failed.append({**item, "error": str(e)})

            # Финальный commit
            db.commit()

            # Сохраняем результаты
            job.results = {
                "imported": imported,
                "duplicates": duplicates,
                "failed": failed,
                "summary": {
                    "total": len(items),
                    "imported": len(imported),
                    "duplicates": len(duplicates),
                    "failed": len(failed),
                    "total_duration": total_duration,
                    "total_size": total_size
                }
            }

            # Помечаем как завершённый
            job.mark_completed()
            db.commit()

            logger.info(f"Local import job {job_id} completed: "
                       f"{len(imported)} imported, {len(duplicates)} duplicates, "
                       f"{len(failed)} failed, {total_duration}s total duration")

            # Notify about completion
            _notify_import_progress(job_id, {
                "status": "completed",
                "imported": len(imported),
                "duplicates": len(duplicates),
                "failed": len(failed),
                "total_duration": total_duration
            })

            return {
                "success": True,
                "imported": len(imported),
                "duplicates": len(duplicates),
                "failed": len(failed)
            }

        except Exception as e:
            logger.exception(f"Unhandled error in import_local_library_task for {job_id}")
            try:
                job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
                if job:
                    job.mark_failed(str(e))
                    db.commit()
            except Exception:
                pass
            raise self.retry(exc=e, countdown=60)
        finally:
            db.close()


# ============================================================================
# Public API
# ============================================================================

def import_youtube_playlist_async(
    job_id: str,
    playlist_url: str,
    channel_id: Optional[str] = None,
    options: Dict[str, Any] = None
) -> bool:
    """
    Запускает асинхронный импорт YouTube плейлиста.

    Args:
        job_id: UUID import job
        playlist_url: URL YouTube плейлиста
        channel_id: Опциональный ID канала
        options: Опции импорта

    Returns:
        True если задача поставлена в очередь
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task(
                'tasks.import_youtube_playlist',
                args=[job_id, playlist_url, channel_id, options or {}]
            )
            logger.info(f"Enqueued YouTube playlist import for job {job_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task")
            return False

    logger.warning("Celery not available, cannot import asynchronously")
    return False


def import_vimeo_album_async(
    job_id: str,
    album_url: str,
    channel_id: Optional[str] = None,
    options: Dict[str, Any] = None
) -> bool:
    """
    Запускает асинхронный импорт Vimeo альбома.

    Args:
        job_id: UUID import job
        album_url: URL Vimeo альбома
        channel_id: Опциональный ID канала
        options: Опции импорта

    Returns:
        True если задача поставлена в очередь
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task(
                'tasks.import_vimeo_album',
                args=[job_id, album_url, channel_id, options or {}]
            )
            logger.info(f"Enqueued Vimeo album import for job {job_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task")
            return False

    logger.warning("Celery not available, cannot import asynchronously")
    return False


def import_local_library_async(
    job_id: str,
    source_path: str,
    channel_id: Optional[str] = None,
    options: Dict[str, Any] = None
) -> bool:
    """
    Запускает асинхронный импорт локальных файлов.

    Args:
        job_id: UUID import job
        source_path: Путь к файлу или директории
        channel_id: Опциональный ID канала
        options: Опции импорта (recursive, file_types)

    Returns:
        True если задача поставлена в очередь
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task(
                'tasks.import_local_library',
                args=[job_id, source_path, channel_id, options or {}]
            )
            logger.info(f"Enqueued local library import for job {job_id}")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task")
            return False

    logger.warning("Celery not available, cannot import asynchronously")
    return False
