# Research: Rust FFmpeg Microservice

**Feature**: 020-ffmpeg-wrapper-rust-python-api  
**Date**: 7 декабря 2025  
**Phase**: 0 - Outline & Research

## Research Questions

### 1. Rust FFmpeg Integration Options

**Question**: Какой подход для интеграции FFmpeg в Rust наиболее подходит?

**Research Findings**:

| Подход | Плюсы | Минусы | Рекомендация |
|--------|-------|--------|--------------|
| **ffmpeg-next** (Rust bindings) | Нативная интеграция, максимальная производительность, типобезопасность | Сложная компиляция, зависимость от системных libav* | Для Phase 2+ |
| **subprocess ffmpeg** | Простота, тот же ffmpeg что и сейчас, легче отлаживать | Overhead на spawn процесса, сложнее streaming | **MVP выбор** |
| **gstreamer-rs** | Гибкий pipeline, хорошие Rust bindings | Другая экосистема, не FFmpeg-совместимо | Не рекомендуется |

**Decision**: Начать с **subprocess ffmpeg** в Rust для MVP. Это:
- Минимизирует риск интеграции
- Позволяет переиспользовать существующие ffmpeg args
- Легко тестируется
- Можно мигрировать на ffmpeg-next позже

**Rationale**: Сложность ffmpeg-next bindings (компиляция, linking, версии libav*) несоразмерна выгоде для MVP. Subprocess достаточно для достижения SC-001 (<200ms latency) благодаря async spawn и pipe streaming.

---

### 2. Rust HTTP Framework Selection

**Question**: Какой HTTP фреймворк использовать для Rust-сервиса?

**Research Findings**:

| Фреймворк | Плюсы | Минусы |
|-----------|-------|--------|
| **Axum** | Tokio-native, type-safe extractors, tower middleware | Относительно новый |
| **Actix-web** | Зрелый, высокая производительность, большое сообщество | Actor model может быть избыточен |
| **Warp** | Composable filters, хороший для простых API | Менее интуитивный API |

**Decision**: **Axum** — современный, хорошо интегрируется с tokio, отличные типы для request/response.

**Alternatives considered**: Actix-web — хороший выбор, но actor model не нужен для stateless transcoding.

---

### 3. Streaming Output Strategy

**Question**: Как реализовать streaming output без буферизации всего файла?

**Research Findings**:

Варианты для HTTP streaming:
1. **Chunked Transfer-Encoding** — стандартный HTTP/1.1, широко поддерживается
2. **Server-Sent Events** — для event streams, не подходит для binary
3. **WebSocket** — bidirectional, избыточно для unidirectional audio
4. **gRPC streaming** — эффективно, но добавляет сложность

**Decision**: **Chunked Transfer-Encoding** с `Content-Type: application/octet-stream`

Реализация в Axum:
```rust
// Псевдокод концепции
async fn transcode(req: TranscodeRequest) -> impl IntoResponse {
    let child = Command::new("ffmpeg")
        .args(&build_args(&req))
        .stdout(Stdio::piped())
        .spawn()?;
    
    let stream = ReaderStream::new(child.stdout.unwrap());
    Body::from_stream(stream)
}
```

**Rationale**: HTTP chunked streaming — простейший подход, Python httpx поддерживает streaming responses нативно.

---

### 4. Python Client Integration

**Question**: Как Python-оркестратор будет взаимодействовать с Rust-сервисом?

**Research Findings**:

```python
# httpx streaming client (концепция)
async def transcode_via_rust(source_url: str, filters: dict) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{RUST_SERVICE_URL}/transcode",
            json={"source_url": source_url, "filters": filters}
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk
```

**Decision**: Использовать **httpx** с async streaming для минимальной latency.

**Fallback strategy**:
```python
async def transcode(source_url: str, filters: dict):
    try:
        async for chunk in transcode_via_rust(source_url, filters):
            yield chunk
    except (httpx.ConnectError, httpx.TimeoutException):
        logger.warning("Rust service unavailable, falling back to subprocess")
        async for chunk in transcode_via_subprocess(source_url, filters):
            yield chunk
```

---

### 5. Audio Filter Implementation

**Question**: Как реализовать EQ и speed control в Rust?

**Research Findings**:

FFmpeg filter graph для аудио:
```bash
# Speed control (atempo)
ffmpeg -i input.mp3 -filter:a "atempo=1.5" -f opus output.opus

# EQ (equalizer filter)
ffmpeg -i input.mp3 -af "equalizer=f=1000:t=h:w=200:g=-10" output.opus

# Combined
ffmpeg -i input.mp3 -af "atempo=1.25,equalizer=f=100:t=h:w=100:g=3" output.opus
```

**Decision**: Передавать filter graph как параметр в запросе. Rust-сервис строит ffmpeg command.

**EQ Presets** (перенос из Python):
```rust
enum EqPreset {
    Flat,       // Без изменений
    BassBoost,  // equalizer=f=100:t=h:w=100:g=6
    Voice,      // highpass=f=200,lowpass=f=3000
    Treble,     // equalizer=f=8000:t=h:w=1000:g=4
}
```

---

### 6. Health Check & Metrics

**Question**: Какой формат метрик и health check использовать?

**Research Findings**:

**Health Check** (стандартный формат):
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "active_streams": 5
}
```

**Prometheus Metrics** (используя `prometheus` crate):
```
# HELP transcode_requests_total Total transcoding requests
# TYPE transcode_requests_total counter
transcode_requests_total{status="success"} 1234
transcode_requests_total{status="error"} 12

# HELP transcode_latency_seconds Transcoding start latency
# TYPE transcode_latency_seconds histogram
transcode_latency_seconds_bucket{le="0.1"} 800
transcode_latency_seconds_bucket{le="0.2"} 1100
transcode_latency_seconds_bucket{le="0.5"} 1200

# HELP active_streams Current active transcoding streams
# TYPE active_streams gauge
active_streams 5
```

**Decision**: Использовать `prometheus` crate для метрик, JSON для health check.

---

### 7. Docker Integration

**Question**: Как интегрировать Rust-сервис в существующий docker-compose?

**Research Findings**:

```yaml
# docker-compose.yml addition
rust-transcoder:
  build:
    context: ./rust-transcoder
    dockerfile: Dockerfile
  ports:
    - "8090:8090"  # Internal only, не exposed externally
  environment:
    - RUST_LOG=info
    - FFMPEG_PATH=/usr/bin/ffmpeg
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  depends_on:
    - redis
  networks:
    - internal
```

**Dockerfile** (multi-stage build):
```dockerfile
FROM rust:1.75-slim AS builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/rust-transcoder /usr/local/bin/
EXPOSE 8090
CMD ["rust-transcoder"]
```

**Decision**: Multi-stage Docker build, ffmpeg installed в runtime image.

---

## Resolved Clarifications

| Item | Resolution |
|------|------------|
| FFmpeg integration approach | subprocess для MVP, ffmpeg-next для future |
| HTTP framework | Axum |
| Streaming protocol | HTTP chunked transfer |
| Python client | httpx async streaming |
| Metrics format | Prometheus text format |
| Docker strategy | Multi-stage build, debian-slim base |

## Open Questions (для Phase 2)

1. Нужен ли connection pool для ffmpeg subprocesses?
2. Как ограничить concurrent transcodes (semaphore)?
3. Нужен ли rate limiting на Rust API?
