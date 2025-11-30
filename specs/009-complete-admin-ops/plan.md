# Implementation Plan: Complete Admin Ops

**Branch**: `009-complete-admin-ops` | **Date**: 2024-05-22 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-complete-admin-ops/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement comprehensive admin operations including stream restart (Docker/Systemd abstraction), log viewing, metrics monitoring (via Redis), playlist management (shared volume), and configuration enhancements (FFmpeg args, auto-session recovery). This ensures the system is manageable via UI without direct server access.

## Technical Context

**Language/Version**: Python 3.12+ (Backend/Streamer), Node 20+ (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy, Pyrogram, PyTgCalls, React, Vite, TailwindCSS
**Storage**: PostgreSQL (Backend), Redis (Metrics/Status), File System (Playlist)
**Testing**: pytest (Backend), Playwright (Frontend)
**Target Platform**: Linux server (Systemd/Docker)
**Project Type**: Web application + Headless Streamer
**Performance Goals**: Stream stability, UI responsiveness (<200ms API)
**Constraints**: Headless server, systemd management, Docker isolation
**Scale/Scope**: Single server, admin panel for management

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** — спецификация на русском с независимыми user stories,
  измеримыми критериями успеха и ссылками на связанные документы. ✅
2. **Структура репозитория соблюдена (Принцип II)** — артефакты фичи создаются только в
  `specs/009-complete-admin-ops/`, временные файлы указываются в `.internal/`, тесты планируются в
  `tests/`. ✅
3. **Тесты и наблюдаемость спланированы (Принцип III)** — описаны конкретные pytest,
  Playwright/Vitest, smoke или мониторинговые задачи, которые будут добавлены до кода. ✅
4. **Документация и локализация покрыты (Принцип IV)** — план фиксирует, какие файлы в `docs/`
  или `ai-instructions/` обновятся и какие команды `npm run docs:*` будут выполнены. ✅
5. **Секреты и окружения учтены (Принцип V)** — новые переменные добавляются в `template.env`,
  процесс генерации `.env` описан, исключена утечка секретов. ✅

## Project Structure

### Documentation (this feature)

```text
specs/009-complete-admin-ops/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   │   └── admin.py     # New endpoints
│   ├── services/
│   │   ├── stream_controller.py # New service (Docker/Systemd abstraction)
│   │   └── playlist_service.py  # New service
│   └── core/
│       └── config.py    # Env vars update
└── tests/
    └── api/
        └── test_admin.py

frontend/
├── src/
│   ├── pages/
│   │   └── admin/
│   │       ├── Dashboard.tsx    # Update
│   │       ├── Logs.tsx         # New
│   │       ├── Metrics.tsx      # New
│   │       └── Playlist.tsx     # New
│   └── services/
│       └── admin.ts
└── tests/

streamer/
├── main.py              # Update (Session recovery hook)
├── utils.py             # Update (FFmpeg args)
├── metrics.py           # New (Redis pusher)
└── auto_session_runner.py # New script
```

**Structure Decision**: Standard Backend/Frontend split with shared data volume for playlist.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | - | - |
