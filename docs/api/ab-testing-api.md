# A/B Testing API

> **Spec**: 016-a-b-testing-framework-for-content
> **Версия**: 1.0
> **Дата**: 2026-01-23

## Обзор

API для управления A/B тестированием контента. Позволяет создавать тесты для сравнения различных вариантов видео, расписаний или конфигураций трансляций, отслеживать метрики и анализировать результаты с расчетом статистической значимости.

## Возможности

- Создание A/B тестов с несколькими вариантами (2-10)
- Автоматическое распределение трафика с настраиваемыми весами
- Отслеживание метрик: показы, клики, конверсии, время просмотра, пики слушателей
- Статистический анализ: z-тест, t-тест, доверительные интервалы
- Автоматический выбор победителя на основе статистической значимости
- Управление жизненным циклом тестов (черновик → запуск → пауза → остановка → завершение)

## Endpoints

### POST /api/ab-tests

Создает новый A/B тест с вариантами.

#### Request

```http
POST /api/ab-tests HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Тест превью-изображений",
  "description": "Сравниваем 3 варианта превью для вечернего стрима",
  "hypothesis": "Яркие превью увеличат конверсию на 15%",
  "channel_id": "123e4567-e89b-12d3-a456-426614174000",
  "planned_duration_hours": 24,
  "variants": [
    {
      "name": "Контроль (текущее)",
      "description": "Текущее превью",
      "traffic_allocation": 34,
      "position": 0,
      "configuration": {
        "thumbnail_url": "https://example.com/thumb_a.jpg"
      }
    },
    {
      "name": "Вариант B (яркое)",
      "description": "Увеличенная яркость +20%",
      "traffic_allocation": 33,
      "position": 1,
      "configuration": {
        "thumbnail_url": "https://example.com/thumb_b.jpg"
      }
    },
    {
      "name": "Вариант C (контраст)",
      "description": "Повышенный контраст",
      "traffic_allocation": 33,
      "position": 2,
      "configuration": {
        "thumbnail_url": "https://example.com/thumb_c.jpg"
      }
    }
  ]
}
```

#### Поля запроса

| Поле | Тип | Обязательный | Описание |
|------|-----|--------------|----------|
| `name` | string | Да | Название теста (1-255 символов) |
| `description` | string | Нет | Описание теста |
| `hypothesis` | string | Нет | Гипотеза теста |
| `channel_id` | UUID | Да | ID канала |
| `planned_duration_hours` | int | Нет | Планируемая длительность в часах (≥1) |
| `traffic_config` | object | Нет | Конфигурация распределения трафика |
| `variants` | array | Да | Варианты теста (2-10 штук) |

#### Поля варианта

| Поле | Тип | Обязательный | Описание |
|------|-----|--------------|----------|
| `name` | string | Да | Название варианта (1-255 символов) |
| `description` | string | Нет | Описание варианта |
| `traffic_allocation` | int | Да | Процент трафика (0-100), сумма всех = 100% |
| `position` | int | Да | Порядок отображения (≥0) |
| `configuration` | object | Нет | Конфигурация варианта (playlist_id, schedule_settings, etc.) |

