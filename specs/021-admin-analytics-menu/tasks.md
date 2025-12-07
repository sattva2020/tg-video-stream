# Tasks: Admin Analytics Menu

**Input**: Design documents from `/specs/021-admin-analytics-menu/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/openapi.yaml ✅

**Tests**: Not explicitly requested in specification — test tasks NOT included.

**Organization**: Tasks grouped by user story for independent implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths: `backend/src/`, `frontend/src/` (web app structure)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies

- [X] T001 Install Recharts dependency in frontend/package.json
- [X] T002 [P] Create analytics types file in frontend/src/types/analytics.ts
- [X] T003 [P] Create Pydantic schemas file in backend/src/schemas/analytics.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database and core infrastructure — MUST complete before user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create SQLAlchemy models (TrackPlay, MonthlyAnalytics) in backend/src/models/analytics.py
- [X] T005 Generate Alembic migration for track_plays and monthly_analytics tables
- [ ] T006 Apply migration to development database (server-side)
- [X] T007 [P] Create analytics service with caching in backend/src/services/analytics_service.py
- [X] T008 [P] Add canViewAnalytics to RolePermissions in frontend/src/types/permissions.ts
- [X] T009 [P] Update ROLE_PERMISSIONS const with canViewAnalytics for SUPERADMIN/ADMIN/MODERATOR in frontend/src/types/permissions.ts

**Checkpoint**: Database ready, permissions defined — user story implementation can begin

---

## Phase 3: User Story 1 - Просмотр аналитики администратором (Priority: P1) 🎯 MVP

**Goal**: ADMIN/SUPERADMIN видит пункт "Аналитика" в меню и дашборд с метриками слушателей

**Independent Test**: Авторизоваться как ADMIN, открыть меню, увидеть "Аналитика", перейти и увидеть дашборд

### API Layer (US1)

- [X] T010 [US1] Create analytics router with RBAC in backend/src/api/analytics.py
- [X] T011 [US1] Implement GET /api/analytics/summary endpoint in backend/src/api/analytics.py
- [X] T012 [US1] Implement GET /api/analytics/listeners endpoint in backend/src/api/analytics.py
- [X] T013 [US1] Implement GET /api/analytics/listeners/history endpoint in backend/src/api/analytics.py
- [X] T014 [US1] Implement GET /api/analytics/top-tracks endpoint in backend/src/api/analytics.py
- [X] T015 [US1] Register analytics router in backend/src/main.py

### Frontend API Client (US1)

- [X] T016 [US1] Create analytics API client in frontend/src/api/analytics.ts

### Frontend Components (US1)

- [X] T017 [P] [US1] Create MetricCard component in frontend/src/components/analytics/MetricCard.tsx
- [X] T018 [P] [US1] Create ListenersChart component in frontend/src/components/analytics/ListenersChart.tsx
- [X] T019 [P] [US1] Create TopTracksTable component in frontend/src/components/analytics/TopTracksTable.tsx
- [X] T020 [US1] Create Analytics page in frontend/src/pages/admin/Analytics.tsx
- [X] T021 [US1] Add /admin/analytics route in frontend/src/App.tsx (or router config)

### Navigation (US1)

- [X] T022 [P] [US1] Add Analytics menu item in frontend/src/components/layout/DesktopNav.tsx
- [X] T023 [P] [US1] Add Analytics menu item in frontend/src/components/layout/MobileNav.tsx

**Checkpoint**: ADMIN/SUPERADMIN can view analytics dashboard — MVP complete ✅

---

## Phase 4: User Story 2 - Доступ модератора к аналитике (Priority: P2)

**Goal**: MODERATOR видит тот же раздел "Аналитика" в режиме только-чтение

**Independent Test**: Авторизоваться как MODERATOR, открыть "Аналитику", увидеть все те же данные

### Implementation (US2)

- [X] T024 [US2] Verify MODERATOR has analytics_view permission in backend/src/lib/rbac.py
- [X] T025 [US2] Verify Analytics menu item has moderatorAllowed: true in navigation

**Checkpoint**: MODERATOR can view analytics — same data as ADMIN ✅

---

## Phase 5: User Story 3 - Ограничение доступа для OPERATOR/USER (Priority: P1)

**Goal**: OPERATOR и USER не видят "Аналитику" в меню, API возвращает 403

**Independent Test**: Авторизоваться как OPERATOR/USER, убедиться что пункт скрыт и API возвращает 403

### Implementation (US3)

- [X] T026 [US3] Verify adminOnly: true on Analytics nav item (hides from USER/OPERATOR)
- [X] T027 [US3] Verify require_role excludes OPERATOR/USER in backend/src/api/analytics.py
- [X] T028 [US3] Add route protection (redirect) for /admin/analytics for unauthorized users

**Checkpoint**: OPERATOR/USER cannot access analytics — security verified ✅

---

## Phase 6: Streamer Integration

**Purpose**: Connect data source for analytics

- [ ] T029 Create internal endpoint POST /api/internal/track-play in backend/src/api/analytics.py
- [ ] T030 Implement X-Internal-Token authentication for internal endpoint
- [ ] T031 Document streamer integration in quickstart.md or API docs

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements and validation

- [ ] T032 [P] Add period selector (7d/30d/90d) to Analytics page
- [ ] T033 [P] Add empty state placeholder ("Нет данных за выбранный период")
- [ ] T034 [P] Add error state with retry button
- [ ] T035 [P] Add loading skeleton for analytics cards
- [ ] T036 Add i18n translations for analytics UI (nav.analytics, analytics.*)
- [ ] T037 Run quickstart.md validation
- [ ] T038 Update feature documentation if needed

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────┐
                            ▼
Phase 2: Foundational ──────┤ BLOCKS all user stories
                            │
    ┌───────────────────────┼───────────────────────┐
    ▼                       ▼                       ▼
Phase 3: US1 (P1)    Phase 4: US2 (P2)    Phase 5: US3 (P1)
    │                       │                       │
    └───────────────────────┼───────────────────────┘
                            ▼
                   Phase 6: Streamer Integration
                            ▼
                   Phase 7: Polish
```

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1 (P1) | Foundational | — |
| US2 (P2) | Foundational, T022/T023 | US1 (mostly verification) |
| US3 (P1) | Foundational, T022/T023 | US1 (mostly verification) |

