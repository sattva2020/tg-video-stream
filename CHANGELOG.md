# Changelog

Все важные изменения проекта документируются в этом файле.

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
и этот проект следует [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added (Phase 2.2-2.3) - 2025-12-27

#### Centralized Logging (Loki + Promtail)

- Добавлен Loki 2.9.3 для централизованного хранения логов
- Добавлен Promtail 2.9.3 для сбора логов из 6 источников:
  - Backend JSON logs (`/app/backend/logs/*.log`)
  - Frontend logs (`/app/frontend/logs/*.log`)
  - Docker container logs (`/var/lib/docker/containers/*/*.log`)
  - Syslog (`/var/log/syslog`)
  - Nginx access logs (`/var/log/nginx/access.log`)
  - Nginx error logs (`/var/log/nginx/error.log`)
- Создан модуль structured logging для Python: `backend/src/utils/logging_config.py`
- Добавлена зависимость `structlog>=23.3.0` в `backend/requirements.txt`
- Настроена интеграция Loki с Grafana (datasource provisioning)
- Создан дашборд **Logs Overview** с 16 панелями для визуализации логов
- Конфигурация Loki с 30-дневной retention policy
- Конфигурация Promtail с pipeline stages (JSON parsing, regex extraction, labels)

**Файлы:**
- `docker-compose.monitoring.yml` - добавлены сервисы Loki и Promtail
- `config/monitoring/loki-config.yml` - конфигурация Loki
- `config/monitoring/promtail-config.yml` - конфигурация Promtail
- `backend/src/utils/logging_config.py` - structured logging
- `config/monitoring/grafana/provisioning/datasources.yml` - Loki datasource
- `config/monitoring/grafana/dashboards/logs-overview.json` - дашборд

#### Error Tracking & APM (Glitchtip + Sentry SDK)

- Добавлен self-hosted Glitchtip stack для error tracking
- Создан `docker-compose.glitchtip.yml` с 6 сервисами:
  - glitchtip-web (порт 8080) - веб-интерфейс и API
  - glitchtip-worker - Celery worker для обработки событий
  - glitchtip-beat - планировщик задач
  - glitchtip-migrate - автоматическая миграция БД
  - glitchtip-db - PostgreSQL 15
  - glitchtip-redis - Redis 7
- Проверена существующая backend Sentry integration (`backend/src/instrumentation/sentry.py`, 684 lines)
- Создана новая frontend Sentry integration (`frontend/src/instrumentation/sentry.ts`, 145 lines):
  - BrowserTracing с React Router v6
  - Session Replay (10% sample rate, 100% on errors)
  - Error boundaries для React
  - User authentication context
  - Manual exception/message capture helpers
  - Filtering (browser extensions, ad blockers)
- Добавлена зависимость `@sentry/react` в `frontend/package.json`

**Файлы:**
- `docker-compose.glitchtip.yml` - Glitchtip stack
- `frontend/src/instrumentation/sentry.ts` - React Sentry integration

#### Документация

- Создана полная документация: `docs/deployment/LOGGING_AND_ERROR_TRACKING_SETUP.md`
- Создан отчет о завершении: `docs/REPORTS/PHASE_2.2_2.3_COMPLETE.md`
- Создан Quick Start guide: `docs/deployment/QUICK_START_LOGGING_AND_ERRORS.md`
- Обновлен `docs/development/refactoring-roadmap.md` (Phase 2.2 и 2.3 отмечены как завершенные)

**Observability Stack теперь полностью настроен:**
- ✅ Метрики (Prometheus + Grafana) - Phase 2.1
- ✅ Логи (Loki + Promtail) - Phase 2.2
- ✅ Ошибки (Glitchtip + Sentry SDK) - Phase 2.3
- ✅ Alerts (Alertmanager → Telegram) - Phase 2.1

---

## [0.1.0] - 2025-12-24

### Added (Phase 0 & Phase 2.1)

#### i18n Improvements (Phase 0.1)
- Исправлена асинхронная инициализация i18n с React Suspense
- Убран `window.location.reload()` - языки переключаются без перезагрузки страницы
- Проверена работа для всех языков (en, ru, uk, de)

#### Project Structure Cleanup (Phase 0.2)
- Организована структура проекта согласно `PROJECT_STRUCTURE_GUIDELINES.md`
- Перемещены отчёты в `docs/REPORTS/`
- Перемещена deployment документация в `docs/deployment/`
- Перемещены AI инструкции в `ai-instructions/`
- Удалены устаревшие временные файлы

#### Secrets Management (Phase 1.2)
- Внедрен SOPS + age для шифрования секретов
- Создан `.env.master` - мастер-файл секретов (36 переменных)
- Создан `.env.enc` - зашифрованная версия (безопасно коммитить)
- Созданы скрипты:
  - `scripts/encrypt-secrets.sh` - шифрование
  - `scripts/decrypt-secrets.sh` - расшифровка
  - `scripts/preflight-env.sh` - проверка перед деплоем
- Интеграция с CI/CD: job `env-preflight` в `.github/workflows/ci.yml`

#### Dokploy Alternative (Phase 1.2.1)
- Подготовлена альтернатива: Dokploy (self-hosted PaaS)
- Созданы скрипты:
  - `scripts/setup-dokploy.sh` - установка на VPS
  - `scripts/deploy-dokploy.sh` - деплой через API
  - `scripts/migrate-to-dokploy.sh` - миграция секретов
- Создан `docker-compose.dokploy.yml` с Traefik labels
- Документация: `docs/deployment/DOKPLOY_DEPLOYMENT.md`

#### Security Headers (Phase 1.3)
- Настроены security headers в nginx:
  - Content-Security-Policy
  - X-Frame-Options
  - X-Content-Type-Options
  - X-XSS-Protection
  - Strict-Transport-Security (HSTS)
  - Referrer-Policy
  - Permissions-Policy
- Конфигурация: `config/nginx/security-headers.conf`
- Достигнут рейтинг **A+** на securityheaders.com (dev environment)

#### Advanced Monitoring (Phase 2.1)
- Создано 3 расширенных Grafana дашборда:
  - `backend-advanced.json` (21 панель) - HTTP metrics, DB pool, latency heatmap
  - `postgres-advanced.json` (20 панелей) - transactions, locks, deadlocks, cache hit ratio
  - `system-advanced.json` (23 панели) - CPU/Memory/Disk/Network with thresholds
- Настроено 50+ alert rules в 4 категориях:
  - `critical.yml` - критические алерты (StreamerDown, BackendDown, DatabaseDown, HighErrorRate)
  - `warning.yml` - предупреждения (HighLatency, ElevatedErrorRate, DiskSpaceWarning)
  - `performance.yml` - производительность (BackendResponseTimeDegraded, DatabaseSlowQueries)
  - `application.yml` - приложение (StreamQualityDegraded, TelegramAPIRateLimited)
- Настроена интеграция Alertmanager с Telegram (форматированные сообщения)
- Создан тестовый скрипт: `scripts/test-telegram-alerts.sh`
- Документация: `docs/deployment/TELEGRAM_ALERTS_SETUP.md`

---

## [0.0.1] - 2025-12-23

### Added

- Инициализация проекта
- Базовая структура Frontend (React + TypeScript + Vite)
- Базовая структура Backend (FastAPI + Python)
- Docker Compose оркестрация
- Базовый мониторинг (Prometheus + Grafana)
- i18n поддержка (en, ru, uk, de)
- Telegram бот интеграция
- Music streaming функционал

---

[Unreleased]: https://github.com/yourusername/sattva-tv/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/sattva-tv/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/yourusername/sattva-tv/releases/tag/v0.0.1
