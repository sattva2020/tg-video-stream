# Quickstart Guide: Улучшения аудио-стриминга

**Feature**: 017-audio-streaming-enhancements  
**Date**: 2025-01-20

---

## Быстрый старт

Это руководство поможет разработчику быстро начать работу над фичей.

### Предварительные требования

```bash
# Python 3.11+
python --version  # Python 3.11.x

# Node.js 18+
node --version    # v18.x или выше

# Redis 7+
redis-cli ping    # PONG

# Docker (для локальной разработки)
docker --version
```

### Установка зависимостей

```bash
# Backend
cd backend
pip install lyricsgenius shazamio apscheduler redis

# Frontend
cd frontend
npm install react-i18next i18next i18next-browser-languagedetector
```

---

## Порядок реализации

### Фаза 1: P1 Quick Wins (1-2 недели)

#### 1.1 Rate Limiting (первый приоритет - защита API)

```python
# backend/src/middleware/rate_limiter.py

import redis.asyncio as redis
from fastapi import Request, HTTPException
import time

class RateLimiter:
    def __init__(self, redis_client: redis.Redis, limit: int = 100, window: int = 60):
        self.redis = redis_client
        self.limit = limit
        self.window = window
    
    async def check(self, user_id: str) -> tuple[bool, dict]:
        key = f"rate_limit:{user_id}"
        
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, self.window)
        
        ttl = await self.redis.ttl(key)
        reset_at = int(time.time()) + ttl
        
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.limit - current)),
            "X-RateLimit-Reset": str(reset_at),
        }
        
        if current > self.limit:
            headers["Retry-After"] = str(ttl)
            return False, headers
        
        return True, headers
```

**Тест:**
```python
# backend/tests/unit/test_rate_limiter.py

import pytest
from fakeredis import aioredis
from src.middleware.rate_limiter import RateLimiter

@pytest.fixture
async def rate_limiter():
    redis = aioredis.FakeRedis()
    return RateLimiter(redis, limit=5, window=60)

async def test_allows_requests_under_limit(rate_limiter):
    for i in range(5):
        allowed, _ = await rate_limiter.check("user_1")
        assert allowed is True

async def test_blocks_requests_over_limit(rate_limiter):
    for _ in range(5):
        await rate_limiter.check("user_1")
    
    allowed, headers = await rate_limiter.check("user_1")
    assert allowed is False
    assert "Retry-After" in headers
```

#### 1.2 Speed/Pitch Control

```python
# streamer/playback_control.py

from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped

class PlaybackController:
    def __init__(self, pytgcalls: PyTgCalls):
        self.pytgcalls = pytgcalls
        self._speed_cache: dict[int, float] = {}
    
    async def set_speed(self, chat_id: int, speed: float) -> None:
        """
        Установить скорость воспроизведения.
        
        Args:
            chat_id: ID чата
            speed: Скорость (0.5 - 2.0)
        
        Raises:
            ValueError: Если скорость вне диапазона
        """
        if not 0.5 <= speed <= 2.0:
            raise ValueError(f"Speed must be between 0.5 and 2.0, got {speed}")
        
        call = self.pytgcalls.get_call(chat_id)
        if call:
            await call.set_playback_speed(speed)
            self._speed_cache[chat_id] = speed
    
    async def get_speed(self, chat_id: int) -> float:
        return self._speed_cache.get(chat_id, 1.0)
```

#### 1.3 Seek/Rewind

```python
# streamer/playback_control.py (продолжение)

async def seek(self, chat_id: int, seconds: int) -> tuple[int, int]:
    """
    Перемотать трек.
    
    Args:
        chat_id: ID чата
        seconds: Секунды (положительные - вперед, отрицательные - назад)
    
    Returns:
        (previous_position, new_position)
    
    Raises:
        ValueError: Если seek невозможен (радио-поток)
    """
    call = self.pytgcalls.get_call(chat_id)
    if not call:
        raise ValueError("No active call")
    
    # Проверка на радио
    if call.is_live_stream:
        raise ValueError("Cannot seek in live stream")
    
    current = await call.get_current_position()
    new_pos = max(0, current + seconds)
    duration = await call.get_duration()
    
    if new_pos >= duration:
        # Переход к следующему треку
        await self.next_track(chat_id)
        return current, duration
    
    await call.seek_stream(new_pos)
    return current, new_pos
```

#### 1.4 Radio Streams

