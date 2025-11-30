# Implementation Plan: Telegram Login

**Branch**: `013-telegram-login` | **Date**: 2024-11-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/013-telegram-login/spec.md`

## Summary

Реализация авторизации и регистрации пользователей через Telegram Login Widget как третьего провайдера OAuth наряду с Google и email/password. Техническое решение основано на официальном Telegram Login Widget API с серверной верификацией HMAC-SHA256 подписи. Новые пользователи получают роль `pending` согласно 007-user-approval.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.x (frontend)  
**Primary Dependencies**: FastAPI, SQLAlchemy, React 18, Vite, TailwindCSS  
**Storage**: PostgreSQL 15+ (новые поля: telegram_id, telegram_username)  
**Testing**: pytest (backend), Playwright/Vitest (frontend)  
**Target Platform**: Linux server (Ubuntu 22.04), Web browser (Chrome, Firefox, Safari, Telegram WebView)  
**Project Type**: web (backend + frontend)  
**Performance Goals**: API response <200ms p95, Widget load <500ms  
**Constraints**: Rate limit 5 req/hour/IP, auth_date max 5 min, CAPTCHA after 3 attempts  
**Scale/Scope**: Существующая база пользователей ~100, ожидаемый рост через Telegram

## Constitution Check

*GATE: ✅ PASSED — Все принципы соблюдены*

1. **✅ SSoT подтверждён (Принцип I)** — Спецификация `spec.md` на русском содержит:
   - 18 независимых функциональных требований (FR-001..FR-018)
   - 3 нефункциональных требования (NFR-001..NFR-003)
   - 5 измеримых критериев успеха
   - Ссылки на связанные спецификации: 002-google-auth, 004-email-password-auth, 007-user-approval

2. **✅ Структура репозитория соблюдена (Принцип II)** — Артефакты фичи:
   - `specs/013-telegram-login/` — все документы планирования
   - Тесты будут в `backend/tests/` и `frontend/tests/`
   - Временные файлы — в `.internal/`

3. **✅ Тесты и наблюдаемость спланированы (Принцип III)** — Запланированы:
   - pytest: `test_telegram_auth.py` (верификация подписи, rate limiting, создание пользователя)
   - Playwright: `telegram-login.spec.ts` (widget интеграция, popup flow)
   - Vitest: `TelegramLoginButton.test.tsx` (unit тесты компонента)

4. **✅ Документация и локализация покрыты (Принцип IV)** — План включает:
   - Обновление `docs/features/` с описанием Telegram auth
   - Обновление `ai-instructions/` при необходимости
   - Выполнение `npm run docs:validate` перед merge

5. **✅ Секреты и окружения учтены (Принцип V)** — Новые переменные:
   - `TELEGRAM_BOT_TOKEN` — добавляется в `template.env` с плейсхолдером
   - `TELEGRAM_BOT_USERNAME` — добавляется в `template.env`
   - `TELEGRAM_AUTH_MAX_AGE=300` — с дефолтом
   - `TELEGRAM_AUTH_RATE_LIMIT_PER_HOUR=5` — с дефолтом
   - `TELEGRAM_AUTH_CAPTCHA_THRESHOLD=3` — с дефолтом
   - `TURNSTILE_SITE_KEY` — Cloudflare Turnstile site key
   - `TURNSTILE_SECRET_KEY` — Cloudflare Turnstile secret key
   - Генерация `.env` через существующий template-based процесс

## Project Structure

### Documentation (this feature)

```text
specs/013-telegram-login/
├── spec.md              # Спецификация (18 FR, 3 NFR)
├── plan.md              # Этот файл
├── research.md          # ✅ Исследование Telegram Login Widget API
├── data-model.md        # ✅ Модель данных + Pydantic + миграция
├── quickstart.md        # ✅ Инструкции по настройке
├── contracts/           # ✅ OpenAPI контракты
│   └── telegram-auth.openapi.yaml
├── checklists/
│   └── requirements.md  # ✅ Чеклист требований
└── tasks.md             # ⏳ Будет создан /speckit.tasks
```

### Source Code (repository root)

```text
# Web application structure (backend + frontend)

backend/
├── src/
│   ├── models/
│   │   └── user.py              # Добавление telegram_id, telegram_username
│   ├── services/
│   │   ├── auth_service.py      # Расширение для Telegram
│   │   └── telegram_auth_service.py  # НОВЫЙ: верификация подписи
│   ├── api/
│   │   └── auth/
│   │       └── telegram.py      # НОВЫЙ: endpoints /auth/telegram/*
│   └── schemas/
│       └── telegram_auth.py     # НОВЫЙ: Pydantic schemas
├── tests/
│   └── test_telegram_auth.py    # НОВЫЙ: unit + integration тесты
└── alembic/
    └── versions/
        └── xxx_add_telegram_auth_fields.py  # НОВАЯ миграция

frontend/
├── src/
│   ├── components/
│   │   └── TelegramLoginButton.tsx  # НОВЫЙ: компонент кнопки
│   ├── pages/
│   │   └── LoginPage.tsx            # Модификация: добавить TelegramLoginButton
│   ├── services/
│   │   └── telegramAuth.ts          # НОВЫЙ: API клиент
│   └── hooks/
│       └── useTelegramAuth.ts       # НОВЫЙ: хук для авторизации
└── tests/
    ├── components/
    │   └── TelegramLoginButton.test.tsx  # НОВЫЙ: unit тест
    └── e2e/
        └── telegram-login.spec.ts        # НОВЫЙ: E2E тест
```

**Structure Decision**: Используется структура Web application — backend и frontend раздельные проекты с собственными директориями тестов. Новые файлы добавляются в существующую структуру согласно принятым соглашениям.

## Complexity Tracking

> Нарушений Constitution Check нет — таблица пуста

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Artifacts Created

| Artifact | Status | Description |
|----------|--------|-------------|
| `spec.md` | ✅ | Спецификация с 18 FR, 3 NFR |
| `research.md` | ✅ | Исследование Telegram Login Widget |
| `data-model.md` | ✅ | Модель данных + Pydantic + миграция |
| `contracts/telegram-auth.openapi.yaml` | ✅ | OpenAPI 3.0 контракты |
| `quickstart.md` | ✅ | Инструкции по настройке |
| `checklists/requirements.md` | ✅ | Чеклист требований |
| `tasks.md` | ⏳ | Создаётся командой `/speckit.tasks` |

## Dependencies & Integrations

### Зависимости от существующих спецификаций:

- **002-google-auth** — Переиспользование AuthService.get_or_create_user
- **004-email-password-auth** — Общая модель User, JWT создание
- **007-user-approval** — Роль `pending` для новых пользователей

### Новые зависимости (не требуют установки):

- Telegram Login Widget — подключается через `<script>` (CDN)
- Криптография — стандартные Python `hashlib`, `hmac`

## Security Considerations

1. **Подпись**: Верификация HMAC-SHA256 с bot token как secret
2. **Время жизни**: auth_date не старше 5 минут (защита от replay)
3. **Rate limiting**: 5 попыток/час на IP через slowapi
4. **CAPTCHA**: Cloudflare Turnstile после 3 неудачных попыток за 10 минут (TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY)
5. **Логирование**: Подозрительная активность логируется для анализа

## Next Steps

1. Выполнить `/speckit.tasks` для создания tasks.md
2. Начать реализацию с backend (endpoints, service, tests)
3. Продолжить frontend (component, hooks, tests)
4. Интеграционное тестирование
5. Обновить документацию в `docs/`
6. Выполнить `npm run docs:validate`
