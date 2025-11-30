# Tasks: User Roles (RBAC)

**Feature**: User Roles (RBAC)
**Status**: Pending
**Branch**: `006-user-roles-rbac`

## Phase 1: Setup
*Goal: Prepare the project structure for RBAC implementation.*

- [x] T001 Create `frontend/src/types` directory
- [x] T002 Create `frontend/src/types/user.ts` with `User` interface and `UserRole` enum
- [x] T003 Create `frontend/src/context` directory
- [x] T004 Create `frontend/src/context/AuthContext.tsx` to provide user state and role checking
- [x] T004a Create `backend/tests/test_auth_rbac.py` with initial failing tests for role checks (Constitution III)
- [x] T004b Create `frontend/tests/e2e/rbac.spec.ts` with initial failing tests for UI protection (Constitution III)

## Phase 2: Foundational
*Goal: Implement the core backend and frontend logic for roles. Blocking for all user stories.*

### Backend
- [x] T005 Create Alembic migration to add `role` column to `users` table in `backend/alembic/versions/`
- [x] T006 Update `User` model in `backend/src/models/user.py` to include `role` field (default='user')
- [x] T007 Update `auth_service.create_jwt_for_user` in `backend/src/services/auth_service.py` to include `role` in JWT payload
- [x] T008 Create `backend/scripts/create_admin.py` script to promote a user to admin by email

### Frontend
- [x] T009 Update `frontend/src/api/auth.ts` to use the new `User` type from `types/user.ts`
- [x] T010 Update `frontend/src/context/AuthContext.tsx` to decode JWT and extract `role`

## Phase 3: User Story 1 - Admin Access Control (P1)
*Goal: Restrict access to critical functions to admins only.*

### Backend
- [x] T011 [US1] Create `backend/src/api/admin.py` with `restart_stream` endpoint
- [x] T012 [US1] Implement `require_admin` dependency in `backend/src/api/auth.py` (or `dependencies.py`)
- [x] T013 [US1] Protect `restart_stream` endpoint in `backend/src/api/admin.py` with `require_admin`
- [x] T014 [US1] Register `admin` router in `backend/src/main.py`

### Frontend
- [x] T015 [US1] Update `frontend/src/components/ProtectedRoute.tsx` to accept `allowedRoles` prop
- [x] T016 [US1] Update `frontend/src/App.tsx` to protect admin-only routes (if any) or wrap admin components
- [x] T017 [US1] Create `frontend/src/api/admin.ts` to call admin endpoints

## Phase 4: User Story 2 - Default User Role (P1)
*Goal: Ensure new users are assigned the 'user' role by default.*

### Backend
- [x] T018 [US2] Verify `User` model in `backend/src/models/user.py` has `default='user'` for `role` column
- [x] T019 [US2] (Optional) Add test case in `backend/tests/test_auth_service.py` to verify default role on registration

## Phase 5: User Story 3 - UI Adaptation (P2)
*Goal: Hide admin controls from regular users.*

### Frontend
- [x] T020 [US3] Update `frontend/src/pages/DashboardPage.tsx` to use `useAuth` hook
- [x] T021 [US3] Conditionally render "Restart Stream" button in `frontend/src/pages/DashboardPage.tsx` based on `user.role === 'admin'`

## Phase 6: Polish & Cross-Cutting Concerns
*Goal: Final touches and cleanup.*

- [x] T022 Add "Admin" badge to user avatar/profile in `frontend/src/components/Navbar.tsx` (or similar)
- [x] T023 Run full regression test of Auth flow (Login/Register/Logout) using `backend/tests/test_auth_rbac.py` and `frontend/tests/e2e/rbac.spec.ts`
- [x] T024 Update `docs/development/frontend-auth-implementation.md` with RBAC details (Constitution IV)

## Dependencies

1. **Phase 1 & 2** must be completed before **Phase 3, 4, 5**.
2. **Phase 3 (Backend)** must be completed before **Phase 3 (Frontend)** integration.
3. **Phase 5** depends on **Phase 1 (AuthContext)**.

## Implementation Strategy

1. **MVP**: Complete Phases 1, 2, and 3 (Backend). This gives us a working backend with roles and a way to manually promote admins.
2. **Frontend Integration**: Complete Phase 3 (Frontend) and Phase 5. This exposes the functionality to the user.
3. **Polish**: Phase 6.

## Parallel Execution Examples

- **T011 (Backend Admin API)** and **T015 (Frontend ProtectedRoute)** can be done in parallel after Phase 2.
- **T018 (Verify Default Role)** can be done anytime after T006.
