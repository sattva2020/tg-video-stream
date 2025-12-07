# Quickstart: Rust FFmpeg Microservice

**Feature**: 020-ffmpeg-wrapper-rust-python-api  
**Date**: 7 декабря 2025

## Обзор

Rust-микросервис для аудио транскодирования с HTTP API. Принимает URL аудиофайла, возвращает транскодированный поток в нужном формате.

## Быстрый старт

### 1. Запуск сервиса

```bash
# Через Docker Compose (рекомендуется)
docker compose up rust-transcoder

# Или локально (для разработки)
cd rust-transcoder
cargo run --release
```

### 2. Проверка здоровья

```bash
curl http://localhost:8090/health
```

Ответ:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "uptime_seconds": 120,
  "active_streams": 0,
  "ffmpeg_version": "6.0"
}
```

### 3. Транскодирование

```bash
# Базовый запрос
curl -X POST http://localhost:8090/transcode \
  -H "Content-Type: application/json" \
  -d '{"source_url": "https://example.com/audio.mp3", "output_format": "opus"}' \
  --output output.opus

# С фильтрами (скорость 1.5x, bass boost)
curl -X POST http://localhost:8090/transcode \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://example.com/audio.mp3",
    "output_format": "opus",
    "filters": {
      "speed": 1.5,
      "eq_preset": "bass_boost"
    }
  }' \
  --output output.opus
```

### 4. Метрики (Prometheus)

```bash
curl http://localhost:8090/metrics
```

## Интеграция с Python

```python
import httpx

async def transcode_audio(source_url: str, speed: float = 1.0) -> bytes:
    """Пример использования из Python."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://rust-transcoder:8090/transcode",
            json={
                "source_url": source_url,
                "output_format": "opus",
                "filters": {"speed": speed}
            }
        )
        response.raise_for_status()
        return response.content

# Streaming версия
async def transcode_stream(source_url: str):
    """Streaming без буферизации всего файла."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://rust-transcoder:8090/transcode",
            json={"source_url": source_url, "output_format": "opus"}
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk
```

## Конфигурация

### Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `PORT` | 8090 | HTTP порт сервиса |
| `RUST_LOG` | info | Уровень логирования |
| `FFMPEG_PATH` | /usr/bin/ffmpeg | Путь к ffmpeg |
| `MAX_CONCURRENT_STREAMS` | 50 | Максимум одновременных транскодирований |
| `REQUEST_TIMEOUT_SECS` | 300 | Таймаут запроса (секунды) |

### Docker Compose

```yaml
rust-transcoder:
  build: ./rust-transcoder
  ports:
    - "8090:8090"
  environment:
    - RUST_LOG=info
    - MAX_CONCURRENT_STREAMS=50
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
    interval: 30s
    timeout: 10s
    retries: 3
```

## API Reference

См. [OpenAPI спецификация](./contracts/openapi.yaml)

### Endpoints

| Method | Path | Описание |
|--------|------|----------|
| POST | /transcode | Транскодирование аудио |
| GET | /health | Health check |
| GET | /metrics | Prometheus метрики |

### Форматы вывода

| Формат | Content-Type | Описание |
|--------|--------------|----------|
| opus | audio/opus | Opus 48kHz (рекомендуется) |
| pcm | audio/pcm | Raw PCM 48kHz 16-bit |
| aac | audio/aac | AAC 48kHz |

### EQ Presets

| Preset | Описание |
|--------|----------|
| flat | Без изменений |
| bass_boost | +6dB @ 100Hz |
| voice | Highpass 200Hz, Lowpass 3000Hz |
| treble | +4dB @ 8000Hz |

## Fallback (Python)

Если Rust-сервис недоступен, Python-оркестратор автоматически переключается на subprocess ffmpeg:

```python
async def transcode_with_fallback(source_url: str, filters: dict):
    try:
        async for chunk in transcode_via_rust(source_url, filters):
            yield chunk
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"Rust service unavailable: {e}, using fallback")
        async for chunk in transcode_via_subprocess(source_url, filters):
            yield chunk
```

## Troubleshooting

### Сервис не запускается

```bash
# Проверить логи
docker compose logs rust-transcoder

# Проверить что ffmpeg доступен
docker compose exec rust-transcoder ffmpeg -version
```

### Ошибка FFMPEG_ERROR

```bash
# Проверить входной URL
curl -I "https://example.com/audio.mp3"

# Проверить поддерживаемые форматы
docker compose exec rust-transcoder ffmpeg -formats | grep mp3
```

### Высокий latency

1. Проверить метрики: `/metrics`
2. Уменьшить `MAX_CONCURRENT_STREAMS` если CPU перегружен
3. Использовать `low_latency: true` в запросе
