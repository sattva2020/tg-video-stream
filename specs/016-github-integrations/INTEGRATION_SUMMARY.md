# Интеграция компонентов из GitHub-проектов

**Feature**: 016-github-integrations  
**Дата**: 2025-12-01  
**Статус**: ✅ Завершено (45/45 задач)

---

## 📦 Источники интеграции

### 1. YukkiMusicBot (TeamYukki)

**Репозиторий**: https://github.com/TeamYukki/YukkiMusicBot

**Что взято**:

| Компонент | Исходный файл | Наша реализация | Описание |
|-----------|---------------|-----------------|----------|
| Система очередей | `YukkiMusic/core/queue.py` | `backend/src/services/queue_service.py` | FIFO очередь с Redis persistence |
| StreamQueue | `YukkiMusic/utils/stream/queue.py` | `streamer/queue_manager.py` | Буферизация и подготовка треков |
| Auto-end логика | `YukkiMusic/plugins/play/callback.py` | `streamer/auto_end.py` | Отслеживание слушателей |
| PyTgCalls events | `on_stream_end`, `on_participants_change` | `streamer/auto_end.py` | События завершения и участников |
| Skip/Clear | `YukkiMusic/plugins/admins/skip.py` | `backend/src/api/queue.py` | API для управления очередью |

**Ключевые паттерны из YukkiMusicBot**:

```python
# Оригинал: YukkiMusic/core/queue.py
class Queue:
    def __init__(self):
        self.queue = {}  # chat_id -> list of tracks
    
    async def add(self, chat_id, track):
        if chat_id not in self.queue:
            self.queue[chat_id] = []
        self.queue[chat_id].append(track)

# Наша адаптация: добавили Redis persistence
class QueueService:
    async def add_item(self, channel_id: str, item: QueueItemCreate):
        key = f"stream_queue:{channel_id}"
        await self.redis.rpush(key, item.model_dump_json())
```

```python
# Оригинал: YukkiMusic/plugins/play/callback.py
@app.on_callback_query(filters.regex("^(skip|stop)"))
async def skip_handler(client, callback):
    await pytgcalls.leave_group_call(chat_id)

# Наша адаптация: REST API + WebSocket уведомления
@router.post("/{channel_id}/skip")
async def skip_current(channel_id: str):
    await queue_service.skip(channel_id)
    await ws_manager.broadcast_queue_update(channel_id)
```

---

### 2. telegram-bot-template (Latand)

**Репозиторий**: https://github.com/Latand/telegram-bot-template

**Что взято**:

| Компонент | Исходный файл | Наша реализация | Описание |
|-----------|---------------|-----------------|----------|
| SQLAdmin setup | `infrastructure/database/` | `backend/src/admin/` | Админ-панель для FastAPI |
| User Admin View | `bot/handlers/admin/` | `backend/src/admin/views.py` | CRUD для пользователей |
| Prometheus middleware | `bot/middlewares/` | `backend/src/core/metrics.py` | HTTP метрики |
| Audit logging | `infrastructure/database/repo/` | `backend/src/models/audit_log.py` | Логирование действий |

**Ключевые паттерны**:

```python
# Оригинал: infrastructure/database/ (sqladmin setup)
from sqladmin import Admin, ModelView

admin = Admin(app, engine)

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.is_active]

# Наша адаптация: добавили role-based access
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.telegram_id, User.role]
    form_excluded_columns = [User.hashed_password]
    
    async def is_accessible(self, request):
        return request.state.user.role in ['admin', 'superadmin']
```

```python
# Оригинал: bot/middlewares/ (Prometheus)
from prometheus_client import Counter, Histogram

http_requests = Counter('http_requests_total', 'Total HTTP requests')
http_duration = Histogram('http_request_duration_seconds', 'HTTP latency')

# Наша адаптация: специфичные метрики для стриминга
sattva_streams = Gauge('sattva_active_streams', 'Active streams')
sattva_listeners = Gauge('sattva_stream_listeners', 'Listeners per channel')
sattva_queue_size = Gauge('sattva_queue_size', 'Queue size per channel')
```

