# Research: User Roles (RBAC) Implementation

**Feature**: User Roles (RBAC)
**Date**: 2025-11-22

## 1. JWT Role Storage vs Database Check

### Decision
**Store role in JWT payload (`sub`, `role`).**

### Rationale
- **Performance**: Frontend and Backend can check permissions without an extra DB query on every request.
- **Statelessness**: Aligns with JWT principles.
- **Simplicity**: Frontend immediately knows the role after decoding the token.

### Alternatives Considered
- **Database Check on every request**: More secure (instant revocation), but higher DB load.
- **Separate `/me` call**: Requires an extra round-trip before rendering the UI.

### Implementation Detail
- Update `create_access_token` to include `role` in claims.
- Update `get_current_user` to optionally validate role from token (or just trust token signature).
- **Edge Case**: If a user's role changes, they must re-login to get a new token. This is acceptable for this MVP.

## 2. Frontend Route Protection

### Decision
**Higher-Order Component (HOC) / Wrapper Component `ProtectedRoute`.**

### Rationale
- **Standard Pattern**: Widely used in React.
- **Declarative**: `<Route element={<ProtectedRoute requiredRole="admin" />}>`.

### Implementation Detail
- `AuthProvider` stores `user` object (including `role`).
- `ProtectedRoute` checks `user.role`.
- If check fails, redirect to `/` or show "Access Denied".

## 3. Database Schema

### Decision
**Add `role` column to `users` table as String.**

### Rationale
- **Simplicity**: Enum types in PostgreSQL can be tricky with Alembic migrations (creating types). String is sufficient for 2 roles.
- **Flexibility**: Easy to add new roles later without DB type migration.

### Implementation Detail
- Column: `role` (VARCHAR/String), default `'user'`, not null.
- Migration: Update existing users to `'user'`.

## 4. Admin Creation

### Decision
**CLI Script `scripts/create_admin.py`.**

### Rationale
- **Security**: No public endpoint to "become admin".
- **Automation**: Can be run during deployment or setup.

### Implementation Detail
- Script accepts email and promotes that user to admin.
