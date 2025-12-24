# 📋 План исправления критических проблем проекта

> **Создан:** 23 декабря 2025  
> **Статус:** В работе  
> **Текущая версия:** 1.0  
> **Автор:** Senior DevOps Engineer (Jarvis)

---

## 🎯 Цель: Довести проект до Production-Ready состояния

**Текущий статус:** `4/10` → **Целевой:** `8/10`

---

## 📊 Оценка текущего состояния

### Что работает ✅
- Базовый функционал реализован
- Docker контейнеризация присутствует
- TypeScript используется (хоть и с `any`)
- Есть попытки документации

### Критические проблемы ❌
1. **Security** - уязвимости 🔴 CRITICAL
2. **Performance** - не масштабируется 🔴 CRITICAL  
3. **Infrastructure** - ngrok в продакшене 🔴 CRITICAL
4. **i18n** - неправильная архитектура 🟠 HIGH
5. **Testing** - отсутствует покрытие 🟠 HIGH
6. **Monitoring** - нет observability 🟡 MEDIUM

---

## 🔥 PHASE 0: Немедленные исправления (1-3 дня)

### Приоритет: CRITICAL 🔴

**Цель:** Исправить блокеры, которые ломают работу СЕЙЧАС

### 0.1. Починить i18n 

**Статус:** ✅ ЗАВЕРШЕНО (24 декабря 2025)

**Решённые проблемы:**
- ✅ i18n инициализируется асинхронно с Promise + Suspense
- ✅ Убран `window.location.reload()` - используется React re-render
- ✅ Переключение языков работает плавно БЕЗ перезагрузки страницы
- ⚠️ Дубликаты ключей (126.5% вместо 100%) - откладываем на Phase 5.3
- ⚠️ Bundle size 533KB - оптимизация в Phase 4.1

**Выполненные задачи:**
- [x] Исправить асинхронную инициализацию i18n с Suspense
- [x] Убрать `window.location.reload()` → использовать React re-render
- [ ] Удалить дубликаты ключей (126.5% → 100%) - перенесено в Phase 5.3
- [x] Проверить работу переключения всех языков (en, ru, uk, de)
- [x] Тестирование в dev environment

**Файлы:**
- `frontend/src/i18n.ts`
- `frontend/src/App.tsx`
- `frontend/src/components/auth/LanguageSwitcher.tsx`

**Критерий успеха:** Языки переключаются без перезагрузки страницы, все переводы отображаются

---

### 0.2. Очистить структуру проекта

**Статус:** ✅ ЗАВЕРШЕНО (24 декабря 2025)

**Решено:**
- ✅ Все отчёты перемещены в `docs/REPORTS/`
- ✅ Deployment документация в `docs/deployment/`
- ✅ AI инструкции в `ai-instructions/`
- ✅ Удалены устаревшие временные файлы
- ✅ Корень проекта содержит только критичные файлы

**Выполненные задачи:**
- [x] Переместить `DEPLOYMENT_VPS_SUCCESS.md` в `docs/REPORTS/`
- [x] Переместить `DEPLOYMENT_CHECKLIST.md` в `docs/deployment/`
- [x] Переместить `OUTSTANDING_TASKS_REPORT.md` в `docs/REPORTS/`
- [x] Переместить `SUCCESS_SUMMARY.md` в `docs/REPORTS/`
- [x] Переместить `UI_UX_REVIEW.md` в `docs/REPORTS/`
- [x] Переместить `NEXT_PHASE_INSTRUCTIONS.md` в `ai-instructions/`
- [x] Переместить `GEMINI.md` в `ai-instructions/`
- [x] Переместить `PROJECT_SUMMARY.md` в `docs/`
- [x] Удалить `eMySattvatelegramscriptsuk_missing_keys.txt`
- [x] Проверить соответствие `PROJECT_STRUCTURE_GUIDELINES.md`

