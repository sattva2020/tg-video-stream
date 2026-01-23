# Производительность — auth-error TTI (инструменты и запуск)

Этот каталог содержит вспомогательные скрипты для измерения влияния показа ошибок авторизации на время до интерактивности (TTI) и поведение страницы auth.

Основной скрипт: `tests/perf/auth-error-tti.mjs` — запускает:

- сборку/preview фронтенда (по умолчанию `npm run preview` внутри `frontend/`).
- (опционально) запуск Playwright-сценария для создания контекста страницы; по умолчанию пропускается в CI через `SKIP_PLAYWRIGHT=1`.
- запуск Lighthouse (mobile, CPU slowdown 4×, 4G throttling) против двух ссылок: чистая страница auth и та же страница с `?perfError=conflict` — содержащая forced error state.
- сохранение артефактов: `baseline.report.json`, `baseline.report.html`, `error.report.json`, `error.report.html` и `summary.json`/`summary.md` в `.internal/frontend-logs/perf/${run_id}`.

Как запустить локально

1. Убедитесь, что зависимости установлены в корне репозитория (root):

```bash
npm ci
```

1. Запустить проверку (локально, dev сервер):

```bash
# старт dev сервера и LH измерения
USE_DEV_SERVER=1 SKIP_PLAYWRIGHT=1 npm run perf:auth-errors
```

1. Запуск без dev-сервера — preview (предварительно выполнить `npm run build` в `frontend`):

```bash
# build + preview + lighthouse
USE_DEV_SERVER=0 SKIP_PLAYWRIGHT=1 npm run perf:auth-errors
```

Переменные окружения (опционально):
- `AUTH_BASELINE_URL` — адрес baseline (по умолчанию <http://127.0.0.1:4173/auth>)
- `AUTH_ERROR_URL` — адрес страницы с ошибкой (по умолчанию добавляется ?perfError=conflict)
- `MAX_TTI_MS` — порог TTI (default 2000)
- `MAX_TTI_DELTA_MS` — порог ΔTTI (default 100)
- `SKIP_PLAYWRIGHT` — если =1, пропустить Playwright шаг
- `USE_DEV_SERVER` — если =1, запускается `npm run dev`, иначе — `npm run preview`

Интерпретация результатов

- `baseline.report.json` / `error.report.json` содержит подробные метрики Lighthouse. Ищите `audits.interactive.numericValue` (TTI) и `audits['largest-contentful-paint'].numericValue` (LCP).
- `summary.json` агрегирует TTI, ΔTTI и пороги. `summary.md` — человекочитаемая сводка.

Рекомендации

- Прогонять скрипт в CI (headless environment) для стабильных данных — dev-серверы и локальные машины дают нестабильные и длительные значения.
- Если TTI >> порога, запустить профайлеры Webpack/Vite, проверить bundle size, lazy-loading, сторонние скрипты и heavy assets (3D сцены). Пометить задачи на оптимизацию в `OUTSTANDING_TASKS_REPORT.md`.

Формат артефактов в CI

- CI сохраняет артефакты в `.internal/frontend-logs/perf/${run_id}` и прикладывает их к job `frontend-perf`.

---
Автор: команда разработки
Дата: 2025-11-26