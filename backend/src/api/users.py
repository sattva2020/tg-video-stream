from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import src.models
from database import get_db
from auth import jwt

router = APIRouter()

from api.auth import get_current_user, format_auth_error

@router.get("/me")
def read_users_me(request: Request, current_user: src.models.user.User = Depends(get_current_user)):
    """
    Fetch the current logged-in user's profile.
    """
    # If user hasn't been approved yet, return structured 403 per contract
    if getattr(current_user, 'status', 'approved') != 'approved':
        detail = format_auth_error(
            code='pending' if current_user.status == 'pending' else 'rejected',
            hint='contact_admin',
            message_key='auth.account_pending' if current_user.status == 'pending' else 'auth.account_rejected',
            req=request,
        )
        raise HTTPException(status_code=403, detail=detail)

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "profile_picture_url": current_user.profile_picture_url,
        "role": current_user.role,
        "status": getattr(current_user, 'status', 'approved'),
        "google_id": current_user.google_id,
        "telegram_id": current_user.telegram_id,
        "telegram_username": current_user.telegram_username,
        "created_at": current_user.created_at,
    }