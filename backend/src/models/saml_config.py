"""
SAML Configuration Model
Spec: 025-advanced-security-compliance-features

Модель для хранения конфигураций SAML/SSO интеграций.
Поддерживает несколько Identity Provider (Okta, Azure AD, Google Workspace).
"""

import uuid
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, func, Boolean, text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator
from src.database import Base, GUID


class JSONBCompat(TypeDecorator):
    """Use JSONB on PostgreSQL and JSON elsewhere for test compatibility."""

    impl = JSONB
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON())


class SAMLConfig(Base):
    """Конфигурация SAML Identity Provider для SSO аутентификации."""

    __tablename__ = "saml_configs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Basic configuration
    name = Column(String(255), nullable=False)  # Название конфигурации (например "Okta Production")
    enabled = Column(Boolean, nullable=False, server_default=text('false'), default=False)

    # Identity Provider (IdP) settings
    idp_entity_id = Column(String(500), nullable=False)  # Entity ID из SAML метаданных IdP
    idp_sso_url = Column(String(500), nullable=False)  # IdP Single Sign-On URL
    idp_x509_cert = Column(String, nullable=False)  # X.509 сертификат IdP для проверки подписи
    idp_slo_url = Column(String(500), nullable=True)  # Опциональный IdP Single Logout URL
    idp_metadata_url = Column(String(500), nullable=True)  # Опциональный URL метаданных IdP

    # Service Provider (SP) settings
    sp_entity_id = Column(String(500), nullable=False)  # Наш Entity ID (обычно URL приложения)
    sp_acs_url = Column(String(500), nullable=False)  # Assertion Consumer Service URL
    sp_slo_url = Column(String(500), nullable=True)  # Optional Single Logout URL

    # Security settings
    name_id_format = Column(String(255), nullable=True, default="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified")
    security_config = Column(JSONBCompat, nullable=True)  # {"assertion_encrypted": true, "sign_assertion": false}

    # User provisioning and role mapping
    attribute_mapping = Column(JSONBCompat, nullable=True)  # Mapping SAML attributes to user fields
    # Example: {"email": "email", "full_name": "firstName + ' ' + lastName", "role": "groups"}
    role_mapping = Column(JSONBCompat, nullable=True)  # Map IdP groups/roles to app roles
    # Example: {"Admin": ["admin", "superadmin"], "User": ["user"]}

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SAMLConfig(id='{self.id}', name='{self.name}', enabled={self.enabled})>"

    def is_active(self) -> bool:
        """Проверяет, активна ли конфигурация SAML."""
        return self.enabled

    def get_idp_cert(self) -> str:
        """
        Возвращает сертификат IdP в чистом формате (без пробелов и переносов).
        Используется для инициализации SAML библиотеки.
        """
        if not self.idp_x509_cert:
            return ""
        # Remove whitespace and newlines
        return self.idp_x509_cert.replace("\n", "").replace("\r", "").replace(" ", "")

    def get_name_id_format(self) -> str:
        """Возвращает формат NameID или дефолтное значение."""
        return self.name_id_format or "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"

    def get_attribute_mapping(self) -> dict:
        """Возвращает маппинг атрибутов или дефолтные значения."""
        default_mapping = {
            "email": "email",
            "full_name": "displayName",
            "role": "groups"
        }
        return self.attribute_mapping or default_mapping

    def get_security_config(self) -> dict:
        """Возвращает настройки безопасности или дефолтные значения."""
        default_security = {
            "assertion_encrypted": False,
            "sign_assertion": True,
            "sign_metadata": False
        }
        if self.security_config:
            default_security.update(self.security_config)
        return default_security
