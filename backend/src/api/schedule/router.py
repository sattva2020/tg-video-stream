"""
Агрегированный роутер для API расписания.

Объединяет все подроутеры:
- slots: CRUD для слотов расписания
- templates: управление шаблонами
- playlists: управление плейлистами
- groups: управление группами плейлистов
- sharing: шаринг плейлистов между пользователями
"""
from fastapi import APIRouter

from .slots import router as slots_router
from .templates import router as templates_router
from .playlists import router as playlists_router
from .groups import router as groups_router
from .sharing import router as sharing_router

# Основной роутер расписания с prefix для совместимости
router = APIRouter(prefix="/schedule")

# Подключаем все подроутеры
router.include_router(slots_router)
router.include_router(templates_router)
router.include_router(playlists_router)
router.include_router(groups_router)
router.include_router(sharing_router)

# Экспорт для обратной совместимости
__all__ = ["router"]
