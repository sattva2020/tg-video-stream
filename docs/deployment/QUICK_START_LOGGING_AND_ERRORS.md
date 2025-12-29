# 🚀 Quick Start: Logging & Error Tracking

> **Phase 2.2-2.3 быстрый запуск**  
> **Время:** 5-10 минут

---

## Шаг 1: Запуск всех сервисов

```bash
# Запуск мониторинга + логирования + error tracking
docker compose \
  -f docker-compose.yml \
  -f docker-compose.monitoring.yml \
  -f docker-compose.glitchtip.yml \
  up -d

# Проверка статуса
docker compose -f docker-compose.monitoring.yml ps
docker compose -f docker-compose.glitchtip.yml ps
```

---

## Шаг 2: Настройка Glitchtip

```bash
# 1. Создать superuser
docker compose -f docker-compose.glitchtip.yml run --rm glitchtip-web ./manage.py createsuperuser

# Username: admin
# Email: admin@example.com
# Password: (ваш пароль)
```

```bash
# 2. Открыть UI
open http://localhost:8080  # Linux/Mac
start http://localhost:8080  # Windows
```

**В UI:**
1. Login с созданным superuser
2. Settings → Organizations → Create Organization
   - Name: `Sattva TV`
3. Settings → Projects → Create Project
   - Backend project: `sattva-tv-backend`
   - Frontend project: `sattva-tv-frontend`
4. Получить DSN для каждого проекта:
   - Settings → Projects → [Project Name] → Client Keys (DSN)
   - Скопировать DSN вида: `http://abc123@localhost:8080/1`

---

## Шаг 3: Обновить переменные окружения

**Backend `.env`:**

```bash
# Glitchtip
SENTRY_DSN=http://your_backend_dsn@localhost:8080/1
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=v1.0.0
```

**Frontend `.env.production`:**

```bash
# Glitchtip
VITE_SENTRY_DSN=http://your_frontend_dsn@localhost:8080/2
VITE_SENTRY_ENVIRONMENT=production
VITE_SENTRY_RELEASE=v1.0.0
```

---

## Шаг 4: Установить зависимости

**Backend:**

```bash
cd backend
pip install structlog>=23.3.0
# или
pip install -r requirements.txt
```

**Frontend:**

```bash
cd frontend
npm install @sentry/react
# или
npm install
```

---

## Шаг 5: Добавить инициализацию Sentry (Frontend)

**Файл:** `frontend/src/main.tsx`

```typescript
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { initSentry } from './instrumentation/sentry';  // ← Добавить
import App from './App';
import './index.css';

// Инициализировать Sentry ПЕРЕД рендерингом
initSentry();  // ← Добавить

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

---

## Шаг 6: Перезапуск приложений

```bash
# Перезапуск контейнеров
docker compose restart backend frontend

# Проверка логов
docker logs sattva-backend --tail 50
docker logs sattva-frontend --tail 50
```

---

## Шаг 7: Проверка работы

### 7.1. Логи в Grafana

```bash
# Открыть Grafana
open http://localhost:3001  # Linux/Mac
start http://localhost:3001  # Windows
```

1. Login: `admin` / `admin`
2. Explore → Выбрать datasource: **Loki**
3. Query: `{app="sattva-tv"}`
4. Run query
5. Должны появиться логи

**Или дашборд:**
1. Dashboards → Browse
2. Открыть: **Logs Overview**
3. Должны быть графики и таблицы с логами

### 7.2. Ошибки в Glitchtip

```bash
# Открыть Glitchtip
open http://localhost:8080  # Linux/Mac
start http://localhost:8080  # Windows
```

1. Login
2. Projects → `sattva-tv-backend` или `sattva-tv-frontend`
3. Issues → Должны появиться ошибки (если были)

**Тест ошибки (Frontend):**

Открыть DevTools Console и выполнить:

```javascript
throw new Error('Test error from console');
```

Через 1-2 секунды ошибка появится в Glitchtip UI.

**Тест ошибки (Backend):**

```bash
curl -X GET http://localhost:8000/api/test-error
```

---

## Шаг 8: Использование в коде

### Backend (Python)

```python
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Обычные логи
logger.info("user_login", user_id=user.id, username=user.username)
logger.warning("rate_limit_exceeded", user_id=user.id, attempts=5)
logger.error("database_error", operation="insert_user", error=str(e))

