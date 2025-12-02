"""
PlaybackSettings model for audio streaming enhancements.

Stores user-specific playback preferences:
- Speed/pitch control (0.5x - 2.0x)
- Equalizer presets and custom settings
- UI preferences (language, theme)
- Multi-channel support

Database: PostgreSQL (sqlalchemy ORM)
"""

from sqlalchemy import Column, Integer, Float, String, Boolean, JSON, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from src.database import Base, GUID


def _utcnow() -> datetime:
    """Return timezone-aware UTC timestamps for SQLAlchemy defaults."""

    return datetime.now(timezone.utc)


class PlaybackSettings(Base):
    """User playback preferences and settings."""
    
    __tablename__ = "playback_settings"
    
    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_playback_user_channel"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    channel_id = Column(Integer, nullable=True)  # For multi-channel support (US11)
    
    # Speed/Pitch Control (US1)
    speed = Column(Float, default=1.0)  # Range: 0.5 - 2.0
    pitch_correction = Column(Boolean, default=True)  # Auto-correct pitch with speed changes
    
    # Equalizer (US6)
    equalizer_preset = Column(String(50), default="flat")  # flat, rock, jazz, pop, etc.
    equalizer_custom = Column(JSON, nullable=True)  # [dB, dB, dB, dB, dB, dB, dB, dB, dB, dB]
    
    # UI Preferences
    language = Column(String(5), default="ru")  # ru, en, uk, es
    theme = Column(String(20), default="light")  # light, dark
    
    # Playback Preferences
    auto_play = Column(Boolean, default=True)  # Auto-play next track
    shuffle = Column(Boolean, default=False)
    repeat_mode = Column(String(10), default="off")  # off, one, all
    
    # Timestamps
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    user = relationship("User", back_populates="playback_settings")
    
    def __repr__(self):
        return f"<PlaybackSettings user_id={self.user_id} speed={self.speed}x eq={self.equalizer_preset}>"
