# WebSocket Events Contract

## Overview

WebSocket API для real-time обновлений плейлиста, мониторинга и событий стрима.

**Base URL**: `ws://localhost:8000/api/ws/`  
**Production**: `wss://your-domain.com/api/ws/`

## Endpoints

### Playlist WebSocket

**URL**: `/api/ws/playlist?channel_id={channel_id}`

Подключение для получения обновлений плейлиста конкретного канала.

### Monitoring WebSocket

**URL**: `/api/ws/monitoring?channel_id={channel_id}&events={events}`

Подключение для получения событий мониторинга.

**Query Parameters**:
- `channel_id` (optional): ID канала для фильтрации
- `events` (optional): Comma-separated список типов событий для подписки

---

## Event Types

### Playlist Events

#### playlist_update

Отправляется при изменении плейлиста (добавление/удаление/перемещение элементов).

```json
{
  "event": "playlist_update",
  "channel_id": "-1001234567890",
  "data": {
    "action": "add",
    "item": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Meditation Music - 1 Hour",
      "url": "https://youtube.com/watch?v=abc123",
      "duration": 3600,
      "source": "youtube",
      "position": 5
    },
    "queue_size": 6
  },
  "timestamp": "2025-12-01T10:30:00.123Z"
}
```

**Actions**:
- `add` - элемент добавлен
- `remove` - элемент удален
- `move` - элемент перемещен
- `clear` - очередь очищена

#### track_change

Отправляется при переключении на следующий трек.

```json
{
  "event": "track_change",
  "channel_id": "-1001234567890",
  "data": {
    "previous_track": {
      "id": "prev-track-id",
      "title": "Previous Track"
    },
    "current_track": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Meditation Music - 1 Hour",
      "url": "https://youtube.com/watch?v=abc123",
      "duration": 3600
    },
    "reason": "track_ended"
  },
  "timestamp": "2025-12-01T10:30:00.123Z"
}
```

**Reasons**:
- `track_ended` - трек завершился естественно
- `skip` - трек пропущен пользователем
- `error` - ошибка воспроизведения

#### queue_update

Полное обновление состояния очереди.

```json
{
  "event": "queue_update",
  "channel_id": "-1001234567890",
  "data": {
    "items": [
      {
        "id": "item-1",
        "title": "Track 1",
        "duration": 180
      },
      {
        "id": "item-2",
        "title": "Track 2",
        "duration": 240
      }
    ],
    "total": 2,
    "current_playing_id": "current-track-id",
    "is_placeholder": false
  },
  "timestamp": "2025-12-01T10:30:00.123Z"
}
```

---

### Monitoring Events

#### metrics_update

Периодическое обновление метрик системы (каждые 5 секунд).

```json
{
  "event": "metrics_update",
  "channel_id": null,
  "data": {
    "cpu_percent": 45.2,
    "memory_percent": 62.5,
    "disk_percent": 35.0,
    "active_streams": 3,
    "total_listeners": 45,
    "websocket_connections": 50
  },
  "timestamp": "2025-12-01T10:30:00.123Z"
}
```

#### stream_status

Изменение статуса стрима.

```json
{
  "event": "stream_status",
  "channel_id": "-1001234567890",
  "data": {
    "status": "playing",
    "previous_status": "paused",
    "is_placeholder": false,
    "current_track": "Meditation Music - 1 Hour",
    "listeners_count": 15
  },
  "timestamp": "2025-12-01T10:30:00.123Z"
}
```

**Statuses**:
- `playing` - воспроизведение
- `paused` - пауза
- `stopped` - остановлен
- `placeholder` - воспроизводится заглушка

#### listeners_update

Изменение количества слушателей.

```json
{
  "event": "listeners_update",
  "channel_id": "-1001234567890",
  "data": {
    "count": 15,
    "previous_count": 14,
    "change": 1
  },
  "timestamp": "2025-12-01T10:30:00.123Z"
}
```

#### auto_end_warning

Предупреждение о скором автоматическом завершении стрима.

```json
{
  "event": "auto_end_warning",
  "channel_id": "-1001234567890",
  "data": {
    "message": "Стрим будет завершен через 60 секунд из-за отсутствия слушателей",
    "remaining_seconds": 60,
    "timeout_at": "2025-12-01T10:35:00.000Z",
    "can_cancel": true
  },
  "timestamp": "2025-12-01T10:34:00.123Z"
}
```

#### system_alert

Системные уведомления (высокая нагрузка, ошибки и т.д.).

```json
{
  "event": "system_alert",
  "channel_id": null,
  "data": {
    "level": "warning",
    "code": "high_cpu",
    "message": "Высокая нагрузка на CPU: 95%",
    "details": {
      "cpu_percent": 95.2,
      "threshold": 90
    }
  },
  "timestamp": "2025-12-01T10:30:00.123Z"
}
```