---

### 3. Monitrix / Prometheus Best Practices

**Источник**: Официальная документация Prometheus + паттерны из production проектов

**Что взято**:

| Компонент | Описание | Наша реализация |
|-----------|----------|-----------------|
| Naming conventions | `{namespace}_{subsystem}_{name}_{unit}` | `sattva_http_requests_total` |
| Label cardinality | Ограничение уникальных значений | `channel_id`, `method`, `status` |
| Histogram buckets | Стандартные latency buckets | `[0.01, 0.05, 0.1, 0.5, 1, 5]` |

---

## 🔧 Что было реализовано

### Backend (`backend/src/`)

```
backend/src/
├── services/
│   ├── queue_service.py      # 450+ строк — полный CRUD для очереди
│   └── auto_end_service.py   # 350+ строк — таймеры и WebSocket warnings
├── api/
│   ├── queue.py              # REST API для очереди
│   └── websocket.py          # Расширенный ConnectionManager
├── admin/
│   ├── __init__.py           # SQLAdmin setup
│   ├── views.py              # UserAdmin, PlaylistAdmin
│   └── auth.py               # JWT аутентификация
├── core/
│   └── metrics.py            # Prometheus метрики
└── models/
    └── audit_log.py          # Модель для аудита
```

### Streamer (`streamer/`)

```
streamer/
├── queue_manager.py   # StreamQueue + QueueManager с Redis sync
├── auto_end.py        # AutoEndHandler с PyTgCalls integration
├── placeholder.py     # Loop playback для пустой очереди
└── main.py            # Интеграция всех компонентов
```

### Frontend (`frontend/src/`)

```
frontend/src/
├── pages/
│   └── Monitoring.tsx           # Real-time dashboard
├── components/
│   └── StreamCard.tsx           # Карточка стрима
└── hooks/
    └── useMonitoringWebSocket.ts # WebSocket hook
```

---

## 🌟 Что ещё интересного можно взять

### Из YukkiMusicBot

| Функция | Файл | Описание | Сложность |
|---------|------|----------|-----------|
| **Lyrics integration** | `YukkiMusic/plugins/tools/lyrics.py` | Поиск текстов песен через Genius API | Низкая |
| **Shazam recognition** | `YukkiMusic/plugins/tools/shazam.py` | Распознавание треков по аудио | Средняя |
| **Radio streams** | `YukkiMusic/plugins/play/radio.py` | Подключение к онлайн радиостанциям | Низкая |
| **Equalizer** | `YukkiMusic/plugins/admins/equalizer.py` | FFmpeg эквалайзер (bass boost, etc.) | Средняя |
| **Speed control** | `YukkiMusic/plugins/admins/speed.py` | Изменение скорости воспроизведения | Низкая |
| **Seek/Rewind** | `YukkiMusic/plugins/admins/seek.py` | Перемотка трека | Средняя |
| **Stats command** | `YukkiMusic/plugins/admins/stats.py` | Статистика использования бота | Низкая |

**Пример — Lyrics**:
```python
# YukkiMusic/plugins/tools/lyrics.py
from lyricsgenius import Genius

async def get_lyrics(query: str) -> str:
    genius = Genius(GENIUS_TOKEN)
    song = genius.search_song(query)
    return song.lyrics if song else None
```

**Пример — Speed Control**:
```python
# YukkiMusic/plugins/admins/speed.py
# Использует FFmpeg atempo filter
ffmpeg_args = ["-af", f"atempo={speed}"]  # speed: 0.5 - 2.0
```

---

### Из telegram-bot-template