**Файлы в корне (только критичные):**
- `README.md` - главная документация
- `PROJECT_STRUCTURE_GUIDELINES.md` - правила структуры
- `STRUCTURE_QUICK_REFERENCE.md` - быстрый справочник
- `docker-compose.yml`, `docker-compose.local.yml` - оркестрация
- `package.json` - npm конфигурация
- `requirements-dev.txt` - Python dev зависимости
- `.env`, `.gitignore` и прочие конфигурационные файлы

**Критерий успеха:** ✅ В корне только критичные файлы согласно PROJECT_STRUCTURE_GUIDELINES.md

---

### 0.3. Audit секретов в Git

**Статус:** ✅ ЗАВЕРШЕНО (24 декабря 2025) - **ТРЕБУЕТ ДЕЙСТВИЙ!**

**Выявлено:**
- ✅ `.env` файлы защищены в `.gitignore`
- ✅ `.env.example` файлы существуют
- ✅ Текущие `.env` файлы НЕ в Git (удалены коммитом e2b98442)
- 🚨 **КРИТИЧНО:** Telegram API credentials (API_ID, API_HASH) найдены в истории Git (коммит fecdc4f1)
- ⚠️ Тестовые пароли в комментариях документации

**Выполненные задачи:**
- [x] Проверить `.gitignore` на наличие `.env`
- [x] Поиск `.env` файлов в Git истории
- [x] Поиск секретов (password, token, secret, api_key) в коммитах
- [x] Проверить наличие `.env.example`
- [x] Создан отчёт о найденных уязвимостях

**ТРЕБУЕТСЯ НЕМЕДЛЕННАЯ РОТАЦИЯ:**
- [ ] 🔴 **Telegram API credentials** - API_ID и API_HASH скомпрометированы
  - Удалить старое приложение на https://my.telegram.org/apps
  - Создать новое приложение
  - Обновить `.env` файлы
  - Перезапустить backend

**Опционально (низкий приоритет):**
- [ ] Очистка Git истории с BFG Repo-Cleaner (если репозиторий публичный)
- [ ] Проверка всех паролей БД на продакшене

**Критерий успеха:** ⚠️ Частично выполнен - найдены критические уязвимости, требуется ротация

---

## 🛡️ PHASE 1: Security & Stability (1-2 недели)

### Приоритет: HIGH 🟠

**Цель:** Закрыть критические дыры безопасности

### 1.1. Заменить ngrok на реальный домен

**Статус:** ⏳ НЕ НАЧАТО

**Проблемы:**
- ngrok для продакшена - временное решение
- URL меняется при рестарте
- Нет гарантий стабильности

**Задачи:**
- [ ] Купить домен (или использовать поддомен существующего)
- [ ] Настроить DNS A-record на VPS IP (37.53.91.144)
- [ ] Установить Certbot: `apt install certbot python3-certbot-nginx`
- [ ] Получить SSL сертификат: `certbot --nginx -d ваш-домен.com`
- [ ] Обновить nginx конфиг с новым доменом
- [ ] Обновить `.env` файлы (DOMAIN, BACKEND_URL, FRONTEND_URL)
- [ ] Протестировать HTTPS
- [ ] Настроить auto-renewal: `certbot renew --dry-run`

**Конфигурация nginx:**
```nginx
server {
    listen 80;
    server_name ваш-домен.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ваш-домен.com;
    
    ssl_certificate /etc/letsencrypt/live/ваш-домен.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ваш-домен.com/privkey.pem;
    
    # ... остальная конфигурация
}
```

**Критерий успеха:** Приложение доступно по https://ваш-домен.com с валидным SSL

---

### 1.2. Secret Management

**Статус:** ⏳ НЕ НАЧАТО

**Проблемы:**
- Секреты в `.env` plain text
- Нет ротации секретов
- Риск компрометации при утечке сервера

**Задачи:**

**Вариант A: HashiCorp Vault (рекомендуется для production)**
- [ ] Установить Vault: `docker run -d --name=vault -p 8200:8200 vault`
- [ ] Инициализировать Vault
- [ ] Создать политики доступа
- [ ] Мигрировать секреты из `.env` в Vault
- [ ] Обновить приложение для чтения из Vault
- [ ] Настроить автоматическую ротацию

