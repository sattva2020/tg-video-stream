# -*- coding: utf-8 -*-
"""
Утилиты безопасности для audio streaming сервисов.

Включает:
- Санитизация идентификаторов для Redis и файловой системы
- Валидация числовых диапазонов
- Проверка доступа к каналам

Пример использования:
    from src.lib.security_utils import sanitize_redis_key, validate_band_value
    
    safe_key = sanitize_redis_key(user_id)
    valid_band = validate_band_value(band_value, min_db=-24, max_db=12)
"""

import re
import os
import logging
from typing import Optional, List
from functools import wraps

logger = logging.getLogger(__name__)


# =============================================================================
# Константы безопасности
# =============================================================================

# Допустимые символы для Redis ключей и путей
SAFE_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

# Максимальная длина идентификаторов
MAX_ID_LENGTH = 128

# Ограничения для equalizer bands
BAND_MIN_DB = -24.0
BAND_MAX_DB = 12.0
BAND_COUNT = 10

# Ограничения для скорости воспроизведения
SPEED_MIN = 0.5
SPEED_MAX = 2.0

# Ограничения для pitch
PITCH_MIN = 0.5
PITCH_MAX = 2.0


# =============================================================================
# Санитизация идентификаторов
# =============================================================================

def sanitize_redis_key(identifier: str) -> str:
    """
    Санитизирует строку для безопасного использования в Redis ключах.
    
    Удаляет все символы, кроме букв, цифр, дефисов и подчёркиваний.
    
    Args:
        identifier: Исходный идентификатор
        
    Returns:
        Безопасный идентификатор
        
    Raises:
        ValueError: Если результат пустой или слишком длинный
    """
    if not identifier:
        raise ValueError("Идентификатор не может быть пустым")
    
    # Удаляем небезопасные символы
    safe = re.sub(r'[^a-zA-Z0-9_-]', '', str(identifier))
    
    if not safe:
        raise ValueError("Идентификатор не содержит допустимых символов")
    
    if len(safe) > MAX_ID_LENGTH:
        raise ValueError(f"Идентификатор слишком длинный (max {MAX_ID_LENGTH})")
    
    return safe


def sanitize_filesystem_path(path_component: str) -> str:
    """
    Санитизирует строку для безопасного использования в путях файловой системы.
    
    Предотвращает path traversal атаки.
    
    Args:
        path_component: Компонент пути (имя файла или директории)
        
    Returns:
        Безопасный компонент пути
        
    Raises:
        ValueError: Если обнаружена попытка path traversal
    """
    if not path_component:
        raise ValueError("Компонент пути не может быть пустым")
    
    # Удаляем path traversal паттерны
    if '..' in path_component or '/' in path_component or '\\' in path_component:
        raise ValueError("Обнаружена попытка path traversal")
    
    # Оставляем только безопасные символы
    safe = re.sub(r'[^a-zA-Z0-9_.-]', '', str(path_component))
    
    if not safe:
        raise ValueError("Компонент пути не содержит допустимых символов")
    
    if safe.startswith('.'):
        raise ValueError("Компонент пути не может начинаться с точки")
    
    return safe


def sanitize_channel_id(channel_id: str) -> str:
    """
    Санитизирует ID канала для использования в ключах и путях.
    
    Args:
        channel_id: ID канала
        
    Returns:
        Безопасный ID канала
        
    Raises:
        ValueError: Если ID невалиден
    """
    return sanitize_redis_key(channel_id)


def is_valid_id(identifier: str) -> bool:
    """
    Проверяет, является ли идентификатор валидным.
    
    Args:
        identifier: Идентификатор для проверки
        
    Returns:
        True если идентификатор валиден
    """
    if not identifier or not isinstance(identifier, str):
        return False
    
    if len(identifier) > MAX_ID_LENGTH:
        return False
    
    return bool(SAFE_ID_PATTERN.match(identifier))


# =============================================================================
# Валидация числовых значений
# =============================================================================

