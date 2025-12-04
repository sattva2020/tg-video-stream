"""
Queue API Router

REST API для управления очередью воспроизведения стримов.

Endpoints:
- GET /api/v1/queue/{channel_id} - получить очередь
- POST /api/v1/queue/{channel_id}/items - добавить элемент
- DELETE /api/v1/queue/{channel_id}/items/{item_id} - удалить элемент
- PATCH /api/v1/queue/{channel_id}/items/{item_id}/move - переместить элемент
- POST /api/v1/queue/{channel_id}/skip - пропустить текущий трек
- DELETE /api/v1/queue/{channel_id} - очистить очередь
- GET /api/v1/queue/{channel_id}/state - получить состояние стрима
"""

from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from src.models.user import User
from src.api.auth.dependencies import get_current_user, require_admin
from src.models.queue import (
    QueueItem,
    QueueItemCreate,
    QueueInfo,
    QueueSource,
)
from src.models.stream_state import StreamState, StreamStatus
from src.services.queue_service import (
    QueueFullError,
    QueueEmptyError,
    ItemNotFoundError,
    InvalidPositionError,
)
from src.services.unified_queue_service import (
    UnifiedQueueService,
    get_unified_queue_service,
    QueueMode,
)
from src.services.prometheus_metrics import (
    record_queue_operation,
    record_queue_item_added,
    set_queue_size,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queue", tags=["Queue"])


# ==============================================================================
# Pydantic Schemas (API layer)
# ==============================================================================

class QueueItemCreateRequest(BaseModel):
    """Запрос на добавление элемента в очередь."""
    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=1)
    duration: Optional[int] = Field(None, ge=0)
    source: QueueSource = QueueSource.YOUTUBE
    metadata: Optional[dict] = None


class QueueItemResponse(BaseModel):
    """Ответ с данными элемента очереди."""
    id: str
    channel_id: int
    title: str
    url: str
    duration: Optional[int]
    source: str
    requested_by: Optional[int]
    added_at: str
    metadata: dict

    @classmethod
    def from_queue_item(cls, item: QueueItem) -> "QueueItemResponse":
        return cls(
            id=item.id,
            channel_id=item.channel_id,
            title=item.title,
            url=item.url,
            duration=item.duration,
            source=item.source.value,
            requested_by=item.requested_by,
            added_at=item.added_at.isoformat(),
            metadata=item.metadata
        )


class QueueResponse(BaseModel):
    """Ответ с очередью канала."""
    items: list[QueueItemResponse]
    total: int
    is_placeholder: bool = False
    current_playing: Optional[QueueItemResponse] = None


class StreamStateResponse(BaseModel):
    """Ответ с состоянием стрима."""
    channel_id: int
    status: str
    current_item: Optional[QueueItemResponse]
    started_at: Optional[str]
    current_position: int
    listeners_count: int
    is_placeholder: bool
    auto_end_timer: Optional[dict]
    last_activity: Optional[str]


class MoveRequest(BaseModel):
    """Запрос на перемещение элемента."""
    position: int = Field(..., ge=0, description="Новая позиция (0 = первый)")


class SuccessResponse(BaseModel):
    """Успешный ответ."""
    success: bool = True
    message: str = "Операция выполнена успешно"


class SkipResponse(BaseModel):
    """Ответ на пропуск трека."""
    success: bool = True
    next_item: Optional[QueueItemResponse]
    message: str = "Трек пропущен"


class ErrorResponse(BaseModel):
    """Ответ с ошибкой."""
    error: str
    message: str
    details: Optional[dict] = None


class QueueModeRequest(BaseModel):
    """Запрос на смену режима очереди."""
    mode: str = Field(..., pattern="^(fifo|priority)$", description="Режим очереди: fifo или priority")


class QueueModeResponse(BaseModel):
    """Ответ с режимом очереди."""
    channel_id: int
    mode: str
    message: str = "Режим очереди получен"


class QueueStatsResponse(BaseModel):
    """Ответ со статистикой очереди."""
    channel_id: int
    mode: str
    total: int
    vip: int = 0
    admin: int = 0
    normal: int = 0


