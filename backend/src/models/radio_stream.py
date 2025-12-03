"""
RadioStream model for internet radio stream management.

Stores radio stream information:
- Stream URL (HTTP/HTTPS)
- Stream metadata (name, description, genre)
- Admin-configured streams

Database: PostgreSQL (sqlalchemy ORM)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from src.database import Base


class RadioStream(Base):
    """Internet radio stream configuration."""
    
    __tablename__ = "radio_streams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)  # Display name
    url = Column(String(2048), nullable=False, unique=True)  # HTTP/HTTPS stream URL
    description = Column(String(1000), nullable=True)  # Optional description
    genre = Column(String(100), nullable=True)  # Genre classification
    
    is_active = Column(Boolean, default=True)  # Enable/disable without deleting
    added_by = Column(Integer, nullable=True)  # Admin user ID who added stream
    
    # Statistics
    play_count = Column(Integer, default=0)
    last_played = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<RadioStream id={self.id} name={self.name} url={self.url[:50]}...>"
