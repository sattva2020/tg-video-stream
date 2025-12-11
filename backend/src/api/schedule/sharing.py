"""
Эндпоинты для шаринга плейлистов.
"""
import uuid
import secrets
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.database import get_db
from src.models.user import User
from src.models.schedule import Playlist
from src.api.auth import get_current_user

from .schemas import PlaylistResponse

router = APIRouter(tags=["schedule-sharing"])


class ShareResponse(BaseModel):
    """Ответ при генерации кода шаринга."""
    share_code: str
    playlist_id: str
    playlist_name: str


class ImportRequest(BaseModel):
    """Запрос на импорт плейлиста по коду."""
    share_code: str
    channel_id: str = None  # Опционально - привязать к каналу


@router.get("/playlists/public", response_model=List[PlaylistResponse])
async def get_public_playlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список публичных плейлистов."""
    playlists = db.query(Playlist).filter(
        Playlist.is_public == True,
        Playlist.is_active == True
    ).order_by(Playlist.created_at.desc()).all()
    
    return [
        PlaylistResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            channel_id=str(p.channel_id) if p.channel_id else None,
            group_id=str(p.group_id) if p.group_id else None,
            position=p.position or 0,
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


@router.post("/playlists/{playlist_id}/share", response_model=ShareResponse)
async def generate_share_code(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Сгенерировать код для шаринга плейлиста."""
    playlist = db.query(Playlist).filter(
        Playlist.id == uuid.UUID(playlist_id),
        Playlist.user_id == current_user.id
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    # Генерируем уникальный код (UUID без дефисов)
    share_code = secrets.token_urlsafe(24)[:32]  # 32 символа
    
    # Проверяем уникальность
    while db.query(Playlist).filter(Playlist.share_code == share_code).first():
        share_code = secrets.token_urlsafe(24)[:32]
    
    playlist.share_code = share_code
    db.commit()
    
    return ShareResponse(
        share_code=share_code,
        playlist_id=str(playlist.id),
        playlist_name=playlist.name
    )


@router.post("/playlists/import", response_model=PlaylistResponse)
async def import_playlist_by_code(
    request: ImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Импортировать плейлист по коду шаринга."""
    # Находим оригинальный плейлист
    original = db.query(Playlist).filter(
        Playlist.share_code == request.share_code,
        Playlist.is_active == True
    ).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Invalid share code")
    
    # Создаём копию плейлиста для текущего пользователя
    max_pos = db.query(Playlist).filter(
        Playlist.user_id == current_user.id,
        Playlist.is_active == True
    ).count()
    
    new_playlist = Playlist(
        user_id=current_user.id,
        channel_id=uuid.UUID(request.channel_id) if request.channel_id else None,
        name=f"{original.name} (копия)",
        description=original.description,
        color=original.color,
        source_type=original.source_type,
        source_url=original.source_url,
        items=original.items,
        items_count=original.items_count,
        total_duration=original.total_duration,
        is_shuffled=original.is_shuffled,
        position=max_pos
    )
    
    db.add(new_playlist)
    db.commit()
    db.refresh(new_playlist)
    
    return PlaylistResponse(
        id=str(new_playlist.id),
        name=new_playlist.name,
        description=new_playlist.description,
        channel_id=str(new_playlist.channel_id) if new_playlist.channel_id else None,
        group_id=str(new_playlist.group_id) if new_playlist.group_id else None,
        position=new_playlist.position or 0,
        color=new_playlist.color,
        source_type=new_playlist.source_type,
        source_url=new_playlist.source_url,
        items=new_playlist.items or [],
        items_count=new_playlist.items_count,
        total_duration=new_playlist.total_duration,
        is_active=new_playlist.is_active,
        is_shuffled=new_playlist.is_shuffled,
        created_at=new_playlist.created_at
    )


@router.delete("/playlists/{playlist_id}/share")
async def revoke_share_code(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отозвать код шаринга (удалить share_code)."""
    playlist = db.query(Playlist).filter(
        Playlist.id == uuid.UUID(playlist_id),
        Playlist.user_id == current_user.id
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    playlist.share_code = None
    db.commit()
    
    return {"status": "revoked"}


@router.post("/playlists/{playlist_id}/copy", response_model=PlaylistResponse)
async def copy_public_playlist(
    playlist_id: str,
    channel_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Скопировать публичный плейлист себе."""
    original = db.query(Playlist).filter(
        Playlist.id == uuid.UUID(playlist_id),
        Playlist.is_public == True,
        Playlist.is_active == True
    ).first()
    
    if not original:
        raise HTTPException(status_code=404, detail="Public playlist not found")
    
    # Создаём копию
    max_pos = db.query(Playlist).filter(
        Playlist.user_id == current_user.id,
        Playlist.is_active == True
    ).count()
    
    new_playlist = Playlist(
        user_id=current_user.id,
        channel_id=uuid.UUID(channel_id) if channel_id else None,
        name=f"{original.name} (копия)",
        description=original.description,
        color=original.color,
        source_type=original.source_type,
        source_url=original.source_url,
        items=original.items,
        items_count=original.items_count,
        total_duration=original.total_duration,
        is_shuffled=original.is_shuffled,
        position=max_pos
    )
    
    db.add(new_playlist)
    db.commit()
    db.refresh(new_playlist)
    
    return PlaylistResponse(
        id=str(new_playlist.id),
        name=new_playlist.name,
        description=new_playlist.description,
        channel_id=str(new_playlist.channel_id) if new_playlist.channel_id else None,
        group_id=str(new_playlist.group_id) if new_playlist.group_id else None,
        position=new_playlist.position or 0,
        color=new_playlist.color,
        source_type=new_playlist.source_type,
        source_url=new_playlist.source_url,
        items=new_playlist.items or [],
        items_count=new_playlist.items_count,
        total_duration=new_playlist.total_duration,
        is_active=new_playlist.is_active,
        is_shuffled=new_playlist.is_shuffled,
        created_at=new_playlist.created_at
    )
