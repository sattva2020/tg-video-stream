# Research: Реальные данные мониторинга системы

**Feature**: 015-real-system-monitoring  
**Date**: 2025-11-30  
**Status**: Complete

## Исследуемые вопросы

### 1. Получение системных метрик на Python

**Decision**: Использовать библиотеку `psutil`

**Rationale**:
- Стандарт де-факто для системных метрик в Python
- Кроссплатформенная (Linux, Windows, macOS)
- Лёгкая, без внешних зависимостей
- Уже используется в экосистеме проекта (проверено в requirements)
- Документация: https://psutil.readthedocs.io/

**Код примера**:
```python
import psutil

# CPU
cpu_percent = psutil.cpu_percent(interval=1)

# RAM
memory = psutil.virtual_memory()
ram_percent = memory.percent

# Disk
disk = psutil.disk_usage('/')
disk_percent = disk.percent
```

**Alternatives considered**:
- `resource` (stdlib) — только для текущего процесса, не системные метрики
- `os.sysconf` — низкоуровневый, требует ручного парсинга /proc
- Prometheus node_exporter — избыточен для одного сервера

---

### 2. Получение информации о соединениях PostgreSQL

**Decision**: SQL-запрос к `pg_stat_activity`

**Rationale**:
- Встроенная функциональность PostgreSQL
- Не требует дополнительных расширений
- Точные данные о текущих соединениях

**Код примера**:
```sql
-- Текущие соединения
SELECT count(*) FROM pg_stat_activity 
WHERE state IS NOT NULL AND datname = current_database();

-- Максимальное количество соединений
SHOW max_connections;
```

**Python интеграция**:
```python
from sqlalchemy import text

# Текущие соединения
result = db.execute(text("""
    SELECT count(*) FROM pg_stat_activity 
    WHERE state IS NOT NULL AND datname = current_database()
"""))
current_connections = result.scalar()

# Max connections
result = db.execute(text("SHOW max_connections"))
max_connections = int(result.scalar())
```

**Alternatives considered**:
- pg_stat_database — даёт только общую статистику, не активные соединения
- Внешний мониторинг (pgwatch2) — избыточен

---

### 3. Измерение латентности API

**Decision**: Middleware + точечные замеры в health check

**Rationale**:
- Существующий `/health` endpoint уже измеряет latency к DB и Redis
- Добавим endpoint latency как время ответа на простой запрос
- Минимальная нагрузка

**Код примера**:
```python
import time

async def measure_api_latency():
    start = time.time()
    # Простой SELECT 1 для измерения round-trip
    db.execute(text("SELECT 1"))
    return (time.time() - start) * 1000  # ms
```

---

### 4. Хранение событий активности

**Decision**: Отдельная таблица `activity_events` в PostgreSQL

**Rationale**:
- Простая схема, быстрый поиск
- Автоматическая очистка старых записей (LIMIT на чтение + периодический DELETE)
- Интеграция с существующей инфраструктурой SQLAlchemy

**Схема таблицы**:
```sql
CREATE TABLE activity_events (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,  -- user_registered, stream_started, etc.
    message TEXT NOT NULL,
    user_email VARCHAR(255),    -- nullable, для событий без пользователя
    details JSONB,              -- дополнительная информация
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_activity_events_created_at ON activity_events(created_at DESC);
CREATE INDEX idx_activity_events_type ON activity_events(type);
```

**Политика хранения**:
- Хранить последние 1000 записей
- Периодическая очистка: DELETE при INSERT если count > 1100 (гистерезис)

**Alternatives considered**:
- Redis Streams — сложнее для persistence и SQL-запросов
- Файловые логи — сложнее парсить, нет индексов
- Отдельный сервис (ELK) — избыточен для масштаба

---

### 5. Frontend polling vs WebSocket

**Decision**: Polling каждые 30 секунд через TanStack Query

**Rationale**:
- Простая реализация
- TanStack Query уже используется
- Автоматический refetchInterval
- 1 запрос в 30 сек — минимальная нагрузка
- WebSocket избыточен для 1-2 админов

**Код примера**:
```typescript
const { data: metrics } = useQuery({
  queryKey: ['system', 'metrics'],
  queryFn: () => systemApi.getMetrics(),
  refetchInterval: 30_000, // 30 seconds
});
```

**Alternatives considered**:
- WebSocket — сложнее, не нужен для такого масштаба
- Server-Sent Events — нет поддержки в существующей инфраструктуре
- Manual setInterval — дублирует функциональность TanStack Query

---

### 6. Точки записи событий

**Decision**: Декоратор/функция для записи в точках изменения состояния

**Места записи событий**:
| Событие | Файл | Триггер |
|---------|------|---------|
| user_registered | `backend/src/api/auth/routes.py` | После успешной регистрации |
| user_approved | `backend/src/api/users.py` | При изменении статуса на approved |
| user_rejected | `backend/src/api/users.py` | При изменении статуса на rejected |
| stream_started | `backend/src/api/admin.py` | После успешного start_stream |
| stream_stopped | `backend/src/api/admin.py` | После успешного stop_stream |
| track_added | `backend/src/api/playlist.py` | После добавления трека |

**Код примера**:
```python
from src.services.activity_service import log_activity

async def register_user(...):
    # ... регистрация ...
    await log_activity(
        type="user_registered",
        message=f"Новый пользователь зарегистрировался",
        user_email=user.email
    )
```

---

## Зависимости для установки

### Backend
```
psutil>=5.9.0
```
Проверка: уже установлен или добавить в `requirements.txt`

### Frontend
Новые зависимости не требуются — используем существующие TanStack Query, date-fns.

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| psutil не работает в LXC | Низкая | Тестирование на сервере, fallback "N/A" |
| Высокая нагрузка от polling | Низкая | 30 сек интервал, один запрос |
| Переполнение таблицы событий | Средняя | Лимит 1000 записей + очистка |
| Latency замеров неточный | Низкая | Использовать несколько samples |

---

## Вывод

Все вопросы разрешены. Готовы к Phase 1 (data-model, contracts, quickstart).
