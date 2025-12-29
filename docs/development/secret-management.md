# Управление секретами (sops + age)

**Статус:** ✅ Полностью реализовано (27 декабря 2025)

## Цель
Безопасно хранить переменные окружения и обеспечить воспроизводимый деплой без утечек секретов.

## Политика
- Секреты не коммитятся в репозиторий.
- В Git хранятся только *.env.example* с плейсхолдерами.
- Шифрованные копии *.env* допускаются только в формате *.env.enc* (sops+age) и не содержат боевых ключей по умолчанию.
- Ключ age хранится вне репозитория (секретный менеджер/Password Manager). Не кладём его в Git, не отправляем в мессенджеры.

## Инструменты
- **sops** для шифрования файлов `.env` → `.env.enc`.
- **age** как бэкенд ключей (один ключ для команды).

## Структура файлов
- `.env.example` — корень (плейсхолдеры, добавлен DB_PASSWORD).
- `frontend/.env.example` — Vite переменные (API, Telegram, Turnstile, тема).
- `backend/.env.example` — backend переменные, ссылается на `DB_PASSWORD` из корня.
- Шифрованный вариант: один `.env.enc` в корне (содержит все переменные). После расшифровки разделяем на:
   - `backend/.env` — все строки, кроме `VITE_*`
   - `frontend/.env` — только `VITE_*`

## Быстрый старт (sops + age)
1. Установить sops и age.
2. Сгенерировать ключ age (один раз):
   ```bash
   age-keygen -o .internal/age.key
   chmod 600 .internal/age.key
   ```
3. Создать файл реальных секретов (локально): `.env` (корень, включает и backend, и VITE_*).
4. Зашифровать (один файл):
   ```bash
   SOPS_AGE_KEY_FILE=.internal/age.key sops --encrypt --output .env.enc .env
   ```
   Открытый `.env` удалить/переместить в `.internal/`.
5. Расшифровать при работе:
   ```bash
   SOPS_AGE_KEY_FILE=.internal/age.key sops --decrypt .env.enc > .env
   ```
   После этого сформировать производные файлы для сервисов (см. ниже).

### Разделение после расшифровки (локально или на сервере)
```bash
# Предполагается, что .env уже расшифрован из .env.enc
mkdir -p backend frontend
grep -Ev '^VITE_' .env > backend/.env
grep -E '^VITE_' .env > frontend/.env
```
Если frontend требует только публичные значения, держим в `frontend/.env` исключительно `VITE_*`.

### Команды: генерация *.env.enc* (один файл)
```bash
# 1) Подготовить рабочий файл на базе примера
cp .env.example .env

# 2) Заполнить реальные значения в .env (включая VITE_*)

# 3) Зашифровать в .env.enc с ключом age
SOPS_AGE_KEY_FILE=.internal/age.key sops --encrypt --output .env.enc .env

# 4) Удалить/перенести открытый .env (оставить .env.enc и .env.example)
shred -u .env 2>/dev/null || rm -f .env
```

### Команды: расшифровка перед сборкой/запуском
```bash
# Используем файл ключа
SOPS_AGE_KEY_FILE=.internal/age.key sops --decrypt .env.enc > .env

# Или через переменную (CI/CD): SOPS_AGE_KEY="<private_key>"
SOPS_AGE_KEY="$SOPS_AGE_KEY" sops --decrypt .env.enc > .env

# Разложить по сервисам
mkdir -p backend frontend
grep -Ev '^VITE_' .env > backend/.env
grep -E '^VITE_' .env > frontend/.env
```

### Preflight перед деплоем (без вывода секретов)
```bash
./scripts/preflight-env.sh
# Переменные:
#   ENV_ENC_PATH   путь к .env.enc (по умолчанию .env.enc)
#   SOPS_AGE_KEY_FILE или SOPS_AGE_KEY
```
В CI добавлен джоб `env-preflight` (см. `.github/workflows/ci.yml`), который запускается только если в репозитории присутствует `.env.enc` и использует секрет `SOPS_AGE_KEY`.

## Скрипты автоматизации

| Скрипт | Описание |
|--------|----------|
| `scripts/encrypt-secrets.sh` | Шифрует `.env.master` → `.env.enc` |
| `scripts/decrypt-secrets.sh` | Расшифровывает `.env.enc` и создаёт `backend/.env`, `frontend/.env` |
| `scripts/preflight-env.sh` | Проверяет возможность расшифровки (без вывода секретов) |

### Пример использования

```bash
# Шифрование (после редактирования .env.master)
SOPS_AGE_KEY_FILE=.internal/age.key ./scripts/encrypt-secrets.sh .env.master

# Расшифровка (перед запуском/деплоем)
SOPS_AGE_KEY_FILE=.internal/age.key ./scripts/decrypt-secrets.sh

# Dry-run (проверить что будет создано)
./scripts/decrypt-secrets.sh --dry-run

# Принудительная перезапись существующих файлов
./scripts/decrypt-secrets.sh --force
```

## Ротация
- При утечке или смене доступа — выпустить новый ключ age, заново зашифровать *.env* и распространить новый ключ через безопасный канал.
- После ротации старый ключ уничтожить.

## Требования к деплою
- В CI/CD или на сервере должен быть доступ к age-ключу (секретный менеджер, переменная среды `SOPS_AGE_KEY`, или монтируемый файл `SOPS_AGE_KEY_FILE`).
- Скрипты деплоя должны выполнять расшифровку перед сборкой/запуском контейнеров.

## Чек-лист перед коммитом
- [ ] В рабочей директории нет открытых `.env`, только `.env.enc` (при необходимости) и `.env.example`.
- [ ] Ключ age не находится в репозитории.
- [ ] Плейсхолдеры в `.env.example`/`frontend/.env.example`/`backend/.env.example` актуальны и покрывают все используемые переменные.

## Связанные файлы
- [docs/development/refactoring-roadmap.md](refactoring-roadmap.md)
- [PROJECT_STRUCTURE_GUIDELINES.md](../../PROJECT_STRUCTURE_GUIDELINES.md)
