---
title: "Tasks — auth page localization + frontend logs"
---

# Tasks: 008-auth-page-localization-logs

**Источник**: `specs/008-auth-page-localization-logs/spec.md`, `plan.md`.  
**Трекинг**: Пользовательские истории US1–US3, требования FR-001..FR-005, NFR-001..NFR-003.  
**Логи**: Все тестовые артефакты Playwright/Vitest складываем в `.internal/frontend-logs/` (директория уже в `.gitignore`). Публичные артефакты (`frontend/logs/`) публикуем только по согласованию.

## Формат записей

`- [ ] TXXXX (P?, USn) Краткое описание (файл/директория) — ссылка на FR/SC.`

## Phase 0 — Shared prerequisites (Blocking)

- [ ] T0001 (Foundation) Синхронизировать `.github/workflows/ci.yml` (job `frontend-test`) и `.github/workflows/e2e.yml` на Node 20, добавить установку `unixodbc-dev g++ libpq-dev` **до** `npm ci`, гарантировать копирование Playwright отчётов в `.internal/frontend-logs/playwright/${{ github.run_id }}` (FR-003, NFR-002, US3).
- [ ] T0002 (Foundation) Обновить `docs/test-cases.md` и `docs/development/frontend-auth-implementation.md`, добавив процедуру воспроизведения локализованных ошибок и ссылку на скачивание артефактов из `.internal/frontend-logs` (US1, US3, Принцип IV).
- [ ] T0003 (P, Foundation) Создать `tests/smoke/frontend/i18n-smoke.sh`, который запускает `npm run test:unit && npx playwright test tests/e2e/auth-errors.spec.ts --workers=1`, выгружает отчёты в `.internal/frontend-logs/smoke/${timestamp}` и документирует запуск в `tests/README.md` (US3, NFR-002).

## Phase 1 — US1 (P1) Локализованное отображение ошибок

**Цель**: Клиент всегда показывает человекочитаемое сообщение при 403/409/500 согласно FR-001..FR-004.

### Tests first

- [ ] T1001 (P, US1) Добавить контрактный pytest `backend/tests/test_auth_error_contract.py`, который проверяет, что объект `AuthError` содержит `code`, `hint` и один из `message/message_key`, плюс fallback `auth.server_error` (FR-001..FR-003, AC-1).
- [ ] T1002 (P, US1) Расширить `frontend/tests/vitest/i18n-keys.spec.ts`, чтобы ключи подтягивались из `specs/008-auth-page-localization-logs/spec.md` (парсинг Markdown) и сравнивались с i18n ресурсами — исключаем расхождения при добавлении новых переводов (FR-004, AC-2).

### Implementation

- [ ] T1003 (US1) Выделить `AuthErrorPayload` в `backend/src/models/auth_error.py` + использовать его в `backend/src/api/auth.py` для типизации `detail` и централизованного fallback (FR-001..FR-003, EC-1/EC-2).
- [ ] T1004 (US1) Обновить `backend/src/services/auth_service.py` и `backend/src/api/auth.py`, чтобы ответы `/register` и `/login` всегда возвращали `message_key`, даже когда сервер уже сгенерировал `message`, и логировали несоответствия (NFR-001 observability).
- [ ] T1005 (P, US1) Создать/обновить `specs/008-auth-page-localization-logs/contracts/auth-error.yaml` с описанием полей, примеров 403/409/500 и ссылкой на pytest (AC-1).
- [ ] T1006 (US1) Доработать компонент ошибок (`frontend/src/components/auth/AuthErrorNotice.tsx` + `frontend/src/pages/LoginPage.tsx`/`RegisterPage.tsx`), чтобы он принимал `message_key`, использовал `useTranslation()` и отображал подпись `hint` (FR-003, US1 acceptance).
- [ ] T1007 (US1) Задокументировать новую схему ошибок в `docs/auth-page-ui.md`, добавив таблицу соответствия `code` ↔ `message_key` (US1, Принцип IV).

## Phase 2 — US2 (P1) Клиентская локализация и устойчивость ключей

**Цель**: Клиент хранит выбор языка, умеет fallback и синхронизирован с backend ключами (FR-004, FR-005, EC-1).

