"""
Security Policy Model
Spec: 025-advanced-security-compliance-features

Модель для хранения политик безопасности, включая правила принудительного использования 2FA.
Поддерживает различные типы политик безопасности для enterprise требований.
"""

import uuid
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, func, Boolean, text, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class JSONBCompat(TypeDecorator):
    """Use JSONB on PostgreSQL and JSON elsewhere for test compatibility."""

    impl = JSONB
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class PolicyType(str, PyEnum):
    """Типы политик безопасности."""
    TWO_FACTOR_ENFORCEMENT = "2fa_enforcement"
    PASSWORD_COMPLEXITY = "password_complexity"
    SESSION_TIMEOUT = "session_timeout"
    IP_RESTRICTION = "ip_restriction"


class EnforcementLevel(str, PyEnum):
    """Уровни принудительного применения политик."""
    OPTIONAL = "optional"  # Policy is recommended but not enforced
    MANDATORY = "mandatory"  # Policy must be followed, blocks access if not
    AUDIT_ONLY = "audit_only"  # Policy violations are logged but not enforced


class SecurityPolicy(Base):
    """Политика безопасности для управления правилами доступа и аутентификации.

    Поддерживает различные типы политик, включая:
    - Принудительное использование 2FA для определенных ролей
    - Требования к сложности паролей
    - Таймауты сессий
    - IP-ограничения
    """

    __tablename__ = "security_policies"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # Basic configuration
    name = Column(String(255), nullable=False)  # Название политики (например "2FA для администраторов")
    policy_type = Column(String(50), nullable=False, default=PolicyType.TWO_FACTOR_ENFORCEMENT.value)
    enabled = Column(Boolean, nullable=False, server_default=text('false'), default=False)

    # Enforcement settings
    enforcement_level = Column(String(50), nullable=False, default=EnforcementLevel.OPTIONAL.value)
    # Which roles this policy applies to (NULL = all roles)
    # Example: ["admin", "superadmin"] or [] for all roles
    affected_roles = Column(JSONBCompat, nullable=True)

    # 2FA-specific settings
    # Grace period in hours before 2FA requirement is enforced (e.g., 24 hours)
    grace_period_hours = Column(Integer, nullable=True, default=0)
    # Whether to exempt users who have alternative auth methods (e.g., SAML)
    allow_exempt_alternative_auth = Column(Boolean, nullable=False, server_default=text('false'), default=False)

    # Additional policy-specific configuration (flexible schema for different policy types)
    # Example: {"max_password_age_days": 90, "min_password_length": 12}
    policy_config = Column(JSONBCompat, nullable=True)

    # Description of the policy purpose
    description = Column(String(1000), nullable=True)

    # Track who created/modified this policy (for audit purposes)
    created_by_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    created_by = relationship("User", foreign_keys=[created_by_id], backref="created_policies")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<SecurityPolicy(id='{self.id}', name='{self.name}', type='{self.policy_type}', enabled={self.enabled})>"

    def is_active(self) -> bool:
        """Проверяет, активна ли политика безопасности."""
        return self.enabled

    def applies_to_role(self, role: str) -> bool:
        """
        Проверяет, применяется ли политика к указанной роли.

        Args:
            role: Роль пользователя (например "admin", "user")

        Returns:
            bool: True если политика применяется к роли, False если нет
        """
        if not self.affected_roles:
            # Если список ролей не указан, политика применяется ко всем ролям
            return True
        return role in self.affected_roles

    def is_mandatory(self) -> bool:
        """Проверяет, является ли политика обязательной."""
        return self.enforcement_level == EnforcementLevel.MANDATORY.value

    def is_optional(self) -> bool:
        """Проверяет, является ли политика опциональной."""
        return self.enforcement_level == EnforcementLevel.OPTIONAL.value

    def is_audit_only(self) -> bool:
        """Проверяет, работает ли политика в режиме только для аудита."""
        return self.enforcement_level == EnforcementLevel.AUDIT_ONLY.value

    def get_grace_period_seconds(self) -> int:
        """
        Возвращает период ожидания в секундах.

        Returns:
            int: Период ожидания в секундах
        """
        hours = self.grace_period_hours or 0
        return hours * 3600

    def get_policy_config(self) -> dict:
        """Возвращает конфигурацию политики или дефолтные значения."""
        default_config = {}
        if self.policy_config:
            default_config.update(self.policy_config)
        return default_config

    def get_affected_roles_list(self) -> list:
        """Возвращает список затронутых ролей."""
        if not self.affected_roles:
            return []
        return self.affected_roles if isinstance(self.affected_roles, list) else []

    def enable(self) -> None:
        """Активирует политику."""
        self.enabled = True

    def disable(self) -> None:
        """Деактивирует политику."""
        self.enabled = False

    def set_mandatory(self) -> None:
        """Устанавливает обязательный уровень принудительного применения."""
        self.enforcement_level = EnforcementLevel.MANDATORY.value

    def set_optional(self) -> None:
        """Устанавливает опциональный уровень принудительного применения."""
        self.enforcement_level = EnforcementLevel.OPTIONAL.value

    def set_audit_only(self) -> None:
        """Устанавливает режим только для аудита."""
        self.enforcement_level = EnforcementLevel.AUDIT_ONLY.value
