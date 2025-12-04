# Implementation Plan: Интеграция компонентов из GitHub-проектов

**Branch**: `016-github-integrations` | **Date**: 2025-12-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/016-github-integrations/spec.md`

## Summary

Интеграция проверенных паттернов из open-source проектов (YukkiMusicBot, telegram-bot-template, monitrix) в Sattva Streamer:
- Система очередей с персистентностью в Redis и автопереключением треков
- Автоматическое завершение пустых стримов (auto-end) через PyTgCalls events
- Административная панель на базе sqladmin для FastAPI
- Prometheus метрики и WebSocket мониторинг в реальном времени

## Technical Context

**Language/Version**: Python 3.11+, TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy, Redis, PyTgCalls, Pyrogram, sqladmin, prometheus_client  
**Storage**: PostgreSQL (users, audit logs), Redis (очереди, auto-end таймеры, метрики кеш)  
**Testing**: pytest (backend), Playwright/Vitest (frontend), smoke-скрипты (streamer)  
**Target Platform**: Linux server (Ubuntu 22.04), systemd services  
**Project Type**: Web application (backend + frontend + streamer)  
**Performance Goals**: <1 сек переключение треков, <200ms p95 для API, <2 сек WebSocket updates  
**Constraints**: Обратная совместимость API, <5% overhead от метрик, использование существующего WebSocket  
**Scale/Scope**: 1-10 одновременных стримов, 50+ WebSocket соединений

## Design Principles

*Практические принципы для этой фичи:*

1. **SSoT (Единый источник правды)** ✅
   - Спецификация на русском с 5 независимыми user stories
   - Измеримые критерии успеха (SC-001...SC-007)
   - 19 функциональных требований с трассируемостью

2. **Структура репозитория** ✅
   - Артефакты в `specs/016-github-integrations/`
   - Код будет в `backend/src/`, `streamer/`, `frontend/src/`
   - Тесты в `backend/tests/`, `tests/smoke/`

3. **Тесты и наблюдаемость** ✅
   - pytest для queue_service, auto_end_service, admin, metrics
   - Playwright для админ-панели UI
   - smoke-тесты для auto-end и очередей
   - Prometheus /metrics эндпоинты (streamer:9090 + backend API)

4. **Документация и локализация** ✅
   - Обновление `docs/features/` с описанием новых модулей
   - Все сообщения и UI на русском
   - `npm run docs:validate` после завершения

5. **Секреты и окружения** ✅
   - Новые переменные: `AUTO_END_TIMEOUT_MINUTES`, `PLACEHOLDER_AUDIO_PATH`
   - Добавить в `template.env` перед `.env`
   - Prometheus не требует секретов

## Project Structure

### Documentation (this feature)

```text
specs/016-github-integrations/
├── plan.md              # This file
├── research.md          # Phase 0: исследование PyTgCalls events, sqladmin, prometheus_client
├── data-model.md        # Phase 1: Queue, StreamMetrics, AdminAuditLog
├── quickstart.md        # Phase 1: инструкции по запуску и тестированию
├── contracts/           # Phase 1: OpenAPI для queue, metrics, admin endpoints
└── tasks.md             # Phase 2: декомпозиция на задачи
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   ├── admin.py           # Расширение существующего
│   │   ├── metrics.py         # NEW: /metrics endpoint
│   │   ├── queue.py           # NEW: /api/queue/* endpoints
│   │   └── websocket.py       # Расширение для monitoring events
│   ├── models/
│   │   └── audit_log.py       # NEW: AdminAuditLog модель
│   ├── services/
│   │   ├── queue_service.py   # NEW: логика очереди с Redis
│   │   ├── auto_end_service.py # NEW: логика auto-end
│   │   └── metrics_service.py # EXTEND: добавить Prometheus экспорт (уже есть)
│   └── admin/
│       ├── __init__.py        # NEW: sqladmin setup
│       ├── views.py           # NEW: UserAdmin, PlaylistAdmin, etc.
│       └── auth.py            # NEW: аутентификация админ-панели
└── tests/
    ├── test_queue_service.py       # NEW
    ├── test_auto_end_service.py    # NEW
    ├── test_prometheus_metrics.py  # NEW
    └── api/
        └── test_admin_panel.py     # NEW

