# Research: Интеграция компонентов из GitHub-проектов

**Feature**: 016-github-integrations | **Date**: 2025-12-01  
**Status**: ✅ Complete

## Research Tasks

| # | Question | Status |
|---|----------|--------|
| R1 | PyTgCalls callback для отслеживания слушателей | ✅ |
| R2 | sqladmin интеграция с FastAPI и SQLAlchemy | ✅ |
| R3 | prometheus_client паттерны для Python | ✅ |
| R4 | Redis persistence для asyncio.Queue | ✅ |
| R5 | WebSocket extension patterns для monitoring | ✅ |

---

## R1: PyTgCalls — Отслеживание слушателей

### Контекст
Необходимо определить, когда все слушатели покинули голосовой чат для автоматического завершения стрима (auto-end).

### Исследование

**Источник**: [YukkiMusicBot](https://github.com/TeamYukki/YukkiMusicBot), py-tgcalls документация

**Доступные callback'и в PyTgCalls**:

```python
from pytgcalls import PyTgCalls
from pytgcalls.types import Update

app = PyTgCalls(client)

# Основные события для отслеживания участников:

@app.on_update()
async def on_update(client: PyTgCalls, update: Update):
    """Универсальный обработчик всех событий"""
    pass

@app.on_participants_change()
async def on_participants_change(client: PyTgCalls, update: Update):
    """Вызывается при изменении списка участников голосового чата"""
    chat_id = update.chat_id
    participants = update.participants  # List[GroupCallParticipant]
    # Проверка: если participants == 1 (только бот), запустить auto-end таймер
```

**Структура GroupCallParticipant**:
```python
class GroupCallParticipant:
    user_id: int
    muted: bool
    can_self_unmute: bool
    video: bool
    screen_sharing: bool
    raised_hand: bool
    volume: int
```

**Паттерн из YukkiMusicBot** (`YukkiMusic/plugins/play/callback.py`):
```python
# Проверка количества участников
async def check_participants(chat_id: int) -> int:
    try:
        call = await pytgcalls.get_call(chat_id)
        if call:
            return len(call.participants)
    except Exception:
        return 0
    return 0
```

### Decision

**Выбор**: Использовать `@app.on_participants_change()` callback

**Rationale**:
- Нативный event-driven подход (не polling)
- Минимальная нагрузка на Telegram API
- Проверенный паттерн в YukkiMusicBot
- Точное отслеживание join/leave событий

**Alternatives considered**:
- Polling через `get_call().participants` каждые N секунд — отвергнуто (лишние API вызовы, задержка обнаружения)
- Использование Pyrogram handlers — отвергнуто (требует дополнительной логики синхронизации)

### Implementation Notes

```python
# streamer/auto_end.py

from pytgcalls import PyTgCalls
from pytgcalls.types import Update
import asyncio
from typing import Dict

class AutoEndManager:
    def __init__(self, call: PyTgCalls, timeout_minutes: int = 5):
        self.call = call
        self.timeout_minutes = timeout_minutes
        self.timers: Dict[int, asyncio.Task] = {}  # chat_id -> timer task
    
    async def setup(self):
        """Регистрация callback'а"""
        @self.call.on_participants_change()
        async def on_change(client: PyTgCalls, update: Update):
            await self._handle_participants_change(update)
    
    async def _handle_participants_change(self, update: Update):
        chat_id = update.chat_id
        participants_count = len(update.participants)
        
        # Если остался только бот (1 участник)
        if participants_count <= 1:
            await self._start_auto_end_timer(chat_id)
        else:
            await self._cancel_auto_end_timer(chat_id)
    
    async def _start_auto_end_timer(self, chat_id: int):
        if chat_id in self.timers:
            return  # Таймер уже запущен
        
        async def timer_task():
            await asyncio.sleep(self.timeout_minutes * 60)
            await self._end_stream(chat_id)
        
        self.timers[chat_id] = asyncio.create_task(timer_task())
    
    async def _cancel_auto_end_timer(self, chat_id: int):
        if chat_id in self.timers:
            self.timers[chat_id].cancel()
            del self.timers[chat_id]
    
    async def _end_stream(self, chat_id: int):
        await self.call.leave_call(chat_id)
        del self.timers[chat_id]
```

---

## R2: sqladmin — Административная панель для FastAPI

### Контекст
Текущий проект использует Flask-Admin в нескольких местах (telegram-bot-template). Нужно найти эквивалент для FastAPI.

### Исследование

**Источник**: [sqladmin](https://github.com/aminalaee/sqladmin), версия 0.16+

**Ключевые особенности**:
- Нативная поддержка FastAPI и Starlette
- Асинхронная работа с SQLAlchemy 2.0
- Встроенная аутентификация через Starlette
- Расширяемые views и формы

**Пример интеграции**:

```python
# backend/src/admin/__init__.py

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import engine
from src.models.user import User
from src.models.playlist import PlaylistItem
from src.admin.views import UserAdmin, PlaylistAdmin

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        
        # Валидация через существующий auth_service
        session = request.state.db
        user = await auth_service.authenticate(session, username, password)
        
        if user and user.role in ["admin", "superadmin"]:
            request.session.update({"admin_user_id": user.id})
            return True
        return False
    
    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True
    
    async def authenticate(self, request: Request) -> bool:
        return "admin_user_id" in request.session

def setup_admin(app: FastAPI):
    authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=authentication_backend,
        title="Sattva Admin",
        base_url="/admin"
    )
    
    admin.add_view(UserAdmin)
    admin.add_view(PlaylistAdmin)
    admin.add_view(AuditLogAdmin)
    
    return admin
```

**Пример ModelView**:

```python
# backend/src/admin/views.py

from sqladmin import ModelView
from src.models.user import User, UserRole

class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"
    
    column_list = [User.id, User.email, User.telegram_id, User.role, User.status, User.created_at]
    column_searchable_list = [User.email, User.telegram_id]
    column_sortable_list = [User.id, User.created_at, User.role]
    column_default_sort = [(User.created_at, True)]
    
    form_excluded_columns = [User.hashed_password, User.created_at, User.updated_at]
    
    can_create = True
    can_edit = True
    can_delete = False  # Soft-delete only
    can_export = True
    
    async def on_model_change(self, data, model, is_created, request):
        """Hook для audit logging"""
        await audit_service.log_action(
            user_id=request.session.get("admin_user_id"),
            action="create" if is_created else "update",
            model_name="User",
            model_id=model.id,
            changes=data
        )
```

### Decision

**Выбор**: sqladmin с custom AuthenticationBackend

**Rationale**:
- Официально рекомендован для FastAPI
- Async-first архитектура
- Минимальный boilerplate код
- Встроенная поддержка SQLAlchemy 2.0 (уже используется в проекте)

**Alternatives considered**:
- FastAPI-Admin — менее активная разработка, меньше features
- Custom React admin — слишком много работы, дублирование frontend

### Implementation Notes

**Зависимости** (`requirements.txt`):
```txt
sqladmin>=0.16.0
itsdangerous>=2.1.2  # для sessions
```

**Структура файлов**:
```
backend/src/admin/
├── __init__.py      # setup_admin()
├── auth.py          # AdminAuth class
└── views.py         # UserAdmin, PlaylistAdmin, AuditLogAdmin
```

---

## R3: prometheus_client — Метрики для Python

### Контекст
Необходимо экспортировать метрики приложения в Prometheus формате через `/metrics` endpoint.

### Исследование

**Источник**: [prometheus_client](https://github.com/prometheus/client_python), [monitrix](https://github.com/user/monitrix)

**Типы метрик**:

```python
from prometheus_client import Counter, Gauge, Histogram, Summary, Info

# Counter — только увеличивается (запросы, ошибки)
REQUESTS_TOTAL = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Gauge — может увеличиваться/уменьшаться (активные соединения, очередь)
QUEUE_SIZE = Gauge(
    'stream_queue_size',
    'Number of items in stream queue',
    ['channel_id']
)

# Histogram — распределение значений (latency)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# Info — статическая информация
APP_INFO = Info('app', 'Application info')
APP_INFO.info({'version': '1.0.0', 'environment': 'production'})
```

**Интеграция с FastAPI**:

```python
# backend/src/api/metrics.py

from fastapi import APIRouter, Response
from prometheus_client import (
    generate_latest, 
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    multiprocess,
    REGISTRY
)

router = APIRouter(tags=["metrics"])

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Middleware для автоматического сбора HTTP метрик**:

```python
# backend/src/middleware/metrics.py

import time
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'path']
)

class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        # Нормализация path (убрать ID из URL)
        path = self._normalize_path(request.url.path)
        
        REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            path=path
        ).observe(time.time() - start_time)
        
        return response
    
    def _normalize_path(self, path: str) -> str:
        """Заменяет ID на placeholder для группировки"""
        import re
        # /api/users/123 -> /api/users/{id}
        return re.sub(r'/\d+', '/{id}', path)
