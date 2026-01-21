# Деплой через Dokploy

**Последнее обновление**: 27 декабря 2025

Dokploy — это self-hosted PaaS (альтернатива Vercel/Heroku/Netlify), который упрощает деплой и управление приложениями.

## Преимущества Dokploy

| Функция | Описание |
|---------|----------|
| **UI панель** | Веб-интерфейс для управления деплоями |
| **Environment Variables** | Безопасное хранение секретов в UI |
| **Auto Deploy** | Автоматический деплой при push в Git |
| **Traefik** | Автоматическая настройка HTTPS и routing |
| **Docker Compose** | Нативная поддержка compose файлов |
| **Мониторинг** | CPU, RAM, Network в реальном времени |
| **Уведомления** | Telegram, Slack, Discord, Email |
| **Бэкапы** | Автоматические бэкапы в S3 |

## Сравнение способов деплоя

| Критерий | sops + scripts | Dokploy |
|----------|---------------|---------|
| Секреты | `.env.enc` (sops) | UI панель |
| SSL | Certbot вручную | Автоматически (Traefik) |
| Мониторинг | Prometheus/Grafana | Встроенный |
| CI/CD | Ручные скрипты | Webhooks/API |
| Rollback | `rollback_release.sh` | UI кнопка |
| Сложность | Средняя | Низкая |

## Быстрый старт

### 1. Установка Dokploy на VPS

```bash
# Требования: Ubuntu 22.04+, 2GB RAM, Docker
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144

# Установка (одна команда)
curl -sSL https://dokploy.com/install.sh | sh
```

После установки Dokploy будет доступен на: `https://dokploy.sattva-ai.top/dashboard/projects`

### 2. Первоначальная настройка

1. Откройте `https://dokploy.sattva-ai.top/dashboard/projects`
2. Создайте admin аккаунт
3. Настройте домен (Settings → Server → Domain)

### 3. Создание проекта tg-streamer

> **Статус**: ✅ Проект уже развёрнут и работает

#### Текущая структура проекта

**Проект**: `tg-streamer` (production environment)

**Сервисы**:

1. ✅ **sattva-app** (Compose) — основной стек приложения
  - GitHub: `github.com/sattva2020/tg-video-stream.git`
  - Branch: `main`
  - Compose Path: `docker-compose.dokploy.yml`
  - Домен: `sattva-streamer.top`
  - Включает: frontend, PostgreSQL, Redis, backend-proxy (Traefik → systemd backend)

2. ✅ **tg-engine** (Application) — Telegram engine
   - GitHub: `github.com/sattva2020/tg-video-stream.git`
   - Branch: `main`
   - Build Path: `/tg-engine`
   - Dockerfile: `tg-engine/Dockerfile`
   - Описание: AyuGram headless Telegram engine

#### Если нужно создать проект с нуля:

<details>
<summary>Развернуть инструкцию</summary>

##### Шаг 1: Создать проект

1. Откройте `https://dokploy.sattva-ai.top/dashboard/projects`
2. Нажмите кнопку **+ Create Project**
3. Введите имя: `tg-streamer`
4. Описание: `24/7 Telegram Video Streamer`
5. Нажмите **Create**

##### Шаг 2: Добавить Docker Compose сервис (sattva-app)

1. Откройте проект `tg-streamer`
2. Нажмите **+ Add Service** → выберите **Compose**
3. Настройте:
   - **Name**: `sattva-app`
   - **Source Type**: Git
   - **Repository**: ваш репозиторий
   - **Branch**: `main`
   - **Compose Path**: `docker-compose.dokploy.yml` ⚠️ **ВАЖНО!**
4. Нажмите **Create**

##### Шаг 3: Добавить TG Engine (отдельный Application)

> **Важно**: TG Engine требует длительной сборки, поэтому деплоим отдельно.

1. В проекте нажмите **+ Add Service** → **Application**
2. Настройте:
   - **Name**: `tg-engine`
   - **Source Type**: Git
   - **Repository**: тот же репозиторий
   - **Branch**: `main`
   - **Build Type**: Dockerfile
   - **Build Path**: `/tg-engine`
   - **Dockerfile Path**: `tg-engine/Dockerfile`
3. Нажмите **Create**

</details>

### 4. Настройка Environment Variables

> **Статус**: ✅ Переменные уже настроены в Dokploy UI

В Dokploy секреты хранятся безопасно в UI:

1. Откройте проект → сервис **sattva-app** → вкладка **Environment**
2. Текущие переменные (уже настроены):

```env
# Domain (автоматически устанавливается Dokploy)
DOMAIN=${project.DOMAIN}

# Database
DB_PASSWORD=$4dQ*yKSpTK6E^CNz7*b
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/telegram_db

# JWT
JWT_SECRET=IvAInkSqEEzbi7DfVfhtu5MEpDKn61ly
SESSION_ENCRYPTION_KEY=YyPjZWReBsJZlYxV4cKj-prBjJJtqGcGWODTzj9dERs=

# Telegram
API_ID=37831214
API_HASH=1a10843db60c599ce2ec67bc6a55f1c2
TELEGRAM_BOT_TOKEN=8431060192:AAEBOCf9BEu4H3YhTt8Aj8-cvIeoCie1lsA

# Google OAuth
GOOGLE_CLIENT_ID=134449806518-tavv2bfsrjnndmivp6tgiithcphcs997.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# URLs (используют переменную DOMAIN из Dokploy)
FRONTEND_URL=https://sattva-streamer.top
BACKEND_URL=https://sattva-streamer.top
```

⚠️ **Важно**: После изменения Environment Variables нажмите **Save**, затем сделайте **Redeploy**!

