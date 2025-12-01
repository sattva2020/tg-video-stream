# Tasks: Интеграция компонентов из GitHub-проектов

**Input**: Design documents from `/specs/016-github-integrations/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies

- [ ] T001 Add sqladmin, prometheus_client to backend/requirements.txt
- [ ] T002 [P] Add AUTO_END_TIMEOUT_MINUTES, PLACEHOLDER_AUDIO_PATH to template.env
- [ ] T003 [P] Create backend/src/admin/ directory structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

⚠️ **CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create QueueItem Pydantic model in backend/src/models/queue.py
- [ ] T005 [P] Create StreamState model in backend/src/models/stream_state.py
- [ ] T006 Create QueueService with Redis persistence in backend/src/services/queue_service.py
- [ ] T007 [P] Extend existing metrics_service.py with Prometheus registry in backend/src/services/metrics_service.py

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 — Система очередей треков (Priority: P1) 🎯 MVP

**Goal**: Администратор может добавлять треки в очередь, и они автоматически переключаются

**Independent Test**: Добавить 5 треков, запустить воспроизведение, убедиться что треки переключаются автоматически

### Implementation for User Story 1

- [ ] T008 [US1] Implement add/remove/move operations in backend/src/services/queue_service.py
- [ ] T009 [US1] Create Queue API router in backend/src/api/queue.py
- [ ] T010 [P] [US1] Add GET /api/v1/queue/{channel_id} endpoint in backend/src/api/queue.py
- [ ] T011 [P] [US1] Add POST /api/v1/queue/{channel_id}/items endpoint in backend/src/api/queue.py
- [ ] T012 [US1] Add DELETE, PUT position endpoints in backend/src/api/queue.py
- [ ] T013 [US1] Add POST /api/v1/queue/{channel_id}/skip endpoint in backend/src/api/queue.py
- [ ] T014 [US1] Register queue router in backend/src/main.py
- [ ] T015 [US1] Extend existing StreamQueue class with Redis sync in streamer/queue_manager.py
- [ ] T016 [US1] Implement on_track_end handler in streamer/queue_manager.py
- [ ] T017 [US1] Create placeholder.py with loop playback in streamer/placeholder.py
- [ ] T018 [US1] Integrate QueueManager into streamer/main.py
- [ ] T019 [US1] Extend ConnectionManager with queue_update event in backend/src/api/websocket.py

**Checkpoint**: User Story 1 — очередь работает и автоматически переключает треки

---

## Phase 4: User Story 2 — Автоматическое завершение пустого стрима (Priority: P1)

**Goal**: Система автоматически завершает стрим при отсутствии слушателей N минут

**Independent Test**: Запустить стрим без слушателей, дождаться таймаута, стрим остановился

### Implementation for User Story 2

- [ ] T020 [US2] Create AutoEndService in backend/src/services/auto_end_service.py
- [ ] T021 [US2] Implement start_timer/cancel_timer with Redis TTL in backend/src/services/auto_end_service.py
- [ ] T022 [US2] Create auto_end.py with PyTgCalls integration in streamer/auto_end.py
- [ ] T023 [US2] Add on_participants_change handler in streamer/auto_end.py
- [ ] T024 [US2] Integrate AutoEndService into streamer/main.py
- [ ] T025 [US2] Add auto_end_warning WebSocket event in backend/src/api/websocket.py
- [ ] T026 [US2] Log stream end reason (auto-end/manual/error) in backend/src/services/auto_end_service.py

**Checkpoint**: User Story 2 — auto-end работает корректно

---

## Phase 5: User Story 3 — Административная панель (Priority: P2)

**Goal**: Администратор управляет пользователями и контентом через веб-интерфейс /admin

**Independent Test**: Войти в /admin, изменить роль пользователя, изменения применились

### Implementation for User Story 3

- [ ] T027 [US3] Create AdminAuth backend in backend/src/admin/auth.py
- [ ] T028 [US3] Setup sqladmin Admin instance in backend/src/admin/__init__.py
- [ ] T029 [US3] Create UserAdmin view in backend/src/admin/views.py
- [ ] T030 [P] [US3] Create PlaylistAdmin view in backend/src/admin/views.py
- [ ] T031 [P] [US3] Create StreamAdmin view in backend/src/admin/views.py
- [ ] T032 [US3] Mount admin to FastAPI app in backend/src/main.py
- [ ] T033 [US3] Create AdminAuditLog SQLAlchemy model in backend/src/models/audit_log.py
- [ ] T034 [US3] Create Alembic migration for audit_log table
- [ ] T035 [US3] Implement audit logging middleware in backend/src/admin/auth.py

**Checkpoint**: User Story 3 — админ-панель работает с аудитом

---

## Phase 6: User Story 4 — Prometheus мониторинг (Priority: P2)

**Goal**: DevOps получает метрики в формате Prometheus на /metrics

**Independent Test**: curl /metrics возвращает OpenMetrics, Prometheus scrapes успешно

### Implementation for User Story 4

- [ ] T036 [US4] Create /metrics endpoint in backend/src/api/metrics.py
- [ ] T037 [US4] Add http_requests_total Counter in backend/src/services/prometheus_service.py
- [ ] T038 [US4] Add http_request_duration_seconds Histogram in backend/src/services/prometheus_service.py
- [ ] T039 [US4] Add active_streams, total_listeners Gauges in backend/src/services/prometheus_service.py
- [ ] T040 [US4] Create PrometheusMiddleware in backend/src/middleware/prometheus.py
- [ ] T041 [US4] Register middleware in backend/src/main.py
- [ ] T042 [US4] Add GET /api/v1/metrics/system JSON endpoint in backend/src/api/metrics.py
- [ ] T043 [US4] Implement system metrics (CPU, memory) collection in backend/src/services/prometheus_service.py

**Checkpoint**: User Story 4 — /metrics работает, Prometheus собирает данные

---

## Phase 7: User Story 5 — WebSocket мониторинг (Priority: P3)

**Goal**: Оператор видит статистику стримов в реальном времени без перезагрузки

**Independent Test**: Открыть дашборд, запустить стрим, метрики обновляются live

### Implementation for User Story 5

- [ ] T044 [US5] Extend ConnectionManager with metrics_update event in backend/src/api/websocket.py
- [ ] T045 [US5] Extend ConnectionManager with stream_status event in backend/src/api/websocket.py
- [ ] T046 [US5] Extend ConnectionManager with listeners_update event in backend/src/api/websocket.py
- [ ] T047 [US5] Implement periodic metrics broadcast (5s interval) in backend/src/api/websocket.py
- [ ] T048 [US5] Create useMonitoringWebSocket hook in frontend/src/hooks/useMonitoringWebSocket.ts
- [ ] T049 [US5] Create StreamCard component in frontend/src/components/StreamCard.tsx
- [ ] T050 [US5] Create Monitoring page in frontend/src/pages/Monitoring.tsx
- [ ] T051 [US5] Add Monitoring route to frontend router

**Checkpoint**: User Story 5 — real-time мониторинг работает

---

## Phase 8: Polish, Testing & Documentation

**Purpose**: Tests, docs, and improvements that affect multiple user stories

### Unit Tests

- [ ] T052 [P] Create backend/tests/test_queue_service.py with pytest
- [ ] T053 [P] Create backend/tests/test_auto_end_service.py with pytest
- [ ] T054 [P] Create backend/tests/test_prometheus_metrics.py with pytest
- [ ] T055 [P] Create backend/tests/api/test_admin_panel.py with pytest

### Smoke Tests

- [ ] T056 Create tests/smoke/test_queue_operations.sh
- [ ] T057 Create tests/smoke/test_auto_end.sh

### Documentation

- [ ] T058 [P] Create docs/features/queue-system.md
- [ ] T059 [P] Create docs/features/admin-panel.md  
- [ ] T060 [P] Create docs/features/monitoring.md
- [ ] T061 Run npm run docs:validate and fix issues
- [ ] T062 Run quickstart.md validation
---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Can Start After | May Integrate With |
|-------|-----------------|-------------------|
| US1 (Queue) | Phase 2 | - |
| US2 (Auto-end) | Phase 2 | - |
| US3 (Admin) | Phase 2 | - |
| US4 (Prometheus) | Phase 2 | US3 (audit logs) |
| US5 (WebSocket) | Phase 2 | US4 (metrics) |

### Parallel Opportunities per Phase

```
Phase 1: T001, T002, T003 — all parallel
Phase 2: T004 || T005, T006 || T007
Phase 3: T010 || T011
Phase 5: T030 || T031
Phase 8: T052 || T053 || T054
```

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 62 |
| Setup Phase | 3 tasks |
| Foundational Phase | 4 tasks |
| User Story Tasks | 44 tasks |
| Testing Tasks | 6 tasks |
| Documentation Tasks | 5 tasks |
| P1 (MVP) Tasks | 19 tasks |
| P2 Tasks | 17 tasks |
| P3 Tasks | 8 tasks |
| Parallel Tasks [P] | 18 tasks |

## Existing Code to Extend (NOT create new)

| File | Action | Tasks |
|------|--------|-------|
| `streamer/queue_manager.py` | EXTEND with Redis | T015, T016 |
| `backend/src/services/metrics_service.py` | EXTEND with Prometheus | T007 |
| `backend/src/api/websocket.py` | EXTEND ConnectionManager | T019, T025, T044-T047 |
