# Система мониторинга

**Версия**: 1.0  
**Дата**: 2025-12-01  
**Спецификация**: [spec.md](/specs/016-github-integrations/spec.md)

## Обзор

Комплексная система мониторинга включает:
- Prometheus метрики для всех компонентов
- WebSocket для real-time обновлений
- React-дашборд с визуализацией
- Auto-end с предупреждениями

## Архитектура

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React UI      │◀───▶│   WebSocket     │◀───▶│   Backend       │
│  Monitoring.tsx │     │   /ws/stats     │     │   FastAPI       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                               ┌────────────────────────┼────────────────────────┐
                               ▼                        ▼                        ▼
                        ┌─────────────┐          ┌─────────────┐          ┌─────────────┐
                        │   Redis     │          │  Prometheus │          │  Streamer   │
                        │   State     │          │   Metrics   │          │  PyTgCalls  │
                        └─────────────┘          └─────────────┘          └─────────────┘
```

## Компоненты

### 1. Prometheus Metrics

Расположение: `backend/src/core/metrics.py`

#### Доступные метрики

| Метрика | Тип | Описание |
|---------|-----|----------|
| `sattva_http_requests_total` | Counter | HTTP запросы по методу, эндпоинту, статусу |
| `sattva_http_request_duration_seconds` | Histogram | Латентность запросов |
| `sattva_active_streams` | Gauge | Количество активных стримов |
| `sattva_stream_listeners` | Gauge | Слушатели по каналам |
| `sattva_queue_size` | Gauge | Размер очереди по каналам |
| `sattva_queue_operations_total` | Counter | Операции с очередью |
| `sattva_auto_end_events_total` | Counter | События auto-end |
| `sattva_websocket_connections` | Gauge | WebSocket подключения |

#### Пример экспорта

```
# GET /metrics

sattva_active_streams 3
sattva_stream_listeners{channel_id="123"} 15
sattva_stream_listeners{channel_id="456"} 8
sattva_queue_size{channel_id="123"} 5
sattva_http_requests_total{method="GET",endpoint="/api/queue",status="200"} 1542
```

### 2. WebSocket Endpoint

Расположение: `backend/src/api/websocket/stats.py`

#### Подключение

```javascript
const ws = new WebSocket('wss://example.com/ws/stats');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

#### Формат сообщений

```typescript
interface StatsMessage {
    type: 'stats' | 'stream_update' | 'auto_end_warning' | 'error';
    timestamp: string;
    data: SystemStats | StreamUpdate | AutoEndWarning;
}

interface SystemStats {
    active_streams: number;
    total_listeners: number;
    queue_items: number;
    cpu_percent: number;
    memory_percent: number;
    uptime_seconds: number;
}

interface StreamUpdate {
    channel_id: string;
    event: 'started' | 'stopped' | 'track_changed';
    current_track?: Track;
    listeners: number;
}

interface AutoEndWarning {
    channel_id: string;
    seconds_remaining: number;
    reason: 'no_listeners';
}
```

#### Интервал обновлений

- System stats: каждые 5 секунд
- Stream updates: real-time (при изменениях)
- Auto-end warnings: 60, 30, 10 секунд до завершения

### 3. React Monitoring Page

Расположение: `frontend/src/pages/Monitoring.tsx`

#### Функции

- **System Metrics Card**: CPU, Memory, Uptime
- **Active Streams Grid**: Все активные стримы
- **Stream Cards**: Трек, слушатели, очередь
- **Auto-End Warnings**: Предупреждения с таймером
- **Connection Status**: Статус WebSocket

#### Хук useMonitoringWebSocket

```typescript
import { useMonitoringWebSocket } from '@/hooks/useMonitoringWebSocket';

function Monitoring() {
    const { 
        stats, 
        streams, 
        warnings, 
        isConnected, 
        error 
    } = useMonitoringWebSocket();
    
    // Рендер UI
}
```

### 4. Auto-End Service

Расположение: `backend/src/services/auto_end_service.py`

#### Логика

```
Слушатели = 0
    ↓
Запуск таймера (5 минут)
    ↓
Предупреждения через WebSocket
(60s, 30s, 10s)
    ↓
Остановка стрима
```

