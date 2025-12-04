# Research: Улучшения аудио-стриминга

**Feature**: 017-audio-streaming-enhancements  
**Date**: 2025-01-20  
**Status**: Complete

---

## Обзор исследования

Данный документ содержит результаты анализа исходного кода из YukkiMusicBot и telegram-bot-template для адаптации к проекту Sattva Telegram.

---

## P1: Speed/Pitch Control

### Источник: YukkiMusicBot/plugins/admins/speed.py

**Decision**: Использовать GStreamer элемент `scaletempo` через PyTgCalls

**Rationale**: 
- PyTgCalls уже использует GStreamer для аудио обработки
- `scaletempo` сохраняет pitch при изменении скорости (Time Stretching)
- Диапазон 0.5x-2.0x поддерживается нативно

**Alternatives Considered**:
1. ❌ FFmpeg - требует перекодирования файла, не realtime
2. ❌ SoundTouch - дополнительная зависимость, сложнее интегрировать

**Implementation Pattern**:
```python
# Из YukkiMusicBot speed.py
async def set_speed(chat_id: int, speed: float):
    """
    speed: 0.5 - 2.0
    Использует GStreamer scaletempo element
    """
    call = pytgcalls.get_call(chat_id)
    await call.set_playback_speed(speed)  # PyTgCalls API
```

**Target**: `streamer/playback_control.py`

---

## P1: Seek/Rewind Navigation

### Источник: YukkiMusicBot/plugins/admins/seek.py

**Decision**: Использовать PyTgCalls `seek_stream()` API

**Rationale**:
- PyTgCalls имеет встроенный метод seek
- Поддерживает абсолютную и относительную перемотку
- Работает только для локальных файлов и загруженных стримов

**Alternatives Considered**:
1. ❌ Перезапуск стрима с offset - потеря качества, задержка

**Implementation Pattern**:
```python
# Из YukkiMusicBot seek.py
async def seek_audio(chat_id: int, seconds: int):
    """
    seconds: положительное (вперед) или отрицательное (назад)
    """
    call = pytgcalls.get_call(chat_id)
    current_pos = await call.get_current_position()
    new_pos = max(0, current_pos + seconds)
    await call.seek_stream(new_pos)
```

**Edge Case**: Seek невозможен для live радио-потоков (обработать gracefully)

**Target**: `streamer/playback_control.py`

---

## P1: Radio Streams (HTTP/HTTPS)

### Источник: YukkiMusicBot/plugins/play/radio.py

**Decision**: Использовать PyTgCalls с HTTP URL напрямую

**Rationale**:
- PyTgCalls поддерживает HTTP/HTTPS стримы через GStreamer
- Автоматическая буферизация
- Поддержка ICY metadata (название трека)

**Alternatives Considered**:
1. ❌ FFmpeg pipe - избыточно, PyTgCalls уже поддерживает
2. ❌ yt-dlp для стримов - не нужен для прямых URL

**Implementation Pattern**:
```python
# Из YukkiMusicBot radio.py
async def play_radio(chat_id: int, stream_url: str):
    """
    stream_url: HTTP/HTTPS URL радио-потока
    """
    await pytgcalls.join_group_call(
        chat_id,
        AudioPiped(stream_url),  # GStreamer обработает HTTP
    )
```

**Reconnection Logic**:
```python
MAX_RECONNECT_ATTEMPTS = 3
RECONNECT_DELAY = 5  # seconds

async def on_stream_error(chat_id: int):
    for attempt in range(MAX_RECONNECT_ATTEMPTS):
        await asyncio.sleep(RECONNECT_DELAY)
        if await try_reconnect(chat_id):
            return
    await notify_stream_failed(chat_id)
```

**Target**: `streamer/radio_handler.py`

---

## P1: Rate Limiting (Fixed Window Counter)

### Источник: telegram-bot-template/bot/middlewares/throttling.py

**Decision**: Redis INCR + EXPIRE (Fixed Window Counter)

**Rationale**:
- Простейший алгоритм, достаточный для 100 req/min
- O(1) операции в Redis
- Легко тестировать с fakeredis