# Исключения
try:
    risky_operation()
except Exception:
    logger.exception("operation_failed", operation="risky_operation")

# Sentry manual capture
import sentry_sdk
sentry_sdk.capture_exception(e)
sentry_sdk.capture_message("Important event", level="info")
```

### Frontend (TypeScript/React)

```typescript
import { 
  captureException, 
  captureMessage, 
  setSentryUser,
  clearSentryUser,
  SentryErrorBoundary 
} from './instrumentation/sentry';

// Установить пользователя (после логина)
setSentryUser({ id: user.id, username: user.username, email: user.email });

// Очистить пользователя (после логаута)
clearSentryUser();

// Захват ошибки
try {
  riskyOperation();
} catch (error) {
  captureException(error as Error, { operation: 'checkout' });
}

// Захват сообщения
captureMessage('User completed onboarding', 'info');

// Error Boundary
function App() {
  return (
    <SentryErrorBoundary fallback={<ErrorFallback />} showDialog={true}>
      <Routes />
    </SentryErrorBoundary>
  );
}
```

---

## 📊 Проверка статуса

```bash
# Проверка контейнеров
docker ps --filter "name=sattva"

# Должны быть запущены:
# - sattva-loki (порт 3100)
# - sattva-promtail
# - sattva-glitchtip-web (порт 8080)
# - sattva-glitchtip-worker
# - sattva-glitchtip-beat
# - sattva-glitchtip-db
# - sattva-glitchtip-redis

# Проверка логов
docker logs sattva-loki --tail 20
docker logs sattva-promtail --tail 20
docker logs sattva-glitchtip-web --tail 20

# Проверка health
curl http://localhost:3100/ready        # Loki
curl http://localhost:8080/             # Glitchtip
```

---

## 🔧 Troubleshooting

### Promtail не собирает логи

```bash
# Проверить конфигурацию
docker exec sattva-promtail cat /etc/promtail/config.yml

# Проверить позиции
docker exec sattva-promtail cat /tmp/positions.yaml

# Перезапустить
docker restart sattva-promtail
```

### Glitchtip не принимает события

```bash
# Проверить логи worker
docker logs sattva-glitchtip-worker --tail 100

# Проверить подключение к БД
docker exec sattva-glitchtip-web ./manage.py check

# Перезапустить стек
docker compose -f docker-compose.glitchtip.yml restart
```

### Frontend не отправляет ошибки

1. Проверить DSN в `.env.production`
2. Проверить инициализацию в `main.tsx`
3. Открыть DevTools Console — должно быть: "✅ Sentry initialized"
4. Проверить Network tab — должны быть запросы к `localhost:8080/api/`

---

## ✅ Checklist

- [ ] Все контейнеры запущены
- [ ] Glitchtip superuser создан
- [ ] Организация и проекты созданы в Glitchtip UI
- [ ] DSN добавлены в `.env` файлы
- [ ] Зависимости установлены (structlog, @sentry/react)
- [ ] `initSentry()` добавлен в `frontend/src/main.tsx`
- [ ] Контейнеры перезапущены
- [ ] Логи видны в Grafana (Logs Overview dashboard)
- [ ] Ошибки видны в Glitchtip UI
- [ ] Тестовая ошибка успешно отправлена и получена

---

## 📚 Дополнительная документация

- **Полная документация:** [docs/deployment/LOGGING_AND_ERROR_TRACKING_SETUP.md](LOGGING_AND_ERROR_TRACKING_SETUP.md)
- **Отчет Phase 2.2-2.3:** [docs/REPORTS/PHASE_2.2_2.3_COMPLETE.md](../REPORTS/PHASE_2.2_2.3_COMPLETE.md)
- **Roadmap:** [docs/development/refactoring-roadmap.md](../development/refactoring-roadmap.md)

---

**🎉 Готово! Observability stack настроен и работает.**

**Доступ:**
- Grafana (Logs): http://localhost:3001 (admin/admin)
- Glitchtip (Errors): http://localhost:8080 (ваш superuser)
