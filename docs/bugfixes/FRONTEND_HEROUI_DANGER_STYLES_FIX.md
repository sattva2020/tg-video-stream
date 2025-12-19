# Исправление: отсутствовали стили HeroUI `danger` (точка «В эфире» была невидимой)

**Дата:** 2025-12-19  
**Автор:** Jarvis (GitHub Copilot)  
**Компонент:** `frontend` (TailwindCSS + HeroUI)

## Контекст
В UI требуется красная «точка» (live-индикатор «В эфире»). В DOM появлялись классы вида `bg-danger`/`text-danger`, но визуально индикатор оставался без окраски.

## Симптомы
- В инспекторе DOM видно `bg-danger`, но в итоговом `dist/assets/index-*.css` отсутствуют соответствующие правила.
- В результате dot/Badge не окрашивается в «danger».

## Причина
TailwindCSS не генерировал утилиты, используемые HeroUI, потому что:
- в `frontend/tailwind.config.js` не был подключён плагин HeroUI (`heroui()`);
- `content` не включал файлы `node_modules/@heroui/**/dist/**/*.{js,mjs}`, из-за чего Tailwind не «видел» классы, которые рендерит HeroUI.

## Решение
Обновлён `frontend/tailwind.config.js`:
- добавлен импорт `heroui` из `@heroui/react`;
- расширен `content` на `./node_modules/@heroui/**/dist/**/*.{js,mjs}`;
- подключён `plugins: [heroui()]`.

## Проверка
Локально:
- `npm run build` успешно собирает `frontend/dist`.
- В `dist/assets/index-*.css` присутствуют переменные и классы HeroUI, включая `--heroui-danger`, `text-danger` и `bg-danger`.

На VPS:
- Обновлён `frontend/dist` атомарной заменой.
- В `current/frontend/dist/assets/index-*.css` подтверждено наличие `--heroui-danger`.

## Затронутые файлы
- [frontend/tailwind.config.js](../../frontend/tailwind.config.js)
