"""
Utility functions для Schedule API.
"""

import uuid
from datetime import time
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.models.schedule import ScheduleSlot


def parse_time(time_str: str) -> time:
    """
    Парсинг времени из строки HH:MM.
    
    Args:
        time_str: Время в формате "HH:MM"
        
    Returns:
        datetime.time объект
        
    Raises:
        HTTPException: Если формат неверный
    """
    try:
        parts = time_str.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid time format: {time_str}. Expected HH:MM"
        )


def format_time(t: time) -> str:
    """
    Форматирование времени в строку HH:MM.
    
    Args:
        t: datetime.time объект
        
    Returns:
        Строка в формате "HH:MM"
    """
    return t.strftime("%H:%M")


def check_slot_overlap(
    db: Session, 
    channel_id: str, 
    start_date, 
    start_time: time, 
    end_time: time,
    exclude_id: Optional[str] = None
) -> bool:
    """
    Проверка пересечения слотов.
    
    Проверяет, есть ли активные слоты на канале, 
    которые пересекаются с указанным временным диапазоном.
    
    Args:
        db: Сессия базы данных
        channel_id: ID канала
        start_date: Дата слота
        start_time: Время начала
        end_time: Время окончания
        exclude_id: ID слота для исключения (при обновлении)
        
    Returns:
        True если есть пересечение, False иначе
    """
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
