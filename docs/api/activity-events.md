# Activity Events API

> **Spec**: 015-real-system-monitoring  
> **Версия**: 1.0  
> **Дата**: 2025-01-15

## Обзор

API для получения и управления событиями активности системы.
Используется компонентом `ActivityTimeline` на Dashboard.

## Endpoints

### GET /api/system/activity

Получает список событий активности с пагинацией и фильтрацией.

#### Request

```http
GET /api/system/activity?limit=20&offset=0&type=user_registered&search=email HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Query Parameters

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `limit` | int | 20 | Количество записей (1-100) |
| `offset` | int | 0 | Смещение для пагинации |
| `type` | string | — | Фильтр по типу события |
| `search` | string | — | Поиск по тексту сообщения (макс. 100 символов) |

#### Response

```json
{
  "events": [
    {
      "id": 1,
      "type": "user_registered",
      "message": "Новый пользователь зарегистрирован: user@example.com",
      "user_email": "admin@example.com",
      "details": {
        "method": "email_password",
        "status": "pending"
      },
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 42
}
```

#### Поля события

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Уникальный идентификатор события |
| `type` | string | Тип события (см. ниже) |
| `message` | string | Человекочитаемое описание события |
| `user_email` | string | Email пользователя, выполнившего действие |
| `details` | object | Дополнительные данные (опционально) |
| `created_at` | datetime | Время события (ISO 8601) |

#### Типы событий

| Тип | Описание | Иконка |
|-----|----------|--------|
| `user_registered` | Регистрация нового пользователя | 👤+ |
| `user_approved` | Одобрение пользователя | ✅ |
| `user_rejected` | Отклонение пользователя | ❌ |
| `stream_started` | Запуск трансляции | ▶️ |
| `stream_stopped` | Остановка трансляции | ⏹️ |
| `stream_error` | Ошибка трансляции | ⚠️ |
| `track_added` | Добавление трека в плейлист | 🎵 |
| `track_removed` | Удаление трека из плейлиста | 🗑️ |
| `system_warning` | Системное предупреждение | ⚠️ |
| `system_error` | Системная ошибка | ❌ |

#### Пример использования (React)

```tsx
import { useActivityEvents } from '@/hooks/useActivityEvents';

function ActivityTimeline() {
  const { 
    events, 
    total, 
    isLoading 
  } = useActivityEvents({ 
    limit: 10,
    type: 'user_registered',
    search: 'gmail'
  });
  
  if (isLoading) return <Skeleton />;
  
  return (
    <ul>
      {events.map(event => (
        <li key={event.id}>
          <span>{event.message}</span>
          <time>{event.created_at}</time>
        </li>
      ))}
      <p>Всего событий: {total}</p>
    </ul>
  );
}
```

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 401 | Не авторизован |
| 422 | Неверные параметры (limit > 100, search > 100 символов) |
| 500 | Ошибка сервера |

## Интеграция событий

События автоматически логируются в следующих точках:

### Регистрация пользователей

- **Файл**: `backend/src/api/auth/email_password.py`
- **Событие**: `user_registered`
- **Когда**: При успешной регистрации через email/password

- **Файл**: `backend/src/api/auth/oauth.py`
- **Событие**: `user_registered`
- **Когда**: При первой авторизации через Google OAuth

### Управление пользователями

- **Файл**: `backend/src/api/admin.py`
- **События**: `user_approved`, `user_rejected`
- **Когда**: При одобрении/отклонении пользователя админом

### Управление трансляцией

- **Файл**: `backend/src/api/admin.py`
- **События**: `stream_started`, `stream_stopped`, `stream_error`
- **Когда**: При запуске/остановке/ошибке стрима

### Управление плейлистом

- **Файл**: `backend/src/api/playlist.py`
- **События**: `track_added`, `track_removed`
- **Когда**: При добавлении/удалении треков

## Автоматическая очистка

Сервис автоматически удаляет старые события, сохраняя последние 1000 записей.
Очистка происходит после добавления каждого нового события
с гистерезисом 100 записей.

```python
MAX_EVENTS = 1000
CLEANUP_THRESHOLD = 100  # Очистка при count > 1100
```

## Реализация

### Backend

- **Router**: `backend/src/api/system.py`
- **Service**: `backend/src/services/activity_service.py`
- **Model**: `backend/src/models/activity_event.py`
- **Migration**: `backend/migrations/versions/015_add_activity_events.py`

### Frontend

- **Хук**: `frontend/src/hooks/useActivityEvents.ts`
- **API клиент**: `frontend/src/api/system.ts`
- **Компонент**: `frontend/src/components/dashboard/ActivityTimeline.tsx`

### Схема базы данных

```sql
CREATE TABLE activity_events (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    user_email VARCHAR(255),
    details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_activity_events_type ON activity_events(type);
CREATE INDEX idx_activity_events_created ON activity_events(created_at);
CREATE INDEX idx_activity_events_type_created ON activity_events(type, created_at);
```

## Связанные документы

- [System Metrics API](./system-metrics.md)
- [Dashboard Architecture](../architecture/dashboard.md)
- [015-real-system-monitoring Spec](../../specs/015-real-system-monitoring/)
