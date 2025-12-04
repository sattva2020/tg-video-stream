# Data Model: Улучшения аудио-стриминга

**Feature**: 017-audio-streaming-enhancements  
**Date**: 2025-01-20  
**Status**: Complete

---

## Обзор сущностей

| Entity | Storage | Purpose |
|--------|---------|---------|
| PlaybackSettings | PostgreSQL | Пользовательские настройки воспроизведения |
| RadioStream | PostgreSQL | Информация о радио-потоках |
| ScheduledPlaylist | PostgreSQL | Запланированные плейлисты |
| LyricsCache | PostgreSQL | Кэш текстов песен |
| RateLimitCounter | Redis | Счетчики rate limiting |
| PriorityQueue | Redis | Очередь с приоритетами |

---

## PostgreSQL Entities

### PlaybackSettings

Хранит персональные настройки воспроизведения пользователя.

```python
# backend/src/models/playback_settings.py

from sqlalchemy import Column, Integer, Float, String, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.models.base import Base

class PlaybackSettings(Base):
    __tablename__ = "playback_settings"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Speed/Pitch
    speed = Column(Float, default=1.0)  # 0.5 - 2.0
    pitch_correction = Column(Boolean, default=True)
    
    # Equalizer
    equalizer_preset = Column(String(50), default="flat")  # flat, rock, jazz, etc.
    equalizer_custom = Column(JSON, nullable=True)  # [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    
    # UI Preferences
    language = Column(String(5), default="ru")  # ru, en, uk, es
    show_lyrics = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="playback_settings")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("speed >= 0.5 AND speed <= 2.0", name="speed_range"),
        CheckConstraint("language IN ('ru', 'en', 'uk', 'es')", name="valid_language"),
    )
```

**Validation Rules**:
- `speed`: 0.5 ≤ speed ≤ 2.0
- `equalizer_preset`: One of predefined presets
- `language`: One of supported locales

---

### RadioStream

Информация о сохраненных радио-потоках.

```python
# backend/src/models/radio_stream.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from src.models.base import Base

class RadioStream(Base):
    __tablename__ = "radio_streams"
    
    id = Column(Integer, primary_key=True)
    
    # Stream info
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False, unique=True)
    genre = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    
    # Metadata
    logo_url = Column(String(1024), nullable=True)
    bitrate = Column(Integer, nullable=True)  # kbps
    
    # Status
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("url LIKE 'http%'", name="valid_url"),
    )
```

**Validation Rules**:
- `url`: Must start with http:// or https://
- `bitrate`: Positive integer if provided

---

### ScheduledPlaylist

Запланированные плейлисты для автоматического воспроизведения.

```python
# backend/src/models/scheduled_playlist.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.models.base import Base
import enum

class RepeatType(enum.Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class ScheduledPlaylist(Base):
    __tablename__ = "scheduled_playlists"
    
    id = Column(Integer, primary_key=True)
    
    # Schedule
    name = Column(String(255), nullable=False)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    repeat_type = Column(Enum(RepeatType), default=RepeatType.ONCE)
    cron_expression = Column(String(100), nullable=True)  # For complex schedules
    
    # Status
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    
    # Conflict resolution
    override_current = Column(Boolean, default=False)  # Override manual playback?
    
    # Ownership
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    playlist = relationship("Playlist", back_populates="schedules")
    creator = relationship("User")
```

**State Transitions**:
```
[Created] -> [Pending] -> [Running] -> [Completed]
                 |             |
                 v             v
             [Cancelled]   [Failed]
```

---

### LyricsCache

Кэш текстов песен из Genius API.

```python
# backend/src/models/lyrics_cache.py

from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.sql import func
from src.models.base import Base

class LyricsCache(Base):
    __tablename__ = "lyrics_cache"
    
    id = Column(Integer, primary_key=True)
    
    # Track identification
    artist = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    
    # Lyrics
    lyrics = Column(Text, nullable=True)  # Plain text
    synced_lyrics = Column(Text, nullable=True)  # LRC format with timestamps
    
    # Source
    source = Column(String(50), default="genius")  # genius, manual
    source_url = Column(String(1024), nullable=True)
    
    # Cache metadata
    fetched_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)  # 30 days TTL
    
    # Indexes
    __table_args__ = (
        Index("idx_lyrics_artist_title", "artist", "title", unique=True),
    )
```

**Cache Strategy**:
- TTL: 30 days
- On miss: Fetch from Genius API
- On error: Store null with short TTL (1 day)

---

## Redis Schemas

### RateLimitCounter

Счетчик запросов для rate limiting (Fixed Window Counter).

```
Key Pattern: rate_limit:{user_id}
Type: String (counter)
TTL: 60 seconds (window)

Operations:
  INCR rate_limit:123    # Increment counter
  EXPIRE rate_limit:123 60  # Set TTL on first request
  GET rate_limit:123     # Check current count
  TTL rate_limit:123     # Get remaining window time
```

**Example**:
```redis
> INCR rate_limit:user_123
(integer) 1
> EXPIRE rate_limit:user_123 60
(integer) 1
> INCR rate_limit:user_123
(integer) 2
> TTL rate_limit:user_123
(integer) 58
```

---

### PriorityQueue

Очередь воспроизведения с приоритетами (Redis Sorted Set).

