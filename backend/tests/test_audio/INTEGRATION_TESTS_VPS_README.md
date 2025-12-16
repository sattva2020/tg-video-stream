# Integration Tests с VPS PostgreSQL БД

## Обзор

Этот подход использует реальную PostgreSQL БД на VPS для integration tests вместо in-memory SQLite. Это позволяет тестировать реальную интеграцию с БД без сложной настройки dependency injection.

## Архитектура

```
Локальная машина           VPS (37.53.91.144)
│                          │
│  tests/                  │  Docker Network (10.99.99.0/24)
│    test_audio/           │    │
│      conftest.py ────────┼────┼─► PostgreSQL Container (db:5432)
│      test_endpoints.py   │    │     └─ sattva_test_db (test DB)
│      .env.test           │    │
│                          │    └─► Backend Container
│                          │          (запуск тестов)
```

## Настройка

### 1. Тестовая База Данных

Тестовая БД уже создана на VPS:
- **Database**: `sattva_test_db`
- **User**: `sattva_test`  
- **Password**: `TestPassword2024Secure`
- **Host**: `db` (внутри Docker сети) или `localhost` (на VPS)

### 2. Файл .env.test

```env
DATABASE_URL="postgresql://sattva_test:TestPassword2024Secure@db:5432/sattva_test_db"
RUST_TRANSCODER_URL="http://rust-transcoder:8090"
JWT_SECRET="test_secret_key_for_unit_tests_only"
...
```

### 3. Конфигурация conftest.py

- Загружает `.env.test` при запуске
- Определяет тип БД (PostgreSQL или SQLite fallback)
- Создает таблицы через `Base.metadata.create_all()`
- Выполняет cleanup после каждого теста (удаляет test@example.com юзеров)

## Запуск Тестов

### Вариант A: На VPS (Рекомендуется)

```bash
# Через SSH
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144

# Внутри VPS
cd /root
docker compose exec backend pytest tests/test_audio/ -v
```

### Вариант B: Локально (Требует SSH Tunnel)

```bash
# Открыть SSH tunnel к PostgreSQL
ssh -i ~/.ssh/id_rsa_n8n -L 5432:db:5432 root@37.53.91.144

# В другом терминале запустить тесты
cd backend
pytest tests/test_audio/ -v
```

### Вариант C: Через скрипт

```bash
# На локальной машине
scp -i ~/.ssh/id_rsa_n8n backend/.env.test root@37.53.91.144:/tmp/
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 << 'EOF'
  docker compose exec -T backend bash -c "
    export $(grep -v '^#' /tmp/env.test | xargs)
    pytest tests/test_audio/ -v
  "
EOF
```

## Преимущества

✅ **Реальная интеграция** - тестирование с реальной PostgreSQL БД  
✅ **Простота** - не требует сложной настройки mocks  
✅ **Изоляция** - отдельная тестовая БД не влияет на production  
✅ **Скорость** - БД на том же сервере = минимальная латентность  

## Недостатки

⚠️ **Зависимость от сети** - нужен доступ к VPS  
⚠️ **Cleanup критичен** - важно очищать тестовые данные  
⚠️ **Параллелизм** - может быть проблема при параллельном запуске тестов  

## Cleanup Стратегия

После каждого теста:
1. Rollback транзакции
2. Удаление PlaybackSettings для test юзеров
3. Удаление Users с email паттерном `test%@example.com`

```python
session.query(PlaybackSettings).filter(
    PlaybackSettings.user_id.in_(
        session.query(User.id).filter(User.email.like('test%@example.com'))
    )
).delete(synchronize_session=False)

session.query(User).filter(User.email.like('test%@example.com')).delete()
```

## Troubleshooting

### Connection Refused

**Проблема**: `connection to server at "10.99.99.6", port 5432 failed`

**Решение**: 10.99.99.6 - это внутренний Docker network IP. Запускайте тесты на VPS или используйте SSH tunnel.

### Database Does Not Exist

**Проблема**: `database "sattva_test_db" does not exist`

**Решение**: Создайте БД через скрипт:
```bash
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 "bash /tmp/create_test_db_simple.sh"
```

### Authentication Failed

**Проблема**: `password authentication failed for user "sattva_test"`

**Решение**: Проверьте пароль в `.env.test` и в БД:
```bash
ssh root@37.53.91.144
docker exec sattva-streamer-db-1 psql -U postgres -c "ALTER USER sattva_test WITH PASSWORD 'TestPassword2024Secure';"
```

### Tables Do Not Exist

**Проблема**: `relation "users" does not exist`

**Решение**: Таблицы создаются автоматически через `Base.metadata.create_all()` в conftest. Убедитесь что:
- Все модели импортированы
- БД доступна
- У пользователя есть права CREATE TABLE

## CI/CD Integration

Для GitHub Actions:

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.VPS_SSH_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
      
      - name: Run tests on VPS
        run: |
          ssh -o StrictHostKeyChecking=no root@37.53.91.144 "
            cd /root &&
            docker compose exec -T backend pytest tests/test_audio/ -v --junitxml=test-results.xml
          "
      
      - name: Publish Test Results
        uses: EnricoMi/publish-unit-test-result-action@v2
        if: always()
        with:
          files: test-results.xml
```

## Альтернативы

### 1. In-Memory SQLite
- **Плюсы**: Быстро, без зависимостей
- **Минусы**: Не тестирует PostgreSQL-специфичные фичи

### 2. Testcontainers
- **Плюсы**: Изолированные Docker контейнеры для каждого теста
- **Минусы**: Требует Docker на локальной машине

### 3. pytest-docker
- **Плюсы**: Автоматическое управление Docker контейнерами
- **Минусы**: Сложная настройка

## Дополнительные Скрипты

- `scripts/create_test_db.sh` - Создание тестовой БД с миграциями
- `scripts/create_test_db_simple.sh` - Быстрое создание БД без миграций
- `scripts/run_tests_on_vps.sh` - Запуск тестов на VPS

## Следующие Шаги

1. ✅ Настроить PostgreSQL тестовую БД на VPS
2. ✅ Обновить conftest для работы с VPS БД
3. ✅ Добавить cleanup после тестов
4. ⏳ Запустить тесты и проверить работоспособность
5. ⏳ Добавить в CI/CD pipeline
6. ⏳ Расширить тестовое покрытие
