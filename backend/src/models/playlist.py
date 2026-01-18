import uuid
from sqlalchemy import Column, String, DateTime, func, Integer, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from src.database import Base, GUID

class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    channel_id = Column(GUID(), ForeignKey("channels.id"), nullable=True, index=True)
    # Phase 6: Clean Architecture - Stream FK for new architecture
    stream_id = Column(GUID(), ForeignKey("streams.id"), nullable=True, index=True, comment="FK to streams table (Clean Architecture)")
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    type = Column(String, default="youtube") # youtube, local, stream
    # NEW: playback status (playing, queued, error)
    status = Column(String, default="queued")
    # NEW: duration in seconds, NULL if unknown
    duration = Column(BigInteger, nullable=True)
    position = Column(BigInteger, default=0)
    created_by = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("src.models.user.User")
    channel = relationship("src.models.telegram.Channel", backref="playlist_items")
    # Phase 6: Clean Architecture - Stream relationship
    stream = relationship("src.models.stream.Stream", back_populates="playlists", lazy="joined")

    def __repr__(self):
        return f"<PlaylistItem(url='{self.url}')>"
