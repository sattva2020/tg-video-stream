# Implementation Plan: Advanced Audio & Playlist UI

**Branch**: `011-advanced-audio` | **Date**: 2024-05-23 | **Spec**: [specs/011-advanced-audio/spec.md](../spec.md)
**Input**: Feature specification from `/specs/011-advanced-audio/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement advanced audio features including on-the-fly transcoding for unsupported formats (FLAC, OGG) using FFmpeg and PyTgCalls. Develop a full-stack Playlist Management UI (React Frontend + FastAPI Backend) to allow users to manage the playback queue dynamically.

## Technical Context

**Language/Version**: Python 3.12 (Backend/Streamer), Node 20+ (Frontend)
**Primary Dependencies**: 
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL
- **Streamer**: PyTgCalls, Pyrogram, FFmpeg, yt-dlp
- **Frontend**: React, Vite, TailwindCSS
**Storage**: PostgreSQL (Backend) for playlist persistence.
**Testing**: 
- Backend: `pytest`
- Frontend: `Playwright`
- Streamer: Manual/Smoke tests (due to complexity of audio verification)
**Target Platform**: Linux server (Dockerized)
**Project Type**: Web application + Background Service
**Performance Goals**: Transcoding start < 5s, UI update < 1s.
**Constraints**: Must run on 2 vCPU / 4 GB RAM.
**Scale/Scope**: Single active stream per instance.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** — ✅ Спецификация `specs/011-advanced-audio/spec.md` утверждена.
2. **Структура репозитория соблюдена (Принцип II)** — ✅ Артефакты в `specs/011-advanced-audio/`, код в `backend/`, `frontend/`, `streamer/`.
3. **Тесты и наблюдаемость спланированы (Принцип III)** — ✅ Backend: unit-тесты API. Frontend: E2E тесты UI. Streamer: smoke-тест транскодирования.
4. **Документация и локализация покрыты (Принцип IV)** — ✅ Обновление `docs/` и `ai-instructions/`.
5. **Секреты и окружения учтены (Принцип V)** — ✅ Новые переменные (если будут) через `template.env`.

## Project Structure

### Documentation (this feature)

```text
specs/011-advanced-audio/
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
│   ├── models/          # New Playlist model
│   ├── api/             # New Playlist endpoints
│   └── services/        # Playlist logic
└── tests/

frontend/
├── src/
│   ├── components/      # Playlist UI components
│   ├── pages/           # Playlist management page
│   └── services/        # API client updates
└── tests/

streamer/
├── audio_utils.py       # Transcoding logic
├── main.py              # Integration with transcoding
└── requirements.txt     # FFmpeg dependencies
```

**Structure Decision**: Standard 3-tier architecture (Frontend -> Backend -> DB) with an autonomous Streamer worker polling the Backend.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | | |
