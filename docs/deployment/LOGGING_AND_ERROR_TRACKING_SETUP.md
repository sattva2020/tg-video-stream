# Centralized Logging (Loki) и Error Tracking (Glitchtip) — Setup Guide

> **Дата:** 27 декабря 2025  
> **Назначение:** Полная инструкция по настройке централизованного логирования и отслеживания ошибок

---

## 📋 Содержание

1. [Phase 2.2: Centralized Logging (Loki)](#phase-22-centralized-logging-loki)
2. [Phase 2.3: Error Tracking (Glitchtip)](#phase-23-error-tracking-glitchtip)
3. [Интеграция в приложение](#интеграция-в-приложение)
4. [Быстрый старт](#быстрый-старт)
5. [Troubleshooting](#troubleshooting)

---

## 🔍 Phase 2.2: Centralized Logging (Loki)

### Что это?

**Grafana Loki** — система централизованного логирования, оптимизированная для Kubernetes и микросервисов.

**Преимущества:**
- ✅ Интеграция с Grafana (единый интерфейс для метрик и логов)
- ✅ Низкое потребление ресурсов (не индексирует текст логов)
- ✅ Мощный язык запросов LogQL (похож на PromQL)
- ✅ Retention policy (автоматическое удаление старых логов)

### Компоненты

1. **Loki** — хранилище логов (похож на Prometheus для метрик)
2. **Promtail** — агент для сбора логов (tail файлов и отправка в Loki)
3. **Grafana** — UI для просмотра и поиска логов

### Архитектура

```
Backend/Frontend → Logs (files) → Promtail → Loki → Grafana
```

### Конфигурация Loki

Файл: `config/monitoring/loki-config.yml`

**Основные настройки:**
- **Retention:** 30 дней (720 часов)
- **Storage:** Filesystem (для production можно S3/GCS)
- **Ingestion limits:** 10MB/s rate, 20MB burst
- **Max streams:** 10000 на пользователя

### Конфигурация Promtail

Файл: `config/monitoring/promtail-config.yml`

**Собираются логи из:**
- `/app/backend/logs/*.log` — Backend JSON logs
- `/app/frontend/logs/*.log` — Frontend logs
- `/var/lib/docker/containers/*/*.log` — Docker container logs
- `/var/log/syslog` — System logs
- `/var/log/nginx/*.log` — Nginx access/error logs

**Pipeline stages:**
- **JSON parsing** — для структурированных логов
- **Regex extraction** — для неструктурированных логов (nginx, syslog)
- **Labels** — автоматическая маркировка (job, level, service)
- **Timestamp** — парсинг временных меток

### Структурированное логирование (Backend)

**Библиотека:** `structlog` (Python)

**Файл:** `backend/src/utils/logging_config.py`

**Формат логов:** JSON

```json
{
  "timestamp": "2025-12-27T10:30:15.123Z",
  "level": "error",
  "logger": "api.auth",
  "message": "Login failed",
  "app": "sattva-tv-backend",
  "environment": "production",
  "user_id": 123,
  "ip": "192.168.1.100"
}
```

**Использование:**

```python
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Базовые логи
logger.info("user_login", user_id=user.id, username=user.username)
logger.warning("rate_limit_exceeded", user_id=user.id, attempts=5)
logger.error("database_error", operation="insert_user", error=str(e))

# Исключения с контекстом
try:
    risky_operation()
except Exception:
    logger.exception("operation_failed", operation="risky_operation", user_id=user.id)
```

### Дашборд Logs Overview

**Файл:** `config/monitoring/grafana/dashboards/logs-overview.json`

**Панели:**
1. **Log Statistics** — Total/Error/Warning/Info counts (5m)
2. **Log Rate by Level** — Timeseries графики по уровням
3. **Log Rate by Service** — Распределение по сервисам (backend, frontend, docker)
4. **Recent Logs** — Последние 100-200 логов с фильтрацией
5. **Top Error Messages** — Топ-20 ошибок за последний час

**LogQL примеры:**

```logql
# Все логи приложения
{app="sattva-tv"}

# Только ошибки
{app="sattva-tv", level="error"}

# Поиск по тексту
{app="sattva-tv"} |= "database"

# Regex фильтр
{app="sattva-tv"} |~ "error|fail|exception"

# JSON парсинг
{app="sattva-tv"} | json | user_id="123"

# Rate запросов
sum(rate({app="sattva-tv"}[5m]))
```

---

## 🐛 Phase 2.3: Error Tracking (Glitchtip)

### Что это?

**Glitchtip** — self-hosted альтернатива Sentry для error tracking и APM.

**Преимущества:**
- ✅ Open-source и self-hosted (никаких лимитов)
- ✅ Совместимость с Sentry SDK (plug-and-play)
- ✅ Полный контроль над данными (GDPR compliance)
- ✅ Низкая стоимость (только инфраструктура)

### Компоненты

1. **Glitchtip Web** — веб-интерфейс и API
2. **Glitchtip Worker** — обработка событий (Celery)
3. **Glitchtip Beat** — планировщик задач
4. **PostgreSQL** — хранилище событий
5. **Redis** — очередь задач

### Архитектура

```
Frontend → Sentry SDK → Glitchtip Web → PostgreSQL
Backend  → Sentry SDK → Glitchtip Web → PostgreSQL
                            ↓
                      Celery Worker
```

### Запуск Glitchtip

```bash
# Запуск Glitchtip стека
docker compose -f docker-compose.glitchtip.yml up -d

# Первоначальная миграция БД
docker compose -f docker-compose.glitchtip.yml run --rm glitchtip-migrate

# Создание superuser
docker compose -f docker-compose.glitchtip.yml run --rm glitchtip-web ./manage.py createsuperuser

# Проверка статуса
docker compose -f docker-compose.glitchtip.yml ps
```

**Доступ:** http://localhost:8080

### Настройка проекта в Glitchtip

1. **Создать организацию:**
   - Открыть http://localhost:8080
   - Settings → Organizations → Create Organization
   - Name: `Sattva TV`

2. **Создать проекты:**
   - Backend: `sattva-tv-backend`
   - Frontend: `sattva-tv-frontend`

3. **Получить DSN:**
   - Settings → Projects → [Project Name] → Client Keys (DSN)
   - Скопировать DSN вида: `http://abc123@localhost:8080/1`

### Интеграция Backend (FastAPI)

**SDK:** `sentry-sdk[fastapi]` (уже установлен)

**Файл:** `backend/src/instrumentation/sentry.py` (уже настроен)

**Переменные в `.env`:**

```bash
# Glitchtip DSN для backend
SENTRY_DSN=http://your_backend_dsn@localhost:8080/1
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=v1.0.0  # Опционально
```

**Автоматически отслеживается:**
- ✅ Все необработанные исключения
- ✅ HTTP requests (URL, method, status, latency)
- ✅ SQLAlchemy queries
- ✅ Redis commands
- ✅ Celery tasks

**Ручной захват:**

```python
import sentry_sdk

# Отправка сообщения
sentry_sdk.capture_message("Important event", level="info")

# Отправка исключения
try:
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)

# Установка пользовательского контекста
sentry_sdk.set_user({"id": user.id, "username": user.username})
sentry_sdk.set_context("custom", {"operation": "payment", "amount": 100})
```

### Интеграция Frontend (React)

**SDK:** `@sentry/react` (добавлен в package.json)

**Файл:** `frontend/src/instrumentation/sentry.ts`

**Переменные в `.env.production`:**

```bash
# Glitchtip DSN для frontend
VITE_SENTRY_DSN=http://your_frontend_dsn@localhost:8080/2
VITE_SENTRY_ENVIRONMENT=production
VITE_SENTRY_RELEASE=v1.0.0  # Опционально
```

**Инициализация в `main.tsx`:**

```typescript
import { initSentry } from './instrumentation/sentry';

// ПЕРЕД рендерингом приложения
initSentry();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

**Автоматически отслеживается:**
- ✅ Необработанные ошибки React
- ✅ Network requests (fetch/axios)
- ✅ React Router navigation
- ✅ Performance traces

**Ручной захват:**

```typescript
import { captureException, captureMessage, setSentryUser } from './instrumentation/sentry';

// Отправка ошибки
try {
  riskyOperation();
} catch (error) {
  captureException(error as Error, { operation: 'checkout' });
}

// Отправка сообщения
captureMessage('User completed onboarding', 'info');

// Установка пользователя (после логина)
setSentryUser({ id: user.id, username: user.username, email: user.email });
```

**Error Boundary:**

```tsx
import { SentryErrorBoundary } from './instrumentation/sentry';

function App() {
  return (
    <SentryErrorBoundary
      fallback={<ErrorFallback />}
      showDialog={true}
    >
      <Routes />
    </SentryErrorBoundary>
  );
}
```

---

## 🚀 Быстрый старт

### 1. Запуск всех сервисов

```bash
# Запуск мониторинга + логирования
docker compose \
  -f docker-compose.yml \
  -f docker-compose.monitoring.yml \
  -f docker-compose.glitchtip.yml \
  up -d

# Проверка статуса
docker compose -f docker-compose.monitoring.yml ps
docker compose -f docker-compose.glitchtip.yml ps
```

### 2. Настройка Glitchtip

```bash
# Создать superuser
docker compose -f docker-compose.glitchtip.yml run --rm glitchtip-web ./manage.py createsuperuser

# Открыть UI
open http://localhost:8080

# Создать организацию и проекты
# Получить DSN для backend и frontend
```

### 3. Добавить переменные окружения

**Backend `.env`:**

```bash
# Glitchtip
SENTRY_DSN=http://your_backend_dsn@localhost:8080/1
SENTRY_ENVIRONMENT=production
```

**Frontend `.env.production`:**

```bash
# Glitchtip
VITE_SENTRY_DSN=http://your_frontend_dsn@localhost:8080/2
VITE_SENTRY_ENVIRONMENT=production
```

### 4. Установить зависимости

**Backend:**

```bash
cd backend
pip install structlog>=23.3.0
```

**Frontend:**

```bash
cd frontend
npm install @sentry/react
```

### 5. Перезапуск приложений

```bash
docker compose restart backend frontend
```

### 6. Доступ к UI

- **Grafana (Logs):** http://localhost:3001
  - Explore → Loki datasource
  - Dashboards → Logs Overview
- **Glitchtip (Errors):** http://localhost:8080
  - Projects → Backend/Frontend → Issues

---

## 🔧 Troubleshooting

### Promtail не собирает логи

```bash
# Проверка логов Promtail
docker logs sattva-promtail --tail 100

# Проверка positions file
docker exec sattva-promtail cat /tmp/positions.yaml

# Проверка доступности Loki
docker exec sattva-promtail wget -q -O- http://loki:3100/ready
```

### Loki не принимает логи

```bash
# Проверка health
curl http://localhost:3100/ready

# Проверка логов
docker logs sattva-loki --tail 100

# Проверка metrics
curl http://localhost:3100/metrics
```

### Glitchtip не принимает события

```bash
# Проверка логов web
docker logs sattva-glitchtip-web --tail 100

# Проверка логов worker
docker logs sattva-glitchtip-worker --tail 100

# Тест отправки события
curl -X POST http://localhost:8080/api/1/store/ \
  -H 'Content-Type: application/json' \
  -H 'X-Sentry-Auth: Sentry sentry_key=YOUR_KEY' \
  -d '{
    "message": "Test error",
    "level": "error"
  }'
```

### Frontend не отправляет ошибки

1. **Проверка DSN:**
   ```bash
   echo $VITE_SENTRY_DSN
   ```

2. **Проверка инициализации:**
   - Открыть DevTools Console
   - Должно быть сообщение: "✅ Sentry initialized"

3. **Проверка Network:**
   - DevTools → Network
   - Искать запросы к `localhost:8080/api/`

4. **Тест ошибки:**
   ```typescript
   throw new Error('Test error from frontend');
   ```

---

## 📊 Метрики успеха

| Компонент | Статус | URL |
|-----------|--------|-----|
| Loki | ✅ | http://localhost:3100 |
| Promtail | ✅ | - |
| Grafana (Logs) | ✅ | http://localhost:3001 |
| Glitchtip Web | ✅ | http://localhost:8080 |
| Backend Logging | ✅ | structlog JSON |
| Frontend Error Tracking | ✅ | @sentry/react |

---

**🎉 Phase 2.2 и 2.3 полностью настроены!**

Теперь у проекта есть:
- ✅ Централизованное логирование (Loki)
- ✅ Мощный поиск по логам (LogQL)
- ✅ Error tracking (Glitchtip)
- ✅ Performance monitoring (APM)
- ✅ Session Replay (опционально)
- ✅ Self-hosted (полный контроль данных)