#### Response

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174111",
  "channel_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Тест превью-изображений",
  "description": "Сравниваем 3 варианта превью для вечернего стрима",
  "hypothesis": "Яркие превью увеличат конверсию на 15%",
  "status": "draft",
  "start_time": null,
  "end_time": null,
  "planned_duration_hours": 24,
  "traffic_config": null,
  "winner_variant_id": null,
  "confidence_level": null,
  "is_significant": null,
  "created_at": "2026-01-23T10:00:00Z",
  "updated_at": null,
  "created_by": "123e4567-e89b-12d3-a456-426614174999",
  "variants": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174201",
      "test_id": "123e4567-e89b-12d3-a456-426614174111",
      "name": "Контроль (текущее)",
      "description": "Текущее превью",
      "traffic_allocation": 34,
      "position": 0,
      "configuration": {
        "thumbnail_url": "https://example.com/thumb_a.jpg"
      },
      "is_winner": false,
      "conversion_rate": null,
      "improvement": null,
      "created_at": "2026-01-23T10:00:00Z",
      "updated_at": null
    },
    {
      "id": "123e4567-e89b-12d3-a456-426614174202",
      "test_id": "123e4567-e89b-12d3-a456-426614174111",
      "name": "Вариант B (яркое)",
      "description": "Увеличенная яркость +20%",
      "traffic_allocation": 33,
      "position": 1,
      "configuration": {
        "thumbnail_url": "https://example.com/thumb_b.jpg"
      },
      "is_winner": false,
      "conversion_rate": null,
      "improvement": null,
      "created_at": "2026-01-23T10:00:00Z",
      "updated_at": null
    },
    {
      "id": "123e4567-e89b-12d3-a456-426614174203",
      "test_id": "123e4567-e89b-12d3-a456-426614174111",
      "name": "Вариант C (контраст)",
      "description": "Повышенный контраст",
      "traffic_allocation": 33,
      "position": 2,
      "configuration": {
        "thumbnail_url": "https://example.com/thumb_c.jpg"
      },
      "is_winner": false,
      "conversion_rate": null,
      "improvement": null,
      "created_at": "2026-01-23T10:00:00Z",
      "updated_at": null
    }
  ]
}
```

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешно создан |
| 400 | Невалидные данные (traffic_allocation ≠ 100%, < 2 вариантов) |
| 401 | Не авторизован |
| 403 | Недостаточно прав (только SUPERADMIN, ADMIN) |
| 500 | Ошибка сервера |

---

### GET /api/ab-tests

Получает список A/B тестов с фильтрацией и пагинацией.

#### Request

```http
GET /api/ab-tests?status=running&limit=20&offset=0 HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Query Parameters

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `channel_id` | UUID | — | Фильтр по ID канала |
| `status` | string | — | Фильтр по статусу (draft, running, paused, completed, stopped) |
| `limit` | int | 50 | Количество записей (1-100) |
| `offset` | int | 0 | Смещение для пагинации |

#### Response

```json
{
  "tests": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174111",
      "channel_id": "123e4567-e89b-12d3-a456-426614174000",
      "name": "Тест превью-изображений",
      "status": "running",
      "start_time": "2026-01-23T10:00:00Z",
      "end_time": null,
      "winner_variant_id": null,
      "is_significant": null,
      "created_at": "2026-01-23T09:00:00Z",
      "variant_count": 3
    }
  ],
  "total": 15
}
```

#### Пример использования (React)

```tsx
import { listABTests } from '@/api/ab-testing';
import { useQuery } from '@tanstack/react-query';

function ABTestList() {
  const { data, isLoading } = useQuery({
    queryKey: ['ab-tests', { status: 'running' }],
    queryFn: () => listABTests(undefined, 'running', 20, 0)
  });

  if (isLoading) return <Skeleton />;

  return (
    <ul>
      {data.tests.map(test => (
        <li key={test.id}>
          <h3>{test.name}</h3>
          <StatusBadge status={test.status} />
          <p>Вариантов: {test.variant_count}</p>
        </li>
      ))}
    </ul>
  );
}
```

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 401 | Не авторизован |
| 403 | Недостаточно прав |
| 500 | Ошибка сервера |

---

### GET /api/ab-tests/{test_id}

Получает детальную информацию о A/B тесте с вариантами и метриками.

#### Request