```

### Decision

**Выбор**: prometheus_client с custom middleware и dedicated metrics

**Rationale**:
- Официальный Python клиент Prometheus
- Стандартный формат экспорта
- Минимальный overhead (<1ms на запрос)
- Поддержка multiprocess mode (важно для Gunicorn)

**Alternatives considered**:
- starlette-prometheus — wrapper, меньше контроля
- Datadog/NewRelic — платные, overkill для проекта

### Implementation Notes

**Метрики для Sattva Streamer**:

```python
# backend/src/services/prometheus_service.py

from prometheus_client import Gauge, Counter, Histogram, Info

# Стримы
ACTIVE_STREAMS = Gauge(
    'sattva_active_streams',
    'Number of active streams',
    ['channel_id']
)

STREAM_LISTENERS = Gauge(
    'sattva_stream_listeners',
    'Number of listeners per stream',
    ['channel_id']
)

STREAM_DURATION = Histogram(
    'sattva_stream_duration_seconds',
    'Stream duration in seconds',
    buckets=(60, 300, 600, 1800, 3600, 7200)
)

# Очереди
QUEUE_SIZE = Gauge(
    'sattva_queue_size',
    'Queue size per channel',
    ['channel_id']
)

QUEUE_OPERATIONS = Counter(
    'sattva_queue_operations_total',
    'Queue operations',
    ['channel_id', 'operation']  # add, remove, skip, clear
)