**Вариант B: Облачное решение**
- AWS Secrets Manager
- Azure Key Vault
- Google Cloud Secret Manager

**Вариант C: Простое решение (минимум)**
- [ ] Зашифровать `.env` с помощью `ansible-vault` или `sops`
- [ ] Хранить ключ шифрования отдельно (не в Git!)
- [ ] Расшифровка при деплое

**Критерий успеха:** Секреты не хранятся в plain text, есть процесс ротации

---

### 1.3. Security Headers

**Статус:** ⏳ НЕ НАЧАТО

**Задачи:**
- [ ] Добавить security headers в nginx:

```nginx
# config/nginx/security-headers.conf
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' wss: https:; frame-ancestors 'none';" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

- [ ] Настроить CORS правильно в backend:

```python
# backend/src/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ваш-домен.com"],  # Конкретный домен!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600,
)
```

- [ ] Добавить rate limiting в nginx:

```nginx
# config/nginx/rate-limit.conf
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
}

location /api/auth/login {
    limit_req zone=login_limit burst=2 nodelay;
}
```

- [ ] Тестирование на https://securityheaders.com/

**Критерий успеха:** A+ на securityheaders.com, rate limiting работает

---

### 1.4. Аутентификация и 2FA

**Статус:** ⏳ НЕ НАЧАТО

**Задачи:**
- [ ] Добавить 2FA для админов (TOTP):
  - Установить `pyotp`
  - Добавить поле `totp_secret` в User model
  - Endpoint для генерации QR кода
  - Endpoint для верификации кода
  - UI для настройки 2FA

- [ ] Улучшить JWT токены:
  - Refresh tokens с rotation
  - Access token TTL = 15 минут
  - Refresh token TTL = 7 дней
  - Blacklist для отозванных токенов (Redis)

- [ ] Session management:
  - Хранение сессий в Redis
  - "Logout from all devices"
  - "Active sessions" для пользователя

- [ ] Дополнительно:
  - Password strength requirements
  - Password reset flow
  - Account lockout после N failed attempts

**Пример кода:**
```python
# backend/src/services/auth_service.py
import pyotp

def generate_totp_secret(user_id: int) -> str:
    secret = pyotp.random_base32()
    # Сохранить в БД
    return secret

def verify_totp(user_id: int, token: str) -> bool:
    secret = get_user_totp_secret(user_id)
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)
```

**Критерий успеха:** Все админы используют 2FA, refresh tokens работают

---

## 📈 PHASE 2: Observability (2-3 недели)

### Приоритет: HIGH 🟠

**Цель:** Видеть что происходит в системе

### 2.1. Monitoring (Prometheus + Grafana)

**Статус:** ⏳ НЕ НАЧАТО

**Задачи:**
- [ ] Создать `docker-compose.monitoring.yml`:

```yaml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./config/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./config/monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_INSTALL_PLUGINS=redis-datasource

  node_exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'

  postgres_exporter:
    image: prometheuscommunity/postgres-exporter:latest
    environment:
      DATA_SOURCE_NAME: "postgresql://user:password@postgres:5432/db?sslmode=disable"
    ports:
      - "9187:9187"

volumes:
  prometheus_data:
  grafana_data:
```

- [ ] Настроить `config/monitoring/prometheus.yml`
- [ ] Создать Grafana дашборды:
  - System metrics (CPU, RAM, Disk, Network)
  - Application metrics (requests/sec, errors, latency)
  - Database metrics (connections, queries, cache hit ratio)
  - Custom business metrics

- [ ] Добавить метрики в приложение:
```python
# backend/requirements.txt
prometheus-fastapi-instrumentator

# backend/src/main.py
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

**Критерий успеха:** Real-time мониторинг всех компонентов в Grafana

---

### 2.2. Centralized Logging (Loki)

**Статус:** ⏳ НЕ НАЧАТО

