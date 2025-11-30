# Quickstart: Advanced Audio & Playlist UI

**Feature**: 011-advanced-audio

## Prerequisites

- Docker & Docker Compose
- Python 3.12+
- Node.js 20+

## Running the Feature

1. **Start Backend & Database**:
   ```bash
   docker-compose up -d db backend
   ```

2. **Apply Migrations**:
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

3. **Start Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   Access UI at `http://localhost:5173/playlist`.

4. **Start Streamer**:
   ```bash
   cd streamer
   # Ensure .env has API_ID, API_HASH, SESSION_STRING
   python main.py
   ```

## Testing

### Backend
```bash
cd backend
pytest tests/api/test_playlist_item_fields.py
```

### Frontend
```bash
cd frontend
npm run test:ui
```

### Manual Verification
1. Open `http://localhost:5173/playlist`.
2. Add a URL to a FLAC file (e.g., from a public sample site).
3. Verify it appears in the list.
4. Use `curl` or your HTTP client with the `X-Streamer-Token` header to PATCH `/api/playlist/{id}/status` with `{"status": "playing", "duration": 125}` and confirm the `Status`/`Duration` columns on `/playlist` reflect the update before and after playback (change to `queued` or `error` as needed).
5. Check streamer logs: `Detected audio-only source`, `Playing: ...`.
6. Listen to the Telegram Group Call to confirm audio.