def validate_band_value(value: float, band_index: int = 0) -> float:
    """
    Валидирует значение полосы эквалайзера.
    
    Args:
        value: Значение в дБ
        band_index: Индекс полосы (для сообщения об ошибке)
        
    Returns:
        Валидное значение
        
    Raises:
        ValueError: Если значение вне допустимого диапазона
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"Band {band_index}: значение должно быть числом")
    
    if value < BAND_MIN_DB or value > BAND_MAX_DB:
        raise ValueError(
            f"Band {band_index}: значение {value} dB вне диапазона "
            f"[{BAND_MIN_DB}, {BAND_MAX_DB}]"
        )
    
    return float(value)


def validate_bands(bands: List[float]) -> List[float]:
    """
    Валидирует массив полос эквалайзера.
    
    Args:
        bands: Список значений полос
        
    Returns:
        Валидный список
        
    Raises:
        ValueError: Если количество или значения невалидны
    """
    if not isinstance(bands, list):
        raise ValueError("Bands должен быть списком")
    
    if len(bands) != BAND_COUNT:
        raise ValueError(f"Ожидается {BAND_COUNT} полос, получено {len(bands)}")
    
    return [validate_band_value(v, i) for i, v in enumerate(bands)]


def validate_speed(speed: float) -> float:
    """
    Валидирует скорость воспроизведения.
    
    Args:
        speed: Скорость (множитель)
        
    Returns:
        Валидная скорость
        
    Raises:
        ValueError: Если скорость вне диапазона
    """
    if not isinstance(speed, (int, float)):
        raise ValueError("Скорость должна быть числом")
    
    if speed < SPEED_MIN or speed > SPEED_MAX:
        raise ValueError(
            f"Скорость {speed}x вне диапазона [{SPEED_MIN}, {SPEED_MAX}]"
        )
    
    return float(speed)


def validate_pitch(pitch: float) -> float:
    """
    Валидирует коэффициент pitch.
    
    Args:
        pitch: Pitch коэффициент
        
    Returns:
        Валидный pitch
        
    Raises:
        ValueError: Если pitch вне диапазона
    """
    if not isinstance(pitch, (int, float)):
        raise ValueError("Pitch должен быть числом")
    
    if pitch < PITCH_MIN or pitch > PITCH_MAX:
        raise ValueError(
            f"Pitch {pitch}x вне диапазона [{PITCH_MIN}, {PITCH_MAX}]"
        )
    
    return float(pitch)


def validate_position(position: float, duration: Optional[float] = None) -> float:
    """
    Валидирует позицию в треке.
    
    Args:
        position: Позиция в секундах
        duration: Длительность трека (опционально)
        
    Returns:
        Валидная позиция
        
    Raises:
        ValueError: Если позиция невалидна
    """
    if not isinstance(position, (int, float)):
        raise ValueError("Позиция должна быть числом")
    
    if position < 0:
        raise ValueError("Позиция не может быть отрицательной")
    
    if duration is not None and position > duration:
        raise ValueError(
            f"Позиция {position}s превышает длительность {duration}s"
        )
    
    return float(position)


# =============================================================================
# Валидация URL
# =============================================================================

def validate_stream_url(url: str) -> str:
    """
    Валидирует URL радио стрима.
    
    Допускает http, https, icecast протоколы.
    
    Args:
        url: URL для валидации
        
    Returns:
        Валидный URL
        
    Raises:
        ValueError: Если URL невалиден
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL не может быть пустым")
    
    url = url.strip()
    
    # Допустимые протоколы
    allowed_protocols = ('http://', 'https://', 'icecast://')
    
    if not any(url.startswith(p) for p in allowed_protocols):
        raise ValueError(
            f"URL должен начинаться с одного из: {', '.join(allowed_protocols)}"
        )
    
    # Базовая проверка структуры
    if len(url) < 10 or len(url) > 2048:
        raise ValueError("Длина URL должна быть от 10 до 2048 символов")
    
    # Проверка на подозрительные паттерны
    suspicious = ['javascript:', 'data:', 'file:', 'ftp://']
    if any(s in url.lower() for s in suspicious):
        raise ValueError("URL содержит недопустимый протокол")
    
    return url


# =============================================================================
# Декораторы безопасности
# =============================================================================

def sanitize_id_param(param_name: str = 'channel_id'):
    """
    Декоратор для автоматической санитизации ID параметра.
    
    Пример:
        @sanitize_id_param('channel_id')
        def get_channel(channel_id: str):
            ...  # channel_id уже безопасен
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if param_name in kwargs:
                try:
                    kwargs[param_name] = sanitize_redis_key(kwargs[param_name])
                except ValueError as e:
                    raise ValueError(f"Невалидный {param_name}: {e}")
            return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if param_name in kwargs:
                try:
                    kwargs[param_name] = sanitize_redis_key(kwargs[param_name])
                except ValueError as e:
                    raise ValueError(f"Невалидный {param_name}: {e}")
            return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def validate_numeric_param(param_name: str, min_val: float, max_val: float):
    """
    Декоратор для автоматической валидации числового параметра.
    
    Пример:
        @validate_numeric_param('speed', 0.5, 2.0)
        def set_speed(speed: float):
            ...  # speed уже провалидирован
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if param_name in kwargs:
                value = kwargs[param_name]
                if not isinstance(value, (int, float)):
                    raise ValueError(f"{param_name} должен быть числом")
                if value < min_val or value > max_val:
                    raise ValueError(
                        f"{param_name} {value} вне диапазона [{min_val}, {max_val}]"
                    )
            return func(*args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if param_name in kwargs:
                value = kwargs[param_name]
                if not isinstance(value, (int, float)):
                    raise ValueError(f"{param_name} должен быть числом")
                if value < min_val or value > max_val:
                    raise ValueError(
                        f"{param_name} {value} вне диапазона [{min_val}, {max_val}]"
                    )
            return await func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


# =============================================================================
# Логирование безопасности
# =============================================================================

def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    details: Optional[str] = None,
    severity: str = "warning",
):
    """
    Логирует событие безопасности.
    
    Args:
        event_type: Тип события (rate_limit, auth_failure, etc.)
        user_id: ID пользователя (если известен)
        details: Дополнительные детали
        severity: Уровень (info, warning, error, critical)
    """
    log_func = getattr(logger, severity, logger.warning)
    
    message = f"[SECURITY] {event_type}"
    if user_id:
        # Не логируем полный ID для приватности
        safe_id = user_id[:8] + "..." if len(str(user_id)) > 8 else user_id
        message += f" user={safe_id}"
    if details:
        # Ограничиваем длину деталей
        safe_details = details[:200] + "..." if len(details) > 200 else details
        message += f" details={safe_details}"
    
    log_func(message)
