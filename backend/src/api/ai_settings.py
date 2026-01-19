"""
API эндпоинты для управления AI/LLM настройками.
Доступно только для SUPERADMIN.

Автор: Jarvis
Дата: 2025-12-29
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from src.models.user import User, UserRole
from api.auth import get_current_user
import os
import json

router = APIRouter(prefix="/ai-settings", tags=["AI Settings"])

# Путь к файлу конфигурации AI
AI_CONFIG_PATH = os.getenv("AI_CONFIG_PATH", "/app/data/ai_config.json")


# ============================================
# СХЕМЫ
# ============================================

class AIProviderConfig(BaseModel):
    """Конфигурация одного AI-провайдера."""
    id: str = Field(..., description="Идентификатор провайдера (openai, anthropic, etc.)")
    name: str = Field(..., description="Отображаемое имя")
    enabled: bool = Field(default=False, description="Включён ли провайдер")
    api_key: Optional[str] = Field(default=None, description="API ключ (маскируется при чтении)")
    base_url: Optional[str] = Field(default=None, description="Кастомный base URL")
    model: str = Field(..., description="Используемая модель")
    description: Optional[str] = Field(default=None, description="Описание провайдера")


class AISettingsResponse(BaseModel):
    """Ответ с текущими настройками AI."""
    active_provider: str = Field(..., description="Активный провайдер")
    providers: List[Dict[str, Any]] = Field(..., description="Список провайдеров")
    chatops_enabled: bool = Field(default=False, description="ChatOps бот включён")
    anomaly_detection_enabled: bool = Field(default=False, description="ML Anomaly Detection включён")


class AISettingsUpdate(BaseModel):
    """Обновление настроек AI."""
    active_provider: Optional[str] = None
    providers: Optional[List[AIProviderConfig]] = None
    chatops_enabled: Optional[bool] = None
    anomaly_detection_enabled: Optional[bool] = None


class TestConnectionRequest(BaseModel):
    """Запрос на тест подключения к провайдеру."""
    provider_id: str
    api_key: str
    base_url: Optional[str] = None
    model: str


class TestConnectionResponse(BaseModel):
    """Результат теста подключения."""
    success: bool
    message: str
    latency_ms: Optional[int] = None


# ============================================
# ДЕФОЛТНЫЕ ПРОВАЙДЕРЫ
# ============================================

DEFAULT_PROVIDERS = [
    {
        "id": "openai",
        "name": "OpenAI",
        "enabled": False,
        "api_key": None,
        "base_url": None,
        "model": "gpt-4o-mini",
        "description": "ChatGPT, GPT-4 — быстрая и качественная модель"
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "enabled": False,
        "api_key": None,
        "base_url": None,
        "model": "claude-3-haiku-20240307",
        "description": "Claude 3 — отличный для анализа и диалогов"
    },
    {
        "id": "openrouter",
        "name": "OpenRouter",
        "enabled": False,
        "api_key": None,
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-3-haiku",
        "description": "Универсальный доступ к 100+ моделям через один API"
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "enabled": False,
        "api_key": None,
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "description": "Китайская модель, отлично справляется с кодом"
    },
    {
        "id": "qwen",
        "name": "Qwen (Alibaba)",
        "enabled": False,
        "api_key": None,
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-turbo",
        "description": "Быстрая модель от Alibaba"
    },
    {
        "id": "zai",
        "name": "z.ai",
        "enabled": False,
        "api_key": None,
        "base_url": "https://api.z.ai/v1",
        "model": "z1-mini",
        "description": "Лёгкая и быстрая модель"
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "enabled": False,
        "api_key": None,
        "base_url": None,
        "model": "gemini-1.5-flash",
        "description": "Gemini от Google — бесплатная квота"
    },
]

DEFAULT_CONFIG = {
    "active_provider": "openai",
    "providers": DEFAULT_PROVIDERS,
    "chatops_enabled": False,
    "anomaly_detection_enabled": False,
}


# ============================================
# УТИЛИТЫ
# ============================================

def require_superadmin(current_user: User = Depends(get_current_user)) -> User:
    """Проверка, что пользователь — SUPERADMIN."""
    if current_user.role not in (UserRole.SUPERADMIN.value, "superadmin", "SUPERADMIN"):
        raise HTTPException(
            status_code=403,
            detail="Доступ разрешён только для SUPERADMIN"
        )
    return current_user


def load_config() -> dict:
    """Загрузить конфигурацию из файла."""
    try:
        if os.path.exists(AI_CONFIG_PATH):
            with open(AI_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Сохранить конфигурацию в файл."""
    os.makedirs(os.path.dirname(AI_CONFIG_PATH), exist_ok=True)
    with open(AI_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def mask_api_key(key: Optional[str]) -> Optional[str]:
    """Маскировать API ключ для отображения."""
    if not key:
        return None
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


# ============================================
# ЭНДПОИНТЫ
# ============================================

@router.get("", response_model=AISettingsResponse)
async def get_ai_settings(
    current_user: User = Depends(require_superadmin)
) -> AISettingsResponse:
    """
    Получить текущие настройки AI/LLM.
    
    Доступно только для SUPERADMIN.
    API ключи возвращаются в маскированном виде.
    """
    config = load_config()
    
    # Маскируем API ключи
    providers = []
    for p in config.get("providers", DEFAULT_PROVIDERS):
        masked = p.copy()
        masked["api_key"] = mask_api_key(p.get("api_key"))
        providers.append(masked)
    
    return AISettingsResponse(
        active_provider=config.get("active_provider", "openai"),
        providers=providers,
        chatops_enabled=config.get("chatops_enabled", False),
        anomaly_detection_enabled=config.get("anomaly_detection_enabled", False),
    )


@router.put("", response_model=AISettingsResponse)
async def update_ai_settings(
    update: AISettingsUpdate,
    current_user: User = Depends(require_superadmin)
) -> AISettingsResponse:
    """
    Обновить настройки AI/LLM.
    
    Доступно только для SUPERADMIN.
    Можно обновлять частично (только те поля, которые переданы).
    """
    config = load_config()
    
    if update.active_provider is not None:
        config["active_provider"] = update.active_provider
    
    if update.chatops_enabled is not None:
        config["chatops_enabled"] = update.chatops_enabled
    
    if update.anomaly_detection_enabled is not None:
        config["anomaly_detection_enabled"] = update.anomaly_detection_enabled
    
    if update.providers is not None:
        # Сохраняем старые ключи для провайдеров, где новый ключ не указан
        old_providers = {p["id"]: p for p in config.get("providers", [])}
        new_providers = []
        
        for p in update.providers:
            provider_dict = p.model_dump()
            
            # Если api_key не указан или маскирован, сохраняем старый
            if not provider_dict.get("api_key") or provider_dict["api_key"].startswith("***"):
                old = old_providers.get(provider_dict["id"], {})
                provider_dict["api_key"] = old.get("api_key")
            
            new_providers.append(provider_dict)
        
        config["providers"] = new_providers
    
    save_config(config)
    
    # Возвращаем обновлённые настройки с маскированными ключами
    return await get_ai_settings(current_user)


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_ai_connection(
    request: TestConnectionRequest,
    current_user: User = Depends(require_superadmin)
) -> TestConnectionResponse:
    """
    Тест подключения к AI-провайдеру.
    
    Отправляет тестовый запрос и возвращает результат.
    """
    import time
    import httpx
    
    provider_id = request.provider_id
    api_key = request.api_key
    base_url = request.base_url
    model = request.model
    
    try:
        start = time.time()
        
        if provider_id == "anthropic":
            # Anthropic Claude API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hi"}]
                    },
                    timeout=15
                )
                response.raise_for_status()
        
        elif provider_id == "gemini":
            # Google Gemini API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent?key={api_key}",
                    json={"contents": [{"parts": [{"text": "Hi"}]}]},
                    timeout=15
                )
                response.raise_for_status()
        
        else:
            # OpenAI-совместимые API (OpenAI, OpenRouter, DeepSeek, Qwen, z.ai)
            url = base_url or "https://api.openai.com/v1"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            
            # Дополнительные заголовки для OpenRouter
            if provider_id == "openrouter":
                headers["HTTP-Referer"] = "https://sattva.app"
                headers["X-Title"] = "Sattva AI Settings Test"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hi"}]
                    },
                    timeout=15
                )
                response.raise_for_status()
        
        latency = int((time.time() - start) * 1000)
        
        return TestConnectionResponse(
            success=True,
            message=f"✅ Подключение успешно! Модель: {model}",
            latency_ms=latency
        )
    
    except httpx.HTTPStatusError as e:
        error_detail = str(e.response.text)[:200] if e.response else str(e)
        return TestConnectionResponse(
            success=False,
            message=f"❌ Ошибка API ({e.response.status_code}): {error_detail}"
        )
    
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"❌ Ошибка подключения: {str(e)}"
        )


