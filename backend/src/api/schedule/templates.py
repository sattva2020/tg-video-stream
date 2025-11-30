"""
Эндпоинты для работы с шаблонами расписания.

Включает:
- CRUD операции для ScheduleTemplate
- Применение шаблонов на выбранные даты
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.models.schedule import ScheduleSlot, ScheduleTemplate, RepeatType
from src.api.auth import get_current_user

from .schemas import (
    ScheduleTemplateCreate,
    ScheduleTemplateResponse,
    ApplyTemplateRequest,
)
from .utils import parse_time, check_slot_overlap

router = APIRouter(tags=["schedule-templates"])


@router.get("/templates", response_model=List[ScheduleTemplateResponse])
async def get_templates(
    channel_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список шаблонов расписания."""
    query = db.query(ScheduleTemplate).filter(
        or_(
            ScheduleTemplate.user_id == current_user.id,
            ScheduleTemplate.is_public == True
        )
    )
    
    if channel_id:
        query = query.filter(
            or_(
                ScheduleTemplate.channel_id == uuid.UUID(channel_id),
                ScheduleTemplate.channel_id == None
            )
        )
    
    templates = query.order_by(ScheduleTemplate.created_at.desc()).all()
    
    return [
        ScheduleTemplateResponse(
            id=str(t.id),
            name=t.name,
            description=t.description,
            channel_id=str(t.channel_id) if t.channel_id else None,
            slots=t.slots,
            is_public=t.is_public,
            created_at=t.created_at
        )
        for t in templates
    ]


@router.post("/templates", response_model=ScheduleTemplateResponse, status_code=201)
async def create_template(
    template_data: ScheduleTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать шаблон расписания."""
    template = ScheduleTemplate(
        user_id=current_user.id,
        channel_id=uuid.UUID(template_data.channel_id) if template_data.channel_id else None,
        name=template_data.name,
        description=template_data.description,
        slots=[s.model_dump() for s in template_data.slots],
        is_public=template_data.is_public
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return ScheduleTemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description,
        channel_id=str(template.channel_id) if template.channel_id else None,
        slots=template.slots,
        is_public=template.is_public,
        created_at=template.created_at
    )


@router.post("/templates/apply")
async def apply_template(
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Применить шаблон расписания на выбранные даты.
    
    Создает слоты из шаблона для каждой указанной даты.
    """
    template = db.query(ScheduleTemplate).filter(
        ScheduleTemplate.id == uuid.UUID(request.template_id)
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Проверка доступа к шаблону
    if template.user_id != current_user.id and not template.is_public:
        raise HTTPException(status_code=403, detail="Access denied to this template")
    
    created_count = 0
    skipped_count = 0
    
    for target_date in request.target_dates:
        for slot_data in template.slots:
            start_t = parse_time(slot_data["start_time"])
            end_t = parse_time(slot_data["end_time"])
            
            # Проверяем пересечения
            if check_slot_overlap(db, request.channel_id, target_date, start_t, end_t):
                skipped_count += 1
                continue
            
            playlist_id = slot_data.get("playlist_id")
            
            new_slot = ScheduleSlot(
                channel_id=uuid.UUID(request.channel_id),
                playlist_id=uuid.UUID(playlist_id) if playlist_id else None,
                start_date=target_date,
                start_time=start_t,
                end_time=end_t,
                title=slot_data.get("title"),
                color=slot_data.get("color", "#3B82F6"),
                created_by=current_user.id
            )
            
            db.add(new_slot)
            created_count += 1
    
    db.commit()
    
    return {
        "message": f"Applied template: created {created_count} slots, skipped {skipped_count}",
        "created": created_count,
        "skipped": skipped_count
    }


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить шаблон расписания."""
    template = db.query(ScheduleTemplate).filter(
        ScheduleTemplate.id == uuid.UUID(template_id),
        ScheduleTemplate.user_id == current_user.id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found or access denied")
    
    db.delete(template)
    db.commit()
    
    return {"message": "Template deleted", "id": template_id}
