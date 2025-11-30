# Tasks: Telegram Login

**Input**: Design documents from `/specs/013-telegram-login/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Включены тесты согласно Constitution (Принцип III) — pytest, Vitest, Playwright.

**Organization**: Задачи сгруппированы по user stories для независимой реализации и тестирования.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Можно выполнять параллельно (разные файлы, нет зависимостей)
- **[Story]**: К какой user story относится задача (US1, US2, US3, US4)
- Указаны точные пути к файлам

> ⚖️ Конституция: для каждой пользовательской истории зафиксированы связанные тесты в `tests/`
> и необходимые обновления документации. Задачи по окружению ссылаются на `template.env`.

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`, `frontend/tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Переменные окружения и базовая конфигурация

- [X] T001 Добавить переменные Telegram в config/template.env
- [X] T002 [P] Обновить backend/src/core/config.py для загрузки Telegram переменных
- [X] T003 [P] Добавить константы Telegram в frontend/src/config.ts

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Расширение модели User и миграция БД — БЛОКИРУЕТ все user stories

**⚠️ CRITICAL**: Без этой фазы невозможна работа над user stories

- [X] T004 Добавить поля telegram_id, telegram_username в backend/src/models/user.py
- [X] T005 Создать Alembic миграцию в backend/alembic/versions/xxx_add_telegram_auth_fields.py
- [X] T006 [P] Создать Pydantic схемы в backend/src/schemas/telegram_auth.py
- [X] T007 [P] Создать сервис верификации подписи в backend/src/services/telegram_auth_service.py
- [X] T008 Зарегистрировать роутер Telegram в backend/src/api/__init__.py

**Checkpoint**: Модель User расширена, миграция применена, сервис верификации готов

---

## Phase 3: User Story 1 — Вход через Telegram Login Widget (Priority: P1) 🎯 MVP

**Goal**: Пользователь может войти через Telegram и получить сессию

**Independent Test**: Нажатие "Войти через Telegram" → авторизация в Telegram → перенаправление на /dashboard

### Tests for User Story 1

- [X] T009 [P] [US1] Unit тест верификации подписи в backend/tests/test_telegram_auth_service.py
- [X] T010 [P] [US1] Integration тест endpoint /api/auth/telegram в backend/tests/test_telegram_auth_api.py
- [X] T011 [P] [US1] Unit тест TelegramLoginButton в frontend/tests/components/TelegramLoginButton.test.tsx

### Implementation for User Story 1

- [X] T012 [US1] Реализовать POST /api/auth/telegram endpoint в backend/src/api/auth/telegram.py
- [X] T013 [US1] Расширить AuthService для Telegram в backend/src/services/auth_service.py
- [X] T014 [P] [US1] Создать TelegramLoginButton компонент в frontend/src/components/TelegramLoginButton.tsx
- [X] T015 [P] [US1] Создать API клиент telegramAuth в frontend/src/services/telegramAuth.ts
- [X] T016 [P] [US1] Создать хук useTelegramAuth в frontend/src/hooks/useTelegramAuth.ts
- [X] T017 [US1] Добавить TelegramLoginButton на LoginPage в frontend/src/pages/LoginPage.tsx
- [X] T018 [US1] Добавить структурированное логирование для Telegram auth событий

**Checkpoint**: User Story 1 полностью функциональна — вход через Telegram работает

---

## Phase 4: User Story 2 — Автоматическая регистрация (Priority: P1)

**Goal**: При первом входе через Telegram автоматически создаётся аккаунт с ролью "pending"

**Independent Test**: Первый вход через Telegram → создание нового пользователя → роль "pending"

### Tests for User Story 2

- [X] T019 [P] [US2] Тест создания нового пользователя в backend/tests/test_telegram_auth_service.py
- [X] T020 [P] [US2] Тест присвоения роли pending в backend/tests/test_telegram_auth_api.py

### Implementation for User Story 2

- [X] T021 [US2] Реализовать get_or_create_telegram_user в backend/src/services/auth_service.py
- [X] T022 [US2] Добавить обработку is_new_user в ответе API
- [X] T023 [US2] Реализовать обновление профиля (имя, фото) при каждом входе

**Checkpoint**: User Story 2 работает — новые пользователи создаются автоматически

---

## Phase 5: User Story 3 — Выход из системы (Priority: P2)

**Goal**: Пользователь может выйти из приложения

**Independent Test**: Авторизованный пользователь нажимает "Выйти" → сессия завершается → редирект на /login

### Implementation for User Story 3

- [X] T024 [US3] Проверить существующий logout endpoint работает для Telegram сессий
- [ ] T025 [US3] Добавить тест logout для Telegram-авторизованных пользователей

**Checkpoint**: User Story 3 работает — выход корректно завершает сессию

---

## Phase 6: User Story 4 — Связывание Telegram с аккаунтом (Priority: P2)

**Goal**: Пользователь с Google/email аккаунтом может привязать Telegram

**Independent Test**: Авторизованный пользователь → настройки → подключить Telegram → успешное связывание

### Tests for User Story 4

- [ ] T026 [P] [US4] Тест POST /api/auth/telegram/link в backend/tests/test_telegram_link_api.py
- [ ] T027 [P] [US4] Тест DELETE /api/auth/telegram/unlink в backend/tests/test_telegram_unlink_api.py
- [ ] T028 [P] [US4] Тест конфликта (Telegram уже привязан к другому) в backend/tests/test_telegram_link_api.py

### Implementation for User Story 4

- [X] T029 [US4] Реализовать POST /api/auth/telegram/link в backend/src/api/auth/telegram.py
- [X] T030 [US4] Реализовать DELETE /api/auth/telegram/unlink в backend/src/api/auth/telegram.py
- [X] T031 [US4] Добавить проверку альтернативного способа входа перед unlink
- [X] T032 [P] [US4] Добавить кнопку "Подключить Telegram" в frontend/src/pages/SettingsPage.tsx
- [X] T033 [US4] Реализовать UI для отвязки Telegram (с проверкой возможности)

**Checkpoint**: User Story 4 работает — связывание и отвязка Telegram функционирует

---

## Phase 7: Security & Rate Limiting (Cross-Cutting)

**Purpose**: Защита от атак согласно FR-016, FR-017, FR-018

- [X] T034 [P] Добавить rate limiting на /api/auth/telegram с slowapi (использовать TELEGRAM_AUTH_RATE_LIMIT_PER_HOUR из template.env)
- [X] T035 [P] Добавить CAPTCHA backend проверку (Cloudflare Turnstile) после 3 попыток за 10 минут
- [X] T035a [P] Интегрировать Turnstile CAPTCHA компонент в frontend/src/components/TurnstileWidget.tsx
- [X] T036 [P] Добавить логирование подозрительных попыток регистрации
- [ ] T037 Тест rate limiting в backend/tests/test_telegram_rate_limit.py

---

## Phase 8: Polish & Documentation

**Purpose**: Финальная документация и валидация

- [X] T038 [P] Создать документацию в docs/features/telegram-auth.md
- [X] T039 [P] Обновить docs/README.md с описанием Telegram auth
- [ ] T040 Выполнить npm run docs:validate
- [ ] T041 Провести E2E тест по quickstart.md сценариям
- [ ] T042 [P] E2E тест Playwright в frontend/tests/e2e/telegram-login.spec.ts

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Нет зависимостей — начинать сразу
- **Foundational (Phase 2)**: Зависит от Setup — БЛОКИРУЕТ все user stories
- **User Stories (Phase 3-6)**: Все зависят от Foundational
  - US1 и US2: Можно параллельно
  - US3: Минимальные изменения, можно параллельно
  - US4: Можно параллельно после US1/US2
- **Security (Phase 7)**: Зависит от Phase 3 (endpoint должен существовать)
- **Polish (Phase 8)**: Зависит от завершения всех желаемых user stories

### User Story Dependencies

```
Setup (Phase 1)
    │
    ▼
