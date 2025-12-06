# Архитектура деплоймента

**Версия документа**: 1.0  
**Дата создания**: 1 декабря 2025  
**Статус**: Актуален

## Обзор

Проект использует **гибридную архитектуру** деплоймента: часть сервисов работает через systemd на хосте, часть — в Docker-контейнерах.

## Почему гибридная архитектура?

### Проблема с Docker для Backend/Streamer

**YouTube постоянно меняет API**, что требует регулярного обновления `yt-dlp`. При использовании Docker:
- Обновление требует пересборки образа
- Downtime при rebuild/restart
- Усложнённый процесс обновления

### Решение

- **Backend и Streamer** работают через `systemd` на хосте
- **Вспомогательные сервисы** (DB, Redis, мониторинг) работают в Docker
- **yt-dlp** обновляется автоматически через cron без пересборки

## Архитектура сервисов

```
┌─────────────────────────────────────────────────────────────┐
│                        VPS (Ubuntu)                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              SYSTEMD (на хосте)                      │    │
│  │                                                      │    │
│  │  ┌─────────────────┐    ┌─────────────────┐         │    │
│  │  │ sattva-streamer │    │ yt-dlp-update   │         │    │
│  │  │  (PyTgCalls)    │    │   (timer)       │         │    │
│  │  │  + yt-dlp       │    │  04:00 UTC      │         │    │
│  │  └─────────────────┘    └─────────────────┘         │    │
│  │           │                      │                   │    │
│  │           └──────────────────────┘                   │    │
│  │                 streamer/venv                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│                    localhost (Redis :6379)                   │
│                          │                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  DOCKER COMPOSE                      │    │
│  │                                                      │    │
│  │  ┌──────────┐  ┌──────────┐  ┌───────┐  ┌───────┐   │    │
│  │  │ frontend │  │ backend  │  │  db   │  │ redis │   │    │
│  │  │ (nginx)  │  │ (FastAPI)│  │(pg15) │  │(redis)│   │    │
│  │  │  :3000   │  │  :8000   │  │ :5432 │  │ :6379 │   │    │
│  │  └──────────┘  └──────────┘  └───────┘  └───────┘   │    │
│  │                                                      │    │
│  │  ┌────────────┐  ┌─────────────┐  ┌──────────────┐  │    │
│  │  │ prometheus │  │   grafana   │  │ alertmanager │  │    │
│  │  │   :9090    │  │    :3001    │  │    :9093     │  │    │
│  │  └────────────┘  └─────────────┘  └──────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Детальная таблица сервисов

| Сервис | Метод | Порт | Причина выбора |
|--------|-------|------|----------------|
| Backend (FastAPI) | `Docker` | 8000 | Стабильный, не требует yt-dlp |
| Streamer (PyTgCalls) | `systemd` | — | Требует частых обновлений yt-dlp |
| Frontend (Nginx) | `Docker` | 3000 | Статика, стабильный |
| PostgreSQL | `Docker` | 5432 | Стабильный, изолированный |
| Redis | `Docker` | 6379 | Стабильный |
| Prometheus | `Docker` | 9090 | Мониторинг |
| Grafana | `Docker` | 3001 | Мониторинг |
| Alertmanager | `Docker` | 9093 | Алерты |

## Автообновление yt-dlp

### Systemd Timer (04:00 UTC)

```bash
# Включение таймера
systemctl enable --now yt-dlp-update.timer

# Проверка следующего запуска
systemctl list-timers yt-dlp-update.timer
```

### Скрипт обновления

```bash
#!/bin/bash
# /opt/sattva-streamer/scripts/yt-dlp-update.sh

echo "$(date): Starting yt-dlp update..."

# Обновление yt-dlp в streamer venv
/opt/sattva-streamer/streamer/venv/bin/pip install -U yt-dlp

# Перезапуск streamer
systemctl restart sattva-streamer

echo "$(date): yt-dlp update completed"
```

## Конфигурация Nginx (Frontend)

```nginx
# frontend/nginx.conf
server {
    listen 80;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        # Backend на хосте через systemd (НЕ в Docker!)
        # 172.17.0.1 — IP адрес docker0 интерфейса
        proxy_pass http://172.17.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Systemd Unit Files

### Backend Service

```ini
# /etc/systemd/system/sattva-backend.service
[Unit]
Description=Sattva Streamer Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sattva-streamer/backend
Environment="PATH=/opt/sattva-streamer/backend/venv/bin"
ExecStart=/opt/sattva-streamer/backend/venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Streamer Service

```ini
# /etc/systemd/system/sattva-streamer.service
[Unit]
Description=Sattva Telegram Streamer
After=network.target sattva-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sattva-streamer/streamer
Environment="PATH=/opt/sattva-streamer/streamer/venv/bin"
ExecStart=/opt/sattva-streamer/streamer/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Команды управления

### Systemd сервисы

```bash
# Статус
systemctl status sattva-backend
systemctl status sattva-streamer

# Перезапуск
systemctl restart sattva-backend
systemctl restart sattva-streamer

# Логи (в реальном времени)
journalctl -u sattva-backend -f
journalctl -u sattva-streamer -f

# Логи (последние 100 строк)
journalctl -u sattva-backend -n 100
```

### Docker сервисы

```bash
# Статус всех контейнеров
docker ps

# Перезапуск frontend
docker compose restart frontend

# Логи frontend
docker logs sattva-streamer-frontend-1 -f

# Полный перезапуск всех Docker сервисов
docker compose down && docker compose up -d
```

## Порядок запуска

### Правильный порядок

```bash
# 1. Запустить Docker сервисы (БЕЗ backend!)
cd /opt/sattva-streamer
docker compose up -d db redis frontend prometheus grafana alertmanager

# 2. Дождаться готовности БД
sleep 10

# 3. Запустить systemd сервисы
systemctl start sattva-backend
systemctl start sattva-streamer

# 4. Проверить статус
systemctl status sattva-backend sattva-streamer
docker ps
```

### ⚠️ Что НЕ делать

```bash
# ❌ НЕ запускать backend через Docker!
docker compose up -d backend  # НЕПРАВИЛЬНО! Конфликт портов!

# ❌ НЕ использовать docker-compose для всех сервисов
docker compose up -d  # НЕПРАВИЛЬНО! Включит Docker backend!
```

## Troubleshooting

### Конфликт порта 8000

```bash
# Проверить что занимает порт
lsof -i :8000

# Если Docker backend — остановить
docker stop sattva-streamer-backend-1

# Перезапустить systemd backend
systemctl restart sattva-backend
```

### Nginx 502 Bad Gateway

```bash
# Проверить что backend работает
curl http://localhost:8000/health

# Проверить логи nginx
docker logs sattva-streamer-frontend-1

# Проверить доступность из контейнера
docker exec sattva-streamer-frontend-1 wget -q -O- http://172.17.0.1:8000/health
```

### yt-dlp ошибки

```bash
# Ручное обновление
/opt/sattva-streamer/backend/venv/bin/pip install -U yt-dlp

# Проверить версию
/opt/sattva-streamer/backend/venv/bin/yt-dlp --version

# Перезапуск сервисов
systemctl restart sattva-backend sattva-streamer
```

## Связанные документы

- [DEPLOYMENT_SYNC_RULE.md](../../ai-instructions/DEPLOYMENT_SYNC_RULE.md) — правила синхронизации
- [BUSINESS_REQUIREMENTS.md](../BUSINESS_REQUIREMENTS.md) — бизнес-требования
- [docker-compose.yml](../../docker-compose.yml) — конфигурация Docker