**Задачи:**
- [ ] Добавить Loki + Promtail в `docker-compose.monitoring.yml`:

```yaml
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./config/monitoring/loki-config.yml:/etc/loki/local-config.yaml
      - loki_data:/loki

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log:ro
      - ./logs:/app/logs:ro
      - ./config/monitoring/promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
```

- [ ] Структурированное логирование в приложении:

```python
# backend/src/utils/logger.py
import structlog
import logging.config

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

- [ ] Log rotation:
```bash
# /etc/logrotate.d/telegram-app
/var/log/telegram-app/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
}
```

- [ ] Интеграция Loki с Grafana

**Критерий успеха:** Централизованные логи с поиском и фильтрацией в Grafana

---

### 2.3. Alerting (Alertmanager)

**Статус:** ⏳ НЕ НАЧАТО

**Задачи:**
- [ ] Добавить Alertmanager в `docker-compose.monitoring.yml`
- [ ] Создать alert rules в `config/monitoring/alerts.yml`:

```yaml
groups:
  - name: system_alerts
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage detected"
          description: "CPU usage is above 80% (current: {{ $value }}%)"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 85
        for: 5m
        labels:
          severity: warning

      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes * 100) < 10
        for: 5m
        labels:
          severity: critical

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 2m
        labels:
          severity: critical

      - alert: DatabaseConnectionFailure
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
```

- [ ] Настроить уведомления в Telegram:

```yaml
# config/monitoring/alertmanager.yml
receivers:
  - name: 'telegram'
    telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: YOUR_CHAT_ID
        parse_mode: 'HTML'
        message: |
          <b>{{ .GroupLabels.alertname }}</b>
          {{ range .Alerts }}
          {{ .Annotations.description }}
          {{ end }}
```

**Критерий успеха:** Получение уведомлений о проблемах в Telegram

---

### 2.4. APM (Application Performance Monitoring)

**Статус:** ⏳ НЕ НАЧАТО

**Варианты:**

**A. Sentry (рекомендуется)**
```bash
# Frontend
npm install @sentry/react

# Backend
pip install sentry-sdk[fastapi]
```

```typescript
// frontend/src/main.tsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "YOUR_SENTRY_DSN",
  environment: import.meta.env.MODE,
  tracesSampleRate: 1.0,
});
```

```python
# backend/src/main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)
```

**B. Self-hosted Glitchtip** (open-source альтернатива)

**Задачи:**
- [ ] Выбрать решение (Sentry cloud vs self-hosted Glitchtip)
- [ ] Интеграция в Frontend
- [ ] Интеграция в Backend
- [ ] Настроить source maps для production
- [ ] Error tracking
- [ ] Performance monitoring
- [ ] Release tracking

**Критерий успеха:** Все ошибки и performance issues отслеживаются

---

## 🧪 PHASE 3: Testing (2-3 недели)

### Приоритет: MEDIUM 🟡

**Цель:** Автоматизировать тестирование

### 3.1. Unit Tests

**Backend:**
```bash
# backend/tests/test_auth.py
import pytest
from fastapi.testclient import TestClient

def test_login_success(client: TestClient):
    response = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "password"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_protected_endpoint_without_token(client: TestClient):
    response = client.get("/api/admin/users")
    assert response.status_code == 401
```

**Frontend:**
```typescript
// frontend/tests/LanguageSwitcher.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import LanguageSwitcher from '@/components/auth/LanguageSwitcher';

describe('LanguageSwitcher', () => {
  it('switches language on click', async () => {
    render(<LanguageSwitcher />);
    const ukButton = screen.getByText('UK');
    fireEvent.click(ukButton);
    // Assertions...
  });
});
```

**Задачи:**
- [ ] Backend unit tests (coverage > 70%)
- [ ] Frontend unit tests (coverage > 60%)
- [ ] Настроить coverage reports
- [ ] Mock внешних зависимостей

**Критерий успеха:** Coverage reports показывают > 70% для backend, > 60% для frontend

---

### 3.2. Integration Tests

**Задачи:**
- [ ] API contract testing (Pact или Postman/Newman)
- [ ] Database migrations testing
- [ ] WebSocket testing
- [ ] E2E критических флоу (Playwright):

```typescript
// frontend/tests/e2e/auth.spec.ts
import { test, expect } from '@playwright/test';

