---
description: "Generated task list for 002-prod-broadcast-improvements"
---

# Tasks: Production Broadcast Improvements

### Functional Requirements

- **FR-001**: Приложение MUST перехватывать `pyrogram.errors.SessionExpired` и логировать понятное сообщение с рекомендацией действий.
- **FR-002**: При настроенном режиме автоперегенерации приложение MUST инициировать безопасный поток генерации новой сессии через `test/auto_session_runner.py --write-env`; при успехе обновить `.env` и exit(0), при ошибке логировать и exit(1).
- **FR-003**: systemd unit MUST содержать `Restart=always`, `RestartSec=10`, `StartLimitInterval=0` для автоматического восстановления.
- **FR-004**: Система MUST иметь расписание (systemd-timer) для еженедельного обновления `yt-dlp` (Sunday 02:00 UTC) и логировать в `/var/log/yt-dlp-update.log`.
- **FR-005**: Приложение MUST поддерживать `FFMPEG_ARGS` из `.env` (space-separated, double-quote escaping; fallback if invalid) и передавать их ffmpeg-процессу.
- **FR-006**: Deploy pipeline MUST устанавливать права `.env` как `600` и владельца — `tgstream` (атомарно).
- **FR-007**: systemd unit MUST include `ProtectSystem=full`, `NoNewPrivileges=yes`, `PrivateTmp=true`.
- **FR-008**: Приложение MUST expose Prometheus metrics on port 9090 (configurable, fallback if occupied), type=Counter, `streams_played_total`.
- **FR-009**: CI pipeline MUST restart systemd unit после deploy с 60s timeout, validate Active state, fail если неактивен.
- **FR-010** *(NEW)*: MUST вывести приложение в degraded mode если SESSION_STRING невалиден. Degraded: no streaming, log WARN "Degraded mode; run: python test/auto_session_runner.py --write-env", periodic regen attempts каждые 60s.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure required to safely implement user stories.