# ==============================================================================
# Dependencies
# ==============================================================================

def get_queue_svc() -> UnifiedQueueService:
    """Получить UnifiedQueueService."""
    return get_unified_queue_service()


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get(
    "/{channel_id}",
    response_model=QueueResponse,
    summary="Получить очередь канала",
    description="Возвращает текущую очередь воспроизведения для указанного канала"
)
async def get_queue(
    channel_id: int,
    limit: int = Query(50, ge=1, le=100, description="Максимальное количество элементов"),
    offset: int = Query(0, ge=0, description="Смещение для пагинации"),
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> QueueResponse:
    """Получить очередь канала с пагинацией."""
    queue_info = await queue_service.get_all(
        channel_id=channel_id,
        limit=limit,
        offset=offset
    )
    
    items = [QueueItemResponse.from_queue_item(item) for item in queue_info.items]
    
    return QueueResponse(
        items=items,
        total=queue_info.total_items,
        is_placeholder=False,  # TODO: получить из StreamState
        current_playing=items[0] if items else None
    )


@router.post(
    "/{channel_id}/items",
    response_model=QueueItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить элемент в очередь",
    description="Добавляет новый трек в конец очереди"
)
async def add_queue_item(
    channel_id: int,
    item_data: QueueItemCreateRequest,
    priority: bool = Query(False, description="Добавить в начало очереди (только для FIFO режима)"),
    current_user: User = Depends(get_current_user),
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> QueueItemResponse:
    """Добавить элемент в очередь."""
    item_create = QueueItemCreate(
        title=item_data.title,
        url=item_data.url,
        duration=item_data.duration,
        source=item_data.source,
        metadata=item_data.metadata
    )
    
    try:
        if priority:
            item = await queue_service.add_priority(
                channel_id=channel_id,
                item_create=item_create,
                requested_by=getattr(current_user, 'telegram_id', None)
            )
            record_queue_operation(channel_id, "priority_add")
        else:
            # Для unified service передаем и requested_by (FIFO), и user (PRIORITY)
            item = await queue_service.add(
                channel_id=channel_id,
                item_create=item_create,
                requested_by=getattr(current_user, 'telegram_id', None),
                user=current_user,  # Для PRIORITY режима
            )
            record_queue_operation(channel_id, "add")
        
        # Обновляем метрику размера очереди
        size = await queue_service.get_size(channel_id)
        set_queue_size(channel_id, size)
        
        # Записываем источник
        record_queue_item_added(channel_id, item.source.value)
        
        logger.info(
            f"User {current_user.id} added item to queue: "
            f"channel={channel_id}, item={item.id}"
        )
        
        return QueueItemResponse.from_queue_item(item)
        
    except QueueFullError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{channel_id}/items/{item_id}",
    response_model=SuccessResponse,
    summary="Удалить элемент из очереди",
    description="Удаляет указанный элемент из очереди независимо от активного режима"
)
async def remove_queue_item(
    channel_id: int,
    item_id: str,
    current_user: User = Depends(get_current_user),
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> SuccessResponse:
    """Удалить элемент из очереди."""
    try:
        await queue_service.remove(channel_id=channel_id, item_id=item_id)

        record_queue_operation(channel_id, "remove")

        # Обновляем метрику размера очереди
        size = await queue_service.get_size(channel_id)
        set_queue_size(channel_id, size)

        logger.info(
            f"User {current_user.id} removed item from queue: "
            f"channel={channel_id}, item={item_id}"
        )

        return SuccessResponse(message="Элемент удален из очереди")

    except ItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Элемент {item_id} не найден в очереди"
        )


@router.patch(
    "/{channel_id}/items/{item_id}/move",
    response_model=QueueResponse,
    summary="Переместить элемент в очереди",
    description="Доступно только в FIFO режиме; в PRIORITY режиме вернет ошибку"
)
async def move_queue_item(
    channel_id: int,
    item_id: str,
    move_data: MoveRequest,
    current_user: User = Depends(get_current_user),
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> QueueResponse:
    """Переместить элемент на новую позицию (FIFO режим)."""
    try:
        items = await queue_service.move(
            channel_id=channel_id,
            item_id=item_id,
            new_position=move_data.position
        )

        record_queue_operation(channel_id, "move")

        logger.info(
            f"User {current_user.id} moved item in queue: "
            f"channel={channel_id}, item={item_id}, position={move_data.position}"
        )

        response_items = [QueueItemResponse.from_queue_item(item) for item in items]

        return QueueResponse(
            items=response_items,
            total=len(items),
            current_playing=response_items[0] if response_items else None
        )

    except ItemNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Элемент {item_id} не найден в очереди"
        )
    except InvalidPositionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{channel_id}/skip",
    response_model=SkipResponse,
    summary="Пропустить текущий трек",
    description="Пропускает текущий трек и переходит к следующему в очереди"
)
async def skip_current_track(
    channel_id: int,
    current_user: User = Depends(get_current_user),
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> SkipResponse:
    """Пропустить текущий трек."""
    try:
        next_item = await queue_service.skip(channel_id=channel_id)
        
        record_queue_operation(channel_id, "skip")
        
        # Обновляем метрику
        size = await queue_service.get_size(channel_id)
        set_queue_size(channel_id, size)
        
        logger.info(f"User {current_user.id} skipped track: channel={channel_id}")
        
        return SkipResponse(
            success=True,
            next_item=QueueItemResponse.from_queue_item(next_item) if next_item else None,
            message="Трек пропущен" if next_item else "Очередь пуста"
        )
        
    except QueueEmptyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Очередь пуста, нечего пропускать"
        )


