# Quickstart: Интеграция компонентов из GitHub-проектов

**Feature**: 016-github-integrations | **Date**: 2025-12-01

## Содержание

1. [Предварительные требования](#предварительные-требования)
2. [Установка зависимостей](#установка-зависимостей)
3. [Конфигурация](#конфигурация)
4. [Запуск разработки](#запуск-разработки)
5. [Тестирование](#тестирование)
6. [Проверка интеграции](#проверка-интеграции)

---

## Предварительные требования

### Системные требования

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (для локальной разработки)

### Проверка версий

```bash
# Python
python --version  # >= 3.11

# Node.js
node --version    # >= 18.0

# Redis
redis-cli --version  # >= 7.0

# PostgreSQL
psql --version    # >= 14.0
```

### Существующая инфраструктура

Убедитесь, что запущены:
- PostgreSQL с базой `sattva`
- Redis на порту 6379

```bash
# Проверка PostgreSQL
psql -h localhost -U postgres -c "SELECT 1"

# Проверка Redis
redis-cli ping  # Должен вернуть PONG
```

---

## Установка зависимостей

### Backend (Python)

```bash
cd backend

# Создание виртуального окружения (если еще нет)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или .venv\Scripts\activate  # Windows

# Установка зависимостей с новыми пакетами
pip install -r requirements.txt

# Новые зависимости для этой feature:
pip install sqladmin>=0.16.0 prometheus_client>=0.19.0 itsdangerous>=2.1.2
```

### Добавить в `backend/requirements.txt`:

```txt
# Admin panel
sqladmin>=0.16.0
itsdangerous>=2.1.2  # для session management

# Metrics
prometheus_client>=0.19.0
```

### Frontend (Node.js)

```bash
cd frontend

# Установка зависимостей
npm install

# Новых зависимостей для frontend нет
# Используем существующий React + WebSocket
```

### Streamer (Python)

```bash
cd streamer

# Активация того же venv
source ../backend/.venv/bin/activate

# Дополнительные зависимости не требуются
# PyTgCalls уже установлен
```

---

## Конфигурация

### 1. Обновить template.env

Добавить новые переменные в `template.env`:

```bash
# ===== Auto-End Configuration =====
AUTO_END_TIMEOUT_MINUTES=5
AUTO_END_ENABLED=true

# ===== Placeholder Configuration =====
PLACEHOLDER_AUDIO_PATH=/app/data/placeholder.mp3
PLACEHOLDER_LOOP=true

# ===== Admin Panel =====
ADMIN_SECRET_KEY=change_this_admin_secret_key_123
ADMIN_SESSION_LIFETIME_HOURS=24

# ===== Prometheus =====
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
```

### 2. Regenerate .env

```bash
# Использовать setup.sh для генерации
./scripts/generate_env.sh

# Или вручную скопировать и обновить
cp template.env .env
# Отредактировать .env с реальными значениями
```

### 3. Placeholder Audio

Создать или скачать placeholder аудио:

```bash
mkdir -p data
# Скачать или создать placeholder.mp3
# Рекомендуется: 10-секундный loop тишины или ambient звук
```

### 4. Database Migration

```bash
cd backend

# Создать миграцию для AdminAuditLog
alembic revision --autogenerate -m "add_admin_audit_logs"

# Применить миграции
alembic upgrade head
```

---

## Запуск разработки

### Вариант 1: Docker Compose (рекомендуется)

```bash
# Из корня проекта
docker-compose up -d

# Проверка логов
docker-compose logs -f backend
```

### Вариант 2: Локальный запуск

#### Terminal 1: Backend

```bash
cd backend
source .venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

#### Terminal 2: Frontend

```bash
cd frontend
npm run dev
```

#### Terminal 3: Streamer (опционально)

```bash
cd streamer
source ../backend/.venv/bin/activate
python run.py
```

### Проверка запуска

```bash
# Backend health check
curl http://localhost:8000/health

# Admin panel
open http://localhost:8000/admin

# Prometheus metrics
curl http://localhost:8000/metrics

# Frontend
open http://localhost:5173
```

---

## Тестирование

### Unit Tests

```bash
cd backend

# Запуск всех тестов
pytest

# Тесты для новых модулей
pytest tests/test_queue_service.py -v
pytest tests/test_auto_end_service.py -v
pytest tests/test_prometheus_metrics.py -v
pytest tests/api/test_admin_panel.py -v

# С покрытием
pytest --cov=src --cov-report=html
```

### Smoke Tests

```bash
# Queue operations
./tests/smoke/test_queue_operations.sh

# Auto-end
./tests/smoke/test_auto_end.sh
```

### Manual Testing

#### Queue API

```bash
# Добавить элемент в очередь
curl -X POST http://localhost:8000/api/v1/queue/-1001234567890/items \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "Test Track",
    "url": "https://youtube.com/watch?v=test123",
    "source": "youtube"
  }'

# Получить очередь
curl http://localhost:8000/api/v1/queue/-1001234567890

# Пропустить трек
curl -X POST http://localhost:8000/api/v1/queue/-1001234567890/skip \
  -H "Authorization: Bearer <token>"
```

#### Metrics API

```bash
# Prometheus формат
curl http://localhost:8000/metrics

# JSON системные метрики
curl http://localhost:8000/api/v1/metrics/system \
  -H "Authorization: Bearer <token>"

# Метрики стримов
curl http://localhost:8000/api/v1/metrics/streams \
  -H "Authorization: Bearer <token>"
```

#### Admin Panel

1. Открыть http://localhost:8000/admin
2. Войти с admin credentials
3. Проверить:
   - Список пользователей
   - Список плейлистов
   - Аудит-логи
   - Dashboard статистика

#### WebSocket

```javascript
// В browser console
const ws = new WebSocket('ws://localhost:8000/api/ws/monitoring?events=metrics_update,listeners_update');

ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Event:', JSON.parse(e.data));
ws.onerror = (e) => console.error('Error:', e);

// Ping test
ws.send(JSON.stringify({type: 'ping'}));
```

---

## Проверка интеграции

### Checklist

- [ ] Backend запускается без ошибок
- [ ] `/metrics` возвращает Prometheus формат
- [ ] `/admin` показывает login страницу
- [ ] Admin login работает для admin/superadmin
- [ ] Queue API endpoints отвечают
- [ ] WebSocket соединение устанавливается
- [ ] WebSocket получает события
- [ ] Redis хранит очередь (проверить `redis-cli KEYS "stream_queue:*"`)
- [ ] PostgreSQL содержит таблицу `admin_audit_logs`

### Отладка

#### Backend не запускается

```bash
# Проверить зависимости
pip check

# Проверить импорты
python -c "from src.admin import setup_admin; print('OK')"
python -c "from prometheus_client import generate_latest; print('OK')"
```

#### Redis не сохраняет очередь

```bash
# Проверить подключение
redis-cli ping

# Проверить ключи
redis-cli KEYS "*"

# Проверить содержимое очереди
redis-cli LRANGE "stream_queue:-1001234567890" 0 -1
```

#### Миграции не применяются

```bash
# Проверить текущую версию
alembic current

# Проверить историю
alembic history

# Откат и повторное применение
alembic downgrade -1
alembic upgrade head
```

#### WebSocket не подключается

```bash
# Проверить CORS настройки в backend
# Проверить, что endpoint зарегистрирован

curl -i http://localhost:8000/api/ws/monitoring
# Должен вернуть 426 Upgrade Required
```

---

## Следующие шаги

После успешной настройки:

1. **Разработка**: Реализовать компоненты согласно `plan.md`
2. **Тестирование**: Написать unit и integration тесты
3. **Документация**: Обновить `docs/features/` с описанием новых модулей
4. **Code Review**: Создать PR в ветку `main`

---

## Полезные команды

```bash
# Форматирование кода
cd backend && black src/ && isort src/
cd frontend && npm run format

# Линтинг
cd backend && flake8 src/ && mypy src/
cd frontend && npm run lint

# Документация
npm run docs:validate

# Очистка Docker
docker-compose down -v
docker system prune -f
```