test('user can login and access dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('[name="username"]', 'admin');
  await page.fill('[name="password"]', 'password');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('/admin/dashboard');
  await expect(page.locator('h1')).toContainText('Dashboard');
});
```

**Критерий успеха:** Критические user flows покрыты E2E тестами

---

### 3.3. CI/CD Pipeline

**Задачи:**
- [ ] Создать `.github/workflows/ci.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Lint
        run: |
          cd backend
          pylint src/
          mypy src/
      - name: Test
        run: |
          cd backend
          pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Lint
        run: |
          cd frontend
          npm run lint
          npm run type-check
      - name: Test
        run: |
          cd frontend
          npm run test:coverage
      - name: Build
        run: |
          cd frontend
          npm run build

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

  deploy:
    needs: [backend-tests, frontend-tests, security-scan]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          # Deployment script
```

- [ ] Pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json

  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/pylint
    rev: v3.0.3
    hooks:
      - id: pylint

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.56.0
    hooks:
      - id: eslint
        files: \.(js|ts|tsx)$
```

- [ ] Branch protection rules в GitHub

**Критерий успеха:** CI/CD проверяет всё автоматически, деплой только после прохождения тестов

---

## ⚡ PHASE 4: Performance Optimization (3-4 недели)

### Приоритет: MEDIUM 🟡

**Цель:** Ускорить приложение

### 4.1. Frontend Optimization

**Code Splitting:**
```typescript
// frontend/src/i18n.ts - Lazy loading переводов
import i18next from 'i18next';
import HttpBackend from 'i18next-http-backend';

i18next
  .use(HttpBackend)
  .init({
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    // Загружается только текущий язык!
  });
```

**React Performance:**
```typescript
// Мемоизация компонентов
export const ExpensiveComponent = React.memo(({ data }) => {
  const processedData = useMemo(() => {
    return heavyComputation(data);
  }, [data]);

  const handleClick = useCallback(() => {
    // ...
  }, []);

  return <div>{processedData}</div>;
});
```

**Задачи:**
- [ ] Разделить i18n на отдельные JSON файлы по языкам
- [ ] Lazy load переводов (только текущий язык)
- [ ] Route-based code splitting
- [ ] Vendor bundle optimization
- [ ] React.memo для тяжёлых компонентов
- [ ] useMemo/useCallback где нужно
- [ ] Virtual scrolling (react-window) для длинных списков
- [ ] Анализ с webpack-bundle-analyzer
- [ ] Tree shaking неиспользуемого кода

**Целевые метрики:**
- Bundle size: 533KB → < 300KB
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- Lighthouse score: > 90

---

### 4.2. Backend Optimization

**Database:**
```sql
-- Добавить индексы на частые запросы
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_channels_status ON channels(status) WHERE status = 'active';
CREATE INDEX idx_sessions_user_id ON sessions(user_id);

-- Composite индексы
CREATE INDEX idx_logs_user_date ON logs(user_id, created_at DESC);
```

```python
# Connection pooling
# backend/src/database/connection.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)
```

**Caching:**
```python
# backend/src/utils/cache.py
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

def cached(ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # Проверка кэша
            cached_value = redis_client.get(cache_key)
            if cached_value:
                return json.loads(cached_value)
            
            # Вызов функции
            result = await func(*args, **kwargs)
            
            # Сохранение в кэш
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

# Использование
@cached(ttl=600)
async def get_user_stats(user_id: int):
    # Тяжёлый запрос
    return stats
```