@router.delete(
    "/{channel_id}",
    response_model=SuccessResponse,
    summary="Очистить очередь канала",
    description="Удаляет все элементы из очереди указанного канала"
)
async def clear_queue(
    channel_id: int,
    current_user: User = Depends(require_admin),
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> SuccessResponse:
    """Очистить очередь (только для админов)."""
    count = await queue_service.clear(channel_id=channel_id)
    
    record_queue_operation(channel_id, "clear")
    set_queue_size(channel_id, 0)
    
    logger.info(
        f"Admin {current_user.id} cleared queue: "
        f"channel={channel_id}, items_removed={count}"
    )
    
    return SuccessResponse(
        message=f"Очередь очищена ({count} элементов удалено)"
    )


@router.get(
    "/{channel_id}/state",
    response_model=StreamStateResponse,
    summary="Получить состояние стрима",
    description="Возвращает текущее состояние стрима (статус, текущий трек, слушатели)"
)
async def get_stream_state(
    channel_id: int,
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> StreamStateResponse:
    """
    Получить состояние стрима.
    
    TODO: Интегрировать с StreamStateService для получения реального состояния.
    Сейчас возвращает заглушку.
    """
    # Получаем текущий элемент
    current_item = await queue_service.get_next(channel_id)
    
    # TODO: Получить реальное состояние из Redis
    # Пока возвращаем заглушку
    return StreamStateResponse(
        channel_id=channel_id,
        status=StreamStatus.STOPPED.value,
        current_item=QueueItemResponse.from_queue_item(current_item) if current_item else None,
        started_at=None,
        current_position=0,
        listeners_count=0,
        is_placeholder=False,
        auto_end_timer=None,
        last_activity=None
    )


# ==============================================================================
# WebSocket Integration (для уведомлений об изменениях очереди)
# ==============================================================================

async def notify_queue_update(channel_id: int, operation: str, item_id: Optional[str] = None):
    """
    Отправить WebSocket уведомление об изменении очереди.
    
    TODO: Интегрировать с ConnectionManager
    """
    try:
        # Lazy import to avoid circular imports
        from src.api.websocket import connection_manager
        
        message = {
            "type": "queue_update",
            "channel_id": channel_id,
            "operation": operation,
            "item_id": item_id
        }
        
        await connection_manager.broadcast_to_channel(channel_id, message)
        
    except ImportError:
        logger.debug("WebSocket module not available")
    except Exception as e:
        logger.warning(f"Failed to send queue update notification: {e}")


# ==============================================================================
# Queue Mode Management Endpoints
# ==============================================================================

@router.get(
    "/{channel_id}/mode",
    response_model=QueueModeResponse,
    summary="Получить режим очереди",
    description="Возвращает текущий режим очереди канала (fifo или priority)"
)
async def get_queue_mode(
    channel_id: int,
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> QueueModeResponse:
    """Получить текущий режим очереди."""
    mode = queue_service._get_mode(channel_id)
    
    return QueueModeResponse(
        channel_id=channel_id,
        mode=mode.value,
        message=f"Текущий режим очереди: {mode.value}"
    )


@router.put(
    "/{channel_id}/mode",
    response_model=QueueModeResponse,
    summary="Установить режим очереди",
    description="Изменяет режим очереди канала. ВАЖНО: существующие элементы не мигрируются автоматически!"
)
async def set_queue_mode(
    channel_id: int,
    mode_request: QueueModeRequest,
    current_user: User = Depends(require_admin),
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> QueueModeResponse:
    """
    Установить режим очереди (только для админов).
    
    ВНИМАНИЕ: При смене режима существующая очередь НЕ мигрируется автоматически.
    Рекомендуется очистить очередь перед сменой режима или использовать 
    POST /{channel_id}/migrate для миграции.
    """
    mode = QueueMode(mode_request.mode)
    await queue_service.set_mode(channel_id, mode)
    
    logger.info(
        f"Admin {current_user.id} changed queue mode for channel {channel_id} to {mode.value}"
    )
    
    return QueueModeResponse(
        channel_id=channel_id,
        mode=mode.value,
        message=f"Режим очереди изменен на {mode.value}. "
                "Существующие элементы НЕ мигрированы автоматически!"
    )


@router.post(
    "/{channel_id}/migrate",
    response_model=SuccessResponse,
    summary="Мигрировать очередь между режимами",
    description="Переносит все элементы из одного режима очереди в другой"
)
async def migrate_queue_mode(
    channel_id: int,
    from_mode: str = Query(..., pattern="^(fifo|priority)$", description="Исходный режим"),
    to_mode: str = Query(..., pattern="^(fifo|priority)$", description="Целевой режим"),
    current_user: User = Depends(require_admin),
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> SuccessResponse:
    """
    Мигрировать очередь между режимами (только для админов).
    
    Переносит все элементы из исходного режима в целевой,
    затем очищает исходную очередь.
    """
    from_mode_enum = QueueMode(from_mode)
    to_mode_enum = QueueMode(to_mode)
    
    migrated_count = await queue_service.migrate_queue(
        channel_id=channel_id,
        from_mode=from_mode_enum,
        to_mode=to_mode_enum,
    )
    
    # Автоматически переключаем режим
    await queue_service.set_mode(channel_id, to_mode_enum)
    
    logger.info(
        f"Admin {current_user.id} migrated queue for channel {channel_id}: "
        f"{from_mode} -> {to_mode}, items={migrated_count}"
    )
    
    return SuccessResponse(
        message=f"Очередь мигрирована: {migrated_count} элементов "
                f"перенесено из {from_mode} в {to_mode}"
    )


@router.get(
    "/{channel_id}/stats",
    response_model=QueueStatsResponse,
    summary="Получить статистику очереди",
    description="Возвращает статистику распределения треков по приоритетам (для priority режима)"
)
async def get_queue_statistics(
    channel_id: int,
    queue_service: UnifiedQueueService = Depends(get_queue_svc)
) -> QueueStatsResponse:
    """
    Получить статистику очереди.
    
    Для PRIORITY режима показывает распределение по ролям (VIP/admin/normal).
    Для FIFO режима показывает только total.
    """
    stats = await queue_service.get_queue_stats(channel_id)
    mode = queue_service._get_mode(channel_id)
    
    return QueueStatsResponse(
        channel_id=channel_id,
        mode=mode.value,
        total=stats["total"],
        vip=stats.get("vip", 0),
        admin=stats.get("admin", 0),
        normal=stats.get("normal", 0),
    )

