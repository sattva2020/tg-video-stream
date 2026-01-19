"""
Stream Controller

FRAMEWORKS LAYER
Dependencies: Application Layer (DTOs, Use Cases)

Endpoints для управления потоками вещания.
Использует Clean Architecture DTOs для request/response.

Endpoints:
- POST /api/v1/streams - создание потока
- GET /api/v1/streams/{stream_id}/status - получение статуса
- POST /api/v1/streams/{stream_id}/start - запуск потока
- POST /api/v1/streams/{stream_id}/stop - остановка потока
- POST /api/v1/streams/{stream_id}/skip - пропуск трека
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from src.application.dtos.stream import (
    CreateStreamRequest,
    CreateStreamResponse,
    GetStreamStatusRequest,
    GetStreamStatusResponse,
)
from src.domain.errors import DomainError

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/streams", tags=["Streams"])


# ========================
# Request/Response Models для FastAPI (Pydantic)
# ========================

from pydantic import BaseModel, Field


class CreateStreamRequestSchema(BaseModel):
    """Pydantic schema для создания потока."""
    
    chat_id: int | str = Field(..., description="ID Telegram чата для вещания")
    title: str = Field(..., min_length=1, max_length=100, description="Название потока")
    track_ids: list[int] | None = Field(None, description="Список ID треков для плейлиста")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chat_id": -1001234567890,
                "title": "Вечерний эфир",
                "track_ids": [1, 2, 3]
            }
        }


class StreamStatusResponseSchema(BaseModel):
    """Pydantic schema для статуса потока."""
    
    stream_id: int
    status: str
    current_track_index: int
    title: str
    owner_id: int
    chat_id: int | str
    started_at: datetime | None = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "stream_id": 1,
                "status": "ACTIVE",
                "current_track_index": 2,
                "title": "Вечерний эфир",
                "owner_id": 123,
                "chat_id": -1001234567890,
                "started_at": "2024-01-15T20:00:00Z"
            }
        }


class StreamCreatedResponseSchema(BaseModel):
    """Pydantic schema для ответа на создание потока."""
    
    stream_id: int
    owner_id: int
    chat_id: int | str
    title: str
    status: str
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "stream_id": 1,
                "owner_id": 123,
                "chat_id": -1001234567890,
                "title": "Вечерний эфир",
                "status": "IDLE",
                "created_at": "2024-01-15T19:30:00Z"
            }
        }


class StreamActionResponseSchema(BaseModel):
    """Pydantic schema для ответа на действия с потоком."""
    
    stream_id: int
    action: str
    status: str
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "stream_id": 1,
                "action": "start",
                "status": "ACTIVE",
                "message": "Поток успешно запущен"
            }
        }


# ========================
# Endpoints
# ========================

@router.post(
    "",
    response_model=StreamCreatedResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новый поток вещания",
    description="Создаёт новый поток вещания для указанного Telegram чата"
)
async def create_stream(
    request: CreateStreamRequestSchema,
    # Зависимости для DI будут добавлены позже:
    # current_user: User = Depends(get_current_user),
    # stream_use_case: CreateStreamUseCase = Depends(get_create_stream_use_case),
) -> StreamCreatedResponseSchema:
    """
    Создаёт новый поток вещания.
    
    Args:
        request: Данные для создания потока
        
    Returns:
        StreamCreatedResponseSchema: Созданный поток
        
    Raises:
        HTTPException 400: Ошибка валидации
        HTTPException 409: Поток для чата уже существует
    """
    try:
        # TODO: Получить owner_id из current_user
        owner_id = 1  # Placeholder
        
        # Преобразование Pydantic -> DTO
        dto_request = CreateStreamRequest(
            owner_id=owner_id,
            chat_id=request.chat_id,
            title=request.title,
            track_ids=request.track_ids,
        )
        
        log.info(f"Creating stream: {dto_request}")
        
        # TODO: Вызов Use Case
        # result = await stream_use_case.execute(dto_request)
        
        # Placeholder response
        now = datetime.utcnow()
        response = CreateStreamResponse(
            stream_id=1,
            owner_id=owner_id,
            chat_id=request.chat_id,
            title=request.title,
            status="IDLE",
            created_at=now,
        )
        
        return StreamCreatedResponseSchema(
            stream_id=response.stream_id,
            owner_id=response.owner_id,
            chat_id=response.chat_id,
            title=response.title,
            status=response.status,
            created_at=response.created_at,
        )
        
    except DomainError as e:
        log.warning(f"Domain error creating stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        log.error(f"Unexpected error creating stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.get(
    "/{stream_id}/status",
    response_model=StreamStatusResponseSchema,
    summary="Получить статус потока",
    description="Возвращает текущий статус указанного потока вещания"
)
async def get_stream_status(
    stream_id: int,
    # stream_use_case: GetStreamStatusUseCase = Depends(get_stream_status_use_case),
) -> StreamStatusResponseSchema:
    """
    Получает текущий статус потока.
    
    Args:
        stream_id: ID потока
        
    Returns:
        StreamStatusResponseSchema: Текущий статус
        
    Raises:
        HTTPException 404: Поток не найден
    """
    try:
        # Преобразование в DTO
        dto_request = GetStreamStatusRequest(stream_id=stream_id)
        
        log.info(f"Getting stream status: {dto_request}")
        
        # TODO: Вызов Use Case
        # result = await stream_use_case.execute(dto_request)
        
        # Placeholder response
        response = GetStreamStatusResponse(
            stream_id=stream_id,
            status="IDLE",
            current_track_index=0,
            title="Placeholder Stream",
            owner_id=1,
            chat_id=-1001234567890,
            started_at=None,
        )
        
        return StreamStatusResponseSchema(
            stream_id=response.stream_id,
            status=response.status,
            current_track_index=response.current_track_index,
            title=response.title,
            owner_id=response.owner_id,
            chat_id=response.chat_id,
            started_at=response.started_at,
        )
        
    except DomainError as e:
        log.warning(f"Domain error getting stream status: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        log.error(f"Unexpected error getting stream status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        )


@router.post(
    "/{stream_id}/start",
    response_model=StreamActionResponseSchema,
    summary="Запустить поток",
    description="Запускает вещание для указанного потока"
)
async def start_stream(
    stream_id: int,
) -> StreamActionResponseSchema:
    """
    Запускает поток вещания.
    
    Args:
        stream_id: ID потока
        
    Returns:
        StreamActionResponseSchema: Результат действия
        
    Raises:
        HTTPException 404: Поток не найден
        HTTPException 409: Поток уже запущен
    """
    log.info(f"Starting stream {stream_id}")
    
    # TODO: Вызов Use Case
    
    return StreamActionResponseSchema(
        stream_id=stream_id,
        action="start",
        status="ACTIVE",
        message="Поток успешно запущен"
    )


@router.post(
    "/{stream_id}/stop",
    response_model=StreamActionResponseSchema,
    summary="Остановить поток",
    description="Останавливает вещание для указанного потока"
)
async def stop_stream(
    stream_id: int,
) -> StreamActionResponseSchema:
    """
    Останавливает поток вещания.
    
    Args:
        stream_id: ID потока
        
    Returns:
        StreamActionResponseSchema: Результат действия
        
    Raises:
        HTTPException 404: Поток не найден
        HTTPException 409: Поток не запущен
    """
    log.info(f"Stopping stream {stream_id}")
    
    # TODO: Вызов Use Case
    
    return StreamActionResponseSchema(
        stream_id=stream_id,
        action="stop",
        status="IDLE",
        message="Поток успешно остановлен"
    )


@router.post(
    "/{stream_id}/skip",
    response_model=StreamActionResponseSchema,
    summary="Пропустить трек",
    description="Пропускает текущий трек и переходит к следующему"
)
async def skip_track(
    stream_id: int,
) -> StreamActionResponseSchema:
    """
    Пропускает текущий трек.
    
    Args:
        stream_id: ID потока
        
    Returns:
        StreamActionResponseSchema: Результат действия
        
    Raises:
        HTTPException 404: Поток не найден
        HTTPException 409: Поток не активен
    """
    log.info(f"Skipping track in stream {stream_id}")
    
    # TODO: Вызов Use Case
    
    return StreamActionResponseSchema(
        stream_id=stream_id,
        action="skip",
        status="ACTIVE",
        message="Трек пропущен, переход к следующему"
    )
