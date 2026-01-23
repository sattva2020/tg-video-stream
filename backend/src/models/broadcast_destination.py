import uuid
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from src.database import Base, GUID

class BroadcastDestination(Base):
    __tablename__ = "broadcast_destinations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    channel_id = Column(GUID(), ForeignKey("channels.id"), nullable=False, index=True)
    platform_id = Column(GUID(), ForeignKey("streaming_platforms.id"), nullable=False, index=True)

    # Platform-specific settings stored as JSON string
    platform_settings = Column(Text, nullable=True)

    # Destination-specific configuration
    enabled = Column(Boolean, default=True)  # Whether this destination is active
    status = Column(String, default="idle")  # idle, streaming, error
    last_error = Column(String, nullable=True)  # Last error message if any

    # Optional custom title/description for this specific destination
    custom_title = Column(String, nullable=True)
    custom_description = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    channel = relationship("Channel", backref="broadcast_destinations")
    platform = relationship("StreamingPlatform", backref="broadcast_destinations")
