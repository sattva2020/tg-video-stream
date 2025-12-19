# Канонический runtime на VPS (release-based)

**Дата:** 18 декабря 2025  
**Цель:** убрать путаницу между `/opt/sattva-streamer` и `/opt/tg_video_streamer` и исключить дубли обработчиков Redis-команд.

## Канонический путь

На VPS канонический runtime развернут в release-based структуре:

- `/opt/tg_video_streamer/releases/<timestamp>/` — конкретный релиз (immutable)
- `/opt/tg_video_streamer/current` — симлинк на активный релиз

Это позволяет:

- безопасно делать откаты (переключением `current`)
- иметь предсказуемый web-root для nginx
- исключать «деплой в не ту папку»

## Web-root nginx

Фронтенд должен раздаваться из:

- `/opt/tg_video_streamer/current/frontend/dist`

Если изменения не видны в браузере — сначала проверяйте реальный `root` в конфиге nginx.

## Стример: единственный подписчик Redis

В проде должен существовать **ровно один** процесс, подписанный на `stream:control`.

### Источник истины

- `systemd` сервис: `tg_video_streamer`

### Почему нельзя одновременно запускать docker-стример

Если поднять контейнер `streamer` из `docker compose`, он тоже подпишется на `stream:control`, и команды начнут обрабатываться дважды (гонки, конкурирующие обновления, нестабильное поведение).

## Как проверять (обязательный минимум)

### 1) Проверка количества подписчиков

```bash
redis-cli -h 127.0.0.1 PUBSUB NUMSUB stream:control
```

Ожидаем:

- `stream:control 1`

### 2) Диагностика дублей

```bash
redis-cli -h 127.0.0.1 CLIENT LIST | grep -E "sub|subscribe" -i
```

### 3) Быстрый тест доставки

```bash
redis-cli -h 127.0.0.1 PUBLISH stream:control '{"action":"noop","channel_id":"debug"}'
journalctl -u tg_video_streamer --since "1 min ago" --no-pager
```

## Docker Compose: стример под profile

В репозитории сервис `streamer` помечен как profile `docker-streamer`.

- По умолчанию он **не стартует** при `docker compose up -d`.
- Для локальных экспериментов запускать только явно:

```bash
docker compose --profile docker-streamer up -d streamer
```

## Legacy директория `/opt/sattva-streamer`

`/opt/sattva-streamer` может встречаться на сервере как исторический каталог/клон.

Правило:

- не использовать его как источник истины для деплоя
- не поднимать из него docker-стример в проде

Дополнительно на VPS legacy systemd unit `sattva-streamer.service` должен быть **masked** (symlink на `/dev/null`), чтобы его нельзя было случайно запустить.

Проверка:

```bash
systemctl is-enabled sattva-streamer.service
```

Ожидаем: `masked`

---

Если нужно — могу дополнить документ точными командами переключения релизов через `current` и шаблоном безопасного rollback.
