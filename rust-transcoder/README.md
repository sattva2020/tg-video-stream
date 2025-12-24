# Rust FFmpeg Transcoder Microservice

Высокопроизводительный микросервис для аудио транскодирования на базе Rust + FFmpeg.

## 🚀 Быстрый старт

### Docker Compose (рекомендуется)

```bash
docker compose up rust-transcoder
```

### Локальная разработка

```bash
cd rust-transcoder
cargo build --release
cargo run --release
```

Сервис будет доступен на `http://localhost:8090`

## 📋 API Endpoints

### Health Check

```bash
curl http://localhost:8090/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "rust-transcoder",
  "version": "0.1.0",
  "uptime_seconds": 120,
  "ffmpeg_version": "ffmpeg version 6.0",
  "active_streams": 2,
  "max_concurrent_streams": 50
}
```

### Базовое транскодирование

```bash
curl -X POST http://localhost:8090/transcode \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://example.com/audio.mp3",
    "output_format": "opus"
  }' \
  --output output.opus
```

### С аудио-фильтрами

```bash
curl -X POST http://localhost:8090/transcode \
  -H "Content-Type: application/json" \
  -d '{
    "source_url": "https://example.com/audio.mp3",
    "output_format": "opus",
    "filters": {
      "speed": 1.5,
      "eq_preset": "bass_boost",
      "volume": 1.2
    }
  }' \
  --output output.opus
```

### Prometheus Metrics

```bash
curl http://localhost:8090/metrics
```

**Метрики:**
- `transcode_requests_total` - общее количество запросов
- `active_streams` - текущее количество активных потоков
- `transcode_latency_milliseconds` - гистограмма latency транскодирования
- `transcode_errors_total` - количество ошибок

## 🐍 Интеграция с Python

### Базовый пример

```python
import httpx

async def transcode_audio(source_url: str, speed: float = 1.0) -> bytes:
    """Транскодирование аудио через Rust-сервис."""
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
```

### Streaming (без буферизации)

```python
async def transcode_stream(source_url: str):
    """Streaming транскодирование для больших файлов."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://rust-transcoder:8090/transcode",
            json={"source_url": source_url, "output_format": "opus"}
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk
```

### Fallback механизм

```python
async def transcode_with_fallback(source_url: str) -> bytes:
    """Транскодирование с fallback на subprocess ffmpeg."""
    try:
        # Попытка через Rust-сервис
        return await transcode_audio(source_url)
    except httpx.RequestError:
        # Fallback на subprocess
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-i", source_url, "-f", "opus", "-"],
            capture_output=True,
            check=True
        )
        return result.stdout
```

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|-----------|---------------------|----------|
| `PORT` | `8090` | Порт HTTP сервера |
| `MAX_CONCURRENT_STREAMS` | `50` | Максимум одновременных потоков |
| `RUST_LOG` | `info` | Уровень логирования |

### Пример docker-compose.yml

```yaml
rust-transcoder:
  build: ./rust-transcoder
  ports:
    - "8090:8090"
  environment:
    - RUST_LOG=info
    - MAX_CONCURRENT_STREAMS=50
  healthcheck:
    test: ["CMD", "wget", "-q", "--spider", "http://localhost:8090/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  restart: unless-stopped
```

## 🎯 Поддерживаемые форматы

### Output Formats

- `opus` - Opus codec (рекомендуется для стриминга)
- `pcm` - Raw PCM (для low-latency)
- `aac` - AAC codec (совместимость)

### Audio Filters

- **Speed**: `0.5` - `2.0` (скорость воспроизведения)
- **EQ Presets**: `flat`, `bass_boost`, `voice`, `treble`
- **Volume**: `0.0` - `2.0` (громкость)

## 📊 Performance

- **Latency**: < 200ms старт транскодирования
- **Memory**: < 256MB для 10 concurrent streams
- **Throughput**: 50+ concurrent streams на 4 vCPU

## 🔧 Разработка

### Запуск тестов

```bash
cargo test
cargo test --test contract_health_test
cargo test --test contract_metrics_test
```

### Форматирование и линтинг

```bash
cargo fmt
cargo clippy -- -D warnings
```

### Сборка release

```bash
cargo build --release
./target/release/rust-transcoder
```

## 📚 Документация

- [Quickstart Guide](../specs/020-ffmpeg-wrapper-rust-python-api/quickstart.md)
- [API Specification](../specs/020-ffmpeg-wrapper-rust-python-api/spec.md)
- [Implementation Plan](../specs/020-ffmpeg-wrapper-rust-python-api/plan.md)
- [Tasks](../specs/020-ffmpeg-wrapper-rust-python-api/tasks.md)

## � Security

### SSRF Protection

✅ **Implemented** - защита от Server-Side Request Forgery атак.

**Блокируются:**
- `file://` URLs
- Приватные IP: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- Localhost: 127.0.0.1, ::1, localhost
- Link-local: 169.254.0.0/16

**Разрешены только:**
- HTTP/HTTPS URLs
- Публичные IP адреса

См. [API Documentation](../docs/api/rust-transcoder.md#security-considerations) для деталей.

---

### Сервис не стартует

Проверьте что FFmpeg установлен:
```bash
ffmpeg -version
```

### High memory usage

Уменьшите `MAX_CONCURRENT_STREAMS` в конфигурации.

### Timeouts

Увеличьте timeout в HTTP клиенте для больших файлов.

## 📄 License

MIT
