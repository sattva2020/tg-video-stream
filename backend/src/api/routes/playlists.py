from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import uuid

from src.database import get_db
from src.schemas.playlist import (
    PlaylistCreate, PlaylistUpdate, PlaylistResponse,
    PlaylistTemplateCreate, PlaylistTemplateUpdate, PlaylistTemplateResponse,
    ApplyTemplateRequest
)
from src.services.user_playlist_service import UserPlaylistService
from src.services.playlist_template_service import PlaylistTemplateService
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
