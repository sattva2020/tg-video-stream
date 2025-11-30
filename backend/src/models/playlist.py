import uuid
from sqlalchemy import Column, String, DateTime, func, Integer, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base, GUID

class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    channel_id = Column(GUID(), ForeignKey("channels.id"), nullable=True)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    type = Column(String, default="youtube") # youtube, local, stream
    # NEW: playback status (playing, queued, error)
    status = Column(String, default="queued")
    # NEW: duration in seconds, NULL if unknown
    duration = Column(Integer, nullable=True)
    position = Column(Integer, default=0)
    created_by = Column(GUID(), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("src.models.user.User")
    channel = relationship("src.models.telegram.Channel", backref="playlist_items")

    def __repr__(self):
        return f"<PlaylistItem(url='{self.url}')>"
