"""
Use Case Example - Clean Architecture

Пример Use Case с Result Pattern и Dependency Injection.
"""

from dataclasses import dataclass
from typing import Protocol, Optional
from abc import abstractmethod

from src.shared.kernel.result import Result


# ========================
# DTOs (Application Layer)
# ========================

@dataclass(frozen=True)
class CreateOrderRequest:
    """Request DTO для создания заказа."""
    customer_id: int
    items: list[dict]  # [{"product_id": 1, "quantity": 2}]


@dataclass(frozen=True)
class CreateOrderResponse:
    """Response DTO."""
    order_id: int
    total_amount: int
    status: str


# ========================
# Ports (Application Layer Interfaces)
# ========================

class IOrderRepository(Protocol):
    """Порт для репозитория заказов."""
    
    @abstractmethod
    async def save(self, order) -> int:
        """Сохраняет заказ и возвращает ID."""
        ...
    
    @abstractmethod
    async def find_by_id(self, order_id: int):
        """Находит заказ по ID."""
        ...


class IProductService(Protocol):
    """Порт для сервиса продуктов."""
    
    @abstractmethod
    async def get_price(self, product_id: int) -> Optional[int]:
        """Возвращает цену продукта в копейках."""
        ...
    
    @abstractmethod
    async def check_availability(self, product_id: int, quantity: int) -> bool:
        """Проверяет наличие товара."""
        ...


class INotificationService(Protocol):
    """Порт для уведомлений."""
    
    @abstractmethod
    async def notify_order_created(self, order_id: int, customer_id: int) -> None:
        """Отправляет уведомление о создании заказа."""
        ...


# ========================
# Domain Errors
# ========================

@dataclass(frozen=True)
class OrderError:
    """Базовая ошибка заказа."""
    message: str


@dataclass(frozen=True)
class ProductNotFoundError(OrderError):
    """Продукт не найден."""
    product_id: int


@dataclass(frozen=True)
class InsufficientStockError(OrderError):
    """Недостаточно товара на складе."""
    product_id: int
    requested: int
    available: int


@dataclass(frozen=True)
class EmptyOrderError(OrderError):
    """Пустой заказ."""
    pass


# ========================
# Use Case
# ========================

class CreateOrderUseCase:
    """
    Use Case: Создание заказа
    
    Демонстрирует:
    - Dependency Injection через конструктор
    - Result Pattern для обработки ошибок
    - Оркестрация нескольких сервисов
    - Чистое разделение ответственности
    """
    
    def __init__(
        self,
        order_repository: IOrderRepository,
        product_service: IProductService,
        notification_service: INotificationService
    ):
        self._order_repository = order_repository
        self._product_service = product_service
        self._notification_service = notification_service
    
    async def execute(
        self, 
        request: CreateOrderRequest
    ) -> Result[CreateOrderResponse, OrderError]:
        """
        Выполняет создание заказа.
        
        Шаги:
        1. Валидация входных данных
        2. Проверка наличия товаров
        3. Создание доменной сущности Order
        4. Сохранение в репозитории
        5. Отправка уведомления
        
        Returns:
            Result[CreateOrderResponse, OrderError]
        """
        
        # 1. Валидация
        if not request.items:
            return Result.failure(EmptyOrderError(
                message="Order must contain at least one item"
            ))
        
        # 2. Проверка наличия и цен
        order_items = []
        total_amount = 0
        
        for item in request.items:
            product_id = item["product_id"]
            quantity = item["quantity"]
            
            # Получаем цену
            price = await self._product_service.get_price(product_id)
            if price is None:
                return Result.failure(ProductNotFoundError(
                    message=f"Product {product_id} not found",
                    product_id=product_id
                ))
            
            # Проверяем наличие
            is_available = await self._product_service.check_availability(
                product_id, quantity
            )
            if not is_available:
                return Result.failure(InsufficientStockError(
                    message=f"Product {product_id} is out of stock",
                    product_id=product_id,
                    requested=quantity,
                    available=0  # В реальности получили бы реальное значение
                ))
            
            order_items.append({
                "product_id": product_id,
                "quantity": quantity,
                "price": price
            })
            total_amount += price * quantity
        
        # 3. Создание доменной сущности
        # (В реальном коде здесь был бы Order.create(...))
        order_data = {
            "customer_id": request.customer_id,
            "items": order_items,
            "total": total_amount,
            "status": "pending"
        }
        
        # 4. Сохранение
        order_id = await self._order_repository.save(order_data)
        
        # 5. Уведомление (fire-and-forget, не влияет на результат)
        try:
            await self._notification_service.notify_order_created(
                order_id=order_id,
                customer_id=request.customer_id
            )
        except Exception:
            # Логируем, но не прерываем операцию
            pass
        
        # Успешный результат
        return Result.success(CreateOrderResponse(
            order_id=order_id,
            total_amount=total_amount,
            status="pending"
        ))


# ========================
# Usage Example (with mocks)
# ========================

class MockOrderRepository:
    """Mock репозитория для тестов."""
    
    async def save(self, order) -> int:
        return 42
    
    async def find_by_id(self, order_id: int):
        return None


class MockProductService:
    """Mock сервиса продуктов."""
    
    async def get_price(self, product_id: int) -> Optional[int]:
        prices = {1: 1000, 2: 2500, 3: 500}
        return prices.get(product_id)
    
    async def check_availability(self, product_id: int, quantity: int) -> bool:
        return product_id != 999  # 999 = out of stock


class MockNotificationService:
    """Mock сервиса уведомлений."""
    
    async def notify_order_created(self, order_id: int, customer_id: int) -> None:
        print(f"[Mock] Notification sent: order {order_id} for customer {customer_id}")


async def main():
    """Демонстрация использования Use Case."""
    
    # Создаём Use Case с mock зависимостями
    use_case = CreateOrderUseCase(
        order_repository=MockOrderRepository(),
        product_service=MockProductService(),
        notification_service=MockNotificationService()
    )
    
    # Успешный сценарий
    request = CreateOrderRequest(
        customer_id=1,
        items=[
            {"product_id": 1, "quantity": 2},
            {"product_id": 2, "quantity": 1}
        ]
    )
    
    result = await use_case.execute(request)
    
    if result.is_success:
        response = result.value
        print(f"Order created: #{response.order_id}")
        print(f"Total: {response.total_amount / 100:.2f} ₽")
        print(f"Status: {response.status}")
    else:
        error = result.error
        print(f"Error: {error.message}")
    
    # Сценарий с ошибкой - продукт не найден
    bad_request = CreateOrderRequest(
        customer_id=1,
        items=[{"product_id": 999, "quantity": 1}]
    )
    
    result = await use_case.execute(bad_request)
    
    if result.is_failure:
        error = result.error
        print(f"\nExpected error: {error.message}")
        if isinstance(error, ProductNotFoundError):
            print(f"Product ID: {error.product_id}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
