"""API для получателей уведомлений: CRUD."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.notifications import (
    NotificationRecipientCreate,
    NotificationRecipientResponse,
    NotificationRecipientUpdate,
)
from src.services.notifications.base import NotificationService

router = APIRouter(prefix="/api/notifications/recipients", tags=["Notifications"])


@router.get("", response_model=List[NotificationRecipientResponse])
def list_recipients(
    status: Optional[str] = Query(None, description="Фильтр по статусу: active|blocked|opt-out"),
    r_type: Optional[str] = Query(None, alias="type", description="Фильтр по типу получателя"),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    return service.list_recipients(status=status, r_type=r_type)


@router.post("", response_model=NotificationRecipientResponse, status_code=status.HTTP_201_CREATED)
def create_recipient(data: NotificationRecipientCreate, db: Session = Depends(get_db)):
    service = NotificationService(db)
    return service.create_recipient(data)


@router.patch("/{recipient_id}", response_model=NotificationRecipientResponse)
def update_recipient(recipient_id: UUID, data: NotificationRecipientUpdate, db: Session = Depends(get_db)):
    service = NotificationService(db)
    recipient = service.update_recipient(recipient_id, data)
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")
    return recipient


@router.delete("/{recipient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipient(recipient_id: UUID, db: Session = Depends(get_db)):
    service = NotificationService(db)
    deleted = service.delete_recipient(recipient_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
