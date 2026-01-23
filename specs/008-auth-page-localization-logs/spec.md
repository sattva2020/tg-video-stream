---
title: "Auth page — localization + logs"
---

# Спецификация: Локализация ошибок авторизации и сбор фронтенд-артефактов

Коротко: эта фича добавляет полноценную поддержку локализованных ошибок аутентификации
в клиенте и бэкенде, фиксирует контракт API (AuthError) и гарантирует сбор фронтенд-артефактов
Playwright/Vitest в `.internal/frontend-logs` для диагностики.

Контекст:
- Файлы реализации: `frontend/src/i18n/index.ts`, `frontend/tests/vitest/i18n-keys.spec.ts`
- CI: выгрузка артефактов Playwright в `.internal/frontend-logs` (см. `.github/workflows/e2e.yml`)

Цель:
- Обеспечить однозначное поведение при возврате ошибок из `/auth` (backend) — поддержка `message` или `message_key`.
- Дать клиенту детерминированный путь получения локализованного сообщения (i18n) и предусмотреть fallback.
- Настроить и документировать CI-артефакты для e2e отчётов (Playwright) и локальных smoketests (Vitest).

---

## Функциональные требования (FR)

- FR-001: Бэкенд возвращает объект ошибки `AuthError` с полями `code` (строка) и `hint` (обязательное описание).
- FR-002: `AuthError` может содержать либо `message` — локализованный текст (server-side), либо `message_key` — ключ для клиентского i18n.
- FR-003: Клиент (frontend) разрешает оба варианта: если приходит `message` — отображает его; если приходит `message_key` — использует i18n ресурсы для локализации.
- FR-004: Клиент сохраняет выбранный язык/локаль и поддерживает fallback на `en`/`ru` при отсутствии перевода.
- FR-005: Добавить детерминированный Vitest smoke-test, который проверяет наличие ключей локализации, используемых в UI.

## Нефункциональные требования (NFR)

- NFR-001: Производительность — рендер ошибки не должен увеличивать TTI страницы более чем на 100 мс относительно чистой auth страницы **при измерении через Lighthouse (mobile, 4× CPU throttle, 4G)**. Замеры выполняются скриптом `tests/perf/auth-error-tti.mjs`, который запускает тестовый Playwright сценарий с принудительным показом ошибки и сохраняет отчёт в `.internal/frontend-logs/perf/${run_id}`.
- NFR-002: Диагностика — все Playwright/CI-отчёты сохраняются в `.internal/frontend-logs/playwright/${run_id}`.
- NFR-003: Трассируемость — тестовые отчёты и лог-файлы должны быть доступны как артефакты CI для PR.

## Пользовательские истории (приоритеты)

1. **US1 (P1)** — Клиент показывает человекочитаемую локализованную ошибку при регистрации и логине.
   - Acceptance: при ответе backend с `code=409`/`message_key=auth.email_registered` клиент на экране регистрации показывает текст из i18n на языке пользователя.
2. **US2 (P1)** — Клиент обрабатывает конфликты/ошибки (403/409) используя ключи локализации и гарантирует fallback при отсутствии перевода.
   - Acceptance: при `code=409`/`message_key=auth.google_account_exists` UI показывает сообщение и `hint`; при отсутствии перевода — fallback `auth.server_error` появляется <200 мс.
3. **US3 (P2)** — Оператор/разработчик получает диагностические артефакты для Playwright и Vitest.
   - Acceptance: Playwright отчёт загружен в `.internal/frontend-logs/playwright/${run_id}` ≤2 мин после завершения теста, Vitest smoke-test регистрируется в CI с логами ≤5 МБ.

## Контракты API / модель ошибок

AuthError (HTTP JSON)
```json
{
  "code": "409",
  "hint": "conflict: email exists",
  // либо
  "message": "Пользователь с таким email уже существует",
  // либо
  "message_key": "auth.email_registered"
}
```

Обязательные поля: `code`, `hint`. Один из `message` или `message_key` может присутствовать — разрешается оба быть отсутствующими в общем случае (тогда UI показывает общий message_key `auth.server_error`).

## Acceptance criteria (критерии приёмки)

- AC-1: Backend-ответы для типичных сценариев (403/rejected, 409/conflict, 500 generic) формализованы тестами и контрактами.
- AC-2: Клиент покрыт Vitest smoke-test, проверяющим перечисленные message_key'и: auth.email_registered, auth.google_account_exists, auth.account_pending, auth.account_rejected, auth.server_error.
- AC-3: Playwright e2e, при сбоях, сохраняет и загружает отчёты в `/.internal/frontend-logs/playwright/${run_id}` и CI прикрепляет их к PR.

## Edge cases

- EC-1: Отсутствие ключа локализации в клиенте → fallback: если message_key не найден, использовать `message` из сервера; если и того нет — показать generic `auth.server_error`.
- EC-2: Ответ сервера содержит только `message` на языке, отличном от языка клиента → клиент показывает `message` без попытки перевода.
- EC-3: Неожиданные 5xx не в зоне ответственности фичи (глобальная обработка), UI показывает generic server message.

## Tests & Validation

- Юнит/интеграция: backend pytest для контрактного теста `AuthError` (см. tasks.md) — целевое время выполнения < 10 с.
- Frontend Vitest smoke-test `frontend/tests/vitest/i18n-keys.spec.ts` — выполняется ≤5 с и проходит при повторном запуске без флаки (<1 % нестабильных прогонов).
- E2E Playwright: сценарии регистрации/логина с контролируемыми backend-подделками, отчётность в CI; генерация HTML-отчёта и trace длится ≤2 минут.
- Performance/Lighthouse: `tests/perf/auth-error-tti.mjs` запускает Lighthouse (mobile preset) до и после вызова ошибки авторизации, проверяет `TTI ≤ 2 с` и `ΔTTI ≤ 100 мс`, логирует JSON + HTML отчёты в `.internal/frontend-logs/perf/${run_id}`.

---

Дата последнего обновления: 2025-11-26
