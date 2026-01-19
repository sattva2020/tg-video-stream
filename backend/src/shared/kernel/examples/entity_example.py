"""
Entity Example - Clean Architecture

Пример доменной сущности с использованием Value Objects и бизнес-логики.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from src.shared.kernel.value_object import ValueObject


# ========================
# Value Objects
# ========================

class Money(ValueObject):
    """Value Object для денежных значений."""
    
    amount: int  # в копейках для точности
    currency: str = "RUB"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if self.currency not in ("RUB", "USD", "EUR"):
            raise ValueError(f"Unsupported currency: {self.currency}")
    
    def add(self, other: "Money") -> "Money":
        """Сложение денег (той же валюты)."""
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)
    
    def to_display(self) -> str:
        """Человекочитаемый формат."""
        symbols = {"RUB": "₽", "USD": "$", "EUR": "€"}
        return f"{self.amount / 100:.2f} {symbols[self.currency]}"


class ProductId(ValueObject):
    """Value Object для ID продукта."""
    
    value: int
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("ProductId must be non-negative")


# ========================
# Entity
# ========================

class OrderStatus(Enum):
    """Статусы заказа."""
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass
class OrderItem:
    """Элемент заказа (не отдельная сущность, часть агрегата)."""
    
    product_id: ProductId
    quantity: int
    unit_price: Money
    
    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
    
    @property
    def total(self) -> Money:
        """Общая стоимость позиции."""
        return Money(
            amount=self.unit_price.amount * self.quantity,
            currency=self.unit_price.currency
        )


@dataclass
class Order:
    """
    Order - Aggregate Root
    
    Демонстрирует:
    - Identity (id)
    - Value Objects (Money, ProductId)
    - Бизнес-правила (add_item, cancel)
    - Защита инвариантов (статусы)
    """
    
    id: int
    customer_id: int
    status: OrderStatus = OrderStatus.DRAFT
    items: list[OrderItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cancelled_at: Optional[datetime] = None
    
    # ========================
    # Factory Methods
    # ========================
    
    @classmethod
    def create(cls, customer_id: int) -> "Order":
        """Фабричный метод для создания нового заказа."""
        return cls(id=0, customer_id=customer_id)
    
    @classmethod
    def reconstitute(
        cls,
        id: int,
        customer_id: int,
        status: OrderStatus,
        items: list[OrderItem],
        created_at: datetime,
        cancelled_at: Optional[datetime] = None
    ) -> "Order":
        """Восстановление сущности из хранилища (bypasses business rules)."""
        order = cls(id=id, customer_id=customer_id)
        order.status = status
        order.items = items
        order.created_at = created_at
        order.cancelled_at = cancelled_at
        return order
    
    # ========================
    # Business Logic
    # ========================
    
    def add_item(self, product_id: ProductId, quantity: int, unit_price: Money) -> None:
        """
        Добавляет позицию в заказ.
        
        Бизнес-правило: Можно добавлять только в draft заказы.
        """
        if self.status != OrderStatus.DRAFT:
            raise ValueError(f"Cannot add items to order in status {self.status.value}")
        
        # Проверяем, есть ли уже такой продукт
        for item in self.items:
            if item.product_id == product_id:
                # Увеличиваем количество
                item.quantity += quantity
                return
        
        # Добавляем новую позицию
        self.items.append(OrderItem(
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price
        ))
    
    def remove_item(self, product_id: ProductId) -> None:
        """Удаляет позицию из заказа."""
        if self.status != OrderStatus.DRAFT:
            raise ValueError(f"Cannot remove items from order in status {self.status.value}")
        
        self.items = [item for item in self.items if item.product_id != product_id]
    
    def submit(self) -> None:
        """
        Отправляет заказ на обработку.
        
        Бизнес-правила:
        - Заказ должен быть в статусе DRAFT
        - Заказ должен содержать хотя бы одну позицию
        """
        if self.status != OrderStatus.DRAFT:
            raise ValueError(f"Cannot submit order in status {self.status.value}")
        
        if not self.items:
            raise ValueError("Cannot submit empty order")
        
        self.status = OrderStatus.PENDING
    
    def mark_as_paid(self) -> None:
        """Отмечает заказ как оплаченный."""
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot mark as paid order in status {self.status.value}")
        
        self.status = OrderStatus.PAID
    
    def cancel(self, reason: str = "") -> None:
        """
        Отменяет заказ.
        
        Бизнес-правило: Нельзя отменить доставленный заказ.
        """
        if self.status == OrderStatus.DELIVERED:
            raise ValueError("Cannot cancel delivered order")
        
        if self.status == OrderStatus.CANCELLED:
            raise ValueError("Order is already cancelled")
        
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
    
    # ========================
    # Computed Properties
    # ========================
    
    @property
    def total(self) -> Money:
        """Общая сумма заказа."""
        if not self.items:
            return Money(amount=0, currency="RUB")
        
        total = self.items[0].total
        for item in self.items[1:]:
            total = total.add(item.total)
        return total
    
    @property
    def is_cancellable(self) -> bool:
        """Можно ли отменить заказ."""
        return self.status not in (OrderStatus.DELIVERED, OrderStatus.CANCELLED)
    
    @property
    def item_count(self) -> int:
        """Количество позиций в заказе."""
        return len(self.items)


# ========================
# Usage Example
# ========================

if __name__ == "__main__":
    # Создание заказа
    order = Order.create(customer_id=1)
    print(f"Created order: {order.id}, status: {order.status.value}")
    
    # Добавление товаров
    order.add_item(
        product_id=ProductId(value=100),
        quantity=2,
        unit_price=Money(amount=1500)  # 15.00 ₽
    )
    order.add_item(
        product_id=ProductId(value=200),
        quantity=1,
        unit_price=Money(amount=3000)  # 30.00 ₽
    )
    print(f"Order total: {order.total.to_display()}")  # 60.00 ₽
    print(f"Item count: {order.item_count}")
    
    # Отправка заказа
    order.submit()
    print(f"Order submitted, status: {order.status.value}")
    
    # Попытка добавить товар после отправки (ошибка!)
    try:
        order.add_item(ProductId(value=300), 1, Money(amount=500))
    except ValueError as e:
        print(f"Error: {e}")  # Cannot add items to order in status pending
    
    # Оплата
    order.mark_as_paid()
    print(f"Order paid, status: {order.status.value}")
