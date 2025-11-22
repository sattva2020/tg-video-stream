# Tasks: User Authentication with Google

**Input**: Design documents from `/specs/002-google-auth/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No explicit test tasks are included as they were not requested in the feature specification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency configuration.

- [X] T001 Configure environment variables for backend in a `.env` file (e.g., `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `DATABASE_URL`, `JWT_SECRET`).
- [X] T002 Add backend dependencies to `backend/requirements.txt`: `fastapi`, `uvicorn`, `python-jose[cryptography]`, `requests-oauthlib`, `psycopg2-binary`, `SQLAlchemy`.
- [X] T003 [P] Add frontend dependencies to `frontend/package.json`: `axios`, `react-router-dom`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

- [X] T004 [P] Set up database connection and session management in `backend/src/database.py`.
- [X] T005 [P] Define the User model and table schema in `backend/src/models/user.py` based on `data-model.md`.
- [X] T006 Create initial database migration for the users table using a migration tool (e.g., Alembic).
- [X] T007 [P] Set up main FastAPI application and API router in `backend/src/main.py`.
- [X] T008 [P] Configure JWT utility functions for creating and decoding tokens in `backend/src/auth/jwt.py`.

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Stories 1 & 2 - Google Login (Priority: P1) 🎯 MVP

**Goal**: Allow new and returning users to sign up and log in via their Google account.

**Independent Test**: A user can click "Sign in with Google" on the frontend, complete the Google authentication flow, and be redirected back to the application as a fully logged-in user with a valid session.

### Implementation for User Stories 1 & 2

- [X] T009 [P] [US1] Create a "Sign in with Google" button component in `frontend/src/components/GoogleLoginButton.tsx`.
- [X] T010 [US1] Add the Google login button to the login page at `frontend/src/pages/LoginPage.tsx`.
- [X] T011 [US1] Implement the frontend logic to handle the redirect to the backend's `/auth/google` endpoint when the button is clicked.
- [X] T012 [US1] Implement the `/auth/google` redirect endpoint in `backend/src/api/auth.py`.
- [X] T013 [US1] Implement the `/auth/google/callback` endpoint in `backend/src/api/auth.py`.
- [X] T014 [US1] Create an authentication service in `backend/src/services/auth_service.py` to process the Google callback, create/retrieve users, generate a JWT, and handle the edge case where an email already exists with a different auth provider.
- [X] T015 [US1] Implement a frontend component/route to handle the callback from the backend, store the JWT, and redirect the user to the dashboard `frontend/src/pages/AuthCallback.tsx`.
- [X] T016 [P] [US1] Implement a protected `/users/me` endpoint in `backend/src/api/users.py` to allow the frontend to verify the JWT and fetch user data.

**Checkpoint**: At this point, User Stories 1 & 2 should be fully functional and testable independently.

---

## Phase 4: User Story 3 - Logout (Priority: P2)

**Goal**: Allow an authenticated user to securely end their session.

**Independent Test**: A logged-in user can click a "Logout" button, which clears their session on the frontend and redirects them to the login page.

### Implementation for User Story 3

- [X] T017 [P] [US3] Create a "Logout" button component in `frontend/src/components/LogoutButton.tsx`.
- [X] T018 [US3] Add the logout button to a visible part of the UI for authenticated users (e.g., a navbar).
- [X] T019 [US3] Implement the frontend logic to clear the stored JWT and redirect to the login page when the logout button is clicked.
- [X] T020 [US3] Implement the `/auth/logout` endpoint in `backend/src/api/auth.py`. (Note: For stateless JWT, this might be a no-op on the backend, or could add the token to a blacklist if implemented).

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories.

- [X] T021 [P] Add comprehensive error handling and user feedback to the frontend authentication flow.
- [X] T022 [P] Add structured logging to the backend authentication endpoints for monitoring and debugging.
- [X] T023 [P] Review and ensure all secrets and credentials are managed securely via environment variables and not hardcoded.

---

## Phase 6: Testing

**Purpose**: Ensure the feature is robust, reliable, and meets requirements.

- [X] T024 [P] [US1, US2] Write backend unit tests for the authentication service in `backend/src/services/auth_service.py`, covering user creation, retrieval, and the edge case of existing emails.
- [X] T025 [US1, US2] Write backend integration tests for the Google login endpoints (`/auth/google`, `/auth/google/callback`) in `backend/tests/`.
- [X] T026 [P] [US3] Write backend tests for the logout functionality.

---
**NOTE**: Tasks T027 and T028 were skipped. The Vitest testing environment is encountering a persistent and unresolvable module import error that prevents frontend unit tests from running. This issue needs to be investigated separately. The backend implementation and its tests are complete.
---

- [ ] T027 [P] [US1, US2] Write frontend unit tests for the `GoogleLoginButton` and `AuthCallback` page components.
- [ ] T028 [P] [US3] Write frontend unit tests for the `LogoutButton` component.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion. BLOCKS all user stories.
- **User Stories (Phase 3+)**: Depend on Foundational phase completion.
- **Polish (Final Phase)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Stories 1 & 2 (P1)**: Can start after Foundational (Phase 2). No dependencies on other stories.
- **User Story 3 (P2)**: Can start after Foundational (Phase 2). Depends on a user being logged in (i.e., US1/US2 functionality).

### Parallel Opportunities

- Once Foundational phase completes, different user stories can be worked on in parallel.
- Tasks marked with [P] can be worked on in parallel within their respective phases.

---

## Implementation Strategy

### MVP First (User Stories 1 & 2)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Stories 1 & 2.
4. **STOP and VALIDATE**: Test the complete Google login flow independently. This is the MVP.

### Incremental Delivery

1. Complete Setup + Foundational.
2. Add User Stories 1 & 2 → Test independently → Deploy/Demo (MVP).
3. Add User Story 3 → Test independently → Deploy/Demo.