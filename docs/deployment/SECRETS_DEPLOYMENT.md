# Деплой секретов на VPS (sops + age)

**Последнее обновление**: 27 декабря 2025

## Быстрый старт

### 1. Первоначальная настройка сервера (один раз)

```bash
# Установить sops на VPS
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 <<'EOF'
curl -LO https://github.com/getsops/sops/releases/download/v3.9.4/sops-v3.9.4.linux.amd64
chmod +x sops-v3.9.4.linux.amd64
mv sops-v3.9.4.linux.amd64 /usr/local/bin/sops
sops --version
EOF

# Передать age ключ на сервер
scp -i ~/.ssh/id_rsa_n8n .internal/age.key root@37.53.91.144:/opt/tg_video_streamer/.age.key

# Установить права
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 "chmod 600 /opt/tg_video_streamer/.age.key"
```

### 2. Локальная подготовка

```bash
# Зашифровать секреты (если изменились)
SOPS_AGE_KEY_FILE=.internal/age.key ./scripts/encrypt-secrets.sh .env.master

# Проверить расшифровку
SOPS_AGE_KEY_FILE=.internal/age.key ./scripts/preflight-env.sh

# Собрать артефакт (включит .env.enc)
./scripts/build_artifact.sh
```

### 3. Деплой

```bash
# Полный деплой с автоматической расшифровкой на сервере
./scripts/deploy_full.sh
```

## Как это работает

```
Локально                          VPS
─────────────────────────────────────────────────────────
.env.master ─┐
             │ encrypt
             ▼
         .env.enc ──────────► .env.enc (в артефакте)
                                    │
                     .age.key ──────┼─► sops decrypt
                                    │
                                    ▼
                               .env (расшифрован)
                                    │
                        ┌───────────┴───────────┐
                        ▼                       ▼
                 backend/.env            frontend/.env
```

## Файлы

| Файл | Описание | Git |
|------|----------|-----|
| `.env.master` | Мастер-файл всех секретов | ❌ |
| `.env.enc` | Зашифрованная версия | ✅ |
| `.internal/age.key` | Приватный ключ | ❌ |
| `.internal/age.pub` | Публичный ключ | ✅ |

## Скрипты

| Скрипт | Назначение |
|--------|------------|
| `scripts/encrypt-secrets.sh` | Шифрование `.env.master` → `.env.enc` |
| `scripts/decrypt-secrets.sh` | Расшифровка и split на backend/frontend |
| `scripts/preflight-env.sh` | Проверка расшифровки (для CI/CD) |
| `scripts/build_artifact.sh` | Сборка артефакта (включает `.env.enc`) |
| `scripts/deploy_full.sh` | Полный деплой с расшифровкой |
| `scripts/remote_deploy.sh` | Выполняется на сервере (расшифровка) |

## Ротация ключей

При компрометации ключа:

```bash
# 1. Сгенерировать новый ключ
age-keygen -o .internal/age.key.new

# 2. Расшифровать старым ключом, зашифровать новым
SOPS_AGE_KEY_FILE=.internal/age.key sops --decrypt .env.enc > .env.tmp
mv .internal/age.key.new .internal/age.key
SOPS_AGE_KEY_FILE=.internal/age.key sops --encrypt --age $(cat .internal/age.pub) .env.tmp > .env.enc
rm .env.tmp

# 3. Передать новый ключ на сервер
scp -i ~/.ssh/id_rsa_n8n .internal/age.key root@37.53.91.144:/opt/tg_video_streamer/.age.key

# 4. Уничтожить старый ключ
```

## Troubleshooting

### Ошибка: "sops not found"
```bash
# Установить sops на сервере
curl -LO https://github.com/getsops/sops/releases/download/v3.9.4/sops-v3.9.4.linux.amd64
chmod +x sops-v3.9.4.linux.amd64
mv sops-v3.9.4.linux.amd64 /usr/local/bin/sops
```

### Ошибка: "SOPS_AGE_KEY_FILE or SOPS_AGE_KEY is required"
```bash
# Проверить ключ на сервере
ssh -i ~/.ssh/id_rsa_n8n root@37.53.91.144 "ls -la /opt/tg_video_streamer/.age.key"

# Если отсутствует — передать
scp -i ~/.ssh/id_rsa_n8n .internal/age.key root@37.53.91.144:/opt/tg_video_streamer/.age.key
```

### Ошибка: "invalid dotenv input"
```bash
# Проверить формат файла (не должно быть пустых строк)
cat .env.master | grep -v '^$' > .env.master.clean
mv .env.master.clean .env.master
```

## Связанные файлы

- [docs/development/secret-management.md](../development/secret-management.md) — полная документация
- [docs/deployment/DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) — чек-лист деплоя