**Levels**:
- `info` - информационное
- `warning` - предупреждение
- `error` - ошибка
- `critical` - критическая ошибка

---

## Client Messages

### ping

Клиент может отправлять ping для поддержания соединения.

```json
{"type": "ping"}
```

**Response**:
```json
{"type": "pong", "timestamp": "2025-12-01T10:30:00.123Z"}
```

### subscribe

Подписка на дополнительные события (для monitoring WebSocket).

```json
{
  "type": "subscribe",
  "events": ["listeners_update", "auto_end_warning"]
}
```

**Response**:
```json
{
  "type": "subscribed",
  "events": ["listeners_update", "auto_end_warning", "metrics_update"]
}
```

### unsubscribe

Отписка от событий.

```json
{
  "type": "unsubscribe",
  "events": ["metrics_update"]
}
```

---

## Connection Flow

### 1. Initial Connection

```
Client                                Server
  |                                      |
  |  WS Connect /api/ws/monitoring       |
  |  ?channel_id=123&events=metrics      |
  |------------------------------------->|
  |                                      |
  |  Connection Accepted                 |
  |<-------------------------------------|
  |                                      |
  |  {"event": "connected",              |
  |   "data": {"subscribed_events": []}} |
  |<-------------------------------------|
```

### 2. Receiving Events

```
Client                                Server
  |                                      |
  |  (every 5 seconds)                   |
  |  {"event": "metrics_update", ...}    |
  |<-------------------------------------|
  |                                      |
  |  (on listener change)                |
  |  {"event": "listeners_update", ...}  |
  |<-------------------------------------|
```

### 3. Keep-Alive

```
Client                                Server
  |                                      |
  |  {"type": "ping"}                    |
  |------------------------------------->|
  |                                      |
  |  {"type": "pong", ...}               |
  |<-------------------------------------|
```

### 4. Error Handling

```
Client                                Server
  |                                      |
  |  (invalid subscription)              |
  |  {"type": "subscribe",               |
  |   "events": ["invalid_event"]}       |
  |------------------------------------->|
  |                                      |
  |  {"type": "error",                   |
  |   "code": "invalid_event_type",      |
  |   "message": "Unknown event type"}   |
  |<-------------------------------------|
```

---

## TypeScript Types

```typescript
// Event types
type WebSocketEventType = 
  | 'playlist_update'
  | 'track_change'
  | 'queue_update'
  | 'metrics_update'
  | 'stream_status'
  | 'listeners_update'
  | 'auto_end_warning'
  | 'system_alert';

// Base event interface
interface WebSocketEvent<T = unknown> {
  event: WebSocketEventType;
  channel_id: string | null;
  data: T;
  timestamp: string;
}

// Playlist events
interface PlaylistUpdateData {
  action: 'add' | 'remove' | 'move' | 'clear';
  item?: QueueItem;
  queue_size: number;
}

interface TrackChangeData {
  previous_track: QueueItem | null;
  current_track: QueueItem | null;
  reason: 'track_ended' | 'skip' | 'error';
}

interface QueueUpdateData {
  items: QueueItem[];
  total: number;
  current_playing_id: string | null;
  is_placeholder: boolean;
}

// Monitoring events
interface MetricsUpdateData {
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
  active_streams: number;
  total_listeners: number;
  websocket_connections: number;
}

interface StreamStatusData {
  status: 'playing' | 'paused' | 'stopped' | 'placeholder';
  previous_status: string;
  is_placeholder: boolean;
  current_track: string | null;
  listeners_count: number;
}

interface ListenersUpdateData {
  count: number;
  previous_count: number;
  change: number;
}

interface AutoEndWarningData {
  message: string;
  remaining_seconds: number;
  timeout_at: string;
  can_cancel: boolean;
}

interface SystemAlertData {
  level: 'info' | 'warning' | 'error' | 'critical';
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// Client messages
interface ClientMessage {
  type: 'ping' | 'subscribe' | 'unsubscribe';
  events?: WebSocketEventType[];
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| `invalid_channel_id` | Некорректный ID канала |
| `channel_not_found` | Канал не найден |
| `invalid_event_type` | Неизвестный тип события |
| `subscription_failed` | Ошибка подписки |
| `authentication_required` | Требуется авторизация |
| `rate_limit_exceeded` | Превышен лимит запросов |
| `internal_error` | Внутренняя ошибка сервера |

---

## Rate Limits

- **Ping**: максимум 1 раз в 10 секунд
- **Subscribe/Unsubscribe**: максимум 10 операций в минуту
- **Connection**: максимум 5 соединений с одного IP

При превышении лимитов сервер отправляет:

```json
{
  "type": "error",
  "code": "rate_limit_exceeded",
  "message": "Too many requests",
  "retry_after": 60
}
```
