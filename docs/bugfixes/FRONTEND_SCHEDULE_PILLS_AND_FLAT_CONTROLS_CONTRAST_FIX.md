# FRONTEND: /schedule — «пиллы» вкладок и контраст flat-кнопок

**Дата:** 20.12.2025  
**Компонент:** Frontend (`/schedule`)  

## 🔴 Проблема
На странице `/schedule` в тёмной теме часть элементов управления оставалась «серой»/низкоконтрастной (flat-кнопки, стрелки навигации, кнопки в модалках). Также вкладки визуально не соответствовали «пиллам» в стиле Dashboard V2.

## 🔄 Шаги воспроизведения
1. Открыть админку и перейти на `/schedule` в тёмной теме.
2. Обратить внимание на:
   - вкладки (вид «underlined», не «пиллы»);
   - flat-кнопки в календаре (стрелки, «Сегодня», «Шаблон», «Копировать»);
   - flat-кнопки в модалках (например, «Отмена» в окне копирования расписания и в редакторе слота).
3. Ожидаемое поведение: элементы читаемы, контрастные, вкладки выглядят как «пиллы».
4. Фактическое поведение: часть controls выглядит приглушённо/серо.

## 🔍 Корневая причина
1. Компоненты HeroUI с `variant="flat"` в тёмной теме не всегда дают достаточный контраст по умолчанию — в ряде мест отсутствовали явные классы для текста/фона/бордера на дизайн-токенах.
2. Вкладки были реализованы как HeroUI `Tabs variant="underlined"`, что визуально не совпадает с выбранным паттерном Dashboard V2 («пиллы»).

## ✅ Решение
1. Введён единый паттерн оформления flat-кнопок (на токенах темы):

```ts
const flatControlClassName =
  'text-foreground bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-hover)] hover:border-[color:var(--color-border-strong)] transition-colors';
```

2. Этот класс применён к проблемным `variant="flat"` кнопкам на `/schedule`:
   - в шапке страницы;
   - в календаре (стрелки, «Сегодня», «Шаблон», «Копировать»);
   - в модалках расписания (`CopyScheduleModal`, `SlotEditorModal`, `PlaylistManager`).

3. Вкладки `/schedule` переведены на кастомные «пиллы» (кнопки) вместо `Tabs/Tab`:
   - активное состояние: accent-обводка + мягкая подложка;
   - неактивное состояние: surface-muted + border.

## 📁 Изменённые файлы
- [frontend/src/pages/SchedulePage.tsx](../../frontend/src/pages/SchedulePage.tsx) — вкладки-пиллы вместо `Tabs/Tab`, контрастные flat-кнопки в шапке.
- [frontend/src/components/schedule/ScheduleCalendar.tsx](../../frontend/src/components/schedule/ScheduleCalendar.tsx) — единый стиль для стрелок/«Сегодня»/кнопок «Шаблон» и «Копировать».
- [frontend/src/components/schedule/CopyScheduleModal.tsx](../../frontend/src/components/schedule/CopyScheduleModal.tsx) — контрастные flat-кнопки (быстрые действия, навигация месяцев, «Отмена»).
- [frontend/src/components/schedule/SlotEditorModal.tsx](../../frontend/src/components/schedule/SlotEditorModal.tsx) — контрастные flat-кнопки «Отмена».
- [frontend/src/components/schedule/PlaylistManager.tsx](../../frontend/src/components/schedule/PlaylistManager.tsx) — контрастная flat-кнопка «Отмена» в редакторе плейлиста.

## 🧪 Тестирование
- Локальная сборка фронтенда: `pnpm build` (успешно).
- Ручная проверка:
  - `/schedule`: вкладки выглядят как «пиллы», контраст элементов управления в календаре.
  - Модалки: «Копировать расписание», «Новый слот», редактор плейлиста — кнопки `variant="flat"` читаемы в тёмной теме.

## 🚀 Статус
- [x] Исправление реализовано
- [x] Задеплоено на VPS
- [x] Протестировано на VPS
