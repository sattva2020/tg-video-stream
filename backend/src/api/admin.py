from fastapi import APIRouter, Depends, HTTPException, Query
from api.auth import require_admin
from src.models.user import User
from src.models.playlist import PlaylistItem
from database import get_db
from sqlalchemy.orm import Session
from uuid import UUID
import redis
import json
import os
from typing import List, Optional
from pydantic import BaseModel
from src.services.stream_controller import get_stream_controller, StreamController
from src.services.playlist_service import playlist_service

router = APIRouter()

class PlaylistUpdate(BaseModel):
    items: List[str]

class PaginatedUsersResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int

# Redis connection
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379"))


@router.get("/users", response_model=PaginatedUsersResponse)
def list_users(
    status: str | None = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search by email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    List users with pagination and optional filtering.
    """
    query = db.query(User)
    
    # Apply filters
    if status:
        query = query.filter(User.status == status)
    if search:
        query = query.filter(User.email.ilike(f"%{search}%"))
    
    # Get total count
    total = query.count()
    
    # Calculate pagination
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size
    
    # Get paginated results
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()
    
    return PaginatedUsersResponse(
        items=[{
            "id": str(u.id),
            "email": u.email,
            "status": getattr(u, 'status', None),
            "role": getattr(u, 'role', 'user'),
            "full_name": getattr(u, 'full_name', None),
            "created_at": u.created_at.isoformat() if u.created_at else None
        } for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/users/{user_id}/approve")
def approve_user(user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    # Защита: нельзя изменять superadmin
    if getattr(user, 'role', '').lower() == 'superadmin':
        raise HTTPException(status_code=403, detail="Cannot modify superadmin account")
    user.status = 'approved'
    db.commit()
    db.refresh(user)
    return {"status": "ok", "id": str(user.id), "new_status": user.status}


@router.post("/users/{user_id}/reject")
def reject_user(user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    # Защита: нельзя изменять superadmin
    if getattr(user, 'role', '').lower() == 'superadmin':
        raise HTTPException(status_code=403, detail="Cannot modify superadmin account")
    user.status = 'rejected'
    db.commit()
    db.refresh(user)
    return {"status": "ok", "id": str(user.id), "new_status": user.status}


@router.delete("/users/{user_id}")
def delete_user(user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Delete a user. Superadmin accounts cannot be deleted."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Защита: нельзя удалить superadmin
    if getattr(user, 'role', '').lower() == 'superadmin':
        raise HTTPException(status_code=403, detail="Cannot delete superadmin account")
    # Нельзя удалить самого себя
    if user.id == current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete yourself")
    db.delete(user)
    db.commit()
    return {"status": "ok", "message": "User deleted", "id": str(user_id)}

@router.post("/stream/start")
def start_stream(current_user: User = Depends(require_admin), controller: StreamController = Depends(get_stream_controller)):
    success = controller.start_stream()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start stream")
    return {"status": "success", "message": "Stream started"}

@router.post("/stream/stop")
def stop_stream(current_user: User = Depends(require_admin), controller: StreamController = Depends(get_stream_controller)):
    success = controller.stop_stream()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to stop stream")
    return {"status": "success", "message": "Stream stopped"}

@router.post("/stream/restart")
def restart_stream(current_user: User = Depends(require_admin), controller: StreamController = Depends(get_stream_controller)):
    """
    Restarts the video stream service.
    Only accessible by admins.
    """
    success = controller.restart_stream()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to restart stream")
    return {"status": "success", "message": "Stream restarted"}

@router.get("/stream/status")
def get_stream_status(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """
    Get comprehensive stream status including:
    - Online/offline status
    - Currently playing track
    - Queue length
    - Uptime
    """
    try:
        # Get metrics from Redis
        metrics_json = redis_client.get('streamer:metrics:latest')
        metrics = json.loads(metrics_json) if metrics_json else None
        
        # Get stream state from Redis
        state_json = redis_client.get('streamer:state')
        state = json.loads(state_json) if state_json else {}
        
        # Get currently playing track from database
        current_track = db.query(PlaylistItem).filter(
            PlaylistItem.status == 'playing'
        ).first()
        
        # Get queue stats
        queue_total = db.query(PlaylistItem).count()
        queue_queued = db.query(PlaylistItem).filter(PlaylistItem.status == 'queued').count()
        
        return {
            "online": metrics is not None or state.get("status") == "running",
            "status": state.get("status", "unknown"),
            "uptime_seconds": state.get("uptime_seconds", 0),
            "current_track": {
                "id": str(current_track.id) if current_track else None,
                "title": current_track.title if current_track else None,
                "url": current_track.url if current_track else None,
                "duration": current_track.duration if current_track else None,
                "type": current_track.type if current_track else None,
            } if current_track else None,
            "queue": {
                "total": queue_total,
                "queued": queue_queued,
            },
            "metrics": metrics,
        }
    except Exception as e:
        # Return offline status on error
        return {
            "online": False,
            "status": "error",
            "error": str(e),
            "current_track": None,
            "queue": {"total": 0, "queued": 0},
            "metrics": None,
        }

@router.get("/stream/logs")
def get_stream_logs(lines: int = 100, current_user: User = Depends(require_admin), controller: StreamController = Depends(get_stream_controller)):
    logs = controller.get_logs(lines)
    return {"logs": logs}

@router.get("/stream/metrics")
def get_stream_metrics(current_user: User = Depends(require_admin)):
    try:
        metrics_json = redis_client.get('streamer:metrics:latest')
        metrics = json.loads(metrics_json) if metrics_json else None
        return {
            "online": metrics is not None,
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@router.get("/playlist")
def get_playlist(current_user: User = Depends(require_admin)):
    items = playlist_service.get_playlist()
    return {"items": items}

@router.post("/playlist")
def update_playlist(playlist: PlaylistUpdate, current_user: User = Depends(require_admin)):
    success = playlist_service.update_playlist(playlist.items)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update playlist")
    return {"status": "success", "items": playlist.items}
