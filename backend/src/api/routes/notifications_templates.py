"""API для шаблонов уведомлений."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from src.database import get_db
from src.schemas.notifications import (
    NotificationTemplateCreate,
    NotificationTemplateResponse,
    NotificationTemplateUpdate,
)
from src.services.notifications.base import NotificationService

router = APIRouter(prefix="/api/notifications/templates", tags=["Notifications"])


@router.get("", response_model=List[NotificationTemplateResponse])
def list_templates(
    locale: Optional[str] = Query(None, description="Фильтр по локали"),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    return service.list_templates(locale=locale)


@router.post("", response_model=NotificationTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(data: NotificationTemplateCreate, db: Session = Depends(get_db)):
    service = NotificationService(db)
    return service.create_template(data)


@router.patch("/{template_id}", response_model=NotificationTemplateResponse)
def update_template(template_id: UUID, data: NotificationTemplateUpdate, db: Session = Depends(get_db)):
    service = NotificationService(db)
    template = service.update_template(template_id, data)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: UUID, db: Session = Depends(get_db)):
    service = NotificationService(db)
    deleted = service.delete_template(template_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
