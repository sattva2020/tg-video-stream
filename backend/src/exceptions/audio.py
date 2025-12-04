# -*- coding: utf-8 -*-
"""
Кастомные исключения для audio streaming сервисов.
Обеспечивает единообразную обработку ошибок.

Пример использования:
    from src.exceptions.audio import StreamNotFoundError, RateLimitExceededError
    
    if not stream:
        raise StreamNotFoundError(stream_id=stream_id)
"""

from typing import Optional


class AudioServiceError(Exception):
    """
    Базовое исключение для audio streaming сервисов.
    
    Все специфичные исключения наследуются от этого класса,
    что позволяет ловить все audio-ошибки одним except.
    """
    
    def __init__(self, message: str, code: Optional[str] = None):
        self.message = message
        self.code = code or "AUDIO_ERROR"
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Преобразует исключение в словарь для API ответа."""
        return {
            "error": self.code,
            "message": self.message,
        }


class StreamNotFoundError(AudioServiceError):
    """
    Стрим или трек не найден.
    
    Attributes:
        stream_id: ID искомого стрима
        track_id: ID искомого трека
    """
    
    def __init__(
        self, 
        stream_id: Optional[str] = None, 
        track_id: Optional[str] = None,
        message: Optional[str] = None,
    ):
        self.stream_id = stream_id
        self.track_id = track_id
        
        if message:
            msg = message
        elif stream_id:
            msg = f"Стрим не найден: {stream_id}"
        elif track_id:
            msg = f"Трек не найден: {track_id}"
        else:
            msg = "Стрим или трек не найден"
        
        super().__init__(msg, code="STREAM_NOT_FOUND")


class ChannelNotFoundError(AudioServiceError):
    """Канал не найден."""
    
    def __init__(self, channel_id: str, message: Optional[str] = None):
        self.channel_id = channel_id
        msg = message or f"Канал не найден: {channel_id}"
        super().__init__(msg, code="CHANNEL_NOT_FOUND")


class ChannelAccessDeniedError(AudioServiceError):
    """Доступ к каналу запрещён."""
    
    def __init__(self, channel_id: str, user_id: int, message: Optional[str] = None):
        self.channel_id = channel_id
        self.user_id = user_id
        msg = message or f"Доступ к каналу {channel_id} запрещён для пользователя {user_id}"
        super().__init__(msg, code="CHANNEL_ACCESS_DENIED")


class RateLimitExceededError(AudioServiceError):
    """
    Превышен лимит запросов.
    
    Attributes:
        retry_after: Секунды до возможности повторного запроса
        limit: Максимальное количество запросов
        window: Размер окна в секундах
    """
    
    def __init__(
        self, 
        retry_after: int,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        message: Optional[str] = None,
    ):
        self.retry_after = retry_after
        self.limit = limit
        self.window = window
        
        msg = message or f"Превышен лимит запросов. Повторите через {retry_after} секунд"
        super().__init__(msg, code="RATE_LIMIT_EXCEEDED")
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        result["retry_after"] = self.retry_after
        if self.limit:
            result["limit"] = self.limit
        if self.window:
            result["window"] = self.window
        return result


class PlaybackError(AudioServiceError):
    """Ошибка воспроизведения."""
    
    def __init__(self, operation: str, reason: str, message: Optional[str] = None):
        self.operation = operation
        self.reason = reason
        msg = message or f"Ошибка воспроизведения ({operation}): {reason}"
        super().__init__(msg, code="PLAYBACK_ERROR")


class SeekError(AudioServiceError):
    """Ошибка перемотки."""
    
    def __init__(
        self, 
        position: float, 
        duration: Optional[float] = None,
        message: Optional[str] = None,
    ):
        self.position = position
        self.duration = duration
        
        if message:
            msg = message
        elif duration and position > duration:
            msg = f"Позиция {position}s превышает длительность {duration}s"
        else:
            msg = f"Ошибка перемотки на позицию {position}s"
        
        super().__init__(msg, code="SEEK_ERROR")


class RadioStreamError(AudioServiceError):
    """Ошибка радио стрима."""
    
    def __init__(self, url: str, reason: str, message: Optional[str] = None):
        self.url = url
        self.reason = reason
        msg = message or f"Ошибка радио стрима ({url}): {reason}"
        super().__init__(msg, code="RADIO_STREAM_ERROR")


class QueueError(AudioServiceError):
    """Ошибка очереди воспроизведения."""
    
    def __init__(self, operation: str, reason: str, message: Optional[str] = None):
        self.operation = operation
        self.reason = reason
        msg = message or f"Ошибка очереди ({operation}): {reason}"
        super().__init__(msg, code="QUEUE_ERROR")


class QueueFullError(QueueError):
    """Очередь переполнена."""
    
    def __init__(self, max_size: int, message: Optional[str] = None):
        self.max_size = max_size
        msg = message or f"Очередь достигла максимального размера: {max_size}"
        super().__init__("add", msg, msg)
        self.code = "QUEUE_FULL"


class EqualizerError(AudioServiceError):
    """Ошибка эквалайзера."""
    
    def __init__(self, preset: Optional[str] = None, message: Optional[str] = None):
        self.preset = preset
        msg = message or f"Ошибка эквалайзера" + (f" (пресет: {preset})" if preset else "")
        super().__init__(msg, code="EQUALIZER_ERROR")


class LyricsNotFoundError(AudioServiceError):
    """Текст песни не найден."""
    
    def __init__(self, artist: str, title: str, message: Optional[str] = None):
        self.artist = artist
        self.title = title
        msg = message or f"Текст не найден для: {artist} - {title}"
        super().__init__(msg, code="LYRICS_NOT_FOUND")


class ShazamRecognitionError(AudioServiceError):
    """Ошибка распознавания Shazam."""
    
    def __init__(self, reason: str, message: Optional[str] = None):
        self.reason = reason
        msg = message or f"Ошибка распознавания: {reason}"
        super().__init__(msg, code="SHAZAM_ERROR")


class SchedulerError(AudioServiceError):
    """Ошибка планировщика."""
    
    def __init__(self, operation: str, reason: str, message: Optional[str] = None):
        self.operation = operation
        self.reason = reason
        msg = message or f"Ошибка планировщика ({operation}): {reason}"
        super().__init__(msg, code="SCHEDULER_ERROR")


class GStreamerError(AudioServiceError):
    """Ошибка GStreamer."""
    
    def __init__(self, pipeline: Optional[str] = None, message: Optional[str] = None):
        self.pipeline = pipeline
        msg = message or f"Ошибка GStreamer" + (f": {pipeline}" if pipeline else "")
        super().__init__(msg, code="GSTREAMER_ERROR")


class ConfigurationError(AudioServiceError):
    """Ошибка конфигурации."""
    
    def __init__(self, parameter: str, message: Optional[str] = None):
        self.parameter = parameter
        msg = message or f"Ошибка конфигурации: {parameter}"
        super().__init__(msg, code="CONFIGURATION_ERROR")


# =============================================================================
# Exception Handler для FastAPI
# =============================================================================

def audio_exception_handler(request, exc: AudioServiceError):
    """
    FastAPI exception handler для audio exceptions.
    
    Использование:
        from fastapi import FastAPI
        from src.exceptions.audio import AudioServiceError, audio_exception_handler
        
        app = FastAPI()
        app.add_exception_handler(AudioServiceError, audio_exception_handler)
    """
    from fastapi.responses import JSONResponse
    
    status_code = 400
    
    # Определяем HTTP код по типу ошибки
    if isinstance(exc, (StreamNotFoundError, ChannelNotFoundError, LyricsNotFoundError)):
        status_code = 404
    elif isinstance(exc, ChannelAccessDeniedError):
        status_code = 403
    elif isinstance(exc, RateLimitExceededError):
        status_code = 429
    elif isinstance(exc, ConfigurationError):
        status_code = 500
    
    return JSONResponse(
        status_code=status_code,
        content=exc.to_dict(),
    )
