# Database Password Mismatch Fix

**Дата:** 2025-12-12  
**Автор:** Jarvis  
**Статус:** Исправлено ✅

---

## 🔴 Проблема

После пересборки frontend образа через `docker compose build --no-cache frontend` произошла **автоматическая пересборка зависимых контейнеров** (db, backend), что привело к рассинхронизации паролей:

```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
connection to server at "db" (172.19.0.3), port 5432 failed: 
FATAL: password authentication failed for user "postgres"
```

### Причина
- **docker-compose.yml:** `POSTGRES_PASSWORD: sattva_secure_db_password_2025`
- **backend/.env:** `DB_PASSWORD=postgres` (дефолтный пароль)

### Последствия
- Backend контейнер в статусе **unhealthy**
- Все API запросы к `/api/*` возвращали 500 Internal Server Error
- Telegram Login не работал
- Dashboard не загружался

---

## ✅ Решение

### 1. Обновление backend/.env на сервере
```bash
ssh root@37.53.91.144
cd /opt/sattva-streamer/backend
sed -i 's/DB_PASSWORD=postgres/DB_PASSWORD=sattva_secure_db_password_2025/' .env
```

### 2. Пересоздание backend контейнера
```bash
cd /opt/sattva-streamer
docker compose up -d --force-recreate backend
```

### 3. Проверка результата
```bash
# Проверка статуса
docker ps | grep backend
# Результат: Up 50 seconds (healthy)

# Проверка подключения к БД
curl https://sattva-streamer.top/health
# Результат: "database": {"status": "up", "latency_ms": 2.12}
```

---

## 🔧 Техническая информация

### Файлы, задействованные в проблеме:
- `/opt/sattva-streamer/docker-compose.yml` — содержит `${DB_PASSWORD}` для db service
- `/opt/sattva-streamer/backend/.env` — содержит реальное значение `DB_PASSWORD`
- Backend использует: `DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/telegram_db`

### Контейнеры, затронутые восстановлением:
- `sattva-streamer-db-1` (Postgres 15 Alpine) — пересоздан
- `sattva-streamer-backend-1` (FastAPI) — пересоздан

### Время простоя:
- **Начало:** 18:00 UTC (после docker compose build frontend)
- **Окончание:** 18:37 UTC (после пересоздания backend)
- **Простой:** ~37 минут

---

## 📊 Статус после исправления

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 79.1,
  "dependencies": [
    {
      "name": "database",
      "status": "up",
      "latency_ms": 2.68,
      "last_check": "2025-12-12T18:38:26.435632+00:00"
    }
  ]
}
```

---

## 🛡️ Предотвращение повторения

### Рекомендации:

1. **Синхронизация паролей:**
   - Убедиться, что `backend/.env` содержит актуальный `DB_PASSWORD`
   - Периодически проверять соответствие паролей через `grep DB_PASSWORD`

2. **Изолированная пересборка:**
   ```bash
   # Вместо:
   docker compose build --no-cache frontend
   
   # Использовать:
   docker compose build --no-cache frontend --no-deps
   ```
   Флаг `--no-deps` предотвращает пересоздание зависимых сервисов.

3. **Мониторинг:**
   - Настроить алерты на статус backend контейнера (unhealthy)
   - Добавить healthcheck на доступность БД

4. **Pre-deploy проверка:**
   ```bash
   # Проверка перед деплоем
   docker compose config | grep -A 2 "POSTGRES_PASSWORD"
   grep DB_PASSWORD backend/.env
   ```

---

## 📝 Связанные изменения

- **Коммит:** N/A (изменения только на production сервере)
- **Файлы изменены на проде:**
  - `/opt/sattva-streamer/backend/.env` — обновлён DB_PASSWORD

---

## ✅ Проверка работоспособности

1. **Backend health:**
   ```bash
   curl https://sattva-streamer.top/health
   ```

2. **Database connectivity:**
   ```bash
   docker exec sattva-streamer-backend-1 \
     python -c "from src.core.database import engine; print(engine.execute('SELECT 1').scalar())"
   ```

3. **Telegram Login:**
   - Открыть https://sattva-streamer.top/login
   - Попробовать войти через Telegram
   - Проверить, что нет ошибок подключения к БД

---

**Статус:** ✅ Исправлено и задокументировано  
**Verified:** 2025-12-12 18:38 UTC
