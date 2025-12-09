"""
API endpoints для управления расписанием трансляций.

Функционал:
- CRUD для слотов расписания
- Шаблоны расписания (сохранение/применение)
- Копирование расписания между днями
- CRUD для плейлистов
"""

import uuid
from datetime import date, time, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
import logging
from sqlalchemy import and_, or_
from pydantic import BaseModel, ConfigDict, Field

from src.database import get_db
from src.models.schedule import ScheduleSlot, ScheduleTemplate, Playlist, PlaylistGroup, RepeatType
from src.models.telegram import Channel
from src.api.auth import get_current_user, require_admin
from src.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/schedule", tags=["schedule"])


# ==================== Pydantic Schemas ====================

class TimeSlotBase(BaseModel):
    """Базовый слот времени для шаблонов."""
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    playlist_id: Optional[str] = None
    title: Optional[str] = None
    color: str = "#3B82F6"


class ScheduleSlotCreate(BaseModel):
    """Создание слота расписания."""
    channel_id: str
    playlist_id: Optional[str] = None
    start_date: date
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"
    repeat_type: RepeatType = RepeatType.NONE
    repeat_days: Optional[List[int]] = None  # 0=Пн, 6=Вс
    repeat_until: Optional[date] = None
    title: Optional[str] = None
    description: Optional[str] = None
    color: str = "#3B82F6"
    priority: int = 0


class ScheduleSlotUpdate(BaseModel):
    """Обновление слота расписания."""
    playlist_id: Optional[str] = None
    start_date: Optional[date] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    repeat_type: Optional[RepeatType] = None
    repeat_days: Optional[List[int]] = None
    repeat_until: Optional[date] = None
    title: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


class ScheduleSlotResponse(BaseModel):
    """Ответ с данными слота."""
    id: str
    channel_id: str
    playlist_id: Optional[str]
    playlist_name: Optional[str] = None
    start_date: date
    start_time: str
    end_time: str
    repeat_type: RepeatType
    repeat_days: Optional[List[int]]
    repeat_until: Optional[date]
    title: Optional[str]
    description: Optional[str]
    color: str
    is_active: bool
    priority: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScheduleTemplateCreate(BaseModel):
    """Создание шаблона расписания."""
    name: str
    description: Optional[str] = None
    channel_id: Optional[str] = None
    slots: List[TimeSlotBase]
    is_public: bool = False


class ScheduleTemplateResponse(BaseModel):
    """Ответ с данными шаблона."""
    id: str
    name: str
    description: Optional[str]
    channel_id: Optional[str]
    slots: List[dict]
    is_public: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaylistCreate(BaseModel):
    """Создание плейлиста."""
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    channel_id: Optional[str] = None
    group_id: Optional[str] = None
    color: str = "#8B5CF6"
    source_type: str = "manual"
    source_url: Optional[str] = None
    items: List[dict] = []
    is_shuffled: bool = False


