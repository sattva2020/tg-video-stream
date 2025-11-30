# Data Model: Advanced Audio

**Feature**: 011-advanced-audio

## Entities

### Playlist Item (`playlist_items`)

Represents a media track in the playback queue.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, Auto-increment | Unique identifier |
| `url` | String | Not Null, Max 2048 | Direct URL to the media resource |
| `title` | String | Nullable, Max 255 | Display title of the track |
| `duration` | Integer | Nullable | Duration in seconds |
| `status` | Enum | Default 'queued' | `queued`, `playing`, `played`, `error` |
| `created_at` | DateTime | Default Now | Timestamp of addition |
| `updated_at` | DateTime | On Update Now | Timestamp of last status change |

## Relationships

- None (Single table for MVP).

## State Transitions

1. **New** -> `queued` (Initial state)
2. `queued` -> `playing` (Streamer picks up the track)
3. `playing` -> `played` (Streamer finishes playback)
4. `playing` -> `error` (Playback failed)
