# Настройка GitHub Secrets для CD Pipeline

**Дата**: 29.11.2025  
**Ветка**: 012-project-improvements

---

## Обзор

CD pipeline (`cd.yml`) автоматически деплоит проект на VPS при push в `main` ветку или вручную через workflow dispatch.

## Требуемые секреты

### 1. SSH_PRIVATE_KEY (обязательный)

SSH ключ для подключения к VPS.

**Настройка:**

1. На VPS генерируем пару ключей (если не существует):
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy
   ```

2. Добавляем публичный ключ в authorized_keys:
   ```bash
   cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

3. Копируем приватный ключ:
   ```bash
   cat ~/.ssh/github_deploy
   ```

4. В GitHub репозитории:
   - Переходим в **Settings** → **Secrets and variables** → **Actions**
   - Нажимаем **New repository secret**
   - Name: `SSH_PRIVATE_KEY`
   - Value: содержимое приватного ключа (включая `-----BEGIN...` и `-----END...`)

### 2. Опциональные секреты

| Секрет | Описание | Использование |
|--------|----------|---------------|
| `TELEGRAM_BOT_TOKEN` | Токен бота для уведомлений | Оповещения о деплое |
| `TELEGRAM_CHAT_ID` | ID чата для уведомлений | Оповещения о деплое |
| `SENTRY_DSN` | DSN для Sentry | Мониторинг ошибок |

## Environments

Репозиторий использует GitHub Environments для разделения staging/production:

### Staging
- **URL**: http://37.53.91.144:3000
- **Триггер**: автоматический при push в main
- **Защита**: нет

### Production
- **URL**: http://37.53.91.144:3000
- **Триггер**: ручной через workflow dispatch
- **Защита**: требуется approval

**Настройка Environment:**

1. **Settings** → **Environments** → **New environment**
2. Создать `staging` и `production`
3. Для `production`:
   - Включить **Required reviewers**
   - Добавить необходимых reviewers
   - Опционально: включить **Wait timer** (например, 5 минут)

## Проверка настройки

### 1. Тест SSH подключения

```bash
# Локально (с приватным ключом)
ssh -i ~/.ssh/github_deploy root@37.53.91.144 "echo 'Connection OK'"
```

### 2. Тест workflow

```bash
# Через GitHub CLI
gh workflow run cd.yml -f environment=staging
```

### 3. Мониторинг деплоя

- **Actions tab**: https://github.com/sattva2020/tg-video-stream/actions
- **Логи на сервере**: `docker compose logs -f`

## Rollback

При неудачном деплое выполняется автоматический rollback. Для ручного:

```bash
# SSH на сервер
ssh root@37.53.91.144

# Перейти в директорию проекта
cd /root/telegram-broadcast

# Посмотреть предыдущий коммит
cat .previous_commit

# Откатиться
git checkout <commit_hash>
docker compose up -d --build
```

Или использовать скрипт:
```bash
./scripts/rollback_release.sh
```

## Безопасность

1. **Никогда** не коммитьте приватные ключи в репозиторий
2. Используйте отдельный SSH ключ только для GitHub Actions
3. Ограничьте права ключа на сервере (только deploy директория)
4. Регулярно ротируйте ключи

## Troubleshooting

### "Permission denied (publickey)"
- Проверьте что публичный ключ добавлен в `~/.ssh/authorized_keys`
- Проверьте права: `chmod 600 ~/.ssh/authorized_keys`

### "Host key verification failed"
- Добавлен `StrictHostKeyChecking=no` в ssh-action

### "Health check failed"
- Проверьте логи: `docker compose logs backend`
- Проверьте статус: `docker compose ps`
- Откатитесь к предыдущей версии

---

## Чеклист для нового репозитория

- [ ] Создать SSH ключ для деплоя
- [ ] Добавить публичный ключ на сервер
- [ ] Добавить `SSH_PRIVATE_KEY` секрет в GitHub
- [ ] Создать environments (staging, production)
- [ ] Настроить protection rules для production
- [ ] Протестировать workflow вручную
