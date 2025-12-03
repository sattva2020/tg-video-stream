# Data Model: Интеграция компонентов из GitHub-проектов

**Feature**: 016-github-integrations | **Date**: 2025-12-01  
**Status**: ✅ Complete

## Entities Overview

| Entity | Type | Storage | Description |
|--------|------|---------|-------------|
| QueueItem | Value Object | Redis List | Элемент очереди стрима |
| StreamState | Value Object | Redis Hash | Состояние активного стрима |
| AutoEndTimer | Value Object | Redis String | Таймер auto-end |
| AdminAuditLog | Entity | PostgreSQL | Лог действий админа |
| StreamMetrics | Value Object | Memory → Prometheus | Метрики стрима |

---

## Entity: QueueItem

**Description**: Элемент очереди воспроизведения для стрима  
**Storage**: Redis List (`stream_queue:{channel_id}`)  
**Lifecycle**: Создается при добавлении в очередь → удаляется при воспроизведении или skip

### Fields

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| id | string | yes | uuid4() | UUID format | Уникальный ID элемента |
| channel_id | int | yes | - | >0 | ID Telegram канала |
| title | string | yes | - | 1-500 chars | Название трека |
| url | string | yes | - | Valid URL | URL аудио/видео |
| duration | int | no | null | ≥0 | Длительность в секундах |
| source | enum | yes | - | youtube\|file\|stream | Источник контента |
| requested_by | int | no | null | Telegram user_id | Кто добавил |
| added_at | datetime | yes | now() | ISO 8601 | Время добавления |
| metadata | object | no | {} | JSON | Дополнительные данные |

### JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "id": { "type": "string", "format": "uuid" },
    "channel_id": { "type": "integer", "minimum": 1 },
    "title": { "type": "string", "minLength": 1, "maxLength": 500 },
    "url": { "type": "string", "format": "uri" },
    "duration": { "type": ["integer", "null"], "minimum": 0 },
    "source": { "type": "string", "enum": ["youtube", "file", "stream"] },
    "requested_by": { "type": ["integer", "null"] },
    "added_at": { "type": "string", "format": "date-time" },
    "metadata": { "type": "object" }
  },
  "required": ["id", "channel_id", "title", "url", "source", "added_at"]
}
```

### Redis Key Pattern

```
stream_queue:{channel_id}  → LIST of JSON-serialized QueueItem
```

### Example

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "channel_id": -1001234567890,
  "title": "Meditation Music - 1 Hour",
  "url": "https://youtube.com/watch?v=abc123",
  "duration": 3600,
  "source": "youtube",
  "requested_by": 123456789,
  "added_at": "2025-12-01T10:30:00Z",
  "metadata": {
    "thumbnail": "https://i.ytimg.com/vi/abc123/default.jpg",
    "artist": "Relaxing Sounds"
  }
}
```

---

## Entity: StreamState

**Description**: Текущее состояние активного стрима  
**Storage**: Redis Hash (`stream_state:{channel_id}`)  
**Lifecycle**: Создается при старте стрима → обновляется во время воспроизведения → удаляется при остановке

### Fields

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| channel_id | int | yes | - | >0 | ID Telegram канала |
| status | enum | yes | - | playing\|paused\|stopped\|placeholder | Статус стрима |
| current_item_id | string | no | null | UUID | ID текущего QueueItem |
| started_at | datetime | yes | now() | ISO 8601 | Время старта стрима |
| current_position | int | no | 0 | ≥0 | Текущая позиция в секундах |
| listeners_count | int | no | 0 | ≥0 | Количество слушателей |
| is_placeholder | bool | no | false | - | Воспроизводится placeholder |
| last_activity | datetime | yes | now() | ISO 8601 | Последняя активность |

### Redis Hash Structure

```
HSET stream_state:{channel_id} 
  status "playing"
  current_item_id "550e8400-e29b-41d4-a716-446655440000"
  started_at "2025-12-01T10:30:00Z"
  current_position "120"
  listeners_count "5"
  is_placeholder "false"
  last_activity "2025-12-01T10:32:00Z"
```

### State Transitions

