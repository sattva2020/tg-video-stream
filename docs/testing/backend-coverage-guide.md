# Backend Test Coverage Guide

> **Создан:** 28 декабря 2025  
> **Статус:** Production-Ready  
> **Coverage:** 98.75% (8 priority services)

---

## 🎯 Цели покрытия

### Достигнутые результаты (28 декабря 2025)

**Приоритетные сервисы - 98.75% среднее покрытие:**

| № | Сервис | Coverage | Tests | Критичность | Статус |
|---|--------|----------|-------|-------------|--------|
| 1 | `session_service` | **100%** | 29 | 🔴 CRITICAL | ✅ Идеально |
| 2 | `activity_service` | **100%** | 29 | 🟠 HIGH | ✅ Идеально |
| 3 | `playback_service` | **99%** | 82 | 🔴 CRITICAL | ✅ Отлично |
| 4 | `queue_service` | **99%** | 60 | 🔴 CRITICAL | ✅ Отлично |
| 5 | `telegram_rate_limiter` | **99%** | 54 | 🔴 CRITICAL | ✅ Отлично |
| 6 | `channel_service` | **99%** | 55 | 🟠 HIGH | ✅ Отлично |
| 7 | `auth_service` | **98%** | 23 | 🔴 CRITICAL | ✅ Отлично |
| 8 | `priority_queue_service` | **96%** | 46 | 🟠 HIGH | ✅ Хорошо |

**Итого: 353 теста, все проходят успешно**

---

## 📊 Структура тестов

### Организация файлов

```
backend/
├── src/
│   └── services/
│       ├── playback_service.py     # 129 строк, 99% coverage
│       ├── auth_service.py         # 113 строк, 98% coverage
│       ├── session_service.py      # 107 строк, 100% coverage
│       ├── activity_service.py     # 105 строк, 100% coverage
│       ├── telegram_rate_limiter.py # 154 строки, 99% coverage
│       ├── queue_service.py        # 219 строк, 99% coverage
│       ├── priority_queue_service.py # 155 строк, 96% coverage
│       └── channel_service.py      # 169 строк, 99% coverage
└── tests/
    ├── test_playback_service.py    # 82 теста
    ├── test_auth_service.py        # 23 теста
    ├── test_session_service.py     # 29 тестов
    ├── test_activity_service.py    # 29 тестов
    ├── test_telegram_rate_limiter.py # 54 теста
    ├── test_queue_service.py       # 60 тестов
    ├── test_priority_queue_service.py # 46 тестов
    └── test_channel_service.py     # 55 тестов
```

### Типы тестов

1. **Unit тесты** - изолированные функции и методы
2. **Integration тесты** - взаимодействие с Redis/DB (fakeredis, AsyncMock)
3. **Edge cases** - граничные условия и ошибки
4. **Branch coverage** - все ветви if/else/try/except

---

## 🚀 Запуск тестов

### Локальная разработка

```bash
cd backend

# Все приоритетные сервисы
pytest tests/test_playback_service.py tests/test_auth_service.py \
  tests/test_session_service.py tests/test_activity_service.py \
  tests/test_telegram_rate_limiter.py tests/test_queue_service.py \
  tests/test_priority_queue_service.py tests/test_channel_service.py \
  --cov=src.services.playback_service \
  --cov=src.services.auth_service \
  --cov=src.services.session_service \
  --cov=src.services.activity_service \
  --cov=src.services.telegram_rate_limiter \
  --cov=src.services.queue_service \
  --cov=src.services.priority_queue_service \
  --cov=src.services.channel_service \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-branch \
  -v
```

### Быстрые команды

```bash
# Только один сервис
pytest tests/test_playback_service.py -v

# С coverage для одного сервиса
pytest tests/test_playback_service.py \
  --cov=src.services.playback_service \
  --cov-report=term-missing

# Быстрый запуск без verbose
pytest tests/test_*.py -q

# HTML отчёт (откроется в браузере)
pytest --cov=src.services --cov-report=html
open htmlcov/index.html
```

### CI/CD

Автоматический запуск в GitHub Actions:

```yaml
# .github/workflows/backend-coverage.yml
- name: Run 8 Priority Services Tests
  run: |
    python -m pytest \
      tests/test_playback_service.py \
      tests/test_auth_service.py \
      tests/test_session_service.py \
      tests/test_activity_service.py \
      tests/test_telegram_rate_limiter.py \
      tests/test_queue_service.py \
      tests/test_priority_queue_service.py \
      tests/test_channel_service.py \
      --cov=src.services \
      --cov-report=json \
      --cov-branch \
      -v
```

**Триггеры:**
- Push в `main`, `develop`
- Pull Request
- Manual dispatch
- Изменения в `backend/src/services/**` или `backend/tests/test_*_service.py`

---

## 🔍 Анализ покрытия

### Непокрытые линии

#### auth_service.py - 98% (1 miss)

**Линия 19:** `serializer = URLSafeTimedSerializer(SECRET)`

**Причина:** Module-level код, выполняется до начала измерения coverage.

**Решение:** Технически непокрываемо. Serializer используется в 6 функциях, все покрыты тестами.

**Статус:** ✅ Принято (module-level limitation)

#### priority_queue_service.py - 96% (2 miss, 6 branch partials)

**Непокрытые линии:**
- `81`: JSON decode error в edge case
- `305`: Branch в обработке ошибок

**Причина:** Редкие edge cases, требующие сложной имитации ошибок.