### 5. Настройка Docker Compose

Используйте специальный compose файл для Dokploy:

```yaml
# docker-compose.dokploy.yml
version: '3.8'

services:
  backend-proxy:
    image: alpine:3.19
    command: ["sh", "-c", "sleep infinity"]
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`sattva-streamer.top`) && PathPrefix(`/api`)"
      - "traefik.http.services.backend.loadbalancer.server.url=http://172.17.0.1:8000"

  frontend:
    build: ./frontend
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`sattva-streamer.top`)"

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=telegram_db
    volumes:
      - ../files/postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - ../files/redis_data:/data
```

### 6. Настройка домена

> **Статус**: ✅ Домен уже настроен

**Текущая конфигурация**:

- **Host**: `sattva-streamer.top`
- **SSL**: Автоматически через Let's Encrypt (Traefik)
- **Services**:
  - `frontend` → `/` (Container Port: 80)
  - `backend-proxy` → `/api` (Traefik → systemd backend)

> ⚠️ Внешний Nginx на хосте должен быть отключён, иначе будет конфликт портов 80/443.

Если нужно добавить новый домен:

1. Откройте сервис → вкладка **Domains**
2. Нажмите **Add Domain**
3. Настройте:
   - **Service Name**: `frontend` или `backend`
   - **Host**: `your-domain.com`
   - **Path**: `/` (для frontend) или `/api` (для backend)
   - **Container Port**: `80` (frontend) или `8000` (backend)
   - **HTTPS**: включить
4. Нажмите **Save**
5. Traefik автоматически получит SSL сертификат

### 7. Auto Deploy (CI/CD)

#### Вариант A: GitHub Webhook

1. В Dokploy включите **Auto Deploy** в настройках проекта
2. Скопируйте Webhook URL
3. В GitHub: **Settings** → **Webhooks** → добавьте URL
4. Теперь каждый push будет триггерить деплой

#### Вариант B: API деплой

```bash
# Получить API токен в Dokploy: Profile → API Tokens

# Получить ID приложения
curl -X GET 'https://dokploy.sattva-ai.top/api/project.all' \
  -H 'x-api-key: YOUR_API_TOKEN'

# Триггерить деплой
curl -X POST 'https://sattva-streamer.top:3000/api/compose.deploy' \
  -H 'x-api-key: YOUR_API_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"composeId": "YOUR_COMPOSE_ID"}'
```

## Скрипты автоматизации

### Локальный деплой через API

```bash
./scripts/deploy-dokploy.sh
```

### Миграция с sops на Dokploy

```bash
./scripts/migrate-to-dokploy.sh
```

## Структура файлов

```
├── docker-compose.dokploy.yml    # Compose для Dokploy
├── scripts/
│   ├── deploy-dokploy.sh         # Деплой через API
│   ├── migrate-to-dokploy.sh     # Миграция секретов
│   └── setup-dokploy.sh          # Установка Dokploy
└── docs/deployment/
    └── DOKPLOY_DEPLOYMENT.md     # Эта документация
```

## Мониторинг и уведомления

### Встроенный мониторинг

Dokploy автоматически показывает:
- CPU/RAM/Disk использование
- Network трафик
- Логи контейнеров
- История деплоев

### Telegram уведомления

1. **Settings** → **Notifications** → **Telegram**
2. Введите Bot Token и Chat ID
3. Выберите события: Deploy Success, Deploy Failed, etc.

## Бэкапы

### Настройка S3 бэкапов

1. **Settings** → **S3 Destinations** → добавьте bucket
2. **Volume Backups** → выберите volumes для бэкапа
3. Настройте расписание

### Ручной бэкап базы

```bash
# Через UI: Database → Backups → Create Backup
# Или через API
curl -X POST 'https://sattva-streamer.top:3000/api/backup.create' \
  -H 'x-api-key: YOUR_API_TOKEN' \
  -d '{"databaseId": "YOUR_DB_ID"}'
```

## Rollback

### Через UI

1. **Deployments** → выберите предыдущий успешный деплой
2. Нажмите **Rollback**

### Через API

```bash
curl -X POST 'https://sattva-streamer.top:3000/api/compose.redeploy' \
  -H 'x-api-key: YOUR_API_TOKEN' \
  -d '{"composeId": "ID", "commit": "PREVIOUS_COMMIT_SHA"}'
```

## Troubleshooting

### Dokploy не запускается

```bash
# Проверить логи
docker logs dokploy

# Перезапустить
docker restart dokploy
```

### Ошибка деплоя

1. Проверьте логи в **Deployments** → выберите деплой → **View Logs**
2. Проверьте Environment Variables
3. Убедитесь что Docker Compose валидный

### SSL не работает

1. Убедитесь что домен указывает на IP сервера
2. Проверьте что порт 443 открыт
3. Traefik автоматически получит сертификат

## Сравнение с текущим подходом

### Когда использовать sops + scripts

- Нужен полный контроль над инфраструктурой
- Уже настроенный CI/CD pipeline
- Требуется интеграция с HashiCorp Vault
- Минимальный overhead на сервере

### Когда использовать Dokploy

- Быстрый старт без глубоких знаний DevOps
- Нужен UI для управления
- Команда без DevOps специалиста
- Простое масштабирование

## Связанные файлы

- [docs/deployment/SECRETS_DEPLOYMENT.md](SECRETS_DEPLOYMENT.md) — деплой через sops
- [docs/deployment/DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) — общий чек-лист
- [docker-compose.dokploy.yml](../../docker-compose.dokploy.yml) — compose для Dokploy