**Alternatives Considered**:
1. ❌ Sliding Window Log - избыточно для наших лимитов
2. ❌ Token Bucket - сложнее реализовать, не нужен burst control
3. ❌ Leaky Bucket - избыточно

**Implementation Pattern**:
```python
# Адаптировано из telegram-bot-template
import redis.asyncio as redis

class RateLimiter:
    def __init__(self, redis_client: redis.Redis, limit: int = 100, window: int = 60):
        self.redis = redis_client
        self.limit = limit
        self.window = window
    
    async def is_allowed(self, user_id: str) -> tuple[bool, int]:
        """
        Returns: (allowed: bool, retry_after: int)
        """
        key = f"rate_limit:{user_id}"
        
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, self.window)
        
        if current > self.limit:
            ttl = await self.redis.ttl(key)
            return False, ttl
        
        return True, 0
```

**FastAPI Middleware**:
```python
from fastapi import Request, HTTPException

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    user_id = get_user_id(request)
    allowed, retry_after = await rate_limiter.is_allowed(user_id)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": str(retry_after)}
        )
    
    return await call_next(request)
```

**Target**: `backend/src/middleware/rate_limiter.py`

---

## P2: Priority Queues

### Источник: Custom implementation

**Decision**: Redis Sorted Sets (ZADD/ZPOPMIN)

**Rationale**:
- Redis ZSET идеален для приоритетных очередей
- Атомарные операции
- O(log N) вставка и извлечение

**Implementation Pattern**:
```python
class PriorityQueue:
    PRIORITIES = {"high": 0, "normal": 50, "low": 100}
    
    async def add(self, queue_id: str, item: str, priority: str = "normal"):
        score = self.PRIORITIES[priority] + time.time() / 1e10  # FIFO within priority
        await self.redis.zadd(f"queue:{queue_id}", {item: score})
    
    async def pop(self, queue_id: str) -> str | None:
        result = await self.redis.zpopmin(f"queue:{queue_id}")
        return result[0][0] if result else None
```

**Target**: `backend/src/services/queue_service.py`

---

## P2: Equalizer Presets

### Источник: YukkiMusicBot/plugins/admins/equalizer.py

**Decision**: GStreamer `equalizer-10bands` element

**Rationale**:
- 10-полосный эквалайзер достаточен для всех пресетов
- Нативная поддержка в GStreamer
- Realtime изменение без прерывания воспроизведения

**Presets**:
```python
EQUALIZER_PRESETS = {
    # Стандартные пресеты (из YukkiMusicBot)
    "flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "rock": [5, 4, 3, 2, -1, -1, 0, 2, 3, 4],
    "jazz": [4, 3, 1, 2, -1, -1, 0, 1, 2, 3],
    "classical": [5, 4, 3, 2, -1, -2, 0, 2, 3, 4],
    "voice": [-2, -1, 0, 3, 5, 5, 4, 2, 0, -2],
    "bass_boost": [6, 5, 4, 2, 0, 0, 0, 0, 0, 0],
    
    # Пресеты для медитации и релаксации (Sattva-specific)
    "meditation": [3, 2, 1, 0, -1, -2, -1, 0, 1, 2],      # Мягкие низкие + легкие высокие, убраны средние
    "relax": [2, 3, 2, 1, 0, -1, -1, 0, 1, 1],            # Теплый звук, усиленный бас, мягкие высокие
    "new_age": [4, 3, 2, 0, -2, -2, 0, 2, 3, 4],          # "Космический" звук: бас + высокие, провал средних
    "ambient": [3, 4, 3, 1, -1, -2, -1, 1, 2, 3],         # Атмосферный: широкий звук с акцентом на низкие/высокие
    "sleep": [2, 2, 1, 0, -1, -2, -2, -1, 0, 0],          # Максимально мягкий: убраны средние и высокие
    "nature": [1, 2, 2, 1, 0, 0, 1, 2, 2, 1],             # Естественный: ровный с легким подъёмом
}
```

**Preset Design Rationale**:
| Пресет | Характер звука | Применение |
|--------|----------------|------------|
| meditation | Мягкий, глубокий | Медитация, йога, дыхательные практики |
| relax | Тёплый, обволакивающий | Расслабление, отдых |
| new_age | Космический, эфирный | New Age музыка, синтезаторы |
| ambient | Атмосферный, широкий | Эмбиент, фоновая музыка |
| sleep | Очень мягкий | Засыпание, ASMR |
| nature | Естественный, сбалансированный | Звуки природы, биофония |