Foundational (Phase 2) ─── GATE ───┐
    │                              │
    ▼                              ▼
┌───────────┬───────────┬───────────┬───────────┐
│  US1 (P1) │  US2 (P1) │  US3 (P2) │  US4 (P2) │
│   Вход    │  Регистр. │   Выход   │   Link    │
└───────────┴───────────┴───────────┴───────────┘
         │                              │
         ▼                              ▼
    Security (Phase 7)           Polish (Phase 8)
```

### Within Each User Story

- Тесты ДОЛЖНЫ быть написаны и ПАДАТЬ до реализации
- Models → Services → Endpoints → UI
- Core implementation → Integration

### Parallel Opportunities

- T002, T003 — параллельно (конфиг backend/frontend)
- T006, T007 — параллельно (схемы и сервис)
- T009, T010, T011 — параллельно (тесты US1)
- T014, T015, T016 — параллельно (frontend компоненты)
- T026, T027, T028 — параллельно (тесты US4)
- T034, T035, T036 — параллельно (security)
- T038, T039, T042 — параллельно (документация)

---

## Parallel Example: User Story 1

```bash
# После завершения Phase 2, запустить параллельно:

# Тесты (должны падать):
T009: Unit тест верификации подписи
T010: Integration тест endpoint
T011: Unit тест TelegramLoginButton

# Frontend компоненты (независимые файлы):
T014: TelegramLoginButton компонент
T015: API клиент telegramAuth
T016: Хук useTelegramAuth
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. ✅ Complete Phase 1: Setup
2. ✅ Complete Phase 2: Foundational (CRITICAL)
3. ✅ Complete Phase 3: User Story 1 (Вход)
4. ✅ Complete Phase 4: User Story 2 (Регистрация)
5. **STOP and VALIDATE**: Тест входа через Telegram работает
6. Deploy/demo если готово

### Incremental Delivery

1. Setup + Foundational → База готова
2. US1 + US2 → Вход и регистрация через Telegram → **MVP!**
3. US3 → Выход → Deploy/Demo
4. US4 → Связывание → Deploy/Demo
5. Security + Polish → Финальный релиз

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 43 |
| **Phase 1 (Setup)** | 3 |
| **Phase 2 (Foundational)** | 5 |
| **US1 (Вход)** | 10 |
| **US2 (Регистрация)** | 5 |
| **US3 (Выход)** | 2 |
| **US4 (Связывание)** | 8 |
| **Security** | 5 |
| **Polish** | 5 |
| **Parallel Opportunities** | 24 tasks marked [P] |
| **MVP Scope** | US1 + US2 (18 tasks) |

---

## Notes

- [P] = разные файлы, нет зависимостей — можно параллельно
- [Story] = привязка к user story для трассировки
- Каждая user story независимо тестируема
- Коммит после каждой задачи или логической группы
- Остановка на любом checkpoint для валидации
