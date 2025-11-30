import uuid
from sqlalchemy import Column, String, DateTime, func, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from src.database import Base, GUID

class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    phone = Column(String, nullable=False)
    encrypted_session = Column(String, nullable=False)
    tg_user_id = Column(BigInteger, nullable=True) # Telegram User ID (64-bit)
    first_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("src.models.user.User", backref="telegram_accounts")

class Channel(Base):
    __tablename__ = "channels"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    account_id = Column(GUID(), ForeignKey("telegram_accounts.id"), nullable=False)
    chat_id = Column(BigInteger, nullable=False) # Telegram Chat ID (64-bit)
    name = Column(String, nullable=False)
    status = Column(String, default="stopped") # stopped, running, error
    
    # Configuration specific to this channel
    ffmpeg_args = Column(String, nullable=True)
    video_quality = Column(String, default="best")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    account = relationship("TelegramAccount", backref="channels")