- [ ] T001 Create `specs/002-prod-broadcast-improvements/plan.md` from the spec and implementation notes (path: `specs/002-prod-broadcast-improvements/plan.md`).
- [ ] T002 [P] Add `.env.template` at repository root with placeholders for `API_ID`, `API_HASH`, `SESSION_STRING`, `CHAT_ID`, `FFMPEG_ARGS`, `PROMETHEUS_PORT` (path: `.env.template`).
- [ ] T003 [P] Ensure diagnostic & session helpers are present and documented: verify `test/diag_session.py`, `test/auto_session_runner.py`, `generate_session_and_list_dialogs.py`, `generate_session_telethon.py` and add README snippet in `specs/002-prod-broadcast-improvements/quickstart.md` describing how to run them (path: `specs/002-prod-broadcast-improvements/quickstart.md`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infra that MUST be completed before implementing user stories.

- [ ] T004 [P] Update `scripts/remote_deploy.sh` to enforce `.env` ownership and permissions after deploy: `chown tgstream:tgstream {{deploy_path}}/.env` and `chmod 600 {{deploy_path}}/.env` (path: `scripts/remote_deploy.sh`).
- [ ] T005 [P] Create a systemd unit template for `tg_video_streamer.service` and add it to `specs/002-prod-broadcast-improvements/deploy/systemd/tg_video_streamer.service` (template must include `Restart=always`, `RestartSec=10`, `ProtectSystem=full`, `NoNewPrivileges=yes`, `PrivateTmp=true`, `User=tgstream`, `EnvironmentFile=/opt/tg_video_streamer/current/.env`).
- [ ] T006 [P] Add a systemd-timer + service pair for weekly `yt-dlp` updates and logging: create `specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.service` and `yt-dlp-update.timer`, and a helper script `scripts/yt-dlp-update.sh` that runs the venv pip update and writes to `/var/log/yt-dlp-update.log` (paths: `specs/002-prod-broadcast-improvements/deploy/systemd/`, `scripts/yt-dlp-update.sh`).
- [ ] T007 [P] Add CI snippet file with restart step template at `.github/workflows/snippets/restart-tg_video_streamer-step.yml` (path: `.github/workflows/snippets/restart-tg_video_streamer-step.yml`).
- [ ] T008 [P] Add `prometheus_client` to `requirements.txt` and document port default in `.env.template` (path: `requirements.txt`, `.env.template`).

---

## Phase 3: User Story 1 - Надёжное восстановление сессии (Priority: P1) 🎯 MVP

**Goal**: При истёкшей/битой `SESSION_STRING` приложение корректно информирует оператора, не падает аварийно, и при включённом режиме автоперегенерации запускает безопасный локальный helper.

**Independent Test**: Симулировать `SessionExpired` или передать испорченный `SESSION_STRING` и проверить логи и поведение (degraded loop, exit code or regen attempt).

- [ ] T009 [US1] Add explicit `pyrogram.errors.SessionExpired`/`AuthKeyError` handling in `main.py` startup sequence and log a clear recovery message with recommended operator actions (path: `main.py`).
- [ ] T010 [P] [US1] Enhance `test/auto_session_runner.py` to support an optional `--write-env` flag that safely updates local `.env` with a newly generated `SESSION_STRING` (atomic write: temp → mv, with backup) and returns exit codes 0 (success) / 1 (failure); ensure concurrent access safety via file locking or atomic operations (path: `test/auto_session_runner.py`).
- [ ] T011 [P] [US1] Add an automated integration test `test/test_session_expiry.py` that asserts `main.py` enters degraded mode when `SESSION_STRING` is invalid and logs recovery suggestion (path: `test/test_session_expiry.py`).
- [ ] T012 [US1] [P] Add README snippet in `specs/002-prod-broadcast-improvements/quickstart.md` documenting interactive regen steps, --write-env usage, concurrent access precautions, and how to push `.env` to remote (path: `specs/002-prod-broadcast-improvements/quickstart.md`).

---

## Phase 4: User Story 2 - Контроль цикла и автоперезапуск systemd (Priority: P1)

**Goal**: Systemd перезапускает упавший unit с разумным backoff.

**Independent Test**: Вызвать аварийное завершение и проверить, что systemd перезапустил unit в ~10s.

- [ ] T013 [US2] Deploy and test `specs/002-prod-broadcast-improvements/deploy/systemd/tg_video_streamer.service` (from T005) on a staging host and verify `Restart=always` and `RestartSec=10` behaviour (path: `specs/002-prod-broadcast-improvements/deploy/systemd/tg_video_streamer.service`).
- [ ] T014 [US2] [P] Create a smoke test script `test/smoke/test_systemd_restart.sh` that intentionally kills the process and asserts `systemctl is-active tg_video_streamer` becomes `active` after restart (path: `test/smoke/test_systemd_restart.sh`).

---

## Phase 5: User Story 3 - Автообновление зависимостей yt-dlp (Priority: P2)

**Goal**: Еженедельное автоматическое обновление `yt-dlp` с логированием результата.

**Independent Test**: Запустить systemd-timer вручную и проверить `/var/log/yt-dlp-update.log`.

- [ ] T015 [US3] Implement the updater script `scripts/yt-dlp-update.sh` that activates the per-release venv (via `/opt/tg_video_streamer/current/venv`) and runs `pip install -U yt-dlp` and appends stdout/stderr to `/var/log/yt-dlp-update.log` with exit code handling (path: `scripts/yt-dlp-update.sh`).
- [ ] T016 [US3] [P] Create `specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.service` and `yt-dlp-update.timer` (timer triggers weekly, Sunday 02:00 UTC; on failure, retry next scheduled window) and document how to enable them on the host (paths: `specs/002-prod-broadcast-improvements/deploy/systemd/yt-dlp-update.*`).

---

## Phase 6: User Story 4 - FFMPEG_ARGS из `.env` (Priority: P2)

**Goal**: Операторы могут настраивать ffmpeg через `FFMPEG_ARGS` без правки кода.

**Independent Test**: Поставить `FFMPEG_ARGS` в `.env`, запустить локальную проигрывающую ветку и проверить, что `build_ffmpeg_av_args` использует эти параметры.

- [ ] T017 [US4] Update `utils.py` implementation of `build_ffmpeg_av_args` to read optional `FFMPEG_ARGS` from environment (space-separated, double-quote escaping; validate and fallback to empty list on invalid; log WARNING if fallback used) and return parsed video/audio args (path: `utils.py`).
- [ ] T018 [US4] [P] Add `FFMPEG_ARGS` example to `.env.template` (e.g., `FFMPEG_ARGS="-b:v 1000k -c:v h264"`) and document safe default fallback + validation rules in `specs/002-prod-broadcast-improvements/quickstart.md` (paths: `.env.template`, `specs/002-prod-broadcast-improvements/quickstart.md`).

---

## Phase 7: User Story 5 - Безопасность и права (Priority: P1)

**Goal**: `.env` хранится с правами `600` и владельцем `tgstream`; service runs as unprivileged user with sandbox options.

**Independent Test**: Проверить `stat` на `.env` и содержимое systemd unit for sandboxing flags.

- [ ] T019 [US5] [P] Update `scripts/remote_deploy.sh` to chown and chmod `.env` as part of the deploy pipeline (path: `scripts/remote_deploy.sh`).
- [ ] T020 [US5] [P] Ensure the systemd unit template (`specs/.../deploy/systemd/tg_video_streamer.service`) sets `User=tgstream` and includes `ProtectSystem=full`, `NoNewPrivileges=yes`, `PrivateTmp=true` (path: `specs/002-prod-broadcast-improvements/deploy/systemd/tg_video_streamer.service`).

---

## Phase 8: User Story 6 - Prometheus metrics (Priority: P2)

**Goal**: Экспортировать `streams_played_total` и базовые метрики на `/metrics` (порт по умолчанию 9090).

**Independent Test**: Сделать HTTP GET `:9090/metrics` и убедиться, что `streams_played_total` присутствует.

- [ ] T021 [US6] Implement basic Prometheus exporter in `main.py` (use `prometheus_client`, start exporter on configurable port; if port occupied, attempt next free port + log WARNING, or fallback to file-based metrics; increment `streams_played_total` Counter as tracks start) (path: `main.py`).
- [ ] T022 [US6] [P] Add `prometheus_client` to `requirements.txt` and document `PROMETHEUS_PORT` in `.env.template` (default 9090) with fallback strategy (paths: `requirements.txt`, `.env.template`).
- [ ] T027 [FR-008] Ensure FR-008 (Prometheus metrics type=Counter, port fallback, streams_played_total) is fully implemented via T021-T022, with validation that metrics are scrapeable on `/metrics` and counter increments correctly when tracks play (path: `main.py`, test validation).

---

## Phase 9: User Story 7 - CI/CD restart step (Priority: P2)

**Goal**: CI restarts `tg_video_streamer` after successful deploy and verifies `Active=active`.

**Independent Test**: Run CI job (or local run of the ssh step) and assert `systemctl is-active tg_video_streamer` returns `active`.

- [ ] T023 [US7] Create `.github/workflows/deploy-restart.yml` example workflow that SSHes to the host and runs `sudo systemctl restart tg_video_streamer` with 60s timeout and validates `systemctl is-active` returns `active` (path: `.github/workflows/deploy-restart.yml`).
- [ ] T024 [US7] [P] Add CI verification step script `ci/check_service_active.sh` that returns 0 if `systemctl is-active tg_video_streamer` = `active` within 60s, else return 1 and log failure reason (path: `ci/check_service_active.sh`).

---

## Final Phase: Polish & Cross-Cutting Concerns

- [ ] T025 [P] Update documentation in `specs/002-prod-broadcast-improvements/README.md` summarizing deploy steps, regen steps, and monitoring configuration (path: `specs/002-prod-broadcast-improvements/README.md`).
- [ ] T026 [P] Run quick validation: execute `python -m pytest test/test_session_expiry.py` and `python test/diag_session.py` and report PASS/FAIL (path: repo root commands).
- [ ] T028 [P] [US8] Add degraded mode state machine to `main.py`: on SessionExpired, enter degraded mode, log WARN "Degraded mode; SESSION_STRING invalid; run: python test/auto_session_runner.py --write-env", and spawn background thread for periodic regen attempts every 60s with exponential backoff (max 3 retries per cycle) (path: `main.py`).
- [ ] T029 [P] [US8] Add integration test `test/test_degraded_mode.py` that asserts degraded mode entry, logging, and regen attempt cycle behavior (path: `test/test_degraded_mode.py`).
- [ ] T030 [US8] Document degraded mode operator workflow in `specs/002-prod-broadcast-improvements/quickstart.md` (path: `specs/002-prod-broadcast-improvements/quickstart.md`).

---

## Dependencies & Execution Order

- Phase 1 (T001-T003) must complete before Phase 2.
- Phase 2 (T004-T008) must complete before Phase 3 (user stories) begin.
- User stories phases (T009-T030) are independent after foundational phase; many tasks marked [P] can run in parallel.

## Summary

- Total tasks: 30 (was 26, added T028-T030 for degraded mode)
- Tasks per user story:
  - US1 (Session recovery): 4 tasks (T009-T012)
  - US2 (systemd restart): 2 tasks (T013-T014)
  - US3 (yt-dlp updates): 2 tasks (T015-T016)
  - US4 (FFMPEG_ARGS): 2 tasks (T017-T018)
  - US5 (Security): 2 tasks (T019-T020)
  - US6 (Prometheus): 3 tasks (T021-T022, T027)
  - US7 (CI restart): 2 tasks (T023-T024)
  - US8 (Degraded mode): 3 tasks (T028-T030) *(NEW)*
  - Setup/Foundation/Polish: 8 tasks (T001-T008, T025-T026)

- Parallel opportunities: many tasks marked [P] (environment templating, CI snippets, updater scripts, requirements update, docs) can be executed in parallel by separate contributors.

- Suggested MVP: Complete Phase 1 + Phase 2 + Phase 3 (User Story 1). That yields a minimal working recovery flow and keeps service resilient.

---

Format validation: All tasks follow the required checklist format `- [ ] T### [P?] [US?] Description with file path`.

Generated by automation on: 2025-11-08
