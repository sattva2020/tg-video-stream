# Документация по UI страницы авторизации

## Содержание

- [Назначение](#назначение)
- [Дизайн-токены и типографика](#дизайн-токены-и-типографика)
- [Компоненты и ответственность](#компоненты-и-ответственность)
- [Скриншоты и визуальные артефакты](#скриншоты-и-визуальные-артефакты)
- [Процедура валидации визуального соответствия](#процедура-валидации-визуального-соответствия)

## Назначение

Эта страница описывает, как реализована и проверяется визуальная часть авторизации по требованиям `specs/008-auth-page-design/spec.md`. Фронтенд обязан повторять эстетику лендинга ZenScene: фон из 3D-сцены, шрифты LandingSans/Serif и палитра «чернила/пергамент». Документ служит источником истины для дизайнеров, разработчиков и тестировщиков: здесь зафиксированы токены, состав компонентов и шаги проверки.

## Дизайн-токены и типографика

Все значения определены в `frontend/src/styles/tokens.css` и подключаются в Tailwind (`tailwind.config.js`) и 3D-сцене. Таблица ниже помогает сверять тему с макетом лендинга.

| Токен | CSS custom property | Светлая тема | Тёмная тема | Использование |
|-------|---------------------|--------------|-------------|---------------|
| Font Heading | `--font-heading` | LandingSerif | LandingSerif | Заголовки в `AuthCard`, Dashboard preview |
| Font Body | `--font-body` | LandingSans | LandingSans | Основной текст, кнопки |
| Ink | `--color-ink-light` / `--color-ink-dark` | `#1E1A19` | `#E5D9C7` | Основной текст, иконки |
| Parchment | `--color-parchment-light` | `#F7E2C6` | — | Фон карточек и CTA |
| Night Sky | `--color-night-sky` | — | `#0C0A09` | Фон тёмной темы, ZenScene |
| Accent | `--color-accent` | `#B8845F` | `#B8845F` | Border/CTA, chipы статуса |
| Transition | `--transition-theme` | `220ms ease-in-out` | `220ms ease-in-out` | Анимация hover и переключения тем |

Дополнительно:

- `data-theme="light|dark"` навешивается на `html`, чтобы компоненты Hero UI читали токены.
- Tailwind spacing переопределён так, чтобы `space-1 == 4px` (см. `data-model.md`, раздел Responsive Breakpoints).

## Компоненты и ответственность

### `frontend/src/components/auth/AuthCard.tsx`

- Карточка авторизации/регистрации на основе Aceternity+Magic UI.
- Использует токены через классы `text-[var(--color-ink-light)]`, tabs/CTA наследуют LandingSans/Serif.
- Встроенный Google CTA стилизован под тёмный текст поверх пергамента.
- При ошибке placeholder блоков используется тема `ink/parchment`, без переключателя (US1 scope).

### `frontend/src/components/dashboard/HeroPanel.tsx`

- Отрисовывает приветствие и стат-блоки из лендинга (ранее `DashboardPreview`).
- Поддерживает светлую и тёмную темы, автоматически переключая цвета фона и текста.
- Цвет полос прогресса синхронизирован с `--color-accent`, текстовые блоки зеркалят шрифты LandingSans/Serif.
- Компонент используется справа от формы на десктопе, а на мобильных уходит под неё.

### `frontend/src/components/auth/ThemeToggle.tsx`

- Кнопка переключения темы (Солнце/Луна).
- Использует `useThemePreference` для управления состоянием.
- Расположена в заголовке страницы.

### `frontend/src/pages/AuthPage3D.tsx`

- Собирает сцену: фон `ZenScene`, `AuthCard`, `HeroPanel`, `ThemeToggle`.
- Поддерживает переключение тем (светлая/тёмная) с сохранением выбора в `localStorage`.
- Query `?banner=` позволяет включать маркетинговые сообщения, стилизованные в тех же цветах.

### Дополнительные элементы

- `frontend/src/styles/tokens.css` — единственный источник значений цвета/шрифтов.
- `frontend/src/hooks/useThemePreference.ts` управляет темой (light/dark) и синхронизирует её с `document.documentElement.dataset.theme`.

## Статусы ошибок и локализация

Система ошибок авторизации использует структурированный формат, согласованный с `specs/008-auth-page-design/contracts/auth-ui.yaml`:

- Обязательные поля: `code` и `hint`.
- Текст ошибки может приходить в двух формах:
	- `message` — если сервер локализовал текст для запрошенного языка (Accept-Language) — фронтенд показывает его напрямую.
	- `message_key` — ключ локализации (например `auth.email_registered`) — фронтенд резолвит через i18next и показывает перевод для текущего языка.

Для этой фичи поддерживаем минимум `ru` и `en`. Тесты покрывают оба сценария: когда сервер возвращает `message` и когда возвращает `message_key`.

Примеры ответов сервера (403/409):

```json
{ "code": "conflict", "hint": "email_exists", "message_key": "auth.email_registered" }
```

или

```json
{ "code": "conflict", "hint": "email_exists", "message": "Пользователь с таким email уже существует" }
```


## Скриншоты и визуальные артефакты

Чтобы доказать соответствие лендингу (SC-001), сохраняем актуальные скриншоты в `docs/img/auth-page/`:

1. **`auth-page-light.png`** — вид при `width=1440`, показывает 3D фон + форму + dashboard preview.
2. **`auth-card-mobile.png`** — вид при `width=390`, подтверждает, что токены и типографика сохраняются на мобильном.

Процесс обновления:

1. `cd frontend && npm run dev`.
2. Открыть `http://localhost:5173/auth?forceStatic=0` в Chrome, включить нужный viewport через DevTools.
3. Сделать full-page screenshot, сохранить по именам выше и положить в `docs/img/auth-page/` (каталог добавь в git, но сами PNG не коммить в .md).
4. В описании PR приложить ссылки на новые PNG или на Playwright артефакты (`frontend/logs/playwright-theme/`).

## Процедура валидации визуального соответствия

1. **Vitest снапшоты** — `cd frontend && npx vitest run tests/vitest/auth-card.spec.tsx`. Тест фиксирует classes/tokens для светлой темы.
2. **Playwright тема** — `npx playwright test tests/playwright/auth-page.spec.ts --grep theme`. Скрипт проверяет шрифты/цвета формы и preview.
3. **Ручная сверка** — сравнить актуальные скриншоты с лендингом в Figma (`Landing Auth v3`). Фокус на совпадении `LandingSerif` заголовков и цветов `#F7E2C6`/`#1E1A19`.
4. **Логи** — результаты тестов складываются в `frontend/logs/` (см. `T003`), файлы добавляем в PR как артефакты, но не коммитим.

При расхождениях обновляем токены в `tokens.css`, прогоняем тесты и публикуем свежие скриншоты.
