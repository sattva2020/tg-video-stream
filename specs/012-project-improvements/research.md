# Research: План улучшения проекта 24/7 TV Telegram

**Branch**: `012-project-improvements` | **Date**: 29.11.2025  
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

---

## R-001: Docker Socket Security Alternatives {#docker-socket}

### Проблема

Текущий `docker-compose.yml` монтирует Docker socket в backend контейнер:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

Это критическая уязвимость — контейнер получает root-доступ к хосту.

### Решение

**Decision**: Удалить Docker socket mount. Backend не требует управления контейнерами.

**Rationale**: 
- Анализ кода backend показывает отсутствие использования Docker API
- Socket был добавлен для отладки и не используется в production
- Если потребуется Docker API — использовать Docker-in-Docker (dind) или remote Docker API с TLS

**Alternatives Rejected**:
- Docker socket proxy (Tecnativa/docker-socket-proxy) — усложняет без необходимости
- Rootless Docker — требует изменений на хосте

### Implementation

```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - ./backend:/app
      - ./data:/app/data
      # УДАЛЕНО: - /var/run/docker.sock:/var/run/docker.sock
```

---

## R-002: Docker Network Isolation Patterns {#network-isolation}

### Проблема

Все сервисы находятся в default network — frontend может напрямую обращаться к БД.

### Решение

**Decision**: Создать изолированные сети `internal` и `external`.

**Rationale**:
- `internal` network: backend, db, redis — без external exposure
- `external` network: frontend, backend (только API endpoints)
- Streamer: отдельная сеть с redis

**Network Topology**:
```
┌─────────────────────────────────────────────────────────────┐
│                         external                             │
│  ┌──────────┐         ┌───────────┐                         │
│  │ frontend │ ──────► │  backend  │ (только /api/*)         │
│  │  :3000   │         │   :8000   │                         │
│  └──────────┘         └─────┬─────┘                         │
└─────────────────────────────┼───────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────┐
│                         internal                             │
│                       ┌─────▼─────┐                         │
│  ┌─────────┐          │  backend  │          ┌───────────┐  │
│  │   db    │ ◄────────┤           ├────────► │   redis   │  │
│  │  :5432  │          │   :8000   │          │   :6379   │  │
│  └─────────┘          └───────────┘          └─────┬─────┘  │
└─────────────────────────────────────────────────────┼───────┘
                                                      │
┌─────────────────────────────────────────────────────┼───────┐
│                        streamer                      │       │
│  ┌────────────┐                              ┌──────▼────┐  │
│  │  streamer  │ ─────────────────────────────┤   redis   │  │
│  │            │                              │   :6379   │  │
│  └────────────┘                              └───────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```yaml
# docker-compose.yml
networks:
  external:
    driver: bridge
  internal:
    driver: bridge
    internal: true  # Нет доступа к внешней сети
  streamer:
    driver: bridge

services:
  frontend:
    networks:
      - external

  backend:
    networks:
      - external
      - internal

  db:
    networks:
      - internal

  redis:
    networks:
      - internal
      - streamer

  streamer:
    networks:
      - streamer
```

---

## R-003: SQLAlchemy 2.0 Migration Guide {#sqlalchemy-migration}

### Проблема

Текущий код использует deprecated API:
```python
# backend/src/database.py
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
```

### Решение

**Decision**: Миграция на `DeclarativeBase` из SQLAlchemy 2.0.

**Rationale**:
- `declarative_base()` deprecated в SQLAlchemy 2.0
- Новый подход обеспечивает лучшую типизацию
- Совместим с Alembic без изменений миграций

### Implementation

```python
# backend/src/database.py - BEFORE
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# backend/src/database.py - AFTER
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

**Migration Checklist**:
1. Обновить `sqlalchemy>=2.0` в requirements.txt
2. Изменить `database.py`
3. Все модели остаются без изменений (наследуются от Base)
4. Запустить тесты с `-W error::DeprecationWarning`

---

## R-004: Pydantic v2 ConfigDict Migration {#pydantic-migration}

### Проблема

Текущий код использует deprecated `class Config`:
```python
# Найдено в 6 файлах
class Config:
    from_attributes = True
```

### Решение

