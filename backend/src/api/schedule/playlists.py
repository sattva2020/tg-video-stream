"""
Эндпоинты для работы с плейлистами.

Включает:
- CRUD операции для Playlist
- Привязка к каналам
- Управление элементами плейлиста
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.models.schedule import ScheduleSlot, Playlist
from src.api.auth import get_current_user

from .schemas import (
    PlaylistCreate,
    PlaylistUpdate,
    PlaylistResponse,
)

router = APIRouter(tags=["schedule-playlists"])


@router.get("/playlists", response_model=List[PlaylistResponse])
async def get_playlists(
    channel_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список плейлистов."""
    query = db.query(Playlist).filter(Playlist.user_id == current_user.id)
    
    if channel_id:
        query = query.filter(
            or_(
                Playlist.channel_id == uuid.UUID(channel_id),
                Playlist.channel_id == None
            )
        )
    
    playlists = query.filter(Playlist.is_active == True).order_by(Playlist.name).all()
    
    return [
        PlaylistResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            channel_id=str(p.channel_id) if p.channel_id else None,
            color=p.color,
            source_type=p.source_type,
            source_url=p.source_url,
            items=p.items or [],
            items_count=p.items_count,
            total_duration=p.total_duration,
            is_active=p.is_active,
            is_shuffled=p.is_shuffled,
            created_at=p.created_at
        )
        for p in playlists
    ]


@router.post("/playlists", response_model=PlaylistResponse, status_code=201)
async def create_playlist(
    playlist_data: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новый плейлист."""
    # Вычисляем статистику
    items = playlist_data.items or []
    total_duration = sum(item.get("duration", 0) for item in items)
    
    playlist = Playlist(
        user_id=current_user.id,
        channel_id=uuid.UUID(playlist_data.channel_id) if playlist_data.channel_id else None,
        name=playlist_data.name,
        description=playlist_data.description,
        color=playlist_data.color,
        source_type=playlist_data.source_type,
        source_url=playlist_data.source_url,
        items=items,
        items_count=len(items),
        total_duration=total_duration,
        is_shuffled=playlist_data.is_shuffled
    )
    
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    
    return PlaylistResponse(
        id=str(playlist.id),
        name=playlist.name,
        description=playlist.description,
        channel_id=str(playlist.channel_id) if playlist.channel_id else None,
        color=playlist.color,
        source_type=playlist.source_type,
        source_url=playlist.source_url,
        items=playlist.items or [],
        items_count=playlist.items_count,
        total_duration=playlist.total_duration,
        is_active=playlist.is_active,
        is_shuffled=playlist.is_shuffled,
        created_at=playlist.created_at
    )


@router.put("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: str,
    playlist_data: PlaylistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить плейлист."""
    playlist = db.query(Playlist).filter(
        Playlist.id == uuid.UUID(playlist_id),
        Playlist.user_id == current_user.id
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    update_data = playlist_data.model_dump(exclude_unset=True)
    
    # Пересчитываем статистику при обновлении items
    if "items" in update_data:
        items = update_data["items"] or []
        update_data["items_count"] = len(items)
        update_data["total_duration"] = sum(item.get("duration", 0) for item in items)
    
    for key, value in update_data.items():
        setattr(playlist, key, value)
    
    db.commit()
    db.refresh(playlist)
    
    return PlaylistResponse(
        id=str(playlist.id),
        name=playlist.name,
        description=playlist.description,
        channel_id=str(playlist.channel_id) if playlist.channel_id else None,
        color=playlist.color,
        source_type=playlist.source_type,
        source_url=playlist.source_url,
        items=playlist.items or [],
        items_count=playlist.items_count,
        total_duration=playlist.total_duration,
        is_active=playlist.is_active,
        is_shuffled=playlist.is_shuffled,
        created_at=playlist.created_at
    )


@router.delete("/playlists/{playlist_id}", status_code=204)
async def delete_playlist(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить плейлист (soft delete)."""
    playlist = db.query(Playlist).filter(
        Playlist.id == uuid.UUID(playlist_id),
        Playlist.user_id == current_user.id
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    # Проверка использования в активных слотах
    used = db.query(ScheduleSlot).filter(
        ScheduleSlot.playlist_id == playlist.id,
        ScheduleSlot.is_active == True
    ).first()
    if used:
        raise HTTPException(status_code=409, detail="Playlist is currently in use")

    # Soft delete
    playlist.is_active = False
    db.commit()

    return Response(status_code=204)
