# AI Instructions для проекта Telegram Video Broadcast

Этот документ содержит инструкции для AI-агентов (GitHub Copilot, Claude и др.) при работе с проектом.

---

## 📁 Структура проекта

```
telegram/
├── backend/           # FastAPI backend (Python 3.12)
│   ├── src/          # Исходный код
│   │   ├── api/      # API endpoints
│   │   ├── models/   # SQLAlchemy models
│   │   ├── services/ # Business logic
│   │   └── lib/      # Утилиты и middleware
│   └── tests/        # Pytest тесты
├── frontend/         # React frontend (Vite + TypeScript)
│   ├── src/          # Исходный код
│   └── tests/        # Vitest + Playwright тесты
├── streamer/         # Telegram streaming service
├── docs/             # Документация
│   ├── bugfixes/     # КРИТИЧНО: Все документы об исправлении багов ТОЛЬКО сюда!
│   ├── api/          # API документация
│   ├── architecture/ # Архитектурные решения
│   └── development/  # Процессы разработки
├── specs/            # Спецификации и планы
└── scripts/          # Утилиты и скрипты
```

---

## 🔧 Технологический стек

### Backend
- **Runtime**: Python 3.12
- **Framework**: FastAPI 0.109+
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Queue**: Celery с Redis broker
- **Validation**: Pydantic 2.x

### Frontend
- **Framework**: React 18.2
- **Build**: Vite 5.1
- **Styling**: TailwindCSS 3.4
- **Language**: TypeScript 5.3
- **State**: React Context + hooks
- **Testing**: Vitest + Playwright
- **UI Docs**: Storybook 8.x

### Infrastructure
- **Container**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana

---

## 📋 Правила разработки

### Code Style

#### Python
- Форматирование: Black (line-length=88)
- Сортировка импортов: isort
- Линтинг: Ruff
- Type hints обязательны

#### TypeScript/React
- ESLint + Prettier
- Functional components + hooks
- Props interfaces обязательны

### Тестирование

#### Backend
- Pytest с pytest-asyncio
- Coverage target: 70%
- Конфигурация в pyproject.toml

#### Frontend
- Vitest для unit тестов
- Playwright для E2E
- Coverage target: 60%

### API Contracts

Используем Pydantic 2.x для валидации:
- Входящие данные: строгая валидация
- Ответы: сериализация через `.model_dump()`
- Ошибки: стандартизированный формат

---

## 🚨 Важные правила

1. **Никогда не коммитить**:
   - `.env` файлы
   - `*.session` файлы (Telegram)
   - Директорию `.internal/`

2. **Структура API endpoints**:
   - Файлы < 300 строк
   - Один router на модуль
   - Schemas отдельно

3. **Модели данных**:
   - Наследуются от Base
   - Используют TypedDict для типизации
   - Relationships через lazy="selectin"

4. **Тесты**:
   - Располагаются в tests/
   - Fixtures в conftest.py
   - Изолированные (без внешних зависимостей)

5. **Документация багфиксов**:
   - ⚠️ **КРИТИЧНО**: Все документы об исправлении багов сохранять в `docs/bugfixes/`
   - Формат имени: `COMPONENT_BUG_DESCRIPTION.md` (например, `TELEGRAM_2FA_FIX.md`)
   - Включать: описание проблемы, причину, решение, тестирование
   - Обновлять ссылки в README.md и ai-instructions/

---

## 🔄 Рабочий процесс

### Создание новой функции

1. Создать спецификацию в `specs/XXX-feature-name/`
2. Запустить `/speckit.plan` для генерации плана
3. Запустить `/speckit.tasks` для декомпозиции
4. Выполнить `/speckit.implement`
5. Запустить тесты и обновить документацию

### Pull Request

1. Ветка от `main`
2. Тесты проходят
3. Coverage не падает
4. Документация обновлена

---

## 📊 Мониторинг

### Coverage Reports
- Backend: `htmlcov/` после `pytest --cov`
- Frontend: `coverage/` после `npm run test:coverage`
- Baseline: `.internal/coverage-baseline.md`

### CI/CD Artifacts
- Coverage отчеты загружаются как артефакты
- Storybook доступен через `npm run storybook`

---

## 🔗 Ссылки

- [docs/README.md](../docs/README.md) — документация
- [docs/bugfixes/](../docs/bugfixes/) — история исправлений багов
- [ai-instructions/BUGFIX_DOCUMENTATION_RULES.md](BUGFIX_DOCUMENTATION_RULES.md) — **ПРАВИЛА документирования багфиксов**
- [OUTSTANDING_TASKS_REPORT.md](../OUTSTANDING_TASKS_REPORT.md) — текущие задачи
- [specs/012-project-improvements/](../specs/012-project-improvements/) — план улучшений

---

*Последнее обновление: 2025-12-20*
