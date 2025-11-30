"""
Activity Event Model
Spec: 015-real-system-monitoring

Модель для хранения событий активности системы.
Используется для отображения в ActivityTimeline на Dashboard.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from src.database import Base


class ActivityEvent(Base):
    """
    Событие активности системы.
    
    Хранит информацию о действиях пользователей и системных событиях
    для отображения в ленте активности на Dashboard.
    
    Типы событий:
    - user_login, user_logout — авторизация
    - stream_start, stream_stop, stream_error — стриминг
    - track_added, track_removed — плейлист
    - playlist_updated — обновление плейлиста
    - system_warning, system_error — системные события
    """
    
    __tablename__ = "activity_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    user_email = Column(String(255), nullable=True)
    details = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False,
        index=True
    )

    # Составные индексы для эффективных запросов
    __table_args__ = (
        Index('idx_activity_events_type_created', 'type', 'created_at'),
    )

    def __repr__(self):
        return f"<ActivityEvent(id={self.id}, type='{self.type}', created_at={self.created_at})>"

    def to_dict(self) -> dict:
        """Преобразует модель в словарь для сериализации."""
        return {
            "id": self.id,
            "type": self.type,
            "message": self.message,
            "user_email": self.user_email,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
