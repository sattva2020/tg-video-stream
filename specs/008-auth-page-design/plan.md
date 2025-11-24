# Implementation Plan: Auth Page Design

**Branch**: `008-auth-page-design` | **Date**: 2025-11-24 | **Spec**: `specs/008-auth-page-design/spec.md`
**Input**: Feature specification + research for обновления UI/UX страницы авторизации и двухтемного dashboard-а.

**Note**: План заполняется через `/speckit.plan` и синхронизирован с веткой `008-auth-page-design`.

## Summary

Обновляем страницу авторизации и стартовые блоки dashboard-а под требования спецификации: визуальное соответствие лендингу, responsive до 320px и ниже, оформленные ошибки, обязательные две темы (светлая «parchment» и тёмная «ink night») с сохранением выбора и синхронным отображением в dashboard. Технически переносим типографику и палитру в единые дизайн-токены, используем Aceternity UI + Magic UI + Hero UI поверх Tailwind, лениво рендерим 3D-сцену и включаем fallback SVG. Обновляем OpenAPI контракт `/specs/008-auth-page-design/contracts/auth-ui.yaml`: 403/409 ответы должны включать обязательный `code` и `hint`, а также либо локализованный `message`, либо `message_key` (ключ локализации) — это покрывается pytest-проверками.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: TypeScript 5.4 + React 18 + Vite 5 (frontend), CSS custom properties для темизации.  
**Primary Dependencies**: TailwindCSS, React Three Fiber (3D фон), Aceternity UI, Magic UI, Hero UI, Zustand (state), i18next для текста.  
**Storage**: N/A — используем существующие API `/api/auth/*`.  
**Testing**: Playwright (desktop + mobile + extra-small 280px), Vitest (snapshots), pytest (API ошибки 403/409), Lighthouse CLI (accessibility/perf).
**Target Platform**: Современные браузеры + Telegram WebApp (mobile-first, min width 320px).  
**Project Type**: Web (frontend + связанный API).  
**Performance Goals**: SC-003 — TTI < 2 c на 4G, Accessibility score > 90, без горизонтального скролла @320px и 280px.  
**Constraints**: Dual-theme toggle (светлая/тёмная), fallback без WebGL, reuse landing fonts/colors, отсутствие блокирующих скриптов.  
**Scale/Scope**: Одна страница авторизации + приветственный блок dashboard-а, затрагивает 3-4 React компонента и UX-контракты.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** — `specs/008-auth-page-design/spec.md` содержит 4 независимые user stories, edge cases и метрики SC-001..006, что покрывает все требования для авторизации, responsive и dual-theme сценариев.  ✅
2. **Структура репозитория соблюдена (Принцип II)** — все артефакты план/исследование/контракты лежат в `specs/008-auth-page-design/`, временные данные храним в `.internal/`, кодовые правки ограничены `frontend/` (UI) и при необходимости `backend/src/api/auth.py` (локализация сообщений).  ✅
3. **Тесты и наблюдаемость спланированы (Принцип III)** — добавляем Playwright сценарии `frontend/tests/playwright/auth-page.spec.ts` для desktop/mobile/sub-320 и theme toggle, Vitest снапшоты компонент ошибок и карточек, Lighthouse CLI шаг в `npm run test:ui`, логи UI билдов уходят в `.internal/frontend-logs/`.  ✅
4. **Документация и локализация покрыты (Принцип IV)** — обновляем `docs/auth-page-ui.md` и `docs/development/frontend-theme.md`, фиксируем команды `npm run docs:validate && npm run docs:report`, текст только на русском.  ✅
5. **Секреты и окружения учтены (Принцип V)** — новые настройки темы не требуют секретов; любые будущие переменные (например, `VITE_THEME_DEFAULT`) сначала попадут в `template.env` и документируются в `ai-instructions/ENV_GENERATION_INSTRUCTIONS.md`.  ✅

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
frontend/
├── src/
│   ├── pages/
│   │   └── AuthPage3D.tsx            # основной экран + dual-theme toggle
│   ├── components/auth/
│   │   ├── AuthCard.tsx             # Aceternity/Magic UI карточки
│   │   ├── ErrorToast.tsx           # Hero UI toast + локализация
│   │   └── ThemeToggle.tsx          # переключение светлая/тёмная темы
│   ├── hooks/
│   │   └── useThemePreference.ts    # хранение выбора + prefers-color-scheme
│   ├── lib/api/
│   │   └── authClient.ts            # вызовы /api/auth/* c fetch/token
│   └── styles/
│       └── tokens.css               # ink/parchment + dark-night custom props
├── tests/
│   ├── playwright/
│   │   └── auth-page.spec.ts        # desktop/mobile + ошибки 403/409
│   └── vitest/
│       └── auth-card.spec.tsx       # снапшоты состояний и переключение тем
└── public/
  └── fallback/zen-scene.svg       # статический фон при отсутствии WebGL

backend/
└── src/api/auth.py                  # при необходимости локализация ответов

docs/
└── auth-page-ui.md                  # руководство по теме и тестам
```

**Structure Decision**: Используем двуслойную web-структуру (frontend + backend API). Основная работа в `frontend/src/pages|components|styles`, поддержка API сообщений — в `backend/src/api/auth.py` (возвращает `code` + `hint` и либо локализованный `message`, либо `message_key`), тесты — в `frontend/tests/{playwright,vitest}`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Нарушений принципов не требуется.
