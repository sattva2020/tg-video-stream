# Spec 024: User Playlists

## 1. Introduction
This specification outlines the implementation of user-specific playlists. Currently, the system supports a single global playlist. This feature will allow users to create, manage, and play their own playlists.

## 2. Scope
- **Database Schema**: New tables for `playlists` and `playlist_items`.
- **Backend API**: CRUD endpoints for playlists.
- **Frontend UI**: Interface for managing playlists (create, edit, delete, add items).
- **Playback Integration**: Ability to select a user playlist for the stream.
- **Sharing**: Ability to mark playlists as public and share them via link.

## 3. Technical Requirements

### 3.1. Database
New tables:
- `playlists`:
  - `id` (UUID, PK)
  - `user_id` (FK to users)
  - `name` (String)
  - `description` (String, nullable)
  - `is_public` (Boolean, default False)
  - `created_at` (DateTime)
  - `updated_at` (DateTime)
- `playlist_items`:
  - `id` (UUID, PK)
  - `playlist_id` (FK to playlists)
  - `file_id` (FK to files, nullable - if using uploaded files)
  - `url` (String, nullable - if using external URLs)
  - `title` (String)
  - `duration` (Integer, seconds)
  - `position` (Integer, for ordering)

### 3.2. API Endpoints
- `GET /api/playlists`: List user's playlists (and public playlists if filter applied).
- `POST /api/playlists`: Create a new playlist.
- `GET /api/playlists/{id}`: Get playlist details (check `is_public` if not owner).
- `PUT /api/playlists/{id}`: Update playlist metadata (owner only).
- `DELETE /api/playlists/{id}`: Delete playlist (owner only).
- `POST /api/playlists/{id}/items`: Add item to playlist (owner only).
- `PUT /api/playlists/{id}/items/{item_id}`: Update item (owner only).
- `DELETE /api/playlists/{id}/items/{item_id}`: Remove item (owner only).
- `POST /api/playlists/{id}/clone`: Clone a public playlist to my library.

### 3.3. Frontend
- **Playlist Manager**: A new page or section in the dashboard.
- **Playlist Editor**: Drag-and-drop interface for reordering items.
- **Selection**: Option to "Play this playlist" which updates the streamer configuration.
- **Sharing UI**: Toggle "Public" switch, "Copy Link" button.
- **Public Library**: View playlists shared by others.

## 4. Implementation Plan
1.  **Database Migration**: Create Alembic migration for new tables.
2.  **Backend Logic**: Implement SQLAlchemy models and Pydantic schemas.
3.  **API Routes**: Implement FastAPI routers.
4.  **Frontend UI**: Build React components.
5.  **Integration**: Connect UI to API.

## 5. Success Criteria
- Users can create multiple playlists.
- Users can add items (files/URLs) to playlists.
- Users can reorder items.
- Admin can select a playlist to be broadcasted.