```http
GET /api/ab-tests/123e4567-e89b-12d3-a456-426614174111 HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Response

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174111",
  "channel_id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Тест превью-изображений",
  "description": "Сравниваем 3 варианта превью для вечернего стрима",
  "hypothesis": "Яркие превью увеличат конверсию на 15%",
  "status": "running",
  "start_time": "2026-01-23T10:00:00Z",
  "end_time": null,
  "planned_duration_hours": 24,
  "traffic_config": null,
  "winner_variant_id": null,
  "confidence_level": null,
  "is_significant": null,
  "created_at": "2026-01-23T09:00:00Z",
  "updated_at": "2026-01-23T10:00:00Z",
  "created_by": "123e4567-e89b-12d3-a456-426614174999",
  "variants": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174201",
      "test_id": "123e4567-e89b-12d3-a456-426614174111",
      "name": "Контроль (текущее)",
      "description": "Текущее превью",
      "traffic_allocation": 34,
      "position": 0,
      "configuration": {
        "thumbnail_url": "https://example.com/thumb_a.jpg"
      },
      "is_winner": false,
      "conversion_rate": 0.125,
      "improvement": 0.0,
      "created_at": "2026-01-23T09:00:00Z",
      "updated_at": "2026-01-23T10:00:00Z"
    },
    {
      "id": "123e4567-e89b-12d3-a456-426614174202",
      "test_id": "123e4567-e89b-12d3-a456-426614174111",
      "name": "Вариант B (яркое)",
      "description": "Увеличенная яркость +20%",
      "traffic_allocation": 33,
      "position": 1,
      "configuration": {
        "thumbnail_url": "https://example.com/thumb_b.jpg"
      },
      "is_winner": false,
      "conversion_rate": 0.145,
      "improvement": 16.0,
      "created_at": "2026-01-23T09:00:00Z",
      "updated_at": "2026-01-23T10:00:00Z"
    },
    {
      "id": "123e4567-e89b-12d3-a456-426614174203",
      "test_id": "123e4567-e89b-12d3-a456-426614174111",
      "name": "Вариант C (контраст)",
      "description": "Повышенный контраст",
      "traffic_allocation": 33,
      "position": 2,
      "configuration": {
        "thumbnail_url": "https://example.com/thumb_c.jpg"
      },
      "is_winner": false,
      "conversion_rate": 0.138,
      "improvement": 10.4,
      "created_at": "2026-01-23T09:00:00Z",
      "updated_at": "2026-01-23T10:00:00Z"
    }
  ]
}
```

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешный запрос |
| 401 | Не авторизован |
| 403 | Недостаточно прав |
| 404 | Тест не найден |
| 500 | Ошибка сервера |

---

### PATCH /api/ab-tests/{test_id}

Обновляет метаданные A/B теста. Только для тестов в статусе `draft`.

#### Request

```http
PATCH /api/ab-tests/123e4567-e89b-12d3-a456-426614174111 HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Тест превью (обновленный)",
  "description": "Обновленное описание",
  "planned_duration_hours": 48
}
```

#### Поля запроса

| Поле | Тип | Обязательный | Описание |
|------|-----|--------------|----------|
| `name` | string | Нет | Название теста (1-255 символов) |
| `description` | string | Нет | Описание теста |
| `hypothesis` | string | Нет | Гипотеза теста |
| `planned_duration_hours` | int | Нет | Планируемая длительность в часах (≥1) |
| `traffic_config` | object | Нет | Конфигурация распределения трафика |

#### Response

Возвращает обновленный тест (см. ответ GET /api/ab-tests/{test_id}).

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешно обновлен |
| 400 | Невалидные данные или статус не draft |
| 401 | Не авторизован |
| 403 | Недостаточно прав |
| 404 | Тест не найден |
| 500 | Ошибка сервера |

---

### DELETE /api/ab-tests/{test_id}

Удаляет A/B тест. Только для тестов НЕ в статусе `running`.

#### Request

```http
DELETE /api/ab-tests/123e4567-e89b-12d3-a456-426614174111 HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Response

```json
{
  "success": true,
  "message": "A/B test deleted successfully"
}
```

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешно удален |
| 400 | Нельзя удалить запущенный тест |
| 401 | Не авторизован |
| 403 | Недостаточно прав |
| 404 | Тест не найден |
| 500 | Ошибка сервера |

---

### POST /api/ab-tests/{test_id}/start

Запускает A/B тест для сбора данных. Только для тестов в статусе `draft` или `paused`.

#### Request

```http
POST /api/ab-tests/123e4567-e89b-12d3-a456-426614174111/start HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Response