class PlaylistUpdate(BaseModel):
    """Обновление плейлиста."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    group_id: Optional[str] = None
    position: Optional[int] = None
    items: Optional[List[dict]] = None
    is_active: Optional[bool] = None
    is_shuffled: Optional[bool] = None


class PlaylistResponse(BaseModel):
    """Ответ с данными плейлиста."""
    id: str
    name: str
    description: Optional[str]
    channel_id: Optional[str]
    group_id: Optional[str] = None
    position: int = 0
    color: str
    source_type: str
    source_url: Optional[str]
    items: List[dict]
    items_count: int
    total_duration: int
    is_active: bool
    is_shuffled: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== Playlist Group Schemas ====================

class PlaylistGroupCreate(BaseModel):
    """Создание группы плейлистов."""
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    channel_id: Optional[str] = None
    color: str = "#6366F1"
    icon: str = "folder"


class PlaylistGroupUpdate(BaseModel):
    """Обновление группы плейлистов."""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    position: Optional[int] = None
    is_expanded: Optional[bool] = None
    is_active: Optional[bool] = None


class PlaylistGroupResponse(BaseModel):
    """Ответ с данными группы плейлистов."""
    id: str
    name: str
    description: Optional[str]
    channel_id: Optional[str]
    color: str
    icon: str
    position: int
    is_expanded: bool
    is_active: bool
    playlists_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaylistGroupWithPlaylistsResponse(PlaylistGroupResponse):
    """Группа с вложенными плейлистами."""
    playlists: List[PlaylistResponse] = []


class BulkCopyRequest(BaseModel):
    """Запрос на копирование расписания."""
    source_date: date
    target_dates: List[date]
    channel_id: str


class ApplyTemplateRequest(BaseModel):
    """Запрос на применение шаблона."""
    template_id: str
    channel_id: str
    target_dates: List[date]


class CalendarViewResponse(BaseModel):
    """Ответ для календарного представления."""
    date: date
    slots: List[ScheduleSlotResponse]
    has_conflicts: bool = False


# ==================== Helper Functions ====================

def parse_time(time_str: str) -> time:
    """Парсинг времени из строки HH:MM."""
    try:
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail=f"Invalid time format: {time_str}. Expected HH:MM")


def format_time(t: time) -> str:
    """Форматирование времени в строку HH:MM."""
    return t.strftime("%H:%M")


def check_slot_overlap(
    db: Session, 
    channel_id: str, 
    start_date: date, 
    start_time: time, 
    end_time: time,
    exclude_id: Optional[str] = None
) -> bool:
    """Проверка пересечения слотов."""
    query = db.query(ScheduleSlot).filter(
        ScheduleSlot.channel_id == uuid.UUID(channel_id),
        ScheduleSlot.start_date == start_date,
        ScheduleSlot.is_active == True,
        or_(
            # Новый слот начинается внутри существующего
            and_(
                ScheduleSlot.start_time <= start_time,
                ScheduleSlot.end_time > start_time
            ),
            # Новый слот заканчивается внутри существующего
            and_(
                ScheduleSlot.start_time < end_time,
                ScheduleSlot.end_time >= end_time
            ),
            # Новый слот полностью покрывает существующий
            and_(
                ScheduleSlot.start_time >= start_time,
                ScheduleSlot.end_time <= end_time
            )
        )
    )
    if exclude_id:
        query = query.filter(ScheduleSlot.id != uuid.UUID(exclude_id))
    return query.first() is not None


# ==================== Schedule Slots API ====================

@router.get("/slots", response_model=List[ScheduleSlotResponse])
async def get_schedule_slots(
    channel_id: str,
    start_date: date = Query(..., description="Начало периода (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Конец периода (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Получить расписание для канала за период.
    
    Возвращает все слоты в указанном диапазоне дат.
    """
    # Проверка доступа к каналу
    channel = db.query(Channel).filter(Channel.id == uuid.UUID(channel_id)).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
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
    Получить календарное представление расписания на месяц.
    
    Возвращает слоты сгруппированные по дням.
    """
    from calendar import monthrange
    
    # Определяем первый и последний день месяца
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    
    # Получаем ВСЕ активные слоты канала (фильтрацию по датам сделаем в Python для надежности)
    slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.channel_id == uuid.UUID(channel_id),
        ScheduleSlot.is_active == True
    ).order_by(ScheduleSlot.start_time).all()
    
    import sys
    sys.stderr.write(f"[CALENDAR DEBUG] Fetching for channel {channel_id}, {year}-{month}: found {len(slots)} active slots\n")
    sys.stderr.flush()
    print(f"[CALENDAR DEBUG] Fetching for channel {channel_id}, {year}-{month}: found {len(slots)} active slots", flush=True)
    logger.info(f"[CALENDAR DEBUG] Fetching for channel {channel_id}, {year}-{month}: found {len(slots)} active slots")
    
    # Формируем ответ для всех дней месяца
    result = []
    current_day = first_day
    
    while current_day <= last_day:
        day_slots = []
        
        for slot in slots:
            # Проверяем, попадает ли слот на этот день
            is_match = False
            
            # Базовая проверка диапазона дат для повторяющихся
            if slot.repeat_type != RepeatType.NONE:
                if slot.start_date > current_day:
                    continue
                if slot.repeat_until and slot.repeat_until < current_day:
                    continue
            
            if slot.repeat_type == RepeatType.NONE:
                is_match = (slot.start_date == current_day)
                
            elif slot.repeat_type == RepeatType.DAILY:
                is_match = True
                
            elif slot.repeat_type == RepeatType.WEEKLY:
                is_match = (slot.start_date.weekday() == current_day.weekday())
                
            elif slot.repeat_type == RepeatType.WEEKDAYS:
                is_match = (current_day.weekday() < 5) # 0-4 are Mon-Fri
                
            elif slot.repeat_type == RepeatType.WEEKENDS:
                is_match = (current_day.weekday() >= 5) # 5-6 are Sat-Sun
                
            elif slot.repeat_type == RepeatType.CUSTOM:
                if slot.repeat_days:
                    # Ensure repeat_days is a list of integers
                    r_days = slot.repeat_days
                    if isinstance(r_days, list):
                        is_match = (current_day.weekday() in r_days)
            
            if is_match:
                playlist_name = None
                if slot.playlist_id:
                     p = db.query(Playlist).filter(Playlist.id == slot.playlist_id).first()
                     playlist_name = p.name if p else None

                day_slots.append(ScheduleSlotResponse(
                    id=str(slot.id),
                    channel_id=str(slot.channel_id),
                    playlist_id=str(slot.playlist_id) if slot.playlist_id else None,
                    playlist_name=playlist_name,
                    start_date=current_day, # Use current day for display
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
        
        # Сортировка слотов дня по времени
        day_slots.sort(key=lambda x: x.start_time)

        # Проверяем конфликты (пересечения)
        has_conflicts = False
        for i, s1 in enumerate(day_slots):
            for s2 in day_slots[i+1:]:
                t1_start = parse_time(s1.start_time)
                t1_end = parse_time(s1.end_time)
                t2_start = parse_time(s2.start_time)
                t2_end = parse_time(s2.end_time)
                if t1_start < t2_end and t2_start < t1_end:
                    has_conflicts = True
                    break
            if has_conflicts:
                break
        
        result.append(CalendarViewResponse(
            date=current_day,
            slots=day_slots,
            has_conflicts=has_conflicts
        ))
        current_day += timedelta(days=1)
    
    import sys
    total_slots_count = sum(len(d.slots) for d in result)
    sys.stderr.write(f"[CALENDAR DEBUG] Returning {len(result)} days, total slots: {total_slots_count}\n")
    sys.stderr.flush()
    print(f"[CALENDAR DEBUG] Returning {len(result)} days, total slots across all days: {total_slots_count}", flush=True)
    logger.info(f"[CALENDAR DEBUG] Returning {len(result)} days, total slots across all days: {total_slots_count}")
    
    # TEMPORARY DEBUG: Force error to see values (check channel_id type)
    debug_msg = f"DEBUG: channel_id={channel_id} (type={type(channel_id)}), Found {len(slots)} total slots, returning {len(result)} days with {total_slots_count} total slots"
    raise HTTPException(status_code=500, detail=debug_msg)
    
    return result


@router.get("/debug/calendar")
async def debug_calendar_view(
    channel_id: str,
    year: int = Query(2025),
    month: int = Query(12),
    db: Session = Depends(get_db)
):
    """Temporary debug endpoint without auth to test calendar logic."""
    import sys
    from calendar import monthrange
    
    first_day = date(year, month, 1)
    last_day = date(year, month, monthrange(year, month)[1])
    
    slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.channel_id == uuid.UUID(channel_id),
        ScheduleSlot.is_active == True
    ).order_by(ScheduleSlot.start_time).all()
    
    debug_info = {
        "channel_id": channel_id,
        "year": year,
        "month": month,
        "first_day": str(first_day),
        "last_day": str(last_day),
        "total_active_slots": len(slots),
        "slots_detail": []
    }
    
    for slot in slots:
        debug_info["slots_detail"].append({
            "id": str(slot.id),
            "start_date": str(slot.start_date),
            "start_time": str(slot.start_time),
            "end_time": str(slot.end_time),
            "repeat_type": str(slot.repeat_type),
            "repeat_until": str(slot.repeat_until) if slot.repeat_until else None
        })
    
    # Test matching logic for December 11 and 12
    test_dates = [date(2025, 12, 11), date(2025, 12, 12)]
    matching_results = {}
    
    for test_day in test_dates:
        matching_slots = []
        for slot in slots:
            is_match = False
            
            if slot.repeat_type != RepeatType.NONE:
                if slot.start_date > test_day:
                    continue
                if slot.repeat_until and slot.repeat_until < test_day:
                    continue
            
            if slot.repeat_type == RepeatType.NONE:
                is_match = (slot.start_date == test_day)
            elif slot.repeat_type == RepeatType.DAILY:
                is_match = True
            
            if is_match:
                matching_slots.append(str(slot.id))
        
        matching_results[str(test_day)] = matching_slots
    
    debug_info["matching_test"] = matching_results
    
    return debug_info


@router.get("/expand", response_model=List[ScheduleSlotResponse])
async def expand_schedule(
    channel_id: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Возвращает развёрнутые слоты (например, развернуть повторяющиеся слоты в отдельные даты)."""
    # Validate channel
    channel = db.query(Channel).filter(Channel.id == uuid.UUID(channel_id)).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    slots = db.query(ScheduleSlot).filter(
        ScheduleSlot.channel_id == uuid.UUID(channel_id),
        ScheduleSlot.is_active == True
    ).all()

    result = []
    for slot in slots:
        # single occurrence
        if slot.repeat_type == RepeatType.NONE:
            if slot.start_date >= start_date and slot.start_date <= end_date:
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
            # build occurrences
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
            # For other types (weekly/custom), we may extend support later; skip for now
            continue

    # sort by date/time
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
    
    # Disallow zero-length or reversed ranges (end must be after start)
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
    update_data = slot_data.dict(exclude_unset=True)
    
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
    
    # Return 204 No Content
    return Response(status_code=204)