**Target**: `streamer/audio_filters.py`

---

## P2: Scheduled Playlists

### Источник: telegram-bot-template/infrastructure/scheduler/

**Decision**: APScheduler с Redis job store

**Rationale**:
- Проверенная библиотека для Python
- Поддержка cron-выражений
- Персистентность через Redis

**Implementation Pattern**:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore

scheduler = AsyncIOScheduler(
    jobstores={"default": RedisJobStore(host="redis")}
)

async def schedule_playlist(playlist_id: str, cron: str):
    scheduler.add_job(
        play_playlist,
        "cron",
        args=[playlist_id],
        **parse_cron(cron),
        id=f"playlist_{playlist_id}"
    )
```

**Target**: `backend/src/services/scheduler_service.py`

---

## P2: Lyrics Display

### Источник: YukkiMusicBot/plugins/tools/lyrics.py

**Decision**: Genius API через lyricsgenius library

**Rationale**:
- Большая база текстов
- Готовая Python библиотека
- Бесплатный API

**Implementation Pattern**:
```python
import lyricsgenius

genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)

async def get_lyrics(artist: str, title: str) -> str | None:
    song = genius.search_song(title, artist)
    return song.lyrics if song else None
```

**Caching Strategy**:
- Кэш в PostgreSQL (LyricsCache entity)
- TTL: 30 дней (тексты не меняются)

**Target**: `backend/src/services/lyrics_service.py`

---

## P3: Shazam-like Recognition

### Источник: YukkiMusicBot/plugins/tools/shazam.py

**Decision**: shazamio library (бесплатная)

**Rationale**:
- Не требует API ключа
- Использует Shazam API напрямую
- Проверена в YukkiMusicBot

**Implementation Pattern**:
```python
from shazamio import Shazam

shazam = Shazam()

async def recognize_song(audio_path: str) -> dict | None:
    result = await shazam.recognize_song(audio_path)
    if result.get("matches"):
        track = result["track"]
        return {
            "title": track["title"],
            "artist": track["subtitle"],
            "album": track.get("sections", [{}])[0].get("metadata", [{}])[0].get("text"),
        }
    return None
```

**Target**: `backend/src/services/shazam_service.py`

---

## P3: i18n Localization

### Источник: telegram-bot-template/bot/locales/

**Decision**: react-i18next для frontend

**Rationale**:
- Индустриальный стандарт для React
- TypeScript support
- Lazy loading переводов
- Browser language detection

**Implementation Pattern**:
```typescript
// frontend/src/i18n/index.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    supportedLngs: ['ru', 'en', 'uk', 'es'],
    interpolation: { escapeValue: false },
  });
```

**Locale Files Structure**:
```json
// frontend/src/i18n/locales/ru.json
{
  "player": {
    "speed": "Скорость",
    "seek_forward": "Вперед {{seconds}} сек",
    "seek_backward": "Назад {{seconds}} сек"
  },
  "equalizer": {
    "preset_rock": "Рок",
    "preset_jazz": "Джаз"
  }
}
```

**Target**: `frontend/src/i18n/`

---

## Зависимости

### Python (backend/streamer)
```
lyricsgenius>=3.0.0    # Genius API
shazamio>=0.4.0        # Shazam recognition
apscheduler>=3.10.0    # Scheduled tasks
redis>=5.0.0           # Already used
```

### Node.js (frontend)
```
react-i18next@^13.0.0
i18next@^23.0.0
i18next-browser-languagedetector@^7.0.0
```

---

## Риски и митигации

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| shazamio API блокировка | Low | Fallback на ACRCloud (платный) |
| Genius rate limits | Medium | Кэширование в DB, retry logic |
| GStreamer scaletempo качество | Low | Протестировать все скорости |
| Redis downtime | Low | Rate limiter fallback: allow all |

---

## Заключение

Все исследовательские задачи завершены. Технические решения приняты на основе анализа исходного кода из YukkiMusicBot и telegram-bot-template. Готовы к Phase 1 (Design & Contracts).
