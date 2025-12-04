"""
Административная панель на базе sqladmin для FastAPI.

Модуль предоставляет веб-интерфейс для управления:
- Пользователями и ролями
- Аудит-логами действий администраторов

Требования:
- sqladmin>=0.16.0
- SQLAlchemy 2.0+
- starlette[full] (для сессий)

Использование:
    from src.admin import setup_admin
    setup_admin(app, engine)

Автор: Sattva Team
Дата: 2025-12-01
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from sqlalchemy.ext.asyncio import AsyncEngine


async def setup_admin(app: "FastAPI", engine: "AsyncEngine") -> None:
    """
    Настройка и монтирование административной панели.

    Args:
        app: Экземпляр FastAPI приложения
        engine: Асинхронный движок SQLAlchemy

    Монтирует sqladmin на /admin с:
    - Аутентификацией через AdminAuth
    - Views для User и AdminAuditLog моделей
    - Аудит-логированием всех действий
    """
    from sqladmin import Admin
    from starlette.middleware.sessions import SessionMiddleware

    from src.admin.auth import AdminAuth
    from src.admin.views import ALL_MODEL_VIEWS
    from src.config import settings

    # Добавляем middleware для сессий (нужен для sqladmin аутентификации)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie="admin_session",
        max_age=3600 * 24,  # 24 часа
        same_site="lax",
        https_only=settings.ENVIRONMENT == "production"
    )

    # Создаём экземпляр Admin с аутентификацией
    admin = Admin(
        app,
        engine,
        authentication_backend=AdminAuth(secret_key=settings.SECRET_KEY),
        title="Sattva Admin",
        base_url="/admin",
    )

    # Регистрируем все views
    for view_class in ALL_MODEL_VIEWS:
        admin.add_view(view_class)


__all__ = ["setup_admin"]
