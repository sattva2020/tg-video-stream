# Python SDK Integration Guide

> **Spec**: 026-api-webhook-ecosystem
> **Версия**: 1.0
> **Дата**: 2026-01-23

## Обзор / Overview

Official Python SDK for the Sattva Streaming Platform API.
Официальный Python SDK для API Sattva Streaming Platform.

The SDK provides a Pythonic interface to all Sattva API endpoints, including stream management, playlist control, webhooks, and API key management.
SDK предоставляет Python-интерфейс ко всем endpoint'ам Sattva API, включая управление стримами, плейлистами, вебхуками и API ключами.

## Установка / Installation

### Using pip (Рекомендуется / Recommended)

```bash
pip install sattva-api
```

### From source (Из исходников)

```bash
git clone https://github.com/sattva/sattva-python-sdk.git
cd sattva-python-sdk
pip install -e .
```

### Development Installation (Для разработки)

```bash
pip install -e ".[dev]"
```

This installs additional development dependencies: pytest, black, ruff, mypy.
Это устанавливает дополнительные зависимости для разработки: pytest, black, ruff, mypy.

## Quick Start / Быстрый старт

### Basic Initialization (Базовая инициализация)

```python
from sattva_api import SattvaClient

# Initialize client with API key
# Инициализация клиента с API ключом
client = SattvaClient(
    api_key="your-api-key-here",
    base_url="https://api.sattva.io/api/v1"
)

# List all streams
# Получить список всех стримов
streams = client.streams.list()
for stream in streams:
    print(f"Stream: {stream['name']} - {stream['status']}")
```

### Using Environment Variables (Использование переменных окружения)

```python
import os
from sattva_api import SattvaClient

# Recommended for production
# Рекомендуется для production
client = SattvaClient(
    api_key=os.getenv("SATTVA_API_KEY"),
    base_url=os.getenv("SATTVA_API_URL", "https://api.sattva.io/api/v1")
)
```

## Authentication / Аутентификация

### API Key Setup (Настройка API ключа)

```python
from sattva_api import SattvaClient

# Create API key in dashboard or via API
# Создайте API ключ в дашборде или через API
client = SattvaClient(
    api_key="sk_live_xxxxxxxxxxxx"  # Your API key / Ваш API ключ
)
```

### API Key Security (Безопасность API ключей)

⚠️ **Security Best Practices / Рекомендации по безопасности:**

- Never commit API keys to version control / Никогда не коммитьте API ключи в репозиторий
- Use environment variables in production / Используйте переменные окружения в production
- Rotate API keys regularly / Регулярно обновляйте API ключи
- Use separate keys for dev/prod / Используйте разные ключи для разработки и продакшна

```python
# .env file (НЕ коммитьте в git!)
SATTVA_API_KEY=sk_live_xxxxxxxxxxxx
SATTVA_API_URL=https://api.sattva.io/api/v1

# Python code / Python код
from dotenv import load_dotenv
from sattva_api import SattvaClient

load_dotenv()
client = SattvaClient(api_key=os.getenv("SATTVA_API_KEY"))
```

## Resources / Ресурсы

### Streams (Стримы)

```python
from sattva_api import SattvaClient

client = SattvaClient(api_key="your-api-key")

# List all streams / Список всех стримов
streams = client.streams.list()

# Get specific stream / Получить конкретный стрим
stream = client.streams.get(stream_id="stream-123")

# Start a stream / Запустить стрим
response = client.streams.start(channel_id="channel-123")
print(f"Stream started: {response['stream_id']}")

# Stop a stream / Остановить стрим
client.streams.stop(stream_id="stream-123")

# Pause a stream / Поставить стрим на паузу
client.streams.pause(stream_id="stream-123")

# Resume a stream / Продолжить стрим
client.streams.resume(stream_id="stream-123")

# Restart a stream / Перезапустить стрим
response = client.streams.restart(channel_id="channel-123")
```

### Playlists (Плейлисты)

