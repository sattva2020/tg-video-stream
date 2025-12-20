"""
Эндпоинты для работы с плейлистами.

Включает:
- CRUD операции для Playlist
- Привязка к каналам
- Управление элементами плейлиста
"""
import uuid
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.models.schedule import ScheduleSlot, Playlist, PlaylistGroup, RepeatType
from src.api.auth import get_current_user

from .schemas import (
    PlaylistCreate,
    PlaylistUpdate,
    PlaylistResponse,
)


async def _maybe_expand_gdrive_folder_items(source_type: str, source_url: Optional[str]) -> Optional[list]:
    """Если source_type == gdrive_folder — развернуть публичную папку в список items.

    В items сохраняем относительные URL к backend-прокси, чтобы не светить GOOGLE_DRIVE_API_KEY.
    """
    if (source_type or "").lower() != "gdrive_folder":
        return None

    if not source_url:
        raise HTTPException(status_code=400, detail="source_url is required for gdrive_folder")

    import os
    from src.services.google_drive import extract_drive_folder_id, list_drive_folder_files, filter_media_files

    api_key = os.getenv("GOOGLE_DRIVE_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="GOOGLE_DRIVE_API_KEY is not configured")

    try:
        folder_id = extract_drive_folder_id(source_url)
        files = await list_drive_folder_files(folder_id=folder_id, api_key=api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch Google Drive folder")

    media_files = filter_media_files(files)
    media_files.sort(key=lambda f: (f.get("name") or "").lower())

    items: list = []
    for f in media_files:
        file_id = f.get("id")
        name = f.get("name") or "Untitled"
        if not file_id:
            continue
        safe_name = quote(name)
        items.append(
            {
                "url": f"/api/media/gdrive/files/{file_id}/{safe_name}",
                "title": name,
                "duration": 0,
                "type": "stream",
            }
        )
    return items

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
            is_public=p.is_public if hasattr(p, 'is_public') else False,
            share_code=p.share_code if hasattr(p, 'share_code') else None,
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
    # Для gdrive_folder разворачиваем source_url в items на backend
    expanded = await _maybe_expand_gdrive_folder_items(playlist_data.source_type, playlist_data.source_url)

    # Вычисляем статистику
    items = expanded if expanded is not None else (playlist_data.items or [])
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
        group_id=str(playlist.group_id) if playlist.group_id else None,
        position=playlist.position or 0,
        color=playlist.color,
        source_type=playlist.source_type,
        source_url=playlist.source_url,
        items=playlist.items or [],
        items_count=playlist.items_count,
        total_duration=playlist.total_duration,
        is_active=playlist.is_active,
        is_shuffled=playlist.is_shuffled,
        is_public=getattr(playlist, 'is_public', False),
        share_code=getattr(playlist, 'share_code', None),
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

    # Если обновляют gdrive_folder source_url/source_type — пересобираем items.
    # Важный нюанс: фронт для non-manual источников может не отправлять items.
    new_source_type = (update_data.get("source_type") or playlist.source_type or "").lower()
    new_source_url = update_data.get("source_url") if "source_url" in update_data else playlist.source_url
    if new_source_type == "gdrive_folder" and ("source_url" in update_data or "source_type" in update_data) and "items" not in update_data:
        expanded = await _maybe_expand_gdrive_folder_items(new_source_type, new_source_url)
        update_data["items"] = expanded or []
    
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
        group_id=str(playlist.group_id) if playlist.group_id else None,
        position=playlist.position or 0,
        color=playlist.color,
        source_type=playlist.source_type,
        source_url=playlist.source_url,
        items=playlist.items or [],
        items_count=playlist.items_count,
        total_duration=playlist.total_duration,
        is_active=playlist.is_active,
        is_shuffled=playlist.is_shuffled,
        is_public=getattr(playlist, 'is_public', False),
        share_code=getattr(playlist, 'share_code', None),
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


@router.get("/playlists/channel/{channel_id}/active")
async def get_channel_active_playlist(
    channel_id: str,
    db: Session = Depends(get_db)
):
    """
    Получить активный плейлист для канала (для стримера).
    
    Логика приоритетов:
    1. Активный слот расписания на текущее время
    2. Плейлист, привязанный к каналу
    3. Пустой список если ничего не найдено
    
    Не требует авторизации (внутренний API для стримера).
    """
    from datetime import datetime, timezone, time as time_type
    
    channel_uuid = uuid.UUID(channel_id)
    now = datetime.now(timezone.utc)
    current_date = now.date()
    current_time = now.time()
    
    # 1. Ищем активный слот расписания на текущее время
    active_slot = db.query(ScheduleSlot).filter(
        ScheduleSlot.channel_id == channel_uuid,
        ScheduleSlot.is_active == True,
        ScheduleSlot.start_date <= current_date,
        ScheduleSlot.start_time <= current_time,
        ScheduleSlot.end_time > current_time,
        ScheduleSlot.playlist_id != None
    ).first()
    
    if active_slot and active_slot.playlist_id:
        playlist = db.query(Playlist).filter(
            Playlist.id == active_slot.playlist_id,
            Playlist.is_active == True
        ).first()
        
        if playlist:
            items = playlist.items or []
            if not items and playlist.source_url:
                items = [{"url": playlist.source_url, "title": playlist.name}]
                
            if items:
                return {
                    "source": "schedule",
                    "playlist_id": str(playlist.id),
                    "playlist_name": playlist.name,
                    "is_shuffled": playlist.is_shuffled,
                    "items": items
                }
    
    # 2. Ищем плейлист, привязанный к каналу (берем первый с элементами)
    channel_playlists = db.query(Playlist).filter(
        Playlist.channel_id == channel_uuid,
        Playlist.is_active == True
    ).order_by(Playlist.created_at.desc()).limit(10).all()
    
    for pl in channel_playlists:
        items = pl.items or []
        if not items and pl.source_url:
            items = [{"url": pl.source_url, "title": pl.name}]
            
        if items:
            return {
                "source": "channel",
                "playlist_id": str(pl.id),
                "playlist_name": pl.name,
                "is_shuffled": pl.is_shuffled,
                "items": items
            }
    
    # 3. Ничего не найдено
    return {
        "source": "none",
        "playlist_id": None,
        "playlist_name": None,
        "is_shuffled": False,
        "items": []
    }


@router.post("/playlists/{playlist_id}/move-to-group", response_model=PlaylistResponse)
async def move_playlist_to_group(
    playlist_id: str,
    group_id: Optional[str] = None,
    position: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Переместить плейлист в группу."""
    # Superadmin/Admin могут перемещать любые плейлисты
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        playlist = db.query(Playlist).filter(Playlist.id == uuid.UUID(playlist_id)).first()
    else:
        playlist = db.query(Playlist).filter(
            Playlist.id == uuid.UUID(playlist_id),
            Playlist.user_id == current_user.id
        ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if group_id:
        group = db.query(PlaylistGroup).filter(
            PlaylistGroup.id == uuid.UUID(group_id),
            PlaylistGroup.is_active == True
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        playlist.group_id = uuid.UUID(group_id)
    else:
        playlist.group_id = None
    
    if position is not None:
        playlist.position = position
    
    db.commit()
    db.refresh(playlist)
    
    return PlaylistResponse(
        id=str(playlist.id),
        name=playlist.name,
        description=playlist.description,
        channel_id=str(playlist.channel_id) if playlist.channel_id else None,
        group_id=str(playlist.group_id) if playlist.group_id else None,
        position=playlist.position or 0,
        color=playlist.color,
        source_type=playlist.source_type,
        source_url=playlist.source_url,
        items=playlist.items or [],
        items_count=playlist.items_count,
        total_duration=playlist.total_duration,
        is_active=playlist.is_active,
        is_shuffled=playlist.is_shuffled,
        is_public=playlist.is_public if hasattr(playlist, 'is_public') else False,
        share_code=playlist.share_code if hasattr(playlist, 'share_code') else None,
        created_at=playlist.created_at
    )


@router.post("/playlists/{playlist_id}/play-now")
async def play_playlist_now(
    playlist_id: str,
    channel_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Запустить плейлист немедленно на указанном канале.
    
    Создаёт временный слот в расписании и отправляет команду стримеру.
    """
    import json
    import redis
    import os
    from datetime import datetime, timezone, timedelta
    
    # Проверяем плейлист
    playlist = db.query(Playlist).filter(
        Playlist.id == uuid.UUID(playlist_id),
        Playlist.is_active == True
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    # Проверяем канал
    from src.models.telegram import Channel
    channel = db.query(Channel).filter(
        Channel.id == uuid.UUID(channel_id)
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Создаём временный слот на текущее время (2 часа)
    now = datetime.now(timezone.utc)
    slot = ScheduleSlot(
        channel_id=uuid.UUID(channel_id),
        playlist_id=uuid.UUID(playlist_id),
        start_date=now.date(),
        start_time=now.time(),
        end_time=(now + timedelta(hours=2)).time(),
        title=f"🎵 {playlist.name}",
        color=playlist.color or "#8B5CF6",
        is_active=True,
    )
    db.add(slot)
    db.commit()
    
    # Отправляем команду стримеру через Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        r = redis.from_url(redis_url)
        
        command = {
            "action": "update_playlist",
            "channel_id": channel_id,
            "playlist_id": playlist_id,
            "immediate": True
        }
        r.publish("stream:control", json.dumps(command))
        
    except Exception as e:
        # Логируем ошибку, но не прерываем - слот создан
        import logging
        logging.error(f"Failed to send Redis command: {e}")
    
    return {
        "status": "success",
        "message": f"Плейлист '{playlist.name}' запущен на канале '{channel.name}'",
        "slot_id": str(slot.id)
    }