# Implementation Plan: Реальные данные мониторинга системы

**Branch**: `015-real-system-monitoring` | **Date**: 2025-11-30 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/015-real-system-monitoring/spec.md`

## Summary

Подключение реальных данных в блоки Dashboard "Здоровье системы" (SystemHealth) и "Активность" (ActivityTimeline). Backend получает метрики через psutil + pg_stat_activity, frontend polling каждые 30 секунд. События записываются в новую таблицу `activity_events` при действиях пользователей/системы.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, psutil, SQLAlchemy/Alembic (backend); React 18, TanStack Query, date-fns (frontend)  
**Storage**: PostgreSQL 16 (systemd service) — таблица `activity_events`  
**Testing**: pytest (backend), Vitest (frontend unit), Playwright (e2e)  
**Target Platform**: Ubuntu 24.04 LXC (VPS), современные браузеры  
**Project Type**: Web application (backend + frontend)  
**Performance Goals**: Latency получения метрик <500ms, обновление каждые 30 сек  
**Constraints**: Минимальная нагрузка от polling (один запрос в 30 сек), хранение последних 1000 событий  
**Scale/Scope**: Один сервер, 1-2 администратора, ~50 пользователей

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** — ✅ Спецификация на русском с 4 независимыми user stories, измеримыми критериями успеха (SC-001...SC-005). Каждая история имеет acceptance scenarios.

2. **Структура репозитория соблюдена (Принцип II)** — ✅ Артефакты в `specs/015-real-system-monitoring/`, код в `backend/src/` и `frontend/src/`, тесты в `backend/tests/` и `frontend/tests/`.

3. **Тесты и наблюдаемость спланированы (Принцип III)** — ✅ Планируются:
   - pytest: `backend/tests/api/test_system_metrics.py`, `backend/tests/api/test_activity_events.py`
   - Vitest: `frontend/src/components/dashboard/__tests__/SystemHealth.test.tsx`
   - Playwright: `frontend/tests/dashboard-monitoring.spec.ts`

4. **Документация и локализация покрыты (Принцип IV)** — ✅ Обновления:
   - `docs/api/system-metrics.md` — новый endpoint
   - `docs/api/activity-events.md` — новый endpoint
   - Локализация: ключи `dashboard.health.*`, `dashboard.activity.*` в i18n

5. **Секреты и окружения учтены (Принцип V)** — ✅ Новые переменные не требуются. Используется существующее подключение к БД через `DATABASE_URL`. psutil работает локально без секретов.

## Project Structure

### Documentation (this feature)

```text
specs/015-real-system-monitoring/
├── plan.md              # Этот файл
├── research.md          # Phase 0: исследование psutil, pg_stat_activity
├── data-model.md        # Phase 1: схема ActivityEvent
├── quickstart.md        # Phase 1: быстрый старт для тестирования
├── contracts/           # Phase 1: OpenAPI для новых endpoints
│   └── system-monitoring-api.yaml
└── tasks.md             # Phase 2: детальные задачи (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── system.py          # NEW: /api/system/metrics, /api/system/activity
│   ├── models/
│   │   └── activity_event.py  # NEW: ActivityEvent SQLAlchemy model
│   └── services/
│       └── metrics_service.py # NEW: psutil + pg_stat_activity collection
├── migrations/
│   └── versions/
│       └── xxx_add_activity_events.py  # NEW: Alembic migration
└── tests/
    └── api/
        ├── test_system_metrics.py      # NEW
        └── test_activity_events.py     # NEW

frontend/
├── src/
│   ├── api/
│   │   └── system.ts                   # NEW: API client for /api/system/*
│   ├── components/dashboard/
│   │   ├── SystemHealth.tsx            # MODIFY: real data from API
│   │   └── ActivityTimeline.tsx        # MODIFY: real data from API
│   ├── hooks/
│   │   └── useSystemMetrics.ts         # NEW: TanStack Query hook
│   └── types/
│       └── system.ts                   # NEW: SystemMetrics, ActivityEvent types
└── tests/
    └── dashboard-monitoring.spec.ts    # NEW: Playwright e2e
```

**Structure Decision**: Web application structure (Option 2). Backend и frontend уже существуют, добавляем новые файлы без изменения архитектуры.

## Complexity Tracking

> Нет нарушений Constitution — простое расширение существующей функциональности.
