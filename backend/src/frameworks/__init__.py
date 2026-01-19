"""
FRAMEWORKS LAYER (Clean Architecture)

Точка входа приложения: HTTP сервер, админ-панель, CLI команды, middleware.
Это самый внешний слой, зависящий от всех остальных.

Правила:
- ✅ МОЖЕТ импортировать из: Infrastructure, Application, Domain
- ✅ МОЖЕТ импортировать: FastAPI, Click, любые фреймворки

Структура:
- http/ - FastAPI приложение (controllers, middleware, app factory, DI dependencies)
- admin/ - Админ-панель (sqladmin)
- cli/ - CLI команды
"""
