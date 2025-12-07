# Implementation Plan: Rust FFmpeg Microservice

**Branch**: `020-ffmpeg-wrapper-rust-python-api` | **Date**: 7 декабря 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/020-ffmpeg-wrapper-rust-python-api/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Вынос FFmpeg транскодирования в отдельный Rust микросервис для улучшения производительности и надёжности. Python остаётся для API, Redis-очереди и PyTgCalls интеграции. Rust-сервис обрабатывает аудио транскодирование с низкой latency, а Python-оркестратор имеет fallback на subprocess ffmpeg.

## Technical Context

**Language/Version**: Rust 1.75+ (microservice), Python 3.11 (orchestrator/API)  
**Primary Dependencies**: 
- Rust: axum/actix-web (HTTP), tokio (async), ffmpeg-next или subprocess ffmpeg
- Python: FastAPI, httpx (async client), PyTgCalls, Redis  
**Storage**: Redis (queue state), PostgreSQL (playlist metadata)  
**Testing**: cargo test (Rust), pytest (Python integration)  
**Target Platform**: Linux server (Docker), x86_64  
**Project Type**: Web application (backend + streamer + rust-service)  
**Performance Goals**: <200ms transcode start latency, 50 concurrent streams, 30% CPU reduction  
**Constraints**: <256MB memory per 10 streams, graceful fallback <3s, streaming output (no full buffering)  
**Scale/Scope**: Single VPS (4 vCPU, 8GB RAM), 1-10 concurrent channels

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution file содержит шаблон (не заполнен). Применяются общие принципы проекта:

| Principle | Status | Notes |
|-----------|--------|-------|
| Library-First | ✅ PASS | Rust-сервис — изолированная библиотека с CLI/HTTP интерфейсом |
| CLI Interface | ✅ PASS | REST API (JSON in/out), можно добавить CLI wrapper |
| Test-First | ⚠️ NEEDS ATTENTION | Требуется определить тесты до имплементации |
| Integration Testing | ✅ PASS | Contract tests между Python и Rust сервисами |
| Observability | ✅ PASS | Prometheus метрики, structured logging |
| Simplicity | ✅ PASS | MVP: subprocess ffmpeg в Rust, затем bindings |

**GATE RESULT**: ✅ PASS — можно продолжать

## Project Structure

### Documentation (this feature)

```text
specs/020-ffmpeg-wrapper-rust-python-api/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI specs)
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
# Существующая структура (сохраняется)
backend/
├── src/
│   ├── api/           # FastAPI endpoints (существует)
│   ├── models/        # SQLAlchemy models (существует)
│   └── services/      # Business logic (существует)
└── tests/

streamer/              # Python orchestrator (модифицируется)
├── main.py            # PyTgCalls + transcode client
├── transcode_client.py # NEW: HTTP client для Rust-сервиса
├── audio_utils.py     # Упрощается (логика в Rust)
└── ...

# НОВАЯ директория
rust-transcoder/       # NEW: Rust microservice
├── Cargo.toml
├── Dockerfile
├── src/
│   ├── main.rs        # Entrypoint, HTTP server
│   ├── api/           # Axum routes
│   │   ├── mod.rs
│   │   ├── transcode.rs
│   │   ├── health.rs
│   │   └── metrics.rs
│   ├── transcoder/    # Core transcoding logic
│   │   ├── mod.rs
│   │   ├── profiles.rs
│   │   ├── filters.rs
│   │   └── ffmpeg.rs
│   └── models/        # Request/Response types
│       ├── mod.rs
│       └── transcode.rs
└── tests/
    ├── integration/
    └── unit/

frontend/              # Без изменений
```

**Structure Decision**: Добавляется новая директория `rust-transcoder/` на уровне корня репозитория, рядом с `backend/`, `streamer/`, `frontend/`. Это отдельный Docker-сервис в docker-compose.yml.

## Complexity Tracking

| Добавление | Причина | Альтернатива отклонена |
|------------|---------|------------------------|
| Новый Rust проект | Performance requirements (SC-001..SC-003) | Python subprocess недостаточно для <200ms latency |
| HTTP вместо gRPC | MVP simplicity | gRPC добавляет сложность, HTTP достаточно для начала |
| Fallback механизм | 99.9% uptime requirement (SC-004) | Без fallback — single point of failure |

---

## Post-Design Constitution Check

*Re-evaluated after Phase 1 design completion.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| Library-First | ✅ PASS | `rust-transcoder/` — изолированный сервис с собственным Cargo.toml |
| CLI Interface | ✅ PASS | REST API с JSON, OpenAPI spec в `contracts/openapi.yaml` |
| Test-First | ✅ PASS | Contract tests определены в OpenAPI, unit tests в `rust-transcoder/tests/` |
| Integration Testing | ✅ PASS | Python→Rust интеграция тестируется через HTTP |
| Observability | ✅ PASS | `/health` + `/metrics` (Prometheus) endpoints |
| Simplicity | ✅ PASS | MVP: subprocess ffmpeg, не ffmpeg bindings |

**GATE RESULT**: ✅ PASS — Phase 1 завершена успешно

---

## Phase 0/1 Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| Research | [research.md](./research.md) | ✅ Complete |
| Data Model | [data-model.md](./data-model.md) | ✅ Complete |
| API Contract | [contracts/openapi.yaml](./contracts/openapi.yaml) | ✅ Complete |
| Quickstart | [quickstart.md](./quickstart.md) | ✅ Complete |
| Agent Context | `.github/agents/copilot-instructions.md` | ✅ Updated |

---

## Next Steps

Phase 2 (`/speckit.tasks`) создаст:
- `tasks.md` с конкретными задачами имплементации
- Разбивка по приоритетам (P1 → P2 → P3)
- Estimated effort и dependencies

Для запуска Phase 2:
```
/speckit.tasks
```
