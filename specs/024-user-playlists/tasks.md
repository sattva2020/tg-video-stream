# Tasks for Spec 024: User Playlists

## Phase 1: Database & Backend Core
- [x] **T001** Create SQLAlchemy models (`Playlist`, `PlaylistItem`) in `backend/src/database/models.py` (Reused existing `Playlist` in `schedule.py`).
- [x] **T002** Create Pydantic schemas in `backend/src/schemas/playlist.py`.
- [x] **T003** Generate Alembic migration (Existing migration `l1m2n3o4p5q6` covers `is_public`).
- [x] **T004** Apply migration to database (Already applied).

## Phase 2: API Implementation
- [x] **T005** Create CRUD service in `backend/src/services/user_playlist_service.py` (handle `is_public` logic).
- [x] **T006** Implement API endpoints in `backend/src/api/routes/playlists.py`.
- [x] **T007** Register new router in `backend/src/main.py`.
- [ ] **T008** Write unit tests for playlist API (including access control).

## Phase 3: Frontend Implementation
- [ ] **T009** Create API client methods in `frontend/src/api/playlists.ts`.
- [ ] **T010** Create `PlaylistList` component (list of playlists + public tab).
- [ ] **T011** Create `PlaylistEditor` component (manage items + public toggle).
- [ ] **T012** Add "Playlists" page to the router and navigation.

## Phase 4: Integration & Polish
- [ ] **T013** Implement "Play Now" functionality (replace current streamer playlist).
- [ ] **T014** Add drag-and-drop reordering support (dnd-kit or similar).
- [ ] **T015** Implement "Clone Playlist" feature for public playlists.
- [ ] **T016** Verify permissions (users can only edit their own, view public).
