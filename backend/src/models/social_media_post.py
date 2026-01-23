import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    ForeignKey,
    Index,
    BigInteger,
    func,
)
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class SocialMediaPost(Base):
    """Track auto-posted announcements to social media platforms"""

    __tablename__ = "social_media_posts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_id = Column(GUID(), ForeignKey("streaming_platforms.id", ondelete="CASCADE"), nullable=False, index=True)

    # Post details
    post_type = Column(String(50), nullable=False, default="stream_start")  # stream_start, stream_end, custom
    status = Column(String(32), nullable=False, default="pending")  # pending, posted, failed, cancelled
    content = Column(Text, nullable=True)  # The post content/message

    # Platform response
    platform_post_id = Column(String(255), nullable=True)  # ID of the post on the platform (e.g., tweet ID)
    platform_post_url = Column(String(512), nullable=True)  # URL to the post on the platform

    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(BigInteger, nullable=False, default=0)  # Number of retry attempts

    # Timestamps
    posted_at = Column(DateTime(timezone=True), nullable=True)  # When successfully posted
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    channel = relationship("Channel", backref="social_media_posts")
    platform = relationship("StreamingPlatform", backref="social_media_posts")

    __table_args__ = (
        Index("ix_social_media_posts_status", "status"),
        Index("ix_social_media_posts_channel_status", "channel_id", "status"),
    )