| Функция | Файл/Модуль | Описание | Сложность |
|---------|-------------|----------|-----------|
| **Scheduled tasks** | `infrastructure/scheduler/` | APScheduler для cron jobs | Низкая |
| **Backup system** | `infrastructure/database/backup.py` | Автоматический backup PostgreSQL | Низкая |
| **Rate limiting** | `bot/middlewares/throttling.py` | Redis-based rate limiter | Низкая |
| **Localization** | `bot/locales/` | i18n с Fluent/gettext | Средняя |
| **Feature flags** | `infrastructure/config/features.py` | Включение/выключение функций | Низкая |

**Пример — Scheduled Tasks**:
```python
# infrastructure/scheduler/
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=3)
async def daily_cleanup():
    await cleanup_old_sessions()
    await cleanup_expired_tokens()
```

**Пример — Rate Limiting**:
```python
# bot/middlewares/throttling.py
class RateLimiter:
    async def check(self, user_id: int, limit: int = 10, period: int = 60):
        key = f"rate:{user_id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, period)
        return count <= limit
```

---

### Из других open-source проектов

| Проект | Функция | Описание | Ссылка |
|--------|---------|----------|--------|
| **aiogram-dialog** | Wizard flows | Пошаговые диалоги в Telegram | [GitHub](https://github.com/Tishka17/aiogram_dialog) |
| **FastAPI-Users** | OAuth providers | Google, GitHub, Discord OAuth | [GitHub](https://github.com/fastapi-users/fastapi-users) |
| **Flower** | Celery monitoring | Если добавим Celery для тяжёлых задач | [GitHub](https://github.com/mher/flower) |
| **Grafana Loki** | Log aggregation | Централизованные логи | [Grafana](https://grafana.com/oss/loki/) |
| **Sentry** | Error tracking | Production error monitoring | [Sentry](https://sentry.io/) |

---

## 📊 Рекомендации для следующих фич

### Приоритет 1 (P1) — Быстрые улучшения (2-6 часов)

| № | Фича | Время | Источник | Ценность |
|---|------|-------|----------|----------|
| 1 | **Speed/Pitch control** | 2-3 ч | YukkiMusicBot | ⭐⭐⭐⭐⭐ |
| 2 | **Redis rate limiting** | 2-3 ч | telegram-bot-template | ⭐⭐⭐⭐⭐ |
| 3 | **Seek/Rewind** | 3-4 ч | YukkiMusicBot | ⭐⭐⭐⭐ |
| 4 | **Radio streams** | 2-3 ч | YukkiMusicBot | ⭐⭐⭐ |
| 5 | **Stats dashboard** | 4-6 ч | telegram-bot-template | ⭐⭐⭐⭐ |

#### 1. Speed/Pitch Control ⏱️ 2-3 часа
**Источник**: `YukkiMusicBot/plugins/admins/speed.py`

```python
# Реализация через FFmpeg atempo filter
# Диапазон: 0.5x - 2.0x
SPEED_PRESETS = {
    "0.5x": ["-af", "atempo=0.5"],
    "0.75x": ["-af", "atempo=0.75"],
    "1.25x": ["-af", "atempo=1.25"],
    "1.5x": ["-af", "atempo=1.5"],
    "2.0x": ["-af", "atempo=2.0"],
}
```

**Задачи**:
- [ ] Добавить `speed` параметр в `streamer/main.py`
- [ ] API endpoint `POST /api/stream/{channel_id}/speed`
- [ ] UI кнопки в `StreamCard.tsx`

---

#### 2. Redis Rate Limiting ⏱️ 2-3 часа
**Источник**: `telegram-bot-template/bot/middlewares/throttling.py`

```python
# Sliding window rate limiter
class RateLimiter:
    def __init__(self, redis: Redis, prefix: str = "ratelimit"):
        self.redis = redis
        self.prefix = prefix
    
    async def is_allowed(
        self, 
        key: str, 
        limit: int = 100, 
        window: int = 60
    ) -> bool:
        redis_key = f"{self.prefix}:{key}"
        current = await self.redis.incr(redis_key)
        if current == 1:
            await self.redis.expire(redis_key, window)
        return current <= limit
```

**Задачи**:
- [ ] Создать `backend/src/core/rate_limiter.py`
- [ ] Middleware для FastAPI
- [ ] Конфиг: `RATE_LIMIT_REQUESTS=100`, `RATE_LIMIT_WINDOW=60`

---

#### 3. Seek/Rewind ⏱️ 3-4 часа
**Источник**: `YukkiMusicBot/plugins/admins/seek.py`

```python
# PyTgCalls seek implementation
async def seek_stream(chat_id: int, seconds: int):
    # Получить текущую позицию
    current = await pytgcalls.get_current_position(chat_id)
    new_position = max(0, current + seconds)
    
    # Перезапустить с новой позиции
    await pytgcalls.change_stream(
        chat_id,
        AudioPiped(url, additional_ffmpeg_parameters=[
            "-ss", str(new_position)
        ])
    )
```

**Задачи**:
- [ ] Handler в `streamer/main.py`
- [ ] API: `POST /api/stream/{channel_id}/seek?seconds=30`
- [ ] UI: кнопки ⏪ -10s / +10s ⏩

---

### Приоритет 2 (P2) — Средние улучшения (4-8 часов)

| № | Фича | Время | Источник | Ценность |
|---|------|-------|----------|----------|
| 6 | **Scheduled playlists** | 4-6 ч | telegram-bot-template | ⭐⭐⭐⭐⭐ |
| 7 | **Lyrics display** | 4-6 ч | YukkiMusicBot | ⭐⭐⭐ |
| 8 | **Equalizer presets** | 6-8 ч | YukkiMusicBot | ⭐⭐⭐ |
| 9 | **Backup automation** | 4-6 ч | telegram-bot-template | ⭐⭐⭐⭐⭐ |
| 10 | **Feature flags** | 3-4 ч | telegram-bot-template | ⭐⭐⭐⭐ |

#### 6. Scheduled Playlists ⏱️ 4-6 часов
**Источник**: `telegram-bot-template/infrastructure/scheduler/`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

# Модель расписания
class ScheduledStream(Base):
    id: int
    channel_id: str
    playlist_id: int
    cron_expression: str  # "0 9 * * 1-5" = 9:00 пн-пт
    is_active: bool

# Job
async def start_scheduled_stream(channel_id: str, playlist_id: int):
    playlist = await get_playlist(playlist_id)
    await streamer_api.start(channel_id, playlist)

# Регистрация
scheduler.add_job(
    start_scheduled_stream,
    CronTrigger.from_crontab("0 9 * * 1-5"),
    args=[channel_id, playlist_id],
    id=f"stream_{channel_id}"
)
```

**Задачи**:
- [ ] Модель `ScheduledStream` в БД
- [ ] API: CRUD для расписаний
- [ ] UI: Календарь/расписание
- [ ] Интеграция с systemd для автозапуска scheduler

---

#### 7. Lyrics Display ⏱️ 4-6 часов
**Источник**: `YukkiMusicBot/plugins/tools/lyrics.py`

```python
# Genius API integration
from lyricsgenius import Genius

class LyricsService:
    def __init__(self, token: str):
        self.genius = Genius(token)
    
    async def get_lyrics(self, artist: str, title: str) -> Optional[str]:
        song = self.genius.search_song(title, artist)
        if song:
            return song.lyrics
        return None
    
    async def get_lyrics_by_query(self, query: str) -> Optional[str]:
        song = self.genius.search_song(query)
        return song.lyrics if song else None
```

**Требуется**: `GENIUS_API_TOKEN` в `.env`

**Задачи**:
- [ ] `backend/src/services/lyrics_service.py`
- [ ] API: `GET /api/lyrics?track_id=xxx`
- [ ] UI: Модальное окно с текстом
- [ ] WebSocket: синхронизация с текущим треком

---

#### 8. Equalizer Presets ⏱️ 6-8 часов
**Источник**: `YukkiMusicBot/plugins/admins/equalizer.py`

```python
# FFmpeg audio filters
EQ_PRESETS = {
    "flat": [],
    "bass_boost": ["-af", "bass=g=10:f=110:w=0.6"],
    "treble_boost": ["-af", "treble=g=5:f=3000:w=0.6"],
    "vocal": ["-af", "equalizer=f=1000:width_type=o:width=2:g=3"],
    "electronic": ["-af", "bass=g=7,treble=g=4"],
    "rock": ["-af", "bass=g=4,equalizer=f=2000:width_type=o:width=1:g=2"],
    "jazz": ["-af", "bass=g=3,treble=g=2,equalizer=f=500:width_type=o:width=1:g=1"],
}

async def apply_equalizer(chat_id: int, preset: str):
    eq_args = EQ_PRESETS.get(preset, [])
    # Перезапустить стрим с новыми аргументами FFmpeg
    await restart_with_args(chat_id, eq_args)
```

**Задачи**:
- [ ] Конфиг пресетов в `streamer/config.py`
- [ ] API: `POST /api/stream/{channel_id}/equalizer`
- [ ] UI: Dropdown с пресетами
- [ ] Сохранение выбора в Redis/DB

---

### Приоритет 3 (P3) — Долгосрочные (1-3 дня)

| № | Фича | Время | Источник | Ценность |
|---|------|-------|----------|----------|
| 11 | **Shazam recognition** | 1-2 д | YukkiMusicBot | ⭐⭐⭐ |
| 12 | **Multi-language (i18n)** | 2-3 д | telegram-bot-template | ⭐⭐⭐⭐ |
| 13 | **Telegram bot commands** | 1-2 д | YukkiMusicBot | ⭐⭐⭐⭐ |
| 14 | **Grafana dashboards** | 1 д | Prometheus best practices | ⭐⭐⭐⭐⭐ |
| 15 | **Sentry integration** | 0.5 д | Production best practices | ⭐⭐⭐⭐⭐ |

#### 11. Shazam Recognition ⏱️ 1-2 дня
**Источник**: `YukkiMusicBot/plugins/tools/shazam.py`

```python
from shazamio import Shazam

class ShazamService:
    def __init__(self):
        self.shazam = Shazam()
    
    async def recognize_from_url(self, audio_url: str) -> Optional[dict]:
        # Скачать фрагмент аудио
        audio_data = await download_audio_fragment(audio_url, duration=10)
        
        # Распознать
        result = await self.shazam.recognize(audio_data)
        
        if result and 'track' in result:
            return {
                'title': result['track']['title'],
                'artist': result['track']['subtitle'],
                'cover': result['track']['images']['coverart'],
            }
        return None
```

**Задачи**:
- [ ] `backend/src/services/shazam_service.py`
- [ ] API: `POST /api/recognize` (upload audio)
- [ ] Автоматическое тегирование плейлиста
- [ ] UI: Кнопка "Распознать трек"

---

#### 12. Multi-Language Support ⏱️ 2-3 дня
**Источник**: `telegram-bot-template/bot/locales/`

```python
# i18n структура
locales/
├── ru/
│   └── LC_MESSAGES/
│       └── messages.po
├── en/
│   └── LC_MESSAGES/
│       └── messages.po
└── uk/
    └── LC_MESSAGES/
        └── messages.po

# Использование
from babel import Locale
from babel.support import Translations

def _(text: str, locale: str = "ru") -> str:
    translations = Translations.load('locales', [locale])
    return translations.gettext(text)

# В коде
message = _("Stream started", user_locale)
```

**Задачи**:
- [ ] Структура locales/ для backend
- [ ] react-i18next для frontend (уже частично есть)
- [ ] API: определение языка пользователя
- [ ] Перевод всех строк UI

---

#### 14. Grafana Dashboards ⏱️ 1 день

```yaml
# docker-compose.monitoring.yml
services:
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - ./config/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./config/grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
```

**Дашборды**:
- **Overview**: Active streams, total listeners, queue sizes
- **Performance**: API latency p50/p95/p99, error rate
- **Streams**: Per-channel metrics, auto-end events
- **System**: CPU, Memory, Disk, Network

---

#### 15. Sentry Integration ⏱️ 0.5 дня

```python
# backend/src/core/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry():
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "development"),
    )
```

**Задачи**:
- [ ] Создать проект в Sentry
- [ ] Добавить `SENTRY_DSN` в `.env`
- [ ] Интеграция в backend и streamer
- [ ] Алерты в Telegram

---

## 📈 Матрица приоритизации

```
                    ЦЕННОСТЬ
              Высокая ◄─────► Низкая
         ┌─────────────────────────────┐
  Низкая │  Rate Limit │  Lyrics      │
         │  Speed      │  Equalizer   │
 СЛОЖНОСТЬ│  Seek       │  Shazam      │
         ├─────────────┼──────────────┤
  Высокая│  Scheduler  │  i18n        │
         │  Grafana    │              │
         │  Sentry     │              │
         └─────────────────────────────┘
              
Рекомендуемый порядок:
1. Rate Limit + Sentry (защита + мониторинг ошибок)
2. Speed + Seek (UX улучшения)
3. Scheduler (автоматизация)
4. Grafana (observability)
5. Остальное по необходимости
```

---

## 🛠️ Quick Start для каждой фичи

### Минимальный набор для старта

```bash
# 1. Rate Limiting (2-3 часа)
pip install slowapi
# Готовый middleware, минимум кода

# 2. Sentry (30 минут)
pip install sentry-sdk[fastapi]
# Одна функция init_sentry()

# 3. Speed Control (2-3 часа)
# Только изменения в streamer/main.py
# FFmpeg args уже поддерживаются

# 4. Grafana (1 день)
docker-compose -f docker-compose.monitoring.yml up -d
# + импорт готовых дашбордов
```

---

## 📁 Созданные файлы (полный список)

### Backend
- `backend/src/services/queue_service.py`
- `backend/src/services/auto_end_service.py`
- `backend/src/api/queue.py`
- `backend/src/admin/__init__.py`
- `backend/src/admin/views.py`
- `backend/src/admin/auth.py`
- `backend/src/core/metrics.py`
- `backend/tests/test_queue_service.py`
- `backend/tests/test_auto_end_service.py`
- `backend/tests/test_prometheus_metrics.py`
- `backend/tests/api/test_admin_panel.py`

### Streamer
- `streamer/auto_end.py`
- `streamer/placeholder.py`
- `streamer/queue_manager.py` (расширен)
- `streamer/main.py` (расширен)

### Frontend
- `frontend/src/pages/Monitoring.tsx`
- `frontend/src/components/StreamCard.tsx`
- `frontend/src/hooks/useMonitoringWebSocket.ts`

### Documentation
- `docs/features/queue-system.md`
- `docs/features/admin-panel.md`
- `docs/features/monitoring.md`

### Tests
- `tests/smoke/test_queue_operations.sh`
- `tests/smoke/test_auto_end.sh`

---

## 🔗 Ссылки на источники

1. **YukkiMusicBot**: https://github.com/TeamYukki/YukkiMusicBot
   - Лицензия: MIT
   - Stars: 1.5k+
   - Активно поддерживается

2. **telegram-bot-template**: https://github.com/Latand/telegram-bot-template
   - Лицензия: MIT
   - Stars: 500+
   - Best practices для aiogram 3.x

3. **PyTgCalls**: https://github.com/pytgcalls/pytgcalls
   - Официальная библиотека для Group Calls
   - Документация: https://pytgcalls.github.io/

4. **SQLAdmin**: https://github.com/aminalaee/sqladmin
   - Админ-панель для FastAPI/Starlette
   - Документация: https://aminalaee.dev/sqladmin/

5. **Prometheus Python Client**: https://github.com/prometheus/client_python
   - Официальный клиент
   - Документация: https://prometheus.github.io/client_python/

---

*Документ создан: 2025-12-01*  
*Последнее обновление: 2025-12-01*
