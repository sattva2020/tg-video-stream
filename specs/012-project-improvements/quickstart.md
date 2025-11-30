# Quickstart: План улучшения проекта 24/7 TV Telegram

**Branch**: `012-project-improvements` | **Date**: 29.11.2025

---

## Обзор

Это руководство для быстрого старта работы над фичей 012-project-improvements.

### Что делает фича

1. **Безопасность** — устраняет критические уязвимости Docker и credentials
2. **Модернизация** — обновляет deprecated SQLAlchemy/Pydantic код
3. **Инфраструктура** — добавляет health checks, CD pipeline, мониторинг
4. **Качество** — рефакторинг, Storybook, code coverage

---

## Предварительные требования

### Инструменты

```bash
# Проверь версии
python --version  # >= 3.11
node --version    # >= 20.0
docker --version  # >= 24.0
docker compose version  # >= 2.20
```

### SSH доступ

```bash
# Проверь доступ к VPS
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 "echo OK"
```

---

## Быстрый старт

### 1. Клонирование и переключение на ветку

```bash
git clone <repo-url>
cd telegram
git checkout 012-project-improvements
```

### 2. Установка зависимостей

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

# Frontend
cd ../frontend
npm install
```

### 3. Настройка окружения

```bash
# Скопировать и заполнить .env
cp template.env .env
# Редактировать .env, заполнить секреты
```

### 4. Запуск в dev режиме

```bash
# Из корня проекта
docker compose up -d

# Проверить статус
docker compose ps
```

---

## Структура задач

### Приоритет P1 (сначала)

| User Story | Задача | Файлы |
|------------|--------|-------|
| US-1 | Удалить Docker socket mount | `docker-compose.yml` |
| US-1 | Добавить сетевую изоляцию | `docker-compose.yml` |
| US-1 | Мигрировать credentials в secrets | `docker-compose.yml`, `template.env` |
| US-2 | SQLAlchemy 2.0 migration | `backend/src/database.py` |
| US-2 | Pydantic v2 ConfigDict | `backend/src/api/*.py` |

### Приоритет P2 (затем)

| User Story | Задача | Файлы |
|------------|--------|-------|
| US-3 | Добавить health endpoints | `backend/src/api/health.py` |
| US-3 | Docker healthchecks | `docker-compose.yml` |
| US-4 | CD pipeline | `.github/workflows/cd.yml` |
| US-5 | Prometheus + Grafana | `config/monitoring/`, `docker-compose.yml` |

### Приоритет P3 (потом)

| User Story | Задача | Файлы |
|------------|--------|-------|
| US-6 | Рефакторинг schedule.py | `backend/src/api/schedule/` |
| US-7 | Storybook setup | `frontend/.storybook/` |
| US-8 | Coverage setup | `pyproject.toml`, `vitest.config.ts` |

---

## Тестирование

### Backend

```bash
cd backend

# Обычный запуск
pytest

# С проверкой deprecation warnings (US-2)
pytest -W error::DeprecationWarning

# С coverage (US-8)
pytest --cov=src --cov-report=html
```

### Frontend

```bash
cd frontend

# Unit tests
npm run test

# E2E tests
npm run test:e2e

# Coverage (US-8)
npm run test:coverage
```

### Security Scan

```bash
# Trivy scan (US-1)
trivy config docker-compose.yml
trivy image telegram-backend:latest
```

---

## Валидация изменений

### До коммита

```bash
# Документация
npm run docs:validate

# Линтеры
cd backend && ruff check src/
cd frontend && npm run lint

# Тесты
pytest && npm run test
```

### После PR

CI автоматически проверит:
- [ ] Тесты проходят
- [ ] Нет DeprecationWarning
- [ ] Coverage >= 70% (backend) / 60% (frontend)
- [ ] Документация валидна

---

## Полезные команды

### Docker

```bash
# Перезапуск с пересборкой
docker compose up -d --build

# Логи сервиса
docker compose logs -f backend

# Health check статус
docker inspect --format='{{json .State.Health}}' telegram-backend-1
```

### Мониторинг (после US-5)

```bash
# Grafana
open http://localhost:3001

# Prometheus
open http://localhost:9090

# Метрики backend
curl http://localhost:8000/metrics
```

### Rollback (CD)

```bash
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 << 'EOF'
cd /opt/telegram
git log --oneline -5
git revert HEAD --no-edit
docker compose up -d --build
EOF
```

---

## Emergency Procedures

### Быстрый откат к предыдущей версии

При критических проблемах используй скрипт `scripts/rollback_release.sh`:

```bash
# SSH на VPS
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144

# Выполнить rollback (автоматически откатит к последнему стабильному состоянию)
./scripts/rollback_release.sh

# Или ручной откат
git checkout $(cat .previous_commit)
docker compose up -d --build
```

### Откат к конкретной версии

```bash
# Посмотреть историю
git log --oneline -10

# Откатиться к конкретному коммиту
git checkout <commit_hash>
docker compose up -d --build

# Проверить health
curl http://localhost:8000/health
```

### Восстановление базы данных

```bash
# Найти бэкап
ls -la /root/backups/

# Восстановить из бэкапа
docker compose exec -T db psql -U postgres telegram_db < /root/backups/<backup_file>.sql
```

### Полный рестарт всех сервисов

```bash
# Остановить все
docker compose down

# Очистить volumes (ВНИМАНИЕ: удалит данные!)
# docker compose down -v

# Запустить заново
docker compose up -d --build

# Мониторить логи
docker compose logs -f
```

### Контакты для экстренных случаев

- **SSH доступ**: `ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144`
- **Логи**: `docker compose logs --tail=100`
- **Health check**: `curl http://localhost:8000/health`

---

## Troubleshooting

### Docker socket permission denied

**Проблема**: После удаления socket mount — ошибка "permission denied"

**Решение**: Это ожидаемо! Удаление socket — цель US-1. Проверь, что backend не использует Docker API.

### Deprecation warnings

**Проблема**: `pytest -W error::DeprecationWarning` падает

**Решение**: Выполни миграцию US-2:
- `declarative_base()` → `DeclarativeBase`
- `class Config` → `model_config = ConfigDict(...)`

### Health check timeout

**Проблема**: Container не становится healthy

**Решение**: 
1. Проверь что `/health` endpoint существует
2. Увеличь `start_period` в healthcheck
3. Проверь зависимости (db, redis)

---

## Связанные документы

- [Спецификация](./spec.md) — полные User Stories и требования
- [План](./plan.md) — технический контекст и Constitution Check
- [Research](./research.md) — исследование решений
- [Data Model](./data-model.md) — схемы данных
- [Health API Contract](./contracts/health-api.yaml) — OpenAPI спецификация
- [Metrics Spec](./contracts/metrics-spec.md) — Prometheus метрики

---

## Контакты

При вопросах:
1. Проверь документацию в `docs/`
2. Смотри `ai-instructions/` для контекста агента
3. Создай issue в GitHub с тегом `012-project-improvements`
