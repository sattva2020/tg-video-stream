"""
ScheduledPlaylist model for time-based playlist automation.

Stores scheduled playback configurations:
- Scheduled time (e.g., 08:00 daily)
- Associated playlist
- Admin-managed schedules

Database: PostgreSQL (sqlalchemy ORM)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from datetime import datetime

from src.database import Base


class ScheduledPlaylist(Base):
    """Scheduled playlist playback configuration."""
    
    __tablename__ = "scheduled_playlists"
    
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, nullable=False)  # Reference to existing playlist
    
    # Schedule timing
    schedule_time = Column(String(5), nullable=False)  # HH:MM format (e.g., "08:00")
    days_of_week = Column(JSON, default=lambda: list(range(7)))  # [0-6] = [Mon-Sun]
    timezone = Column(String(50), default="UTC")
    
    # Configuration
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, nullable=True)  # Admin user ID
    
    # Statistics
    last_triggered = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<ScheduledPlaylist id={self.id} time={self.schedule_time} playlist={self.playlist_id}>"
