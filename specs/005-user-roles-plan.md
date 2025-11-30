# План внедрения системы ролей (RBAC)

## 1. Цель
Разделить пользователей на обычных (`user`) и администраторов (`admin`) для управления доступом к критически важным функциям (управление стримом, бан пользователей, просмотр статистики).

## 2. Изменения в Базе Данных (Backend)

### 2.1. Модель данных
*   Добавить поле `role` в таблицу `users`.
*   Тип данных: `String` (или `Enum` в SQLAlchemy).
*   Значение по умолчанию: `'user'`.
*   Возможные значения: `'user'`, `'admin'`.

### 2.2. Миграции (Alembic)
*   Создать новую ревизию Alembic: `alembic revision --autogenerate -m "add user roles"`.
*   В миграции прописать обновление существующих записей: `UPDATE users SET role = 'user' WHERE role IS NULL`.

## 3. Изменения в Backend (FastAPI)

### 3.1. Обновление Pydantic моделей
*   В `User` (schema) добавить поле `role: str`.
*   В `TokenData` (payload JWT) добавить поле `role: str | None = None`.

### 3.2. Генерация токена (JWT)
*   Обновить функцию `create_access_token` в `auth_service.py`.
*   Включать `role` в payload токена (`{"sub": user_id, "role": user.role}`).
    *   *Плюс:* Фронтенд сразу знает роль без лишних запросов.
    *   *Минус:* При смене роли нужно перелогиниться.

### 3.3. Защита роутов (Dependencies)
*   Создать новую зависимость `get_current_admin` в `api/deps.py` (или `auth.py`).
    ```python
    def get_current_admin(current_user: User = Depends(get_current_user)):
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Not enough privileges")
        return current_user
    ```
*   Применить `Depends(get_current_admin)` к админским эндпоинтам (например, в будущем `router.post("/stream/restart")`).

### 3.4. Регистрация
*   При регистрации (`/register`) жестко задавать `role="user"`.
*   Создание первого админа:
    *   **Вариант А:** Скрипт `scripts/create_admin.py`.
    *   **Вариант Б:** Ручной SQL запрос.

## 4. Изменения во Frontend (React)

### 4.1. Типизация
*   Обновить интерфейс `User` в `src/types/user.ts` (или где он определен): добавить `role: 'user' | 'admin'`.

### 4.2. Состояние (Auth Context)
*   При декодировании JWT (или получении `/users/me`) сохранять роль в стейт приложения (Zustand/Context).

### 4.3. Защищенные маршруты
*   Обновить компонент `ProtectedRoute`. Добавить проп `requiredRole`.
    ```tsx
    <Route element={<ProtectedRoute requiredRole="admin" />}>
      <Route path="/admin" element={<AdminDashboard />} />
    </Route>
    ```

### 4.4. UI Элементы
*   Скрывать кнопки/ссылки для не-админов:
    ```tsx
    {user?.role === 'admin' && <button>Restart Stream</button>}
    ```

## 5. План работ (Step-by-Step)

1.  [Backend] Создать миграцию БД и обновить модель `User`.
2.  [Backend] Обновить генерацию JWT токена (добавить claim `role`).
3.  [Backend] Реализовать dependency `get_current_admin`.
4.  [Script] Написать скрипт для назначения роли админа существующему юзеру.
5.  [Frontend] Обновить интерфейсы и логику чтения токена.
6.  [Frontend] Добавить проверку ролей в роутинг.

## 6. Оценка времени
*   Backend: ~1-2 часа.
*   Frontend: ~1-2 часа.
*   Тестирование: ~1 час.
