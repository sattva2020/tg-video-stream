"""
Common DTOs (Data Transfer Objects)

Общие типы и базовые классы для DTOs.
Используются как строительные блоки для более специфичных DTOs.

**Phase 7**: Clean Architecture - DTO для границ слоёв
**Reference**: specs/025-clean-architecture-rules/tasks.md T067
"""

from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar, Generic, List, Optional
from enum import Enum


# Generic type for paginated responses
T = TypeVar('T')


class SortOrder(str, Enum):
    """Порядок сортировки."""
    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class PaginationRequest:
    """
    Параметры пагинации для списковых запросов.
    
    Attributes:
        page: Номер страницы (1-based)
        per_page: Количество элементов на странице
        sort_by: Поле для сортировки (optional)
        sort_order: Порядок сортировки (optional)
    """
    page: int = 1
    per_page: int = 20
    sort_by: Optional[str] = None
    sort_order: SortOrder = SortOrder.ASC
    
    def __post_init__(self):
        """Валидация параметров пагинации."""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.per_page < 1 or self.per_page > 100:
            raise ValueError("Per page must be between 1 and 100")
    
    @property
    def offset(self) -> int:
        """Вычисляет offset для SQL LIMIT/OFFSET."""
        return (self.page - 1) * self.per_page


@dataclass(frozen=True)
class PaginationMeta:
    """
    Метаданные пагинации для ответов.
    
    Attributes:
        total: Общее количество элементов
        page: Текущая страница
        per_page: Элементов на странице
        total_pages: Общее количество страниц
        has_next: Есть ли следующая страница
        has_prev: Есть ли предыдущая страница
    """
    total: int
    page: int
    per_page: int
    
    @property
    def total_pages(self) -> int:
        """Вычисляет общее количество страниц."""
        return (self.total + self.per_page - 1) // self.per_page if self.per_page > 0 else 0
    
    @property
    def has_next(self) -> bool:
        """Проверяет наличие следующей страницы."""
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        """Проверяет наличие предыдущей страницы."""
        return self.page > 1


@dataclass(frozen=True)
class PaginatedResponse(Generic[T]):
    """
    Обёртка для пагинированных ответов.
    
    Attributes:
        items: Список элементов текущей страницы
        meta: Метаданные пагинации
    """
    items: List[T]
    meta: PaginationMeta


@dataclass(frozen=True)
class ErrorResponse:
    """
    Стандартный ответ об ошибке.
    
    Attributes:
        code: Код ошибки (строковый идентификатор)
        message: Человекочитаемое сообщение об ошибке
        details: Дополнительные детали (optional)
        timestamp: Время возникновения ошибки
    """
    code: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        """Устанавливает timestamp если не задан."""
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.utcnow())


@dataclass(frozen=True)
class SuccessResponse:
    """
    Стандартный успешный ответ без данных.
    
    Attributes:
        success: Всегда True
        message: Опциональное сообщение
    """
    success: bool = True
    message: Optional[str] = None


@dataclass(frozen=True)
class IdResponse:
    """
    Ответ с ID созданного/изменённого ресурса.
    
    Attributes:
        id: ID ресурса (int или str)
    """
    id: int | str


@dataclass(frozen=True)
class TimestampedMixin:
    """
    Mixin для DTOs с временными метками.
    
    Attributes:
        created_at: Время создания
        updated_at: Время последнего обновления (optional)
    """
    created_at: datetime
    updated_at: Optional[datetime] = None


# Type aliases for common patterns
UserId = int
StreamId = int
PlaylistId = int
TrackId = int
ChatId = int | str  # может быть username с @