```
┌─────────────┐     start()     ┌─────────────┐
│   stopped   │ ───────────────▶│   playing   │
└─────────────┘                 └─────────────┘
       ▲                              │  │
       │                              │  │
       │         stop()               │  │ pause()
       │◀─────────────────────────────┘  │
       │                                 ▼
       │                        ┌─────────────┐
       │         stop()         │   paused    │
       │◀───────────────────────│             │
       │                        └─────────────┘
       │                              │
       │                              │ resume()
       │                              ▼
       │                        ┌─────────────┐
       │◀───────────────────────│   playing   │
                                └─────────────┘

  queue_empty() triggers:
  
┌─────────────┐  queue_empty()  ┌─────────────┐
│   playing   │ ───────────────▶│ placeholder │
└─────────────┘                 └─────────────┘
                                      │
                                      │ queue_filled()
                                      ▼
                                ┌─────────────┐
                                │   playing   │
                                └─────────────┘
```

---

## Entity: AutoEndTimer

**Description**: Таймер автоматического завершения стрима при отсутствии слушателей  
**Storage**: Redis String (`auto_end_timer:{channel_id}`)  
**Lifecycle**: Создается когда слушателей = 0 → удаляется при появлении слушателя или завершении стрима

### Fields

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| channel_id | int | yes | - | >0 | ID Telegram канала |
| started_at | datetime | yes | now() | ISO 8601 | Время старта таймера |
| timeout_at | datetime | yes | - | ISO 8601 | Время завершения (started_at + timeout) |
| timeout_minutes | int | yes | 5 | 1-60 | Таймаут в минутах |

### Redis Key Pattern

```
auto_end_timer:{channel_id}  → JSON-serialized timer data
EXPIRE auto_end_timer:{channel_id} {timeout_seconds}
```

### Example

```json
{
  "channel_id": -1001234567890,
  "started_at": "2025-12-01T10:30:00Z",
  "timeout_at": "2025-12-01T10:35:00Z",
  "timeout_minutes": 5
}
```

---

## Entity: AdminAuditLog (PostgreSQL)

**Description**: Лог всех действий в административной панели  
**Storage**: PostgreSQL table `admin_audit_logs`  
**Lifecycle**: Создается при каждом действии админа → хранится indefinitely для аудита

### Fields

| Field | Type | Required | Default | Validation | Description |
|-------|------|----------|---------|------------|-------------|
| id | int | yes | auto | PK | Primary key |
| admin_user_id | int | yes | - | FK → users.id | ID админа |
| action | enum | yes | - | see below | Тип действия |
| model_name | string | yes | - | 1-100 chars | Название модели |
| model_id | int | no | null | - | ID измененной записи |
| old_values | jsonb | no | null | - | Значения до изменения |
| new_values | jsonb | no | null | - | Значения после изменения |
| ip_address | string | no | null | IPv4/IPv6 | IP адрес админа |
| user_agent | string | no | null | - | User-Agent браузера |
| created_at | datetime | yes | now() | - | Время действия |

### Action Enum

```python
class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"
    EXPORT = "export"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"
```

### SQLAlchemy Model

```python
# backend/src/models/audit_log.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum as PyEnum

from src.core.database import Base

class AuditAction(str, PyEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"
    EXPORT = "export"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(Enum(AuditAction), nullable=False, index=True)
    model_name = Column(String(100), nullable=False, index=True)
    model_id = Column(Integer, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationship
    admin_user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action} {self.model_name}:{self.model_id} by user:{self.admin_user_id}>"
```

### Alembic Migration

```python
# backend/migrations/versions/xxx_add_admin_audit_logs.py

def upgrade():
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_user_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.Enum('create', 'update', 'delete', 'login', 'logout', 
                                     'view', 'export', 'bulk_update', 'bulk_delete',
                                     name='auditaction'), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_audit_logs_admin_user_id', 'admin_audit_logs', ['admin_user_id'])
    op.create_index('ix_admin_audit_logs_action', 'admin_audit_logs', ['action'])
    op.create_index('ix_admin_audit_logs_model_name', 'admin_audit_logs', ['model_name'])
    op.create_index('ix_admin_audit_logs_created_at', 'admin_audit_logs', ['created_at'])

def downgrade():
    op.drop_table('admin_audit_logs')
    op.execute("DROP TYPE auditaction")
```

---

## Value Object: StreamMetrics

**Description**: Метрики стрима для Prometheus и WebSocket  
**Storage**: In-memory (prometheus_client registry)  
**Lifecycle**: Обновляется в реальном времени → экспортируется через /metrics

### Fields