**Статус:** ✅ Приемлемо (критические пути покрыты)

---

## 🛠️ Инструменты и зависимости

### Основные

```txt
pytest==9.0.2          # Тестовый фреймворк
pytest-cov==4.1.0      # Coverage плагин
pytest-asyncio==0.23.5 # Асинхронные тесты
pytest-mock==3.12.0    # Мокирование
```

### Дополнительные

```txt
fakeredis==2.21.1      # Redis mock
coverage==7.4.1        # Coverage engine
```

### Mock стратегии

```python
from unittest.mock import AsyncMock, Mock, patch

# AsyncMock для async функций
mock_redis = AsyncMock()
mock_redis.get.return_value = b'{"key": "value"}'

# Mock для синхронных функций
mock_db = Mock()
mock_db.query.return_value.filter.return_value.first.return_value = user

# Patch для временной подмены
with patch('services.auth_service.requests.get') as mock_get:
    mock_get.return_value.status_code = 200
    result = check_password_pwned("password123")
```

---

## 📈 CI/CD Integration

### GitHub Actions Workflow

**Файл:** `.github/workflows/backend-coverage.yml`

**Возможности:**
- ✅ Автоматический запуск на push/PR
- ✅ Coverage summary в GitHub Actions
- ✅ Артефакты с HTML отчётами (30 дней)
- ✅ Комментарии в PR с результатами
- ✅ Threshold проверка (минимум 95%)
- ✅ Codecov integration

**Результат workflow:**

```
## 🎯 Backend Coverage Report

### Priority Services (Target: 98.75%)

| Service | Coverage | Status |
|---------|----------|--------|
| playback_service | 99.0% | ✅ |
| auth_service | 98.0% | ✅ |
| session_service | 100.0% | ✅ |
| activity_service | 100.0% | ✅ |
| telegram_rate_limiter | 99.0% | ✅ |
| queue_service | 99.0% | ✅ |
| priority_queue_service | 96.0% | ✅ |
| channel_service | 99.0% | ✅ |
| **AVERAGE** | **98.75%** | 🎉 |

📊 Full report available in artifacts
```

### Badge в README

```markdown
![Backend Coverage](https://img.shields.io/badge/backend%20coverage-98.75%25-brightgreen?style=flat-square&logo=pytest)
![Tests](https://img.shields.io/badge/tests-353%20passed-success?style=flat-square&logo=github-actions)
```

---

## 🎓 Best Practices

### Написание тестов

1. **Именование:**
   ```python
   def test_function_name_scenario():
       """Test that function handles scenario correctly."""
   ```

2. **Структура (AAA):**
   ```python
   def test_add_to_queue():
       # Arrange
       service = QueueService()
       item = {"id": "123", "title": "Track"}
       
       # Act
       result = service.add(item)
       
       # Assert
       assert result is True
       assert service.get_size() == 1
   ```

3. **Покрытие edge cases:**
   ```python
   def test_add_to_full_queue_raises_error():
       """Test that adding to full queue raises QueueFullError."""
       service = QueueService(max_size=1)
       service.add({"id": "1"})
       
       with pytest.raises(QueueFullError):
           service.add({"id": "2"})
   ```

4. **Async тесты:**
   ```python
   @pytest.mark.asyncio
   async def test_update_channel_status():
       service = ChannelService()
       await service.update_channel_status(123, "playing", "Track Title")
       
       status = await service.get_channel_status(123)
       assert status["state"] == "playing"
   ```

### Моки и фикстуры

```python
# conftest.py
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = Mock()
    session.query.return_value.filter.return_value.first.return_value = None
    return session

@pytest.fixture
def mock_redis():
    """Mock Redis connection."""
    return AsyncMock()

# test_service.py
def test_get_user(mock_db_session):
    service = AuthService(db=mock_db_session)
    user = service.get_user(123)
    mock_db_session.query.assert_called_once()
```

---

## 🔄 Поддержка покрытия

### Мониторинг

1. **Локально:**
   ```bash
   pytest --cov=src.services --cov-report=term-missing
   ```

2. **CI/CD:**
   - Проверка при каждом PR
   - Падение если coverage < 95%
   - Автоматические отчёты

3. **Codecov:**
   - Интеграция с GitHub
   - Визуализация изменений
   - Комментарии в PR

### Добавление новых тестов

1. **Создайте файл:** `tests/test_new_service.py`
2. **Напишите тесты:**
   ```python
   import pytest
   from services.new_service import NewService
   
   def test_new_function():
       service = NewService()
       result = service.new_function()
       assert result == expected
   ```
3. **Запустите:**
   ```bash
   pytest tests/test_new_service.py --cov=src.services.new_service
   ```
4. **Проверьте coverage:**
   - Цель: ≥95% для критичных сервисов
   - Минимум: ≥80% для остальных

---

## 📚 Дополнительные ресурсы

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Testing Best Practices](../development/testing-best-practices.md)
- [CI/CD Guide](../deployment/ci-cd-guide.md)

---

## 🎉 Следующие шаги

1. ✅ **Backend coverage зафиксирован** (98.75%)
2. 🔄 **Integration тесты API** - проверка endpoints
3. 🔄 **Frontend unit tests** - компоненты React
4. 🔄 **E2E тесты** - user journeys

**Цель:** Production-Ready Quality Assurance

---

**Версия:** 1.0  
**Последнее обновление:** 28 декабря 2025  
**Автор:** Senior DevOps Engineer (Jarvis)
