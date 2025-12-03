"""
LyricsCache model for storing song lyrics.

Caches lyrics retrieved from external APIs (Genius):
- Lyrics text (synced with timing metadata if available)
- Track metadata for lookup
- TTL-based expiration (7 days)

Database: PostgreSQL (sqlalchemy ORM)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime, timedelta

from src.database import Base


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
    fetched_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    last_accessed = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<LyricsCache {self.artist_name} - {self.track_title}>"
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() > self.expires_at