```json
{
  "test_id": "123e4567-e89b-12d3-a456-426614174111",
  "status": "running",
  "start_time": "2026-01-23T10:30:00Z"
}
```

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешно запущен |
| 400 | Неверный статус (только draft или paused) или тест не найден |
| 401 | Не авторизован |
| 403 | Недостаточно прав |
| 500 | Ошибка сервера |

---

### POST /api/ab-tests/{test_id}/stop

Останавливает A/B тест с выбором победителя. Только для тестов в статусе `running`.

#### Request

```http
POST /api/ab-tests/123e4567-e89b-12d3-a456-426614174111/stop?select_winner=true HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Query Parameters

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `select_winner` | boolean | true | Автоматически выбрать победителя |
| `winner_variant_id` | UUID | — | ID варианта-победителя (для ручного выбора) |

#### Response

```json
{
  "test_id": "123e4567-e89b-12d3-a456-426614174111",
  "status": "stopped",
  "end_time": "2026-01-23T10:35:00Z",
  "winner_variant_id": "123e4567-e89b-12d3-a456-426614174202",
  "confidence_level": 95.0
}
```

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешно остановлен |
| 400 | Неверный статус или неверный winner_variant_id |
| 401 | Не авторизован |
| 403 | Недостаточно прав |
| 404 | Тест не найден |
| 500 | Ошибка сервера |

---

### GET /api/ab-tests/{test_id}/analysis

Получает результаты статистического анализа A/B теста с доверительными интервалами и проверкой значимости.

#### Request

```http
GET /api/ab-tests/123e4567-e89b-12d3-a456-426614174111/analysis?confidence_level=0.95 HTTP/1.1
Host: api.example.com
Authorization: Bearer <token>
```

#### Query Parameters

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `confidence_level` | float | 0.95 | Уровень доверия (0.5-0.99) |

#### Response

```json
{
  "test_id": "123e4567-e89b-12d3-a456-426614174111",
  "test_name": "Тест превью-изображений",
  "status": "running",
  "variants": [
    {
      "variant_id": "123e4567-e89b-12d3-a456-426614174201",
      "variant_name": "Контроль (текущее)",
      "impressions": 1000,
      "conversions": 125,
      "conversion_rate": 0.125,
      "confidence_interval_lower": 0.105,
      "confidence_interval_upper": 0.148
    },
    {
      "variant_id": "123e4567-e89b-12d3-a456-426614174202",
      "variant_name": "Вариант B (яркое)",
      "impressions": 990,
      "conversions": 144,
      "conversion_rate": 0.145,
      "confidence_interval_lower": 0.124,
      "confidence_interval_upper": 0.169
    },
    {
      "variant_id": "123e4567-e89b-12d3-a456-426614174203",
      "variant_name": "Вариант C (контраст)",
      "impressions": 1010,
      "conversions": 139,
      "conversion_rate": 0.138,
      "confidence_interval_lower": 0.117,
      "confidence_interval_upper": 0.161
    }
  ],
  "winner_variant_id": "123e4567-e89b-12d3-a456-426614174202",
  "confidence_level": 95.0,
  "is_significant": true,
  "p_value": 0.032,
  "recommended_action": "Вариант B показывает статистически значимое улучшение на 16%. Рекомендуется остановить тест и выбрать B как победителя.",
  "analyzed_at": "2026-01-23T10:35:00Z"
}
```

#### Статистические методы

- **Z-тест**: Для сравнения пропорций (конверсий)
- **Интервал Уилсона**: Для расчета доверительных интервалов (лучше для малых выборок)
- **P-value**: Вероятность получить наблюдаемые результаты случайно
- **Уровень значимости**: p < 0.05 → статистически значимый результат (при confidence_level=0.95)

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешный анализ |
| 400 | Недостаточно данных для анализа |
| 401 | Не авторизован |
| 403 | Недостаточно прав |
| 404 | Тест не найден |
| 500 | Ошибка сервера |

---

### POST /api/ab-tests/metrics

Записывает метрику для варианта A/B теста. Внутренний эндпоинт для сбора данных.

#### Request

```http
POST /api/ab-tests/metrics HTTP/1.1
Host: api.example.com
Content-Type: application/json

