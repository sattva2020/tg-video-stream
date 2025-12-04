# Система очередей треков

**Версия**: 1.0  
**Дата**: 2025-12-01  
**Спецификация**: [spec.md](/specs/016-github-integrations/spec.md)

## Обзор

Система очередей треков обеспечивает:
- Динамическое управление порядком воспроизведения
- Персистентность в Redis с автоматическим восстановлением
- Автоматическое переключение между треками
- Воспроизведение placeholder при пустой очереди

## Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Backend     │────▶│      Redis      │
│  (API calls)    │     │  QueueService   │     │  stream_queue:  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │    Streamer     │
                        │  QueueManager   │
                        └─────────────────┘
```

## Компоненты

### QueueService (Backend)

Расположение: `backend/src/services/queue_service.py`

Основные методы:

```python
# Добавление элемента в конец очереди
await queue_service.add_item(channel_id, item_create)

# Приоритетное добавление (в начало)
await queue_service.priority_add(channel_id, item_create)

# Получение очереди
queue_info = await queue_service.get_queue(channel_id)

# Удаление элемента
await queue_service.remove_item(channel_id, item_id)

# Перемещение элемента
await queue_service.move_item(channel_id, item_id, new_position)

# Пропуск текущего трека
next_item = await queue_service.skip_current(channel_id)
```

### Queue API

Расположение: `backend/src/api/queue.py`

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/v1/queue/{channel_id}` | Получить очередь |
| POST | `/api/v1/queue/{channel_id}/items` | Добавить элемент |
| DELETE | `/api/v1/queue/{channel_id}/items/{item_id}` | Удалить элемент |
| PUT | `/api/v1/queue/{channel_id}/items/{item_id}/position` | Переместить |
| POST | `/api/v1/queue/{channel_id}/skip` | Пропустить трек |
| DELETE | `/api/v1/queue/{channel_id}` | Очистить очередь |

### QueueManager (Streamer)

Расположение: `streamer/queue_manager.py`

Отвечает за:
- Буферизацию треков (3 элемента)
- Подготовку прямых ссылок
- Определение типа контента (audio/video)
- Транскодирование при необходимости

## Модель данных

### QueueItem

```python
class QueueItem(BaseModel):
    id: str                    # UUID элемента
    channel_id: int            # ID Telegram канала
    title: str                 # Название трека
    url: str                   # URL источника (YouTube, файл)
    source: QueueSource        # youtube, telegram, file
    duration: Optional[int]    # Длительность в секундах
    thumbnail: Optional[str]   # URL превью
    requested_by: Optional[int] # ID пользователя
    added_at: datetime         # Время добавления
    position: int              # Позиция в очереди
```

### QueueInfo

```python
class QueueInfo(BaseModel):
    channel_id: int
    items: List[QueueItem]
    total_items: int
    is_placeholder_active: bool
```

## Redis Storage

Ключи:
- `stream_queue:{channel_id}` — LIST с JSON-сериализованными QueueItem

Пример:
```bash
# Получить очередь
LRANGE stream_queue:123456 0 -1

# Добавить элемент в конец
RPUSH stream_queue:123456 '{"id":"...","title":"..."}'

# Добавить в начало (priority)
LPUSH stream_queue:123456 '{"id":"...","title":"..."}'

# Размер очереди
LLEN stream_queue:123456
```

## WebSocket события

При изменениях в очереди отправляется событие `queue_update`:

```json
{
    "type": "queue_update",
    "channel_id": 123456,
    "operation": "add",
    "item_id": "uuid-here",
    "position": 5,
    "timestamp": "2025-12-01T12:00:00Z"
}
```

Операции: `add`, `remove`, `move`, `clear`, `skip`, `priority_add`

## Placeholder

При пустой очереди воспроизводится placeholder:

Расположение: `streamer/placeholder.py`

Конфигурация:
```bash
PLACEHOLDER_AUDIO_PATH=/path/to/placeholder.mp3
```

Placeholder циклически воспроизводится до появления треков в очереди.

## Лимиты

| Параметр | Значение |
|----------|----------|
| Максимальный размер очереди | 100 элементов |
| Таймаут добавления | 5 секунд |
| Таймаут операций Redis | 5 секунд |

## Ошибки

| Код | Описание |
|-----|----------|
| 400 | Некорректные данные (URL, position) |
| 404 | Элемент не найден |
| 409 | Очередь полна (100 элементов) |
| 503 | Redis недоступен |

## Тестирование

### Unit тесты
```bash
cd backend
pytest tests/test_queue_service.py -v
```

### Smoke тесты
```bash
./tests/smoke/test_queue_operations.sh http://localhost:8000 123456
```

## Метрики

Prometheus метрики:
- `sattva_queue_size{channel_id}` — размер очереди
- `sattva_queue_operations_total{operation}` — операции с очередью

## См. также

- [Спецификация](/specs/016-github-integrations/spec.md)
- [API контракты](/specs/016-github-integrations/contracts/queue-api.yaml)
- [Auto-End система](./auto-end.md)
