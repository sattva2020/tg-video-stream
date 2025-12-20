# Release metadata и smoke-тесты деплоя

Дата: 2025-12-20  
Автор: Jarvis

## Зачем это нужно

В продакшене важно быстро понимать:
- **какой именно билд** раскатан на сервере;
- **когда** он был собран и раскатан;
- что базовые компоненты (systemd сервис, nginx, фронтенд) реально в рабочем состоянии.

Чтобы не гадать по косвенным признакам, добавлены файлы метаданных релиза и smoke-тесты.

## Release metadata

### 1) RELEASE_META.json (в артефакте)

Файл создаётся при сборке артефакта скриптом:
- [scripts/build_artifact.sh](../../scripts/build_artifact.sh)

И попадает в корень tar-артефакта.
Содержит:
- `artifact_name` — имя файла артефакта
- `build_time_utc` — время сборки (UTC)
- `git_sha`, `git_branch` — git-идентификаторы (если сборка выполнялась внутри git-репозитория)
- `git_dirty` — `true/false/null` (null, если git недоступен)

### 2) DEPLOY_META.json (на сервере)

Файл создаётся при раскатке релиза скриптом:
- [scripts/remote_deploy.sh](../../scripts/remote_deploy.sh)

Записывается в директорию релиза (`releases/<ver>/DEPLOY_META.json`) и копируется в:
- `/opt/tg_video_streamer/current/DEPLOY_META.json`

Это позволяет быстро проверить текущий релиз без поиска по каталогам.

## Smoke-тесты

### 1) Проверка, что артефакт содержит RELEASE_META.json

- [tests/smoke/test_artifact_release_meta.sh](../../tests/smoke/test_artifact_release_meta.sh)

Запуск:

```bash
./tests/smoke/test_artifact_release_meta.sh
```

Тест:
- находит последний `telegram-deploy-*.tar.gz` (или пытается собрать его, если `frontend/dist` уже существует);
- проверяет наличие `RELEASE_META.json` внутри tar;
- валидирует JSON (парсинг + обязательные ключи).

### 2) Smoke-check VPS после деплоя

- [tests/smoke/test_vps_release_smoke.sh](../../tests/smoke/test_vps_release_smoke.sh)

Запуск:

```bash
./tests/smoke/test_vps_release_smoke.sh
```

Проверки на сервере:
- `current` symlink резолвится;
- существует `frontend/dist/index.html`;
- существуют `current/RELEASE_META.json` и `current/DEPLOY_META.json`;
- `systemctl is-active tg_video_streamer` == active;
- `nginx -t` проходит.

## Примечания

- Smoke-тесты не должны требовать секретов, кроме локального SSH-ключа для VPS (у вас он уже используется в текущем процессе деплоя).
- Это не заменяет полноценные e2e, но сильно ускоряет диагностику «что именно раскатано и живо ли оно».
