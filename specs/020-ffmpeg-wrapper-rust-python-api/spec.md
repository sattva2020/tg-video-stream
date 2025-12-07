# Feature Specification: Rust FFmpeg Microservice

**Feature Branch**: `020-ffmpeg-wrapper-rust-python-api`  
**Created**: 7 декабря 2025  
**Status**: Draft  
**Input**: User description: "рассмотрите возможность выноса движка вещания (FFmpeg wrapper) в отдельный микросервис на Rust, оставив Python для API"

## Обзор

Вынос "движка" вещания (FFmpeg wrapper, транскодирование, управление потоками) в отдельный высокопроизводительный микросервис на Rust. Python остаётся для API, оркестрации и бизнес-логики. Это позволит:
- Улучшить производительность обработки медиа
- Снизить потребление памяти (Rust без GC)
- Повысить надёжность и предсказуемость latency
- Независимо масштабировать компоненты

## Текущая архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                     streamer/ (Python)                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ main.py        - PyTgCalls + FFmpeg orchestration           ││
│  │ audio_utils.py - Transcoding profiles, playlist parsing     ││
│  │ utils.py       - FFmpeg args builder, yt-dlp integration    ││
│  │ multi_channel.py - Multi-channel state management           ││
│  │ queue_manager.py - Redis-backed queue                       ││
│  │ playback_control.py - Speed, EQ, position tracking          ││
│  └─────────────────────────────────────────────────────────────┘│
│                              ▼                                   │
│                    subprocess.run(ffmpeg...)                     │
│                    PyTgCalls → Telegram                          │
└─────────────────────────────────────────────────────────────────┘
```

## Предлагаемая архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    Python Services                               │
│  ┌─────────────────┐   ┌──────────────────────────────────────┐ │
│  │   Backend API   │   │      Streamer Orchestrator           │ │
│  │   (FastAPI)     │   │ - Queue management (Redis)           │ │
│  │                 │   │ - Playlist logic                     │ │
│  │   /api/...      │   │ - Channel state                      │ │
│  │   /api/...      │   │ - PyTgCalls (Telegram integration)   │ │
│  └─────────────────┘   └──────────────────────────────────────┘ │
│                                      │                           │
│                                      │ HTTP (REST)               │
│                                      ▼                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │               Rust FFmpeg Microservice                       ││
│  │  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐  ││
│  │  │ Transcode API  │  │ Stream Muxer   │  │ Audio Filters │  ││
│  │  │ - Profiles     │  │ - HLS/DASH     │  │ - EQ presets  │  ││
│  │  │ - Quality      │  │ - Raw pipe     │  │ - Speed ctrl  │  ││
│  │  └────────────────┘  └────────────────┘  └───────────────┘  ││
│  │                                                              ││
│  │  ffmpeg-next (Rust bindings) / direct libav* calls          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Базовое транскодирование через Rust сервис (Priority: P1)

Администратор добавляет трек в плейлист. Python-оркестратор отправляет запрос в Rust-сервис на транскодирование. Rust-сервис возвращает поток в нужном формате (Opus/AAC) для PyTgCalls.

**Why this priority**: Базовая функциональность — без неё остальные фичи невозможны.

**Independent Test**: Можно протестировать изолированно, отправив HTTP/gRPC запрос в Rust-сервис с URL аудиофайла и получив транскодированный поток.

**Acceptance Scenarios**:

1. **Given** Rust-сервис запущен, **When** отправлен запрос на транскодирование MP3→Opus, **Then** возвращается поток Opus 48kHz с корректным битрейтом
2. **Given** входной файл FLAC, **When** запрос на транскодирование с профилем "lowlatency", **Then** возвращается Opus с -application lowdelay
3. **Given** некорректный URL, **When** запрос на транскодирование, **Then** возвращается ошибка с кодом и описанием

---

### User Story 2 - Применение аудио-фильтров (EQ, скорость) (Priority: P2)

Оператор меняет скорость воспроизведения или эквалайзер через UI. Python-оркестратор передаёт параметры фильтров в Rust-сервис. Изменения применяются к текущему потоку в реальном времени.

**Why this priority**: Дифференцирующая функциональность для продвинутых пользователей.

**Independent Test**: Отправить запрос с параметрами `speed=1.25` и `eq_preset=bass_boost`, проверить что выходной поток соответствует ожиданиям.

**Acceptance Scenarios**:

1. **Given** активный поток, **When** запрос на изменение скорости 1.0→1.5, **Then** скорость воспроизведения меняется без прерывания
2. **Given** активный поток, **When** применяется preset "voice", **Then** фильтр эквалайзера применяется
3. **Given** недопустимое значение скорости (например, 10.0), **When** запрос, **Then** возвращается ошибка валидации

---

### User Story 3 - Мониторинг и метрики Rust-сервиса (Priority: P3)

DevOps инженер может отслеживать производительность Rust-сервиса: CPU, память, latency транскодирования, количество активных потоков.

**Why this priority**: Необходимо для production-ready решения, но не блокирует базовую функциональность.

**Independent Test**: Запросить endpoint /metrics, проверить наличие ключевых метрик.

**Acceptance Scenarios**:

1. **Given** Rust-сервис обрабатывает потоки, **When** запрос /metrics, **Then** возвращаются метрики (active_streams, transcode_latency_ms, memory_usage_bytes)
2. **Given** сервис простаивает, **When** запрос /health, **Then** возвращается статус healthy с версией

---

### User Story 4 - Graceful degradation при недоступности Rust-сервиса (Priority: P2)

Если Rust-сервис недоступен, Python-оркестратор автоматически переключается на локальный subprocess ffmpeg (текущая реализация) с логированием предупреждения.


**Why this priority**: Критично для production — нельзя терять вещание из-за отказа одного компонента.

**Independent Test**: Остановить Rust-сервис, проверить что вещание продолжается через fallback.

**Acceptance Scenarios**:

1. **Given** Rust-сервис недоступен (connection refused), **When** запрос на транскодирование, **Then** Python использует subprocess ffmpeg и логирует предупреждение
2. **Given** Rust-сервис вернулся в строй, **When** следующий запрос, **Then** автоматически используется Rust-сервис

---

### Edge Cases

- Что происходит при разрыве соединения с Rust-сервисом во время транскодирования? → Graceful fallback + retry
- Как обрабатывается исчерпание памяти в Rust-сервисе? → OOM handler, метрики, алерты
- Что если входной файл повреждён? → Возврат структурированной ошибки, fallback на следующий трек
- Как обрабатываются одновременные запросы на транскодирование? → Bounded concurrency через tokio::sync::Semaphore (max 50 concurrent)
- Что если формат входного файла не поддерживается? → Попытка через ffmpeg, ошибка если невозможно

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Rust-сервис MUST принимать запросы на транскодирование через HTTP REST API
- **FR-002**: Rust-сервис MUST поддерживать входные форматы: MP3, AAC, FLAC, OGG, WAV, M4A, Opus
- **FR-003**: Rust-сервис MUST выводить в форматах Opus (48kHz, 96-128kbps), AAC (48kHz, 128kbps) и raw PCM
- **FR-004**: Rust-сервис MUST поддерживать streaming output (не буферизировать весь файл)
- **FR-005**: Rust-сервис MUST применять аудио-фильтры: изменение скорости (0.5-2.0x), эквалайзер (presets)
- **FR-006**: Python-оркестратор MUST иметь fallback на subprocess ffmpeg при недоступности Rust-сервиса
- **FR-007**: Rust-сервис MUST предоставлять health check endpoint (/health)
- **FR-008**: Rust-сервис MUST экспортировать метрики в формате Prometheus (/metrics)
- **FR-009**: Python-оркестратор MUST передавать параметры транскодирования через конфигурируемый клиент
- **FR-010**: Rust-сервис MUST корректно обрабатывать SIGTERM для graceful shutdown
- **FR-011**: Система MUST логировать все операции транскодирования с timing метриками
- **FR-012**: Rust-сервис MUST возвращать структурированные ошибки с кодами и описаниями

### Key Entities

- **TranscodeRequest**: Запрос на транскодирование (source_url, output_format, filters, quality_preset)
- **TranscodeStream**: Активный поток транскодирования (id, state, progress, metrics)
- **AudioFilter**: Параметры аудио-обработки (speed, eq_preset, volume)
- **ServiceHealth**: Статус Rust-сервиса (status, version, uptime, active_streams)
- **TranscodeError**: Структурированная ошибка (code, message, details, recoverable)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Latency старта транскодирования не превышает 200ms (от запроса до первых байт output)
- **SC-002**: Потребление памяти Rust-сервиса не превышает 256MB при 10 одновременных потоках
- **SC-003**: CPU utilization снижается на 30% по сравнению с subprocess ffmpeg при 10 concurrent streams на 4 vCPU VPS
- **SC-004**: 99.9% uptime вещания благодаря graceful fallback
- **SC-005**: Время переключения на fallback не превышает 3 секунды
- **SC-006**: Rust-сервис обрабатывает до 50 одновременных потоков транскодирования

## Assumptions

- FFmpeg или libav* доступны на сервере (либо статически слинкованы в Rust binary)
- Сетевая latency между Python и Rust-сервисами минимальна (они на одном хосте или в одной сети Docker)
- Используется Rust 1.75+ с async runtime (tokio)
- Для MVP допустимо использовать REST API; gRPC — как оптимизация в следующих итерациях

## Out of Scope

- Видео транскодирование (только аудио в рамках этой фичи)
- Замена PyTgCalls (он остаётся в Python для Telegram интеграции)
- Автоматическое масштабирование Rust-сервисов (Kubernetes HPA и т.п.)
- Web UI для управления Rust-сервисом напрямую

## Risks & Mitigations

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Сложность интеграции ffmpeg-next | Средняя | Высокое | Начать с subprocess ffmpeg в Rust, затем мигрировать на bindings |
| Увеличение сложности деплоя | Низкая | Среднее | Docker Compose с обоими сервисами, единая точка входа |
| Рост latency из-за сетевого вызова | Низкая | Среднее | Unix socket или localhost, streaming вместо buffering |
| Нехватка Rust-экспертизы в команде | Средняя | Высокое | Хорошая документация, простой API, fallback на Python |

## Appendix: Текущие компоненты для миграции

Файлы/функции которые будут частично или полностью перенесены в Rust:

1. **streamer/audio_utils.py**:
   - `TRANSCODING_PROFILES` → Rust enum/struct
   - `get_transcoding_profile()` → Rust matcher
   
2. **streamer/utils.py**:
   - `build_ffmpeg_av_args()` → Rust command builder
   
3. **streamer/audio_filters.py**:
   - EQ presets → Rust audio filter chain

Python оркестратор сохранит:
- PyTgCalls интеграцию (main.py)
- Очередь и Redis (queue_manager.py)
- Multi-channel state (multi_channel.py)
- API endpoints (backend/)
