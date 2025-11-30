# Test Plan — Message vs message_key (Auth errors)

Цель: уточнить и зафиксировать набор тестов, покрывающих поведение сервера и фронтенда при возврате локализованного `message` и при возврате `message_key`.

Область: `/api/auth/login`, `/api/auth/register`, `/api/users/me` — ответы 403/409.

Контексты тестирования:
- Backend contract tests (pytest)
- Frontend unit tests (Vitest)
- Frontend e2e tests (Playwright)

Общие правила:
- Любой тест должен проверять наличие `code` и `hint` в теле ответа.
- Поведение локализации:
  - Если клиент отправляет `Accept-Language` и сервер поддерживает язык, сервер возвращает `message` (локализованный текст).
  - Если сервер не локализует — возвращает `message_key`.

1) Pytest — backend/tests/test_auth_errors.py (контракт)
- TC1: `Accept-Language: ru` AND server has translation
  - Выполнить POST /api/auth/register или /api/auth/login так, чтобы получить 409/403.
  - assert response.status == 409/403
  - assert `code` in body and `hint` in body
  - assert `message` in body and type == string
  - assert either `message_key` may or may not be present; but `message` must be present

- TC2: server does NOT localize (no translation for requested lang or no Accept-Language)
  - Simulate server configured without translation support OR omit Accept-Language
  - assert `message_key` in body (pattern: /^[a-z0-9_]+(\.[a-z0-9_]+)*$/)
  - assert `message` not required

- TC3: contract conformance
  - Validate response body against `contracts/auth-ui.yaml` schema (anyOf case)

2) Vitest — frontend unit (ErrorToast, authService)
- UT1: ErrorToast renders `message` value directly
  - stub a response: { code: 'conflict', hint: 'email exists', message: 'Этот адрес уже занят' }
  - Ensure ErrorToast displays 'Этот адрес уже занят' and styling (light/dark) checks

- UT2: ErrorToast resolves `message_key` via i18next stub
  - stub a response: { code: 'conflict', hint: 'email exists', message_key: 'auth.email_registered' }
  - stub i18next.t('auth.email_registered') -> 'Этот адрес уже занят'
  - Ensure ErrorToast displays resolved string

- UT3: authService transforms backend payload into AuthFormState.error
  - validate for inputs with message and message_key

3) Playwright — e2e scenarios (frontend/tests/playwright/auth-page.spec.ts)
- E2E1: Stub server returns localized `message` (Accept-Language: ru)
  - Start app, stub `/api/auth/register` to return 409 + body with `message` in RU
  - Fill form -> submit -> expect toast/inline displays server `message` literally

- E2E2: Stub server returns `message_key` (no server localization)
  - stub `/api/auth/register` 409 + body { message_key: 'auth.email_registered' }
  - Ensure i18next is configured with RU catalog for `auth.email_registered` and UI shows localized string

- E2E3: Coverage for `/api/auth/login` 403 and `/api/users/me` non-approved
  - Similar to E2E1/E2E2, check ErrorToast + form state changes

4) CI integration & reporting
- Ensure pytest tests run in backend CI job
- Ensure Vitest + Playwright run in frontend CI jobs
- Save test reports to `.internal/frontend-logs/` and add links to PR

Run commands (local dev):

# Backend tests
pytest backend/tests/test_auth_errors.py::test_message_returned_when_localized -q
pytest backend/tests/test_auth_errors.py::test_message_key_returned_when_no_localization -q

# Frontend unit
pnpm run test:unit -- test/vitest/error-toast.spec.tsx

# Playwright
pnpm exec playwright test frontend/tests/playwright/auth-page.spec.ts --grep "errors" --project=chromium

Дополнительно: создать тестовые данные/fixtures для разных языков и добавить minimal i18n catalog (RU) used by tests.
