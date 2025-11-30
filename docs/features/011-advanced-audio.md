# Feature 011 — Advanced Audio & Playlist UI

Summary
-------

This feature adds on-the-fly transcoding support for non-native audio formats (FLAC, OGG, WAV) and a web UI to manage the playlist. The streamer will attempt to transcode incompatible audio to a format suitable for PyTgCalls (Opus by default) using FFmpeg.

Key changes
- Backend (`backend/`): `PlaylistItem` model extended with `status` and `duration`; API exposes those fields for clients.
- Streamer (`streamer/`): Added detection and transcoding profiles (`audio_utils.get_transcoding_profile`) and runtime pipeline to use `AudioPiped` with additional FFmpeg args when needed.
- Frontend (`frontend/`): New Playlist UI — `AddTrackForm`, `PlaylistQueue` and `/playlist` page; client-side polling (3s) keeps the UI in sync.

Testing & validation
- Backend: pytest unit tests were added for playlist API (tests/api/test_playlist_item_fields.py).
- Streamer: smoke/unit tests added for transcoding detection (tests/audio/test_transcoding.py).
- Frontend: vitest unit tests added for the playlist service (frontend/tests/vitest/playlist.service.spec.ts). Add Playwright E2E tests later when running the app end-to-end.

Deployment notes
- Ensure FFmpeg is available in the runtime image (streamer Dockerfile) and `yt-dlp` remains installed for best stream selection.
- The streamer expects a running backend at `BACKEND_URL` (env var) and will poll `/api/playlist/` for items.

Quick Verification
1. Add items via the UI: `http://localhost:5173/playlist`.
2. Observe streamer logs for "Transcoding required" messages when adding FLAC/OGG tracks.
3. Verify that playlist items include `status` and `duration` fields in the API responses.
