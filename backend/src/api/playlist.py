from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
from models.playlist import PlaylistItem
from models.user import User
from api.auth import get_current_user
import uuid

router = APIRouter()

# Pydantic models
class PlaylistItemCreate(BaseModel):
    url: str
    title: Optional[str] = None

class PlaylistItemResponse(BaseModel):
    id: uuid.UUID
    url: str
    title: Optional[str]
    position: int
    created_at: str

    class Config:
        orm_mode = True

@router.get("/", response_model=List[PlaylistItemResponse])
def get_playlist(db: Session = Depends(get_db)):
    items = db.query(PlaylistItem).order_by(PlaylistItem.position.asc(), PlaylistItem.created_at.asc()).all()
    # Convert datetime to string for simple response
    return [
        PlaylistItemResponse(
            id=item.id,
            url=item.url,
            title=item.title,
            position=item.position,
            created_at=item.created_at.isoformat() if item.created_at else ""
        ) for item in items
    ]

@router.post("/", response_model=PlaylistItemResponse)
def add_playlist_item(
    item: PlaylistItemCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Simple logic to determine position: put at the end
    last_item = db.query(PlaylistItem).order_by(PlaylistItem.position.desc()).first()
    new_position = (last_item.position + 1) if last_item else 0

    new_item = PlaylistItem(
        url=item.url,
        title=item.title or item.url, # Fallback title
        position=new_position,
        created_by=current_user.id
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    
    return PlaylistItemResponse(
        id=new_item.id,
        url=new_item.url,
        title=new_item.title,
        position=new_item.position,
        created_at=new_item.created_at.isoformat() if new_item.created_at else ""
    )

@router.delete("/{item_id}")
def delete_playlist_item(
    item_id: uuid.UUID, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    item = db.query(PlaylistItem).filter(PlaylistItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(item)
    db.commit()
    return {"ok": True}
