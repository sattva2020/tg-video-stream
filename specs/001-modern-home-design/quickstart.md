# Quickstart — Современный лендинг

Этот документ описывает минимальные шаги для запуска/тестирования фичи локально.

## 1. Подготовьте окружение

1. `cd frontend`
2. `npm install` (если зависимости ещё не подтянуты)
3. Скопируйте `.env` → `.env.local` при необходимости (Vite использует переменные `VITE_*`). Лендинг сам по себе не требует новых секретов.

## 2. Запустите dev-сервер

```bash
cd frontend
npm run dev
```

DevServer поднимется на `http://localhost:5173`. Основная страница теперь `/`.

## 3. Проверка функционала

1. Откройте `/` — увидите hero-блок и кнопку "Вход".
2. Нажмите "Вход" → вы должны перейти на `/login` (существующая AuthPage3D).
3. Измените язык через переключатель — тексты hero/benefits/CTA обновляются без перезагрузки.
4. Сузьте окно до 280 px: CTA остаётся на экране, горизонтального скролла нет.
5. Отключите WebGL (Chrome devtools → Run command `WebGL` → Disable) или включите `prefers-reduced-motion` — фон переключится на poster/градиент.
6. В консоли DevTools выполните `window.__landingMetrics`, чтобы увидеть текущие метрики fps и причину fallback (значения обновляются при каждом рендере ZenScene).

## 4. Прогоните тесты

```bash
cd frontend
npx playwright test tests/e2e/landing/landing-cta.spec.ts \
  tests/e2e/landing/landing-benefits.spec.ts \
  tests/e2e/landing/landing-language.spec.ts \
  tests/e2e/landing/landing-autodetect.spec.ts \
  tests/e2e/landing/landing-responsive.spec.ts \
  tests/e2e/landing/landing-accessibility.spec.ts \
  tests/e2e/landing/landing-visuals.spec.ts \
  tests/e2e/landing/landing-visual-metrics.spec.ts
```

## 4.1 Сбор метрик визуального слоя

- После прогона `landing-visual-metrics.spec.ts` зафиксируйте вывод `window.__landingMetrics` (средний fps, `fallbackReason`, `fallbackLatencyMs`).
- Добавьте выдержку с датой/временем в этот файл (секция «Сбор метрик визуального слоя») при обновлении данных.

## 4.2 Lighthouse / TTI проверка

```bash
cd frontend
npm run test:lh
```

Скрипт автоматически собирает `npm run build`, поднимает `vite preview` и запускает Lighthouse для `/`. Отчёты (`.json` и `.html`) сохраняются в `.internal/lighthouse/landing-<timestamp>.{json,html}` и содержат значения TTI / perf score для приложений CI.

## 5. Production build

```bash
cd frontend
npm run build
```

После сборки убедитесь, что `dist/index.html` содержит ссылку на `landing-poster.webp` и что `dist/assets` включает новые изображения.

## 6. Обновление контейнера

1. `docker-compose build frontend`
2. `docker-compose up -d frontend`
3. Проверить `http://localhost:3000/`.

## 7. Документация

- Обновите `docs/development/dev-onboarding.md` (секция про фронтенд пути) ссылкой на новый лендинг и процесс локализации.
