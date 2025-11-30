# Quickstart: Реальные данные мониторинга системы

**Feature**: 015-real-system-monitoring  
**Date**: 2025-11-30

## Обзор

Этот документ описывает быстрый старт для тестирования реальных данных мониторинга на Dashboard. После реализации администратор увидит актуальные метрики системы и ленту событий вместо mock данных.

## Предварительные требования

- Python 3.12+ с установленным backend
- Node.js 20+ с установленным frontend
- PostgreSQL 16 запущен
- Redis запущен (для кеширования, опционально)
- Пользователь с ролью `admin` или `superadmin`

## Быстрая проверка

### 1. Применить миграцию БД

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

Должна создаться таблица `activity_events`.

### 2. Проверить API метрик

```bash
# Получить JWT токен (предполагается что уже залогинен)
TOKEN="your-jwt-token"

# Запрос метрик
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/system/metrics
```

**Ожидаемый ответ**:
```json
{
  "cpu_percent": 23.5,
  "ram_percent": 45.2,
  "disk_percent": 35.1,
  "latency_ms": 8.3,
  "db_connections": 3,
  "db_max_connections": 100,
  "timestamp": "2025-11-30T12:00:00Z"
}
```

### 3. Проверить API событий

```bash
curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8000/api/system/activity?limit=5"
```

**Ожидаемый ответ**:
```json
{
  "events": [
    {
      "id": 1,
      "type": "user_registered",
      "message": "Новый пользователь зарегистрировался",
      "user_email": "test@example.com",
      "created_at": "2025-11-30T11:55:00Z"
    }
  ],
  "total": 1
}
```

### 4. Проверить UI Dashboard

```bash
cd frontend
npm run dev
```

1. Открыть http://localhost:5173
2. Войти как admin/superadmin
3. Перейти на Dashboard
4. **Блок "Здоровье системы"**: должны отображаться реальные % CPU, RAM, диска
5. **Блок "Последняя активность"**: должны отображаться реальные события

### 5. Проверить автообновление

1. Открыть Dashboard
2. Подождать 30 секунд
3. Метрики должны обновиться автоматически (смотреть Network tab в DevTools)

### 6. Проверить запись событий

```bash
# Зарегистрировать нового пользователя
curl -X POST http://localhost:8000/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"newuser@test.com","password":"TestPass123!"}'

# Проверить что событие появилось
curl -H "Authorization: Bearer $TOKEN" \
     "http://localhost:8000/api/system/activity?limit=1"
```

Должно появиться событие `user_registered`.

## Тестирование критических порогов

### Высокая нагрузка CPU

```bash
# На сервере запустить stress test
stress --cpu 4 --timeout 60s
```

Dashboard должен показать красный индикатор CPU при >90%.

### Переполнение диска (симуляция)

Временно изменить пороги в коде для тестирования UI.

## Запуск тестов

### Backend

```bash
cd backend
pytest tests/api/test_system_metrics.py -v
pytest tests/api/test_activity_events.py -v
```

### Frontend

```bash
cd frontend
npm run test -- --grep "SystemHealth"
```

### E2E

```bash
cd frontend
npx playwright test tests/dashboard-monitoring.spec.ts
```

## Troubleshooting

### "Данные временно недоступны"

- Проверить что psutil установлен: `pip show psutil`
- Проверить логи backend на ошибки доступа к /proc

### Метрики не обновляются

- Проверить Network tab — запросы каждые 30 сек
- Проверить console на ошибки JavaScript
- Убедиться что refetchInterval установлен

### События не записываются

- Проверить логи backend на ошибки записи в БД
- Проверить что миграция применена: `alembic current`
- Проверить права доступа к таблице activity_events

## Checklist готовности

- [ ] Миграция applied
- [ ] API /metrics возвращает реальные данные
- [ ] API /activity возвращает события
- [ ] UI показывает реальные метрики
- [ ] UI показывает реальные события
- [ ] Автообновление работает (30 сек)
- [ ] События записываются при действиях
- [ ] Критические пороги подсвечиваются
- [ ] Тесты проходят