# ==================== Bulk Operations ====================

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
    
    # If no source slots found, return success with zero created entries (tests expect this)
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


# ==================== Templates API ====================

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
        slots=[s.dict() for s in template_data.slots],
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


# ==================== Playlists API ====================

@router.get("/playlists", response_model=List[PlaylistResponse])
async def get_playlists(
    channel_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список плейлистов."""
    # SuperAdmin и Admin видят все плейлисты
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        query = db.query(Playlist)
    else:
        query = db.query(Playlist).filter(Playlist.user_id == current_user.id)
    
    if channel_id:
        query = query.filter(
            or_(
                Playlist.channel_id == uuid.UUID(channel_id),
                Playlist.channel_id == None
            )
        )
    
    playlists = query.filter(Playlist.is_active == True).order_by(Playlist.position, Playlist.name).all()
    
    return [
        PlaylistResponse(
            id=str(p.id),
            name=p.name,
            description=p.description,
            channel_id=str(p.channel_id) if p.channel_id else None,
            group_id=str(p.group_id) if p.group_id else None,
            position=p.position or 0,
            color=p.color,
            source_type=p.source_type,
            source_url=p.source_url,
            items=p.items or [],
            items_count=p.items_count,
            total_duration=p.total_duration,
            is_active=p.is_active,
            is_shuffled=p.is_shuffled,
            created_at=p.created_at
        )
        for p in playlists
    ]


@router.post("/playlists", response_model=PlaylistResponse, status_code=201)
async def create_playlist(
    playlist_data: PlaylistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новый плейлист."""
    # Вычисляем статистику
    items = playlist_data.items or []
    total_duration = sum(item.get("duration", 0) for item in items)
    
    playlist = Playlist(
        user_id=current_user.id,
        channel_id=uuid.UUID(playlist_data.channel_id) if playlist_data.channel_id else None,
        name=playlist_data.name,
        description=playlist_data.description,
        color=playlist_data.color,
        source_type=playlist_data.source_type,
        source_url=playlist_data.source_url,
        items=items,
        items_count=len(items),
        total_duration=total_duration,
        is_shuffled=playlist_data.is_shuffled
    )
    
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    
    return PlaylistResponse(
        id=str(playlist.id),
        name=playlist.name,
        description=playlist.description,
        channel_id=str(playlist.channel_id) if playlist.channel_id else None,
        color=playlist.color,
        source_type=playlist.source_type,
        source_url=playlist.source_url,
        items=playlist.items or [],
        items_count=playlist.items_count,
        total_duration=playlist.total_duration,
        is_active=playlist.is_active,
        is_shuffled=playlist.is_shuffled,
        created_at=playlist.created_at
    )


@router.put("/playlists/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: str,
    playlist_data: PlaylistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить плейлист."""
    playlist = db.query(Playlist).filter(
        Playlist.id == uuid.UUID(playlist_id),
        Playlist.user_id == current_user.id
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    update_data = playlist_data.dict(exclude_unset=True)
    
    # Пересчитываем статистику при обновлении items
    if "items" in update_data:
        items = update_data["items"] or []
        update_data["items_count"] = len(items)
        update_data["total_duration"] = sum(item.get("duration", 0) for item in items)
    
    for key, value in update_data.items():
        setattr(playlist, key, value)
    
    db.commit()
    db.refresh(playlist)
    
    return PlaylistResponse(
        id=str(playlist.id),
        name=playlist.name,
        description=playlist.description,
        channel_id=str(playlist.channel_id) if playlist.channel_id else None,
        color=playlist.color,
        source_type=playlist.source_type,
        source_url=playlist.source_url,
        items=playlist.items or [],
        items_count=playlist.items_count,
        total_duration=playlist.total_duration,
        is_active=playlist.is_active,
        is_shuffled=playlist.is_shuffled,
        created_at=playlist.created_at
    )


@router.delete("/playlists/{playlist_id}", status_code=204)
async def delete_playlist(
    playlist_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить плейлист (soft delete)."""
    playlist = db.query(Playlist).filter(
        Playlist.id == uuid.UUID(playlist_id),
        Playlist.user_id == current_user.id
    ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    # Prevent deletion if playlist is used in active schedule slots
    used = db.query(ScheduleSlot).filter(ScheduleSlot.playlist_id == playlist.id, ScheduleSlot.is_active == True).first()
    if used:
        raise HTTPException(status_code=409, detail="Playlist is currently in use")

    # Soft delete
    playlist.is_active = False
    db.commit()

    # Soft delete: return 204 No Content
    return Response(status_code=204)


# ==================== Playlist Groups API ====================

@router.get("/groups", response_model=List[PlaylistGroupResponse])
async def get_playlist_groups(
    channel_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список групп плейлистов."""
    # SuperAdmin и Admin видят все группы
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        query = db.query(PlaylistGroup)
    else:
        query = db.query(PlaylistGroup).filter(PlaylistGroup.user_id == current_user.id)
    
    if channel_id:
        query = query.filter(
            or_(
                PlaylistGroup.channel_id == uuid.UUID(channel_id),
                PlaylistGroup.channel_id == None
            )
        )
    
    groups = query.filter(PlaylistGroup.is_active == True).order_by(PlaylistGroup.position, PlaylistGroup.name).all()
    
    return [
        PlaylistGroupResponse(
            id=str(g.id),
            name=g.name,
            description=g.description,
            channel_id=str(g.channel_id) if g.channel_id else None,
            color=g.color,
            icon=g.icon or "folder",
            position=g.position or 0,
            is_expanded=g.is_expanded if g.is_expanded is not None else True,
            is_active=g.is_active,
            playlists_count=len([p for p in g.playlists if p.is_active]),
            created_at=g.created_at
        )
        for g in groups
    ]


@router.get("/groups/with-playlists", response_model=List[PlaylistGroupWithPlaylistsResponse])
async def get_playlist_groups_with_playlists(
    channel_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить группы с вложенными плейлистами (для UI)."""
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        query = db.query(PlaylistGroup)
    else:
        query = db.query(PlaylistGroup).filter(PlaylistGroup.user_id == current_user.id)
    
    if channel_id:
        query = query.filter(
            or_(
                PlaylistGroup.channel_id == uuid.UUID(channel_id),
                PlaylistGroup.channel_id == None
            )
        )
    
    groups = query.filter(PlaylistGroup.is_active == True).order_by(PlaylistGroup.position, PlaylistGroup.name).all()
    
    result = []
    for g in groups:
        active_playlists = [p for p in g.playlists if p.is_active]
        result.append(PlaylistGroupWithPlaylistsResponse(
            id=str(g.id),
            name=g.name,
            description=g.description,
            channel_id=str(g.channel_id) if g.channel_id else None,
            color=g.color,
            icon=g.icon or "folder",
            position=g.position or 0,
            is_expanded=g.is_expanded if g.is_expanded is not None else True,
            is_active=g.is_active,
            playlists_count=len(active_playlists),
            created_at=g.created_at,
            playlists=[
                PlaylistResponse(
                    id=str(p.id),
                    name=p.name,
                    description=p.description,
                    channel_id=str(p.channel_id) if p.channel_id else None,
                    group_id=str(p.group_id) if p.group_id else None,
                    position=p.position or 0,
                    color=p.color,
                    source_type=p.source_type,
                    source_url=p.source_url,
                    items=p.items or [],
                    items_count=p.items_count,
                    total_duration=p.total_duration,
                    is_active=p.is_active,
                    is_shuffled=p.is_shuffled,
                    created_at=p.created_at
                )
                for p in sorted(active_playlists, key=lambda x: (x.position or 0, x.name))
            ]
        ))
    
    return result


@router.post("/groups", response_model=PlaylistGroupResponse, status_code=201)
async def create_playlist_group(
    group_data: PlaylistGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать группу плейлистов."""
    max_pos = db.query(PlaylistGroup).filter(
        PlaylistGroup.user_id == current_user.id,
        PlaylistGroup.is_active == True
    ).count()
    
    group = PlaylistGroup(
        user_id=current_user.id,
        channel_id=uuid.UUID(group_data.channel_id) if group_data.channel_id else None,
        name=group_data.name,
        description=group_data.description,
        color=group_data.color,
        icon=group_data.icon,
        position=max_pos
    )
    
    db.add(group)
    db.commit()
    db.refresh(group)
    
    return PlaylistGroupResponse(
        id=str(group.id),
        name=group.name,
        description=group.description,
        channel_id=str(group.channel_id) if group.channel_id else None,
        color=group.color,
        icon=group.icon or "folder",
        position=group.position or 0,
        is_expanded=True,
        is_active=True,
        playlists_count=0,
        created_at=group.created_at
    )


@router.put("/groups/{group_id}", response_model=PlaylistGroupResponse)
async def update_playlist_group(
    group_id: str,
    group_data: PlaylistGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить группу плейлистов."""
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        group = db.query(PlaylistGroup).filter(PlaylistGroup.id == uuid.UUID(group_id)).first()
    else:
        group = db.query(PlaylistGroup).filter(
            PlaylistGroup.id == uuid.UUID(group_id),
            PlaylistGroup.user_id == current_user.id
        ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    update_data = group_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(group, key, value)
    
    db.commit()
    db.refresh(group)
    
    return PlaylistGroupResponse(
        id=str(group.id),
        name=group.name,
        description=group.description,
        channel_id=str(group.channel_id) if group.channel_id else None,
        color=group.color,
        icon=group.icon or "folder",
        position=group.position or 0,
        is_expanded=group.is_expanded if group.is_expanded is not None else True,
        is_active=group.is_active,
        playlists_count=len([p for p in group.playlists if p.is_active]),
        created_at=group.created_at
    )


@router.delete("/groups/{group_id}", status_code=204)
async def delete_playlist_group(
    group_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить группу (soft delete). Плейлисты переносятся в ungrouped."""
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        group = db.query(PlaylistGroup).filter(PlaylistGroup.id == uuid.UUID(group_id)).first()
    else:
        group = db.query(PlaylistGroup).filter(
            PlaylistGroup.id == uuid.UUID(group_id),
            PlaylistGroup.user_id == current_user.id
        ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    db.query(Playlist).filter(Playlist.group_id == group.id).update({Playlist.group_id: None})
    group.is_active = False
    db.commit()
    
    return Response(status_code=204)


@router.post("/playlists/{playlist_id}/move-to-group", response_model=PlaylistResponse)
async def move_playlist_to_group(
    playlist_id: str,
    group_id: Optional[str] = None,
    position: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Переместить плейлист в группу."""
    if current_user.role.upper() in ("SUPERADMIN", "ADMIN"):
        playlist = db.query(Playlist).filter(Playlist.id == uuid.UUID(playlist_id)).first()
    else:
        playlist = db.query(Playlist).filter(
            Playlist.id == uuid.UUID(playlist_id),
            Playlist.user_id == current_user.id
        ).first()
    
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    
    if group_id:
        group = db.query(PlaylistGroup).filter(
            PlaylistGroup.id == uuid.UUID(group_id),
            PlaylistGroup.is_active == True
        ).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        playlist.group_id = uuid.UUID(group_id)
    else:
        playlist.group_id = None
    
    if position is not None:
        playlist.position = position
    
    db.commit()
    db.refresh(playlist)
    
    return PlaylistResponse(
        id=str(playlist.id),
        name=playlist.name,
        description=playlist.description,
        channel_id=str(playlist.channel_id) if playlist.channel_id else None,
        group_id=str(playlist.group_id) if playlist.group_id else None,
        position=playlist.position or 0,
        color=playlist.color,
        source_type=playlist.source_type,
        source_url=playlist.source_url,
        items=playlist.items or [],
        items_count=playlist.items_count,
        total_duration=playlist.total_duration,
        is_active=playlist.is_active,
        is_shuffled=playlist.is_shuffled,
        created_at=playlist.created_at
    )

