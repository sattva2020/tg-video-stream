# FRONTEND_SCHEDULE_DASHBOARD_STYLE_FIX

**Дата:** 20.12.2025  
**Статус:** ✅ Исправлено и задеплоено  
**Компонент:** Frontend (`/schedule`)  

## Проблема
На странице `/schedule` в production визуально проявлялись «светлые/синие» поверхности и стили, которые не соответствовали тёмному референсу `/dashboard` (Dashboard V2). Из-за этого страница выбивалась из общей тёмной стилистики приложения.

## Причина
- В ряде мест использовались не-токеновые классы (например, `bg-*`, `text-default-*`, `ring-primary`), и дефолтные стили HeroUI для Tabs/Card.
- Это приводило к появлению «синих/светлых» поверхностей вместо токенов темы (`--color-surface`, `--color-panel`, `--color-border`, `--color-text`, `--color-text-muted`, `--color-accent`).

## Решение
Привели ключевые UI-элементы `/schedule` к dashboard-паттерну «panel»:
- Панель: `bg-[color:var(--color-panel)] + border + ring-1 ring-inset + shadow-black/5`.
- Для HeroUI Card: контур/тень вынесены во внешний wrapper, сама `Card` переведена в `bg-transparent shadow-none border-none` (устойчиво и предсказуемо в production).
- Tabs: `tabList` сделан `bg-transparent`, активный акцент использует `--color-accent`.

### Изменённые файлы (ключевые)
- frontend/src/pages/SchedulePage.tsx
- frontend/src/components/schedule/PlaylistManager.tsx
- frontend/src/components/schedule/ScheduleCalendar.tsx
- frontend/src/components/schedule/SlotEditorModal.tsx
- frontend/src/components/schedule/CopyScheduleModal.tsx

## Тестирование
Локально:
- `pnpm -C frontend test:unit` → **21 passed**, **217 passed**, **20 skipped**.
- `pnpm -C frontend build` → успешная сборка.

## Деплой
Использована каноническая release-based схема деплоя:
- Сборка фронтенда: `pnpm -C frontend build`
- Сборка артефакта: `bash scripts/build_artifact.sh` (формат `telegram-deploy-*.tar.gz`)
- Деплой на VPS: `bash scripts/deploy_to_remote.sh --skip-tests`

На сервере:
- Обновлён `/opt/tg_video_streamer/current` → новый релиз
- Nginx перезагружен (конфиг обновлён из артефакта)
- `tg_video_streamer` перезапущен