{
  "variant_id": "123e4567-e89b-12d3-a456-426614174202",
  "metric_type": "conversions",
  "metric_value": 1,
  "metadata": {
    "user_id": "user123",
    "timestamp": "2026-01-23T10:30:00Z"
  }
}
```

#### Поля запроса

| Поле | Тип | Обязательный | Описание |
|------|-----|--------------|----------|
| `variant_id` | UUID | Да | ID варианта |
| `metric_type` | string | Да | Тип метрики (impressions, clicks, conversions, watch_time_seconds, peak_listeners, avg_view_duration) |
| `metric_value` | int | Да | Значение метрики (≥0) |
| `metadata` | object | Нет | Дополнительные данные |

#### Response

```json
{
  "id": 12345,
  "variant_id": "123e4567-e89b-12d3-a456-426614174202",
  "metric_type": "conversions",
  "metric_value": 1,
  "recorded_at": "2026-01-23T10:30:00Z",
  "metadata": {
    "user_id": "user123",
    "timestamp": "2026-01-23T10:30:00Z"
  }
}
```

#### Коды ошибок

| Код | Описание |
|-----|----------|
| 200 | Успешно записана |
| 400 | Невалидные данные |
| 404 | Вариант не найден |
| 500 | Ошибка сервера |

---

## Статусы теста

| Статус | Описание | Доступные действия |
|--------|----------|-------------------|
| `draft` | Черновик, тест создан но не запущен | Обновить, запустить, удалить |
| `running` | Тест запущен, идет сбор данных | Остановить, просмотр анализа |
| `paused` | Тест приостановлен | Запустить, остановить, удалить |
| `completed` | Тест завершен автоматически (достигнута длительность) | Просмотр, удаление |
| `stopped` | Тест остановлен вручную | Просмотр, удаление |

## Типы метрик

| Тип | Описание | Единицы измерения |
|-----|----------|-------------------|
| `impressions` | Показы варианта | количество |
| `clicks` | Клики по варианту | количество |
| `conversions` | Конверсии (целевые действия) | количество |
| `watch_time_seconds` | Время просмотра | секунды |
| `peak_listeners` | Пик слушателей | количество |
| `avg_view_duration` | Средняя длительность просмотра | секунды |

## Статистический анализ

### Z-тест для пропорций

Используется для сравнения конверсий между вариантами:

```
z = (p1 - p2) / SE
где:
  p1, p2 - конверсии вариантов
  SE - стандартная ошибка разности
  SE = sqrt(p1*(1-p1)/n1 + p2*(1-p2)/n2)
```

### Доверительный интервал (Wilson score)

Более точен для малых выборок:

```
CI = (p + z²/(2n) ± z*sqrt(p(1-p)/n + z²/(4n²))) / (1 + z²/n)
```

### P-value

Рассчитывается через нормальное распределение:

```
p-value = 2 * (1 - Φ(|z|))
где:
  Φ - кумулятивная функция нормального распределения
