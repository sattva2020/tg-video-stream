# Data Model: Rust FFmpeg Microservice

**Feature**: 020-ffmpeg-wrapper-rust-python-api  
**Date**: 7 декабря 2025  
**Phase**: 1 - Design & Contracts

## Entities

### TranscodeRequest

Запрос на транскодирование аудио.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| source_url | string (URL) | ✅ | URL источника аудио (HTTP/HTTPS/file://) |
| output_format | enum | ✅ | Выходной формат: `opus`, `pcm`, `aac` |
| sample_rate | integer | ❌ | Sample rate (default: 48000) |
| bitrate | string | ❌ | Bitrate (default: "96k") |
| channels | integer | ❌ | Количество каналов (default: 2) |
| filters | AudioFilters | ❌ | Аудио-фильтры |
| low_latency | boolean | ❌ | Low-latency mode (default: true) |

### AudioFilters

Параметры аудио-обработки.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| speed | float | ❌ | Скорость воспроизведения (0.5-2.0, default: 1.0) |
| eq_preset | enum | ❌ | Preset эквалайзера: `flat`, `bass_boost`, `voice`, `treble` |
| volume | float | ❌ | Громкость (0.0-2.0, default: 1.0) |
| custom_filter | string | ❌ | Custom FFmpeg filter graph |

### TranscodeResponse (streaming)

HTTP response с chunked transfer encoding.

| Header | Value | Description |
|--------|-------|-------------|
| Content-Type | application/octet-stream | Binary audio data |
| Transfer-Encoding | chunked | Streaming mode |
| X-Transcode-Id | UUID | Unique transcode session ID |
| X-Source-Format | string | Detected input format |

### TranscodeError

Структурированная ошибка.

| Field | Type | Description |
|-------|------|-------------|
| code | string | Код ошибки (INVALID_URL, UNSUPPORTED_FORMAT, FFMPEG_ERROR, etc.) |
| message | string | Человекочитаемое описание |
| details | object | Дополнительные детали (optional) |
| recoverable | boolean | Можно ли повторить запрос |

### ServiceHealth

Статус сервиса.

| Field | Type | Description |
|-------|------|-------------|
| status | enum | `healthy`, `degraded`, `unhealthy` |
| version | string | Версия сервиса (semver) |
| uptime_seconds | integer | Время работы в секундах |
| active_streams | integer | Количество активных транскодирований |
| ffmpeg_version | string | Версия FFmpeg |

## Enums

### OutputFormat

```
opus    - Opus codec, 48kHz, 96-128kbps (default)
pcm     - Raw PCM, 48kHz, 16-bit signed little-endian
aac     - AAC codec, 48kHz, 128kbps
```

### EqPreset

```
flat        - Без изменений
bass_boost  - Усиление низких частот (+6dB @ 100Hz)
voice       - Оптимизация для голоса (highpass 200Hz, lowpass 3000Hz)
treble      - Усиление высоких частот (+4dB @ 8000Hz)
```

### ErrorCode

```
INVALID_URL          - Некорректный URL источника
UNSUPPORTED_FORMAT   - Неподдерживаемый формат входного файла
FFMPEG_ERROR         - Ошибка FFmpeg процесса
DOWNLOAD_FAILED      - Не удалось скачать источник
TIMEOUT              - Превышен таймаут операции
INTERNAL_ERROR       - Внутренняя ошибка сервиса
RATE_LIMITED         - Превышен лимит запросов
FILTER_INVALID       - Некорректные параметры фильтра
```

## Relationships

```
┌─────────────────┐
│ TranscodeRequest│
│                 │
│ source_url      │
│ output_format   │──────────┐
│ filters ────────┼───────┐  │
└─────────────────┘       │  │
                          ▼  │
                  ┌───────────────┐
                  │ AudioFilters  │
                  │               │
                  │ speed         │
                  │ eq_preset ────┼───────┐
                  │ volume        │       │
                  └───────────────┘       │
                                          ▼
                                  ┌───────────────┐
                                  │   EqPreset    │
                                  │   (enum)      │
                                  └───────────────┘
```

## Validation Rules

### TranscodeRequest

| Field | Validation |
|-------|------------|
| source_url | Must be valid URL (http/https/file scheme) |
| output_format | Must be one of: opus, pcm, aac |
| sample_rate | Must be 8000, 16000, 22050, 44100, or 48000 |
| bitrate | Must match pattern: `\d+k` (e.g., "96k", "128k") |
| channels | Must be 1 or 2 |

### AudioFilters

| Field | Validation |
|-------|------------|
| speed | Must be 0.5 ≤ speed ≤ 2.0 |
| volume | Must be 0.0 ≤ volume ≤ 2.0 |
| eq_preset | Must be valid enum value |
| custom_filter | Must not contain shell injection characters |

## State Transitions (TranscodeStream internal)

```
[PENDING] → [DOWNLOADING] → [TRANSCODING] → [STREAMING] → [COMPLETED]
                ↓                ↓               ↓
            [ERROR]          [ERROR]         [ERROR]
```

| State | Description |
|-------|-------------|
| PENDING | Запрос получен, ожидает обработки |
| DOWNLOADING | Скачивание источника (для HTTP URLs) |
| TRANSCODING | FFmpeg процесс запущен |
| STREAMING | Активная передача данных клиенту |
| COMPLETED | Успешно завершено |
| ERROR | Ошибка на любом этапе |