```
Key Pattern: queue:{chat_id}
Type: Sorted Set (ZSET)
Score: priority_value + (timestamp / 1e10)

Priority Values:
  high:   0
  normal: 50
  low:    100

Operations:
  ZADD queue:123 0.1234567890 "track_id_1"    # Add high priority
  ZADD queue:123 50.1234567891 "track_id_2"   # Add normal priority
  ZPOPMIN queue:123                            # Get next track
  ZRANGE queue:123 0 -1 WITHSCORES            # List all
  ZREM queue:123 "track_id_1"                  # Remove specific
```

**Example**:
```redis
> ZADD queue:chat_123 0.1705700000 "track_abc"
(integer) 1
> ZADD queue:chat_123 50.1705700001 "track_def"
(integer) 1
> ZPOPMIN queue:chat_123
1) "track_abc"
2) "0.1705700000"
```

---

## Entity Relationships

```
User (1) -----> (1) PlaybackSettings
  |
  +---> (N) ScheduledPlaylist

Playlist (1) -----> (N) ScheduledPlaylist

Track (N) <----> (1) LyricsCache (via artist+title)
```

---

## Migrations

### Migration 001: PlaybackSettings

```python
# alembic/versions/001_add_playback_settings.py

def upgrade():
    op.create_table(
        'playback_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), unique=True),
        sa.Column('speed', sa.Float(), default=1.0),
        sa.Column('pitch_correction', sa.Boolean(), default=True),
        sa.Column('equalizer_preset', sa.String(50), default='flat'),
        sa.Column('equalizer_custom', sa.JSON(), nullable=True),
        sa.Column('language', sa.String(5), default='ru'),
        sa.Column('show_lyrics', sa.Boolean(), default=True),
    )

def downgrade():
    op.drop_table('playback_settings')
```

### Migration 002: RadioStreams

```python
# alembic/versions/002_add_radio_streams.py

def upgrade():
    op.create_table(
        'radio_streams',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(1024), nullable=False, unique=True),
        sa.Column('genre', sa.String(100)),
        sa.Column('country', sa.String(100)),
        sa.Column('logo_url', sa.String(1024)),
        sa.Column('bitrate', sa.Integer()),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_checked', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=func.now()),
    )

def downgrade():
    op.drop_table('radio_streams')
```

### Migration 003: ScheduledPlaylists

```python
# alembic/versions/003_add_scheduled_playlists.py

def upgrade():
    op.create_table(
        'scheduled_playlists',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('playlist_id', sa.Integer(), sa.ForeignKey('playlists.id')),
        sa.Column('scheduled_time', sa.DateTime(), nullable=False),
        sa.Column('repeat_type', sa.Enum(RepeatType)),
        sa.Column('cron_expression', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_run', sa.DateTime()),
        sa.Column('next_run', sa.DateTime()),
        sa.Column('override_current', sa.Boolean(), default=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(), server_default=func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=func.now()),
    )

def downgrade():
    op.drop_table('scheduled_playlists')
```

### Migration 004: LyricsCache

```python
# alembic/versions/004_add_lyrics_cache.py

def upgrade():
    op.create_table(
        'lyrics_cache',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('artist', sa.String(255), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('lyrics', sa.Text()),
        sa.Column('synced_lyrics', sa.Text()),
        sa.Column('source', sa.String(50), default='genius'),
        sa.Column('source_url', sa.String(1024)),
        sa.Column('fetched_at', sa.DateTime(), server_default=func.now()),
        sa.Column('expires_at', sa.DateTime()),
    )
    op.create_index('idx_lyrics_artist_title', 'lyrics_cache', ['artist', 'title'], unique=True)

def downgrade():
    op.drop_index('idx_lyrics_artist_title')
    op.drop_table('lyrics_cache')
```

---

## Pydantic Schemas (API)

```python
# backend/src/schemas/playback.py

from pydantic import BaseModel, Field
from typing import Optional, List

class SpeedChangeRequest(BaseModel):
    speed: float = Field(ge=0.5, le=2.0, description="Playback speed multiplier")

class SeekRequest(BaseModel):
    seconds: int = Field(description="Seconds to seek (positive=forward, negative=backward)")

class EqualizerPresetRequest(BaseModel):
    preset: str = Field(description="Preset name: flat, rock, jazz, classical, voice, bass_boost")

class EqualizerCustomRequest(BaseModel):
    bands: List[int] = Field(min_items=10, max_items=10, description="10-band EQ values (-12 to 12)")

class PlaybackSettingsResponse(BaseModel):
    speed: float
    pitch_correction: bool
    equalizer_preset: str
    language: str
    
    class Config:
        from_attributes = True


# backend/src/schemas/radio.py

class RadioStreamCreate(BaseModel):
    name: str = Field(max_length=255)
    url: str = Field(max_length=1024, pattern=r'^https?://')
    genre: Optional[str] = None
    country: Optional[str] = None

class RadioStreamResponse(BaseModel):
    id: int
    name: str
    url: str
    genre: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True


# backend/src/schemas/lyrics.py

class LyricsResponse(BaseModel):
    artist: str
    title: str
    lyrics: Optional[str]
    synced: bool
    source: str
```

---

## Заключение

Модель данных спроектирована с учетом:
1. **Разделение ответственности**: PostgreSQL для персистентных данных, Redis для runtime состояния
2. **Масштабируемость**: Индексы, кэширование, TTL
3. **Валидация**: Constraints на уровне БД + Pydantic schemas
4. **Расширяемость**: JSON поля для custom настроек