# Auto-end
AUTO_END_TRIGGERS = Counter(
    'sattva_auto_end_total',
    'Auto-end triggers',
    ['channel_id', 'reason']  # timeout, manual, error
)

# WebSocket
WEBSOCKET_CONNECTIONS = Gauge(
    'sattva_websocket_connections',
    'Active WebSocket connections',
    ['channel_id']
)

# Системные (расширение существующих)
SYSTEM_CPU = Gauge('sattva_system_cpu_percent', 'System CPU usage')
SYSTEM_MEMORY = Gauge('sattva_system_memory_percent', 'System memory usage')
SYSTEM_DISK = Gauge('sattva_system_disk_percent', 'System disk usage')
```

---

## R4: Redis Persistence для asyncio.Queue

### Контекст
Существующий `StreamQueue` в `streamer/queue_manager.py` использует `asyncio.Queue` без персистентности. Нужно добавить Redis backup для recovery после рестарта.

### Исследование

**Источник**: [YukkiMusicBot](https://github.com/TeamYukki/YukkiMusicBot) queue module, Redis patterns

**Паттерн из YukkiMusicBot**:
```python
# YukkiMusic использует MongoDB для персистентности
# Мы адаптируем под Redis (уже есть в проекте)
```

**Redis структуры для очередей**:

```python
# Вариант 1: Redis List (FIFO queue)
# Pros: Atomic LPUSH/RPOP, простота
# Cons: Нет random access

import aioredis

async def push_to_queue(redis: aioredis.Redis, channel_id: int, item: dict):
    key = f"queue:{channel_id}"
    await redis.rpush(key, json.dumps(item))

async def pop_from_queue(redis: aioredis.Redis, channel_id: int) -> dict | None:
    key = f"queue:{channel_id}"
    data = await redis.lpop(key)
    return json.loads(data) if data else None

# Вариант 2: Redis Sorted Set (priority queue)
# Pros: Приоритеты, range queries
# Cons: Сложнее, не нужно для FIFO

# Вариант 3: Redis Stream (advanced queue)
# Pros: Consumer groups, acknowledgment
# Cons: Overkill для нашего случая
```

**Гибридный подход (рекомендуется)**:

```python
# Используем asyncio.Queue для in-memory операций (быстро)
# Redis как backup для recovery (надежно)

