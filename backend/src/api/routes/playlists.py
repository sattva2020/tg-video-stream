from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import uuid

from src.database import get_db
from src.schemas.playlist import (
    PlaylistCreate, PlaylistUpdate, PlaylistResponse,
    PlaylistTemplateCreate, PlaylistTemplateUpdate, PlaylistTemplateResponse,
    ApplyTemplateRequest,
    SmartPlaylistCreate, SmartPlaylistUpdate, SmartPlaylistResponse,
    PlaylistGroupCreate, PlaylistGroupUpdate, PlaylistGroupResponse,
    BulkDeleteRequest, BulkMoveRequest, BulkCopyRequest, BulkOperationResponse
)
from src.services.user_playlist_service import UserPlaylistService
from src.services.playlist_template_service import PlaylistTemplateService
from src.services.smart_playlist_service import SmartPlaylistService
from src.services.playlist_group_service import PlaylistGroupService
from api.auth import get_current_user
from src.models.user import User

router = APIRouter()

@router.get("/", response_model=List[PlaylistResponse])
def get_my_playlists(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's playlists."""
    return UserPlaylistService.get_user_playlists(db, current_user.id, skip, limit)

@router.get("/public", response_model=List[PlaylistResponse])
def get_public_playlists(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all public playlists."""
    return UserPlaylistService.get_public_playlists(db, skip, limit)

@router.post("/", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def create_playlist(
    playlist: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new playlist."""
    return UserPlaylistService.create_playlist(db, playlist, current_user.id)

@router.get("/{playlist_id}", response_model=PlaylistResponse)
def get_playlist(
    playlist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get playlist details. Must be owner or playlist must be public."""
    playlist = UserPlaylistService.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if playlist.user_id != current_user.id and not playlist.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to view this playlist")
        
    return playlist

@router.put("/{playlist_id}", response_model=PlaylistResponse)
def update_playlist(
    playlist_id: uuid.UUID,
    update_data: PlaylistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update playlist. Owner only."""
    playlist = UserPlaylistService.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this playlist")
        
    return UserPlaylistService.update_playlist(db, playlist, update_data)

@router.delete("/{playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_playlist(
    playlist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete playlist. Owner only."""
    playlist = UserPlaylistService.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    if playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this playlist")
        
    UserPlaylistService.delete_playlist(db, playlist)

@router.post("/{playlist_id}/clone", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def clone_playlist(
    playlist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clone a playlist to my library. Source must be public or owned by me."""
    playlist = UserPlaylistService.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    if playlist.user_id != current_user.id and not playlist.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to clone this playlist")
        
    return UserPlaylistService.clone_playlist(db, playlist, current_user.id)

@router.post("/{playlist_id}/play", status_code=status.HTTP_200_OK)
def play_playlist(
    playlist_id: uuid.UUID,
    channel_id: uuid.UUID = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Play a playlist immediately on the user's channel.
    If channel_id is not provided, uses the first available channel.
    """
    playlist = UserPlaylistService.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    # Check access rights (owner or public)
    if playlist.user_id != current_user.id and not playlist.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to play this playlist")

    try:
        result = UserPlaylistService.play_playlist(db, playlist_id, current_user.id, channel_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/import/m3u", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def import_playlist_m3u(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Import playlist from M3U file."""
    if not file.filename.lower().endswith(('.m3u', '.m3u8')):
        raise HTTPException(status_code=400, detail="Invalid file format. Only .m3u and .m3u8 are supported.")
    
    content = await file.read()
    try:
        content_str = content.decode('utf-8')
    except UnicodeDecodeError:
        # Try latin-1 if utf-8 fails
        content_str = content.decode('latin-1')
        
    return UserPlaylistService.import_m3u_playlist(db, content_str, file.filename, current_user.id)

@router.get("/{playlist_id}/export/m3u")
def export_playlist_m3u(
    playlist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export playlist as M3U file."""
    playlist = UserPlaylistService.get_playlist(db, playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    if playlist.user_id != current_user.id and not playlist.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to export this playlist")
        
    content = UserPlaylistService.generate_m3u(playlist)
    
    filename = f"{playlist.name.replace(' ', '_')}.m3u"
    
    return Response(
        content=content,
        media_type="audio/x-mpegurl",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Bulk Operations Routes
@router.post("/bulk/delete", response_model=BulkOperationResponse, status_code=status.HTTP_200_OK)
def bulk_delete_playlists(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk delete multiple playlists. Only playlists owned by the user will be deleted."""
    return UserPlaylistService.bulk_delete_playlists(db, request.playlist_ids, current_user.id)

@router.post("/bulk/move", response_model=BulkOperationResponse, status_code=status.HTTP_200_OK)
def bulk_move_playlists(
    request: BulkMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk move multiple playlists to a group. Only playlists owned by the user will be moved."""
    return UserPlaylistService.bulk_move_playlists(db, request.playlist_ids, request.group_id, current_user.id)

@router.post("/bulk/copy", response_model=BulkOperationResponse, status_code=status.HTTP_200_OK)
def bulk_copy_playlists(
    request: BulkCopyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk copy multiple playlists. Only playlists owned by or public to the user will be copied."""
    return UserPlaylistService.bulk_copy_playlists(db, request.playlist_ids, current_user.id)

# Playlist Templates Routes
@router.get("/templates", response_model=List[PlaylistTemplateResponse])
def get_my_templates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's playlist templates."""
    return PlaylistTemplateService.get_user_templates(db, current_user.id, skip, limit)

@router.get("/templates/public", response_model=List[PlaylistTemplateResponse])
def get_public_templates(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all public playlist templates."""
    return PlaylistTemplateService.get_public_templates(db, skip, limit)

@router.post("/templates", response_model=PlaylistTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template: PlaylistTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new playlist template."""
    items_data = [item.model_dump() for item in template.items]
    return PlaylistTemplateService.create_template(
        db,
        name=template.name,
        user_id=current_user.id,
        items=items_data,
        description=template.description,
        is_public=template.is_public
    )

@router.get("/templates/{template_id}", response_model=PlaylistTemplateResponse)
def get_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get template details. Must be owner or template must be public."""
    template = PlaylistTemplateService.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.user_id != current_user.id and not template.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to view this template")

    return template

@router.put("/templates/{template_id}", response_model=PlaylistTemplateResponse)
def update_template(
    template_id: uuid.UUID,
    update_data: PlaylistTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update template. Owner only."""
    template = PlaylistTemplateService.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this template")

    items_data = None
    if update_data.items is not None:
        items_data = [item.model_dump() for item in update_data.items]

    return PlaylistTemplateService.update_template(
        db,
        db_template=template,
        name=update_data.name,
        description=update_data.description,
        is_public=update_data.is_public,
        items=items_data
    )

@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete template. Owner only."""
    template = PlaylistTemplateService.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this template")

    PlaylistTemplateService.delete_template(db, template)

@router.post("/templates/{template_id}/apply", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
def apply_template(
    template_id: uuid.UUID,
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Apply a template to create a new playlist."""
    template = PlaylistTemplateService.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check access (owner or public)
    if template.user_id != current_user.id and not template.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to use this template")

    try:
        return PlaylistTemplateService.apply_template(
            db,
            template_id=template_id,
            user_id=current_user.id,
            playlist_name=request.playlist_name,
            playlist_description=request.playlist_description,
            group_id=request.group_id,
            channel_id=request.channel_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/templates/{template_id}/clone", response_model=PlaylistTemplateResponse, status_code=status.HTTP_201_CREATED)
def clone_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clone a template to my library. Source must be public or owned by me."""
    template = PlaylistTemplateService.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.user_id != current_user.id and not template.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to clone this template")

    return PlaylistTemplateService.clone_template(db, template, current_user.id)

# Smart Playlists Routes
@router.get("/smart", response_model=List[SmartPlaylistResponse])
def get_my_smart_playlists(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's smart playlists."""
    return SmartPlaylistService.get_user_smart_playlists(db, current_user.id, skip, limit)

@router.get("/smart/public", response_model=List[SmartPlaylistResponse])
def get_public_smart_playlists(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all public smart playlists."""
    return SmartPlaylistService.get_public_smart_playlists(db, skip, limit)

@router.post("/smart", response_model=SmartPlaylistResponse, status_code=status.HTTP_201_CREATED)
def create_smart_playlist(
    smart_playlist: SmartPlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new smart playlist."""
    criteria_dict = smart_playlist.criteria.model_dump()
    return SmartPlaylistService.create_smart_playlist(
        db,
        name=smart_playlist.name,
        user_id=current_user.id,
        criteria=criteria_dict,
        description=smart_playlist.description,
        is_public=smart_playlist.is_public,
        group_id=smart_playlist.group_id,
        auto_update=smart_playlist.auto_update,
        auto_update_interval=smart_playlist.auto_update_interval
    )

@router.get("/smart/{smart_playlist_id}", response_model=SmartPlaylistResponse)
def get_smart_playlist(
    smart_playlist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get smart playlist details. Must be owner or smart playlist must be public."""
    smart_playlist = SmartPlaylistService.get_smart_playlist(db, smart_playlist_id)
    if not smart_playlist:
        raise HTTPException(status_code=404, detail="Smart playlist not found")

    if smart_playlist.user_id != current_user.id and not smart_playlist.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to view this smart playlist")

    return smart_playlist

@router.put("/smart/{smart_playlist_id}", response_model=SmartPlaylistResponse)
def update_smart_playlist(
    smart_playlist_id: uuid.UUID,
    update_data: SmartPlaylistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update smart playlist. Owner only."""
    smart_playlist = SmartPlaylistService.get_smart_playlist(db, smart_playlist_id)
    if not smart_playlist:
        raise HTTPException(status_code=404, detail="Smart playlist not found")

    if smart_playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this smart playlist")

    criteria_dict = update_data.criteria.model_dump() if update_data.criteria else None

    return SmartPlaylistService.update_smart_playlist(
        db,
        db_smart_playlist=smart_playlist,
        name=update_data.name,
        description=update_data.description,
        is_public=update_data.is_public,
        criteria=criteria_dict,
        auto_update=update_data.auto_update,
        auto_update_interval=update_data.auto_update_interval,
        group_id=update_data.group_id
    )

@router.delete("/smart/{smart_playlist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_smart_playlist(
    smart_playlist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete smart playlist. Owner only."""
    smart_playlist = SmartPlaylistService.get_smart_playlist(db, smart_playlist_id)
    if not smart_playlist:
        raise HTTPException(status_code=404, detail="Smart playlist not found")

    if smart_playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this smart playlist")

    SmartPlaylistService.delete_smart_playlist(db, smart_playlist)

@router.post("/smart/{smart_playlist_id}/refresh", response_model=PlaylistResponse, status_code=status.HTTP_200_OK)
def refresh_smart_playlist(
    smart_playlist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Regenerate the smart playlist based on its criteria."""
    smart_playlist = SmartPlaylistService.get_smart_playlist(db, smart_playlist_id)
    if not smart_playlist:
        raise HTTPException(status_code=404, detail="Smart playlist not found")

    if smart_playlist.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to refresh this smart playlist")

    try:
        return SmartPlaylistService.refresh_smart_playlist(db, smart_playlist)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/smart/{smart_playlist_id}/clone", response_model=SmartPlaylistResponse, status_code=status.HTTP_201_CREATED)
def clone_smart_playlist(
    smart_playlist_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clone a smart playlist to my library. Source must be public or owned by me."""
    smart_playlist = SmartPlaylistService.get_smart_playlist(db, smart_playlist_id)
    if not smart_playlist:
        raise HTTPException(status_code=404, detail="Smart playlist not found")

    if smart_playlist.user_id != current_user.id and not smart_playlist.is_public:
        raise HTTPException(status_code=403, detail="Not authorized to clone this smart playlist")

    return SmartPlaylistService.clone_smart_playlist(db, smart_playlist, current_user.id)

# Playlist Groups Routes
@router.get("/groups", response_model=List[PlaylistGroupResponse])
def get_my_groups(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's playlist groups."""
    return PlaylistGroupService.get_user_groups(db, current_user.id, skip, limit)

@router.post("/groups", response_model=PlaylistGroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group: PlaylistGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new playlist group."""
    return PlaylistGroupService.create_group(
        db,
        name=group.name,
        user_id=current_user.id,
        parent_id=group.parent_id,
        description=group.description,
        color=group.color,
        icon=group.icon,
        channel_id=group.channel_id,
        position=group.position
    )

@router.get("/groups/{group_id}", response_model=PlaylistGroupResponse)
def get_group(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get group details. Must be owner."""
    group = PlaylistGroupService.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this group")

    return group

@router.put("/groups/{group_id}", response_model=PlaylistGroupResponse)
def update_group(
    group_id: uuid.UUID,
    update_data: PlaylistGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update group. Owner only."""
    group = PlaylistGroupService.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this group")

    try:
        return PlaylistGroupService.update_group(
            db,
            db_group=group,
            name=update_data.name,
            parent_id=update_data.parent_id,
            description=update_data.description,
            color=update_data.color,
            icon=update_data.icon,
            position=update_data.position
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/groups/{group_id}/move", response_model=PlaylistGroupResponse, status_code=status.HTTP_200_OK)
def move_group(
    group_id: uuid.UUID,
    parent_id: uuid.UUID = None,
    position: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Move a group to a new parent and/or position. Owner only."""
    group = PlaylistGroupService.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to move this group")

    try:
        return PlaylistGroupService.move_group(
            db,
            group_id=group_id,
            new_parent_id=parent_id,
            new_position=position
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete group. Owner only. Child groups will be moved to root level."""
    group = PlaylistGroupService.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this group")

    PlaylistGroupService.delete_group(db, group)
