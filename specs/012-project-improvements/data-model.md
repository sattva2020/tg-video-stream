# Data Model: План улучшения проекта 24/7 TV Telegram

**Branch**: `012-project-improvements` | **Date**: 29.11.2025  
**Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

---

## Entities

### HealthResponse

**Source**: US-3 (Health Checks)

Ответ `/health` endpoint для проверки состояния сервиса.

```typescript
interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;                    // Версия приложения (из settings)
  uptime_seconds: number;             // Время работы в секундах
  timestamp: string;                  // ISO 8601 datetime
  dependencies: DependencyHealth[];   // Статус зависимостей
}
```

**Validation Rules**:
- `status` — enum, определяется по состоянию dependencies
- `uptime_seconds` — ≥0, вычисляется из времени старта
- `dependencies` — массив, минимум 2 элемента (db, redis)

**State Transitions**:
```
healthy ─────► degraded ─────► unhealthy
   ▲              │                │
   └──────────────┴────────────────┘
         (recovery)
```

---

### DependencyHealth

**Source**: US-3 (Health Checks)

Статус отдельной зависимости (база данных, Redis, etc).

```typescript
interface DependencyHealth {
  name: string;                       // Имя зависимости: "database", "redis"
  status: "up" | "down" | "degraded";
  latency_ms: number;                 // Время отклика в миллисекундах
  message?: string;                   // Опциональное сообщение об ошибке
  last_check: string;                 // ISO 8601 datetime последней проверки
}
```

**Validation Rules**:
- `name` — уникальный идентификатор, lowercase
- `latency_ms` — ≥0, -1 если недоступен
- `status: down` требует `message`

---

### AlertRule

**Source**: US-5 (Monitoring)

Правило алертинга Prometheus/Alertmanager.

```typescript
interface AlertRule {
  name: string;                       // Уникальное имя правила
  condition: string;                  // PromQL expression
  duration: string;                   // Длительность условия: "5m", "15m"
  severity: "critical" | "warning" | "info";
  summary: string;                    // Краткое описание
  description: string;                // Подробное описание
  receivers: string[];                // Каналы уведомлений
}
```

**Example Rules**:

| Name | Condition | Severity | Description |
|------|-----------|----------|-------------|
| HighErrorRate | `rate(http_errors_total[5m]) > 0.05` | critical | Ошибки >5% за 5 мин |
| StreamerDown | `up{job="streamer"} == 0` | critical | Streamer недоступен |
| HighLatency | `http_request_duration_seconds{quantile="0.95"} > 0.2` | warning | p95 >200ms |
| LowDiskSpace | `disk_free_bytes < 1e9` | warning | <1GB свободно |

---

### CoverageReport

**Source**: US-8 (Code Coverage)

Отчёт о покрытии кода тестами.

```typescript
interface CoverageReport {
  project: "backend" | "frontend";
  total_lines: number;
  covered_lines: number;
  percentage: number;                 // 0-100, округление до 2 знаков
  threshold: number;                  // Минимальный порог (70 backend, 60 frontend)
  passed: boolean;                    // percentage >= threshold
  by_file: FileCoverage[];
  generated_at: string;               // ISO 8601 datetime
}

interface FileCoverage {
  path: string;                       // Относительный путь от корня проекта
  lines: number;
  covered: number;
  percentage: number;
  uncovered_lines: number[];          // Номера непокрытых строк
}
```

**Validation Rules**:
- `percentage` = `covered_lines / total_lines * 100`
- `passed` = `percentage >= threshold`
- Backend threshold: 70%
- Frontend threshold: 60%

---

### DockerNetwork

**Source**: US-1 (Security)

Конфигурация Docker сети для изоляции.

```typescript
interface DockerNetwork {
  name: string;                       // internal, external, streamer
  driver: "bridge";
  internal: boolean;                  // true = нет выхода в интернет
  services: string[];                 // Список сервисов в сети
}
```