streamer/
├── queue_manager.py       # EXTEND: интеграция с Redis, placeholder support (уже есть StreamQueue)
├── auto_end.py            # NEW: отслеживание слушателей через PyTgCalls
└── metrics.py             # EXTEND: экспорт в Prometheus формат

frontend/
└── src/
    └── pages/
        └── Monitoring.tsx   # NEW: real-time dashboard

tests/
└── smoke/
    ├── test_queue_operations.sh    # NEW
    └── test_auto_end.sh            # NEW
```

**Structure Decision**: Web application (Option 2) — существующая структура backend/frontend/streamer сохраняется, добавляются новые модули в каждый компонент.

## Roadmap

### Источники интеграции (обновлено после реализации)

| Функция | Источник | Статус | Примечание |
|---------|----------|--------|------------|
| Система очередей | Собственная реализация (Redis) | ✅ Реализовано | `backend/src/services/queue_service.py` |
| Auto-end стримов | Собственная реализация (PyTgCalls) | ✅ Реализовано | `backend/src/services/auto_end_service.py` |
| Admin панель | [sqladmin](https://github.com/aminalaee/sqladmin) (официальная библиотека) | ✅ Реализовано | `backend/src/admin/` |
| Prometheus метрики | [prometheus_client](https://github.com/prometheus/client_python) (официальная библиотека) | ✅ Реализовано | `backend/src/services/prometheus_metrics.py` |
| Аналитика событий | Собственная реализация (AdminAuditLog) | ✅ Реализовано | `backend/src/models/audit_log.py` |
| WebSocket мониторинг | Расширение ConnectionManager | ✅ Реализовано | `backend/src/api/websocket.py` |

> **Примечание**: После анализа репозитория `Latand/tgbot_template_v3` было выяснено, что он не содержит sqladmin или prometheus_client интеграции. Все компоненты были реализованы с использованием официальных библиотек и best practices.

### Timeline

```
Week 1 (P1 - Core):
├── Day 1-2: Система очередей с Redis persistence
├── Day 3:   Auto-end стримов (PyTgCalls events)
└── Day 3:   Smoke-тесты для queue и auto-end

Week 2 (P2 - Admin & Metrics):
├── Day 4-5: Admin панель (sqladmin setup, views, auth)
├── Day 6:   Prometheus метрики (/metrics endpoint)
└── Day 7:   Аналитика событий (audit logs)

Week 3 (P3 - Monitoring):
├── Day 8-9: WebSocket мониторинг (расширение ConnectionManager)
├── Day 10:  Frontend Monitoring.tsx dashboard
└── Day 10:  Integration tests, documentation
```

**Общая оценка**: 8-12 рабочих дней

### Ключевые реализованные файлы

| Компонент | Файл | Описание |
|-----------|------|----------|
| Queue Service | `backend/src/services/queue_service.py` | CRUD операции с очередью, Redis persistence |
| Auto-End | `backend/src/services/auto_end_service.py` | Таймеры завершения пустых стримов |
| Admin Panel | `backend/src/admin/__init__.py`, `views.py`, `auth.py` | sqladmin интеграция |
| Prometheus | `backend/src/services/prometheus_metrics.py` | Метрики и гауджи |
| Middleware | `backend/src/middleware/prometheus.py` | HTTP request tracking |
| Queue API | `backend/src/api/queue.py` | REST эндпоинты для очереди |
| Metrics API | `backend/src/api/metrics.py` | /metrics Prometheus endpoint |
| WebSocket | `backend/src/api/websocket.py` | Real-time events (расширен) |
| Frontend | `frontend/src/pages/Monitoring.tsx` | Real-time dashboard |
| Audit Log | `backend/src/models/audit_log.py` | Модель для логов админ-действий |

## Implementation Status: ✅ COMPLETED

**Все 62 задачи выполнены** (tasks.md)

### Реализованные функции:
- ✅ Система очередей с Redis persistence
- ✅ Auto-end стримов с PyTgCalls
- ✅ Admin панель на sqladmin
- ✅ Prometheus метрики (/metrics)
- ✅ WebSocket real-time мониторинг
- ✅ Audit logging
- ✅ Frontend Monitoring dashboard

## Complexity Tracking

> **Prometheus архитектура**: Два источника метрик:
> - `streamer:9090/metrics` — уже реализовано (PyTgCalls, стримы)
> - `backend:8000/api/v1/metrics` — NEW (API latency, HTTP requests, DB)
>
> Все компоненты соответствуют существующей архитектуре.
