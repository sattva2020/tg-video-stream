# Tasks: Complete Admin Ops

**Feature**: Complete Admin Ops
**Status**: Pending
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

## Phase 1: Setup (Project Initialization)

**Goal**: Prepare environment, dependencies, and configuration for the new features.

- [x] T001 Update `backend/requirements.txt` to include `docker` SDK
- [x] T002 Update `streamer/requirements.txt` to include `redis` and `psutil`
- [x] T003 Update `backend/src/core/config.py` to include `STREAM_CONTROLLER_TYPE`, `STREAM_CONTAINER_NAME`, `STREAM_SERVICE_NAME`
- [x] T004 Update `docker-compose.yml` to mount shared volume `/app/data` and docker socket `/var/run/docker.sock`

## Phase 2: Foundational (Blocking Prerequisites)

**Goal**: Implement core logic for stream control abstraction and metrics collection that User Stories depend on.

- [x] T005 Create `backend/src/services/stream_controller.py` implementing Strategy Pattern (Docker vs Systemd)
- [x] T006 Create `streamer/metrics.py` to collect CPU/RAM via `psutil` and push to Redis

## Phase 3: User Story 1 - Control & Monitor (Priority: P1)

**Goal**: Enable admin to restart stream, view logs, and monitor metrics via UI.
**Independent Test**: Verify API endpoints return status/logs and UI updates.

- [x] T007-PRE Create `backend/tests/api/test_admin.py` with skeletons for control, logs, and metrics tests
- [x] T007 [US1] Implement `POST /admin/stream/control` endpoint in `backend/src/api/admin.py` using `StreamController`
- [x] T008 [US1] Implement `GET /admin/stream/logs` endpoint in `backend/src/api/admin.py`
- [x] T009 [US1] Implement `GET /admin/stream/metrics` endpoint in `backend/src/api/admin.py` reading from Redis
- [x] T010-PRE Create `frontend/tests/admin-dashboard.spec.ts` for UI smoke tests
- [x] T010 [P] [US1] Update `frontend/src/services/admin.ts` with methods for control, logs, and metrics
- [x] T011 [P] [US1] Create `frontend/src/pages/admin/Dashboard.tsx` with Start/Stop/Restart controls
- [x] T012 [P] [US1] Create `frontend/src/pages/admin/Logs.tsx` component for real-time log viewing
- [x] T013 [P] [US1] Create `frontend/src/pages/admin/Metrics.tsx` component for CPU/RAM visualization

## Phase 4: User Story 2 - Playlist Management (Priority: P2)

**Goal**: Enable admin to manage the playlist file via UI.
**Independent Test**: Verify changes in UI are reflected in `playlist.txt` on disk.

- [x] T014-PRE Update `backend/tests/api/test_admin.py` with playlist test skeletons
- [x] T014 [US2] Create `backend/src/services/playlist_service.py` for reading/writing `playlist.txt`
- [x] T015 [US2] Implement `GET /admin/playlist` and `POST /admin/playlist` in `backend/src/api/admin.py`
- [x] T016-PRE Update `frontend/tests/admin-dashboard.spec.ts` with playlist UI tests
- [x] T016 [P] [US2] Update `frontend/src/services/admin.ts` with playlist CRUD methods
- [x] T017 [P] [US2] Create `frontend/src/pages/admin/Playlist.tsx` with list editor (add/remove/reorder)

## Phase 5: User Story 3 - Auto-Session Recovery (Priority: P2)

**Goal**: Automatically attempt to recover session on expiration.
**Independent Test**: Simulate session expiry and verify recovery script execution.

- [x] T018 [US3] Create `streamer/auto_session_runner.py` script for session recovery (Scope: Validate env vars, restart process, alert admin; NO interactive 2FA re-login)
- [x] T019 [US3] Update `streamer/main.py` to catch `SessionExpired` exception and trigger recovery

## Phase 6: User Story 4 - Extended Configuration (Priority: P3)

**Goal**: Allow FFmpeg argument injection via environment variables.
**Independent Test**: Set `FFMPEG_ARGS` and verify process arguments.

- [x] T020 [US4] Update `streamer/utils.py` to inject `FFMPEG_ARGS` env var into ffmpeg command

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Finalize documentation and ensure system stability.

- [x] T021 Update `docs/development/admin-ops.md` with usage instructions
- [x] T022 Verify all new endpoints are secured with admin authentication

## Dependencies

1. **US1 (Control)** depends on **Foundational** (StreamController, Metrics)
2. **US2 (Playlist)** is independent of US1/US3
3. **US3 (Auto-Session)** is independent
4. **US4 (Config)** is independent

## Parallel Execution Examples

- **Frontend/Backend Split**: T010-T013 (Frontend US1) can be done in parallel with T007-T009 (Backend US1).
- **Story Parallelism**: US2 (Playlist) tasks (T014-T017) can be done in parallel with US1 tasks.

## Implementation Strategy

1. **MVP (US1)**: Focus first on getting the stream control and monitoring working, as this is the highest priority for operations.
2. **Content (US2)**: Add playlist management to allow content updates.
3. **Reliability (US3)**: Add auto-recovery.
4. **Flexibility (US4)**: Add advanced config last.
