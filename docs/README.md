# Документация проекта Telegram Video Broadcast

Добро пожаловать в документацию проекта **tg-video-stream** — системы для организации 24/7 видео-трансляций в Telegram.

---

## 📚 Структура документации

### Архитектура
- [**architecture/**](./architecture/) — архитектурные решения и диаграммы
  - Общая архитектура системы
  - Взаимодействие компонентов
  - Схемы данных
  - [**TELEGRAM_CALLS_API.md**](./architecture/TELEGRAM_CALLS_API.md) — документация Telegram Calls API, PyTgCalls, E2E шифрование

### Разработка
- [**development/**](./development/) — руководства для разработчиков
  - Настройка окружения
  - Code style и conventions
  - Процесс code review
  - [**RELEASE_METADATA_AND_SMOKE_TESTS.md**](./development/RELEASE_METADATA_AND_SMOKE_TESTS.md) — метаданные релиза и smoke-проверки деплоя

### Функциональность
- [**features/**](./features/) — описание функций системы
  - Расписание трансляций
  - Управление плейлистами
  - Система аутентификации
  - [**011-advanced-audio.md**](./features/011-advanced-audio.md) — транскодирование аудио и Playlist UI
  - [**telegram-auth.md**](./features/telegram-auth.md) — авторизация через Telegram Login Widget

### Бизнес-требования
- [**BUSINESS_REQUIREMENTS.md**](./BUSINESS_REQUIREMENTS.md) — бизнес-требования проекта
- [**PROJECT_AUDIT_REPORT.md**](./PROJECT_AUDIT_REPORT.md) — аудит и план улучшений

### Тестирование
- [**test-cases.md**](./test-cases.md) — тест-кейсы и сценарии
- [**bag-reports.md**](./bag-reports.md) — отчеты о багах

### UI/UX
- [**auth-page-ui.md**](./auth-page-ui.md) — дизайн страницы аутентификации

---

## 🚀 Быстрый старт

### Локальная разработка

```bash
# Клонирование репозитория
git clone <repository-url>
cd telegram

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate на Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Frontend
cd ../frontend
npm install
npm run dev
```

### Docker Compose

- Локальная разработка (полный стек: backend с hot-reload, frontend dev, db, redis, streamer, rust-transcoder, мониторинг):

```bash
docker compose -f docker-compose.local.yml up -d
```

- Порты локального стека: backend 8000, frontend 3000, redis 6379, postgres 5432, rust-transcoder 18090 (health: http://localhost:18090/health), alertmanager 19093.

- Полное docker-развёртывание (без hot-reload; включает мониторинг):

```bash
docker compose -f docker-compose.yml up -d
```

> На проде backend и streamer запускаются через systemd (см. ai-instructions/DEPLOYMENT_SYNC_RULE.md); docker-compose.yml используется для полного docker-стека или стендов.

---

## 🧪 Тестирование

### Backend

```bash
cd backend
pytest                          # Все тесты
pytest --cov=src               # С coverage
pytest tests/api/              # Только API тесты
```

### Frontend

```bash
cd frontend
npm run test:unit              # Unit тесты
npm run test:coverage          # С coverage
npm run test:ui                # E2E тесты (Playwright)
npm run storybook              # UI компоненты документация
```

---

## 📊 Coverage

| Компонент | Текущий | Цель | CI Threshold |
|-----------|---------|------|--------------|
| Backend   | ~43%    | 70%  | ✅ Настроено |
| Frontend  | TBD     | 60%  | ✅ Настроено |

Отчеты coverage генерируются в CI и доступны как артефакты.

---

## 🔗 Связанные ресурсы

- [README.md](../README.md) — главный README проекта
- [specs/](../specs/) — спецификации и планы развития
- [ai-instructions/](../ai-instructions/) — инструкции для AI-агентов
- [.internal/](../.internal/) — внутренние отчеты и логи

---

## 📝 Changelog

Изменения документируются в коммитах и в файле [OUTSTANDING_TASKS_REPORT.md](../OUTSTANDING_TASKS_REPORT.md).

---

*Последнее обновление: 2025-01-20*
