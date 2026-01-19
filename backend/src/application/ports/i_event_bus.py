"""
IEventBus Port Interface

Контракт для публикации доменных событий.
"""

from typing import Protocol
from src.shared.kernel.domain_event import DomainEvent


class IEventBus(Protocol):
    """
    Интерфейс шины событий для публикации Domain Events.
    
    Изолирует Application layer от конкретной реализации (Redis, RabbitMQ, in-memory).
    Позволяет реагировать на доменные события асинхронно.
    
    Domain Events используются для:
    - Интеграции между модулями
    - Логирования важных бизнес-действий
    - Триггеров для фоновых задач
    - Аудита системы
    
    Examples:
        >>> event = UserCreatedEvent(user_id=user.id, email=user.email)
        >>> await event_bus.publish(event)
    """
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Опубликовать доменное событие.
        
        Событие будет обработано всеми подписчиками асинхронно.
        Use Case не блокируется на ожидании обработки события.
        
        Args:
            event: Доменное событие для публикации
            
        Raises:
            EventBusError: При ошибке публикации события
        """
        ...
    
    async def publish_many(self, events: list[DomainEvent]) -> None:
        """
        Опубликовать несколько доменных событий.
        
        Batch публикация для оптимизации производительности.
        
        Args:
            events: Список доменных событий для публикации
            
        Raises:
            EventBusError: При ошибке публикации событий
        """
        ...
