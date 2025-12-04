"""
Аутентификация для административной панели sqladmin.

Реализует:
- Проверку прав доступа (admin, superadmin)
- Сессионное хранение авторизации
- Логирование попыток входа
- Аудит действий администраторов

Требования:
- Роли пользователей: admin, moderator, superadmin
- JWT токены из существующей системы аутентификации
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

logger = logging.getLogger(__name__)


class AdminAuth(AuthenticationBackend):
    """
    Backend аутентификации для sqladmin.

    Проверяет что пользователь:
    1. Авторизован (есть валидная сессия)
    2. Имеет роль admin или superadmin

    Attributes:
        secret_key: Секретный ключ для подписи сессий
    """

    def __init__(self, secret_key: str) -> None:
        super().__init__(secret_key)

    async def login(self, request: Request) -> bool:
        """
        Обработка формы входа в админ-панель.

        Проверяет credentials через базу данных и создаёт сессию при успехе.

        Args:
            request: HTTP запрос с данными формы

        Returns:
            True если вход успешен, False иначе
        """
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if not username or not password:
            logger.warning("Admin login attempt without credentials")
            return False

        # Аутентификация через базу данных
        user = await self._authenticate_user(str(username), str(password))
        
        if user is None:
            logger.warning(f"Admin login failed for user: {username}")
            return False

        # Проверка прав администратора
        if not getattr(user, 'is_superuser', False) and getattr(user, 'role', '') not in ('admin', 'superadmin'):
            logger.warning(f"Admin access denied - insufficient role: {username}")
            return False

        # Сохраняем информацию о пользователе в сессии
        request.session.update({
            "admin_user": user.email or str(user.telegram_id),
            "admin_user_id": str(user.id),
            "admin_role": getattr(user, 'role', 'superadmin') if user.is_superuser else getattr(user, 'role', 'admin'),
        })
        
        # Логируем успешный вход
        await self._log_admin_action(
            user_id=str(user.id),
            action="login",
            details=f"Admin login from {request.client.host if request.client else 'unknown'}"
        )
        
        logger.info(f"Admin login successful: {username}")
        return True

    async def logout(self, request: Request) -> bool:
        """
        Выход из админ-панели.

        Очищает сессию и логирует выход.

        Args:
            request: HTTP запрос

        Returns:
            True всегда
        """
        user = request.session.get("admin_user", "unknown")
        user_id = request.session.get("admin_user_id")
        
        if user_id:
            await self._log_admin_action(
                user_id=user_id,
                action="logout",
                details="Admin panel logout"
            )
        
        request.session.clear()
        logger.info(f"Admin logout: {user}")
        return True

    async def authenticate(self, request: Request) -> Optional[RedirectResponse]:
        """
        Проверка авторизации для каждого запроса к админ-панели.

        Args:
            request: HTTP запрос

        Returns:
            None если авторизован, RedirectResponse на /admin/login иначе
        """
        admin_user = request.session.get("admin_user")

        if not admin_user:
            return RedirectResponse(
                url=request.url_for("admin:login"),
                status_code=302,
            )

        # Проверяем что роль позволяет доступ
        admin_role = request.session.get("admin_role", "")
        if admin_role not in ("admin", "superadmin", "moderator"):
            logger.warning(f"Access denied for user {admin_user} with role {admin_role}")
            return RedirectResponse(
                url=request.url_for("admin:login"),
                status_code=302,
            )

        return None


    async def _authenticate_user(self, username: str, password: str):
        """
        Аутентификация пользователя через базу данных.
        
        Args:
            username: Email или telegram_id
            password: Пароль
            
        Returns:
            User объект или None
        """
        try:
            from src.database import SessionLocal
            from src.models.user import User
            from src.services.auth_service import AuthService
            
            db = SessionLocal()
            try:
                # Поиск по email или telegram_id
                user = db.query(User).filter(
                    (User.email == username) | 
                    (User.telegram_id == username)
                ).first()
                
                if user is None:
                    return None
                
                # Проверка пароля
                auth_service = AuthService()
                if not auth_service.verify_password(password, user.hashed_password or ""):
                    return None
                
                return user
                
            finally:
                db.close()
                
        except ImportError as e:
            logger.error(f"Import error during auth: {e}")
            return None
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return None

    async def _get_user_by_id(self, user_id: str):
        """Получить пользователя по ID."""
        try:
            from src.database import SessionLocal
            from src.models.user import User
            
            db = SessionLocal()
            try:
                return db.query(User).filter(User.id == uuid.UUID(user_id)).first()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None

    async def _log_admin_action(
        self,
        user_id: str,
        action: str,
        details: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> None:
        """
        Логировать административное действие в аудит-лог.
        
        Args:
            user_id: ID пользователя
            action: Тип действия (login, logout, create, update, delete)
            details: Дополнительные детали
            resource_type: Тип ресурса (user, channel, etc.)
            resource_id: ID ресурса
        """
        try:
            from src.database import SessionLocal
            from src.models.audit_log import AdminAuditLog
            
            db = SessionLocal()
            try:
                log_entry = AdminAuditLog(
                    user_id=uuid.UUID(user_id),
                    action=action,
                    details=details,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    timestamp=datetime.utcnow()
                )
                db.add(log_entry)
                db.commit()
            finally:
                db.close()
                
        except ImportError:
            # Модель audit_log еще не создана - пропускаем
            pass
        except Exception as e:
            logger.warning(f"Failed to log admin action: {e}")


def get_current_admin_user(request: Request) -> Optional[dict]:
    """
    Получение информации о текущем администраторе из сессии.

    Args:
        request: HTTP запрос

    Returns:
        Dict с user и role или None если не авторизован
    """
    admin_user = request.session.get("admin_user")
    if not admin_user:
        return None

    return {
        "user": admin_user,
        "role": request.session.get("admin_role", "unknown"),
    }
