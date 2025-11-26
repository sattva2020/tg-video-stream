---
title: "Plan — auth page localization + frontend logs"
---

# План реализации: локализация ошибок авторизации + сбор артефактов

Кратко: план описывает архитектурные решения, фазы разработки, критерии качества и CI-гейт
для фичи `008-auth-page-localization-logs`.

## Технический контекст

- Backend: FastAPI — возвращает `AuthError` по контракту (см. spec.md). Контракт оставляет за сервером право
  вернуть `message` или `message_key`.
- Frontend: React + TypeScript + i18next для локализации. Клиент разрешает `message` (server-rendered) и `message_key`.
- Testing: Vitest (unit/smoke), Playwright (e2e); CI GitHub Actions — сохранять Playwright отчёты в `.internal/frontend-logs`.

### Минимальные изменения CI / окружения

- E2E workflow: гарантировать `workflow_dispatch` для ручного запуска по feature веткам.
- Node engine в CI должен быть выбран как Node 20 LTS; установка `unixodbc-dev g++ libpq-dev` выполняется **до** `npm ci`, чтобы odbc собирался детерминированно.
- Playwright: сохранить HTML/trace/screenshots в папке `.internal/frontend-logs/playwright/${{ github.run_id }}` и загрузить как артефакт в течение ≤2 мин после завершения тестов; архивы ≤50 МБ.

## Фазы реализации (high-level)

Phase 1: Spec & Plan (done)
- Обновить spec.md, plan.md, tasks.md — первый checkpoint

Phase 2: Foundational (blocking)
- T0001–T0003: Настройка окружения, lint, formatting, CI-артефактов
- Обновить .github/workflows/e2e.yml для сохранения отчётов

Phase 3: User stories implementation
- US1 — Localized auth error display (T1001–T1007)
- US2 — Client-side message_key handling + translation coverage (T2001–T2004)
- US3 — CI & diagnostics: Vitest smoke + Playwright artifact uploads (T3001–T3004)

Phase 4: Polish & Release gate
- Lighthouse/TTI checks (T4001–T4004), store reports в `.internal/frontend-logs`, update docs/quickstart (T4001–T4003)

## Data model & contracts

- Data-model: User.status / role — план и тесты предполагают наличие семян/фикстур для `pending`, `rejected`, `conflict`.
- Контракт: `AuthError` — код и hint обязательны; либо message (server-side) либо message_key (client-side i18n).

## QA / tests / pipelines

- Unit & smoke tests:
  - Vitest smoke: `frontend/tests/vitest/i18n-keys.spec.ts` — проверка наличия ключей и соответствия UI, время выполнения ≤5 с, логи ≤1 МБ.
  - Pytest contract tests (backend) — проверки возвращаемых полей AuthError, p95 < 10 с на CI runner.

- E2E:
  - Playwright сценарии регистрации/логина, в которых backend возвращает конфликты (stub/mock responses) и проверяет `message_key` → UI; прогон ≤6 мин.
  - Сбор отчётов и загрузка в `.internal/frontend-logs/playwright/${{ github.run_id }}` + публикация trace ссылок в summary.
- Performance:
  - Lighthouse mobile прогон через `tests/perf/auth-error-tti.mjs` (запускает Playwright setup, затем Lighthouse). Скрипт сравнивает чистый auth экран и forced-error состояние, валидируя `TTI ≤ 2 с` и `ΔTTI ≤ 100 мс`, а результаты (JSON + HTML) архивируются в `.internal/frontend-logs/perf/${{ github.run_id }}` (покрывается задачей T4004).

## Rollout and CI gating

- Главные acceptance-gates:
  - Vitest smoke green (≤5 с, стабильность 99%)
  - Backend pytest green (контрактные тесты <10 с)
  - Playwright e2e green + artefact upload ≤2 мин после завершения
  - Lighthouse/TTI: TTI на auth странице ≤2 с на профиле 4G/CPU 4×, ΔTTI ≤ 100 мс при показе ошибки; отчёты из `tests/perf/auth-error-tti.mjs` прилагаются к release gate

## Risks & mitigation

- Risk: CI uses Node 18 by default — many frontend dependencies (vitest, vite, jsdom) require Node >= 20. Mitigation: set node-version: '20' in workflows for frontend jobs.
- Risk: Native modules during `npm ci` (odbc) cause install failures on hosted runner. Mitigation: add `npm ci --ignore-scripts` for jobs that don't need native modules or remove optional deps from frontend package.json; prefer using lightweight mock libs for tests.

## Документация и процессы

- Обновить `docs/auth-page-ui.md`, `docs/test-cases.md`, `docs/development/frontend-auth-implementation.md` и новый раздел `docs/development/frontend-l10n.md` — описать схему `AuthError`, артефакты и TTI/Playwright измерения.
- Перед PR запускать `npm run docs:validate && npm run docs:report`, сохранять логи в `.internal/docs-logs/${timestamp}` и ссылаться на них в release gate.
- Результаты smoke/e2e тестов прикладывать в `specs/008-auth-page-design/checklists/release-gate.md` (раздел "008-auth-page-localization-logs"), чтобы гейт видел фактические метрики.

## Deliverables

- `spec.md` (this feature) — ✅
- `plan.md` (this file) — ✅
- Tests: `frontend/tests/vitest/i18n-keys.spec.ts` — already present
- CI: `.github/workflows/e2e.yml` updated to upload Playwright reports — already present
- Perf tooling: `tests/perf/auth-error-tti.mjs` — добавляется в рамках T4004 для NFR-001

---

Дата: 2025-11-26