#### Redis ключи

| Ключ | Тип | Описание |
|------|-----|----------|
| `auto_end:{channel_id}:timer` | String+TTL | Время запуска таймера |
| `auto_end:{channel_id}:paused` | String | Флаг паузы (не auto-end при паузе) |

## Интеграция

### Streamer ↔ Backend

```python
# streamer/auto_end.py
class AutoEndHandler:
    async def on_participants_change(self, chat_id: int, participants: list):
        count = len([p for p in participants if p.is_self is False])
        
        if count == 0:
            await self.start_timer(chat_id)
        else:
            await self.cancel_timer(chat_id)
```

### Backend → Frontend

```python
# WebSocket broadcast
async def broadcast_auto_end_warning(channel_id: str, seconds: int):
    await manager.broadcast({
        "type": "auto_end_warning",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "channel_id": channel_id,
            "seconds_remaining": seconds,
            "reason": "no_listeners"
        }
    })
```

## Grafana Dashboards

### Импорт

```bash
# Скопировать dashboard JSON
cp config/monitoring/grafana/dashboards/sattva.json /etc/grafana/dashboards/
```

### Панели

1. **Overview**: Общая статистика
2. **Streams**: Детали по каналам
3. **Queue**: Операции с очередью
4. **Errors**: Ошибки и алерты

## Алерты

### Prometheus Alertmanager

Расположение: `config/monitoring/prometheus/alerts.yml`

```yaml
groups:
  - name: sattva
    rules:
      - alert: NoActiveStreams
        expr: sattva_active_streams == 0
        for: 5m
        labels:
          severity: warning
          
      - alert: HighErrorRate
        expr: rate(sattva_http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
```

### Telegram уведомления

```yaml
# alertmanager.yml
receivers:
  - name: telegram
    telegram_configs:
      - bot_token: ${TELEGRAM_BOT_TOKEN}
        chat_id: ${ADMIN_CHAT_ID}
```

## Конфигурация

### Backend

```bash
# .env
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
STATS_BROADCAST_INTERVAL=5
AUTO_END_TIMEOUT=300
```

### Docker Compose

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./config/monitoring/prometheus:/etc/prometheus
    ports:
      - "9090:9090"
      
  grafana:
    image: grafana/grafana
    volumes:
      - ./config/monitoring/grafana:/etc/grafana
    ports:
      - "3000:3000"
```

## API Endpoints

### GET /metrics

Prometheus формат метрик.

### GET /api/stats

```json
{
    "active_streams": 3,
    "total_listeners": 23,
    "queue_items": 12,
    "uptime": "2d 5h 30m"
}
```

### WS /ws/stats

Real-time статистика (см. формат сообщений выше).

## Тестирование

### Unit тесты

```bash
pytest backend/tests/test_prometheus_metrics.py -v
pytest backend/tests/test_auto_end_service.py -v
```

### Smoke тесты

```bash
./tests/smoke/test_auto_end.sh
```

### Ручная проверка

1. Открыть `/monitoring` в браузере
2. Убедиться в подключении WebSocket
3. Проверить обновление метрик
4. Запустить/остановить стрим
5. Проверить auto-end warning

## Производительность

### WebSocket

- Max подключений: 1000 (настраивается)
- Сжатие: per-message deflate
- Heartbeat: 30 секунд

### Prometheus

- Scrape interval: 15 секунд
- Retention: 15 дней
- Storage: 1GB (приблизительно)

## Troubleshooting

### WebSocket не подключается

1. Проверить CORS настройки
2. Проверить nginx proxy_pass для /ws/
3. Проверить firewall порты

### Метрики не обновляются

1. Проверить `PROMETHEUS_ENABLED=true`
2. Проверить доступ к `/metrics`
3. Проверить scrape config в Prometheus

### Auto-end не срабатывает

1. Проверить Redis подключение
2. Проверить `AUTO_END_TIMEOUT`
3. Проверить логи streamer

## См. также

- [Queue System](./queue-system.md)
- [Admin Panel](./admin-panel.md)
- [Спецификация](/specs/016-github-integrations/spec.md)
