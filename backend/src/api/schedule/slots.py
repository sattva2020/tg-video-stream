"""
Эндпоинты для работы со слотами расписания.

Включает:
- CRUD операции для ScheduleSlot
- Календарный вид
- Развертывание повторяющихся слотов
- Массовое копирование
"""
import uuid
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.models.schedule import ScheduleSlot, RepeatType, Playlist
from src.models.telegram import Channel
from src.api.auth import get_current_user, require_admin

from .schemas import (
    ScheduleSlotCreate,
    ScheduleSlotUpdate,
    ScheduleSlotResponse,
    CalendarViewResponse,
    BulkCopyRequest,
)
from .utils import parse_time, format_time, check_slot_overlap

router = APIRouter(tags=["schedule-slots"])


@router.get("/slots", response_model=List[ScheduleSlotResponse])
async def get_schedule_slots(
    channel_id: str,
    start_date: date = Query(..., description="Начальная дата диапазона"),
    end_date: date = Query(..., description="Конечная дата диапазона"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить слоты расписания для канала в указанном диапазоне дат.
    
    Возвращает активные слоты, отсортированные по дате и времени.
    """
    slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.channel_id == uuid.UUID(channel_id),
        ScheduleSlot.start_date >= start_date,
        ScheduleSlot.start_date <= end_date,
        ScheduleSlot.is_active == True
    ).order_by(ScheduleSlot.start_date, ScheduleSlot.start_time).all()
    
    result = []
    for slot in slots:
        playlist_name = None
        if slot.playlist_id:
            playlist = db.query(Playlist).filter(Playlist.id == slot.playlist_id).first()
            playlist_name = playlist.name if playlist else None
        
        result.append(ScheduleSlotResponse(
            id=str(slot.id),
            channel_id=str(slot.channel_id),
            playlist_id=str(slot.playlist_id) if slot.playlist_id else None,
            playlist_name=playlist_name,
            start_date=slot.start_date,
            start_time=format_time(slot.start_time),
            end_time=format_time(slot.end_time),
            repeat_type=slot.repeat_type,
            repeat_days=slot.repeat_days,
            repeat_until=slot.repeat_until,
            title=slot.title,
            description=slot.description,
            color=slot.color,
            is_active=slot.is_active,
            priority=slot.priority,
            created_at=slot.created_at
        ))
    
    return result


@router.get("/calendar", response_model=List[CalendarViewResponse])
async def get_calendar_view(
    channel_id: str,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить календарный вид расписания для месяца.
    
    Возвращает список дней с количеством слотов и признаком конфликтов.
    """
    from calendar import monthrange
    
    _, days_in_month = monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, days_in_month)
    
    slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.channel_id == uuid.UUID(channel_id),
        ScheduleSlot.start_date >= start_date,
        ScheduleSlot.start_date <= end_date,
        ScheduleSlot.is_active == True
    ).all()
    
    # Группировка по дням
    days_data = {}
    for d in range(1, days_in_month + 1):
        current = date(year, month, d)
        days_data[current] = {"slots": [], "has_conflict": False}
    
    for slot in slots:
        if slot.start_date in days_data:
            days_data[slot.start_date]["slots"].append(slot)
    
    # Проверка конфликтов
    for day_date, data in days_data.items():
        day_slots = data["slots"]
        for i, slot1 in enumerate(day_slots):
            for slot2 in day_slots[i + 1:]:
                # Проверяем пересечение времени
                if not (slot1.end_time <= slot2.start_time or slot2.end_time <= slot1.start_time):
                    data["has_conflict"] = True
                    break
            if data["has_conflict"]:
                break
    
    return [
        CalendarViewResponse(
            date=day_date,
            slots_count=len(data["slots"]),
            has_conflicts=data["has_conflict"]
        )
        for day_date, data in sorted(days_data.items())
    ]


