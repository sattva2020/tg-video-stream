# ✅ Phase 2.2-2.3 Завершено! Следующие шаги для тестирования

## 🎉 Что выполнено

✅ **1. Frontend Sentry Integration**
- `initSentry()` добавлен в `frontend/src/main.tsx`
- Sentry инициализируется ПЕРЕД рендерингом приложения
- `.env.development` файл создан с переменными Sentry

✅ **2. Backend Sentry Integration**
- Существующая интеграция проверена (`backend/src/instrumentation/sentry.py`)
- `.env` файл обновлён с переменными Sentry

✅ **3. Glitchtip Stack**
- Все контейнеры запущены и работают
- Superuser создан: `admin@sattva.tv` / `admin123`
- UI доступен по адресу: http://localhost:8080

✅ **4. Контейнеры перезапущены**
- Frontend и Backend перезапущены с новыми настройками

---

## 📋 Следующие шаги (ОБЯЗАТЕЛЬНО)

### Шаг 1: Создайте проекты в Glitchtip UI

**1.1. Откройте Glitchtip:**
```bash
http://localhost:8080
```

**Credentials:**
- Email: `admin@sattva.tv`
- Password: `admin123`

**1.2. Создайте организацию:**
1. Settings → Organizations → Create Organization
2. Name: `Sattva TV`
3. Slug: `sattva-tv` (автоматически)
4. Click "Create"

**1.3. Создайте Backend проект:**
1. Projects → Create Project
2. Name: `sattva-tv-backend`
3. Platform: `Python` или `Python-FastAPI`
4. Click "Create"
5. Скопируйте DSN: Settings → Projects → `sattva-tv-backend` → Client Keys (DSN)
   - Формат: `http://abc123def456@localhost:8080/1`

**1.4. Создайте Frontend проект:**
1. Projects → Create Project
2. Name: `sattva-tv-frontend`
3. Platform: `JavaScript` или `React`
4. Click "Create"
5. Скопируйте DSN: Settings → Projects → `sattva-tv-frontend` → Client Keys (DSN)
   - Формат: `http://ghi789jkl012@localhost:8080/2`

---

### Шаг 2: Обновите .env файлы с реальными DSN

**Backend: `backend/.env`**
```bash
# Замените "" на реальный DSN из Glitchtip UI
SENTRY_DSN="http://YOUR_BACKEND_DSN@localhost:8080/1"
SENTRY_ENVIRONMENT="development"
SENTRY_RELEASE="v1.0.0"
```

**Frontend: `frontend/.env.development`**
```bash
# Замените "" на реальный DSN из Glitchtip UI
VITE_SENTRY_DSN="http://YOUR_FRONTEND_DSN@localhost:8080/2"
VITE_SENTRY_ENVIRONMENT="development"
VITE_SENTRY_RELEASE="v1.0.0"
```

---

### Шаг 3: Перезапустите контейнеры

```bash
cd /e/My/Sattva/telegram
docker compose restart backend frontend
```

---

### Шаг 4: Проверьте инициализацию

**4.1. Frontend Console:**
1. Откройте http://localhost:3000
2. DevTools → Console (F12)
3. Должно быть: `"⚠️  VITE_SENTRY_DSN not set, error tracking disabled"` ← это пока DSN пустой
4. После добавления DSN и перезапуска НЕ должно быть warning (Sentry инициализируется молча если DSN валидный)

**4.2. Backend Logs:**
```bash
docker logs telegram-backend-1 2>&1 | grep -i sentry
```
Не должно быть ошибок. Sentry инициализируется в `backend/src/instrumentation/sentry.py`.

---

### Шаг 5: Протестируйте отправку ошибок

**5.1. Frontend Error Test:**

Откройте DevTools Console на http://localhost:3000 и выполните:

```javascript
// Тест 1: Простая ошибка
throw new Error('Test frontend error from console');

// Тест 2: Async error
(async () => {
  throw new Error('Test async error');
})();
```

Подождите 2-3 секунды, затем откройте Glitchtip UI:
- Projects → `sattva-tv-frontend` → Issues
- Должна появиться ошибка "Test frontend error from console"

**5.2. Backend Error Test:**

