"""
Redis реализация Event Bus для доменных событий.

Этот модуль реализует IEventBus port используя Redis Pub/Sub.
"""

import json
from typing import Any
from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.application.ports.i_event_bus import IEventBus
from src.shared.kernel.domain_event import DomainEvent
from src.domain.errors import EventBusError


class RedisEventBus:
    """
    Redis Pub/Sub реализация IEventBus.
    
    Использует Redis channels для публикации доменных событий.
    События сериализуются в JSON перед отправкой.
    """
    
    def __init__(
        self,
        redis_client: Redis,
        channel_prefix: str = "domain_events"
    ):
        """
        Инициализация event bus.
        
        Args:
            redis_client: Async Redis клиент
            channel_prefix: Префикс для Redis channels (default: "domain_events")
        """
        self._redis = redis_client
        self._channel_prefix = channel_prefix
    
    async def publish(self, event: DomainEvent) -> None:
        """
        Опубликовать доменное событие в Redis.
        
        Событие публикуется в канал: domain_events:{event_type}
        Например: domain_events:user_created
        
        Args:
            event: Доменное событие для публикации
            
        Raises:
            EventBusError: При ошибке публикации события
        """
        try:
            # Формируем channel name
            event_type = event.__class__.__name__.lower()
            channel = f"{self._channel_prefix}:{event_type}"
            
            # Сериализуем событие в JSON
            event_data = self._serialize_event(event)
            
            # Публикуем в Redis
            await self._redis.publish(channel, json.dumps(event_data))
            
        except RedisError as e:
            raise EventBusError(f"Failed to publish event {event}: {e}") from e
        except Exception as e:
            raise EventBusError(f"Unexpected error publishing event: {e}") from e
    
    async def publish_many(self, events: list[DomainEvent]) -> None:
        """
        Опубликовать несколько доменных событий.
        
        Использует Redis pipeline для batch публикации.
        
        Args:
            events: Список доменных событий для публикации
            
        Raises:
            EventBusError: При ошибке публикации событий
        """
        if not events:
            return
        
        try:
            # Используем pipeline для batch операций
            async with self._redis.pipeline() as pipe:
                for event in events:
                    event_type = event.__class__.__name__.lower()
                    channel = f"{self._channel_prefix}:{event_type}"
                    event_data = self._serialize_event(event)
                    
                    pipe.publish(channel, json.dumps(event_data))
                
                # Выполняем все публикации одной транзакцией
                await pipe.execute()
                
        except RedisError as e:
            raise EventBusError(f"Failed to publish events batch: {e}") from e
        except Exception as e:
            raise EventBusError(f"Unexpected error publishing events: {e}") from e
    
    def _serialize_event(self, event: DomainEvent) -> dict[str, Any]:
        """
        Сериализовать доменное событие в dict для JSON.
        
        Args:
            event: Доменное событие
            
        Returns:
            Dict с данными события
        """
        # Базовые поля
        data = {
            "event_type": event.__class__.__name__,
            "occurred_at": event.occurred_at.isoformat(),
            "aggregate_id": str(event.aggregate_id) if hasattr(event, 'aggregate_id') else None,
        }
        
        # Добавляем поля события (кроме служебных)
        event_fields = {
            k: self._serialize_value(v)
            for k, v in event.__dict__.items()
            if not k.startswith('_') and k not in ['occurred_at']
        }
        data.update(event_fields)
        
        return data
    
    def _serialize_value(self, value: Any) -> Any:
        """
        Сериализовать значение для JSON.
        
        Обрабатывает Value Objects, UUID, datetime и другие типы.
        """
        # Value Objects (имеют .value атрибут)
        if hasattr(value, 'value'):
            return str(value.value)
        
        # UUID
        if hasattr(value, 'hex'):
            return str(value)
        
        # Datetime
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        
        # Enum
        if hasattr(value, 'name') and hasattr(value, 'value'):
            return value.value
        
        # Default: as-is
        return value
