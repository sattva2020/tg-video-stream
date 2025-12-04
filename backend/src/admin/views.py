"""
Views для административной панели sqladmin.

Определяет ModelView классы для каждой сущности:
- UserAdmin: управление пользователями
- AdminAuditLogAdmin: просмотр аудит-логов

Каждый view настраивает:
- Отображаемые колонки
- Поиск и фильтрацию
- Права на CRUD операции
- Экспорт данных
- Аудит логирование изменений
"""

import logging
from typing import Any, TYPE_CHECKING

from sqladmin import ModelView
from starlette.requests import Request

from src.models.user import User
from src.models.audit_log import AdminAuditLog
from src.models.playlist import PlaylistItem

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class UserAdmin(ModelView, model=User):
    """
    Административный view для управления пользователями.

    Возможности:
    - Просмотр всех пользователей
    - Изменение ролей (admin, moderator, user)
    - Изменение статусов (pending, approved, rejected)
    - Экспорт в CSV

    Ограничения:
    - Нельзя удалить последнего superadmin
    - Нельзя менять собственную роль
    """

    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

    # Колонки для списка
    column_list = [
        User.id,
        User.email,
        User.telegram_id,
        User.telegram_username,
        User.full_name,
        User.role,
        User.status,
        User.email_verified,
        User.created_at,
    ]

    # Детальный просмотр
    column_details_list = [
        User.id,
        User.email,
        User.google_id,
        User.telegram_id,
        User.telegram_username,
        User.full_name,
        User.profile_picture_url,
        User.role,
        User.status,
        User.email_verified,
        User.created_at,
        User.updated_at,
    ]

    # Поля для поиска
    column_searchable_list = [
        User.email,
        User.telegram_username,
        User.full_name,
    ]

    # Фильтры
    column_filters = [
        User.role,
        User.status,
        User.email_verified,
        User.created_at,
    ]

    # Сортировка
    column_sortable_list = [
        User.email,
        User.role,
        User.status,
        User.created_at,
    ]

    # Сортировка по умолчанию
    column_default_sort = [(User.created_at, True)]

    # Редактируемые поля
    form_columns = [
        User.email,
        User.full_name,
        User.role,
        User.status,
        User.email_verified,
    ]

    # Исключенные из формы
    form_excluded_columns = [
        User.id,
        User.google_id,
        User.telegram_id,
        User.hashed_password,
        User.created_at,
        User.updated_at,
        User.audit_logs,
    ]

    # Права доступа
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True
    export_max_rows = 10000

    # Пагинация
    page_size = 25
    page_size_options = [25, 50, 100]

    # Лейблы колонок
    column_labels = {
        User.id: "ID",
        User.email: "Email",
        User.telegram_id: "Telegram ID",
        User.telegram_username: "Telegram Username",
        User.full_name: "Full Name",
        User.role: "Role",
        User.status: "Status",
        User.email_verified: "Email Verified",
        User.created_at: "Created At",
        User.updated_at: "Updated At",
    }

    async def on_model_change(self, data: dict, model: Any, is_created: bool, request: Request) -> None:
        """Логирование изменений пользователя."""
        action = "create" if is_created else "update"
        user_id = request.session.get("admin_user_id")
        
        if user_id:
            try:
                from src.admin.auth import AdminAuth
                from src.config import settings
                auth = AdminAuth(secret_key=settings.SECRET_KEY)
                await auth._log_admin_action(
                    user_id=user_id,
                    action=action,
                    resource_type="user",
                    resource_id=str(model.id),
                    details=f"User {'created' if is_created else 'updated'}: {model.email or model.telegram_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to log admin action: {e}")

    async def on_model_delete(self, model: Any, request: Request) -> None:
        """Логирование удаления пользователя."""
        user_id = request.session.get("admin_user_id")
        
        if user_id:
            try:
                from src.admin.auth import AdminAuth
                from src.config import settings
                auth = AdminAuth(secret_key=settings.SECRET_KEY)
                await auth._log_admin_action(
                    user_id=user_id,
                    action="delete",
                    resource_type="user",
                    resource_id=str(model.id),
                    details=f"User deleted: {model.email or model.telegram_id}"
                )
            except Exception as e:
                logger.warning(f"Failed to log admin action: {e}")


