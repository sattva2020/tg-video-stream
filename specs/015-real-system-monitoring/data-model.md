# Data Model: Реальные данные мониторинга системы

**Feature**: 015-real-system-monitoring  
**Date**: 2025-11-30  
**Status**: Complete

## Entities

### 1. SystemMetrics (read-only, не хранится в БД)

Метрики собираются в реальном времени через psutil и pg_stat_activity.

```
SystemMetrics
├── cpu_percent: float          # Загрузка CPU (0-100%)
├── ram_percent: float          # Использование RAM (0-100%)
├── disk_percent: float         # Использование диска (0-100%)
├── latency_ms: float           # Задержка ответа API (ms)
├── db_connections: int         # Текущие соединения к БД
├── db_max_connections: int     # Максимум соединений к БД
└── timestamp: datetime         # Время измерения (UTC)
```

**Validation Rules**:
- cpu_percent, ram_percent, disk_percent: 0.0 ≤ value ≤ 100.0
- latency_ms: ≥ 0
- db_connections: ≥ 0
- db_max_connections: > 0

**Thresholds** (для status):
| Metric | Warning | Critical |
|--------|---------|----------|
| cpu_percent | ≥ 70% | ≥ 90% |
| ram_percent | ≥ 70% | ≥ 85% |
| disk_percent | ≥ 70% | ≥ 90% |
| latency_ms | ≥ 100ms | ≥ 500ms |
| db_connections | ≥ 80% of max | ≥ 95% of max |

---

### 2. ActivityEvent (хранится в PostgreSQL)

События системной активности для ленты Dashboard.

```
ActivityEvent (TABLE: activity_events)
├── id: int [PK, auto]          # Уникальный идентификатор
├── type: str                   # Тип события (enum)
├── message: str                # Читаемое описание
├── user_email: str? [nullable] # Email связанного пользователя
├── details: jsonb? [nullable]  # Дополнительные данные
└── created_at: datetime        # Время создания (UTC, auto)
```

**Event Types** (enum):
```
user_registered   # Новый пользователь зарегистрировался
user_approved     # Пользователь одобрен
user_rejected     # Пользователь отклонён
stream_started    # Трансляция запущена
stream_stopped    # Трансляция остановлена
stream_error      # Ошибка трансляции
track_added       # Трек добавлен в плейлист
track_removed     # Трек удалён из плейлиста
system_warning    # Системное предупреждение
system_error      # Системная ошибка
```

**Validation Rules**:
- type: required, один из enum values
- message: required, 1-500 символов
- user_email: optional, valid email format
- details: optional, valid JSON

**Indexes**:
- `idx_activity_events_created_at` — для сортировки DESC
- `idx_activity_events_type` — для фильтрации по типу

---

## SQLAlchemy Model

```python
# backend/src/models/activity_event.py

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from src.database import Base


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    user_email = Column(String(255), nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def __repr__(self):
        return f"<ActivityEvent {self.id}: {self.type}>"
```

---

## Pydantic Schemas

```python
# backend/src/api/schemas/system.py

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, ConfigDict


# === SystemMetrics ===

class SystemMetricsResponse(BaseModel):
    cpu_percent: float
    ram_percent: float  
    disk_percent: float
    latency_ms: float
    db_connections: int
    db_max_connections: int
    timestamp: datetime
    
    model_config = ConfigDict(from_attributes=True)


# === ActivityEvent ===

ActivityEventType = Literal[
    "user_registered",
    "user_approved", 
    "user_rejected",
    "stream_started",
    "stream_stopped",
    "stream_error",
    "track_added",
    "track_removed",
    "system_warning",
    "system_error"
]


class ActivityEventResponse(BaseModel):
    id: int
    type: ActivityEventType
    message: str
    user_email: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ActivityEventsListResponse(BaseModel):
    events: list[ActivityEventResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)
```

---

## TypeScript Types

```typescript
// frontend/src/types/system.ts

export interface SystemMetrics {
  cpu_percent: number;
  ram_percent: number;
  disk_percent: number;
  latency_ms: number;
  db_connections: number;
  db_max_connections: number;
  timestamp: string; // ISO 8601
}

export type ActivityEventType =
  | 'user_registered'
  | 'user_approved'
  | 'user_rejected'
  | 'stream_started'
  | 'stream_stopped'
  | 'stream_error'
  | 'track_added'
  | 'track_removed'
  | 'system_warning'
  | 'system_error';

export interface ActivityEvent {
  id: number;
  type: ActivityEventType;
  message: string;
  user_email?: string;
  details?: Record<string, unknown>;
  created_at: string; // ISO 8601
}

export interface ActivityEventsResponse {
  events: ActivityEvent[];
  total: number;
}

// Status helpers
export type MetricStatus = 'healthy' | 'warning' | 'critical';

export function getMetricStatus(
  value: number,
  warningThreshold: number,
  criticalThreshold: number
): MetricStatus {
  if (value >= criticalThreshold) return 'critical';
  if (value >= warningThreshold) return 'warning';
  return 'healthy';
}
```

---

## Relationships

```
                      ┌─────────────────┐
                      │  SystemMetrics  │
                      │   (runtime)     │
                      └────────┬────────┘
                               │
                               │ collected via psutil
                               │
┌────────────────────────────────────────────────────────┐
│                    Dashboard UI                        │
│  ┌─────────────────┐   ┌───────────────────────────┐  │
│  │  SystemHealth   │   │    ActivityTimeline       │  │
│  │    Component    │   │       Component           │  │
│  └────────┬────────┘   └────────────┬──────────────┘  │
└───────────┼─────────────────────────┼──────────────────┘
            │                         │
            │ GET /api/system/metrics │ GET /api/system/activity
            │                         │
┌───────────┴─────────────────────────┴──────────────────┐
│                    Backend API                         │
│                                                        │
│  ┌─────────────┐      ┌────────────────────────────┐  │
│  │  psutil     │      │    PostgreSQL              │  │
│  │  + pg_stat  │      │    activity_events table   │  │
│  └─────────────┘      └────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

## Migration

```python
# backend/migrations/versions/xxx_add_activity_events.py

"""Add activity_events table

Revision ID: xxx
Revises: [previous]
Create Date: 2025-11-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


def upgrade():
    op.create_table(
        'activity_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('details', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_activity_events_created_at', 'activity_events', 
                    ['created_at'], unique=False, postgresql_using='btree')
    op.create_index('idx_activity_events_type', 'activity_events', 
                    ['type'], unique=False)


def downgrade():
    op.drop_index('idx_activity_events_type', table_name='activity_events')
    op.drop_index('idx_activity_events_created_at', table_name='activity_events')
    op.drop_table('activity_events')
```

---

## Storage Policy

- **Retention**: Хранить последние 1000 записей
- **Cleanup**: При INSERT проверять count, если > 1100 — удалять старейшие до 1000
- **Frequency**: Cleanup при каждом INSERT (дешёвая операция с индексом)

```python
async def cleanup_old_events(db: Session, max_events: int = 1000):
    """Удаляет старые события, оставляя последние max_events."""
    count = db.query(func.count(ActivityEvent.id)).scalar()
    if count > max_events + 100:  # гистерезис
        oldest_to_keep = db.query(ActivityEvent.id)\
            .order_by(ActivityEvent.created_at.desc())\
            .offset(max_events)\
            .limit(1)\
            .scalar()
        if oldest_to_keep:
            db.query(ActivityEvent)\
                .filter(ActivityEvent.id < oldest_to_keep)\
                .delete()
            db.commit()
```
