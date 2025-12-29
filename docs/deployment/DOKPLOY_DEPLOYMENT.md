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

После установки Dokploy будет доступен на: `http://37.53.91.144:3000`

### 2. Первоначальная настройка

1. Откройте `http://37.53.91.144:3000`
2. Создайте admin аккаунт
3. Настройте домен (Settings → Server → Domain)

### 3. Создание проекта

1. **Projects** → **Create Project** → `sattva-streamer`
2. **Create Service** → **Docker Compose**
3. Выберите источник: **Git** → укажите репозиторий

### 4. Настройка Environment Variables

В Dokploy секреты хранятся безопасно в UI:

1. Откройте проект → **Environment**
2. Добавьте переменные:

```env
# Database
DB_PASSWORD=sattva_db_pass_2025_9f3c0f
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/telegram_db

# JWT
JWT_SECRET=IvAInkSqEEzbi7DfVfhtu5MEpDKn61ly
SESSION_ENCRYPTION_KEY=639n3cZMDnZyU7plIZqbgUmxFORHw8hBlD6WzqXNmO0=

# Telegram
API_ID=37831214
API_HASH=1a10843db60c599ce2ec67bc6a55f1c2
TELEGRAM_BOT_TOKEN=8431060192:AAEBOCf9BEu4H3YhTt8Aj8-cvIeoCie1lsA

# Google OAuth
GOOGLE_CLIENT_ID=134449806518-tavv2bfsrjnndmivp6tgiithcphcs997.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# URLs (Dokploy автоматически подставит домен)
FRONTEND_URL=https://sattva-streamer.top
BACKEND_URL=https://sattva-streamer.top
```

### 5. Настройка Docker Compose

Используйте специальный compose файл для Dokploy:

```yaml
# docker-compose.dokploy.yml
version: '3.8'

services:
  backend:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.backend.rule=Host(`sattva-streamer.top`) && PathPrefix(`/api`)"

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

1. **Domains** → **Add Domain**
2. Введите: `sattva-streamer.top`
3. Dokploy автоматически настроит SSL через Let's Encrypt

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
curl -X GET 'https://sattva-streamer.top:3000/api/project.all' \
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
