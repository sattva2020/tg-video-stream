# Data Model: Admin Dashboard

**Feature**: `009-admin-dashboard`

## Entities

### User
Existing entity in `backend/src/models/user.py`.

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `email` | String | User email |
| `role` | Enum | `user` or `admin` |
| `status` | Enum | `pending`, `approved`, `rejected` |
| `created_at` | DateTime | Registration timestamp |

### StreamStatus (Virtual)
Represents the current state of the video stream service.

| Field | Type | Description |
|-------|------|-------------|
| `status` | String | `online`, `offline`, `restarting` |
| `uptime` | Integer | Seconds since start (optional) |
| `viewers` | Integer | Current viewer count (optional) |

## State Transitions

### User Status
- `pending` -> `approved` (via Admin Action)
- `pending` -> `rejected` (via Admin Action)
- `approved` -> `rejected` (via Admin Action - Ban)
- `rejected` -> `approved` (via Admin Action - Unban)

### Stream Status
- `online` -> `restarting` -> `online` (via Restart Action)
