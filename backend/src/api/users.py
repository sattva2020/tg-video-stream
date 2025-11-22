from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

import models
from database import get_db
from auth import jwt

router = APIRouter()

from api.auth import get_current_user

@router.get("/me")
def read_users_me(current_user: models.user.User = Depends(get_current_user)):
    """
    Fetch the current logged-in user's profile.
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "profile_picture_url": current_user.profile_picture_url,
        "role": current_user.role,
        "created_at": current_user.created_at,
    }