class AdminAuditLogAdmin(ModelView, model=AdminAuditLog):
    """
    View для просмотра аудит-логов действий администраторов.

    Только чтение - логи неизменяемы.

    Показывает:
    - Кто выполнил действие
    - Какое действие
    - На какой сущности
    - Когда
    - Детали изменений
    """

    name = "Audit Log"
    name_plural = "Audit Logs"
    icon = "fa-solid fa-clipboard-list"

    # Колонки для списка
    column_list = [
        AdminAuditLog.id,
        AdminAuditLog.user_id,
        AdminAuditLog.action,
        AdminAuditLog.resource_type,
        AdminAuditLog.resource_id,
        AdminAuditLog.ip_address,
        AdminAuditLog.timestamp,
    ]

    # Детальный просмотр
    column_details_list = [
        AdminAuditLog.id,
        AdminAuditLog.user_id,
        AdminAuditLog.action,
        AdminAuditLog.resource_type,
        AdminAuditLog.resource_id,
        AdminAuditLog.details,
        AdminAuditLog.ip_address,
        AdminAuditLog.user_agent,
        AdminAuditLog.timestamp,
    ]

    # Поиск
    column_searchable_list = [
        AdminAuditLog.action,
        AdminAuditLog.resource_type,
        AdminAuditLog.details,
    ]

    # Фильтры
    column_filters = [
        AdminAuditLog.action,
        AdminAuditLog.resource_type,
        AdminAuditLog.timestamp,
    ]

    # Сортировка
    column_sortable_list = [
        AdminAuditLog.action,
        AdminAuditLog.resource_type,
        AdminAuditLog.timestamp,
    ]

    # Сортировка по умолчанию - новые первые
    column_default_sort = [(AdminAuditLog.timestamp, True)]

    # Логи только для чтения
    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True
    can_export = True
    export_max_rows = 50000

    # Пагинация
    page_size = 50
    page_size_options = [50, 100, 200]

    # Лейблы
    column_labels = {
        AdminAuditLog.id: "ID",
        AdminAuditLog.user_id: "User ID",
        AdminAuditLog.action: "Action",
        AdminAuditLog.resource_type: "Resource Type",
        AdminAuditLog.resource_id: "Resource ID",
        AdminAuditLog.details: "Details",
        AdminAuditLog.ip_address: "IP Address",
        AdminAuditLog.user_agent: "User Agent",
        AdminAuditLog.timestamp: "Timestamp",
    }


class PlaylistItemAdmin(ModelView, model=PlaylistItem):
    """
    Административный view для управления элементами плейлиста.

    Возможности:
    - Просмотр всех треков
    - Изменение позиции в очереди
    - Изменение статуса
    - Удаление треков
    """

    name = "Playlist Item"
    name_plural = "Playlist Items"
    icon = "fa-solid fa-music"

    # Колонки для списка
    column_list = [
        PlaylistItem.id,
        PlaylistItem.title,
        PlaylistItem.url,
        PlaylistItem.type,
        PlaylistItem.status,
        PlaylistItem.duration,
        PlaylistItem.position,
        PlaylistItem.created_at,
    ]

    # Детальный просмотр
    column_details_list = [
        PlaylistItem.id,
        PlaylistItem.channel_id,
        PlaylistItem.url,
        PlaylistItem.title,
        PlaylistItem.type,
        PlaylistItem.status,
        PlaylistItem.duration,
        PlaylistItem.position,
        PlaylistItem.created_by,
        PlaylistItem.created_at,
    ]

    # Поля для поиска
    column_searchable_list = [
        PlaylistItem.title,
        PlaylistItem.url,
    ]

    # Фильтры
    column_filters = [
        PlaylistItem.type,
        PlaylistItem.status,
        PlaylistItem.created_at,
    ]

    # Сортировка
    column_sortable_list = [
        PlaylistItem.title,
        PlaylistItem.type,
        PlaylistItem.status,
        PlaylistItem.position,
        PlaylistItem.created_at,
    ]

    # Сортировка по умолчанию
    column_default_sort = [(PlaylistItem.position, False)]

    # Редактируемые поля
    form_columns = [
        PlaylistItem.title,
        PlaylistItem.url,
        PlaylistItem.type,
        PlaylistItem.status,
        PlaylistItem.position,
    ]

    # Права доступа
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True
    can_export = True

    # Пагинация
    page_size = 50
    page_size_options = [50, 100, 200]

    # Лейблы
    column_labels = {
        PlaylistItem.id: "ID",
        PlaylistItem.channel_id: "Channel ID",
        PlaylistItem.url: "URL",
        PlaylistItem.title: "Title",
        PlaylistItem.type: "Type",
        PlaylistItem.status: "Status",
        PlaylistItem.duration: "Duration (sec)",
        PlaylistItem.position: "Position",
        PlaylistItem.created_by: "Created By",
        PlaylistItem.created_at: "Created At",
    }

    async def on_model_change(self, data: dict, model: Any, is_created: bool, request: Request) -> None:
        """Логирование изменений плейлиста."""
        action = "create" if is_created else "update"
        user_id = request.session.get("admin_user_id")
        
        if user_id:
            try:
                from src.admin.auth import AdminAuth
                from src.config import settings
                auth = AdminAuth(secret_key=settings.SECRET_KEY)
                await auth._log_admin_action(
                    user_id=user_id,
                    action=action,
                    resource_type="playlist_item",
                    resource_id=str(model.id),
                    details=f"PlaylistItem {'created' if is_created else 'updated'}: {model.title or model.url}"
                )
            except Exception as e:
                logger.warning(f"Failed to log admin action: {e}")


# Список всех ModelView для регистрации в Admin
ALL_MODEL_VIEWS = [
    UserAdmin,
    PlaylistItemAdmin,
    AdminAuditLogAdmin,
]
