"""
LyricsService for fetching and caching song lyrics.

Features:
- Genius API integration for lyrics retrieval
- Database caching with 7-day TTL
- Automatic synchronization metadata support
- Fallback handling for missing lyrics

External API: Genius (lyricsgenius library)
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

try:
    import lyricsgenius
except ImportError:  # pragma: no cover - optional dependency
    lyricsgenius = None  # type: ignore[assignment]

from src.models import LyricsCache


logger = logging.getLogger(__name__)


class LyricsService:
    """Manages lyrics fetching and caching."""
    
    # Cache TTL in days
    CACHE_TTL_DAYS = 7
    
    def __init__(
        self,
        db_session: Session,
        genius_token: Optional[str] = None,
        genius_client: Optional[Any] = None,
    ) -> None:
        """Initialize lyrics service with optional Genius client override."""
        self.db = db_session
        self.logger = logger
        
        if genius_client is not None:
            self.genius = genius_client
        elif genius_token and lyricsgenius is not None:
            self.genius = lyricsgenius.Genius(
                genius_token,
                timeout=10,
                skip_non_songs=True,
            )
        else:
            self.genius = None
            self.logger.warning(
                "Genius API token not provided or lyricsgenius missing - lyrics service disabled"
            )

    @staticmethod
    def _now() -> datetime:
        """Return timezone-aware UTC timestamp."""
        return datetime.now(timezone.utc)

    @classmethod
    def _next_expiration(cls, now: Optional[datetime] = None) -> datetime:
        """Return expiration timestamp using configured TTL."""
        reference = now or cls._now()
        return reference + timedelta(days=LyricsService.CACHE_TTL_DAYS)
    
    def get_lyrics(self, artist: str, title: str) -> Optional[Dict]:
        """
        Get lyrics for song (from cache or API).
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Dict with lyrics and metadata, or None if not found
        """
        # Check cache first
        cached = self._get_from_cache(artist, title)
        if cached:
            return cached
        
        # Try to fetch from API
        if not self.genius:
            self.logger.warning(f"Genius API not available for {artist} - {title}")
            return None
        
        try:
            lyrics = self._fetch_from_genius(artist, title)
            if lyrics:
                return lyrics
        except Exception as e:
            self.logger.error(f"Error fetching lyrics: {e}")
        
        return None
    
    def _get_from_cache(self, artist: str, title: str) -> Optional[Dict]:
        """
        Get lyrics from database cache.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Dict with cached lyrics or None
        """
        cache_entry = self.db.query(LyricsCache).filter(
            LyricsCache.artist_name.ilike(artist),
            LyricsCache.track_title.ilike(title)
        ).first()
        
        if not cache_entry:
            return None
        
        # Check if expired
        if cache_entry.is_expired():
            self.db.delete(cache_entry)
            self.db.commit()
            return None
        
        # Update access info
        cache_entry.last_accessed = self._now()
        cache_entry.access_count += 1
        self.db.commit()
        
        self.logger.debug(f"Cache hit: {artist} - {title}")
        
        return {
            "lyrics": cache_entry.lyrics_text,
            "source": "cache",
            "source_api": cache_entry.source_api,
            "cached_at": cache_entry.fetched_at.isoformat(),
            "access_count": cache_entry.access_count
        }
    
    def _fetch_from_genius(self, artist: str, title: str) -> Optional[Dict]:
        """
        Fetch lyrics from Genius API.
        
        Args:
            artist: Artist name
            title: Song title
            
        Returns:
            Dict with lyrics or None if not found
        """
        try:
            song = self.genius.search_song(title, artist)
            
            if not song:
                self.logger.info(f"Song not found on Genius: {artist} - {title}")
                return None
            
            # Save to cache
            cache_entry = LyricsCache(
                track_title=title,
                artist_name=artist,
                external_id=str(song.url),
                lyrics_text=song.lyrics,
                lyrics_html=getattr(song, "html_lyrics", None),
                source_url=song.url,
                source_api="genius",
                expires_at=self._next_expiration(),
            )
        
            self.db.add(cache_entry)
            self.db.commit()
            
            self.logger.info(f"Cached lyrics from Genius: {artist} - {title}")
            
            return {
                "lyrics": song.lyrics,
                "source": "genius",
                "source_url": song.url,
                "source_api": "genius"
            }
            
        except Exception as e:
            self.logger.error(f"Genius API error for {artist} - {title}: {e}")
            return None
    
    def cache_lyrics(
        self,
        artist: str,
        title: str,
        lyrics_text: str,
        source_url: Optional[str] = None,
        source_api: str = "manual"
    ) -> LyricsCache:
        """
        Manually cache lyrics.
        
        Args:
            artist: Artist name
            title: Song title
            lyrics_text: Full lyrics text
            source_url: Optional source URL
            source_api: Source API name
            
        Returns:
            Created LyricsCache object
        """
        # Check if already cached
        existing = self.db.query(LyricsCache).filter(
            LyricsCache.artist_name.ilike(artist),
            LyricsCache.track_title.ilike(title)
        ).first()
        
        if existing:
            existing.lyrics_text = lyrics_text
            existing.source_url = source_url or existing.source_url
            existing.expires_at = self._next_expiration()
            self.db.commit()
            return existing
        
        cache_entry = LyricsCache(
            artist_name=artist,
            track_title=title,
            lyrics_text=lyrics_text,
            source_url=source_url,
            source_api=source_api,
            expires_at=self._next_expiration(),
        )
        
        self.db.add(cache_entry)
        self.db.commit()
        
        self.logger.info(f"Cached lyrics: {artist} - {title}")
        
        return cache_entry
    
    def cleanup_expired(self) -> int:
        """
        Remove expired cache entries.
        
        Returns:
            Number of entries removed
        """
        expired = self.db.query(LyricsCache).filter(
            LyricsCache.expires_at <= self._now()
        ).delete()
        
        self.db.commit()
        self.logger.info(f"Cleaned up {expired} expired lyrics entries")
        
        return expired
