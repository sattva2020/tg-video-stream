"""Конфигурация приложения.

Пакет config объединяет настройки и вспомогательные конфиги,
чтобы остальные модули могли импортировать `settings` через `src.config`.
"""

from src.core.config import Settings, settings as _core_settings

settings: Settings = _core_settings

__all__ = ["settings", "Settings"]
