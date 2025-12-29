"""
Структурированное логирование для проекта.
Использует structlog для JSON-логов, которые Loki может парсить.
"""

import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger

# Директория для логов
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Уровень логирования из environment или INFO по умолчанию
LOG_LEVEL = logging.INFO


def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """Добавляет контекст приложения к каждому лог-событию."""
    event_dict["app"] = "sattva-tv-backend"
    event_dict["environment"] = "production"  # TODO: из env
    return event_dict


def setup_logging() -> structlog.BoundLogger:
    """
    Настройка структурированного логирования.
    
    Returns:
        Настроенный logger
    """
    # Настройка стандартного logging (для библиотек)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=LOG_LEVEL,
    )

    # Настройка structlog
    structlog.configure(
        processors=[
            # Фильтрация по уровню
            structlog.stdlib.filter_by_level,
            # Добавление имени logger'а
            structlog.stdlib.add_logger_name,
            # Добавление уровня лога
            structlog.stdlib.add_log_level,
            # Добавление timestamp в ISO формате
            structlog.processors.TimeStamper(fmt="iso"),
            # Добавление информации о стеке при исключениях
            structlog.processors.StackInfoRenderer(),
            # Форматирование исключений
            structlog.processors.format_exc_info,
            # Преобразование unicode
            structlog.processors.UnicodeDecoder(),
            # Добавление контекста приложения
            add_app_context,
            # JSON рендеринг для Loki
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Возвращаем logger
    return structlog.get_logger()


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Получить logger с указанным именем.
    
    Args:
        name: Имя модуля/компонента
        
    Returns:
        Настроенный logger
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger()


# Настройка при импорте модуля
logger = setup_logging()


# Пример использования:
if __name__ == "__main__":
    log = get_logger("example")
    
    log.info("application_started", version="1.0.0")
    log.debug("debug_message", key="value")
    log.warning("warning_occurred", reason="example")
    
    try:
        raise ValueError("Test exception")
    except Exception:
        log.exception("error_occurred", operation="test")