**Background tasks:**
```python
# backend/src/tasks/celery_app.py
from celery import Celery

celery_app = Celery('tasks', broker='redis://redis:6379/0')

@celery_app.task
def send_notification_email(user_id: int, message: str):
    # Отправка email асинхронно
    pass

# В endpoint
@app.post("/api/notify")
async def notify_user(user_id: int):
    send_notification_email.delay(user_id, "Hello")
    return {"status": "queued"}
```

**Задачи:**
- [ ] Добавить индексы на часто запрашиваемые поля
- [ ] Настроить connection pooling (PgBouncer опционально)
- [ ] Query optimization (EXPLAIN ANALYZE)
- [ ] Избежать N+1 (eager loading)
- [ ] Redis для кэширования
- [ ] Redis для сессий
- [ ] HTTP caching headers
- [ ] Background tasks (Celery/ARQ)
- [ ] WebSocket backpressure handling

**Целевые метрики:**
- API response time (p95): < 200ms
- Database query time (p95): < 50ms
- Cache hit ratio: > 80%

---

### 4.3. Infrastructure

**nginx optimization:**
```nginx
# config/nginx/performance.conf
# Compression
gzip on;
gzip_vary on;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

# Brotli (требует модуль)
brotli on;
brotli_comp_level 6;
brotli_types text/plain text/css text/xml text/javascript application/json application/javascript;

# Caching
location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# HTTP/2
listen 443 ssl http2;

# Buffers
client_body_buffer_size 128k;
client_max_body_size 50m;
```

**Задачи:**
- [ ] Включить Gzip/Brotli compression
- [ ] Настроить static files caching
- [ ] Включить HTTP/2
- [ ] Настроить CloudFlare (или другой CDN)
- [ ] Image optimization (WebP, lazy loading)
- [ ] PostgreSQL tuning:

```sql
-- /etc/postgresql/postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
max_connections = 100
work_mem = 5MB
```

**Критерий успеха:** 
- Lighthouse score > 90
- Страницы загружаются < 2 секунд

---

## 🏗️ PHASE 5: Architecture Refactoring (1-2 месяца)

### Приоритет: LOW 🟢

**Цель:** Подготовить к масштабированию

### 5.1. Backend - Слоёная архитектура

**Текущая структура:**
```
backend/src/
├── main.py
├── models/
├── routes/
└── utils/
```

**Целевая структура:**
```
backend/src/
├── api/
│   ├── dependencies.py
│   ├── v1/
│   │   ├── auth.py
│   │   ├── users.py
│   │   └── channels.py
├── core/
│   ├── config.py
│   ├── security.py
│   └── exceptions.py
├── domain/
│   ├── entities/
│   │   ├── user.py
│   │   └── channel.py
│   └── value_objects/
├── repositories/
│   ├── base.py
│   ├── user_repository.py
│   └── channel_repository.py
├── services/
│   ├── auth_service.py
│   ├── user_service.py
│   └── channel_service.py
├── schemas/
│   ├── requests/
│   └── responses/
└── infrastructure/
    ├── database/
    └── external/
```

**Пример:**
```python
# repositories/user_repository.py
class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    
    async def get_by_id(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).first()
    
    async def create(self, user_data: dict) -> User:
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        return user

# services/user_service.py
class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    async def register_user(self, username: str, password: str) -> UserResponse:
        # Business logic здесь
        hashed_password = hash_password(password)
        user = await self.user_repo.create({
            "username": username,
            "password": hashed_password
        })
        return UserResponse.from_orm(user)

# api/v1/users.py
@router.post("/users")
async def create_user(
    data: CreateUserRequest,
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.register_user(data.username, data.password)
```

**Задачи:**
- [ ] Разделить на слои (API → Service → Repository → DB)
- [ ] Dependency Injection
- [ ] DTOs (Pydantic schemas)
- [ ] Domain entities
- [ ] SOLID principles
- [ ] Repository pattern
- [ ] Service layer pattern

---

### 5.2. Frontend - Модульная архитектура

**Текущая структура:**
```
frontend/src/
├── components/
├── pages/
├── context/
└── utils/
```

