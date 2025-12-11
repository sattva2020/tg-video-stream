"""API для каналов уведомлений: CRUD и тестовая отправка."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.notifications import (
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
)
from src.services.notifications.channels import ChannelValidationError, NotificationChannelService

router = APIRouter(prefix="/api/notifications/channels", tags=["Notifications"])


class ChannelTestRequest(BaseModel):
    recipient: str = Field(..., description="Адрес получателя для тестовой отправки")
    subject: Optional[str] = Field(None, description="Тема/заголовок уведомления")
    body: Optional[str] = Field(None, description="Тело уведомления")
    context: Optional[dict] = Field(None, description="Контекст для подстановок в шаблон")
    use_celery: bool = Field(default=True, description="Отправлять через Celery или синхронно")


class ChannelTestResponse(BaseModel):
    status: str
    event_id: str


@router.get("", response_model=List[NotificationChannelResponse])
def list_channels(
    enabled: Optional[bool] = Query(None, description="Фильтр по включённым каналам"),
    types: Optional[List[str]] = Query(None, alias="type", description="Фильтр по типам"),
    db: Session = Depends(get_db),
):
    service = NotificationChannelService(db)
    return service.base.list_channels(enabled=enabled, types=types)


@router.post("", response_model=NotificationChannelResponse, status_code=status.HTTP_201_CREATED)
def create_channel(data: NotificationChannelCreate, db: Session = Depends(get_db)):
    service = NotificationChannelService(db)
    try:
        return service.create_channel(data)
    except ChannelValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/{channel_id}", response_model=NotificationChannelResponse)
def update_channel(channel_id: UUID, data: NotificationChannelUpdate, db: Session = Depends(get_db)):
    service = NotificationChannelService(db)
    try:
        channel = service.update_channel(channel_id, data)
    except ChannelValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return channel


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(channel_id: UUID, db: Session = Depends(get_db)):
    service = NotificationChannelService(db)
    deleted = service.base.delete_channel(channel_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{channel_id}/test", response_model=ChannelTestResponse, status_code=status.HTTP_202_ACCEPTED)
def test_channel(channel_id: UUID, request: ChannelTestRequest, db: Session = Depends(get_db)):
    service = NotificationChannelService(db)
    try:
        event_id = service.test_channel(
            channel_id=channel_id,
            recipient=request.recipient,
            subject=request.subject,
            body=request.body,
            context=request.context,
            use_celery=request.use_celery,
        )
    except ChannelValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return ChannelTestResponse(status="queued", event_id=event_id)
