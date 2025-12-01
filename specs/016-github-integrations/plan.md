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

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** ✅
   - Спецификация на русском с 5 независимыми user stories
   - Измеримые критерии успеха (SC-001...SC-007)
   - 18 функциональных требований с трассируемостью

2. **Структура репозитория соблюдена (Принцип II)** ✅
   - Артефакты в `specs/016-github-integrations/`
   - Код будет в `backend/src/`, `streamer/`, `frontend/src/`
   - Тесты планируются в `backend/tests/`, `tests/smoke/`

3. **Тесты и наблюдаемость спланированы (Принцип III)** ✅
   - pytest для queue_service, auto_end_service, admin, metrics
   - Playwright для админ-панели UI
   - smoke-тесты для auto-end и очередей в streamer
   - Prometheus /metrics endpoint для наблюдаемости

4. **Документация и локализация покрыты (Принцип IV)** ✅
   - Обновление `docs/features/` с описанием новых модулей
   - Все сообщения и UI на русском
   - `npm run docs:validate` после завершения

5. **Секреты и окружения учтены (Принцип V)** ✅
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

### Источники интеграции

| Функция | Источник (GitHub) | Оценка времени | Приоритет |
|---------|-------------------|----------------|-----------|
| Система очередей | [YukkiMusicBot](https://github.com/TeamYukki/YukkiMusicBot) | 2-3 дня | P1 |
| Auto-end стримов | [YukkiMusicBot](https://github.com/TeamYukki/YukkiMusicBot) | 0.5 дня | P1 |
| Admin панель (sqladmin) | [telegram-bot-template](https://github.com/Latand/telegram-bot-template) | 2-3 дня | P2 |
| Prometheus метрики | [telegram-bot-template](https://github.com/Latand/telegram-bot-template) | 1 день | P2 |
| Аналитика событий | [telegram-bot-template](https://github.com/Latand/telegram-bot-template) | 1-2 дня | P2 |
| WebSocket мониторинг | [monitrix](https://github.com/user/monitrix) | 1-2 дня | P3 |

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

### Ключевые файлы из источников

| Источник | Файл/Модуль | Что адаптируем |
|----------|-------------|----------------|
| YukkiMusicBot | `YukkiMusic/core/queue.py` | Логика очереди, skip, clear |
| YukkiMusicBot | `YukkiMusic/plugins/play/callback.py` | PyTgCalls participants check |
| telegram-bot-template | `infrastructure/database/repo/` | SQLAlchemy patterns |
| telegram-bot-template | `bot/middlewares/` | Prometheus middleware pattern |
| monitrix | `src/websocket/` | Real-time event broadcasting |

## Complexity Tracking

> Нет нарушений Constitution — все компоненты соответствуют существующей архитектуре.