```python
# streamer/radio_handler.py

import asyncio
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped

class RadioHandler:
    MAX_RECONNECT_ATTEMPTS = 3
    RECONNECT_DELAY = 5  # seconds
    
    def __init__(self, pytgcalls: PyTgCalls):
        self.pytgcalls = pytgcalls
        self._active_streams: dict[int, str] = {}
        self._reconnect_tasks: dict[int, asyncio.Task] = {}
    
    async def play_radio(self, chat_id: int, stream_url: str) -> None:
        """Начать воспроизведение радио-потока."""
        self._active_streams[chat_id] = stream_url
        
        await self.pytgcalls.join_group_call(
            chat_id,
            AudioPiped(stream_url),
        )
    
    async def on_stream_error(self, chat_id: int, error: Exception) -> None:
        """Обработка ошибки стрима с автопереподключением."""
        stream_url = self._active_streams.get(chat_id)
        if not stream_url:
            return
        
        for attempt in range(self.MAX_RECONNECT_ATTEMPTS):
            await asyncio.sleep(self.RECONNECT_DELAY)
            try:
                await self.play_radio(chat_id, stream_url)
                return  # Success
            except Exception:
                continue
        
        # All attempts failed
        del self._active_streams[chat_id]
        await self._notify_stream_failed(chat_id)
```

---

### Фаза 2: P2 Features (2-3 недели)

#### 2.1 Priority Queues

```python
# backend/src/services/queue_service.py

import time
import redis.asyncio as redis

class PriorityQueueService:
    PRIORITIES = {"high": 0, "normal": 50, "low": 100}
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def add(self, queue_id: str, item: str, priority: str = "normal") -> None:
        """Добавить элемент в очередь с приоритетом."""
        priority_value = self.PRIORITIES.get(priority, 50)
        # FIFO within same priority using timestamp fraction
        score = priority_value + time.time() / 1e10
        await self.redis.zadd(f"queue:{queue_id}", {item: score})
    
    async def pop(self, queue_id: str) -> str | None:
        """Извлечь следующий элемент."""
        result = await self.redis.zpopmin(f"queue:{queue_id}")
        return result[0][0].decode() if result else None
    
    async def list_all(self, queue_id: str) -> list[str]:
        """Получить все элементы очереди."""
        items = await self.redis.zrange(f"queue:{queue_id}", 0, -1)
        return [item.decode() for item in items]
```

#### 2.2 Equalizer Presets

```python
# streamer/audio_filters.py

EQUALIZER_PRESETS = {
    "flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "rock": [5, 4, 3, 2, -1, -1, 0, 2, 3, 4],
    "jazz": [4, 3, 1, 2, -1, -1, 0, 1, 2, 3],
    "classical": [5, 4, 3, 2, -1, -2, 0, 2, 3, 4],
    "voice": [-2, -1, 0, 3, 5, 5, 4, 2, 0, -2],
    "bass_boost": [6, 5, 4, 2, 0, 0, 0, 0, 0, 0],
}

class EqualizerFilter:
    def __init__(self, pytgcalls):
        self.pytgcalls = pytgcalls
    
    async def apply_preset(self, chat_id: int, preset: str) -> list[int]:
        """Применить пресет эквалайзера."""
        if preset not in EQUALIZER_PRESETS:
            raise ValueError(f"Unknown preset: {preset}")
        
        bands = EQUALIZER_PRESETS[preset]
        await self._apply_eq_bands(chat_id, bands)
        return bands
    
    async def _apply_eq_bands(self, chat_id: int, bands: list[int]) -> None:
        """Применить настройки эквалайзера через GStreamer."""
        call = self.pytgcalls.get_call(chat_id)
        if call:
            # GStreamer equalizer-10bands element
            for i, gain in enumerate(bands):
                await call.set_eq_band(i, gain)
```

#### 2.3 Lyrics Service

```python
# backend/src/services/lyrics_service.py

import lyricsgenius
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.lyrics_cache import LyricsCache

class LyricsService:
    CACHE_TTL_DAYS = 30
    
    def __init__(self, genius_token: str, db: AsyncSession):
        self.genius = lyricsgenius.Genius(genius_token)
        self.db = db
    
    async def get_lyrics(self, artist: str, title: str) -> dict | None:
        # Check cache first
        cached = await self._get_cached(artist, title)
        if cached:
            return cached
        
        # Fetch from Genius
        try:
            song = self.genius.search_song(title, artist)
            if not song:
                return None
            
            result = {
                "artist": artist,
                "title": title,
                "lyrics": song.lyrics,
                "source": "genius",
                "source_url": song.url,
            }
            
            # Cache result
            await self._cache_lyrics(result)
            return result
        
        except Exception:
            return None
    
    async def _get_cached(self, artist: str, title: str) -> dict | None:
        result = await self.db.execute(
            select(LyricsCache).where(
                LyricsCache.artist == artist,
                LyricsCache.title == title,
                LyricsCache.expires_at > datetime.utcnow(),
            )
        )
        cache = result.scalar_one_or_none()
        if cache:
            return {
                "artist": cache.artist,
                "title": cache.title,
                "lyrics": cache.lyrics,
                "source": cache.source,
                "cached": True,
            }
        return None
```

---

