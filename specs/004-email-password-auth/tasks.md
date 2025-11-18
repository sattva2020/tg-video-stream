# Tasks: Email & Password Authentication

Ниже — подробный набор задач (phased tasks) для реализации функциональности Email/Password аутентификации.

## Фаза 0 — Исследование (Research)
- [ ] Проверить текущую реализацию пользователей (`backend/src/models/user.py`) и схемы БД
- [ ] Подобрать библиотеку для хеширования паролей (рекомендации: argon2-cffi или passlib[bcrypt])
- [ ] Проверить требования к отправке почты (SMTP / сервис типа SendGrid) и добавить dev-режим (логирование токенов)
- [ ] Обновить `specs/004-email-password-auth/data-model.md` при необходимости

## Фаза 1 — Дизайн и миграции (Design & Data model)
- [ ] Добавить поле `hashed_password` (nullable) в модель пользователя
- [ ] Создать Alembic migration для добавления поля `hashed_password`
- [ ] Спланировать поведение для существующих пользователей (backfill / оставить NULL)
- [ ] Обновить OpenAPI контракт (`specs/004-email-password-auth/contracts/openapi.yml`) — конечные точки auth

## Фаза 2 — Бэкенд: сервисы и API
- [ ] Добавить зависимость в `backend/requirements.txt` (например `passlib[bcrypt]` или `argon2-cffi`) и зафиксировать версии
- [ ] Реализовать `backend/src/services/auth_service.py`:
  - [ ] Функция hash_password(password) → hashed
  - [ ] Функция verify_password(plain, hashed) → bool
  - [ ] Функции для генерации/проверки токенов сброса пароля (использовать itsdangerous)
- [ ] Добавить роуты в `backend/src/api/auth.py`:
  - [ ] POST /api/auth/register
  - [ ] POST /api/auth/login
  - [ ] POST /api/auth/password-reset/request
  - [ ] POST /api/auth/password-reset/confirm
  - [ ] GET /api/auth/me
- [ ] Обновить `backend/src/main.py` для регистрации маршрутов и middlewares (rate limiting)

## Фаза 3 — Тесты (Unit & Integration)
- [ ] Написать unit-тесты для `auth_service` (pytest)
- [ ] Написать API-интеграционные тесты для эндпоинтов auth (FastAPI TestClient)
- [ ] Добавить тест для edge-cases: слабые пароли, повторная регистрация, неверный токен сброса

## Фаза 4 — Фронтенд
- [ ] Добавить страницы/компоненты: Login, Register, PasswordResetRequest, PasswordResetConfirm
- [ ] Реализовать клиентские вызовы в `frontend/src/services/auth.ts` (fetch/axios)
- [ ] Сохранение JWT / storageState (если используется) и редирект после логина
- [ ] Написать простые E2E тесты (Playwright) для happy-path

## Фаза 5 — Развёртывание и безопасность
- [ ] Добавить переменные окружения (JWT_SECRET, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
- [ ] Настроить отправку писем в staging (dev-mode: логирование токенов)
- [ ] Ручное тестирование и smoke тесты (регистрация, вход, сброс пароля)
- [ ] Обновить README и docs (quickstart)

## Acceptance Criteria
- [ ] Регистрация пользователя через email создает запись с `hashed_password`
- [ ] Вход с корректными учетными данными возвращает валидный JWT
- [ ] Флоу сброса пароля выдаёт токен и позволяет сменить пароль
- [ ] Существующая Google OAuth интеграция не ломается и оба механизма работают параллельно

## Optional / Stretch
- [ ] Email verification (подтверждение почты при регистрации)
- [ ] Rate-limiting / блокировка по IP после N неудачных попыток
- [ ] MFA (TOTP) как следующий шаг

---

Если всё ок — я закоммичу файл на текущую ветку `004-email-password-auth-impl` и запушу изменения. Напишите `ok`, если можно продолжать, или `edit` + краткие правки к содержимому.
