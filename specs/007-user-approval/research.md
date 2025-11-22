# Research — User Approval (Phase 0)

## Decision summary

- Решение: добавить в модель пользователя поле статуса (enum) со значениями: `pending`, `approved`, `rejected`.
- Новая регистрация → статус `pending` (по умолчанию). Существующие пользователи в БД при миграции получают статус `approved` (чтобы не блокировать текущих).
- Аутентификация: блокируем вход для `pending` и `rejected` пользователей — возвращаем корректную ошибку и читаемое сообщение на фронтенде.
- Админскиe операции: REST API для получения списка пользователей по статусу (GET /admin/users?status=pending), endpoint для одобрения (/admin/users/{id}/approve) и отклонения (/admin/users/{id}/reject).
- UI: в админ-панели добавляется страница "Ожидающие пользователи" со списком и кнопками Approve/Reject; регистрационная форма показывает сообщение о том, что аккаунт ожидает утверждения.
- Тесты до реализации: backend — pytest для проверок аутентификации/статусов и admin endpoints; frontend — Playwright e2e сценарии для регистрации/неудачного входа, принятия админом и успешного входа.

## Rationale

- Простота и прозрачность: хранение статуса прямо в модели пользователя — минимальные изменения и лёгкие проверки на стороне API.
- Безопасность: явная блокировка входа предотвращает доступ до проверки администратора.
- Миграция: чтобы не блокировать существующих пользователей (и админов), миграция помечает существующие записи как `approved`.

## Alternatives considered

- Auto-approve new users (rejected: безопасность) — REJECTED for security reasons.
- Invite-only flows / signup tokens (more secure but out of scope) — added as future enhancement.
- Email/Telegram notifications on approval (useful) — out of scope for MVP, can be added later.

## Implementation notes / constraints

- DB migration must set default to `pending` for new rows but set existing rows to `approved`.
- Ensure Alembic migration is reversible.
- Auth logic must check status early to avoid unnecessary 3rd-party calls (e.g., avoid creating JWT for pending users).
- Follow repo constitution: tests and docs added together with implementation and a tasks.md created in this spec dir.

## Test matrix (high-level)

- Backend unit tests:
  - Register new user -> user.status == 'pending'
  - Login with pending user -> rejected with appropriate 403/401 and message
  - Approve user via admin endpoint -> status changes to 'approved'
  - After approve -> login succeeds and JWT issued

- Frontend e2e tests (Playwright):
  - Signup flow: register -> see "account pending" message
  - Login attempt for pending -> show error and no navigation
  - Admin approves pending user -> user can login afterwards

## Next step

Phase 1: data-model.md and API contracts (OpenAPI) + frontend page(s) + quickstart/test instructions.