**Целевая структура (Feature-based):**
```
frontend/src/
├── features/
│   ├── auth/
│   │   ├── components/
│   │   │   ├── LoginForm.tsx
│   │   │   └── LanguageSwitcher.tsx
│   │   ├── hooks/
│   │   │   └── useAuth.ts
│   │   ├── services/
│   │   │   └── authService.ts
│   │   ├── store/
│   │   │   └── authStore.ts
│   │   ├── types/
│   │   │   └── auth.types.ts
│   │   └── index.ts
│   ├── channels/
│   ├── playlist/
│   └── users/
├── shared/
│   ├── components/
│   │   ├── Button/
│   │   ├── Input/
│   │   └── Modal/
│   ├── hooks/
│   ├── utils/
│   └── types/
├── app/
│   ├── providers/
│   ├── router/
│   └── store/
└── lib/
    └── i18n/
```

**State Management (Zustand):**
```typescript
// features/auth/store/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      login: async (credentials) => {
        const user = await authService.login(credentials);
        set({ user, isAuthenticated: true });
      },
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    { name: 'auth-storage' }
  )
);
```

**Задачи:**
- [ ] Feature-based structure
- [ ] State Management (Zustand)
- [ ] Shared components library
- [ ] Custom hooks extraction
- [ ] TypeScript strict mode
- [ ] Barrel exports (index.ts)

---

### 5.3. i18n - Правильная реализация

**Разделение переводов:**
```
frontend/public/locales/
├── en/
│   ├── common.json
│   ├── auth.json
│   ├── dashboard.json
│   └── channels.json
├── ru/
├── uk/
└── de/
```

**Lazy loading:**
```typescript
// lib/i18n/config.ts
import i18next from 'i18next';
import HttpBackend from 'i18next-http-backend';

i18next
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    ns: ['common', 'auth', 'dashboard'],
    defaultNS: 'common',
    interpolation: {
      escapeValue: false,
    },
  });
```

**Pluralization:**
```json
{
  "itemCount": "{{count}} item",
  "itemCount_plural": "{{count}} items",
  "itemCount_zero": "No items"
}
```

**Date/Number localization:**
```typescript
const formattedDate = new Intl.DateTimeFormat(i18n.language).format(new Date());
const formattedNumber = new Intl.NumberFormat(i18n.language).format(1234.56);
```

**Задачи:**
- [ ] Разделить translations на namespace файлы
- [ ] Lazy loading (только текущий язык)
- [ ] Dynamic imports
- [ ] Удалить дубликаты (126.5% → 100%)
- [ ] Pluralization rules
- [ ] Date/Number localization (Intl API)
- [ ] Убрать hardcoded fallbacks `t('key', 'fallback')`
- [ ] Context для переводчиков (comments в JSON)
- [ ] Убрать `window.location.reload()`

**Критерий успеха:** 
- Загружается только 1 язык (~100KB вместо 533KB)
- Переключение без reload

---

## 🚀 PHASE 6: Scalability (2-3 месяца)

### Приоритет: LOW 🟢 (опционально)

**Цель:** Готовность к высоким нагрузкам

⚠️ **Примечание:** Эта фаза нужна только если ожидается > 10,000 одновременных пользователей

### 6.1. Kubernetes Migration

**Задачи:**
- [ ] Создать Kubernetes манифесты
- [ ] Helm charts для deployment
- [ ] ConfigMaps для конфигов
- [ ] Secrets для секретов
- [ ] Horizontal Pod Autoscaler
- [ ] Ingress controller (nginx-ingress)
- [ ] Service mesh (опционально, Istio/Linkerd)

### 6.2. Database High Availability

**Задачи:**
- [ ] PostgreSQL replication (master-slave)
- [ ] Read replicas
- [ ] Automated backups (pgBackRest)
- [ ] Point-in-time recovery
- [ ] Connection pooling (PgBouncer)

### 6.3. Load Balancing & Zero-Downtime

