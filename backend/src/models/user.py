import uuid
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, func, Boolean, text, Enum, BigInteger
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class UserRole(str, PyEnum):
    """Роли пользователей."""
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class UserStatus(str, PyEnum):
    """Статусы пользователей."""
    PENDING = "pending"
    ACTIVE = "active"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # OAuth providers
    google_id = Column(String, unique=True, index=True, nullable=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)  # Telegram Login Widget
    telegram_username = Column(String(255), nullable=True)  # Username в Telegram (без @)
    
    # Common fields
    email = Column(String, unique=True, index=True, nullable=True)  # Nullable для Telegram-only пользователей
    full_name = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")
    # New for user approval workflow: 'pending' | 'approved' | 'rejected'
    status = Column(String, nullable=False, server_default="pending", default="pending")
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    audit_logs = relationship(
        "AdminAuditLog",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    playback_settings = relationship(
        "PlaybackSettings",
        back_populates="user",
        uselist=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(email='{self.email}', telegram_id={self.telegram_id})>"
    
    def has_alternative_auth(self) -> bool:
        """
        Проверяет, есть ли у пользователя альтернативный способ входа.
        Используется для разрешения отвязки Telegram.
        """
        has_google = bool(self.google_id)
        has_email_password = bool(self.email and self.hashed_password)
        return has_google or has_email_password
    
    @property
    def is_superuser(self) -> bool:
        """Проверяет, является ли пользователь суперадмином."""
        return self.role == UserRole.SUPERADMIN.value or self.role == "superadmin"
    
    @property
    def is_admin(self) -> bool:
        """Проверяет, является ли пользователь администратором."""
        return self.role in (UserRole.ADMIN.value, UserRole.SUPERADMIN.value, "admin", "superadmin")