**Networks**:

| Name | Internal | Services |
|------|----------|----------|
| external | false | frontend, backend |
| internal | true | backend, db, redis |
| streamer | false | streamer, redis |

---

### DeploymentConfig

**Source**: US-4 (CD Pipeline)

Конфигурация для CD deployment.

```typescript
interface DeploymentConfig {
  environment: "staging" | "production";
  trigger: "push" | "release";
  host: string;                       // VPS hostname/IP
  user: string;                       // SSH user
  path: string;                       // Remote path
  commands: string[];                 // Deployment commands
  rollback_enabled: boolean;
  approval_required: boolean;         // true для production
}
```

**Environments**:

| Environment | Trigger | Approval | Host |
|-------------|---------|----------|------|
| staging | push to main | false | 37.53.91.144 |
| production | release tag | true | 37.53.91.144 |

---

## Relationships

```
┌─────────────────┐
│ HealthResponse  │
│                 │
│ - dependencies ─┼──────► DependencyHealth[]
│                 │
└─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│   AlertRule     │───────│ Alertmanager    │
│                 │       │   (external)    │
│ - receivers ────┼──────►│ - telegram      │
│                 │       │ - slack         │
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│ CoverageReport  │───────│ CI Pipeline     │
│                 │       │                 │
│ - passed ───────┼──────►│ - fail/pass     │
│                 │       │                 │
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│ DockerNetwork   │───────│ Docker Compose  │
│                 │       │                 │
│ - services ─────┼──────►│ - containers    │
│                 │       │                 │
└─────────────────┘       └─────────────────┘
```

---

## Pydantic Models (Backend)

### HealthResponse Schema

```python
from pydantic import BaseModel, ConfigDict
from typing import Literal
from datetime import datetime

class DependencyHealthSchema(BaseModel):
    name: str
    status: Literal["up", "down", "degraded"]
    latency_ms: float
    message: str | None = None
    last_check: datetime
    
    model_config = ConfigDict(from_attributes=True)

class HealthResponseSchema(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    uptime_seconds: float
    timestamp: datetime
    dependencies: list[DependencyHealthSchema]
    
    model_config = ConfigDict(from_attributes=True)
```

### CoverageReport Schema

```python
class FileCoverageSchema(BaseModel):
    path: str
    lines: int
    covered: int
    percentage: float
    uncovered_lines: list[int]

class CoverageReportSchema(BaseModel):
    project: Literal["backend", "frontend"]
    total_lines: int
    covered_lines: int
    percentage: float
    threshold: float
    passed: bool
    by_file: list[FileCoverageSchema]
    generated_at: datetime
```

---

## TypeScript Interfaces (Frontend)

### HealthResponse

```typescript
// frontend/src/types/health.ts

export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';
export type DependencyStatus = 'up' | 'down' | 'degraded';

export interface DependencyHealth {
  name: string;
  status: DependencyStatus;
  latency_ms: number;
  message?: string;
  last_check: string;
}

export interface HealthResponse {
  status: HealthStatus;
  version: string;
  uptime_seconds: number;
  timestamp: string;
  dependencies: DependencyHealth[];
}
```

---

## Database Migrations

Данная фича **не требует** новых таблиц в базе данных.

Все entities являются:
- Runtime objects (HealthResponse, DependencyHealth)
- Configuration files (AlertRule, DockerNetwork, DeploymentConfig)
- CI artifacts (CoverageReport)

---

## Summary

| Entity | Type | Storage | User Story |
|--------|------|---------|------------|
| HealthResponse | Runtime DTO | Memory | US-3 |
| DependencyHealth | Runtime DTO | Memory | US-3 |
| AlertRule | Config | YAML files | US-5 |
| CoverageReport | CI Artifact | JSON/HTML | US-8 |
| DockerNetwork | Config | docker-compose.yml | US-1 |
| DeploymentConfig | Config | GitHub Workflow | US-4 |
