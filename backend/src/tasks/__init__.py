"""
Tasks модуль для фоновых задач (Celery).

Содержит:
- fetch_metadata_async: получение метаданных видео/аудио
- import_playlist_async: импорт YouTube плейлистов
- notify_admins_async: уведомления админов
- start_recording_async: запуск записи live stream (Feature 019)
- stop_recording_async: остановка записи с пост-обработкой (Feature 019)
- schedule_cleanup_old_recordings: очистка старых записей (Feature 019)
"""

__all__ = [
    "fetch_metadata_async",
    "import_playlist_async",
    "notify_admins_async",
    "start_recording_async",
    "stop_recording_async",
    "schedule_cleanup_old_recordings",
]

# Re-export from submodules
from .media import fetch_metadata_async, import_playlist_async
from .notifications import notify_admins_async
from .recording_tasks import (
    start_recording_async,
    stop_recording_async,
    schedule_cleanup_old_recordings,
)
