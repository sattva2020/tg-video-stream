"""
APPLICATION LAYER (Clean Architecture)

Use Cases и Application Services, которые оркеструют бизнес-логику.
Этот слой координирует выполнение бизнес-правил из Domain Layer.

Правила:
- ✅ МОЖЕТ импортировать из: Domain Layer
- ❌ НЕ МОЖЕТ импортировать из: Infrastructure Layer, Frameworks Layer
- ❌ НЕ МОЖЕТ импортировать: SQLAlchemy, FastAPI, внешние библиотеки

Структура:
- use_cases/ - Use Cases (сценарии использования)
- ports/ - Интерфейсы для внешних зависимостей (репозитории, сервисы)
- dtos/ - Data Transfer Objects для границ слоя
"""