class PersistentQueue:
    def __init__(self, redis: aioredis.Redis, channel_id: int, maxsize: int = 100):
        self.redis = redis
        self.channel_id = channel_id
        self.key = f"queue:{channel_id}"
        self.queue = asyncio.Queue(maxsize=maxsize)
    
    async def restore_from_redis(self):
        """Восстановление очереди при старте"""
        items = await self.redis.lrange(self.key, 0, -1)
        for item in items:
            await self.queue.put(json.loads(item))
    
    async def put(self, item: dict):
        """Добавить в память и Redis"""
        await self.queue.put(item)
        await self.redis.rpush(self.key, json.dumps(item))
    
    async def get(self) -> dict:
        """Получить из памяти и удалить из Redis"""
        item = await self.queue.get()
        await self.redis.lpop(self.key)
        return item
    
    async def peek(self) -> dict | None:
        """Посмотреть первый элемент без удаления"""
        if self.queue.empty():
            return None
        # asyncio.Queue не поддерживает peek, используем Redis
        data = await self.redis.lindex(self.key, 0)
        return json.loads(data) if data else None
    
    def qsize(self) -> int:
        return self.queue.qsize()
```

### Decision

**Выбор**: Гибридный подход — asyncio.Queue + Redis List backup

**Rationale**:
- asyncio.Queue для быстрых in-memory операций
- Redis List для персистентности и recovery
- Простая синхронизация через dual-write
- Redis List — native FIFO, идеально подходит

**Alternatives considered**:
- Только Redis — медленнее для высокочастотных операций
- Redis Streams — избыточная сложность
- Celery — overkill, требует отдельного worker process

### Implementation Notes

**Интеграция с существующим StreamQueue**:

```python
# streamer/queue_manager.py (модификация)

class StreamQueue:
    def __init__(self, redis_url: str, channel_id: int, maxsize: int = 3):
        self.channel_id = channel_id
        self.redis_key = f"stream_queue:{channel_id}"
        self.redis = None  # Lazy init
        self.redis_url = redis_url
        self.queue = asyncio.Queue(maxsize=maxsize)
        self.playlist_items: deque = deque()
        # ... остальной код
    
    async def _init_redis(self):
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url)
            await self._restore_from_redis()
    
    async def _restore_from_redis(self):
        """Восстановление при старте"""
        items = await self.redis.lrange(self.redis_key, 0, -1)
        for item_data in items:
            item = PlaylistItem.from_json(item_data)
            self.playlist_items.append(item)
```

---

## R5: WebSocket Extension для Monitoring

### Контекст
Существующий WebSocket в `backend/src/api/websocket.py` используется для playlist updates. Нужно расширить для monitoring events.

### Исследование

**Источник**: [monitrix](https://github.com/user/monitrix), существующий код проекта

**Текущая реализация** (`backend/src/api/websocket.py`):

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[Optional[str], Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, channel_id: Optional[str] = None):
        await websocket.accept()
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = set()
        self.active_connections[channel_id].add(websocket)
    
    async def broadcast_to_channel(self, channel_id: str, message: dict):
        """Отправка всем подписчикам канала"""
        connections = self.active_connections.get(channel_id, set())
        for connection in connections:
            await connection.send_json(message)
```

**Расширение для monitoring**:

```python
# backend/src/api/websocket.py (расширение)

from enum import Enum
from pydantic import BaseModel
from typing import Literal

class WebSocketEventType(str, Enum):
    # Playlist events (существующие)
    PLAYLIST_UPDATE = "playlist_update"
    TRACK_CHANGE = "track_change"
    QUEUE_UPDATE = "queue_update"
    
    # Monitoring events (новые)
    METRICS_UPDATE = "metrics_update"
    STREAM_STATUS = "stream_status"
    LISTENERS_UPDATE = "listeners_update"
    AUTO_END_WARNING = "auto_end_warning"
    SYSTEM_ALERT = "system_alert"

class WebSocketMessage(BaseModel):
    event: WebSocketEventType
    channel_id: Optional[str] = None
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[Optional[str], Set[WebSocket]] = {}
        self.subscriptions: Dict[WebSocket, Set[WebSocketEventType]] = {}
    
    async def connect(
        self, 
        websocket: WebSocket, 
        channel_id: Optional[str] = None,
        events: Optional[List[WebSocketEventType]] = None
    ):
        """Подключение с опциональной подпиской на события"""
        await websocket.accept()
        
        if channel_id not in self.active_connections:
            self.active_connections[channel_id] = set()
        self.active_connections[channel_id].add(websocket)
        
        # Подписка на конкретные события (или все)
        self.subscriptions[websocket] = set(events) if events else set(WebSocketEventType)
    
    async def broadcast_event(
        self, 
        event_type: WebSocketEventType, 
        data: dict, 
        channel_id: Optional[str] = None
    ):
        """Отправка события только подписанным клиентам"""
        message = WebSocketMessage(
            event=event_type,
            channel_id=channel_id,
            data=data
        )
        
        connections = self.active_connections.get(channel_id, set())
        for conn in connections:
            if event_type in self.subscriptions.get(conn, set()):
                try:
                    await conn.send_json(message.dict())
                except Exception:
                    await self.disconnect(conn, channel_id)
```

