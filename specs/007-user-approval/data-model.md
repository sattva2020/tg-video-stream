# Data model — User Approval

## Entities

### User

- Поля (существующие): id, email, password_hash, role, created_at, updated_at, ...
- Новое поле (для этой фичи): `status`
  - Тип: Enum('pending', 'approved', 'rejected') — хранится как строка (SQLAlchemy Enum or VARCHAR with constraint)
  - Default для NEW rows: `pending`
  - Миграция для существующих rows: при добавлении колонки всё существующие пользователи должны быть помечены как `approved` (чтобы не заблокировать админов и существующих пользователей)

## State transitions

- initial -> pending (on registration)
- pending -> approved (Admin action)
- pending -> rejected (Admin action)
- rejected -> (no transitions) or deleted (optional admin action)

## Validation rules

- При создании пользователя через публичный endpoint `register` — установить `status = 'pending'`.
- Никогда не выставлять `approved` автоматически при регистрации (только через админ-панель or admin API).
- При миграции пометить существующих как `approved`.

## DB migrations

- Alembic migration to:
  1. Add column `status` to `users` (nullable=False) with server default `'approved'` (used during migration), then
  2. Update existing users to `'approved'` explicitly, then
  3. Alter default to `'pending'` for future inserts at application-level (or set server default to `pending` for new rows) and mark non-nullable as appropriate.

Note: ensure migration is reversible — on downgrade drop column and constraints.

## Frontend types

- `frontend/src/types/user.ts` — extend `User` interface:

  - status: 'pending' | 'approved' | 'rejected'

## Tests

- Backend tests (pytest): model and auth layer tests for status enforcement + admin endpoints tests
- Frontend tests (Playwright) ensure registration, pending-behavior, admin approval flow
