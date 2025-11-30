from fastapi import APIRouter, Depends, HTTPException
from typing import List
from src.services.files import FileService
from api.auth import get_current_user
from src.models.user import User

router = APIRouter()

@router.get("/", response_model=List[str])
def list_files(
    current_user: User = Depends(get_current_user)
):
    service = FileService()
    return service.list_files()
