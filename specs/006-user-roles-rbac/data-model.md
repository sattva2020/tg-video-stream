# Data Model: User Roles (RBAC)

## Entities

### User (Updated)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | Integer | Yes | PK | Unique identifier |
| `email` | String | Yes | - | User email |
| `hashed_password` | String | Yes | - | Hashed password |
| `role` | String | Yes | `'user'` | **NEW**: User role ('user', 'admin') |
| ... | ... | ... | ... | Existing fields |

## Database Schema Changes

### Table: `users`

```sql
ALTER TABLE users ADD COLUMN role VARCHAR NOT NULL DEFAULT 'user';
```

## API Data Structures (Pydantic)

### `User` (Response)

```python
class User(BaseModel):
    id: int
    email: str
    role: str  # NEW
    # ...
```

### `TokenData` (Internal)

```python
class TokenData(BaseModel):
    email: str | None = None
    role: str | None = None  # NEW
```