@router.get("/expand", response_model=List[ScheduleSlotResponse])
async def expand_schedule(
    channel_id: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Развернуть расписание с учетом повторяющихся слотов.
    
    Для повторяющихся слотов создает виртуальные копии на каждую дату
    в указанном диапазоне согласно правилам повторения.
    """
    # Получаем все слоты, которые могут попасть в диапазон
    slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.channel_id == uuid.UUID(channel_id),
        ScheduleSlot.is_active == True,
        or_(
            # Одноразовые слоты в диапазоне
            and_(
                ScheduleSlot.repeat_type == RepeatType.NONE,
                ScheduleSlot.start_date >= start_date,
                ScheduleSlot.start_date <= end_date
            ),
            # Повторяющиеся слоты, начавшиеся до конца диапазона
            and_(
                ScheduleSlot.repeat_type != RepeatType.NONE,
                ScheduleSlot.start_date <= end_date
            )
        )
    ).all()
    
    result = []
    
    for slot in slots:
        if slot.repeat_type == RepeatType.NONE:
            # Одноразовый слот
            if start_date <= slot.start_date <= end_date:
                result.append(ScheduleSlotResponse(
                    id=str(slot.id),
                    channel_id=str(slot.channel_id),
                    playlist_id=str(slot.playlist_id) if slot.playlist_id else None,
                    playlist_name=(db.query(Playlist).filter(Playlist.id == slot.playlist_id).first().name
                                   if slot.playlist_id else None),
                    start_date=slot.start_date,
                    start_time=format_time(slot.start_time),
                    end_time=format_time(slot.end_time),
                    repeat_type=slot.repeat_type,
                    repeat_days=slot.repeat_days,
                    repeat_until=slot.repeat_until,
                    title=slot.title,
                    description=slot.description,
                    color=slot.color,
                    is_active=slot.is_active,
                    priority=slot.priority,
                    created_at=slot.created_at
                ))
        elif slot.repeat_type == RepeatType.DAILY:
            # Ежедневное повторение
            start_occ = max(slot.start_date, start_date)
            last_occ = slot.repeat_until if slot.repeat_until else end_date
            last_occ = min(last_occ, end_date)
            current = start_occ
            while current <= last_occ:
                result.append(ScheduleSlotResponse(
                    id=str(slot.id),
                    channel_id=str(slot.channel_id),
                    playlist_id=str(slot.playlist_id) if slot.playlist_id else None,
                    playlist_name=(db.query(Playlist).filter(Playlist.id == slot.playlist_id).first().name
                                   if slot.playlist_id else None),
                    start_date=current,
                    start_time=format_time(slot.start_time),
                    end_time=format_time(slot.end_time),
                    repeat_type=slot.repeat_type,
                    repeat_days=slot.repeat_days,
                    repeat_until=slot.repeat_until,
                    title=slot.title,
                    description=slot.description,
                    color=slot.color,
                    is_active=slot.is_active,
                    priority=slot.priority,
                    created_at=slot.created_at
                ))
                current = current + timedelta(days=1)
        else:
            # Другие типы повторения (weekly/custom) - пропускаем пока
            continue

    # Сортировка по дате/времени
    result.sort(key=lambda r: (r.start_date, r.start_time))
    return result


@router.post("/slots", response_model=ScheduleSlotResponse, status_code=201)
async def create_schedule_slot(
    slot_data: ScheduleSlotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Создать новый слот расписания."""
    # Проверка канала
    channel = db.query(Channel).filter(Channel.id == uuid.UUID(slot_data.channel_id)).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Парсинг времени
    start_t = parse_time(slot_data.start_time)
    end_t = parse_time(slot_data.end_time)
    
    # Проверка: end должен быть после start
    if start_t >= end_t:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    
    # Проверка пересечений
    if check_slot_overlap(db, slot_data.channel_id, slot_data.start_date, start_t, end_t):
        raise HTTPException(status_code=409, detail="Time slot overlaps with existing schedule")
    
    # Проверка плейлиста
    playlist_name = None
    if slot_data.playlist_id:
        playlist = db.query(Playlist).filter(Playlist.id == uuid.UUID(slot_data.playlist_id)).first()
        if not playlist:
            raise HTTPException(status_code=404, detail="Playlist not found")
        playlist_name = playlist.name
    
    slot = ScheduleSlot(
        channel_id=uuid.UUID(slot_data.channel_id),
        playlist_id=uuid.UUID(slot_data.playlist_id) if slot_data.playlist_id else None,
        start_date=slot_data.start_date,
        start_time=start_t,
        end_time=end_t,
        repeat_type=slot_data.repeat_type,
        repeat_days=slot_data.repeat_days,
        repeat_until=slot_data.repeat_until,
        title=slot_data.title,
        description=slot_data.description,
        color=slot_data.color,
        priority=slot_data.priority,
        created_by=current_user.id
    )
    
    db.add(slot)
    db.commit()
    db.refresh(slot)
    
    return ScheduleSlotResponse(
        id=str(slot.id),
        channel_id=str(slot.channel_id),
        playlist_id=str(slot.playlist_id) if slot.playlist_id else None,
        playlist_name=playlist_name,
        start_date=slot.start_date,
        start_time=format_time(slot.start_time),
        end_time=format_time(slot.end_time),
        repeat_type=slot.repeat_type,
        repeat_days=slot.repeat_days,
        repeat_until=slot.repeat_until,
        title=slot.title,
        description=slot.description,
        color=slot.color,
        is_active=slot.is_active,
        priority=slot.priority,
        created_at=slot.created_at
    )


@router.put("/slots/{slot_id}", response_model=ScheduleSlotResponse)
async def update_schedule_slot(
    slot_id: str,
    slot_data: ScheduleSlotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Обновить слот расписания."""
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == uuid.UUID(slot_id)).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Schedule slot not found")
    
    # Обновление полей
    update_data = slot_data.model_dump(exclude_unset=True)
    
    if "start_time" in update_data:
        update_data["start_time"] = parse_time(update_data["start_time"])
    if "end_time" in update_data:
        update_data["end_time"] = parse_time(update_data["end_time"])
    if "playlist_id" in update_data and update_data["playlist_id"]:
        update_data["playlist_id"] = uuid.UUID(update_data["playlist_id"])
    
    # Проверка пересечений при изменении времени
    new_start = update_data.get("start_time", slot.start_time)
    new_end = update_data.get("end_time", slot.end_time)
    new_date = update_data.get("start_date", slot.start_date)
    
    if check_slot_overlap(db, str(slot.channel_id), new_date, new_start, new_end, exclude_id=slot_id):
        raise HTTPException(status_code=409, detail="Time slot overlaps with existing schedule")
    
    for key, value in update_data.items():
        setattr(slot, key, value)
    
    db.commit()
    db.refresh(slot)
    
    playlist_name = None
    if slot.playlist_id:
        playlist = db.query(Playlist).filter(Playlist.id == slot.playlist_id).first()
        playlist_name = playlist.name if playlist else None
    
    return ScheduleSlotResponse(
        id=str(slot.id),
        channel_id=str(slot.channel_id),
        playlist_id=str(slot.playlist_id) if slot.playlist_id else None,
        playlist_name=playlist_name,
        start_date=slot.start_date,
        start_time=format_time(slot.start_time),
        end_time=format_time(slot.end_time),
        repeat_type=slot.repeat_type,
        repeat_days=slot.repeat_days,
        repeat_until=slot.repeat_until,
        title=slot.title,
        description=slot.description,
        color=slot.color,
        is_active=slot.is_active,
        priority=slot.priority,
        created_at=slot.created_at
    )


@router.delete("/slots/{slot_id}", status_code=204)
async def delete_schedule_slot(
    slot_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Удалить слот расписания."""
    slot = db.query(ScheduleSlot).filter(ScheduleSlot.id == uuid.UUID(slot_id)).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Schedule slot not found")
    
    db.delete(slot)
    db.commit()
    
    return Response(status_code=204)


@router.post("/copy")
async def copy_schedule(
    request: BulkCopyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Копировать расписание с одного дня на другие.
    
    Создает копии всех слотов источника на указанные целевые даты.
    Пропускает слоты, которые конфликтуют с существующими.
    """
    # Получаем слоты источника
    source_slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.channel_id == uuid.UUID(request.channel_id),
        ScheduleSlot.start_date == request.source_date,
        ScheduleSlot.is_active == True
    ).all()
    
    # Если нет исходных слотов - возвращаем успех с нулевым счетчиком
    if not source_slots:
        return {
            "message": "No slots found for source date",
            "created": 0,
            "skipped": 0,
            "slots": []
        }
    
    created_count = 0
    skipped_count = 0
    created_slots = []
    
    for target_date in request.target_dates:
        if target_date == request.source_date:
            continue
            
        for source_slot in source_slots:
            # Проверяем пересечения
            if check_slot_overlap(
                db, request.channel_id, target_date, 
                source_slot.start_time, source_slot.end_time
            ):
                skipped_count += 1
                continue
            
            new_slot = ScheduleSlot(
                channel_id=source_slot.channel_id,
                playlist_id=source_slot.playlist_id,
                start_date=target_date,
                start_time=source_slot.start_time,
                end_time=source_slot.end_time,
                repeat_type=RepeatType.NONE,  # Копии не повторяются
                title=source_slot.title,
                description=source_slot.description,
                color=source_slot.color,
                priority=source_slot.priority,
                created_by=current_user.id
            )
            
            db.add(new_slot)
            created_count += 1
            created_slots.append({
                "date": str(target_date),
                "start_time": format_time(source_slot.start_time),
                "end_time": format_time(source_slot.end_time)
            })
    
    db.commit()
    
    return {
        "message": f"Copied {created_count} slots, skipped {skipped_count} due to conflicts",
        "created": created_count,
        "skipped": skipped_count,
        "slots": created_slots
    }