| Field | Type | Prometheus Type | Labels | Description |
|-------|------|-----------------|--------|-------------|
| active_streams | int | Gauge | - | Количество активных стримов |
| queue_size | int | Gauge | channel_id | Размер очереди по каналам |
| listeners_count | int | Gauge | channel_id | Слушатели по каналам |
| stream_duration_seconds | float | Histogram | - | Распределение длительности стримов |
| queue_operations_total | int | Counter | channel_id, operation | Операции с очередью |
| auto_end_triggers_total | int | Counter | channel_id, reason | Триггеры auto-end |
| websocket_connections | int | Gauge | channel_id | WebSocket соединения |
| http_requests_total | int | Counter | method, path, status | HTTP запросы |
| http_request_duration_seconds | float | Histogram | method, path | Latency запросов |

### Prometheus Metrics Definition

```python
# backend/src/services/prometheus_service.py

from prometheus_client import Counter, Gauge, Histogram

# Streams
ACTIVE_STREAMS = Gauge(
    'sattva_active_streams',
    'Number of active streams'
)

QUEUE_SIZE = Gauge(
    'sattva_queue_size',
    'Queue size per channel',
    ['channel_id']
)

LISTENERS_COUNT = Gauge(
    'sattva_stream_listeners',
    'Number of listeners per stream',
    ['channel_id']
)

STREAM_DURATION = Histogram(
    'sattva_stream_duration_seconds',
    'Stream duration in seconds',
    buckets=(60, 300, 600, 1800, 3600, 7200, 14400)
)

# Queue operations
QUEUE_OPERATIONS = Counter(
    'sattva_queue_operations_total',
    'Queue operations',
    ['channel_id', 'operation']
)

# Auto-end
AUTO_END_TRIGGERS = Counter(
    'sattva_auto_end_total',
    'Auto-end triggers',
    ['channel_id', 'reason']
)

# WebSocket
WEBSOCKET_CONNECTIONS = Gauge(
    'sattva_websocket_connections',
    'Active WebSocket connections',
    ['channel_id']
)

# HTTP (via middleware)
HTTP_REQUESTS = Counter(
    'sattva_http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status']
)

HTTP_REQUEST_DURATION = Histogram(
    'sattva_http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'path'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)
```

---

## Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Redis                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  stream_queue:{channel_id}     stream_state:{channel_id}        │
│  ┌──────────────────────┐     ┌──────────────────────┐         │
│  │ LIST                 │     │ HASH                 │         │
│  │ [QueueItem, ...]     │────▶│ status: playing      │         │
│  └──────────────────────┘     │ current_item_id: ... │         │
│                               │ listeners_count: 5   │         │
│                               └──────────────────────┘         │
│                                          │                      │
│                                          │ listeners = 0        │
│                                          ▼                      │
│                               ┌──────────────────────┐         │
│                               │ auto_end_timer:...   │         │
│                               │ TTL: 300s            │         │
│                               └──────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       PostgreSQL                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐           ┌─────────────────────┐             │
│  │   users     │──────────▶│  admin_audit_logs   │             │
│  │             │ 1      *  │                     │             │
│  │ id          │           │ admin_user_id (FK)  │             │
│  │ role        │           │ action              │             │
│  │ status      │           │ model_name          │             │
│  └─────────────┘           │ old_values          │             │
│                            │ new_values          │             │
│                            └─────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       Prometheus                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  StreamMetrics (in-memory → /metrics endpoint)                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ sattva_active_streams                                     │  │
│  │ sattva_queue_size{channel_id="..."}                       │  │
│  │ sattva_stream_listeners{channel_id="..."}                 │  │
│  │ sattva_queue_operations_total{channel_id="...", op="..."}│  │
│  │ sattva_auto_end_total{channel_id="...", reason="..."}     │  │
│  │ sattva_websocket_connections{channel_id="..."}            │  │
│  │ sattva_http_requests_total{method="...", path="..."}      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Validation Rules Summary

| Entity | Field | Rule | Error Message |
|--------|-------|------|---------------|
| QueueItem | title | 1-500 chars | "Название должно быть от 1 до 500 символов" |
| QueueItem | url | Valid URL | "Некорректный URL" |
| QueueItem | source | Enum | "Неподдерживаемый источник" |
| QueueItem | duration | ≥0 | "Длительность не может быть отрицательной" |
| StreamState | status | Enum | "Недопустимый статус стрима" |
| AutoEndTimer | timeout_minutes | 1-60 | "Таймаут должен быть от 1 до 60 минут" |
| AdminAuditLog | model_name | 1-100 chars | "Название модели обязательно" |

---

## Next Steps

1. ✅ Data model complete
2. → Create `contracts/` with OpenAPI specs for queue, metrics, admin endpoints
3. → Create `quickstart.md` with setup and testing instructions
