"""
LyricsCache model for storing song lyrics.

Caches lyrics retrieved from external APIs (Genius):
- Lyrics text (synced with timing metadata if available)
- Track metadata for lookup
- TTL-based expiration (7 days)

Database: PostgreSQL (sqlalchemy ORM)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime, timedelta, timezone

from src.database import Base


def utcnow() -> datetime:
    """Return timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class LyricsCache(Base):
    """Cached lyrics from external sources (Genius API)."""
    
    __tablename__ = "lyrics_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Track identification
    track_title = Column(String(500), nullable=False, index=True)
    artist_name = Column(String(255), nullable=False, index=True)
    external_id = Column(String(255), nullable=True, unique=True)  # Genius ID or similar
    
    # Lyrics content
    lyrics_text = Column(Text, nullable=False)
    lyrics_html = Column(Text, nullable=True)  # Full HTML if available
    
    # Sync metadata (for timing)
    synced_lyrics = Column(Text, nullable=True)  # JSON with [time, line] pairs
    duration_ms = Column(Integer, nullable=True)
    
    # Source info
    source_url = Column(String(2048), nullable=True)
    source_api = Column(String(50), default="genius")  # API source name
    
    # Timestamps
    fetched_at = Column(DateTime(timezone=True), default=utcnow)
    expires_at = Column(DateTime(timezone=True), default=lambda: utcnow() + timedelta(days=7))
    last_accessed = Column(DateTime(timezone=True), default=utcnow)
    access_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<LyricsCache {self.artist_name} - {self.track_title}>"
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        expires_at = self.expires_at
        if expires_at is None:
            return True
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return utcnow() > expires_at
