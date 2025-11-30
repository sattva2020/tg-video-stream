---
description: "Task list for Advanced Audio & Playlist UI"
---

# Tasks: Advanced Audio & Playlist UI

**Input**: Design documents from `/specs/011-advanced-audio/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are MANDATORY per Constitution Principle III. Each component must have associated tests.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Verify project structure and dependencies for backend and frontend

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Update `PlaylistItem` model in `backend/src/models/playlist.py` to add `status` and `duration` fields
- [X] T003 Create Alembic migration for updated playlist table in `backend/alembic/versions/`
- [X] T004 [P] Update `backend/src/api/playlist.py` to expose new fields in Pydantic models and endpoints
- [X] T004a [P] Implement unit tests for Playlist API in `backend/tests/api/test_playlist.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Transcoding Unsupported Formats (Priority: P1) 🎯 MVP

**Goal**: Enable playback of FLAC, OGG, and other non-native formats via on-the-fly transcoding

**Independent Test**: Add a FLAC URL to the playlist and verify audio playback in the Telegram call

### Implementation for User Story 1

- [X] T005 [P] [US1] Update `streamer/audio_utils.py` to detect FLAC/OGG mime types and implement `TranscodingProfile` configuration
- [X] T006 [US1] Implement transcoding logic using `AudioPiped` in `streamer/main.py`
- [X] T006a [US1] Implement smoke test for transcoding logic in `tests/audio/test_transcoding.py`
- [X] T007 [US1] Add error handling for transcoding failures in `streamer/main.py`
 - [X] T015 [US1] Add `PATCH /api/playlist/{id}/status` endpoint so the streamer can push `playing/queued/error`
- [X] T016 [US1] Have the streamer call the status API before/after playback and on errors (include smoke test)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Playlist Management UI (Priority: P2)

**Goal**: Provide a web interface for users to manage the playback queue

**Independent Test**: Open /playlist page, add a track, see it appear in the list

### Implementation for User Story 2

- [X] T008 [P] [US2] Create API client service in `frontend/src/services/playlist.ts`
- [X] T008a [P] [US2] Implement E2E tests for Playlist UI in `frontend/tests/playlist.spec.ts`
- [X] T009 [P] [US2] Create PlaylistQueue component in `frontend/src/components/PlaylistQueue.tsx` with polling synchronization (SC-004)
- [X] T010 [P] [US2] Create AddTrackForm component in `frontend/src/components/AddTrackForm.tsx`
- [X] T011 [US2] Assemble Playlist page in `frontend/src/pages/Playlist.tsx`
- [X] T012 [US2] Add route for /playlist in `frontend/src/App.tsx`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T013 Update documentation in `docs/`
- [X] T014 Verify quickstart instructions in `specs/011-advanced-audio/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Independent of US1 logic

### Parallel Opportunities

- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, US1 and US2 can start in parallel
- Frontend components (T009, T010) can be built in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test transcoding manually
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
