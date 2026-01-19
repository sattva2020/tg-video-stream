"""
API эндпоинты для управления настройками приложения.

Доступ: только для администраторов.
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.lib.db import get_db
from src.models.user import User, UserRole
from src.api.auth.dependencies import get_current_user
from src.services.settings_service import SettingsService, get_active_ai_provider
from src.models.app_settings import SettingCategory

router = APIRouter(prefix="/settings", tags=["settings"])


# === Pydantic Schemas ===

class SettingResponse(BaseModel):
    """Настройка для отображения."""
    id: str
    key: str
    display_name: str
    description: Optional[str]
    category: str
    value_type: str
    is_secret: bool
    is_editable: bool
    has_value: bool
    value: Optional[str]
    from_env: Optional[bool] = None
    default_value: Optional[str]
    validation_pattern: Optional[str]
    validation_message: Optional[str]
    metadata: Optional[dict]
    updated_at: Optional[str]


class UpdateSettingRequest(BaseModel):
    """Запрос на обновление настройки."""
    value: str = Field(..., min_length=1, max_length=500)


class TestApiKeyRequest(BaseModel):
    """Запрос на проверку API ключа."""
    provider: str = Field(..., pattern="^(openai|openrouter|deepseek|gemini|anthropic)$")
    api_key: str = Field(..., min_length=10)


class TestApiKeyResponse(BaseModel):
    """Результат проверки API ключа."""
    success: bool
    provider: Optional[str] = None
    models_available: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


class AuditLogEntry(BaseModel):
    """Запись лога аудита."""
    id: str
    setting_key: str
    action: str
    old_value: Optional[str]
    new_value: Optional[str]
    changed_by_email: Optional[str]
    ip_address: Optional[str]
    created_at: str


class AIStatusResponse(BaseModel):
    """Статус AI провайдеров."""
    active_provider: Optional[str]
    providers: dict


# === Dependency: требуется админ ===

async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Проверка что пользователь - администратор."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для администраторов"
        )
    return current_user


# === Endpoints ===

@router.get("", response_model=dict)
async def get_all_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Получить все настройки сгруппированные по категориям.
    
    Требуется: роль администратора.
    """
    service = SettingsService(db)
    settings = await service.get_all_settings()
    
    return {
        "categories": [
            {
                "key": cat.value,
                "name": _get_category_name(cat),
                "icon": _get_category_icon(cat),
                "settings": settings.get(cat.value, [])
            }
            for cat in SettingCategory
            if settings.get(cat.value)
        ]
    }


@router.get("/category/{category}", response_model=List[SettingResponse])
async def get_settings_by_category(
    category: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Получить настройки конкретной категории."""
    try:
        cat = SettingCategory(category)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown category: {category}"
        )
    
    service = SettingsService(db)
    return await service.get_settings_by_category(cat)


@router.put("/{key}")
async def update_setting(
    key: str,
    data: UpdateSettingRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Обновить значение настройки.
    
    Для секретных значений (API ключей) значение шифруется.
    """
    service = SettingsService(db)
    
    # Получаем IP и User-Agent для аудита
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    
    try:
        success = await service.set_setting(
            key=key,
            value=data.value,
            user_id=str(current_user.id),
            user_email=current_user.email,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Настройка не найдена или не редактируема"
        )
    
    return {"success": True, "message": f"Настройка {key} обновлена"}


@router.delete("/{key}")
async def delete_setting_value(
    key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Удалить значение настройки.
    
    После удаления будет использоваться значение из .env (если есть).
    """
    service = SettingsService(db)
    
    ip_address = request.client.host if request.client else None
    
    success = await service.delete_setting_value(
        key=key,
        user_id=str(current_user.id),
        user_email=current_user.email,
        ip_address=ip_address
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Настройка не найдена"
        )
    
    return {"success": True, "message": f"Значение {key} удалено"}


@router.post("/test-api-key", response_model=TestApiKeyResponse)
async def test_api_key(
    data: TestApiKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Проверить работоспособность API ключа.
    
    Отправляет тестовый запрос к API провайдера.
    """
    service = SettingsService(db)
    result = await service.test_api_key(data.provider, data.api_key)
    return TestApiKeyResponse(**result)


@router.get("/ai/status", response_model=AIStatusResponse)
async def get_ai_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Получить статус AI провайдеров.
    
    Показывает какой провайдер активен и какие настроены.
    """
    service = SettingsService(db)
    
    active = await get_active_ai_provider(db)
    
    providers = {}
    for provider in ["openai", "openrouter", "deepseek", "gemini", "anthropic"]:
        key = await service.get_setting(f"{provider.upper()}_API_KEY")
        providers[provider] = {
            "configured": bool(key),
            "is_active": provider == active
        }
    
    return AIStatusResponse(
        active_provider=active,
        providers=providers
    )


@router.get("/audit", response_model=List[AuditLogEntry])
async def get_audit_log(
    key: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Получить лог изменений настроек.
    
    Можно фильтровать по конкретной настройке.
    """
    service = SettingsService(db)
    return await service.get_audit_log(key=key, limit=min(limit, 100))


@router.post("/initialize")
async def initialize_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Инициализировать предустановленные настройки.
    
    Создаёт настройки для AI провайдеров если их нет.
    """
    service = SettingsService(db)
    created = await service.initialize_settings()
    
    return {
        "success": True,
        "created": created,
        "message": f"Создано настроек: {created}"
    }


# === Helpers ===

def _get_category_name(category: SettingCategory) -> str:
    """Человекочитаемое название категории."""
    names = {
        SettingCategory.AI_PROVIDERS: "AI Провайдеры",
        SettingCategory.INTEGRATIONS: "Интеграции",
        SettingCategory.NOTIFICATIONS: "Уведомления",
        SettingCategory.SECURITY: "Безопасность",
        SettingCategory.GENERAL: "Общие",
        SettingCategory.TELEGRAM: "Telegram",
    }
    return names.get(category, category.value)


def _get_category_icon(category: SettingCategory) -> str:
    """Иконка категории."""
    icons = {
        SettingCategory.AI_PROVIDERS: "cpu",
        SettingCategory.INTEGRATIONS: "plug",
        SettingCategory.NOTIFICATIONS: "bell",
        SettingCategory.SECURITY: "shield",
        SettingCategory.GENERAL: "settings",
        SettingCategory.TELEGRAM: "send",
    }
    return icons.get(category, "settings")
