# 🧪 Testing Guide - Sattva Telegram Broadcast

> **Последнее обновление**: December 28, 2025

## 📊 Текущее состояние тестирования

| Component | Framework | Coverage | Tests | Status |
|-----------|-----------|----------|-------|--------|
| **Backend Unit** | pytest 9.0.2 | 98.70% | 353 passing | ✅ |
| **Integration** | FastAPI TestClient | 100% | 19/19 passing | ✅ |
| **Frontend** | Vitest 4.0.10 | ~60% | 226 passing | ⏳ |
| **E2E** | Playwright 1.41.2 | - | 30+ specs | 🎭 |

---

## 🚀 Быстрый старт

### Backend Tests

```bash
cd backend
source ../venv/Scripts/activate  # Windows Git Bash
python -m pytest
```

### Run with coverage
```bash
python -m pytest --cov=src --cov-report=html --cov-report=term-missing --cov-fail-under=70
```

### Run specific test categories
```bash
# Unit tests only
python -m pytest -m unit

# Integration tests
python -m pytest -m integration

# Auth tests
python -m pytest -m auth

# API tests
python -m pytest -m api
```

### Run parallel (faster)
```bash
python -m pytest -n auto
```

### Verbose with logs
```bash
python -m pytest -v -s
```

## Frontend Tests

### Run all unit tests
```bash
cd frontend
npm test
```

### Run with coverage
```bash
npm run test:coverage
```

### Watch mode (during development)
```bash
npm run test:watch
```

### E2E tests
```bash
npm run test:e2e
```

### E2E UI mode (interactive)
```bash
npm run test:e2e:ui
```

## Coverage Reports

### Backend
```bash
cd backend
python -m pytest --cov=src --cov-report=html
# Open: backend/htmlcov/index.html
```

### Frontend
```bash
cd frontend
npm run test:coverage
# Open: frontend/coverage/index.html
```

## CI/CD

### GitHub Actions (automatic)
```bash
# Runs on push/PR automatically
# See: .github/workflows/tests.yml
```

### Pre-commit hooks
```bash
# Install
pre-commit install

# Run manually
pre-commit run --all-files
```

## Docker Testing

### Build test container
```bash
docker compose -f docker-compose.test.yml build
```

### Run tests in Docker
```bash
docker compose -f docker-compose.test.yml run --rm backend-test
docker compose -f docker-compose.test.yml run --rm frontend-test
```

## Troubleshooting

### Backend tests fail with DB errors
```bash
# Ensure test database is running
docker compose up -d db redis

# Run migrations
cd backend
alembic upgrade head
```

### Frontend tests fail with module errors
```bash
cd frontend
npm install
npm run test -- --clearCache
```

### Coverage too low
```bash
# Check uncovered files
pytest --cov=src --cov-report=term-missing

# Focus on critical modules first:
# - src/api/routes/
# - src/services/
# - src/database/
```
