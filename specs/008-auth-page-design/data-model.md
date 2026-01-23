# Data Model: Auth Page Design

Фича не добавляет новых таблиц, но определяет фронтенд-сущности, необходимые для реализации требований.

## User (existing)

- **id**: UUID (readonly)
- **email**: string, используется в приветствии и fallback, берётся из `/api/users/me`
- **full_name**: string | null, выводится крупным шрифтом; если отсутствует, используем email
- **role**: `admin | user` — управляет видимостью CTA (например, «Перезапустить стрим»)
- **status**: `approved | pending | rejected` — определяет сообщения в модалках

## AuthFormState (frontend)

- **mode**: `login | register`
- **email**: string, валидация `Email`
- **password**: string, проверяем требования (>=12 символов, верхний/нижний регистр, число, спецсимвол)
- **isSubmitting**: boolean, показывает спиннер на кнопке
- **error**: `AuthError | null`

## AuthError (frontend)

- **code**: `conflict | pending | server | validation`
- **message**: локализованный текст
- **hint**: опционально, короткий совет/ссылка
- **severity**: `info | warning | danger` — влияет на цвет Magic UI `Alert`

## ThemeTokens

- **fontHeading**: `LandingSerif`
- **fontBody**: `LandingSans`
- **colorInkLight**: `#1E1A19`
- **colorParchmentLight**: `#F7E2C6`
- **colorInkDark**: `#E5D9C7`
- **colorNightSky**: `#0C0A09`
- **colorAccent**: `#B8845F`
- **spaces**: `base=4px` (используется для Tailwind custom scale)
- **transitions**: `ease-theme = 220ms ease-in-out` для плавного переключения тем

## ThemePreference (frontend)

- **current**: `light | dark`
- **system**: значение `prefers-color-scheme`
- **persistKey**: `tg-auth-theme`
- **toggle()**: переключает тему и обновляет CSS `data-theme`
- **listeners**: подписчики React (context/provider) и ThreeJS сцена (обновляет фон)

## Responsive Breakpoints

- **base**: 320px (узкие устройства) — стековая верстка
- **md**: 768px — двухколоночный layout (форма + вспомогательная панель)
- **xl**: 1280px — форма фиксированной ширины + декоративные блоки (CTA, social proof)
