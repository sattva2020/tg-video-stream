# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary
[Кратко] Новые пользователи при регистрации получают статус "pending" и не могут входить в систему до утверждения администратором. Технический подход: добавить поле статуса в таблицу пользователей (enum), обновить логику аутентификации чтобы блокировать pending/rejected, добавить admin API для просмотра/утверждения/отклонения пользователей, создать миграцию Alembic и тесты (pytest + Playwright) до реализации.
[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11 (backend) / Node 20+ + React 18 + TypeScript (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, PostgreSQL (backend); Vite, React, TypeScript, Playwright (frontend)
**Storage**: PostgreSQL (users table)
**Testing**: pytest (backend unit/integration), Playwright (frontend e2e), smoke tests for streamer unaffected
**Target Platform**: Linux servers (containerized via Docker Compose) and local development environments
**Project Type**: Web application with backend API + frontend admin panel
**Performance Goals**: Keep existing goals — backend <200ms p95; this feature is low perf-impact (simple DB field and API)
**Constraints**: Must follow repo constitution: tests + docs created before/along with implementation; DB migrations via Alembic; no new secrets required for MVP
**Scale/Scope**: Feature is limited — affects user registration/authentication and admin UI only (no streaming logic)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** — спецификация на русском с независимыми user stories,
  измеримыми критериями успеха и ссылками на связанные документы.
2. **Структура репозитория соблюдена (Принцип II)** — артефакты фичи создаются только в
  `specs/[###-feature]/`, временные файлы указываются в `.internal/`, тесты планируются в
  `tests/`.
3. **Тесты и наблюдаемость спланированы (Принцип III)** — описаны конкретные pytest,
  Playwright/Vitest, smoke или мониторинговые задачи, которые будут добавлены до кода.
4. **Документация и локализация покрыты (Принцип IV)** — план фиксирует, какие файлы в `docs/`
  или `ai-instructions/` обновятся и какие команды `npm run docs:*` будут выполнены.
5. **Секреты и окружения учтены (Принцип V)** — новые переменные добавляются в `template.env`,
  процесс генерации `.env` описан, исключена утечка секретов.

**Verdict**: PASS — спецификация соответствует Конституции. Нет новых секретов, все изменения будут в `backend/`, `frontend/` и `specs/007-user-approval/`. Тесты и документация спланированы.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# [REMOVE IF UNUSED] Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# [REMOVE IF UNUSED] Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure: feature modules, UI flows, platform tests]
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

**Structure Decision**: This is a web app change. Files touched: `backend/src/models/user.py`, `backend/src/api/auth.py` (or relevant auth endpoints), Alembic migration in `backend/alembic/versions/`, backend tests added under `backend/tests/`, frontend changes in `frontend/src/pages/admin/` (new PendingUsers page + components) and `frontend/tests/e2e/rbac-approval.spec.ts`.

## Phase 1 outputs

- Research: `research.md` (completed)
- Data model: `data-model.md` (completed)
- Contracts: `contracts/user-approval-openapi.yaml` (completed)
- Quickstart / test-run: `quickstart.md` (completed)

## Constitution re-check

All constitution gates remain satisfied: specification is the single source of truth, tests and documentation are planned and will be created before code changes, and no new secrets are required.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