```

### Статистическая значимость

Результат считается значимым, если:
- p-value < 0.05 (при confidence_level=0.95)
- Доверительные интервалы вариантов не пересекаются

## Права доступа

| Роль | Доступные эндпоинты |
|------|-------------------|
| `SUPERADMIN` | Все эндпоинты |
| `ADMIN` | Все эндпоинты |
| `MODERATOR` | GET /api/ab-tests, GET /api/ab-tests/{id}, GET /api/ab-tests/{id}/analysis |

## Реализация

### Backend

- **Router**: `backend/src/api/ab_testing.py`
- **Service**: `backend/src/services/ab_testing_service.py`
- **Schemas**: `backend/src/schemas/ab_testing.py`
- **Models**: `backend/src/models/ab_testing.py`
- **Migration**: `backend/alembic/versions/l2m3n4o5p6q7_add_ab_testing_tables.py`
- **Tasks**: `backend/src/tasks/ab_testing.py` (Celery для автостопа)

### Frontend

- **API клиент**: `frontend/src/api/ab_testing.ts`
- **Types**: `frontend/src/types/ab_testing.ts`
- **Компоненты**:
  - `frontend/src/components/ab_testing/ABTestList.tsx`
  - `frontend/src/components/ab_testing/ABTestWizard.tsx`
  - `frontend/src/components/ab_testing/ABTestResults.tsx`
- **Страница**: `frontend/src/pages/admin/ABTestingPage.tsx`

### Схема базы данных

```sql
CREATE TABLE ab_tests (
    id UUID PRIMARY KEY,
    channel_id UUID NOT NULL REFERENCES channels(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    hypothesis TEXT,
    status VARCHAR(20) NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    planned_duration_hours INTEGER,
    traffic_config JSONB,
    winner_variant_id UUID REFERENCES ab_test_variants(id),
    confidence_level FLOAT,
    is_significant BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id)
);

CREATE TABLE ab_test_variants (
    id UUID PRIMARY KEY,
    test_id UUID NOT NULL REFERENCES ab_tests(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    traffic_allocation INTEGER NOT NULL CHECK (traffic_allocation >= 0 AND traffic_allocation <= 100),
    position INTEGER NOT NULL,
    configuration JSONB,
    is_winner BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE TABLE ab_test_metrics (
    id SERIAL PRIMARY KEY,
    variant_id UUID NOT NULL REFERENCES ab_test_variants(id),
    metric_type VARCHAR(50) NOT NULL,
    metric_value INTEGER NOT NULL CHECK (metric_value >= 0),
    metadata JSONB,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ab_tests_channel ON ab_tests(channel_id);
CREATE INDEX idx_ab_tests_status ON ab_tests(status);
CREATE INDEX idx_ab_test_metrics_variant ON ab_test_metrics(variant_id);
CREATE INDEX idx_ab_test_metrics_type ON ab_test_metrics(metric_type);
```

## Примеры использования

### Пример 1: Создание теста расписаний

```bash
curl -X POST http://localhost:8000/api/ab-tests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Тест времени стрима",
    "description": "Сравниваем вечернее и дневное время",
    "hypothesis": "Вечерние стримы привлекают на 30% больше зрителей",
    "channel_id": "123e4567-e89b-12d3-a456-426614174000",
    "planned_duration_hours": 48,
    "variants": [
      {
        "name": "Дневной стрим (12:00)",
        "traffic_allocation": 50,
        "position": 0,
        "configuration": {
          "schedule_time": "12:00",
          "timezone": "UTC"
        }
      },
      {
        "name": "Вечерний стрим (19:00)",
        "traffic_allocation": 50,
        "position": 1,
        "configuration": {
          "schedule_time": "19:00",
          "timezone": "UTC"
        }
      }
    ]
  }'
```

### Пример 2: Запись метрики конверсии

```bash
curl -X POST http://localhost:8000/api/ab-tests/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "variant_id": "123e4567-e89b-12d3-a456-426614174202",
    "metric_type": "conversions",
    "metric_value": 1,
    "metadata": {
      "user_id": "user123"
    }
  }'
```

### Пример 3: Анализ результатов

```bash
curl -X GET "http://localhost:8000/api/ab-tests/123e4567-e89b-12d3-a456-426614174111/analysis?confidence_level=0.95" \
  -H "Authorization: Bearer $TOKEN"
```

## Связанные документы

- [Пользовательское руководство](../ab-testing-guide.md)
- [016 Spec](../../.auto-claude/specs/016-a-b-testing-framework-for-content/spec.md)
- [Реализация frontend](../../frontend/src/components/ab_testing/)
