# Data Model — Landing Page

## Overview
Фича не добавляет БД-сущностей, но вводит чёткие UI-модели и текстовые ресурсы. Ниже описаны структуры, которые должны существовать в коде (TypeScript интерфейсы) и/или в i18n словарях.

## Entities

### HeroContent
| Field | Type | Description |
|-------|------|-------------|
| `labelKey` | `string` | i18n ключ для мини-лейбла (например, `hero_label`). |
| `titleKey` | `string` | Основной заголовок (мультилингвальный, например, `hero_title`). |
| `subtitleKey` | `string` | Подзаголовок/объяснение ценности (`hero_subtitle`). |
| `benefits` | `BenefitItem[]` | Список преимуществ, связанных с локализацией. |
| `cta` | `CTA` | Конфигурация единственной кнопки «Вход».

### BenefitItem
| Field | Type | Description |
|-------|------|-------------|
| `icon` | `ReactNode | string` | Имя иконки или компонент. Должен иметь aria-label. |
| `labelKey` | `string` | Ключ перевода текста преимущества. |
| `metricKey?` | `string` | Необязательный ключ для числового значения/метрики (например, `hero_metric_slots`).

### CTA
| Field | Type | Description |
|-------|------|-------------|
| `labelKey` | `string` | Ключ локализованной подписи ("enter"). |
| `href` | `"/login" | "/register"` | Куда ведёт кнопка (из спецификации — `/auth`, используем `/login`). |
| `trackingId` | `string` | Идентификатор события аналитики (например, `landing_enter_click`). |
| `styleVariant` | `'glass' | 'solid'` | Визуальный стиль (по умолчанию `glass`).

### LanguageOption
| Field | Type | Description |
|-------|------|-------------|
| `code` | `"en" | "ru" | "uk" | "de"` | Код языка, уже поддерживаемый i18n. |
| `label` | `string` | Отображаемое название (тоже в i18n). |
| `isDefault` | `boolean` | Флаг, совпадает ли с autodetect языком.

### VisualAsset
| Field | Type | Description |
|-------|------|-------------|
| `type` | `'webgl' | 'poster' | 'gradient'` | Используемая прослойка. |
| `source` | `string` | Путь к ассету или имя компонента. |
| `enabled` | `boolean` | Можно ли показывать при текущих условиях (prefers-reduced-motion, WebGL support). |
| `intensity` | `number` | Для R3F освещение/отражения (0..1). |
| `fallbackColor` | `string` | CSS-переменная, используемая при отключении всех ассетов.

## Relationships
- `HeroContent` агрегирует `BenefitItem[]` и `CTA`.
- `LanguageOption[]` используется в переключателе и влияет на отображение `HeroContent`/`BenefitItem` строк.
- `VisualAsset` выбранный слой зависит от возможностей клиента (feature detection) и влияет только на фоновые компоненты, но не на текстовую структуру.

## Validation Rules
- Должно существовать ровно **1 CTA**. Любая попытка добавить второй должна отлавливаться линтером/ревью.
- `benefits.length` ∈ [3,4]. Меньше — недостаточно ценности, больше — перегружает экран.
- Каждая `LanguageOption` должна иметь перевод для всех ключей `hero_*`, иначе fallback → en.
- Если `VisualAsset.type === 'webgl'`, должен существовать `poster` вариант для static fallback.
