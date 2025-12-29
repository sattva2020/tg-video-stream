from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import uuid

from src.database import get_db
from src.schemas.playlist import PlaylistCreate, PlaylistUpdate, PlaylistResponse
from src.services.user_playlist_service import UserPlaylistService
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