**Decision**: Миграция на `model_config = ConfigDict(...)`.

**Rationale**:
- `class Config` deprecated в Pydantic v2
- `ConfigDict` обеспечивает type safety
- Автоматическое завершение в IDE

### Implementation

```python
# BEFORE
class UserSchema(BaseModel):
    class Config:
        from_attributes = True

# AFTER
from pydantic import ConfigDict

class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```

**Affected Files**:
1. `backend/src/api/telegram_auth.py` (line 29)
2. `backend/src/api/schedule.py` (lines 90, 113, 155)
3. `backend/src/api/playlist.py` (line 57)
4. `backend/src/api/channels.py` (line 30)

---

## R-005: Docker Health Check Best Practices {#health-checks}

### Проблема

Нет health checks — Docker не знает реальное состояние сервисов.

### Решение

**Decision**: Добавить health checks для всех сервисов.

**Rationale**:
- Автоматический restart при unhealthy
- Правильный порядок запуска через `depends_on: condition: service_healthy`
- Интеграция с мониторингом

### Implementation

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

  db:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  frontend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 30s
      timeout: 10s
      retries: 3

  streamer:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9090/metrics"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Backend /health Endpoint**:
```python
@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "dependencies": {
            "database": check_db(db),
            "redis": check_redis()
        }
    }
```

---

## R-006: GitHub Actions CD to VPS Patterns {#cd-pipeline}

### Проблема

Текущий CI только проверяет код, деплой выполняется вручную.

### Решение

**Decision**: GitHub Actions CD с SSH deploy на VPS 37.53.91.144.

**Rationale**:
- Использовать существующий SSH ключ `id_rsa_n8n`
- Deploy при merge в main (staging) и release tag (production с approval)
- Rollback через git revert

### Implementation

```yaml
# .github/workflows/cd.yml
name: CD

on:
  push:
    branches: [main]
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ github.event_name == 'release' && 'production' || 'staging' }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: 37.53.91.144
          username: root
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/telegram
            git pull origin main
            docker compose pull
            docker compose up -d --build
            docker compose ps
```

**Secrets Required**:
- `SSH_PRIVATE_KEY` — содержимое `id_rsa_n8n`

**Rollback Plan**:
```bash
# На VPS
cd /opt/telegram
git log --oneline -5  # Найти предыдущий коммит
git revert HEAD --no-edit
docker compose up -d --build
```

---

## R-007: Grafana + Prometheus + Alertmanager Setup {#monitoring-stack}

### Проблема

Streamer экспортирует Prometheus метрики, но нет визуализации и алертинга.

### Решение

**Decision**: Добавить Grafana + Prometheus + Alertmanager в docker-compose.

**Rationale**:
- Prometheus собирает метрики с `:9090/metrics`
- Grafana визуализирует dashboards
- Alertmanager отправляет уведомления в Telegram

### Implementation

**docker-compose.yml additions**:
```yaml
services:
  prometheus:
    image: prom/prometheus:v2.48.0
    volumes:
      - ./config/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - internal
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:9090/-/healthy"]

  grafana:
    image: grafana/grafana:10.2.0
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - ./config/monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana
    ports:
      - "3001:3000"
    networks:
      - internal
      - external

  alertmanager:
    image: prom/alertmanager:v0.26.0
    volumes:
      - ./config/monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
    networks:
      - internal
```

