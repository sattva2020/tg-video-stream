# FRONTEND_VENDOR_REACT_CHUNK_CYCLE_FIX

## 🔴 Проблема
После деплоя главная страница показывала пустой экран. В консоли браузера фиксировалась ошибка:

```
TypeError: Cannot read properties of undefined (reading 'useState')
```

## 🔄 Шаги воспроизведения
1. Открыть https://sattva-streamer.top/
2. Видим пустую страницу без контента.
3. В консоли появляется ошибка `Cannot read properties of undefined (reading 'useState')`.

## 🔍 Корневая причина
Ручное разбиение чанков в Vite разделяло `react` и `use-sync-external-store` на разные чанки:
- `vendor-react` импортировал зависимости из `vendor-misc`.
- `vendor-misc` импортировал `react` обратно.

Из‑за циклической зависимости между чанками экспорт React не успевал инициализироваться, и `useState` читался у `undefined`.

## ✅ Решение
Упрощено правило `manualChunks`: все зависимости из `node_modules` собираются в один общий чанк `vendor`, чтобы полностью исключить циклические зависимости между vendor-чанками.

## 📁 Изменённые файлы
- [frontend/vite.config.ts](../../frontend/vite.config.ts) — уточнён список пакетов React-экосистемы для `vendor-react`.

## 🧪 Тестирование
1. Сборка фронтенда и деплой.
2. Открыть https://sattva-streamer.top/
3. Убедиться, что контент отображается и в консоли нет ошибки `useState`.

## 🚀 Статус
- [x] Исправление реализовано
- [ ] Задеплоено на VPS
- [ ] Протестировано

Дата: 2026-01-22