```python
# List playlists / Список плейлистов
playlists = client.playlists.list()

# Get playlist / Получить плейлист
playlist = client.playlists.get(playlist_id="playlist-123")

# Create playlist / Создать плейлист
playlist = client.playlists.create(
    name="My Playlist",
    description="Favorite tracks"
)

# Update playlist / Обновить плейлист
playlist = client.playlists.update(
    playlist_id="playlist-123",
    name="Updated Name",
    track_ids=["track-1", "track-2", "track-3"]
)

# Reorder tracks / Переупорядочить треки
client.playlists.reorder(
    playlist_id="playlist-123",
    track_ids=["track-3", "track-1", "track-2"]
)

# Get playlist status / Получить статус плейлиста
status = client.playlists.status(playlist_id="playlist-123")
print(f"Current track: {status['current_track']}")

# Delete playlist / Удалить плейлист
client.playlists.delete(playlist_id="playlist-123")
```

### Channels (Каналы)

```python
# List channels / Список каналов
channels = client.channels.list()

# Get channel / Получить канал
channel = client.channels.get(channel_id="channel-123")

# Create channel / Создать канал
channel = client.channels.create(
    name="My Channel",
    description="Channel description",
    url="https://example.com/stream"
)

# Update channel / Обновить канал
channel = client.channels.update(
    channel_id="channel-123",
    name="Updated Channel"
)

# Delete channel / Удалить канал
client.channels.delete(channel_id="channel-123")
```

### Webhooks (Вебхуки)

```python
# List webhooks / Список вебхуков
webhooks = client.webhooks.list()

# Get webhook / Получить вебхук
webhook = client.webhooks.get(webhook_id="webhook-123")

# Create webhook / Создать вебхук
webhook = client.webhooks.create(
    url="https://your-app.com/webhooks",
    event_types=["stream.started", "stream.stopped", "stream.error"]
)
# IMPORTANT: Save the secret immediately!
# ВАЖНО: Сразу сохраните секрет!
webhook_secret = webhook["secret"]

# Test webhook / Протестировать вебхук
result = client.webhooks.test(webhook_id=webhook["id"])
print(f"Test success: {result['success']}")

# Rotate webhook secret / Обновить секрет вебхука
webhook = client.webhooks.rotate_secret(webhook_id=webhook["id"])
new_secret = webhook["secret"]  # Save new secret / Сохраните новый секрет

# List webhook events / Список событий вебхука
events = client.webhooks.list_events(webhook_id=webhook["id"])
for event in events:
    print(f"Event {event['event_type']}: {event['status']}")

# Delete webhook / Удалить вебхук
client.webhooks.delete(webhook_id=webhook["id"])
```

### API Keys (API ключи)

```python
# List API keys / Список API ключей
keys = client.api_keys.list()
for key in keys:
    print(f"{key['name']}: {key['scopes']}")

# Create API key / Создать API ключ
key = client.api_keys.create(
    name="Read-only Integration",
    scopes=["read:streams", "read:playlists"]
)
# IMPORTANT: Save the key value immediately!
# ВАЖНО: Сразу сохраните значение ключа!
api_key_value = key["key"]

# Revoke API key / Отозвать API ключ
client.api_keys.revoke(key_id="key-123")
```

## Error Handling / Обработка ошибок

### Exception Types (Типы исключений)

```python
from sattva_api import SattvaClient
from sattva_api.exceptions import (
    SattvaAPIError,
    AuthenticationError,
    RateLimitError,
    NotFoundError,
    ValidationError
)

client = SattvaClient(api_key="your-api-key")

try:
    stream = client.streams.get(stream_id="stream-123")
except AuthenticationError:
    print("Invalid API key / Неверный API ключ")
except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after: {e.retry_after} seconds")
    print(f"Превышен лимит запросов. Повторите через: {e.retry_after} секунд")
except NotFoundError:
    print("Stream not found / Стрим не найден")
except ValidationError as e:
    print(f"Validation error: {e.errors}")
    print(f"Ошибка валидации: {e.errors}")
except SattvaAPIError as e:
    print(f"API error: {e}")
    print(f"Ошибка API: {e}")
```

### Retry Strategy (Стратегия повтора)

```python
# Configure automatic retries / Настройка автоматических повторов
client = SattvaClient(
    api_key="your-api-key",
    max_retries=5,        # Number of retries / Количество попыток
    retry_delay=2.0       # Delay between retries (seconds) / Задержка между попытками (секунды)
)

# When rate limit is hit, SDK automatically retries with exponential backoff
# При превышении лимита SDK автоматически повторяет с экспоненциальной задержкой
```

## Webhook Signature Verification (Проверка подписи вебхука)

### Verify Webhooks (Проверка вебхуков)

