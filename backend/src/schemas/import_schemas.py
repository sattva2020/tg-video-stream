"""
Pydantic schemas for content import operations.

Supports importing playlists and content from various platforms:
- YouTube playlists
- Vimeo albums/batches
- Local media libraries
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

from src.models.import_job import ImportPlatform, ImportStatus


class ImportCreateRequest(BaseModel):
    """Запрос на создание нового задания импорта контента."""
    platform: ImportPlatform = Field(
        ...,
        description="Платформа для импорта (youtube, vimeo, local)"
    )
    source_url: Optional[str] = Field(
        None,
        max_length=2000,
        description="URL источника для YouTube или Vimeo"
    )
    source_path: Optional[str] = Field(
        None,
        max_length=2000,
        description="Локальный путь к файлам или папке"
    )
    channel_id: Optional[UUID] = Field(
        None,
        description="ID канала для импорта (опционально)"
    )
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Опции импорта: {deduplicate: bool, quality: str, fetch_metadata: bool}"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "platform": "youtube",
                    "source_url": "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxx",
                    "channel_id": "123e4567-e89b-12d3-a456-426614174000",
                    "options": {"deduplicate": True, "fetch_metadata": True}
                },
                {
                    "platform": "vimeo",
                    "source_url": "https://vimeo.com/album/1234567",
                    "options": {"quality": "best"}
                },
                {
                    "platform": "local",
                    "source_path": "/path/to/music/library",
                    "options": {"deduplicate": True, "recursive": True}
                }
            ]
        }


class ImportJobResponse(BaseModel):
    """Ответ с информацией о задании импорта."""
    id: UUID
    user_id: UUID
    channel_id: Optional[UUID]
    platform: ImportPlatform
    source_url: Optional[str]
    source_path: Optional[str]
    status: ImportStatus
    total_items: Optional[int]
    processed_items: int
    successful_items: int
    failed_items: int
    skipped_items: int
    progress_percentage: int
    error_message: Optional[str]
    error_details: Optional[Dict[str, Any]]
    options: Dict[str, Any]
    metadata: Dict[str, Any]
    results: Dict[str, Any]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class ImportJobListResponse(BaseModel):
    """Ответ со списком заданий импорта."""
    items: List[ImportJobResponse]
    total: int
    page: int
    page_size: int


class ImportJobUpdate(BaseModel):
    """Запрос на обновление задания импорта (пауза/возобновление/отмена)."""
    status: ImportStatus = Field(
        ...,
        description="Новый статус (paused, in_progress, cancelled)"
    )


class ImportProgressUpdate(BaseModel):
    """Обновление прогресса импорта (используется внутренними задачами)."""
    processed_items: int = Field(..., ge=0)
    successful_items: Optional[int] = Field(None, ge=0)
    failed_items: Optional[int] = Field(None, ge=0)
    skipped_items: Optional[int] = Field(None, ge=0)
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class ImportSummaryResponse(BaseModel):
    """Сводка результатов импорта."""
    job_id: UUID
    platform: ImportPlatform
    status: ImportStatus
    total_items: int
    imported_count: int
    duplicate_count: int
    failed_count: int
    duration_seconds: Optional[int]
    errors: List[str] = Field(default_factory=list)


class ImportValidationError(BaseModel):
    """Ошибка валидации при импорте."""
    field: str
    message: str
    code: str
