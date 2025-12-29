# Инструкция: Добавление CODECOV_TOKEN в GitHub Secrets

## Назначение
CODECOV_TOKEN используется для автоматической отправки отчётов о покрытии кода в сервис Codecov.io через CI/CD pipeline.

## Шаги настройки

### 1. Регистрация на Codecov.io (5 минут)

1. Перейти на [https://codecov.io/](https://codecov.io/)
2. Войти через GitHub аккаунт
3. Выбрать "Add new repository"
4. Найти репозиторий `telegram` в списке ваших репозиториев
5. Нажать "Setup repo"

### 2. Получение CODECOV_TOKEN

После добавления репозитория Codecov покажет страницу настройки:

1. Скопировать **Repository Upload Token** (формат: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
2. Этот токен уникален для вашего репозитория

**Важно**: Токен секретный, не коммитить в код!

### 3. Добавление токена в GitHub Secrets

1. Перейти в репозиторий на GitHub
2. `Settings` → `Secrets and variables` → `Actions`
3. Нажать `New repository secret`
4. Заполнить:
   - **Name**: `CODECOV_TOKEN`
   - **Secret**: вставить токен из шага 2
5. Нажать `Add secret`

### 4. Проверка интеграции

После добавления токена, следующий CI/CD run автоматически:

1. Запустит тесты
2. Сгенерирует coverage report (coverage.xml)
3. Отправит отчёт в Codecov
4. На странице Pull Request появится Codecov badge и комментарий с изменениями покрытия

## Пример использования в CI/CD (.github/workflows/test.yml)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests with coverage
        run: |
          cd backend
          pytest --cov=src --cov-report=xml --cov-report=term
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./backend/coverage.xml
          flags: backend
          fail_ci_if_error: true
```

## Альтернативный метод (без токена)

Codecov также поддерживает "tokenless uploads" для публичных репозиториев, но рекомендуется использовать токен для:
- Приватных репозиториев
- Защиты от спама
- Точной привязки к конкретному репозиторию

## Результаты после настройки

После успешной интеграции вы увидите:

1. **Badge в README.md**:
   ```markdown
   [![codecov](https://codecov.io/gh/YOUR_USERNAME/telegram/branch/main/graph/badge.svg?token=CODECOV_TOKEN)](https://codecov.io/gh/YOUR_USERNAME/telegram)
   ```

2. **Codecov Comments** в Pull Requests:
   - Изменение покрытия (например: `+2.15%`)
   - Детализация по файлам
   - Предупреждения о снижении покрытия

3. **Dashboard на Codecov.io**:
   - История покрытия
   - Графики тренда
   - Детальная статистика по файлам/папкам

## Troubleshooting

### Ошибка "Invalid token"
- Проверить, что токен скопирован полностью (с дефисами)
- Убедиться, что имя секрета именно `CODECOV_TOKEN`

### Отчёт не загружается
- Проверить, что файл `coverage.xml` существует после тестов
- Убедиться, что путь к файлу в workflow правильный
- Проверить логи CI/CD на наличие ошибок

### Coverage 0%
- Убедиться, что `pytest --cov=src` запускается из правильной директории
- Проверить `.coveragerc` или `pyproject.toml` конфигурацию

## Дополнительные настройки Codecov

В корне репозитория создать `codecov.yml`:

```yaml
coverage:
  status:
    project:
      default:
        target: 70%  # Минимальный порог покрытия
        threshold: 1%  # Допустимое снижение
    patch:
      default:
        target: 70%

comment:
  layout: "reach, diff, flags, files"
  require_changes: true

ignore:
  - "tests/"
  - "migrations/"
  - "**/conftest.py"
```

## Время выполнения
- **Регистрация на Codecov**: 2 минуты
- **Получение токена**: 1 минута
- **Добавление в GitHub Secrets**: 2 минуты
- **Проверка в CI/CD**: автоматически при следующем push

**Итого**: ~5 минут ручной работы

---
**Статус**: Инструкция готова  
**Последнее обновление**: 27 декабря 2025