```python
from sattva_api import verify_webhook_signature
import json

def webhook_handler(request):
    """
    Django example / Пример для Django
    """
    payload = request.body
    signature = request.headers.get('X-Sattva-Signature')
    secret = 'your-webhook-secret'

    # Verify signature / Проверить подпись
    if verify_webhook_signature(payload, signature, secret):
        event = json.loads(payload)
        print(f"Received event: {event['event_type']}")
        print(f"Получено событие: {event['event_type']}")

        # Process event based on type / Обработать событие по типу
        if event['event_type'] == 'stream.started':
            handle_stream_started(event['data'])
        elif event['event_type'] == 'stream.stopped':
            handle_stream_stopped(event['data'])

        return {'status': 'ok'}
    else:
        print("Invalid signature / Неверная подпись")
        return {'status': 'invalid'}, 401
```

### Flask Example (Пример для Flask)

```python
from flask import Flask, request, jsonify
from sattva_api import verify_webhook_signature
import json

app = Flask(__name__)

@app.route('/webhooks', methods=['POST'])
def handle_webhook():
    payload = request.get_data()
    signature = request.headers.get('X-Sattva-Signature')
    secret = 'your-webhook-secret'

    if verify_webhook_signature(payload, signature, secret):
        event = request.get_json()
        # Process event / Обработать событие
        return jsonify({'status': 'ok'}), 200
    else:
        return jsonify({'error': 'Invalid signature'}), 401
```

## Advanced Usage (Расширенное использование)

### Context Manager (Контекстный менеджер)

```python
# Use context manager for automatic cleanup
# Использовать контекстный менеджер для автоматической очистки
with SattvaClient(api_key="your-api-key") as client:
    streams = client.streams.list()
    # Resources automatically cleaned up on exit
    # Ресурсы автоматически освобождаются при выходе
```

### Custom Configuration (Кастомная конфигурация)

```python
# Configure timeouts and retries / Настроить таймауты и повторы
client = SattvaClient(
    api_key="your-api-key",
    base_url="https://api.sattva.io/api/v1",
    timeout=30,           # Request timeout (seconds) / Таймаут запроса (секунды)
    max_retries=5,        # Max retries on rate limit / Максимум попыток при лимите
    retry_delay=2.0       # Initial retry delay (seconds) / Начальная задержка (секунды)
)
```

### Async Support (Поддержка асинхронности)

```python
import asyncio
from sattva_api import SattvaClient

async def main():
    client = SattvaClient(api_key="your-api-key")

    # Make multiple requests concurrently
    # Выполнять несколько запросов concurrently
    tasks = [
        client.streams.get("stream-1"),
        client.streams.get("stream-2"),
        client.streams.get("stream-3")
    ]
    results = await asyncio.gather(*tasks)
    return results

# Note: SDK uses requests library (synchronous)
# For true async, consider using aiohttp with custom implementation
# Примечание: SDK использует библиотеку requests (синхронно)
# Для настоящей асинхронности рассмотрите aiohttp с кастомной реализацией
```

## Testing (Тестирование)

### Unit Tests (Юнит-тесты)

```python
import unittest
from unittest.mock import Mock, patch
from sattva_api import SattvaClient

class TestSattvaClient(unittest.TestCase):
    def setUp(self):
        self.client = SattvaClient(api_key="test-key")

    @patch('sattva_api.client.requests.get')
    def test_list_streams(self, mock_get):
        mock_get.return_value.json.return_value = {
            "streams": [{"id": "1", "name": "Test Stream"}]
        }

        streams = self.client.streams.list()

        self.assertEqual(len(streams), 1)
        self.assertEqual(streams[0]["name"], "Test Stream")

if __name__ == '__main__':
    unittest.main()
```

### Integration Tests (Интеграционные тесты)

```python
import pytest
from sattva_api import SattvaClient

@pytest.fixture
def client():
    return SattvaClient(api_key="test-api-key")

def test_stream_lifecycle(client):
    # Create / Start / Stop workflow
    # Рабочий процесс создания / запуска / остановки
    streams = client.streams.list()
    assert isinstance(streams, list)
```

## Development (Разработка)

### Running SDK Tests (Запуск тестов SDK)

```bash
cd sdks/python
pytest tests/ -v --cov=sattva_api
```

### Code Formatting (Форматирование кода)