- [ ] T2001 (P, US2) В `frontend/src/i18n/index.ts` добавить типобезопасный список поддерживаемых языков, включить сохранение выбора в `localStorage` (опции `i18next-browser-languagedetector`), описать границы в `docs/development/frontend-auth-implementation.md` (FR-004).
- [ ] T2002 (US2) Расширить `frontend/src/services/authService.ts` и `frontend/src/lib/api/authClient.ts`, чтобы fallback цепочка выглядела `message → resolved message_key → generic auth.server_error`, плюс логирование пропусков в `.internal/frontend-logs/frontend-errors.log` (EC-1, EC-2).
- [ ] T2003 (US2) Добавить Vitest `frontend/tests/vitest/localization-storage.spec.ts`, который мокает `localStorage` и проверяет, что выбор языка сохраняется и восстанавливается за <5 мс (NFR-001 — TTI рост ≤100 мс).
- [ ] T2004 (US2) Создать раздел `docs/development/frontend-l10n.md` (или обновить существующий документ), описав процесс добавления новых `message_key` и обязательные команды `npm run test:unit` + `npx playwright test` (Принцип IV).

## Phase 3 — US3 (P2) Диагностика и артефакты

**Цель**: Playwright/Vitest отчёты доступны из CI и локальных smoke для репродьюса (US3, NFR-002, NFR-003, AC-3).

- [ ] T3001 (P, US3) Добавить Playwright сценарий `frontend/tests/e2e/auth-errors.spec.ts` (happy path + 403/409), обновить `playwright.config.ts` с `reporter: [['html', { outputFolder: 'playwright-report' }], ['list']]` и убедиться, что `npx playwright test tests/e2e/auth-errors.spec.ts --workers=1` генерирует трейс (US3).
- [ ] T3002 (US3) Создать `frontend/scripts/archive-playwright.mjs`, который архивирует `frontend/playwright-report` → `.internal/frontend-logs/playwright/${run_id}/report.zip` и вызывается из npm-скрипта `npm run test:ui:ci` (NFR-002).
- [ ] T3003 (US3) Обновить `.github/workflows/e2e.yml` шаг `Upload frontend Playwright artifacts`, чтобы дополнительно публиковать ссылку в summary (step `actions/github-script`) и описать процедуру в `docs/bag-reports.md` (US3, NFR-003).
- [ ] T3004 (US3) Добавить Vitest smoke команду `npm run test:errors` (alias `vitest run tests/vitest/i18n-keys.spec.ts tests/vitest/localization-storage.spec.ts`) и интегрировать её в job `frontend-test` (`ci.yml`) после линта (US2/US3, AC-2).

## Phase 4 — Polish & Release Gate

- [ ] T4001 [Polish] Обновить `specs/008-auth-page-localization-logs/spec.md` и `plan.md`, синхронизировать метрики (TTI Δ ≤100 мс, Playwright upload SLA <2 мин.) и удалить остатки шаблонов `Feature Specification/Implementation Plan` (Принцип I).
- [ ] T4002 [Polish] Перенести результаты тестов и проверок в `docs/REPORTS/documentation-report.md` через `npm run docs:validate && npm run docs:report`, приложить ссылки к `specs/008-auth-page-design/checklists/release-gate.md` (Принцип IV).
- [ ] T4003 [Polish] Актуализировать `OUTSTANDING_TASKS_REPORT.md`, добавив блок "008-auth-page-localization-logs" с открытыми рисками и ожидаемыми сроками (готовность к релизу).
 - [x] T4004 [Polish, NFR-001] Создать скрипт `tests/perf/auth-error-tti.mjs` + npm-скрипт `npm run perf:auth-errors` — реализован. Скрипт сохраняет отчёты в `.internal/frontend-logs/perf/${run_id}` (см. `2025-11-26T13-56-09-047Z`), генерирует `summary.json` и `summary.md` и публикует метрики (TTI и ΔTTI). (NFR-001).

## Phase 4.1 — Remediation & Performance fixes

- [ ] T5001 (P, US3, NFR-001) Research & profiling — провести профайлинг страницы `auth` (Vite bundle, network waterfall, 3D scenes), собрать список корневых причин высоких TTI, сформировать мердж‑план и список приоритетных изменений. Результат: детализированный отчет в `.internal/frontend-logs/perf/<run_id>/profiling/` + обновление docs. (owner: @frontend)
- [ ] T5002 (P, US3, NFR-001) Implement optimizations — по результатам T5001: lazy-load heavy assets (3D), code-split auth page, reduce initial bundle, defer third-party scripts, уменьшить LCP/TTI; включить regression tests и пересчитать perf. (owner: @frontend)
- [ ] T5003 (P, infra) CI perf guard — включить `frontend-perf.yml` в workflows, настроить PR-run для feature веток и жесткое правило (fail PR) при превышении порогов; документировать поведение в `tests/perf/README.md`. (owner: @ci)
