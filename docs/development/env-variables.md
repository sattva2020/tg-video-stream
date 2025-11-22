 

# Переменные окружения

## Быстрый старт
1. Скопируйте шаблон: `cp .env.template .env`


   Альтернатива: можно использовать скрипт генерации `.env` из шаблона — это удобно, если вы хотите автогенерацию секретов и безопасную перезапись:

   ```bash
   # Создаёт .env из .env.template (интерактивно)
   ./scripts/generate_env.sh

   # Non-interactive вариант (перезапишет .env)
   ./scripts/generate_env.sh --non-interactive --force

   # Автогенерация JWT_SECRET
   ./scripts/generate_env.sh --random-secrets --force
   ```
2. Заполните значения вместо плейсхолдеров `change_this_*`

3. Проверьте права доступа: `chmod 600 .env`

4. Перезапустите сервис/compose, чтобы новые значения попали в приложения


> Шаблон `.env.template` является единственным источником правды. Добавляя новые переменные, сначала обновляйте шаблон, а потом генерируйте `.env`.


## Ключевые группы переменных

### Telegram Broadcast

| Переменная | Назначение |
| --- | --- |
| `API_ID`, `API_HASH` | Ключи Telegram API, полученные на <https://my.telegram.org/apps> |
| `SESSION_STRING` | Сессионная строка Pyrogram/Telethon для авторизованного аккаунта |
| `CHAT_ID` | Канал/чат, в который отправляются видеопотоки |
| `VIDEO_QUALITY` | Предустановленный профиль качества (`best`, `720p`, кастомный фильтр ffmpeg) |
| `LOOP` | Повтор плейлиста (`true/false`) |
| `FFMPEG_ARGS` | Дополнительные параметры кодирования; оставьте пустым для профилей по умолчанию |

### Сервис и наблюдаемость

| Переменная | Назначение |
| --- | --- |
| `PROMETHEUS_PORT` | Порт экспорта метрик; при занятости переключается на следующий |
| `ENVIRONMENT` | Контур деплоя (`development`, `staging`, `production`) |
| `LOG_LEVEL` | Уровень логирования FastAPI/воркеров |
| `SERVICE_NAME` | Идентификатор сервиса в логах и мониторинге |

### Backend API & Auth

| Переменная | Назначение |
| --- | --- |
| `DATABASE_URL` | Строка подключения SQLAlchemy (PostgreSQL в проде, SQLite в тестах) |
| `REDIS_URL` | Redis для rate-limiting и фоновых задач |
| `JWT_SECRET` | Секрет для подписи JWT и сессий FastAPI |
| `ALGORITHM` | Алгоритм подписи токенов (по умолчанию `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | TTL access токена в минутах |
| `RATE_LIMIT_MAX`, `RATE_LIMIT_WINDOW` | Порог и окно rate limiter для auth эндпоинтов |
| `HIBP_ENABLED` | Включение проверки пароля через HaveIBeenPwned (`true/false`) |
| `FRONTEND_BASE_URL`, `BACKEND_BASE_URL` | Базы URL для формирования ссылок в письмах и редиректах |

### OAuth / Google

| Переменная | Назначение |
| --- | --- |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | OAuth 2.0 креды Google для входа и линковки аккаунтов |

### SMTP и Email

| Переменная | Назначение |
| --- | --- |
| `SMTP_HOST`, `SMTP_PORT` | SMTP-сервер и порт (587/465/1025) |
| `SMTP_USER`, `SMTP_PASS` | Учетные данные почтового ящика |
| `SMTP_FROM` | Адрес отправителя по умолчанию для писем подтверждения и линковки |


## Проверка
- Скрипты/сервисы должны читать конфиг из `.env` в корне репозитория
- CI/CD не хранит секреты — используйте Variables/Secrets в рантайме

- Никогда не коммитьте реальные ключи: используйте плейсхолдеры и описывайте процесс заполнения в документации (как здесь)

### Защита от случайного коммита `.env`

Рекомендуется установить pre-commit hook, который предотвратит коммиты `.env`:

1. Установите pre-commit (если еще не установлен):

```bash
pip install pre-commit
pre-commit install
```


2\. В репозитории уже есть `.pre-commit-config.yaml` и `scripts/prevent_commit_env.sh`. Они настроены для блокировки коммита `.env` — достаточно выполнить `pre-commit install`.

3\. Для ручной проверки хуков выполните:

```bash
> Замечание: в CI/CD (`.github/workflows/ci.yml`) pre-commit запускается автоматически перед запуском тестов — CI упадёт, если хуки не пройдут.
pre-commit run --all-files

> Workflow `precommit_feature.yml` triggers pre-commit on `staging` and `feature/**` branches and on PRs into `staging`/`main`.
> Это дополнительный шаг, который гарантирует, что автформатирование и статический анализ пройдены до слияния.
```

