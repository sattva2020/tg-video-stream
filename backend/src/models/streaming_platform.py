import uuid
from sqlalchemy import Column, String, DateTime, func, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.database import Base, GUID

class StreamingPlatform(Base):
    __tablename__ = "streaming_platforms"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    platform_type = Column(String, nullable=False)  # youtube, twitch, twitter, discord, custom_rtmp
    platform_name = Column(String, nullable=False)  # User-defined name for the platform
    encrypted_credentials = Column(Text, nullable=True)  # Encrypted API keys, tokens, etc.
    stream_key = Column(String, nullable=True)  # Stream key for the platform
    stream_url = Column(String, nullable=True)  # RTMP URL or custom stream URL
    status = Column(String, default="inactive")  # inactive, active, error
    last_error = Column(String, nullable=True)  # Last error message if any

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("src.models.user.User", backref="streaming_platforms")
