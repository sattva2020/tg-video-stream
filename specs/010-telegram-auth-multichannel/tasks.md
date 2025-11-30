# Tasks: Telegram Auth & Multichannel

**Feature**: Telegram Auth & Multichannel
**Status**: Completed
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

## Phase 1: Core Backend & Encryption
**Goal**: Implement secure storage for Telegram sessions and the interactive auth API.

- [x] **Task 1.1**: Add `SESSION_ENCRYPTION_KEY` to `.env` generation script and config loader.
- [x] **Task 1.2**: Implement `EncryptionService` (Fernet) in `src/services/encryption.py`.
- [x] **Task 1.3**: Update Database Models:
    - Create `TelegramAccount` (phone, encrypted_session, user_id).
    - Create `Channel` (account_id, chat_id, name, status).
    - Update `PlaylistItem` to support `type` (youtube/local/stream).
- [x] **Task 1.4**: Implement `TelegramAuthService`:
    - `send_code(phone)`
    - `sign_in(phone, code, password)` -> returns session string -> encrypts -> saves to DB.
- [x] **Task 1.5**: Create API Endpoints for Auth (`/api/auth/telegram/*`).

## Phase 2: Streamer Process Management
**Goal**: Enable dynamic management of independent streamer processes.

- [x] **Task 2.1**: Create `SystemdService` in `src/services/systemd.py`:
    - Generate `.service` content for a specific channel.
    - `start_channel(channel_id)`, `stop_channel(channel_id)`, `restart_channel(channel_id)`.
- [x] **Task 2.2**: Update `streamer/main.py` to accept configuration via Environment Variables (loaded from systemd context) instead of just `session_gen.session`.
- [x] **Task 2.3**: Implement `StreamerController` in backend to orchestrate `SystemdService`.

## Phase 3: Frontend Auth Flow & Channel Management
**Goal**: Allow users to manage accounts and channels via UI.

- [x] **Task 3.1**: Create `TelegramLogin` component:
    - Phone input form.
    - Code input form (with countdown).
    - 2FA Password input (conditional).
- [x] **Task 3.2**: Create `ChannelManager` page:
    - List of channels.
    - "Add Channel" modal.
    - Start/Stop controls for each channel.
- [x] **Task 3.3**: Integrate Frontend with Backend Auth & Streamer APIs.

## Phase 4: Local File Support & Integration
**Goal**: Support local media files and finalize the feature.

- [x] **Task 4.1**: Implement `FileService`:
    - `list_files(path)` restricted to `data/media`.
    - Validate file existence before adding to playlist.
- [x] **Task 4.2**: Update Playlist UI to support selecting "Local File" or "URL".
- [x] **Task 4.3**: End-to-End Test:
    - Login -> Create Channel -> Add Local File -> Start Stream -> Verify Process Running.
