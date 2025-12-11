"""
Эндпоинты для работы с группами плейлистов.

Включает:
- CRUD операции для PlaylistGroup
- Получение групп с вложенными плейлистами
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.models.schedule import PlaylistGroup, Playlist
from src.api.auth import get_current_user

from .schemas import (
    PlaylistGroupCreate,
    PlaylistGroupUpdate,
    PlaylistGroupResponse,
    PlaylistGroupWithPlaylistsResponse,
    PlaylistResponse,
)

router = APIRouter(tags=["schedule-groups"])


@router.get("/groups", response_model=List[PlaylistGroupResponse])
async def get_playlist_groups(
    channel_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список групп плейлистов."""
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        query = db.query(PlaylistGroup)
    else:
        query = db.query(PlaylistGroup).filter(PlaylistGroup.user_id == current_user.id)
    
    if channel_id:
        query = query.filter(
            or_(
                PlaylistGroup.channel_id == uuid.UUID(channel_id),
                PlaylistGroup.channel_id == None
            )
        )
    
    groups = query.filter(PlaylistGroup.is_active == True).order_by(PlaylistGroup.position, PlaylistGroup.name).all()
    
    return [
        PlaylistGroupResponse(
            id=str(g.id),
            name=g.name,
            description=g.description,
            channel_id=str(g.channel_id) if g.channel_id else None,
            color=g.color,
            icon=g.icon or "folder",
            position=g.position or 0,
            is_expanded=g.is_expanded if g.is_expanded is not None else True,
            is_active=g.is_active,
            playlists_count=len([p for p in g.playlists if p.is_active]),
            created_at=g.created_at
        )
        for g in groups
    ]


@router.get("/groups/with-playlists", response_model=List[PlaylistGroupWithPlaylistsResponse])
async def get_playlist_groups_with_playlists(
    channel_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить группы с вложенными плейлистами (для UI)."""
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        query = db.query(PlaylistGroup)
    else:
        query = db.query(PlaylistGroup).filter(PlaylistGroup.user_id == current_user.id)
    
    if channel_id:
        query = query.filter(
            or_(
                PlaylistGroup.channel_id == uuid.UUID(channel_id),
                PlaylistGroup.channel_id == None
            )
        )
    
    groups = query.filter(PlaylistGroup.is_active == True).order_by(PlaylistGroup.position, PlaylistGroup.name).all()
    
    result = []
    for g in groups:
        active_playlists = [p for p in g.playlists if p.is_active]
        result.append(PlaylistGroupWithPlaylistsResponse(
            id=str(g.id),
            name=g.name,
            description=g.description,
            channel_id=str(g.channel_id) if g.channel_id else None,
            color=g.color,
            icon=g.icon or "folder",
            position=g.position or 0,
            is_expanded=g.is_expanded if g.is_expanded is not None else True,
            is_active=g.is_active,
            playlists_count=len(active_playlists),
            created_at=g.created_at,
            playlists=[
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
                for p in sorted(active_playlists, key=lambda x: (x.position or 0, x.name))
            ]
        ))
    
    return result


@router.post("/groups", response_model=PlaylistGroupResponse, status_code=201)
async def create_playlist_group(
    group_data: PlaylistGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать группу плейлистов."""
    max_pos = db.query(PlaylistGroup).filter(
        PlaylistGroup.user_id == current_user.id,
        PlaylistGroup.is_active == True
    ).count()
    
    group = PlaylistGroup(
        user_id=current_user.id,
        channel_id=uuid.UUID(group_data.channel_id) if group_data.channel_id else None,
        name=group_data.name,
        description=group_data.description,
        color=group_data.color,
        icon=group_data.icon,
        position=max_pos
    )
    
    db.add(group)
    db.commit()
    db.refresh(group)
    
    return PlaylistGroupResponse(
        id=str(group.id),
        name=group.name,
        description=group.description,
        channel_id=str(group.channel_id) if group.channel_id else None,
        color=group.color,
        icon=group.icon or "folder",
        position=group.position or 0,
        is_expanded=True,
        is_active=True,
        playlists_count=0,
        created_at=group.created_at
    )


@router.put("/groups/{group_id}", response_model=PlaylistGroupResponse)
async def update_playlist_group(
    group_id: str,
    group_data: PlaylistGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить группу плейлистов."""
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        group = db.query(PlaylistGroup).filter(PlaylistGroup.id == uuid.UUID(group_id)).first()
    else:
        group = db.query(PlaylistGroup).filter(
            PlaylistGroup.id == uuid.UUID(group_id),
            PlaylistGroup.user_id == current_user.id
        ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    update_data = group_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(group, key, value)
    
    db.commit()
    db.refresh(group)
    
    return PlaylistGroupResponse(
        id=str(group.id),
        name=group.name,
        description=group.description,
        channel_id=str(group.channel_id) if group.channel_id else None,
        color=group.color,
        icon=group.icon or "folder",
        position=group.position or 0,
        is_expanded=group.is_expanded if group.is_expanded is not None else True,
        is_active=group.is_active,
        playlists_count=len([p for p in group.playlists if p.is_active]),
        created_at=group.created_at
    )


@router.delete("/groups/{group_id}", status_code=204)
async def delete_playlist_group(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить группу плейлистов (soft delete)."""
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        group = db.query(PlaylistGroup).filter(PlaylistGroup.id == uuid.UUID(group_id)).first()
    else:
        group = db.query(PlaylistGroup).filter(
            PlaylistGroup.id == uuid.UUID(group_id),
            PlaylistGroup.user_id == current_user.id
        ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # Soft delete
    group.is_active = False
    db.commit()
    
    return None
