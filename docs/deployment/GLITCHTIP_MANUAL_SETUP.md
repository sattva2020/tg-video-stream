# Glitchtip Configuration (Manual Setup Required)

## 1. Откройте Glitchtip UI

```bash
open http://localhost:8080  # Mac/Linux
start http://localhost:8080  # Windows
```

**Credentials:**
- Email: `admin@sattva.tv`
- Password: `admin123`

## 2. Создайте организацию

1. После логина перейдите в Settings → Organizations
2. Click "Create Organization"
3. Name: `Sattva TV`
4. Slug: `sattva-tv` (автоматически)
5. Click "Create"

## 3. Создайте Backend проект

1. Перейдите в Projects
2. Click "Create Project"
3. Name: `sattva-tv-backend`
4. Platform: `Python` или `Python-FastAPI`
5. Click "Create"

6. Скопируйте DSN:
   - Settings → Projects → `sattva-tv-backend` → Client Keys (DSN)
   - Формат: `http://abc123@localhost:8080/1`

## 4. Создайте Frontend проект

1. Click "Create Project"
2. Name: `sattva-tv-frontend`
3. Platform: `JavaScript` или `React`
4. Click "Create"

5. Скопируйте DSN:
   - Settings → Projects → `sattva-tv-frontend` → Client Keys (DSN)
   - Формат: `http://def456@localhost:8080/2`

## 5. Обновите .env файлы

**Backend: `backend/.env`**
```bash
# Glitchtip
SENTRY_DSN=http://YOUR_BACKEND_DSN@localhost:8080/1
SENTRY_ENVIRONMENT=development
SENTRY_RELEASE=v1.0.0
```

**Frontend: `frontend/.env.development` (для локальной разработки)**
```bash
# Glitchtip
VITE_SENTRY_DSN=http://YOUR_FRONTEND_DSN@localhost:8080/2
VITE_SENTRY_ENVIRONMENT=development
VITE_SENTRY_RELEASE=v1.0.0
```

## 6. Тестовые DSN (для быстрого старта)

Если хотите начать тестирование немедленно, используйте временные DSN:

**Backend `.env`:**
```bash
SENTRY_DSN=http://test-backend@localhost:8080/1
SENTRY_ENVIRONMENT=development
```

**Frontend `.env.development`:**
```bash
VITE_SENTRY_DSN=http://test-frontend@localhost:8080/2
VITE_SENTRY_ENVIRONMENT=development
```

> ⚠️ **Note:** Эти DSN не будут работать до создания проектов в UI, но не помешают запуску приложения.

## 7. Перезапустите контейнеры

```bash
cd /e/My/Sattva/telegram
docker compose restart backend frontend
```

## 8. Проверьте инициализацию

**Frontend Console:**
- Откройте http://localhost:3000
- DevTools → Console
- Должно быть: "✅ Sentry initialized"

**Backend Logs:**
```bash
docker logs telegram-backend-1 2>&1 | grep -i sentry
```

## Troubleshooting

### Glitchtip UI не открывается

```bash
# Проверка статуса
docker logs sattva-glitchtip-web --tail 50

# Перезапуск
docker compose -f docker-compose.glitchtip.yml restart
```

### Frontend не инициализирует Sentry

1. Проверьте DSN в `.env.development`
2. Проверьте импорт в `main.tsx`:
   ```typescript
   import { initSentry } from './instrumentation/sentry';
   initSentry();
   ```
3. Пересоберите: `docker compose build frontend && docker compose restart frontend`

### Backend не отправляет ошибки

1. Проверьте DSN в `backend/.env`
2. Проверьте существующий `backend/src/instrumentation/sentry.py` (должен быть)
3. Перезапустите: `docker compose restart backend`
