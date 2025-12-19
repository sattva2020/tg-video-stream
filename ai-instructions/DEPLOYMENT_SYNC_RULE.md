# Правило синхронизации локального и удалённого репозиториев

## ⚠️ КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО ДЛЯ AI-АГЕНТОВ

### Принцип: LOCAL-FIRST (Локальный репозиторий первичен)

**ВСЕ изменения ОБЯЗАТЕЛЬНО должны сначала вноситься в локальный репозиторий, а затем деплоиться на удалённый сервер.**

---

## Обязательный порядок действий

### 1. Изменения в коде

```text
1. Редактировать файл ЛОКАЛЬНО
2. git add + git commit + git push
3. SSH на сервер: git pull + build/restart
```

### 2. Изменения в конфигурации (.env, config файлы)

```text
1. Редактировать файл ЛОКАЛЬНО (корневой .env, frontend/.env, backend/.env)
2. SSH на сервер: обновить соответствующий .env файл
3. Если нужен rebuild: git pull + npm run build
4. Если нужен restart: systemctl restart service
```

### 3. Изменения только на сервере (emergency fix)

```text
1. Сделать изменение на сервере
2. НЕМЕДЛЕННО внести то же изменение в локальный репозиторий
3. Задокументировать в коммите: "sync: emergency fix from server"
```

---

## Чек-лист перед завершением задачи

- [ ] Все изменения кода есть в локальном репозитории?
- [ ] Все .env переменные добавлены локально?
  - [ ] Корневой `.env`
  - [ ] `frontend/.env` (VITE_* переменные)
  - [ ] `backend/.env` (если используется)
- [ ] Изменения закоммичены и запушены?
- [ ] Сервер обновлён через git pull?

---

## Типичные ошибки (НЕ ДОПУСКАТЬ!)

- ❌ Добавить переменную только в .env на сервере
- ❌ Создать файл только на сервере через SSH
- ❌ Изменить конфиг на сервере без синхронизации
- ❌ Забыть про frontend/.env при добавлении VITE_* переменных

---

## Структура .env файлов

| Файл | Назначение | Где используется |
| ------ | ------------ | ------------------ |
| `.env` | Основные переменные проекта | Docker, backend, общие |
| `frontend/.env` | Vite переменные (VITE_*) | Frontend build |
| `backend/.env` | Backend-специфичные | Python/FastAPI |

### Правило для VITE переменных

Если добавляется `VITE_*` переменная:

1. Добавить в `frontend/.env` локально
2. Добавить в `/opt/sattva-streamer/frontend/.env` на сервере
3. Выполнить `npm run build` на сервере

---

## Пример правильного workflow

### Добавление TELEGRAM_BOT_ID

```bash
# 1. ЛОКАЛЬНО: редактируем .env
echo "TELEGRAM_BOT_ID=8431060192" >> .env

# 2. ЛОКАЛЬНО: редактируем frontend/.env
echo "VITE_TELEGRAM_BOT_ID=8431060192" >> frontend/.env

# 3. Коммитим (если .env не в .gitignore)
# или документируем в README/docs

# 4. НА СЕРВЕРЕ: добавляем в .env
ssh user@server "echo 'TELEGRAM_BOT_ID=8431060192' >> /opt/app/.env"
ssh user@server "echo 'VITE_TELEGRAM_BOT_ID=8431060192' >> /opt/app/frontend/.env"

# 5. НА СЕРВЕРЕ: rebuild если нужно
ssh user@server "cd /opt/app/frontend && npm run build"
```

---

## Дата создания правила

30 ноября 2025

## Причина создания

AI-агент добавил `VITE_TELEGRAM_BOT_ID` только на удалённый сервер, не обновив локальный репозиторий. Это привело к рассинхронизации и потенциальным проблемам при будущих деплоях.

---

**Это правило ОБЯЗАТЕЛЬНО для выполнения при КАЖДОМ изменении!**

---

## 🏗️ Архитектура деплоймента (Hybrid: Systemd + Docker)

### ⚠️ КРИТИЧЕСКИ ВАЖНО: Почему НЕ Docker для Backend/Streamer

**Причина**: YouTube постоянно меняет API, что требует регулярного обновления `yt-dlp`.
При использовании Docker обновление зависимостей требует пересборки образа, что усложняет процесс.

**Решение**: Backend и Streamer работают через **systemd** на хосте, а не в Docker.

### Архитектура сервисов

| Сервис | Метод запуска | Причина |
| -------- | --------------- | --------- |
| **Backend (FastAPI)** | `systemd` | Требует обновления yt-dlp на лету |
| **Streamer (PyTgCalls)** | `systemd` | Требует обновления yt-dlp на лету |
| **Frontend (Nginx)** | `Docker` | Статический контент, не требует обновлений |
| **PostgreSQL** | `Docker` | Стабильный, не требует частых обновлений |
| **Redis** | `Docker` | Стабильный |
| **Prometheus/Grafana** | `Docker` | Мониторинг, изолированный |

### Автообновление yt-dlp

```bash
# Cron задача (04:00 ежедневно)
0 4 * * * /opt/sattva-streamer/backend/venv/bin/pip install -U yt-dlp && systemctl restart sattva-backend sattva-streamer
```

### Конфигурация nginx для связи с хостом

```nginx
# frontend/nginx.conf
location /api/ {
    # Backend на хосте (systemd), не в Docker!
    proxy_pass http://172.17.0.1:8000;
    ...
}
```

**172.17.0.1** — IP адрес docker0 интерфейса, через который Docker-контейнеры обращаются к хосту.

### Systemd сервисы

Файлы в `/etc/systemd/system/`:

- `sattva-backend.service` — FastAPI backend
- `sattva-streamer.service` — PyTgCalls streamer

### Команды управления

```bash
# Backend
systemctl status sattva-backend
systemctl restart sattva-backend
journalctl -u sattva-backend -f

# Streamer  
systemctl status sattva-streamer
systemctl restart sattva-streamer
journalctl -u sattva-streamer -f

# Frontend (Docker)
docker compose restart frontend
docker logs sattva-streamer-frontend-1
```

### ❌ Типичные ошибки (НЕ ДОПУСКАТЬ!)

- Запускать backend через `docker compose up backend` — конфликт портов с systemd!
- Забыть остановить Docker backend после включения systemd сервиса
- Использовать `proxy_pass http://backend:8000` — Docker DNS не резолвит systemd сервис!

### ✅ Правильный порядок запуска

```bash
# 1. Проверить что systemd сервисы работают
systemctl status sattva-backend sattva-streamer

# 2. Запустить Docker сервисы (БЕЗ backend!)
docker compose up -d db redis frontend prometheus grafana alertmanager

# 3. НЕ запускать docker backend!
# docker compose up -d backend  ← НЕ ДЕЛАТЬ!
```

---

## ⚠️ Важно: не допускать дубля streamer через Docker

Если streamer запущен через `systemd`, нельзя одновременно поднимать docker-сервис `streamer` — он тоже подписывается на Redis канал `stream:control` и начнёт обрабатывать команды параллельно.

В `docker-compose.yml` сервис `streamer` вынесен в профиль `docker-streamer`, чтобы **не стартовать по умолчанию**.

Для локальных экспериментов запускать явно:

```bash
docker compose --profile docker-streamer up -d streamer
```

Канонический runtime на VPS описан в: `docs/development/VPS_CANONICAL_RUNTIME.md`.

---

**Дата добавления правила**: 1 декабря 2025  
**Причина**: AI-агент случайно включил Docker backend, что привело к конфликту с systemd сервисом на порту 8000.

