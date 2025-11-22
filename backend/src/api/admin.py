from fastapi import APIRouter, Depends
from api.auth import require_admin
from models.user import User
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/users")
def list_users(status: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    users = query.all()
    return [{"id": str(u.id), "email": u.email, "status": getattr(u, 'status', None)} for u in users]


@router.post("/users/{user_id}/approve")
def approve_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    user.status = 'approved'
    db.commit()
    db.refresh(user)
    return {"status": "ok", "id": str(user.id), "new_status": user.status}


@router.post("/users/{user_id}/reject")
def reject_user(user_id: str, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"status": "error", "message": "User not found"}
    user.status = 'rejected'
    db.commit()
    db.refresh(user)
    return {"status": "ok", "id": str(user.id), "new_status": user.status}

@router.post("/restart_stream")
def restart_stream(current_user: User = Depends(require_admin)):
    """
    Restarts the video stream service.
    Only accessible by admins.
    """
    # In a real app, this would trigger a system command or service restart
    # For now, we just return success
    return {"status": "success", "message": "Stream restart initiated"}