**prometheus.yml**:
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'backend'
    static_configs:
      - targets: ['backend:8000']
  
  - job_name: 'streamer'
    static_configs:
      - targets: ['streamer:9090']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/rules/*.yml'
```

**Telegram Alert Integration**:
```yaml
# alertmanager.yml
receivers:
  - name: 'telegram'
    telegram_configs:
      - bot_token: '${TELEGRAM_ALERT_BOT_TOKEN}'
        chat_id: ${TELEGRAM_ALERT_CHAT_ID}
        message: '{{ .CommonAnnotations.summary }}'
```

---

## R-008: Python File Refactoring Patterns {#refactoring}

### Проблема

`schedule.py` содержит 997 строк — затрудняет навигацию и тестирование.

### Решение

**Decision**: Разбить на модули по domain responsibility.

**Rationale**:
- Single Responsibility Principle
- Каждый модуль <300 строк
- Сохранить backward compatibility через re-exports

### Implementation

**Структура после рефакторинга**:
```
backend/src/api/
├── schedule/
│   ├── __init__.py      # Re-exports для backward compatibility
│   ├── router.py        # Main router aggregation (~50 строк)
│   ├── slots.py         # Slot CRUD (~200 строк)
│   ├── templates.py     # Template CRUD (~200 строк)
│   └── playlists.py     # Playlist CRUD (~200 строк)
└── schedule.py          # DEPRECATED: import from schedule/ (backward compat)
```

**__init__.py**:
```python
# Backward compatibility
from .router import router
from .slots import *
from .templates import *
from .playlists import *
```

**Migration Strategy**:
1. Создать `schedule/` директорию
2. Вынести логику по файлам
3. Добавить re-exports в `__init__.py`
4. Обновить импорты в `main.py`
5. Удалить старый `schedule.py` после подтверждения тестов

---

## R-009: Storybook 7+ React Setup {#storybook}

### Проблема

Нет интерактивной документации UI компонентов.

### Решение

**Decision**: Storybook 7+ с Vite builder.

**Rationale**:
- Native Vite support — быстрый HMR
- Autodocs — автоматическая документация из TypeScript
- Interaction testing — тесты компонентов

### Implementation

```bash
# Установка
cd frontend
npx storybook@latest init --type react --builder vite
```

**.storybook/main.ts**:
```typescript
import type { StorybookConfig } from '@storybook/react-vite';

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx)'],
  addons: [
    '@storybook/addon-links',
    '@storybook/addon-essentials',
    '@storybook/addon-interactions',
  ],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  docs: {
    autodocs: 'tag',
  },
};

export default config;
```

**Button.stories.tsx example**:
```typescript
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  title: 'UI/Button',
  component: Button,
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof Button>;

export const Primary: Story = {
  args: { variant: 'primary', children: 'Click me' },
};

export const Secondary: Story = {
  args: { variant: 'secondary', children: 'Click me' },
};

export const Disabled: Story = {
  args: { disabled: true, children: 'Disabled' },
};
```

---

## R-010: pytest-cov + vitest Coverage Integration {#coverage}

### Проблема

Нет метрик покрытия кода тестами.

### Решение

**Decision**: pytest-cov для backend, vitest --coverage для frontend.

**Rationale**:
- HTML reports для локальной проверки
- CI integration с threshold enforcement
- Badge в README

### Implementation

**Backend (pytest-cov)**:
```bash
pip install pytest-cov

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term --cov-fail-under=70
```

**pyproject.toml**:
```toml
[tool.pytest.ini_options]
addopts = "--cov=src --cov-report=html --cov-fail-under=70"
```

**Frontend (vitest)**:
```bash
npm install -D @vitest/coverage-v8
```

**vitest.config.ts**:
```typescript
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      reportsDirectory: './coverage',
      thresholds: {
        lines: 60,
        branches: 60,
        functions: 60,
        statements: 60,
      },
    },
  },
});
```

**CI Integration (.github/workflows/ci.yml)**:
```yaml
- name: Backend coverage
  run: |
    cd backend
    pytest --cov=src --cov-fail-under=70

- name: Frontend coverage
  run: |
    cd frontend
    npm run test:coverage
```

---

## Summary

| Research ID | Decision | Status |
|-------------|----------|--------|
| R-001 | Удалить Docker socket mount | ✅ Ready |
| R-002 | Изолированные Docker networks | ✅ Ready |
| R-003 | SQLAlchemy 2.0 DeclarativeBase | ✅ Ready |
| R-004 | Pydantic v2 ConfigDict | ✅ Ready |
| R-005 | Docker health checks all services | ✅ Ready |
| R-006 | GitHub Actions CD to VPS | ✅ Ready |
| R-007 | Grafana + Prometheus + Alertmanager | ✅ Ready |
| R-008 | schedule.py → schedule/ module | ✅ Ready |
| R-009 | Storybook 7+ Vite | ✅ Ready |
| R-010 | pytest-cov + vitest coverage | ✅ Ready |

Все NEEDS CLARIFICATION разрешены. Готово к Phase 1: Design & Contracts.