```bash
# Format code / Форматировать код
black sattva_api tests

# Lint code / Проверить код
ruff check sattva_api tests

# Type checking / Проверка типов
mypy sattva_api
```

### Building for Distribution (Сборка для дистрибуции)

```bash
python -m build
twine upload dist/*
```

## Event Types (Типы событий)

Webhook events available for subscription / Вебхук-события, доступные для подписки:

| Event Type | Description / Описание |
|------------|----------------------|
| `stream.started` | Stream has started / Стрим запущен |
| `stream.stopped` | Stream has stopped / Стрим остановлен |
| `stream.paused` | Stream has been paused / Стрим на паузе |
| `stream.resumed` | Stream has been resumed / Стрим возобновлен |
| `stream.error` | Stream encountered an error / Ошибка стрима |
| `viewer.milestone` | Viewer milestone reached / Достигнут milestone зрителей |
| `viewer.joined` | Viewer joined the stream / Зритель присоединился |
| `viewer.left` | Viewer left the stream / Зритель покинул стрим |
| `track.started` | Track started playing / Трек начал воспроизводиться |
| `track.completed` | Track finished playing / Трек закончил воспроизводиться |
| `track.failed` | Track failed to play / Трек не воспроизвелся |
| `track.skipped` | Track was skipped / Трек пропущен |

## Common Use Cases (Частые случаи использования)

### Automating Stream Management (Автоматизация управления стримами)

```python
from sattva_api import SattvaClient

client = SattvaClient(api_key="your-api-key")

def auto_restart_failed_streams():
    """Automatically restart failed streams"""
    """Автоматически перезапускать упавшие стримы"""
    streams = client.streams.list()

    for stream in streams:
        if stream['status'] == 'error':
            print(f"Restarting failed stream: {stream['id']}")
            client.streams.restart(stream['channel_id'])
```

### Syncing Playlists (Синхронизация плейлистов)

```python
def sync_playlist_from_csv(csv_file, playlist_id):
    """Sync playlist tracks from CSV file"""
    """Синхронизировать треки плейлиста из CSV файла"""
    import csv

    with open(csv_file) as f:
        reader = csv.DictReader(f)
        track_ids = [row['track_id'] for row in reader]

    client.playlists.update(
        playlist_id=playlist_id,
        track_ids=track_ids
    )
```

### Monitoring Webhooks (Мониторинг вебхуков)

```python
def check_webhook_health(webhook_id):
    """Check webhook delivery health"""
    """Проверить здоровье доставки вебхуков"""
    events = client.webhooks.list_events(webhook_id=webhook_id)

    failed = [e for e in events if e['status'] == 'failed']
    if len(failed) > 10:
        print(f"Warning: {len(failed)} failed webhook deliveries")
        print(f"Предупреждение: {len(failed)} неудачных доставок вебхуков")
```

## Troubleshooting (Решение проблем)

### Common Issues (Частые проблемы)

| Problem / Проблема | Solution / Решение |
|-------------------|-------------------|
| `AuthenticationError` | Check API key is valid / Проверьте валидность API ключа |
| `RateLimitError` | Implement exponential backoff / Используйте экспоненциальную задержку |
| `NotFoundError` | Verify resource ID exists / Проверьте существование ID ресурса |
| Connection timeout | Increase timeout value / Увеличьте значение таймаута |

### Debug Mode (Режим отладки)

```python
import logging

# Enable debug logging / Включить debug-логирование
logging.basicConfig(level=logging.DEBUG)

client = SattvaClient(api_key="your-api-key")
# All HTTP requests will be logged
# Все HTTP запросы будут логированы
```

## Related Documents (Связанные документы)

- [API Reference](./reference.md)
- [Authentication Guide](./authentication.md)
- [Webhooks Guide](./webhooks.md)
- [API Versioning](./versioning.md)
- [026 Spec](../../specs/026-api-webhook-ecosystem/)

## Support & Resources (Поддержка и ресурсы)

- **Documentation / Документация**: [https://docs.sattva.io](https://docs.sattva.io)
- **GitHub / GitHub**: [https://github.com/sattva/sattva-python-sdk](https://github.com/sattva/sattva-python-sdk)
- **Bug Reports / Баг-репорты**: [GitHub Issues](https://github.com/sattva/sattva-python-sdk/issues)
- **Email / Email**: api@sattva.io

## License (Лицензия)

MIT License - see LICENSE file for details / см. файл LICENSE для деталей
