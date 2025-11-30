# Implementation Plan: User Roles (RBAC)

**Branch**: `006-user-roles-rbac` | **Date**: 2025-11-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-user-roles-rbac/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement Role-Based Access Control (RBAC) with two roles: `user` and `admin`.

- **Backend**: Add `role` column to `users` table, include role in JWT, protect admin endpoints.
- **Frontend**: Store role in auth state, protect routes, hide admin UI elements.
- **Migration**: Update existing users to `user` role.

## Technical Context

**Language/Version**: Python 3.11+ (Backend), Node 20+ (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy, Alembic, React, Vite
**Storage**: PostgreSQL
**Testing**: pytest (Backend), Playwright (Frontend)
**Target Platform**: Linux server (Docker)
**Project Type**: Web application
**Performance Goals**: <200ms overhead for auth checks
**Constraints**: Secure default (user role), explicit promotion for admin
**Scale/Scope**: Foundation for future permission levels

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** — ✅ Спецификация на русском, user stories независимы.
2. **Структура репозитория соблюдена (Принцип II)** — ✅ Артефакты в `specs/006-user-roles-rbac/`.
3. **Тесты и наблюдаемость спланированы (Принцип III)** — ✅ Pytest для auth service, Playwright для UI checks.
4. **Документация и локализация покрыты (Принцип IV)** — ✅ Обновление `docs/development/frontend-auth-implementation.md`.
5. **Секреты и окружения учтены (Принцип V)** — ✅ Секреты не требуются.

## Project Structure

### Documentation (this feature)

```text
specs/006-user-roles-rbac/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/user.py       # Update User model
│   ├── services/auth.py     # Update token generation
│   ├── api/deps.py          # Add get_current_admin
│   └── migrations/          # New Alembic migration
└── tests/
    └── test_auth_rbac.py    # New tests

frontend/
├── src/
│   ├── types/user.ts        # Update User interface
│   ├── context/AuthContext.tsx # Update auth state
│   └── components/ProtectedRoute.tsx # Update/Create wrapper
└── tests/
    └── e2e/rbac.spec.ts     # New e2e tests

scripts/
└── create_admin.py          # Admin promotion script
```

**Structure Decision**: Standard backend/frontend split.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | - | - |
