"""
Repository Example - Clean Architecture

Пример Repository Pattern с маппингом Entity ↔ ORM Model.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Generic, TypeVar
from enum import Enum


# ========================
# Domain Layer
# ========================

class OrderStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"


@dataclass
class Order:
    """Доменная сущность Order."""
    id: int
    customer_id: int
    total_amount: int
    status: OrderStatus
    created_at: datetime


T = TypeVar("T")


# ========================
# Port (Application Layer Interface)
# ========================

class IOrderRepository(ABC, Generic[T]):
    """
    Порт репозитория - определяется в Application Layer.
    
    Контракт:
    - Работает с доменными сущностями (Order)
    - НЕ знает о БД, ORM, SQL
    - Реализуется в Infrastructure Layer
    """
    
    @abstractmethod
    async def save(self, order: Order) -> Order:
        """Сохраняет заказ (insert или update)."""
        ...
    
    @abstractmethod
    async def find_by_id(self, order_id: int) -> Optional[Order]:
        """Находит заказ по ID."""
        ...
    
    @abstractmethod
    async def find_by_customer(self, customer_id: int) -> List[Order]:
        """Находит все заказы клиента."""
        ...
    
    @abstractmethod
    async def delete(self, order_id: int) -> bool:
        """Удаляет заказ. Возвращает True если удалён."""
        ...


# ========================
# ORM Model (Infrastructure Layer)
# ========================

@dataclass
class OrderModel:
    """
    ORM Model - представление в базе данных.
    
    В реальном проекте это был бы SQLAlchemy model:
    
    class OrderModel(Base):
        __tablename__ = "orders"
        id = Column(Integer, primary_key=True)
        ...
    """
    id: Optional[int]
    customer_id: int
    total_amount: int
    status: str  # В БД хранится как строка
    created_at: datetime


# ========================
# Mapper (Infrastructure Layer)
# ========================

class OrderMapper:
    """
    Mapper - преобразует Entity ↔ ORM Model.
    
    Ответственности:
    - Изолирует домен от деталей persistence
    - Обрабатывает различия в типах (enum ↔ str)
    - Конвертирует списки
    """
    
    @staticmethod
    def to_entity(model: OrderModel) -> Order:
        """ORM Model → Domain Entity."""
        return Order(
            id=model.id or 0,
            customer_id=model.customer_id,
            total_amount=model.total_amount,
            status=OrderStatus(model.status),
            created_at=model.created_at
        )
    
    @staticmethod
    def to_model(entity: Order) -> OrderModel:
        """Domain Entity → ORM Model."""
        return OrderModel(
            id=entity.id if entity.id != 0 else None,
            customer_id=entity.customer_id,
            total_amount=entity.total_amount,
            status=entity.status.value,  # Enum → str
            created_at=entity.created_at
        )
    
    @staticmethod
    def to_entity_list(models: List[OrderModel]) -> List[Order]:
        """Список ORM → список Entity."""
        return [OrderMapper.to_entity(m) for m in models]


# ========================
# Repository Implementation (Infrastructure Layer)
# ========================

class InMemoryOrderRepository(IOrderRepository[Order]):
    """
    In-Memory реализация репозитория для тестов.
    
    Преимущества:
    - Быстрые unit-тесты (без БД)
    - Контролируемое состояние
    - Простая отладка
    """
    
    def __init__(self):
        self._orders: dict[int, OrderModel] = {}
        self._next_id = 1
    
    async def save(self, order: Order) -> Order:
        model = OrderMapper.to_model(order)
        
        if model.id is None:
            # Insert
            model.id = self._next_id
            self._next_id += 1
        
        self._orders[model.id] = model
        return OrderMapper.to_entity(model)
    
    async def find_by_id(self, order_id: int) -> Optional[Order]:
        model = self._orders.get(order_id)
        return OrderMapper.to_entity(model) if model else None
    
    async def find_by_customer(self, customer_id: int) -> List[Order]:
        models = [
            m for m in self._orders.values() 
            if m.customer_id == customer_id
        ]
        return OrderMapper.to_entity_list(models)
    
    async def delete(self, order_id: int) -> bool:
        if order_id in self._orders:
            del self._orders[order_id]
            return True
        return False


class SqlAlchemyOrderRepository(IOrderRepository[Order]):
    """
    SQLAlchemy реализация репозитория.
    
    Примечание: Это упрощённая демонстрация.
    В реальном проекте используется AsyncSession.
    """
    
    def __init__(self, session):
        self._session = session
        self._mapper = OrderMapper()
    
    async def save(self, order: Order) -> Order:
        model = self._mapper.to_model(order)
        
        if model.id is None:
            # Insert
            self._session.add(model)
            await self._session.flush()
        else:
            # Update
            existing = await self._session.get(OrderModel, model.id)
            if existing:
                existing.customer_id = model.customer_id
                existing.total_amount = model.total_amount
                existing.status = model.status
        
        await self._session.commit()
        return self._mapper.to_entity(model)
    
    async def find_by_id(self, order_id: int) -> Optional[Order]:
        model = await self._session.get(OrderModel, order_id)
        return self._mapper.to_entity(model) if model else None
    
    async def find_by_customer(self, customer_id: int) -> List[Order]:
        # В реальности: query().filter(...).all()
        result = await self._session.execute(
            f"SELECT * FROM orders WHERE customer_id = {customer_id}"
        )
        models = result.fetchall()
        return self._mapper.to_entity_list(models)
    
    async def delete(self, order_id: int) -> bool:
        model = await self._session.get(OrderModel, order_id)
        if model:
            self._session.delete(model)
            await self._session.commit()
            return True
        return False


# ========================
# Usage Example
# ========================

async def main():
    """Демонстрация Repository Pattern."""
    
    # Создаём In-Memory репозиторий
    repo: IOrderRepository = InMemoryOrderRepository()
    
    # Создаём заказ
    order = Order(
        id=0,  # Новый заказ
        customer_id=42,
        total_amount=15000,  # 150.00 ₽
        status=OrderStatus.PENDING,
        created_at=datetime.now()
    )
    
    # Сохраняем
    saved_order = await repo.save(order)
    print(f"Saved order: #{saved_order.id}")
    
    # Находим по ID
    found = await repo.find_by_id(saved_order.id)
    if found:
        print(f"Found order: #{found.id}, status: {found.status.value}")
    
    # Находим по клиенту
    customer_orders = await repo.find_by_customer(42)
    print(f"Customer 42 has {len(customer_orders)} orders")
    
    # Обновляем статус
    found.status = OrderStatus.PAID
    await repo.save(found)
    
    updated = await repo.find_by_id(found.id)
    print(f"Updated status: {updated.status.value}")
    
    # Удаляем
    deleted = await repo.delete(found.id)
    print(f"Deleted: {deleted}")
    
    # Проверяем удаление
    not_found = await repo.find_by_id(found.id)
    print(f"After delete: {not_found}")  # None


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