**Задачи:**
- [ ] Nginx load balancer
- [ ] Health checks endpoints
- [ ] Graceful shutdown
- [ ] Rolling updates
- [ ] Blue-green deployment strategy

**Критерий успеха:** 99.99% uptime, zero-downtime deployments

---

## 🎯 Приоритизация - Что делать СЕЙЧАС

### 🔴 **На этой неделе:**
1. ✅ Починить i18n переключение (в процессе)
2. Очистить структуру проекта (Phase 0.2)
3. Audit секретов в Git (Phase 0.3)
4. Заменить ngrok на реальный домен (Phase 1.1)

### 🟠 **Следующие 2 недели:**
5. Security headers (Phase 1.3)
6. 2FA для админов (Phase 1.4)
7. Мониторинг Prometheus + Grafana (Phase 2.1)
8. Centralized logging Loki (Phase 2.2)

### 🟡 **В течение месяца:**
9. Unit tests coverage 70% (Phase 3.1)
10. CI/CD pipeline (Phase 3.3)
11. Frontend optimization (Phase 4.1)
12. Database optimization (Phase 4.2)

### 🟢 **Когда будет время:**
13. Рефакторинг архитектуры (Phase 5)
14. Kubernetes migration (Phase 6) - только если нужно масштабирование

---

## 📊 Метрики успеха

| Метрика | Текущее | Целевое | Фаза |
|---------|---------|---------|------|
| **Security Score** | 2/10 | 9/10 | Phase 1 |
| **Lighthouse Performance** | ~40 | 90+ | Phase 4 |
| **Test Coverage Backend** | 0% | 70%+ | Phase 3 |
| **Test Coverage Frontend** | 0% | 60%+ | Phase 3 |
| **Bundle Size** | 533KB | <300KB | Phase 4 |
| **API Response Time (p95)** | ? | <200ms | Phase 4 |
| **Uptime** | ? | 99.9% | Phase 2 |
| **Time to Interactive** | ? | <3s | Phase 4 |
| **i18n Bundle per language** | 533KB (все) | ~100KB (один) | Phase 5 |

---

## ⏱️ Общий Timeline

| Фаза | Время | Критичность |
|------|-------|-------------|
| **Phase 0** | 1-3 дня | 🔴 CRITICAL |
| **Phase 1** | 1-2 недели | 🟠 HIGH |
| **Phase 2** | 2-3 недели | 🟠 HIGH |
| **Phase 3** | 2-3 недели | 🟡 MEDIUM |
| **Phase 4** | 3-4 недели | 🟡 MEDIUM |
| **Phase 5** | 1-2 месяца | 🟢 LOW |
| **Phase 6** | 2-3 месяца | 🟢 LOW (опционально) |

**Минимальный Production-Ready:** ~2 месяца (Phase 0-4)  
**Полная зрелость:** ~4-6 месяцев (Phase 0-6)

---

## 💡 Рекомендации

1. **Не пытайтесь сделать всё сразу** - работайте последовательно по фазам
2. **Phase 0-2 критичны** - без них production небезопасен
3. **Phase 3-4 необходимы** - для стабильности и производительности
4. **Phase 5-6 опциональны** - если не планируется масштабирование > 10K users

---

## 📝 Tracking Progress

Прогресс отслеживается в этом файле. Обновляйте чекбоксы по мере выполнения:
- [ ] Задача не начата (⏳)
- [x] Задача выполнена (✅)
- 🔄 В процессе

**Последнее обновление:** 23 декабря 2025

---

## 🔗 Связанные документы

- [PROJECT_STRUCTURE_GUIDELINES.md](../../PROJECT_STRUCTURE_GUIDELINES.md) - Структура проекта
- [DEPLOYMENT_CHECKLIST.md](../../DEPLOYMENT_CHECKLIST.md) - Чеклист деплоя
- [SSoT_full_ru_v1.3.md](../SSoT_full_ru_v1.3.md) - Технические требования

---

**Готовы начать? Предлагаю продолжить с Phase 0.1 - убедимся, что i18n работает после перезагрузки страницы пользователем.**
