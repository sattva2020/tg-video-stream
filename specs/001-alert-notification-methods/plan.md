# Implementation Plan: Способы оповещений (по аналогии с Zabbix)

**Branch**: `001-alert-notification-methods` | **Date**: 2025-12-10 | **Spec**: `specs/001-alert-notification-methods/spec.md`
**Input**: Feature specification from `/specs/001-alert-notification-methods/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Добавляем систему медиа-типов оповещений (по аналогии с Zabbix) с поддержкой email/Telegram/webhook/Slack/Teams/Discord/PagerDuty/Opsgenie/Pushover/SMS, управляемыми правилами маршрутизации, антиспамом и failover. Технический подход: использовать `apprise` как универсальный адаптер + точечные SDK (aiosmtplib, aiogram, httpx, slack_sdk, twilio), хранить каналы/шаблоны/правила/журналы в PostgreSQL, тестовая отправка и журналы через backend API.

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Celery + Redis broker (для фоновой доставки), httpx, aiosmtplib, aiogram, slack_sdk, twilio, apprise  
**Storage**: PostgreSQL 15 (каналы/правила/шаблоны/журналы) + Redis 7 (очереди задач/дедупликация)  
**Testing**: pytest (backend), Playwright/Vitest (frontend)  
**Target Platform**: Linux server (Docker Compose)  
**Project Type**: Web (backend + frontend)  
**Performance Goals**: p95 доставки уведомления (event → success/failover лог) ≤30s с учётом ретраев  
**Constraints**: 3 попытки, интервал 30s, таймауты 10s HTTP / 15s SMTP, параллелизм по каналу 5, failover по таймауту; dedup/rate-limit и silence windows обязательны  
**Scale/Scope**: До 10k событий/день, ≤200 правил, ≤1k получателей (расширяемые при необходимости)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Конституция v1.0.0 активна (principles I–V, workflow/gates). Для фичи обязательны: тесты для новой логики (backend/frontend/worker), обновление документации/структуры при изменениях, секреты только через шаблоны, соблюдение каталогов. Нарушений на момент планирования нет; контролируем соблюдение гейтов при выполнении фаз.

## Project Structure

### Documentation (this feature)

```text
specs/001-alert-notification-methods/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md (создаётся /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   ├── models/
│   ├── services/
│   └── lib/
└── tests/

frontend/
├── src/
└── tests/

scripts/
config/
docs/
specs/
```

**Structure Decision**: Используем существующую двусоставную структуру (backend + frontend). Логика оповещений и API — в `backend/src` (models/services/api), UI настройки каналов/правил — в `frontend/src`.

## Complexity Tracking

Нет зафиксированных нарушений или оправданий сложности на данном этапе.
