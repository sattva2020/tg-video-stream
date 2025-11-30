# Implementation Plan: Admin Dashboard

**Branch**: `009-admin-dashboard` | **Date**: 2025-11-24 | **Spec**: `specs/009-admin-dashboard/spec.md`
**Input**: Feature specification for Admin Dashboard with user management and stream controls.

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement a comprehensive Admin Dashboard that provides system overview statistics, user management capabilities (approve/reject registrations), and stream control functions (restart). The implementation separates the dashboard logic into `AdminDashboard` and `UserDashboard` components, ensuring role-based access control at the UI level. The design utilizes TailwindCSS and HeroUI components for a responsive, dual-theme compatible interface.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: TypeScript 5.4 + React 18 + Vite 5 (frontend); Python 3.11 + FastAPI (backend).
**Primary Dependencies**: TailwindCSS, HeroUI, i18next, Axios (frontend); SQLAlchemy, Pydantic (backend).
**Storage**: PostgreSQL (User table updates for status/role).
**Testing**: Playwright (UI flows for admin/user dashboards), pytest (API endpoints for admin actions).
**Target Platform**: Modern Web Browsers (Desktop & Mobile).
**Project Type**: Web application (frontend + backend).
**Performance Goals**: Dashboard load time < 1s, User list rendering < 500ms for 100 items.
**Constraints**: Dual-theme support (Light/Dark), Responsive design (mobile-first).
**Scale/Scope**: 2 new dashboard components, 1 page update, 3 API endpoints integration.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** — `specs/009-admin-dashboard/spec.md` содержит 4 независимые user stories, измеримые критерии успеха и ссылки на тесты. ✅
2. **Структура репозитория соблюдена (Принцип II)** — артефакты фичи лежат в `specs/009-admin-dashboard/`, код в `frontend/src/components/dashboard/` и `backend/src/api/`. ✅
3. **Тесты и наблюдаемость спланированы (Принцип III)** — запланированы Playwright тесты `tests/playwright/admin-dashboard.spec.ts` и pytest для API. ✅
4. **Документация и локализация покрыты (Принцип IV)** — будет создан `docs/admin-dashboard.md` и обновлен `docs/development/rbac.md`. ✅
5. **Секреты и окружения учтены (Принцип V)** — новых секретов не требуется. ✅

## Project Structure

### Documentation (this feature)

```text
specs/009-admin-dashboard/
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
backend/
├── src/
│   ├── api/
│   │   └── admin.py         # Admin API endpoints
│   └── models/
│       └── user.py          # User model (status/role)
└── tests/
    └── test_admin_api.py    # API tests

frontend/
├── src/
│   ├── components/
│   │   └── dashboard/
│   │       ├── AdminDashboard.tsx  # Admin UI
│   │       └── UserDashboard.tsx   # User UI
│   ├── pages/
│   │   └── DashboardPage.tsx       # Main container
│   └── api/
│       └── admin.ts                # API client
└── tests/
    └── playwright/
        └── admin-dashboard.spec.ts # UI tests
```

**Structure Decision**: Web application structure with separated frontend components for role-based dashboards and backend API endpoints for administration.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations.
