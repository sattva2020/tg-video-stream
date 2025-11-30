from fastapi import APIRouter, Depends, HTTPException, Header, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict
from src.database import get_db
from src.models.playlist import PlaylistItem
from src.models.user import User
from api.auth import get_current_user
from tasks.media import fetch_metadata_async, import_playlist_async
import uuid
import os
import asyncio

router = APIRouter()

# WebSocket notifications (imported lazily to avoid circular imports)
def _get_ws_module():
    try:
        from api import websocket as ws_module
        return ws_module
    except ImportError:
        return None

def _get_streamer_status_token():
    token = os.getenv("STREAMER_STATUS_TOKEN")
    if not token:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Streamer status updates are disabled")
    return token


def _verify_streamer_token(token: str | None):
    expected = _get_streamer_status_token()
    if token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid streamer token")

# Pydantic models
class PlaylistItemCreate(BaseModel):
    url: str
    title: Optional[str] = None
    type: str = "youtube"  # youtube, local, stream
    # Optional client-provided duration in seconds. Usually left empty; streamer can fill later.
    duration: Optional[int] = None
    # If True, fetch metadata asynchronously via Celery/yt-dlp
    fetch_metadata: bool = True

class PlaylistItemResponse(BaseModel):
    id: uuid.UUID
    url: str
    title: Optional[str]
    type: str
    position: int
    created_at: str
    # New fields
    status: str
    duration: Optional[int]

    model_config = ConfigDict(from_attributes=True)


class PlaylistItemStatusUpdate(BaseModel):
    status: Literal["playing", "queued", "error"]
    duration: Optional[int] = None


class ReorderItem(BaseModel):
    id: uuid.UUID
    position: int


class ReorderRequest(BaseModel):
    items: List[ReorderItem]

@router.get("/", response_model=List[PlaylistItemResponse])
def get_playlist(
    channel_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db)
):
    query = db.query(PlaylistItem)
    if channel_id:
        query = query.filter(PlaylistItem.channel_id == channel_id)
        
    items = query.order_by(PlaylistItem.position.asc(), PlaylistItem.created_at.asc()).all()
    # Convert datetime to string for simple response
    return [
        PlaylistItemResponse(
            id=item.id,
            url=item.url,
            title=item.title,
            type=item.type,
            position=item.position,
            created_at=item.created_at.isoformat() if item.created_at else "",
            status=item.status if hasattr(item, 'status') else 'queued',
            duration=item.duration if hasattr(item, 'duration') else None
        ) for item in items
    ]

