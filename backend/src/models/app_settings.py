"""
Модель настроек приложения с шифрованием чувствительных данных.

Позволяет хранить API ключи и другие настройки в БД вместо .env,
с возможностью управления через админку.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, Boolean, DateTime, Enum as SQLEnum, Index, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from src.database import Base
import enum


class SettingCategory(str, enum.Enum):
    """Категории настроек"""
    AI_PROVIDERS = "ai_providers"      # API ключи для AI провайдеров
    INTEGRATIONS = "integrations"       # Внешние интеграции
    NOTIFICATIONS = "notifications"     # Настройки уведомлений
    SECURITY = "security"               # Настройки безопасности
    GENERAL = "general"                 # Общие настройки
    TELEGRAM = "telegram"               # Telegram настройки


class AppSetting(Base):
    """
    Настройки приложения.
    
    Чувствительные данные (is_secret=True) шифруются Fernet.
    Поддерживает fallback на .env если значение не задано в БД.
    """
    __tablename__ = "app_settings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Ключ настройки (уникальный)
    key = Column(String(100), unique=True, nullable=False, index=True)
    
    # Значение (зашифровано если is_secret=True)
    value = Column(Text, nullable=True)
    
    # Отображаемое название
    display_name = Column(String(200), nullable=False)
    
    # Описание настройки
    description = Column(Text, nullable=True)
    
    # Категория
    category = Column(
        SQLEnum(SettingCategory),
        nullable=False,
        default=SettingCategory.GENERAL
    )
    
    # Тип значения для валидации на фронте
    value_type = Column(
        String(20),
        nullable=False,
        default="string"  # string, number, boolean, json, secret
    )
    
    # Это секретное значение (API ключ и т.п.)
    is_secret = Column(Boolean, default=False, nullable=False)
    
    # Активна ли настройка
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Можно ли редактировать через UI
    is_editable = Column(Boolean, default=True, nullable=False)
    
    # Порядок отображения
    sort_order = Column(BigInteger, default=0, nullable=False)
    
    # Значение по умолчанию (для отображения placeholder)
    default_value = Column(Text, nullable=True)
    
    # Валидация (regex pattern)
    validation_pattern = Column(String(500), nullable=True)
    
    # Сообщение об ошибке валидации
    validation_message = Column(String(500), nullable=True)
    
    # Метаданные (для UI: иконка, подсказки и т.п.)
    extra_data = Column(JSONB, nullable=True)
    
    # Кто последний изменил
    updated_by_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Индексы
    __table_args__ = (
        Index('idx_settings_category', 'category'),
        Index('idx_settings_category_active', 'category', 'is_active'),
    )
    
    def __repr__(self):
        return f"<AppSetting {self.key}={self.value[:20] if self.value and not self.is_secret else '***'}>"


class SettingAuditLog(Base):
    """
    Лог изменений настроек для аудита.
    """
    __tablename__ = "setting_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Какая настройка изменена
    setting_key = Column(String(100), nullable=False, index=True)
    
    # Действие
    action = Column(String(20), nullable=False)  # created, updated, deleted
    
    # Старое значение (для секретов: null)
    old_value = Column(Text, nullable=True)
    
    # Новое значение (для секретов: null)
    new_value = Column(Text, nullable=True)
    
    # Кто изменил
    changed_by_id = Column(UUID(as_uuid=True), nullable=True)
    changed_by_email = Column(String(255), nullable=True)
    
    # IP адрес
    ip_address = Column(String(45), nullable=True)
    
    # User Agent
    user_agent = Column(Text, nullable=True)
    
    # Когда
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_audit_setting_key', 'setting_key'),
        Index('idx_audit_created_at', 'created_at'),
    )


# Предустановленные настройки для AI провайдеров
AI_PROVIDER_SETTINGS = [
    {
        "key": "OPENAI_API_KEY",
        "display_name": "OpenAI API Key",
        "description": "Ключ API для OpenAI (GPT-4, GPT-3.5). Получить: https://platform.openai.com/api-keys",
        "category": SettingCategory.AI_PROVIDERS,
        "value_type": "secret",
        "is_secret": True,
        "sort_order": 1,
        "validation_pattern": r"^sk-[a-zA-Z0-9\-_]{20,}$",
        "validation_message": "Ключ должен начинаться с 'sk-'",
        "extra_data": {
            "icon": "openai",
            "provider": "openai",
            "docs_url": "https://platform.openai.com/docs"
        }
    },
    {
        "key": "OPENROUTER_API_KEY",
        "display_name": "OpenRouter API Key",
        "description": "Ключ API для OpenRouter (доступ к множеству моделей). Получить: https://openrouter.ai/keys",
        "category": SettingCategory.AI_PROVIDERS,
        "value_type": "secret",
        "is_secret": True,
        "sort_order": 2,
        "validation_pattern": r"^sk-or-[a-zA-Z0-9\-_]{20,}$",
        "validation_message": "Ключ должен начинаться с 'sk-or-'",
        "extra_data": {
            "icon": "openrouter",
            "provider": "openrouter",
            "docs_url": "https://openrouter.ai/docs"
        }
    },
    {
        "key": "DEEPSEEK_API_KEY",
        "display_name": "DeepSeek API Key",
        "description": "Ключ API для DeepSeek (бюджетный вариант). Получить: https://platform.deepseek.com",
        "category": SettingCategory.AI_PROVIDERS,
        "value_type": "secret",
        "is_secret": True,
        "sort_order": 3,
        "validation_pattern": r"^sk-[a-zA-Z0-9\-_]{20,}$",
        "validation_message": "Ключ должен начинаться с 'sk-'",
        "extra_data": {
            "icon": "deepseek",
            "provider": "deepseek",
            "docs_url": "https://platform.deepseek.com/docs"
        }
    },
    {
        "key": "GEMINI_API_KEY",
        "display_name": "Google Gemini API Key",
        "description": "Ключ API для Google Gemini. Получить: https://aistudio.google.com/apikey",
        "category": SettingCategory.AI_PROVIDERS,
        "value_type": "secret",
        "is_secret": True,
        "sort_order": 4,
        "validation_pattern": r"^[a-zA-Z0-9\-_]{30,}$",
        "validation_message": "Некорректный формат ключа",
        "extra_data": {
            "icon": "google",
            "provider": "gemini",
            "docs_url": "https://ai.google.dev/docs"
        }
    },
    {
        "key": "ANTHROPIC_API_KEY",
        "display_name": "Anthropic API Key",
        "description": "Ключ API для Anthropic Claude. Получить: https://console.anthropic.com",
        "category": SettingCategory.AI_PROVIDERS,
        "value_type": "secret",
        "is_secret": True,
        "sort_order": 5,
        "validation_pattern": r"^sk-ant-[a-zA-Z0-9\-_]{20,}$",
        "validation_message": "Ключ должен начинаться с 'sk-ant-'",
        "extra_data": {
            "icon": "anthropic",
            "provider": "anthropic",
            "docs_url": "https://docs.anthropic.com"
        }
    },
    {
        "key": "AI_PRIMARY_PROVIDER",
        "display_name": "Основной AI провайдер",
        "description": "Какой провайдер использовать по умолчанию",
        "category": SettingCategory.AI_PROVIDERS,
        "value_type": "select",
        "is_secret": False,
        "sort_order": 0,
        "default_value": "auto",
        "extra_data": {
            "options": [
                {"value": "auto", "label": "Автовыбор"},
                {"value": "openai", "label": "OpenAI"},
                {"value": "openrouter", "label": "OpenRouter"},
                {"value": "deepseek", "label": "DeepSeek"},
                {"value": "gemini", "label": "Google Gemini"},
                {"value": "anthropic", "label": "Anthropic Claude"}
            ]
        }
    }
]
