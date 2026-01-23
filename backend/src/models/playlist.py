import uuid
from sqlalchemy import Column, String, DateTime, func, Integer, ForeignKey, BigInteger, Boolean, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class JSONBCompat(TypeDecorator):
    """Use JSONB on PostgreSQL and JSON elsewhere for test compatibility."""

    impl = JSONB
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON())

class PlaylistItem(Base):
    __tablename__ = "playlist_items"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    channel_id = Column(GUID(), ForeignKey("channels.id"), nullable=True, index=True)
    # Phase 6: Clean Architecture - Stream FK for new architecture
    stream_id = Column(GUID(), ForeignKey("streams.id"), nullable=True, index=True, comment="FK to streams table (Clean Architecture)")
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    type = Column(String, default="youtube")  # youtube, vimeo, dailymotion, twitch, direct, hls, dash, cloud_drive, dropbox, onedrive, rss, local, stream
    # NEW: playback status (playing, queued, error)
    status = Column(String, default="queued")
    # NEW: duration in seconds, NULL if unknown
    duration = Column(BigInteger, nullable=True)
    # Multi-platform video source integration fields
    thumbnail_url = Column(String, nullable=True, comment="URL to video thumbnail image")
    source_metadata = Column(JSONBCompat, nullable=True, comment="Platform-specific metadata (video IDs, channel info, etc.)")
    is_live = Column(Boolean, default=False, comment="Whether this is a live stream (HLS/DASH)")
    requires_auth = Column(Boolean, default=False, comment="Whether authentication is needed for cloud storage")
    auth_token = Column(String, nullable=True, comment="Encrypted token for cloud storage access")
    quality = Column(String, nullable=True, comment="Preferred video quality (e.g., '1080p', '720p')")
    position = Column(BigInteger, default=0)
    created_by = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("src.models.user.User")
    channel = relationship("src.models.telegram.Channel", backref="playlist_items")
    # Phase 6: Clean Architecture - Stream relationship
    stream = relationship("src.models.stream.Stream", back_populates="playlists", lazy="joined")

    def __repr__(self):
        return f"<PlaylistItem(url='{self.url}')>"
