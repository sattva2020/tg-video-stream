# User Approval — behavior guide

This document describes the user approval flow implemented in feature 007-user-approval.

## Overview

- New users who sign up via the public registration endpoint are created with status `pending` and cannot log in until an Administrator approves them.
- Existing users in the database are marked `approved` by the migration so they retain access.
- Administrators can list pending users and approve or reject them using the Admin API or Admin UI.
- Admin notifications (email + Telegram) are sent asynchronously via background worker tasks.

## Endpoints

- POST /api/auth/register — creates user with `status=pending`; does not issue JWT for pending users.
- POST /api/auth/login — blocked for users with status != `approved` (returns 403).
- GET /api/admin/users?status=pending — Admin only; lists users.
- POST /api/admin/users/{id}/approve — Admin only; set status to `approved`.
- POST /api/admin/users/{id}/reject — Admin only; set status to `rejected`.

## Migration

- Alembic migration `c7f9a88e3b2_add_user_status.py` adds `status` column. Existing users are set to `approved`, future users default to `pending`.

## Notifications

- Admin notifications are delivered asynchronously via a background worker (Celery if configured) — see `backend/src/tasks/notifications.py`.
- SMTP and Telegram configuration keys documented in quickstart and `template.env`.

## Tests

- Backend unit tests: `backend/tests/test_user_approval.py`, `backend/tests/test_admin_user_approval.py`, `backend/tests/test_notifications.py`.
- Frontend Playwright e2e: `frontend/tests/e2e/approval.spec.ts`.

End of document
