# Implementation Plan: Email & Password Authentication

**Branch**: `004-email-password-auth` | **Date**: 2025-11-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-email-password-auth/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This plan outlines the technical approach for adding traditional email and password authentication to the existing application. The system currently relies on Google OAuth, and this feature will broaden accessibility. The technical approach involves extending the backend with new endpoints for registration, login, and password recovery. This will be achieved by adding `passlib` for password hashing and `fastapi-mail` for sending recovery emails, while leveraging the existing `itsdangerous` library for secure token generation. The frontend will be updated with new forms and state management to support the new authentication flow.

## Technical Context

**Language/Version**: Python 3.x, TypeScript
**Primary Dependencies**: FastAPI, React, SQLAlchemy
**Storage**: PostgreSQL (production), SQLite (testing)
**Testing**: pytest, ruff
**Target Platform**: Web Application (Linux server)
**Project Type**: Web application
**Performance Goals**: <500ms p95 response time for authentication endpoints.
**Constraints**: Must integrate with the existing Google OAuth system without breaking it.
**Scale/Scope**: Expected to support up to 10,000 users.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution file (`.specify/memory/constitution.md`) is a template and does not contain specific principles to check against. Proceeding with standard best practices.

## Project Structure

### Documentation (this feature)

```text
specs/004-email-password-auth/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/
│   └── openapi.yml      # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
```text
backend/
├── src/
│   ├── models/      # Add `hashed_password` to user.py
│   ├── services/    # Add email service
│   └── api/         # Add new auth endpoints
└── tests/

frontend/
├── src/
│   ├── components/  # Add new auth forms
│   ├── pages/       # Add new pages for login, register, reset password
│   └── services/    # Add API calls for new endpoints
└── tests/
```

**Structure Decision**: The project already follows a standard web application structure with separate `frontend` and `backend` directories. This feature will extend the existing structure by adding new modules, services, and components within these directories as detailed above.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A       | N/A        | N/A                                 |