import uuid
from sqlalchemy import Column, String, DateTime, func, ForeignKey, BigInteger, Boolean, Integer
from sqlalchemy.orm import relationship
from src.database import Base, GUID

class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    phone = Column(String, nullable=False)
    encrypted_session = Column(String, nullable=False)
    tg_user_id = Column(BigInteger, nullable=True) # Telegram User ID (64-bit)
    first_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)

    # Session health fields
    session_health_status = Column(String, nullable=True)  # healthy, expiring, expired, needs_2fa, error
    last_health_check = Column(DateTime(timezone=True), nullable=True)
    session_expires_at = Column(DateTime(timezone=True), nullable=True)
    totp_secret = Column(String, nullable=True)  # Encrypted TOTP secret for 2FA
    auto_refresh_enabled = Column(Boolean, default=True, nullable=False)
    refresh_before_expires_hours = Column(Integer, default=24, nullable=False)
    last_refreshed_at = Column(DateTime(timezone=True), nullable=True)
    refresh_error_message = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("src.models.user.User", backref="telegram_accounts")

class Channel(Base):
    __tablename__ = "channels"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    account_id = Column(GUID(), ForeignKey("telegram_accounts.id"), nullable=False, index=True)
    chat_id = Column(BigInteger, nullable=False) # Telegram Chat ID (64-bit)
    chat_username = Column(String, nullable=True)  # Telegram chat username for peer resolution
    name = Column(String, nullable=False)
    status = Column(String, default="stopped") # stopped, running, error
    error_message = Column(String, nullable=True) # Last error message
    
    # Configuration specific to this channel
    ffmpeg_args = Column(String, nullable=True)
    video_quality = Column(String, default="best")
    stream_type = Column(String, default="video") # video, audio
    placeholder_image = Column(String, nullable=True) # Path to custom placeholder image
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    account = relationship("TelegramAccount", backref="channels")
