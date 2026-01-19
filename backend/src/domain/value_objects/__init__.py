"""Value Objects для Domain Layer.

**Phase 8**: Clean Architecture - Value Objects
**Reference**: specs/025-clean-architecture-rules/tasks.md T074-T076
"""

from src.domain.value_objects.chat_id import ChatId
from src.domain.value_objects.duration import Duration
from src.domain.value_objects.email import Email
from src.domain.value_objects.file_path import FilePath
from src.domain.value_objects.password import Password
from src.domain.value_objects.quality import Quality, VideoQuality, AudioQuality
from src.domain.value_objects.stream_id import StreamId
from src.domain.value_objects.title import Title
from src.domain.value_objects.user_id import UserId

__all__ = [
    # IDs
    "UserId",
    "StreamId",
    "ChatId",
    # Text
    "Email",
    "Title",
    "Password",
    # Measurements
    "Duration",
    "FilePath",
    # Quality
    "Quality",
    "VideoQuality",
    "AudioQuality",
]