@router.get("/available-models/{provider_id}")
async def get_available_models(
    provider_id: str,
    current_user: User = Depends(require_superadmin)
) -> List[Dict[str, str]]:
    """
    Получить список доступных моделей для провайдера.
    """
    models = {
        "openai": [
            {"id": "gpt-4o", "name": "GPT-4o (мощная)"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (быстрая)"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo (дешёвая)"},
        ],
        "anthropic": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (лучшая)"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku (быстрая)"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus (мощная)"},
        ],
        "openrouter": [
            {"id": "anthropic/claude-3-haiku", "name": "Claude 3 Haiku"},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini"},
            {"id": "google/gemini-flash-1.5", "name": "Gemini 1.5 Flash"},
            {"id": "meta-llama/llama-3.1-70b-instruct", "name": "Llama 3.1 70B"},
        ],
        "deepseek": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat"},
            {"id": "deepseek-coder", "name": "DeepSeek Coder"},
        ],
        "qwen": [
            {"id": "qwen-turbo", "name": "Qwen Turbo"},
            {"id": "qwen-plus", "name": "Qwen Plus"},
            {"id": "qwen-max", "name": "Qwen Max"},
        ],
        "zai": [
            {"id": "z1-mini", "name": "Z1 Mini"},
            {"id": "z1", "name": "Z1"},
        ],
        "gemini": [
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash (быстрая)"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro (мощная)"},
            {"id": "gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash (экспериментальная)"},
        ],
    }
    
    return models.get(provider_id, [])
