# -*- coding: utf-8 -*-
"""
Утилиты для работы с датой и временем.
Устраняет дублирование паттернов datetime.now(timezone.utc) и timedelta.

Пример использования:
    from src.lib.time_utils import utc_now, add_days
    
    # Текущее время UTC
    now = utc_now()
    
    # Через 7 дней
    expires_at = add_days(7)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    Возвращает текущее время в UTC с timezone-aware.
    
    Замена для deprecated datetime.utcnow().
    
    Returns:
        datetime объект с timezone.utc
    """
    return datetime.now(timezone.utc)


def add_days(days: int, from_dt: Optional[datetime] = None) -> datetime:
    """
    Добавляет дни к указанной дате.
    
    Args:
        days: Количество дней (может быть отрицательным)
        from_dt: Базовая дата (по умолчанию utc_now())
        
    Returns:
        Новая дата
    """
    base = from_dt or utc_now()
    return base + timedelta(days=days)


def add_hours(hours: int, from_dt: Optional[datetime] = None) -> datetime:
    """
    Добавляет часы к указанной дате.
    
    Args:
        hours: Количество часов
        from_dt: Базовая дата
        
    Returns:
        Новая дата
    """
    base = from_dt or utc_now()
    return base + timedelta(hours=hours)


def add_minutes(minutes: int, from_dt: Optional[datetime] = None) -> datetime:
    """
    Добавляет минуты к указанной дате.
    
    Args:
        minutes: Количество минут
        from_dt: Базовая дата
        
    Returns:
        Новая дата
    """
    base = from_dt or utc_now()
    return base + timedelta(minutes=minutes)


def add_seconds(seconds: int, from_dt: Optional[datetime] = None) -> datetime:
    """
    Добавляет секунды к указанной дате.
    
    Args:
        seconds: Количество секунд
        from_dt: Базовая дата
        
    Returns:
        Новая дата
    """
    base = from_dt or utc_now()
    return base + timedelta(seconds=seconds)


def is_expired(expires_at: datetime) -> bool:
    """
    Проверяет, истекла ли дата.
    
    Args:
        expires_at: Дата истечения
        
    Returns:
        True если дата в прошлом
    """
    # Приводим к UTC если нет timezone
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    return utc_now() > expires_at


def time_until_expiry(expires_at: datetime) -> timedelta:
    """
    Возвращает время до истечения.
    
    Args:
        expires_at: Дата истечения
        
    Returns:
        timedelta до истечения (отрицательный если уже истекло)
    """
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    return expires_at - utc_now()


def format_duration(seconds: float) -> str:
    """
    Форматирует длительность в человекочитаемый формат.
    
    Args:
        seconds: Длительность в секундах
        
    Returns:
        Строка вида "1:23:45" или "23:45"
    """
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def parse_time(time_str: str) -> tuple[int, int]:
    """
    Парсит время в формате HH:MM.
    
    Args:
        time_str: Время в формате "HH:MM" или "H:MM"
        
    Returns:
        Tuple (hours, minutes)
        
    Raises:
        ValueError: Если формат некорректен
    """
    parts = time_str.split(":")
    
    if len(parts) != 2:
        raise ValueError(f"Некорректный формат времени: {time_str}, ожидается HH:MM")
    
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
    except ValueError:
        raise ValueError(f"Некорректный формат времени: {time_str}")
    
    if not (0 <= hours <= 23):
        raise ValueError(f"Часы должны быть от 0 до 23, получено: {hours}")
    
    if not (0 <= minutes <= 59):
        raise ValueError(f"Минуты должны быть от 0 до 59, получено: {minutes}")
    
    return hours, minutes


def ms_to_seconds(milliseconds: int) -> float:
    """
    Конвертирует миллисекунды в секунды.
    
    Args:
        milliseconds: Время в миллисекундах
        
    Returns:
        Время в секундах
    """
    return milliseconds / 1000.0


def seconds_to_ms(seconds: float) -> int:
    """
    Конвертирует секунды в миллисекунды.
    
    Args:
        seconds: Время в секундах
        
    Returns:
        Время в миллисекундах
    """
    return int(seconds * 1000)