@router.post("/", response_model=PlaylistItemResponse)
async def add_playlist_item(
    item: PlaylistItemCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Simple logic to determine position: put at the end
    last_item = db.query(PlaylistItem).order_by(PlaylistItem.position.desc()).first()
    new_position = (last_item.position + 1) if last_item else 0

    new_item = PlaylistItem(
        url=item.url,
        title=item.title or item.url, # Fallback title
        type=item.type,
        position=new_position,
        duration=item.duration,
        created_by=current_user.id
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    # Notify WebSocket clients
    ws_module = _get_ws_module()
    if ws_module:
        channel_id = str(new_item.channel_id) if new_item.channel_id else None
        background_tasks.add_task(ws_module.notify_item_added, new_item, channel_id)
    
    # Fetch metadata asynchronously if requested and type is youtube
    if item.fetch_metadata and item.type == "youtube":
        background_tasks.add_task(
            fetch_metadata_async, 
            str(new_item.id), 
            new_item.url, 
            False  # audio_only
        )
    
    return PlaylistItemResponse(
        id=new_item.id,
        url=new_item.url,
        title=new_item.title,
        type=new_item.type,
        position=new_item.position,
        created_at=new_item.created_at.isoformat() if new_item.created_at else "",
        status=new_item.status if hasattr(new_item, 'status') else 'queued',
        duration=new_item.duration if hasattr(new_item, 'duration') else None
    )

@router.delete("/{item_id}")
async def delete_playlist_item(
    item_id: uuid.UUID, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    item = db.query(PlaylistItem).filter(PlaylistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    channel_id = str(item.channel_id) if item.channel_id else None
    item_id_str = str(item.id)
    
    db.delete(item)
    db.commit()
    
    # Notify WebSocket clients
    ws_module = _get_ws_module()
    if ws_module:
        background_tasks.add_task(ws_module.notify_item_removed, item_id_str, channel_id)
    
    return {"ok": True}


@router.patch("/reorder")
async def reorder_playlist(
    request: ReorderRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Изменяет порядок элементов плейлиста.
    Принимает массив {id, position} и обновляет позиции.
    """
    updated_count = 0
    
    for item_update in request.items:
        item = db.query(PlaylistItem).filter(PlaylistItem.id == item_update.id).first()
        if item:
            item.position = item_update.position
            db.add(item)
            updated_count += 1
    
    db.commit()
    
    # Notify WebSocket clients about reorder
    ws_module = _get_ws_module()
    if ws_module:
        background_tasks.add_task(ws_module.notify_playlist_reordered)
    
    return {"ok": True, "updated": updated_count}


@router.patch("/{item_id}/status")
async def update_playlist_status(
    item_id: uuid.UUID,
    payload: PlaylistItemStatusUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    streamer_token: str | None = Header(None, alias="X-Streamer-Token"),
):
    _verify_streamer_token(streamer_token)
    item = db.query(PlaylistItem).filter(PlaylistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.status = payload.status
    if payload.duration is not None:
        item.duration = payload.duration
    db.add(item)
    db.commit()
    db.refresh(item)

    # Notify WebSocket clients about status change
    ws_module = _get_ws_module()
    if ws_module:
        channel_id = str(item.channel_id) if item.channel_id else None
        background_tasks.add_task(ws_module.notify_item_updated, item, channel_id)

    return {
        "ok": True,
        "status": item.status,
        "duration": item.duration,
    }


# ============================================================================
# Playlist Import
# ============================================================================

class PlaylistImportRequest(BaseModel):
    """Запрос на импорт YouTube плейлиста."""
    url: str
    channel_id: Optional[uuid.UUID] = None


class PlaylistImportResponse(BaseModel):
    """Ответ на запрос импорта плейлиста."""
    success: bool
    message: str
    queued: bool = False


@router.post("/import", response_model=PlaylistImportResponse)
async def import_youtube_playlist(
    request: PlaylistImportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Импортирует все видео из YouTube плейлиста в очередь.
    
    Работает асинхронно через Celery (если настроен) или синхронно.
    Поддерживает YouTube плейлисты и каналы.
    """
    # Валидация URL
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    # Проверяем, что это YouTube URL
    youtube_patterns = ['youtube.com', 'youtu.be', 'youtube']
    if not any(p in url.lower() for p in youtube_patterns):
        raise HTTPException(
            status_code=400, 
            detail="Only YouTube playlists are supported"
        )
    
    channel_id_str = str(request.channel_id) if request.channel_id else None
    
    # Запускаем импорт
    success = import_playlist_async(url, channel_id_str)
    
    if success:
        return PlaylistImportResponse(
            success=True,
            message="Playlist import started. Items will appear in the queue shortly.",
            queued=True
        )
    else:
        return PlaylistImportResponse(
            success=False,
            message="Failed to start playlist import. Check the URL and try again.",
            queued=False
        )


@router.post("/{item_id}/refresh-metadata")
async def refresh_item_metadata(
    item_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Принудительно обновляет метаданные playlist item через yt-dlp.
    """
    item = db.query(PlaylistItem).filter(PlaylistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.type != "youtube":
        raise HTTPException(
            status_code=400, 
            detail="Metadata refresh only supported for YouTube items"
        )
    
    # Запускаем обновление метаданных
    background_tasks.add_task(
        fetch_metadata_async,
        str(item.id),
        item.url,
        False  # audio_only
    )
    
    return {"ok": True, "message": "Metadata refresh started"}

