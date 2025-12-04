"""
RadioService for internet radio stream management.

Features:
- Add/remove radio streams
- URL validation
- Stream metadata management
- Stream reconnection on network failures
"""

import logging
from typing import List, Optional
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from src.models import RadioStream


logger = logging.getLogger(__name__)


class RadioService:
    """Manages internet radio streams."""
    
    def __init__(self, db_session: Session):
        """Initialize radio service."""
        self.db = db_session
        self.logger = logger
    
    def validate_url(self, url: str) -> bool:
        """
        Validate radio stream URL format.
        
        Args:
            url: Stream URL to validate
            
        Returns:
            True if URL is valid HTTP/HTTPS stream
            
        Raises:
            ValueError: If URL format is invalid
        """
        try:
            parsed = urlparse(url)
            
            # Check protocol
            if parsed.scheme not in ["http", "https"]:
                raise ValueError(f"Invalid protocol: {parsed.scheme} (must be http or https)")
            
            # Check for netloc
            if not parsed.netloc:
                raise ValueError("URL must contain host")
            
            return True
            
        except Exception as e:
            raise ValueError(f"URL validation failed: {e}")
    
    def add_stream(
        self,
        name: str,
        url: str,
        description: Optional[str] = None,
        genre: Optional[str] = None,
        added_by: Optional[int] = None
    ) -> RadioStream:
        """
        Add new radio stream.
        
        Args:
            name: Display name for stream
            url: HTTP/HTTPS stream URL
            description: Optional description
            genre: Optional genre classification
            added_by: Admin user ID who added stream
            
        Returns:
            Created RadioStream object
            
        Raises:
            ValueError: If URL is invalid or stream already exists
        """
        # Validate URL
        self.validate_url(url)
        
        # Check for duplicates
        existing = self.db.query(RadioStream).filter(RadioStream.url == url).first()
        if existing:
            raise ValueError(f"Stream already exists: {url}")
        
        # Create stream
        stream = RadioStream(
            name=name,
            url=url,
            description=description,
            genre=genre,
            added_by=added_by,
            is_active=True
        )
        
        self.db.add(stream)
        self.db.commit()
        
        self.logger.info(f"Radio stream added: {name} ({url})")
        
        return stream
    
    def get_stream(self, stream_id: int) -> Optional[RadioStream]:
        """
        Get radio stream by ID.
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            RadioStream object or None if not found
        """
        return self.db.query(RadioStream).filter(RadioStream.id == stream_id).first()
    
    def get_all_streams(self, active_only: bool = True) -> List[RadioStream]:
        """
        Get all radio streams.
        
        Args:
            active_only: If True, return only active streams
            
        Returns:
            List of RadioStream objects
        """
        query = self.db.query(RadioStream)
        
        if active_only:
            query = query.filter(RadioStream.is_active == True)
        
        return query.order_by(RadioStream.name).all()
    
    def remove_stream(self, stream_id: int) -> bool:
        """
        Remove radio stream (soft delete by marking inactive).
        
        Args:
            stream_id: Stream identifier
            
        Returns:
            True if stream was found and removed
        """
        stream = self.get_stream(stream_id)
        
        if not stream:
            return False
        
        stream.is_active = False
        self.db.commit()
        
        self.logger.info(f"Radio stream deactivated: {stream.name}")
        
        return True
    
    def update_play_count(self, stream_id: int) -> None:
        """
        Increment play count for stream.
        
        Args:
            stream_id: Stream identifier
        """
        stream = self.get_stream(stream_id)
        if stream:
            stream.play_count += 1
            self.db.commit()
            self.logger.debug(f"Stream play count: {stream.name} → {stream.play_count}")
    
    def search_streams(self, query: str) -> List[RadioStream]:
        """
        Search streams by name or genre.
        
        Args:
            query: Search query
            
        Returns:
            List of matching RadioStream objects
        """
        return self.db.query(RadioStream).filter(
            (RadioStream.name.ilike(f"%{query}%")) |
            (RadioStream.genre.ilike(f"%{query}%")) |
            (RadioStream.description.ilike(f"%{query}%"))
        ).filter(RadioStream.is_active == True).all()
