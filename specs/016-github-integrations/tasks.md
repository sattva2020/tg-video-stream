# Tasks Decomposition: 016-github-integrations

**Branch**: `016-github-integrations` | **Date**: 2025-12-01 | **Plan**: [plan.md](./plan.md)

## Обзор

Декомпозиция feature на конкретные задачи для разработки. Каждая задача:
- Независима и может быть выполнена изолированно
- Имеет чёткие критерии приёмки (DoD)
- Ссылается на источник паттерна из GitHub

---

## Sprint 1: Core — Queue & Auto-End (P1)

### TASK-001: Модель QueueItem и Redis persistence

**Тип**: Backend  
**Источник**: [YukkiMusicBot/core/queue.py](https://github.com/TeamYukki/YukkiMusicBot)  
**Оценка**: 4h  
**Файлы**:
- `backend/src/models/queue.py` — NEW
- `backend/src/services/queue_service.py` — NEW

**Описание**:
Создать Pydantic модель QueueItem и сервис для работы с очередью в Redis.

**Acceptance Criteria**:
- [ ] Модель QueueItem с полями: id, title, url, duration, source, position, added_by, added_at
- [ ] Сериализация/десериализация в JSON для Redis
- [ ] CRUD операции: add, remove, get_all, clear
- [ ] Unit-тесты для queue_service

**Code Pattern** (из YukkiMusicBot):
```python
# Адаптировать из YukkiMusic/core/queue.py
class Queue:
    def __init__(self):
        self.queue: Dict[str, List[QueueItem]] = {}
    
    async def add(self, chat_id: str, item: QueueItem) -> int:
        """Добавить в конец очереди, вернуть позицию"""
        
    async def get_next(self, chat_id: str) -> Optional[QueueItem]:
        """Получить и удалить следующий элемент"""
```

---

### TASK-002: Queue API endpoints

**Тип**: Backend API  
**Источник**: [contracts/queue-api.yaml](./contracts/queue-api.yaml)  
**Оценка**: 3h  
**Зависит от**: TASK-001  
**Файлы**:
- `backend/src/api/queue.py` — NEW
- `backend/src/api/__init__.py` — MODIFY (add router)

**Описание**:
REST API для управления очередью стрима.

**Endpoints**:
- `GET /api/v1/queue/{channel_id}` — получить очередь
- `POST /api/v1/queue/{channel_id}/items` — добавить элемент
- `DELETE /api/v1/queue/{channel_id}/items/{item_id}` — удалить
- `PUT /api/v1/queue/{channel_id}/items/{item_id}/position` — переместить
- `POST /api/v1/queue/{channel_id}/skip` — пропустить текущий
- `DELETE /api/v1/queue/{channel_id}` — очистить очередь

**Acceptance Criteria**:
- [ ] Все endpoints реализованы согласно OpenAPI spec
- [ ] Авторизация: admin/moderator для модификаций
- [ ] Валидация channel_id
- [ ] Integration tests

---

### TASK-003: Интеграция Queue в Streamer

**Тип**: Streamer  
**Источник**: [YukkiMusicBot](https://github.com/TeamYukki/YukkiMusicBot)  
**Оценка**: 4h  
**Зависит от**: TASK-001  
**Файлы**:
- `streamer/queue_manager.py` — NEW
- `streamer/main.py` — MODIFY

**Описание**:
Интеграция queue_service в streamer для автоматического переключения треков.

**Acceptance Criteria**:
- [ ] Автоматическое получение следующего трека при завершении текущего
- [ ] Fallback на placeholder при пустой очереди
- [ ] Синхронизация с Redis при старте
- [ ] Smoke-тест: добавить 3 трека, проверить автопереключение

**Code Pattern**:
```python
class QueueManager:
    async def on_track_end(self, channel_id: str):
        next_item = await self.queue_service.get_next(channel_id)
        if next_item:
            await self.play_track(next_item)
        else:
            await self.play_placeholder(channel_id)
```

---

### TASK-004: Placeholder audio support

**Тип**: Streamer  
**Источник**: [YukkiMusicBot](https://github.com/TeamYukki/YukkiMusicBot)  
**Оценка**: 2h  
**Зависит от**: TASK-003  
**Файлы**:
- `streamer/placeholder.py` — NEW
- `data/placeholder.mp3` — NEW (asset)
- `template.env` — MODIFY

**Описание**:
Воспроизведение заглушки когда очередь пуста.

**Acceptance Criteria**:
- [ ] Placeholder воспроизводится в цикле
- [ ] Настраиваемый путь через `PLACEHOLDER_AUDIO_PATH`
- [ ] Автоматическое переключение на реальный трек при появлении
- [ ] Индикатор placeholder в метриках

---

### TASK-005: Auto-end сервис

**Тип**: Backend + Streamer  
**Источник**: [YukkiMusicBot/plugins/play/callback.py](https://github.com/TeamYukki/YukkiMusicBot)  
**Оценка**: 4h  
**Файлы**:
- `backend/src/services/auto_end_service.py` — NEW
- `streamer/auto_end.py` — NEW
- `template.env` — MODIFY

**Описание**:
Автоматическое завершение стрима при отсутствии слушателей.

**Acceptance Criteria**:
- [ ] Отслеживание через PyTgCalls `on_participants_change`
- [ ] Настраиваемый таймаут через `AUTO_END_TIMEOUT_MINUTES` (default: 5)
- [ ] Сброс таймера при появлении слушателя
- [ ] Логирование причины завершения
- [ ] Unit-тесты с mock PyTgCalls

**Code Pattern** (из YukkiMusicBot):
```python
@app.on_participants_change()
async def participants_change_handler(client, chat_id, participants):
    if len(participants) == 0:
        await auto_end_service.start_timer(chat_id)
    else:
        await auto_end_service.cancel_timer(chat_id)
```

---

### TASK-006: WebSocket события очереди

**Тип**: Backend  
**Источник**: [contracts/websocket-events.md](./contracts/websocket-events.md)  
**Оценка**: 3h  
**Зависит от**: TASK-001, TASK-002  
**Файлы**:
- `backend/src/api/websocket.py` — MODIFY

**Описание**:
Расширение WebSocket для событий очереди: playlist_update, track_change, queue_update.

**Acceptance Criteria**:
- [ ] События отправляются при изменении очереди
- [ ] Формат согласно websocket-events.md
- [ ] Подписка по channel_id
- [ ] Frontend получает обновления без перезагрузки

---

### TASK-007: Smoke-тесты Queue & Auto-End

**Тип**: Testing  
**Оценка**: 2h  
**Зависит от**: TASK-003, TASK-005  
**Файлы**:
- `tests/smoke/test_queue_operations.sh` — NEW
- `tests/smoke/test_auto_end.sh` — NEW

**Описание**:
End-to-end smoke тесты для проверки основных сценариев.

**Acceptance Criteria**:
- [ ] test_queue_operations: добавление, удаление, переключение
- [ ] test_auto_end: запуск без слушателей → таймаут → завершение
- [ ] Запуск в CI/CD pipeline

---

## Sprint 2: Admin Panel & Metrics (P2)

### TASK-008: sqladmin setup

**Тип**: Backend  
**Источник**: [telegram-bot-template](https://github.com/Latand/telegram-bot-template)  
**Оценка**: 3h  
**Файлы**:
- `backend/src/admin/__init__.py` — NEW
- `backend/src/admin/auth.py` — NEW
- `backend/requirements.txt` — MODIFY

**Описание**:
Установка и настройка sqladmin для FastAPI.

**Acceptance Criteria**:
- [ ] sqladmin интегрирован в FastAPI app
- [ ] Custom AuthenticationBackend с проверкой ролей
- [ ] Доступ только для admin/superadmin
- [ ] `/admin` endpoint работает

**Code Pattern**:
```python
from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend

class AdminAuth(AuthenticationBackend):
    async def login(self, request) -> bool:
        # JWT/session validation
        
    async def logout(self, request) -> bool:
        # Clear session
        
    async def authenticate(self, request) -> Optional[str]:
        # Return user if authenticated
```

---

### TASK-009: Admin Views для основных моделей

**Тип**: Backend  
**Источник**: [telegram-bot-template](https://github.com/Latand/telegram-bot-template)  
**Оценка**: 4h  
**Зависит от**: TASK-008  
**Файлы**:
- `backend/src/admin/views.py` — NEW

**Описание**:
CRUD views для User, Playlist, Track, Stream.

**Acceptance Criteria**:
- [ ] UserAdmin: list, search, edit role, deactivate
- [ ] PlaylistAdmin: list, view items, bulk actions
- [ ] StreamAdmin: view status, stop stream
- [ ] Форматирование дат, статусов, ссылок

---

### TASK-010: AdminAuditLog модель и логирование

**Тип**: Backend  
**Источник**: [telegram-bot-template](https://github.com/Latand/telegram-bot-template)  
**Оценка**: 3h  
**Зависит от**: TASK-009  
**Файлы**:
- `backend/src/models/audit_log.py` — NEW
- `backend/migrations/versions/xxx_add_audit_log.py` — NEW

**Описание**:
Логирование всех действий администраторов.

**Acceptance Criteria**:
- [ ] Модель AdminAuditLog в PostgreSQL
- [ ] Автоматическое логирование CRUD операций
- [ ] Просмотр логов в админ-панели
- [ ] Фильтрация по admin_id, action, target

---

### TASK-011: Prometheus metrics endpoint

**Тип**: Backend  
**Источник**: [telegram-bot-template/bot/middlewares/](https://github.com/Latand/telegram-bot-template)  
**Оценка**: 3h  
**Файлы**:
- `backend/src/services/prometheus_service.py` — NEW
- `backend/src/api/metrics.py` — NEW
- `backend/requirements.txt` — MODIFY

**Описание**:
Экспорт метрик в формате Prometheus.

**Acceptance Criteria**:
- [ ] `/metrics` endpoint возвращает OpenMetrics формат
- [ ] Метрики: http_requests_total, http_request_duration_seconds
- [ ] Метрики: active_streams, total_listeners, websocket_connections
- [ ] Middleware для автоматического сбора request metrics

**Code Pattern**:
```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Request latency')
ACTIVE_STREAMS = Gauge('active_streams', 'Currently active streams')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

### TASK-012: System metrics collection

**Тип**: Backend  
**Источник**: [contracts/metrics-api.yaml](./contracts/metrics-api.yaml)  
**Оценка**: 2h  
**Зависит от**: TASK-011  
**Файлы**:
- `backend/src/services/prometheus_service.py` — MODIFY

**Описание**:
Сбор системных метрик: CPU, memory, disk.

**Acceptance Criteria**:
- [ ] `GET /api/v1/metrics/system` возвращает JSON
- [ ] cpu_percent, memory_percent, disk_percent
- [ ] Кеширование в Redis (5 сек TTL)
- [ ] Экспорт в Prometheus формат

---

### TASK-013: Admin панель UI тесты

**Тип**: Testing  
**Оценка**: 3h  
**Зависит от**: TASK-009  
**Файлы**:
- `backend/tests/api/test_admin_panel.py` — NEW

**Описание**:
Тесты для админ-панели.

**Acceptance Criteria**:
- [ ] Login/logout flow
- [ ] CRUD операции для User
- [ ] Проверка разграничения доступа по ролям
- [ ] Audit log записывается

---

## Sprint 3: WebSocket Monitoring & Frontend (P3)

### TASK-014: WebSocket monitoring events

**Тип**: Backend  
**Источник**: [monitrix](https://github.com/user/monitrix)  
**Оценка**: 3h  
**Зависит от**: TASK-011  
**Файлы**:
- `backend/src/api/websocket.py` — MODIFY

**Описание**:
Расширение WebSocket для событий мониторинга.

**Events**:
- `metrics_update` — периодические метрики системы
- `stream_status` — изменение статуса стрима
- `listeners_update` — изменение количества слушателей
- `auto_end_warning` — предупреждение о скором завершении

**Acceptance Criteria**:
- [ ] Все события согласно contracts/websocket-events.md
- [ ] Подписка на типы событий
- [ ] Throttling для metrics_update (5 сек)
- [ ] Автопереподключение клиента

---

### TASK-015: Frontend Monitoring.tsx

**Тип**: Frontend  
**Источник**: [monitrix](https://github.com/user/monitrix)  
**Оценка**: 4h  
**Зависит от**: TASK-014  
**Файлы**:
- `frontend/src/pages/Monitoring.tsx` — NEW
- `frontend/src/components/StreamCard.tsx` — NEW
- `frontend/src/hooks/useMonitoringWebSocket.ts` — NEW

**Описание**:
Real-time dashboard для мониторинга стримов.

**Acceptance Criteria**:
- [ ] Карточки активных стримов
- [ ] Графики CPU/memory (последние 5 минут)
- [ ] Счётчики слушателей в реальном времени
- [ ] Индикаторы статуса (playing, paused, placeholder)
- [ ] Адаптивный дизайн

---

### TASK-016: Integration tests

**Тип**: Testing  
**Оценка**: 4h  
**Зависит от**: TASK-014, TASK-015  
**Файлы**:
- `frontend/tests/monitoring.spec.ts` — NEW
- `backend/tests/integration/test_websocket_monitoring.py` — NEW

**Описание**:
End-to-end тесты для мониторинга.

**Acceptance Criteria**:
- [ ] WebSocket connection → receive events
- [ ] Frontend отображает обновления
- [ ] Playwright тест для Monitoring.tsx

---

### TASK-017: Документация feature

**Тип**: Documentation  
**Оценка**: 2h  
**Файлы**:
- `docs/features/queue-system.md` — NEW
- `docs/features/admin-panel.md` — NEW
- `docs/features/monitoring.md` — NEW

**Описание**:
Документация для новых модулей.

**Acceptance Criteria**:
- [ ] Описание функционала
- [ ] API reference
- [ ] Конфигурация
- [ ] `npm run docs:validate` проходит

---

## Сводка задач

| ID | Название | Sprint | Оценка | Зависит от |
|----|----------|--------|--------|------------|
| TASK-001 | QueueItem модель и Redis persistence | 1 | 4h | - |
| TASK-002 | Queue API endpoints | 1 | 3h | TASK-001 |
| TASK-003 | Интеграция Queue в Streamer | 1 | 4h | TASK-001 |
| TASK-004 | Placeholder audio support | 1 | 2h | TASK-003 |
| TASK-005 | Auto-end сервис | 1 | 4h | - |
| TASK-006 | WebSocket события очереди | 1 | 3h | TASK-001, TASK-002 |
| TASK-007 | Smoke-тесты Queue & Auto-End | 1 | 2h | TASK-003, TASK-005 |
| TASK-008 | sqladmin setup | 2 | 3h | - |
| TASK-009 | Admin Views для моделей | 2 | 4h | TASK-008 |
| TASK-010 | AdminAuditLog модель | 2 | 3h | TASK-009 |
| TASK-011 | Prometheus metrics endpoint | 2 | 3h | - |
| TASK-012 | System metrics collection | 2 | 2h | TASK-011 |
| TASK-013 | Admin панель UI тесты | 2 | 3h | TASK-009 |
| TASK-014 | WebSocket monitoring events | 3 | 3h | TASK-011 |
| TASK-015 | Frontend Monitoring.tsx | 3 | 4h | TASK-014 |
| TASK-016 | Integration tests | 3 | 4h | TASK-014, TASK-015 |
| TASK-017 | Документация feature | 3 | 2h | - |

**Итого**: 17 задач, ~53 часов (~7 рабочих дней)

---

## Граф зависимостей

```
Sprint 1 (P1):
TASK-001 ─┬─> TASK-002 ─┬─> TASK-006
          │             │
          └─> TASK-003 ─┴─> TASK-007
                │
                └─> TASK-004

TASK-005 ────────────────> TASK-007

Sprint 2 (P2):
TASK-008 ──> TASK-009 ──> TASK-010
                    │
                    └──> TASK-013

TASK-011 ──> TASK-012

Sprint 3 (P3):
TASK-011 ──> TASK-014 ──> TASK-015 ──> TASK-016
```

---

## Критический путь

```
TASK-001 → TASK-003 → TASK-004 → TASK-007
         (4h)        (4h)       (2h)      (2h)
         
Total: 12h (критический путь Sprint 1)
```

Параллельно можно выполнять:
- TASK-005 (auto-end)
- TASK-008 (sqladmin setup)
- TASK-011 (Prometheus)
