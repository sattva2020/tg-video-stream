"""
Schedule API module — управление расписанием трансляций.

Модуль разбит на подмодули:
- schemas: Pydantic модели
- utils: Вспомогательные функции
- slots: API для слотов расписания
- templates: API для шаблонов
- playlists: API для плейлистов
- router: Агрегация роутеров

Backward compatibility:
- Все публичные символы экспортируются из корневого модуля
- router доступен напрямую для регистрации в main.py
"""

from src.api.schedule.router import router
from src.api.schedule.schemas import (
    TimeSlotBase,
    ScheduleSlotCreate,
    ScheduleSlotUpdate,
    ScheduleSlotResponse,
    ScheduleTemplateCreate,
    ScheduleTemplateResponse,
    PlaylistCreate,
    PlaylistUpdate,
    PlaylistResponse,
    BulkCopyRequest,
    ApplyTemplateRequest,
    CalendarViewResponse,
)
from src.api.schedule.utils import (
    parse_time,
    format_time,
    check_slot_overlap,
)

__all__ = [
    # Router
    "router",
    # Schemas
    "TimeSlotBase",
    "ScheduleSlotCreate",
    "ScheduleSlotUpdate",
    "ScheduleSlotResponse",
    "ScheduleTemplateCreate",
    "ScheduleTemplateResponse",
    "PlaylistCreate",
    "PlaylistUpdate",
    "PlaylistResponse",
    "BulkCopyRequest",
    "ApplyTemplateRequest",
    "CalendarViewResponse",
    # Utils
    "parse_time",
    "format_time",
    "check_slot_overlap",
]