```bash
# Отправить запрос на несуществующий endpoint (вызовет 404)
curl http://localhost:8000/api/nonexistent-endpoint

# Или создайте тестовый endpoint для ошибки (если нужно)
```

Откройте Glitchtip UI:
- Projects → `sattva-tv-backend` → Issues
- Должны появиться ошибки (если есть)

---

### Шаг 6: Тестирование логирования (Loki)

**6.1. Проверьте запуск Loki и Promtail:**

```bash
docker ps --filter "name=loki" --format "table {{.Names}}\t{{.Status}}"
docker ps --filter "name=promtail" --format "table {{.Names}}\t{{.Status}}"
```

Должны быть запущены контейнеры:
- `sattva-loki` (Up X seconds)
- `sattva-promtail` (Up X seconds)

**6.2. Проверьте Grafana Logs:**

1. Откройте http://localhost:3001
2. Login: `admin` / `admin123`
3. Explore (левая панель, иконка компаса)
4. Выберите datasource: **Loki**
5. Query: `{app="sattva-tv"}`
6. Click "Run query"
7. Должны появиться логи backend

**6.3. Проверьте Logs Overview Dashboard:**

1. Dashboards → Browse
2. Найдите: **Logs Overview**
3. Откройте дашборд
4. Должны быть графики и таблицы с логами

---

## 🐛 Troubleshooting

### Frontend: Warning "VITE_SENTRY_DSN not set"

**Причина:** DSN пустой в `.env.development`

**Решение:**
1. Создайте проект в Glitchtip UI
2. Скопируйте DSN
3. Добавьте в `frontend/.env.development`
4. Перезапустите: `docker compose restart frontend`

### Glitchtip UI не открывается

```bash
# Проверка логов
docker logs sattva-glitchtip-web --tail 50

# Проверка статуса
docker ps --filter "name=glitchtip"

# Перезапуск
docker compose -f docker-compose.glitchtip.yml restart
```

### Ошибки не появляются в Glitchtip

**Проверки:**
1. DSN корректный? (должен начинаться с `http://` и содержать `@localhost:8080`)
2. Контейнеры перезапущены после добавления DSN?
3. Worker запущен? `docker logs sattva-glitchtip-worker`
4. Ошибка действительно произошла? (проверьте Console/Network в DevTools)

### Loki не показывает логи

```bash
# Проверка Loki
curl http://localhost:3100/ready

# Проверка Promtail
docker logs sattva-promtail --tail 50

# Перезапуск
docker compose -f docker-compose.monitoring.yml restart loki promtail
```

---

## 📚 Документация

- **Полная документация:** [docs/deployment/LOGGING_AND_ERROR_TRACKING_SETUP.md](../deployment/LOGGING_AND_ERROR_TRACKING_SETUP.md)
- **Quick Start:** [docs/deployment/QUICK_START_LOGGING_AND_ERRORS.md](../deployment/QUICK_START_LOGGING_AND_ERRORS.md)
- **Manual Setup:** [docs/deployment/GLITCHTIP_MANUAL_SETUP.md](../deployment/GLITCHTIP_MANUAL_SETUP.md)
- **Phase 2.2-2.3 Report:** [docs/REPORTS/PHASE_2.2_2.3_COMPLETE.md](../REPORTS/PHASE_2.2_2.3_COMPLETE.md)

---

## 🎯 Следующий Phase (после тестирования)

**Phase 3: Testing**
- Unit tests (Backend coverage > 70%, Frontend > 60%)
- Integration tests (API contract testing)
- E2E tests (Playwright)

См. [docs/development/refactoring-roadmap.md](../development/refactoring-roadmap.md) для деталей.

---

## ✅ Checklist

После выполнения всех шагов убедитесь:

- [ ] Glitchtip UI открывается (http://localhost:8080)
- [ ] Организация "Sattva TV" создана
- [ ] Backend проект создан, DSN скопирован
- [ ] Frontend проект создан, DSN скопирован
- [ ] DSN добавлены в .env файлы
- [ ] Контейнеры перезапущены
- [ ] Frontend: нет warning про VITE_SENTRY_DSN
- [ ] Frontend: тестовая ошибка появилась в Glitchtip
- [ ] Grafana Logs: логи видны (http://localhost:3001)
- [ ] Logs Overview dashboard работает

**Всё готово к production deployment! 🚀**
