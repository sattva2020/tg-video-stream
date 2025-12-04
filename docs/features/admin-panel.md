# Административная панель

**Версия**: 1.0  
**Дата**: 2025-12-01  
**Спецификация**: [spec.md](/specs/016-github-integrations/spec.md)

## Обзор

Административная панель на базе SQLAdmin обеспечивает:
- Управление пользователями (роли, статусы)
- Управление контентом (плейлисты, каналы)
- Аудит действий администраторов
- Интеграцию с существующей аутентификацией

## Доступ

URL: `/admin`

Требуемые роли: `superadmin`, `admin`

## Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   /admin URL    │────▶│    SQLAdmin     │────▶│   PostgreSQL    │
│  (браузер)      │     │    FastAPI      │     │   (модели)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  AdminAuditLog  │
                        │   (аудит)       │
                        └─────────────────┘
```

## Компоненты

### Admin Setup

Расположение: `backend/src/admin/__init__.py`

```python
from sqladmin import Admin
from src.admin.auth import AdminAuth
from src.admin.views import UserAdmin, PlaylistAdmin

admin = Admin(app, engine, authentication_backend=AdminAuth())
admin.add_view(UserAdmin)
admin.add_view(PlaylistAdmin)
```

### AdminAuth

Расположение: `backend/src/admin/auth.py`

Обеспечивает:
- Проверку JWT токена
- Валидацию роли (superadmin, admin)
- Логирование входа/выхода
- Интеграцию с существующей auth системой

```python
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        # Проверка JWT из cookies/headers
        # Валидация роли пользователя
        return True/False
    
    async def logout(self, request: Request) -> bool:
        # Логирование выхода
        return True
```

### Views

Расположение: `backend/src/admin/views.py`

#### UserAdmin

```python
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.telegram_id, User.role, User.is_active]
    column_searchable_list = [User.email, User.telegram_id]
    column_sortable_list = [User.id, User.email, User.role]
    form_excluded_columns = [User.hashed_password]
    
    can_create = True
    can_edit = True
    can_delete = False  # Мягкое удаление
```

#### PlaylistAdmin

```python
class PlaylistAdmin(ModelView, model=Playlist):
    column_list = [Playlist.id, Playlist.name, Playlist.channel_id, Playlist.is_active]
    column_searchable_list = [Playlist.name]
```

## Аудит

### AdminAuditLog Model

Расположение: `backend/src/models/audit_log.py`

```python
class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    
    id: int
    admin_id: int              # ID администратора
    action: str                # create, update, delete, login, logout
    entity_type: str           # user, playlist, channel
    entity_id: Optional[int]
    changes: Optional[dict]    # JSON с изменениями
    ip_address: str
    user_agent: str
    created_at: datetime
```

### Автоматическое логирование

Все действия в админ-панели автоматически логируются:

```python
# Middleware для аудита
async def on_model_change(self, data, model, is_created):
    await log_admin_action(
        admin_id=self.admin_id,
        action="create" if is_created else "update",
        entity_type=model.__tablename__,
        entity_id=model.id,
        changes=data
    )
```

## Функциональность

### Управление пользователями

| Действие | Описание |
|----------|----------|
| Просмотр списка | Все пользователи с фильтрацией |
| Поиск | По email, telegram_id |
| Изменение роли | user → moderator → admin |
| Активация/блокировка | Изменение is_active |
| Просмотр истории | Audit log по пользователю |

### Управление плейлистами

| Действие | Описание |
|----------|----------|
| Создание | Новый плейлист для канала |
| Редактирование | Изменение содержимого |
| Публикация | Активация/деактивация |
| Удаление | Мягкое удаление |

## Безопасность

### Аутентификация

1. Проверка JWT токена
2. Валидация срока действия
3. Проверка роли в БД
4. Сессия привязана к IP

### Авторизация

```python
# Проверка доступа
if user.role not in ['superadmin', 'admin']:
    raise HTTPException(403, "Доступ запрещён")

# Superadmin может всё
# Admin не может менять superadmin пользователей
```

### Rate Limiting

- Логин: 5 попыток / минуту
- Операции: 100 / минуту

## Миграции

```bash
# Создание миграции для audit_log
cd backend
alembic revision --autogenerate -m "add_admin_audit_log"
alembic upgrade head
```

## Конфигурация

Переменные окружения:

```bash
# Время жизни сессии админ-панели
ADMIN_SESSION_LIFETIME=3600

# Секретный ключ для сессий
ADMIN_SECRET_KEY=...
```

## Тестирование

### Unit тесты
```bash
pytest backend/tests/api/test_admin.py -v
```

### Ручное тестирование

1. Войти в `/admin` с admin учётными данными
2. Изменить роль пользователя
3. Проверить audit log
4. Выйти и проверить log выхода

## Метрики

Prometheus метрики:
- `sattva_admin_actions_total{action}` — количество действий
- `sattva_admin_sessions_active` — активные сессии

## Скриншоты

### Список пользователей
![Users List](/docs/img/admin-users.png)

### Редактирование пользователя
![User Edit](/docs/img/admin-user-edit.png)

### Audit Log
![Audit Log](/docs/img/admin-audit.png)

## См. также

- [Спецификация](/specs/016-github-integrations/spec.md)
- [Роли и права](/docs/features/user-roles.md)
- [Мониторинг](./monitoring.md)
