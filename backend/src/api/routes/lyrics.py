"""
API routes for lyrics retrieval and caching.

Endpoints:
  GET /api/v1/lyrics/{track_id} - Get lyrics for a track (cached, 7-day TTL)
  GET /api/v1/lyrics/search - Search for lyrics by artist and song
  GET /api/v1/lyrics/cache-status - Get cache statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from pydantic import BaseModel, Field
from typing import Optional
import logging
from datetime import datetime

from ..dependencies import get_current_user
from ...services.lyrics_service import LyricsService
from ...models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/lyrics", tags=["lyrics"])


# Request/Response Models
class SearchLyricsRequest(BaseModel):
    """Request to search for lyrics."""
    artist: str = Field(min_length=1, max_length=200, description="Artist name")
    song: str = Field(min_length=1, max_length=200, description="Song title")


class LyricsResponse(BaseModel):
    """Response with lyrics data."""
    track_id: str
    artist: str
    title: str
    lyrics: str
    source_url: Optional[str] = None
    cached: bool = False
    expires_at: Optional[str] = None


class LyricsCacheStatusResponse(BaseModel):
    """Response with cache statistics."""
    total_cached: int
    expired_count: int
    active_count: int
    oldest_entry: Optional[str]
    newest_entry: Optional[str]
    avg_ttl_days: float


class LyricsSearchResponse(BaseModel):
    """Response with search results."""
    found: bool
    artist: str
    title: str
    lyrics: Optional[str] = None
    source_url: Optional[str] = None
    message: Optional[str] = None


# Route Handlers

@router.get("/{track_id}", response_model=LyricsResponse, status_code=200)
async def get_lyrics(
    track_id: str = Path(description="Track ID (e.g., 'spotify:track:...' or 'artist-song')"),
    current_user: User = Depends(get_current_user),
    lyrics_service: LyricsService = Depends(lambda: LyricsService())
):
    """
    Get lyrics for a specific track.
    
    **Caching**: Results cached for 7 days to reduce Genius API calls
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    
    **Example**:
    - `GET /api/v1/lyrics/the-weeknd-blinding-lights`
    - Returns cached result or fetches from Genius API if not cached
    """
    try:
        # Check cache first
        cached_lyrics = await lyrics_service.get_cached_lyrics(track_id=track_id)
        
        if cached_lyrics:
            logger.info(f"User {current_user.id} retrieved cached lyrics for track {track_id}")
            return LyricsResponse(
                track_id=track_id,
                artist=cached_lyrics.get("artist"),
                title=cached_lyrics.get("title"),
                lyrics=cached_lyrics.get("lyrics"),
                source_url=cached_lyrics.get("source_url"),
                cached=True,
                expires_at=cached_lyrics.get("expires_at")
            )
        
        # Fetch from Genius API
        lyrics_data = await lyrics_service.get_lyrics(track_id=track_id)
        
        if not lyrics_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lyrics not found for this track"
            )
        
        # Cache the result
        await lyrics_service.cache_lyrics(
            track_id=track_id,
            artist=lyrics_data.get("artist"),
            title=lyrics_data.get("title"),
            lyrics=lyrics_data.get("lyrics"),
            source_url=lyrics_data.get("source_url")
        )
        
        logger.info(f"User {current_user.id} fetched new lyrics for track {track_id}")
        
        return LyricsResponse(
            track_id=track_id,
            artist=lyrics_data.get("artist"),
            title=lyrics_data.get("title"),
            lyrics=lyrics_data.get("lyrics"),
            source_url=lyrics_data.get("source_url"),
            cached=False
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving lyrics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve lyrics")


@router.get("/search", response_model=LyricsSearchResponse, status_code=200)
async def search_lyrics(
    artist: str = Query(min_length=1, max_length=200, description="Artist name"),
    song: str = Query(min_length=1, max_length=200, description="Song title"),
    current_user: User = Depends(get_current_user),
    lyrics_service: LyricsService = Depends(lambda: LyricsService())
):
    """
    Search for lyrics by artist and song title.
    
    **Caching**: Results cached for 7 days
    
    **Permission**: Authenticated user only
    
    **Rate Limit**: 100 requests/minute per user (Standard)
    
    **Query Parameters**:
    - `artist`: Artist name (required)
    - `song`: Song title (required)
    
    **Example**:
    - `GET /api/v1/lyrics/search?artist=The+Weeknd&song=Blinding+Lights`
    """
    try:
        track_id = f"{artist.lower()}-{song.lower()}".replace(" ", "-")
        
        # Check cache first
        cached = await lyrics_service.get_cached_lyrics(track_id=track_id)
        if cached:
            return LyricsSearchResponse(
                found=True,
                artist=cached.get("artist"),
                title=cached.get("title"),
                lyrics=cached.get("lyrics"),
                source_url=cached.get("source_url")
            )
        
        # Search Genius API
        result = await lyrics_service.search_lyrics(artist=artist, song=song)
        
        if result:
            # Cache the result
            await lyrics_service.cache_lyrics(
                track_id=track_id,
                artist=result.get("artist"),
                title=result.get("title"),
                lyrics=result.get("lyrics"),
                source_url=result.get("source_url")
            )
            
            logger.info(f"User {current_user.id} found lyrics for {artist} - {song}")
            
            return LyricsSearchResponse(
                found=True,
                artist=result.get("artist"),
                title=result.get("title"),
                lyrics=result.get("lyrics"),
                source_url=result.get("source_url")
            )
        else:
            logger.info(f"User {current_user.id} searched but no lyrics found for {artist} - {song}")
            
            return LyricsSearchResponse(
                found=False,
                artist=artist,
                title=song,
                message="No lyrics found for this track"
            )
    except Exception as e:
        logger.error(f"Error searching lyrics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to search lyrics")


@router.get("/cache/status", response_model=LyricsCacheStatusResponse, status_code=200)
async def get_cache_status(
    current_user: User = Depends(get_current_user),
    lyrics_service: LyricsService = Depends(lambda: LyricsService())
):
    """
    Get cache statistics (admin-only in production).
    
    **Permission**: Authenticated user (should be admin-only)
    
    **Rate Limit**: 50 requests/minute per user (Standard)
    
    **Returns**:
    - `total_cached`: Total number of cached entries
    - `expired_count`: Number of expired entries
    - `active_count`: Number of active (not expired) entries
    - `oldest_entry`: Oldest cache entry date
    - `newest_entry`: Newest cache entry date
    - `avg_ttl_days`: Average time-to-live in days
    """
    try:
        stats = await lyrics_service.get_cache_stats()
        
        logger.info(f"User {current_user.id} requested cache statistics")
        
        return LyricsCacheStatusResponse(
            total_cached=stats.get("total", 0),
            expired_count=stats.get("expired", 0),
            active_count=stats.get("active", 0),
            oldest_entry=stats.get("oldest_entry"),
            newest_entry=stats.get("newest_entry"),
            avg_ttl_days=stats.get("avg_ttl_days", 7.0)
        )
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get cache status")
