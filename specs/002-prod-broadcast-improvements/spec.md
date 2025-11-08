```markdown
# Feature Specification: Production Broadcast Improvements

**Feature Branch**: `002-prod-broadcast-improvements`  
**Created**: 2025-11-08  
**Status**: Draft  
**Input**: Улучшения (по опыту продакшн-вещания): надежное восстановление сессии, автоперезапуск systemd, автообновление yt-dlp, FFMPEG_ARGS в .env, права .env 600, systemd hardening, Prometheus metrics, CI перезапуск сервиса

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Надёжное восстановление сессии (Priority: P1)

Как оператор сервиса, я хочу, чтобы при устаревшей или недействительной Telegram сессии приложение логично сообщало об этом и предлагало путь восстановления (автоперегенерация/чёткий диагностический лог), чтобы минимизировать время простоя вещания.

**Why this priority**: Без корректной session string сервис не может выйти из degraded-mode — это блокер для продакшн-вещания.

**Independent Test**: Искусственно вызвать исключение SessionExpired (или использовать старую/искажённую SESSION_STRING) и убедиться, что приложение логирует понятное сообщение, завершает или инициирует безопасное поведение (в случае автоперегенерации — запрашивает/инициирует поток генерации сессии и завершает процесс корректно если не удалось).

**Acceptance Scenarios**:

1. **Given** устаревшая SESSION_STRING, **When** приложение стартует, **Then** в лог записывается заметное сообщение об истёкшей сессии и exit code = 1 (или инициируется процесс регенерации если включён режим автоперегенерации).
2. **Given** режим автоперегенерации включён, **When** SessionExpired перехвачен, **Then** приложение запускает безопасный helper (локально) или предлагает инструкцию для оператора — и логирует шаги.

**Auto-regeneration Mode Details**: Режим автоперегенерации активируется через флаг `--write-env` в `test/auto_session_runner.py`. **Поток выполнения**:
1. Оператор обнаруживает `SessionExpired` в логах
2. Запускает: `python test/auto_session_runner.py --write-env`
3. Helper запрашивает телефон и код подтверждения (интерактивный ввод)
4. Генерирует новую SESSION_STRING
5. Обновляет локальный `.env` файл безопасно (atomic write с backup)
6. Логирует результат (masked SESSION_STRING, например `SESSION_STRING=***...abcd`)
7. Exit code: 0 (успех) или 1 (ошибка)
8. После успешного обновления оператор вручную перезапускает сервис: `systemctl restart tg_video_streamer` или запускает deploy CI

**Конкурентный доступ**: Deploy и auto_session_runner.py не должны запускаться одновременно (риск коррупции .env). CI должна документировать эту зависимость.

---

### User Story 2 - Контроль цикла и автоперезапуск systemd (Priority: P1)

Как оператор, я хочу чтобы systemd автоматически перезапускал сервис после сбоя с небольшим backoff, чтобы минимизировать ручное вмешательство.

**Why this priority**: Автоматическое восстановление уменьшит MTTR и обеспечит непрерывность вещания.

**Independent Test**: Вынудить падение процесса (raise exception) и проверить, что systemd перезапустил сервис через ~10 секунд и что рестарт ограничен в разумных пределах.

**Acceptance Scenarios**:

1. **Given** краш процесса, **When** systemd видит упавший unit, **Then** он перезапускает unit с Restart=always и RestartSec=10.

---

### User Story 3 - Автообновление зависимостей yt-dlp (Priority: P2)

Как оператор, я хочу, чтобы `yt-dlp` автоматически обновлялся по расписанию, чтобы минимизировать проблемы со скачиванием контента из-за изменений сайтов.

**Why this priority**: yt-dlp часто обновляется для поддержания совместимости с сайтами; автоматизация уменьшит ручную поддержку.

**Independent Test**: Запустить cron/systemd timer вручную и проверить лог `/var/log/yt-dlp-update.log` — команда `pip install -U yt-dlp` должна завершиться успешно и логировать вывод.

**Acceptance Scenarios**:

1. **Given** таймер/cron, **When** наступило расписание, **Then** выполняется `/opt/.../venv/bin/pip install -U yt-dlp` и результат логируется в `/var/log/yt-dlp-update.log`.

---

### User Story 4 - Тонкая настройка качества видео через FFMPEG_ARGS (Priority: P2)

Как оператор, я хочу управлять аргументами ffmpeg через переменную окружения `FFMPEG_ARGS` в `.env`, чтобы иметь гибкость настройки битрейта и кодека без правки кода.

**Why this priority**: Быстрая подстройка качества важна при разных условиях сети и хостинга.

**Independent Test**: Установить `FFMPEG_ARGS` в `.env`, запустить локально команду, и проверить, что `main.py` собирает аргументы через `os.environ.get('FFMPEG_ARGS','').split()` и передаёт их в вызов ffmpeg.

**Acceptance Scenarios**:

1. **Given** корректный `FFMPEG_ARGS` в `.env`, **When** сервис стартует, **Then** ffmpeg запускается с переданными флагами и поток соответствует указанным параметрам.

---

### User Story 5 - Безопасность и ограничения доступа (Priority: P1)

Как оператор, я хочу, чтобы `.env` имел права `600`, владелец — системный пользователь (например, `tgstream`/`telegram`), и чтобы systemd запускал сервис от непривилегированного пользователя с дополнительными защитными опциями (`ProtectSystem=full`, `NoNewPrivileges=yes`, `PrivateTmp=true`).

**Why this priority**: Защищённое хранение секретов и принципы least-privilege критичны для продуктивной среды.

**Independent Test**: Проверить права файла и владельца (`stat`), проверить юнит systemd содержит указанные параметры и что сервис стартует под непривилегированным пользователем.

**Acceptance Scenarios**:

1. **Given** новый релиз, **When** deploy происходит, **Then** `.env` на хосте имеет `chmod 600` и владелец соответствует `tgstream`.
2. **Given** systemd unit, **When** его описали, **Then** unit содержит `ProtectSystem=full`, `NoNewPrivileges=yes`, `PrivateTmp=true`.

---

### User Story 6 - Мониторинг Prometheus (Priority: P2)

Как SRE, я хочу экспортировать базовые метрики Prometheus (количество проигранных треков и т.п.) на HTTP-порт (например, 9090), чтобы подключить Grafana и следить за здоровьем вещания.

**Why this priority**: Метрики дают быстрый взгляд на активность и помогают при инцидентах.

**Independent Test**: Запустить сервис и сделать HTTP-запрос к `:9090/metrics`, убедиться, что метрики присутствуют (например, `streams_played_total`).

**Acceptance Scenarios**:

1. **Given** сервис запущен, **When** обращаются к `/metrics`, **Then** Prometheus-сервер может scrape-ить метрики и в них есть `streams_played_total`.

---

### User Story 7 - CI/CD: перезапуск systemd после deploy (Priority: P2)

Как DevOps, я хочу, чтобы workflow CI включал шаг перезапуска systemd на хосте после успешного deploy, чтобы деплой автоматически приводил систему в рабочее состояние.

**Why this priority**: Автоматизация снижает ручные шаги при релизе.

**Independent Test**: Запустить CI job (или локально выполнить ssh-строку) и проверить, что `systemctl restart tg_video_streamer` выполнен и сервис перезапущен.

**Acceptance Scenarios**:

1. **Given** успешный пакет и deploy, **When** CI достигает шага restart, **Then** сервер перезапускает сервис и возвращает статус Active=active.

---

### Edge Cases

- Ошибки сети во время автоматического обновления `yt-dlp` (логирование и повторная попытка на следующем расписании, не в текущем цикле).  
- Некорректный формат `FFMPEG_ARGS` (валидировать и откатывать к безопасному профилю; логировать WARNING).  
- Prometheus-порт занят (логировать ERROR и fallback: попытка следующего свободного портаили file-based metrics; сервис продолжает работу без Prometheus).
- Session expires mid-stream (Telegram отключает токен во время трансляции): логировать ERROR, pause stream, attempt regen, switch to degraded mode if regen fails.
- Конкурентный доступ к .env (deploy пишет, app читает): используется atomic write (temp → mv) в auto_session_runner.py; deploy script также использует atomic write.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Приложение MUST перехватывать `pyrogram.errors.SessionExpired` и логировать понятное сообщение с рекомендацией действий.
- **FR-002**: При настроенном режиме автоперегенерации приложение MUST инициировать безопасный поток генерации новой сессии через `test/auto_session_runner.py --write-env`; при успехе обновить `.env` и exit(0), при ошибке логировать и exit(1).
- **FR-003**: systemd unit MUST содержать `Restart=always`, `RestartSec=10`, `StartLimitInterval=0` (или эквивалент) для автоматического восстановления.
- **FR-004**: Система MUST иметь расписание (systemd-timer) для еженедельного обновления `yt-dlp` (по умолчанию Sunday 02:00 UTC) и логировать результаты в `/var/log/yt-dlp-update.log`.
- **FR-005**: Приложение MUST поддерживать `FFMPEG_ARGS` из `.env` (space-separated, double-quote escaping; fallback if invalid) и корректно передавать их ffmpeg-процессу.
- **FR-006**: Deploy pipeline MUST устанавливать права `.env` как `600` и владельца — `tgstream` (или указанного непривилегированного пользователя).
- **FR-007**: systemd unit MUST include sandboxing options: `ProtectSystem=full`, `NoNewPrivileges=yes`, `PrivateTmp=true`.
- **FR-008**: Приложение MUST expose Prometheus metrics on configurable порт (по умолчанию 9090) type=Counter, включая минимум счётчик `streams_played_total` (инкрементируется на 1 для каждого трека); если порт занят, логировать ERROR и attempt использовать следующий свободный, или fallback на file-based metrics с логированием WARNING.
- **FR-009**: CI pipeline MUST include a step to restart the systemd unit on the remote host after deploy with 60s timeout; validate Active state; if restart fails → CI job fails with non-zero exit code.
- **FR-010** *(NEW)*: MUST вывести приложение в degraded mode если SESSION_STRING невалиден или аутентификация не удалась. Degraded mode поведение: нет попыток streaming, логировать WARN "Degraded mode; SESSION_STRING invalid; run: python test/auto_session_runner.py --write-env", периодические попытки переаутентификации каждые 60s с логированием результата.

## Key Entities

- **Session**: SESSION_STRING — credential blob for Telegram client; lifecycle: valid → expired → regenerated/replaced.  
- **Release**: per-release directory deployed to `/opt/tg_video_streamer/releases/<id>` and symlinked to `current`.  
- **Metric**: `streams_played_total` and any additional custom counters exposed to Prometheus.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: При искусственном SessionExpired приложение корректно логирует причину и exit code = 1 (или инициирует автоперегенерацию при включённом режиме) — 100% воспроизводимость.
- **SC-002**: После краша unit systemd перезапускает сервис в течение 10-12 секунд в 95% случаев тестов (локальные симуляции рестартов).
- **SC-003**: Еженедельное обновление `yt-dlp` успешно выполняется и логируется, ошибки фиксируются и повторяются в следующем окне; успешных обновлений >= 95% за 30 дней.
- **SC-004**: Метрика `streams_played_total` доступна на `/metrics` и корректно увеличивается при проигрывании роликов.

## Assumptions

- На хосте установлен Python 3.12 и systemd; есть непривилегированный пользователь `tgstream` (или аналог), и deploy pipeline имеет права для смены владельца/прав на `.env` и перезапуска unit.
- CI имеет SSH-доступ к хосту и возможность выполнять `sudo systemctl restart tg_video_streamer` без интерактивного ввода пароля (через sudoers для deploy user).
- Обновление `yt-dlp` выполняется в рамках per-release venv (путь к venv доступен и корректен в CRON/systemd-timer).

## Next Steps

1. Внести правки в `main.py`: добавить перехват `SessionExpired` и аккуратную обработку/логирование; добавить опциональный режим автоперегенерации.
2. Обновить systemd unit шаблон `tg_video_streamer.service` с указанными параметрами и добавить systemd-timer или cron для yt-dlp.
3. Добавить чтение `FFMPEG_ARGS` из `.env` и передачу в ffmpeg-вызов.
4. Добавить Prometheus-экспортёр в код и документацию/quickstart по включению мониторинга.
5. Обновить CI workflow для выполнения restart шага после успешного deploy.

---

**Spec status**: Draft — ready for review.

```