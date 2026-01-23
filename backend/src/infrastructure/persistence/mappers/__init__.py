"""
Mappers для преобразования Entity ↔ ORM (T053-T055).

**Architecture Layer**: Infrastructure / Persistence
**Purpose**: Изоляция Domain Layer от ORM моделей

Mappers реализуют Mapper Pattern для конвертации между:
- Domain Entities (чистый Python, без SQLAlchemy)
- ORM Models (SQLAlchemy declarative models)

**Available Mappers**:
- UserMapper: User Entity ↔ User ORM
- StreamMapper: Stream Entity ↔ Stream ORM (T054)
- PlaylistMapper: Playlist Entity ↔ Playlist ORM (T055)
- PollMapper: Poll Entity ↔ Poll ORM (T020)
- QuestionMapper: Question Entity ↔ Question ORM (T020)
- InteractionMapper: Reaction Entity ↔ EmojiReaction ORM (T020)

**Usage**:
```python
from src.infrastructure.persistence.mappers import UserMapper

# ORM → Entity
user_entity = UserMapper.to_entity(orm_user)

# Entity → ORM
orm_user = UserMapper.to_orm(user_entity)
```
"""

from src.infrastructure.persistence.mappers.user_mapper import UserMapper
from src.infrastructure.persistence.mappers.stream_mapper import StreamMapper
from src.infrastructure.persistence.mappers.playlist_mapper import PlaylistMapper
from src.infrastructure.persistence.mappers.poll_mapper import PollMapper
from src.infrastructure.persistence.mappers.question_mapper import QuestionMapper
from src.infrastructure.persistence.mappers.interaction_mapper import InteractionMapper

__all__ = [
    "UserMapper",
    "StreamMapper",
    "PlaylistMapper",
    "PollMapper",
    "QuestionMapper",
    "InteractionMapper",
]
