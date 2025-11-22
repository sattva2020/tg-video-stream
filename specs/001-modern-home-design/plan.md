# Implementation Plan: Современный лендинг Telegram 24/7 Video Streamer

**Branch**: `001-modern-home-design` | **Date**: 2025-11-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-modern-home-design/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Создаём публичный лендинг (маршрут `/`), который ведёт гостя в экосистему "Telegram 24/7 Video Streamer": hero-блок с градиентом `brand-glow`, новой сценой `ZenScene`, локализованными текстами (en/ru/uk/de) и единственной кнопкой "Вход" → `/login`. Требуется автодетект языка по `Accept-Language`, мгновенная ручная смена языка и стабильная деградация визуального слоя.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: TypeScript 5.x + React 18 (Vite toolchain, Node 20 LTS)  
**Primary Dependencies**: Tailwind CSS, React Three Fiber + Drei, i18next (с `Accept-Language` детектором), Framer Motion (existing), Vite build system  
**Storage**: N/A (статические ресурсы, локальные JSON/i18n)  
**Testing**: Playwright e2e (frontend/tests/e2e) + потенциально Vite preview/Lighthouse; ручные визуальные тесты  
**Target Platform**: Web (desktop + mobile browsers, Nginx container)  
**Project Type**: Web (frontend SPA + backend API, но фича затрагивает только `frontend/`)  
**Performance Goals**: Hero блок и CTA полностью отображаются ≤2 c на 3G (из спецификации); визуальная сцена удерживает ≥45 fps при анимации 10–15с циклом, fallback включается ≤0.5 c при снижении возможностей; graceful degradation на слабых устройствах  
**Constraints**: Единственная кнопка CTA, адаптивность 320px–4K, WCAG AA контраст, fallback без WebGL, использовать существующую i18n матрицу + обязателен fallback на en для каждого ключа преимуществ  
**Scale/Scope**: Один лендинговый экран внутри `frontend/src/pages`, охватывающий 4 языка и общий визуальный фон

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

1. **SSoT подтверждён (Принцип I)** — спецификация и план на русском, содержат независимые пользовательские истории и измеримые success criteria. Все артефакты хранятся в `specs/001-modern-home-design/` и ссылаются на ветку `001-modern-home-design`. ✅
2. **Структура репозитория сохранена (Принцип II)** — работа ограничена `frontend/` и `specs/`, временные ассеты прописаны как `frontend/public/assets/landing/`, мусорные файлы направляются в `.internal/`. ✅
3. **Тесты и наблюдаемость до кода (Принцип III)** — план и tasks закладывают Playwright e2e (CTA, локализация, визуалы) и smoke проверки для ZenScene; перед внедрением дополним перф/доступность метриками. ✅
4. **Документация и локализация (Принцип IV)** — Phase 6 включает обновление `docs/development/dev-onboarding.md`, README и quickstart; все тексты и строки i18n добавляются в существующие bundles. ✅
5. **Секреты и окружения (Принцип V)** — новая функциональность не вводит секретов, переменные окружения останутся в `template.env`; deploy-скрипты не изменяются. ✅

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
backend/
├── src/
│   ├── api/
│   ├── auth/
│   ├── services/
│   └── models/
└── tests/

frontend/
├── src/
│   ├── pages/          # AuthPage3D, новый LandingPage
│   ├── components/     # Hero, LanguageSwitcher, 3D/visual элементы
│   ├── api/
│   ├── lib/
│   └── i18n.ts
├── public/
├── scripts/
└── tests/
  └── e2e/            # Playwright сценарии

docs/
└── development/
  └── dev-onboarding.md
```

**Structure Decision**: Используем существующую двухсервисную структуру `backend/` + `frontend/`, но текущая фича затрагивает исключительно `frontend/src/pages` и связанные `components/`, `lib/`, `i18n.ts`. В рамках фичи добавляем новую 3D-сцену `frontend/src/components/landing/ZenScene.tsx`, ассеты в `frontend/public/assets/landing/`, а также хук `useLandingLocale` для чтения `Accept-Language`. Плейсменты ассетов/тестов следуем текущим путям (`frontend/public`, `frontend/tests/e2e`). Документация по фиче хранится в `specs/001-modern-home-design/*`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
