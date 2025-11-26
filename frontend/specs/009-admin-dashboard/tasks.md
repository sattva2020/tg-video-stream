---
description: "Task list for Admin Dashboard feature implementation"
---

# Tasks: Admin Dashboard

**Input**: Design documents from `/specs/009-admin-dashboard/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Tests are included as requested in the plan (Playwright for UI, pytest for API).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

> ⚖️ Конституция: для каждой пользовательской истории фиксируйте связанные тесты в `tests/`
> и необходимые обновления документации (`docs/`, `ai-instructions/`). Задачи по работе с
> окружением обязаны ссылаться на `template.env`, а временные файлы направлять в `.internal/`.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Ensure directory structure for dashboard components in frontend/src/components/dashboard/
- [ ] T002 [P] Verify HeroUI and Tailwind dependencies in frontend/package.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Implement backend API for fetching user stats in backend/src/api/admin.py
- [ ] T004 [P] Implement backend API for user management (list, approve, reject) in backend/src/api/admin.py
- [ ] T005 [P] Implement backend API for stream control in backend/src/api/admin.py
- [ ] T006 Create frontend API client for admin endpoints in frontend/src/api/admin.ts

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Admin Dashboard Overview (Priority: P1) 🎯 MVP

**Goal**: Provide system overview statistics for administrators.

**Independent Test**: Login as admin and verify Overview tab with stats.

### Tests for User Story 1

- [ ] T007 [P] [US1] Create Playwright test for Admin Dashboard access in frontend/tests/playwright/admin-dashboard.spec.ts

### Implementation for User Story 1

- [ ] T008 [US1] Implement AdminDashboard container layout in frontend/src/components/dashboard/AdminDashboard.tsx
- [ ] T009 [US1] Implement Overview tab with statistics cards in frontend/src/components/dashboard/AdminDashboard.tsx
- [ ] T010 [US1] Integrate Overview tab with stats API in frontend/src/components/dashboard/AdminDashboard.tsx

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - User Management (Priority: P1)

**Goal**: Allow administrators to view and manage user access.

**Independent Test**: Approve a pending user and verify status change.

### Tests for User Story 2

- [ ] T011 [P] [US2] Add Playwright test for User Management flow in frontend/tests/playwright/admin-dashboard.spec.ts

### Implementation for User Story 2

- [ ] T012 [US2] Implement Users tab with table component in frontend/src/components/dashboard/AdminDashboard.tsx
- [ ] T013 [US2] Implement Approve/Reject actions in UI in frontend/src/components/dashboard/AdminDashboard.tsx
- [ ] T014 [US2] Integrate Users tab with user management API in frontend/src/components/dashboard/AdminDashboard.tsx

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Stream Control (Priority: P1)

**Goal**: Allow administrators to restart the stream.

**Independent Test**: Click restart button and verify API call.

### Tests for User Story 3

- [ ] T015 [P] [US3] Add Playwright test for Stream Control in frontend/tests/playwright/admin-dashboard.spec.ts

### Implementation for User Story 3

- [ ] T016 [US3] Implement Stream tab with control buttons in frontend/src/components/dashboard/AdminDashboard.tsx
- [ ] T017 [US3] Integrate Stream tab with restart API in frontend/src/components/dashboard/AdminDashboard.tsx

**Checkpoint**: All admin features should now be functional

---

## Phase 6: User Story 4 - User Dashboard (Priority: P2)

**Goal**: Provide profile view for standard users.

**Independent Test**: Login as user and verify User Dashboard.

### Tests for User Story 4

- [ ] T018 [P] [US4] Add Playwright test for User Dashboard access in frontend/tests/playwright/admin-dashboard.spec.ts

### Implementation for User Story 4

- [ ] T019 [US4] Implement UserDashboard component in frontend/src/components/dashboard/UserDashboard.tsx
- [ ] T020 [US4] Update DashboardPage to route based on role in frontend/src/pages/DashboardPage.tsx

**Checkpoint**: Both Admin and User dashboards are functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T021 [P] Documentation updates in docs/admin-dashboard.md
- [ ] T022 Update RBAC documentation in docs/development/rbac.md
- [ ] T023 Verify responsive design on mobile viewports
- [ ] T024 Verify dark mode support across all components

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup
- **User Stories (Phase 3-6)**: Depend on Foundational phase
- **Polish (Phase 7)**: Depends on all user stories

### User Story Dependencies

- **US1, US2, US3**: Can be implemented in parallel after Foundational phase, as they occupy different tabs in the AdminDashboard.
- **US4**: Independent of Admin stories, can be implemented in parallel.

### Parallel Opportunities

- Backend API tasks (T003-T005) can run in parallel.
- Frontend UI implementation for different tabs (Overview, Users, Stream) can run in parallel.
- UserDashboard (US4) can be built by a separate developer.

---

## Implementation Strategy

### MVP First (Admin Core)

1. Complete Setup & Foundational
2. Implement US1 (Overview) & US2 (User Management) - Critical for operations
3. Validate Admin access and User approval flow

### Full Feature Set

1. Add US3 (Stream Control)
2. Add US4 (User Dashboard)
3. Final Polish & Documentation

