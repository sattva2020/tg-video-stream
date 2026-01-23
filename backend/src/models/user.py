import uuid
from enum import Enum as PyEnum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, func, Boolean, text, Enum, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base, GUID
from src.lib.field_encryption import encrypt_field, decrypt_field


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
    _telegram_username_encrypted = Column("telegram_username", String(255), nullable=True)  # Encrypted PII

    # SAML/SSO
    saml_name_id = Column(String, unique=True, index=True, nullable=True)  # SAML NameID от IdP
    saml_config_id = Column(GUID(), ForeignKey("saml_configs.id", ondelete="SET NULL"), nullable=True)  # Ссылка на конфигурацию SAML

    # Common fields
    email = Column(String, unique=True, index=True, nullable=True)  # Nullable для Telegram-only пользователей
    _full_name_encrypted = Column("full_name", String, nullable=True)  # Encrypted PII
    profile_picture_url = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")
    # New for user approval workflow: 'pending' | 'approved' | 'rejected'
    status = Column(String, nullable=False, server_default="pending", default="pending")
    email_verified = Column(Boolean, default=False)
    # 2FA (TOTP)
    _totp_secret_encrypted = Column("totp_secret", String, nullable=True)  # Encrypted storage
    totp_enabled = Column(Boolean, nullable=False, server_default=text('false'), default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Metadata
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Properties for encrypted fields
    @property
    def totp_secret(self) -> str | None:
        """
        Get the decrypted TOTP secret.

        Returns:
            str | None: Decrypted TOTP secret or None
        """
        if self._totp_secret_encrypted is None:
            return None
        try:
            return decrypt_field(self._totp_secret_encrypted)
        except Exception:
            # If decryption fails, return as-is (might be legacy unencrypted data)
            return self._totp_secret_encrypted

    @totp_secret.setter
    def totp_secret(self, value: str | None) -> None:
        """
        Set the TOTP secret with automatic encryption.

        Args:
            value: Plain text TOTP secret to encrypt and store
        """
        if value is None:
            self._totp_secret_encrypted = None
        elif value == "":
            self._totp_secret_encrypted = ""
        else:
            self._totp_secret_encrypted = encrypt_field(value)

    @property
    def full_name(self) -> str | None:
        """
        Get the decrypted full name.

        Returns:
            str | None: Decrypted full name or None
        """
        if self._full_name_encrypted is None:
            return None
        try:
            return decrypt_field(self._full_name_encrypted)
        except Exception:
            # If decryption fails, return as-is (might be legacy unencrypted data)
            return self._full_name_encrypted

    @full_name.setter
    def full_name(self, value: str | None) -> None:
        """
        Set the full name with automatic encryption.

        Args:
            value: Plain text full name to encrypt and store
        """
        if value is None:
            self._full_name_encrypted = None
        elif value == "":
            self._full_name_encrypted = ""
        else:
            self._full_name_encrypted = encrypt_field(value)

    @property
    def telegram_username(self) -> str | None:
        """
        Get the decrypted Telegram username.

        Returns:
            str | None: Decrypted Telegram username or None
        """
        if self._telegram_username_encrypted is None:
            return None
        try:
            return decrypt_field(self._telegram_username_encrypted)
        except Exception:
            # If decryption fails, return as-is (might be legacy unencrypted data)
            return self._telegram_username_encrypted

    @telegram_username.setter
    def telegram_username(self, value: str | None) -> None:
        """
        Set the Telegram username with automatic encryption.

        Args:
            value: Plain text Telegram username to encrypt and store
        """
        if value is None:
            self._telegram_username_encrypted = None
        elif value == "":
            self._telegram_username_encrypted = ""
        else:
            self._telegram_username_encrypted = encrypt_field(value)


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
    # Phase 6: Clean Architecture - Stream ownership
    streams = relationship(
        "src.models.stream.Stream",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="select"
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

    def update_last_login(self) -> None:
        """Обновить время последнего успешного входа."""
        self.last_login = datetime.now(timezone.utc)
    
    @property
    def is_superuser(self) -> bool:
        """Проверяет, является ли пользователь суперадмином."""
        return self.role == UserRole.SUPERADMIN.value or self.role == "superadmin"
    
    @property
    def is_admin(self) -> bool:
        """Проверяет, является ли пользователь администратором."""
        return self.role in (UserRole.ADMIN.value, UserRole.SUPERADMIN.value, "admin", "superadmin")