# Rust Transcoder API Documentation

**Base URL**: `http://rust-transcoder:8090`  
**Version**: v0.1.0  
**Protocol**: HTTP/REST  
**Format**: JSON

---

## 📑 Table of Contents

- [Health Endpoints](#health-endpoints)
- [Transcode API](#transcode-api)
- [Metrics Endpoint](#metrics-endpoint)
- [Error Responses](#error-responses)
- [Data Models](#data-models)

---

## Health Endpoints

### GET /health

Расширенный health check с информацией о сервисе.

**Response 200 OK:**
```json
{
  "status": "healthy",
  "service": "rust-transcoder",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "ffmpeg_version": "ffmpeg version 6.0 Copyright (c) 2000-2023",
  "active_streams": 5,
  "max_concurrent_streams": 50
}
```

**Fields:**
- `status` (string): всегда `"healthy"`
- `service` (string): название сервиса
- `version` (string): semver версия
- `uptime_seconds` (number, optional): время работы в секундах
- `ffmpeg_version` (string, optional): версия FFmpeg
- `active_streams` (number, optional): текущее количество активных потоков
- `max_concurrent_streams` (number, optional): максимум concurrent потоков

---

### GET /health/ready

Readiness probe для Kubernetes/Docker Swarm.

**Response 200 OK:**
```
ready
```

**Use Case**: Проверка готовности к приёму трафика после старта.

---

### GET /health/live

Liveness probe для Kubernetes/Docker Swarm.

**Response 200 OK:**
```
alive
```

**Use Case**: Проверка что процесс жив и не завис.

---

## Transcode API

### POST /transcode

Транскодирование аудио с streaming output.

**Request Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "source_url": "https://example.com/audio.mp3",
  "output_format": "opus",
  "filters": {
    "speed": 1.5,
    "eq_preset": "bass_boost",
    "volume": 1.2
  }
}
```

**Request Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_url` | string | ✅ Yes | URL источника (http/https) |
| `output_format` | string | ✅ Yes | Формат: `opus`, `pcm`, `aac` |
| `filters` | object | ❌ No | Аудио-фильтры |
| `filters.speed` | number | ❌ No | Скорость: 0.5 - 2.0 |
| `filters.eq_preset` | string | ❌ No | EQ: `flat`, `bass_boost`, `voice`, `treble` |
| `filters.volume` | number | ❌ No | Громкость: 0.0 - 2.0 |

**Response 200 OK:**

Streaming binary data (audio).

**Response Headers:**
```
Content-Type: audio/opus (или audio/pcm, audio/aac)
X-Transcode-Id: 550e8400-e29b-41d4-a716-446655440000
X-Source-Format: mp3
Transfer-Encoding: chunked
```

**Headers:**
- `X-Transcode-Id`: UUID задачи транскодирования
- `X-Source-Format`: исходный формат аудио

---

## Metrics Endpoint

### GET /metrics

Prometheus метрики в text/plain формате.

**Response 200 OK:**
```
# HELP transcode_requests_total Total number of transcode requests
# TYPE transcode_requests_total counter
transcode_requests_total 1523

# HELP active_streams Current number of active transcoding streams
# TYPE active_streams gauge
active_streams 7

# HELP transcode_latency_milliseconds Transcode operation latency in milliseconds
# TYPE transcode_latency_milliseconds histogram
transcode_latency_milliseconds_bucket{format="opus",status="success",le="10"} 0
transcode_latency_milliseconds_bucket{format="opus",status="success",le="50"} 12
transcode_latency_milliseconds_bucket{format="opus",status="success",le="100"} 145
transcode_latency_milliseconds_bucket{format="opus",status="success",le="200"} 1200
transcode_latency_milliseconds_bucket{format="opus",status="success",le="+Inf"} 1523

# HELP transcode_errors_total Total number of transcode errors
# TYPE transcode_errors_total counter
transcode_errors_total 15
```

**Метрики:**

| Metric | Type | Description |
|--------|------|-------------|
| `transcode_requests_total` | Counter | Общее количество запросов |
| `active_streams` | Gauge | Текущее количество активных потоков |
| `transcode_latency_milliseconds` | Histogram | Latency транскодирования (по format, status) |
| `transcode_errors_total` | Counter | Количество ошибок |

**Prometheus Config:**
```yaml
scrape_configs:
  - job_name: 'rust-transcoder'
    scrape_interval: 15s
    static_configs:
      - targets: ['rust-transcoder:8090']
```

---

## Error Responses

### 400 Bad Request

Неверный запрос (валидация не прошла).

```json
{
  "error": "VALIDATION_FAILED",
  "message": "Invalid speed value: 3.0 (must be between 0.5 and 2.0)",
  "details": {
    "field": "filters.speed",
    "value": 3.0,
    "constraint": "0.5 <= value <= 2.0"
  }
}
```

**Error Codes:**
- `VALIDATION_FAILED` - неверные параметры запроса
- `INVALID_URL` - некорректный URL источника

---

### 500 Internal Server Error

Ошибка на сервере (FFmpeg crash, file not found).

```json
{
  "error": "TRANSCODE_FAILED",
  "message": "FFmpeg process exited with code 1",
  "details": {
    "ffmpeg_error": "Invalid data found when processing input"
  }
}
```

**Error Codes:**
- `TRANSCODE_FAILED` - ошибка транскодирования
- `FFMPEG_NOT_FOUND` - FFmpeg не установлен
- `DOWNLOAD_FAILED` - не удалось скачать источник

---

### 503 Service Unavailable

Сервис перегружен (достигнут лимит concurrent потоков).

```json
{
  "error": "TOO_MANY_STREAMS",
  "message": "Maximum concurrent streams reached (50/50)",
  "retry_after_seconds": 5
}
```

---

## Data Models

### TranscodeRequest

```typescript
interface TranscodeRequest {
  source_url: string;           // URL источника (http/https)
  output_format: OutputFormat;  // Формат вывода
  filters?: AudioFilters;       // Опциональные фильтры
}
```

### OutputFormat

```typescript
type OutputFormat = "opus" | "pcm" | "aac";
```

### AudioFilters

```typescript
interface AudioFilters {
  speed?: number;        // 0.5 - 2.0
  eq_preset?: EqPreset;  // EQ пресет
  volume?: number;       // 0.0 - 2.0
}
```

### EqPreset

```typescript
type EqPreset = "flat" | "bass_boost" | "voice" | "treble";
```

---

## Rate Limiting

- **Max Concurrent Streams**: 50 (по умолчанию, настраивается через `MAX_CONCURRENT_STREAMS`)
- **Behaviour**: При превышении лимита возвращается 503 Service Unavailable
- **Retry Strategy**: Exponential backoff с `retry_after_seconds` из response

---

## Security Considerations

### SSRF Protection

⚠️ **TODO**: В текущей версии отсутствует защита от SSRF.

**Планируется:**
- Блокировка `file://` URLs
- Блокировка internal IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Whitelist разрешённых доменов (опционально)

### Authentication

В текущей версии отсутствует аутентификация. Рекомендуется:
- Использовать сетевую изоляцию (internal network)
- Добавить reverse proxy с аутентификацией (nginx + basic auth)
- Использовать API gateway (Kong, Traefik)

---

## Examples

### cURL

```bash
# Базовое транскодирование
curl -X POST http://localhost:8090/transcode \
  -H "Content-Type: application/json" \
  -d '{"source_url": "https://example.com/audio.mp3", "output_format": "opus"}' \
  --output output.opus

# С фильтрами
curl -X POST http://localhost:8090/transcode \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://example.com/audio.mp3",
    "output_format": "opus",
    "filters": {
      "speed": 1.25,
      "eq_preset": "bass_boost",
      "volume": 1.5
    }
  }' \
  --output output.opus
```

### Python (httpx)

```python
import httpx

async def transcode(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://rust-transcoder:8090/transcode",
            json={
                "source_url": url,
                "output_format": "opus",
                "filters": {"speed": 1.5}
            }
        )
        response.raise_for_status()
        return response.content
```

### JavaScript (fetch)

```javascript
async function transcode(url) {
  const response = await fetch('http://rust-transcoder:8090/transcode', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      source_url: url,
      output_format: 'opus',
      filters: {speed: 1.5}
    })
  });
  
  if (!response.ok) throw new Error(`Transcode failed: ${response.statusText}`);
  return await response.arrayBuffer();
}
```

---

## OpenAPI Specification

Полная OpenAPI спецификация доступна в:
[contracts/openapi.yaml](../../specs/020-ffmpeg-wrapper-rust-python-api/contracts/openapi.yaml)

---

**Последнее обновление**: 24 декабря 2025