### Within Phase 3 (US1)

```
T010 → T011, T012, T013, T014 (sequential API endpoints)
T015 depends on T010-T014
T016 depends on T015
T017, T18, T019 parallel (different files)
T020 depends on T17-T19
T021 depends on T20
T022, T023 parallel
```

---

## Parallel Execution Examples

### Phase 1 (Setup)

```bash
# Can run together:
T002: frontend/src/types/analytics.ts
T003: backend/src/schemas/analytics.py
```

### Phase 2 (Foundational)

```bash
# After T004-T006 (DB):
T007: backend/src/services/analytics_service.py
T008: frontend/src/types/permissions.ts
T009: frontend/src/types/permissions.ts (same file, sequential with T008)
```

### Phase 3 (US1 Components)

```bash
# Can run together:
T017: frontend/src/components/analytics/MetricCard.tsx
T018: frontend/src/components/analytics/ListenersChart.tsx
T019: frontend/src/components/analytics/TopTracksTable.tsx
```

---

## Implementation Strategy

### MVP First (Recommended)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T009)
3. Complete Phase 3: User Story 1 (T010-T023)
4. **STOP and VALIDATE**: Test as ADMIN — should see full analytics dashboard
5. If acceptable → Deploy MVP

### Full Delivery

1. MVP (above)
2. Complete Phase 4: US2 (T024-T025) — verify MODERATOR access
3. Complete Phase 5: US3 (T026-T028) — verify OPERATOR/USER blocked
4. Complete Phase 6: Streamer Integration (T029-T031)
5. Complete Phase 7: Polish (T032-T038)

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 38 |
| **Phase 1 (Setup)** | 3 tasks |
| **Phase 2 (Foundational)** | 6 tasks |
| **Phase 3 (US1 - MVP)** | 14 tasks |
| **Phase 4 (US2)** | 2 tasks |
| **Phase 5 (US3)** | 3 tasks |
| **Phase 6 (Streamer)** | 3 tasks |
| **Phase 7 (Polish)** | 7 tasks |
| **Parallelizable** | 12 tasks marked [P] |
| **MVP Scope** | T001-T023 (23 tasks) |

---

## Notes

- All tasks follow checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
- Backend uses existing `require_role` from `backend/src/lib/rbac.py`
- Frontend uses existing `filterNavItems` from `frontend/src/utils/navigationHelpers.ts`
- Navigation pattern matches existing Monitoring menu item (`adminOnly: true, moderatorAllowed: true`)
- Recharts chosen for visualization per research.md
- Redis caching (5 min TTL) per research.md
