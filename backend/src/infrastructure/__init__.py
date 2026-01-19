"""
INFRASTRUCTURE LAYER (Clean Architecture)

Реализации технических деталей: работа с БД, внешними сервисами, файловой системой.
Этот слой реализует интерфейсы (порты) из Application Layer.

Правила:
- ✅ МОЖЕТ импортировать из: Application Layer, Domain Layer
- ❌ НЕ МОЖЕТ импортировать из: Frameworks Layer
- ✅ МОЖЕТ импортировать: SQLAlchemy, Redis, внешние клиенты

Структура:
- persistence/ - Работа с БД (репозитории, маппер Entity↔ORM)
- external/ - Интеграция с внешними API (Telegram, сторонние сервисы)
- messaging/ - Event Bus, очереди сообщений
- security/ - Хеширование паролей, криптография
"""
