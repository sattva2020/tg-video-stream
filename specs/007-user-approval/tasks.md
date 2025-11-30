# Tasks: User Approval (Feature 007)

Feature: любой новый пользователь требует утверждения администратора перед тем как войти.

Phases: Phase 1 — Setup, Phase 2 — Foundational (DB + API), Phase 3 — User stories (P1/P2/P3), Final — Polish & docs

---

## Phase 1 — Setup

- [ ] T001 [P] Create backend tests scaffold for user approval in `backend/tests/test_user_approval.py`
- [ ] T002 [P] Create frontend e2e test scaffold in `frontend/tests/e2e/approval.spec.ts`
- [ ] T003 [P] Add placeholder Alembic migration file `backend/alembic/versions/xxxx_add_user_status.py` (template for implementers)
- [ ] T004 [P] Create test helper / seed script for a test admin `backend/scripts/create_test_admin.py`

---

## Phase 2 — Foundational (blocking prerequisites)

- [ ] T005 Update `backend/src/models/user.py` — add `status` field (enum: 'pending','approved','rejected') and update SQLAlchemy model docs
- [ ] T006 Add Alembic migration `backend/alembic/versions/<timestamp>_add_user_status.py` that:
    - adds `status` column
    - marks existing users as `approved`
    - sets default for new rows to `pending` or ensures application-level default
- [ ] T007 Add/extend backend unit tests in `backend/tests/test_user_approval.py` verifying migration behaviour and model default
- [ ] T008 Ensure CI runs the new backend tests (update `backend/pytest.ini` or CI workflow if required)

---

## Phase 3 — User Stories (priority order)

### User Story 1 — Регистрация и ожидание утверждения (P1)

- [ ] T009 [US1] Write backend test: `backend/tests/test_user_approval.py::test_register_sets_pending` (register -> status == 'pending')
- [ ] T010 [US1] Implement: update register endpoint in `backend/src/api/auth.py` to create new users with `status='pending'`
- [ ] T011 [US1] Update frontend registration flow to show message "Ваш аккаунт ожидает подтверждения администратора" on successful signup: `frontend/src/pages/Auth/RegisterForm.tsx` (or relevant component)
- [ ] T012 [US1] Add Playwright e2e test: `frontend/tests/e2e/approval.spec.ts::signup_shows_pending_message`

### User Story 2 — Утверждение пользователя администратором (P1)

- [ ] T013 [US2] Write backend tests for admin endpoints in `backend/tests/test_admin_user_approval.py` (list pending users, approve endpoint behaviour)
- [ ] T014 [US2] Implement admin endpoints: `backend/src/api/admin/users.py` —
    - `GET /admin/users?status=pending`
    - `POST /admin/users/{user_id}/approve`
- [ ] T015 [US2] After approval, ensure login works: add test `backend/tests/test_user_approval.py::test_approved_user_can_login`
- [ ] T016 [US2] Implement frontend admin page `frontend/src/pages/admin/PendingUsers.tsx` and supporting components (e.g., `frontend/src/components/PendingUserRow.tsx`) with Approve button
- [ ] T017 [US2] Add Playwright e2e test: `frontend/tests/e2e/approval.spec.ts::admin_can_approve_user_and_user_can_login`

### User Story 3 — Отклонение пользователя администратором (P2)

- [ ] T018 [US3] Write backend tests for reject endpoint `backend/tests/test_admin_user_approval.py::test_reject_user_blocks_login`
- [ ] T019 [US3] Implement admin reject endpoint `backend/src/api/admin/users.py::POST /{user_id}/reject` and/or deletion behaviour
- [ ] T020 [US3] Update frontend admin UI to support Reject and confirmation dialog `frontend/src/pages/admin/PendingUsers.tsx`
- [ ] T021 [US3] Add Playwright e2e test: `frontend/tests/e2e/approval.spec.ts::admin_can_reject_user_and_user_cannot_login`

---

## Final Phase — Polish & Cross-cutting concerns

- [ ] T022 [P] Add documentation: `docs/development/user-approval.md` describing behavior, migration notes, and admin instructions
- [ ] T023 [P] Add `specs/007-user-approval/tasks.md` finalised (this file) and update `specs/007-user-approval/quickstart.md` with exact test run commands
- [ ] T024 [P] Add Playwright CI config entries (if required) and ensure tests run in CI (`.github/workflows/ci.yml`)
- [ ] T025 [P] Add DB seed for CI/Dev to create an initial admin user for testing: `backend/scripts/create_test_admin.py` (if not already created) and include instructions in quickstart

- [ ] T026 [P] Decide and install background worker (async queue) — add Celery (or RQ) dependency, worker entrypoint and CI dev task. Document choice in `specs/007-user-approval/plan.md`.
- [ ] T027 [P] Implement backend notification enqueueing on new registration (register -> push notification job to queue). Ensure job payload contains user id/email and metadata.
- [ ] T028 [P] Implement background worker tasks to send Email notifications via SMTP (config in `template.env`: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ADMIN_NOTIFICATION_EMAILS`) and retries.
- [ ] T029 [P] Implement background worker tasks to send Telegram notifications (config `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_IDS`) and retries.
- [ ] T030 [P] Add tests verifying notification jobs are enqueued and worker tasks run (backend unit tests + integration tests using test broker in CI). Update `specs/007-user-approval/quickstart.md` with worker setup instructions.

---

## Dependencies & ordering

- Phase 2 tasks T005/T006/T007 are blocking — must be done before login/register enforcement (T010/T011/T014).
- Tests are written before implementation wherever possible (T009, T013, T018 before their respective implementations).
- Frontend UI tasks can be worked in parallel with backend implementation once contracts are stable (marked [P]).

## Parallel execution examples

- Backend model + migration (T005/T006) / Frontend types (T011) can be worked in parallel after contract confirmation.
- Admin page UI (T016/T020) can be implemented in parallel with backend admin endpoints (T014/T019) if stubbed responses are used during dev.

## Implementation strategy (MVP first)

1. Tests + DB migration + model change (T001-T008)
2. Implement register + block login for pending (T009-T012)
3. Implement admin endpoints + tests (T013-T015)
4. Implement admin UI + e2e (T016-T021)
5. Polish docs + CI + seeds (T022-T025)