### Фаза 3: P3 Features (2-3 недели)

#### 3.1 Shazam Recognition

```python
# backend/src/services/shazam_service.py

from shazamio import Shazam
import tempfile

class ShazamService:
    def __init__(self):
        self.shazam = Shazam()
    
    async def recognize(self, audio_bytes: bytes) -> dict | None:
        """Распознать музыку по аудио."""
        # Save to temp file (shazamio requires file path)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_bytes)
            temp_path = f.name
        
        try:
            result = await self.shazam.recognize_song(temp_path)
            
            if not result.get("matches"):
                return None
            
            track = result["track"]
            return {
                "title": track["title"],
                "artist": track["subtitle"],
                "album": self._extract_album(track),
                "cover_url": track.get("images", {}).get("coverart"),
            }
        finally:
            import os
            os.unlink(temp_path)
    
    def _extract_album(self, track: dict) -> str | None:
        sections = track.get("sections", [])
        for section in sections:
            metadata = section.get("metadata", [])
            for item in metadata:
                if item.get("title") == "Album":
                    return item.get("text")
        return None
```

#### 3.2 i18n Setup (Frontend)

```typescript
// frontend/src/i18n/index.ts

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import ru from './locales/ru.json';
import en from './locales/en.json';
import uk from './locales/uk.json';
import es from './locales/es.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      ru: { translation: ru },
      en: { translation: en },
      uk: { translation: uk },
      es: { translation: es },
    },
    fallbackLng: 'en',
    supportedLngs: ['ru', 'en', 'uk', 'es'],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

export default i18n;
```

```json
// frontend/src/i18n/locales/ru.json
{
  "player": {
    "play": "Воспроизвести",
    "pause": "Пауза",
    "speed": "Скорость",
    "speed_value": "{{value}}x",
    "seek_forward": "Вперед {{seconds}} сек",
    "seek_backward": "Назад {{seconds}} сек"
  },
  "equalizer": {
    "title": "Эквалайзер",
    "preset_flat": "Нейтральный",
    "preset_rock": "Рок",
    "preset_jazz": "Джаз",
    "preset_classical": "Классика",
    "preset_voice": "Голос",
    "preset_bass_boost": "Усиление басов"
  },
  "radio": {
    "add_station": "Добавить станцию",
    "now_playing": "Сейчас играет",
    "buffering": "Буферизация...",
    "reconnecting": "Переподключение..."
  },
  "lyrics": {
    "show": "Показать текст",
    "hide": "Скрыть текст",
    "not_found": "Текст не найден",
    "loading": "Загрузка текста..."
  }
}
```

```tsx
// frontend/src/components/LanguageSwitcher.tsx

import { useTranslation } from 'react-i18next';

const languages = [
  { code: 'ru', name: 'Русский', flag: '🇷🇺' },
  { code: 'en', name: 'English', flag: '🇬🇧' },
  { code: 'uk', name: 'Українська', flag: '🇺🇦' },
  { code: 'es', name: 'Español', flag: '🇪🇸' },
];

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  
  return (
    <select
      value={i18n.language}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
      className="language-select"
    >
      {languages.map((lang) => (
        <option key={lang.code} value={lang.code}>
          {lang.flag} {lang.name}
        </option>
      ))}
    </select>
  );
}
```

---

## Тестирование

### Unit Tests

```bash
# Backend
cd backend
pytest tests/unit/ -v

# Frontend
cd frontend
npm test
```

### Integration Tests

```bash
# API tests
pytest tests/integration/test_playback_api.py -v

# E2E tests
cd frontend
npx playwright test
```

### Ручная проверка

1. **Rate Limiting**: Отправить 101 запрос за минуту → получить 429
2. **Speed Control**: Изменить скорость на 1.5x → звук ускоряется
3. **Seek**: Нажать -30 сек → позиция изменяется
4. **Radio**: Добавить URL радио → воспроизведение начинается
5. **Equalizer**: Выбрать "Rock" → звук изменяется
6. **Lyrics**: Открыть текст → текст отображается
7. **i18n**: Переключить на английский → интерфейс на английском

---

## Чеклист перед коммитом

- [ ] Все тесты проходят
- [ ] Lint проверка пройдена
- [ ] Миграции созданы и применены
- [ ] API документация обновлена
- [ ] README обновлен (если нужно)
- [ ] CHANGELOG обновлен

---

## Полезные ссылки

- [YukkiMusicBot](https://github.com/TeamYukki/YukkiMusicBot) - источник кода
- [telegram-bot-template](https://github.com/Latand/telegram-bot-template) - rate limiting, scheduler
- [lyricsgenius](https://pypi.org/project/lyricsgenius/) - Genius API
- [shazamio](https://pypi.org/project/shazamio/) - Shazam recognition
- [react-i18next](https://react.i18next.com/) - i18n для React
