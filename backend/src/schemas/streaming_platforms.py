"""
Streaming platforms and broadcasting API schemas
Feature: 021-social-media-integration-cross-platform-broadcasting
"""
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# === Types ===

PlatformType = Literal["youtube", "twitch", "twitter", "discord", "custom_rtmp"]
PlatformStatus = Literal["inactive", "active", "error"]
DestinationStatus = Literal["idle", "streaming", "error"]
PostType = Literal["stream_start", "stream_end", "custom"]
PostStatus = Literal["pending", "posted", "failed", "cancelled"]


# === Streaming Platform Schemas ===

class StreamingPlatformBase(BaseModel):
    """Базовые поля платформы стриминга."""
    platform_type: PlatformType = Field(..., description="Тип платформы")
    platform_name: str = Field(..., min_length=1, max_length=255, description="Название платформы")


class StreamingPlatformCreate(StreamingPlatformBase):
    """Схема для создания платформы стриминга."""
    stream_key: Optional[str] = Field(None, max_length=500, description="Ключ стрима")
    stream_url: Optional[str] = Field(None, max_length=500, description="RTMP URL или кастомный URL")
    encrypted_credentials: Optional[str] = Field(None, description="Зашифрованные учетные данные")


class StreamingPlatformUpdate(BaseModel):
    """Схема для обновления платформы стриминга."""
    platform_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Название платформы")
    stream_key: Optional[str] = Field(None, max_length=500, description="Ключ стрима")
    stream_url: Optional[str] = Field(None, max_length=500, description="RTMP URL или кастомный URL")
    encrypted_credentials: Optional[str] = Field(None, description="Зашифрованные учетные данные")
    status: Optional[PlatformStatus] = Field(None, description="Статус платформы")


class StreamingPlatformResponse(StreamingPlatformBase):
    """Ответ с информацией о платформе стриминга."""
    id: str = Field(..., description="ID платформы")
    user_id: str = Field(..., description="ID пользователя")
    status: PlatformStatus = Field(..., description="Статус платформы")
    last_error: Optional[str] = Field(None, description="Последняя ошибка")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: Optional[datetime] = Field(None, description="Время обновления")

    class Config:
        from_attributes = True


class StreamingPlatformListResponse(BaseModel):
    """Список платформ стриминга пользователя."""
    platforms: List[StreamingPlatformResponse] = Field(default_factory=list, description="Список платформ")
    total: int = Field(..., description="Общее количество")


# === Broadcast Destination Schemas ===

class BroadcastDestinationBase(BaseModel):
    """Базовые параметры назначения трансляции."""
    channel_id: str = Field(..., description="ID канала")
    platform_id: str = Field(..., description="ID платформы")


class BroadcastDestinationCreate(BroadcastDestinationBase):
    """Схема для создания назначения трансляции."""
    enabled: bool = Field(True, description="Включено ли назначение")
    platform_settings: Optional[dict] = Field(None, description="Настройки платформы (JSON)")
    custom_title: Optional[str] = Field(None, max_length=255, description="Кастомный заголовок")
    custom_description: Optional[str] = Field(None, description="Кастомное описание")


class BroadcastDestinationUpdate(BaseModel):
    """Схема для обновления назначения трансляции."""
    enabled: Optional[bool] = Field(None, description="Включено ли назначение")
    platform_settings: Optional[dict] = Field(None, description="Настройки платформы (JSON)")
    custom_title: Optional[str] = Field(None, max_length=255, description="Кастомный заголовок")
    custom_description: Optional[str] = Field(None, description="Кастомное описание")


class BroadcastDestinationResponse(BroadcastDestinationBase):
    """Ответ с информацией о назначении трансляции."""
    id: str = Field(..., description="ID назначения")
    enabled: bool = Field(..., description="Включено ли назначение")
    status: DestinationStatus = Field(..., description="Статус трансляции")
    last_error: Optional[str] = Field(None, description="Последняя ошибка")
    platform_settings: Optional[dict] = Field(None, description="Настройки платформы")
    custom_title: Optional[str] = Field(None, description="Кастомный заголовок")
    custom_description: Optional[str] = Field(None, description="Кастомное описание")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: Optional[datetime] = Field(None, description="Время обновления")

    class Config:
        from_attributes = True


