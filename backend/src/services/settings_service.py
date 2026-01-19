"""
Сервис для работы с настройками приложения.

Обеспечивает:
- Шифрование/дешифрование секретных значений (Fernet)
- Кэширование настроек
- Fallback на переменные окружения
- Аудит изменений
"""

import os
import re
import logging
from typing import Optional, Dict, Any, List
from functools import lru_cache
from datetime import datetime, timedelta

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert

from src.models.app_settings import (
    AppSetting, SettingAuditLog, SettingCategory, AI_PROVIDER_SETTINGS
)

logger = logging.getLogger(__name__)


class SettingsService:
    """Сервис управления настройками приложения."""
    
    # Кэш настроек (время жизни 5 минут)
    _cache: Dict[str, Any] = {}
    _cache_expires: datetime = datetime.min
    CACHE_TTL = timedelta(minutes=5)
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._fernet = self._get_fernet()
    
    @staticmethod
    def _get_fernet() -> Optional[Fernet]:
        """Получить Fernet для шифрования/дешифрования."""
        # Ключ шифрования из .env (32 байта base64)
        encryption_key = os.getenv("SETTINGS_ENCRYPTION_KEY")
        
        if not encryption_key:
            # Генерируем ключ если не задан (для разработки)
            # В продакшене ОБЯЗАТЕЛЬНО задать в .env!
            logger.warning(
                "SETTINGS_ENCRYPTION_KEY not set! Using fallback key. "
                "This is insecure for production!"
            )
            # Fallback ключ (НЕ использовать в продакшене!)
            encryption_key = "dGhpc19pc19hX3NlY3VyZV9rZXlfZm9yX2Rldl9vbmx5IQ=="
        
        try:
            return Fernet(encryption_key.encode())
        except Exception as e:
            logger.error(f"Failed to initialize Fernet: {e}")
            return None
    
    def encrypt_value(self, value: str) -> str:
        """Зашифровать значение."""
        if not self._fernet or not value:
            return value
        
        try:
            encrypted = self._fernet.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return value
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Расшифровать значение."""
        if not self._fernet or not encrypted_value:
            return encrypted_value
        
        try:
            decrypted = self._fernet.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except InvalidToken:
            # Значение не зашифровано или ключ изменился
            logger.warning("Failed to decrypt value - may be plaintext or wrong key")
            return encrypted_value
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_value
    
    def _invalidate_cache(self):
        """Инвалидировать кэш."""
        self._cache.clear()
        self._cache_expires = datetime.min
    
    async def get_setting(
        self, 
        key: str, 
        default: Optional[str] = None,
        decrypt: bool = True
    ) -> Optional[str]:
        """
        Получить значение настройки.
        
        Приоритет:
        1. Значение из БД (если есть и активно)
        2. Переменная окружения
        3. default
        """
        # Проверяем кэш
        cache_key = f"setting:{key}"
        if cache_key in self._cache and datetime.now() < self._cache_expires:
            return self._cache[cache_key]
        
        # Ищем в БД
        result = await self.db.execute(
            select(AppSetting)
            .where(AppSetting.key == key)
            .where(AppSetting.is_active == True)
        )
        setting = result.scalar_one_or_none()
        
        value = None
        
        if setting and setting.value:
            # Есть в БД
            if setting.is_secret and decrypt:
                value = self.decrypt_value(setting.value)
            else:
                value = setting.value
        else:
            # Fallback на .env
            value = os.getenv(key, default)
        
        # Кэшируем
        self._cache[cache_key] = value
        self._cache_expires = datetime.now() + self.CACHE_TTL
        
        return value
    
    async def get_settings_by_category(
        self, 
        category: SettingCategory
    ) -> List[Dict[str, Any]]:
        """Получить все настройки категории."""
        result = await self.db.execute(
            select(AppSetting)
            .where(AppSetting.category == category)
            .where(AppSetting.is_active == True)
            .order_by(AppSetting.sort_order)
        )
        settings = result.scalars().all()
        
        items = []
        for s in settings:
            item = {
                "id": str(s.id),
                "key": s.key,
                "display_name": s.display_name,
                "description": s.description,
                "category": s.category.value,
                "value_type": s.value_type,
                "is_secret": s.is_secret,
                "is_editable": s.is_editable,
                "has_value": bool(s.value),
                "default_value": s.default_value,
                "validation_pattern": s.validation_pattern,
                "validation_message": s.validation_message,
                "metadata": s.extra_data,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            
            # Для несекретных показываем значение
            if not s.is_secret:
                item["value"] = s.value or os.getenv(s.key) or s.default_value
            else:
                # Для секретных показываем маску если есть значение
                if s.value:
                    item["value"] = "••••••••"
                else:
                    env_value = os.getenv(s.key)
                    item["value"] = "••••••••" if env_value else None
                    item["from_env"] = bool(env_value)
            
            items.append(item)
        
        return items
    
    async def get_all_settings(self) -> Dict[str, List[Dict[str, Any]]]:
        """Получить все настройки сгруппированные по категориям."""
        result = {}
        for category in SettingCategory:
            settings = await self.get_settings_by_category(category)
            if settings:
                result[category.value] = settings
        return result
    
    async def set_setting(
        self,
        key: str,
        value: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """Установить значение настройки."""
        # Находим настройку
        result = await self.db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            logger.warning(f"Setting {key} not found")
            return False
        
        if not setting.is_editable:
            logger.warning(f"Setting {key} is not editable")
            return False
        
        # Валидация
        if setting.validation_pattern and value:
            if not re.match(setting.validation_pattern, value):
                raise ValueError(setting.validation_message or "Validation failed")
        
        # Сохраняем старое значение для аудита
        old_value = setting.value
        
        # Шифруем если секрет
        if setting.is_secret and value:
            encrypted_value = self.encrypt_value(value)
        else:
            encrypted_value = value
        
        # Обновляем
        setting.value = encrypted_value
        setting.updated_by_id = user_id
        setting.updated_at = datetime.utcnow()
        
        # Аудит
        audit = SettingAuditLog(
            setting_key=key,
            action="updated",
            old_value=None if setting.is_secret else old_value,
            new_value=None if setting.is_secret else value,
            changed_by_id=user_id,
            changed_by_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(audit)
        
        await self.db.commit()
        
        # Инвалидируем кэш
        self._invalidate_cache()
        
        logger.info(f"Setting {key} updated by {user_email}")
        return True
    
    async def delete_setting_value(
        self,
        key: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> bool:
        """Удалить значение настройки (будет использоваться fallback на .env)."""
        result = await self.db.execute(
            select(AppSetting).where(AppSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            return False
        
        old_value = setting.value
        setting.value = None
        setting.updated_at = datetime.utcnow()
        
        # Аудит
        audit = SettingAuditLog(
            setting_key=key,
            action="deleted",
            old_value=None if setting.is_secret else old_value,
            new_value=None,
            changed_by_id=user_id,
            changed_by_email=user_email,
            ip_address=ip_address
        )
        self.db.add(audit)
        
        await self.db.commit()
        self._invalidate_cache()
        
        return True
    
    async def initialize_settings(self) -> int:
        """
        Инициализировать предустановленные настройки.
        Вызывается при первом запуске или миграции.
        """
        created = 0
        
        for setting_data in AI_PROVIDER_SETTINGS:
            # Проверяем существует ли
            result = await self.db.execute(
                select(AppSetting).where(AppSetting.key == setting_data["key"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                setting = AppSetting(**setting_data)
                self.db.add(setting)
                created += 1
        
        if created > 0:
            await self.db.commit()
            logger.info(f"Initialized {created} default settings")
        
        return created
    
    async def test_api_key(self, provider: str, api_key: str) -> Dict[str, Any]:
        """
        Проверить работоспособность API ключа.
        Возвращает статус и информацию о провайдере.
        """
        import aiohttp
        
        test_configs = {
            "openai": {
                "url": "https://api.openai.com/v1/models",
                "headers": {"Authorization": f"Bearer {api_key}"}
            },
            "openrouter": {
                "url": "https://openrouter.ai/api/v1/models",
                "headers": {"Authorization": f"Bearer {api_key}"}
            },
            "deepseek": {
                "url": "https://api.deepseek.com/v1/models",
                "headers": {"Authorization": f"Bearer {api_key}"}
            },
            "gemini": {
                "url": f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
                "headers": {}
            },
            "anthropic": {
                "url": "https://api.anthropic.com/v1/messages",
                "headers": {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
            }
        }
        
        if provider not in test_configs:
            return {"success": False, "error": f"Unknown provider: {provider}"}
        
        config = test_configs[provider]
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    config["url"],
                    headers=config["headers"],
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models_count = len(data.get("models", data.get("data", [])))
                        return {
                            "success": True,
                            "provider": provider,
                            "models_available": models_count,
                            "message": f"Ключ валиден. Доступно моделей: {models_count}"
                        }
                    elif response.status == 401:
                        return {
                            "success": False,
                            "error": "Неверный API ключ"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Ошибка API: {response.status}"
                        }
        except aiohttp.ClientError as e:
            return {"success": False, "error": f"Ошибка соединения: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_audit_log(
        self,
        key: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Получить лог изменений настроек."""
        query = select(SettingAuditLog).order_by(SettingAuditLog.created_at.desc())
        
        if key:
            query = query.where(SettingAuditLog.setting_key == key)
        
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        return [
            {
                "id": str(log.id),
                "setting_key": log.setting_key,
                "action": log.action,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "changed_by_email": log.changed_by_email,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]


# Хелперы для быстрого доступа к AI ключам
async def get_ai_api_key(db: AsyncSession, provider: str = "auto") -> Optional[str]:
    """
    Получить API ключ для AI провайдера.
    
    Args:
        db: Сессия БД
        provider: openai, openrouter, deepseek, gemini, anthropic или auto
    
    Returns:
        API ключ или None
    """
    service = SettingsService(db)
    
    if provider == "auto":
        # Проверяем настройку основного провайдера
        primary = await service.get_setting("AI_PRIMARY_PROVIDER", "auto")
        if primary and primary != "auto":
            provider = primary
    
    providers_order = ["openai", "openrouter", "deepseek", "gemini", "anthropic"]
    
    if provider != "auto":
        # Конкретный провайдер
        key_name = f"{provider.upper()}_API_KEY"
        return await service.get_setting(key_name)
    
    # Автовыбор - первый доступный
    for p in providers_order:
        key_name = f"{p.upper()}_API_KEY"
        key = await service.get_setting(key_name)
        if key:
            return key
    
    return None


async def get_active_ai_provider(db: AsyncSession) -> Optional[str]:
    """Получить имя активного AI провайдера."""
    service = SettingsService(db)
    
    primary = await service.get_setting("AI_PRIMARY_PROVIDER", "auto")
    if primary and primary != "auto":
        key = await service.get_setting(f"{primary.upper()}_API_KEY")
        if key:
            return primary
    
    # Автовыбор
    for provider in ["openai", "openrouter", "deepseek", "gemini", "anthropic"]:
        key = await service.get_setting(f"{provider.upper()}_API_KEY")
        if key:
            return provider
    
    return None