**Паттерн подписки на события**:

```python
# frontend/src/hooks/useMonitoring.ts

interface MonitoringEvent {
  event: 'metrics_update' | 'stream_status' | 'listeners_update' | 'auto_end_warning';
  channel_id?: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export function useMonitoring(channelId: string) {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [listeners, setListeners] = useState<number>(0);
  const [autoEndWarning, setAutoEndWarning] = useState<string | null>(null);
  
  useEffect(() => {
    const ws = new WebSocket(
      `${WS_BASE_URL}/api/ws/monitoring?channel_id=${channelId}&events=metrics_update,listeners_update,auto_end_warning`
    );
    
    ws.onmessage = (event) => {
      const message: MonitoringEvent = JSON.parse(event.data);
      
      switch (message.event) {
        case 'metrics_update':
          setMetrics(message.data as SystemMetrics);
          break;
        case 'listeners_update':
          setListeners(message.data.count as number);
          break;
        case 'auto_end_warning':
          setAutoEndWarning(message.data.message as string);
          break;
      }
    };
    
    return () => ws.close();
  }, [channelId]);
  
  return { metrics, listeners, autoEndWarning };
}
```

### Decision

**Выбор**: Расширение существующего ConnectionManager с event subscriptions

**Rationale**:
- Минимальные изменения в существующем коде
- Гибкая система подписок (клиент выбирает нужные события)
- Эффективность — не отправляем ненужные события
- Совместимость с существующим frontend

**Alternatives considered**:
- Отдельный WebSocket endpoint для monitoring — дублирование кода
- Server-Sent Events (SSE) — нет bi-directional, сложнее с reconnect
- GraphQL Subscriptions — требует переписать API

### Implementation Notes

**Новые endpoints**:

```python
# backend/src/api/websocket.py

@router.websocket("/ws/monitoring")
async def monitoring_websocket(
    websocket: WebSocket,
    channel_id: Optional[str] = Query(None),
    events: Optional[str] = Query(None)  # comma-separated
):
    """WebSocket для monitoring events"""
    event_types = None
    if events:
        event_types = [WebSocketEventType(e) for e in events.split(",")]
    
    await manager.connect(websocket, channel_id, event_types)
    
    try:
        while True:
            # Поддержка ping/pong для keep-alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel_id)
```

**Интеграция с metrics**:

```python
# backend/src/services/prometheus_service.py

async def broadcast_metrics(manager: ConnectionManager):
    """Периодическая отправка метрик через WebSocket"""
    while True:
        metrics = await collect_current_metrics()
        await manager.broadcast_event(
            WebSocketEventType.METRICS_UPDATE,
            metrics.dict()
        )
        await asyncio.sleep(5)  # Каждые 5 секунд
```

---

## Summary

| Research | Decision | Confidence |
|----------|----------|------------|
| R1: PyTgCalls | `on_participants_change()` callback | ✅ High |
| R2: sqladmin | sqladmin + custom AuthenticationBackend | ✅ High |
| R3: prometheus_client | prometheus_client + middleware | ✅ High |
| R4: Redis Queue | asyncio.Queue + Redis List hybrid | ✅ High |
| R5: WebSocket | Extend ConnectionManager + subscriptions | ✅ High |

## Next Steps

1. ✅ Research complete
2. → Phase 1: Create `data-model.md` with Queue, StreamMetrics, AdminAuditLog entities
3. → Phase 1: Create `contracts/` with OpenAPI specs
4. → Phase 1: Create `quickstart.md` with setup instructions