class BroadcastDestinationListResponse(BaseModel):
    """Список назначений трансляции для канала."""
    destinations: List[BroadcastDestinationResponse] = Field(default_factory=list, description="Список назначений")
    total: int = Field(..., description="Общее количество")


# === Social Media Post Schemas ===

class SocialMediaPostBase(BaseModel):
    """Базовые поля поста в соцсетях."""
    channel_id: str = Field(..., description="ID канала")
    platform_id: str = Field(..., description="ID платформы")


class SocialMediaPostCreate(SocialMediaPostBase):
    """Схема для создания поста."""
    post_type: PostType = Field(..., description="Тип поста")
    content: Optional[str] = Field(None, description="Содержимое поста")


class SocialMediaPostResponse(SocialMediaPostBase):
    """Ответ с информацией о посте."""
    id: str = Field(..., description="ID поста")
    post_type: PostType = Field(..., description="Тип поста")
    status: PostStatus = Field(..., description="Статус поста")
    content: Optional[str] = Field(None, description="Содержимое поста")
    platform_post_id: Optional[str] = Field(None, description="ID поста на платформе")
    platform_post_url: Optional[str] = Field(None, description="URL поста на платформе")
    error_message: Optional[str] = Field(None, description="Сообщение об ошибке")
    retry_count: int = Field(..., ge=0, description="Количество попыток повтора")
    posted_at: Optional[datetime] = Field(None, description="Время публикации")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: Optional[datetime] = Field(None, description="Время обновления")

    class Config:
        from_attributes = True


class SocialMediaPostListResponse(BaseModel):
    """Список постов в соцсетях."""
    posts: List[SocialMediaPostResponse] = Field(default_factory=list, description="Список постов")
    total: int = Field(..., description="Общее количество")


# === Chat Message Schemas ===

class ChatMessageBase(BaseModel):
    """Базовые поля сообщения чата."""
    platform_id: str = Field(..., description="ID платформы")
    channel_id: str = Field(..., description="ID канала")
    platform_message_id: str = Field(..., description="ID сообщения на платформе")


class ChatMessageCreate(ChatMessageBase):
    """Схема для создания сообщения чата (внутреннее использование)."""
    author_name: str = Field(..., max_length=255, description="Имя автора")
    author_display_name: Optional[str] = Field(None, max_length=255, description="Отображаемое имя автора")
    content: str = Field(..., description="Текст сообщения")
    message_timestamp: datetime = Field(..., description="Время отправки сообщения")
    author_color: Optional[str] = Field(None, max_length=7, description="Цвет автора (hex)")
    metadata: Optional[dict] = Field(None, description="Дополнительные данные (JSON)")


class ChatMessageResponse(ChatMessageBase):
    """Ответ с информацией о сообщении чата."""
    id: str = Field(..., description="ID сообщения")
    author_name: str = Field(..., description="Имя автора")
    author_display_name: Optional[str] = Field(None, description="Отображаемое имя автора")
    content: str = Field(..., description="Текст сообщения")
    message_timestamp: datetime = Field(..., description="Время отправки сообщения")
    author_color: Optional[str] = Field(None, description="Цвет автора (hex)")
    metadata: Optional[dict] = Field(None, description="Дополнительные данные")
    created_at: datetime = Field(..., description="Время создания записи")

    class Config:
        from_attributes = True


class ChatMessageListResponse(BaseModel):
    """Список сообщений чата."""
    messages: List[ChatMessageResponse] = Field(default_factory=list, description="Список сообщений")
    total: int = Field(..., description="Общее количество")


class ChatMessageAggregatedResponse(BaseModel):
    """Агрегированные сообщения чата с разных платформ."""
    channel_id: str = Field(..., description="ID канала")
    messages: List[ChatMessageResponse] = Field(default_factory=list, description="Сообщения с всех платформ")
    platforms: List[str] = Field(default_factory=list, description="Список платформ с сообщениями")
    total: int = Field(..., description="Общее количество сообщений")
