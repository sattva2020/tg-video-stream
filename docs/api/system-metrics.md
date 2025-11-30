# System Metrics API

> **Spec**: 015-real-system-monitoring  
> **Версия**: 1.0  
> **Дата**: 2025-01-15

## Обзор

API для получения системных метрик сервера в реальном времени.
Используется компонентом `SystemHealth` на Dashboard.

## Endpoints

### GET /api/system/metrics

Получает актуальные системные метрики через psutil и pg_stat_activity.

#### Request

```http
GET /api/system/metrics HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Response

```json
{
  "cpu_percent": 23.5,
  "ram_percent": 45.2,
  "disk_percent": 67.8,
  "db_connections_active": 3,
  "db_connections_idle": 2,
  "uptime_seconds": 86400,
  "collected_at": "2025-01-15T10:30:00Z"
}
```

#### Поля ответа

| Поле | Тип | Описание |
|------|-----|----------|
| `cpu_percent` | float | Загрузка CPU (0-100%) |
| `ram_percent` | float | Использование RAM (0-100%) |
| `disk_percent` | float | Использование диска (0-100%) |
| `db_connections_active` | int | Активные подключения к PostgreSQL |
| `db_connections_idle` | int | Неактивные подключения к PostgreSQL |
| `uptime_seconds` | int | Время работы приложения в секундах |
| `collected_at` | datetime | Время сбора метрик (ISO 8601) |

#### Пороговые значения

Компонент `SystemHealth` отображает индикаторы состояния по следующим порогам:

| Метрика | Норма | Предупреждение | Критично |
|---------|-------|----------------|----------|
| CPU | < 70% | 70-90% | ≥ 90% |
| RAM | < 70% | 70-85% | ≥ 85% |
| Disk | < 80% | 80-90% | ≥ 90% |

#### Пример использования (React)

```tsx
import { useSystemMetrics } from '@/hooks/useSystemMetrics';

function SystemHealth() {
  const { data, isLoading, error } = useSystemMetrics();
  
  if (isLoading) return <Skeleton />;
  if (error) return <Error message={error.message} />;
  
  return (
    <div>
      <Gauge value={data.cpu_percent} label="CPU" />
      <Gauge value={data.ram_percent} label="RAM" />
      <Gauge value={data.disk_percent} label="Disk" />
    </div>
  );
}
```

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 401 | Не авторизован |
| 500 | Ошибка сервера (psutil недоступен) |

## Реализация

### Backend

- **Файл**: `backend/src/api/system.py`
- **Сервис**: `backend/src/services/metrics_service.py`
- **Зависимость**: `psutil>=5.9.0`

### Frontend

- **Хук**: `frontend/src/hooks/useSystemMetrics.ts`
- **API клиент**: `frontend/src/api/system.ts`
- **Компонент**: `frontend/src/components/dashboard/SystemHealth.tsx`

### Интервал обновления

- **Backend**: Данные собираются при каждом запросе
- **Frontend**: Автоматическое обновление каждые 30 секунд через TanStack Query

## Связанные документы

- [Activity Events API](./activity-events.md)
- [Dashboard Architecture](../architecture/dashboard.md)
- [015-real-system-monitoring Spec](../../specs/015-real-system-monitoring/)
