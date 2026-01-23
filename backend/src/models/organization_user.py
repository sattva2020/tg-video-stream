import uuid
from enum import Enum as PyEnum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, func, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class OrganizationUserStatus(str, PyEnum):
    """Статусы пользователей в организации."""
    ACTIVE = "active"
    PENDING = "pending"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class OrganizationRole(Base):
    """Organization roles for multi-tenant permission management."""
    __tablename__ = "organization_roles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    permissions = Column(JSON(), nullable=False, default=dict, server_default="'{}'::jsonb")
    is_system_role = Column(Boolean(), nullable=False, default=False, server_default='false')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship(
        "Organization",
        back_populates="roles",
        lazy="select"
    )
    users = relationship(
        "OrganizationUser",
        back_populates="role",
        lazy="dynamic"
    )

    def __repr__(self):
        return f"<OrganizationRole(id='{self.id}', name='{self.name}', organization_id='{self.organization_id}')>"

    def has_permission(self, permission: str) -> bool:
        """Check if role has a specific permission."""
        if not self.permissions:
            return False
        return self.permissions.get(permission, False)


class OrganizationUser(Base):
    """Organization users for multi-tenant user management."""
    __tablename__ = "organization_users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(GUID(), ForeignKey("organization_roles.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(32), nullable=False, default=OrganizationUserStatus.ACTIVE.value, server_default="'active'", index=True)
    invited_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    organization = relationship(
        "Organization",
        back_populates="organization_users",
        lazy="select"
    )
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="organization_memberships",
        lazy="select"
    )
    role = relationship(
        "OrganizationRole",
        back_populates="users",
        lazy="select"
    )
    inviter = relationship(
        "User",
        foreign_keys=[invited_by],
        lazy="select"
    )

    def __repr__(self):
        return f"<OrganizationUser(id='{self.id}', organization_id='{self.organization_id}', user_id='{self.user_id}')>"

    def activate(self) -> None:
        """Activate user in organization."""
        self.status = OrganizationUserStatus.ACTIVE.value
        if not self.joined_at:
            self.joined_at = datetime.now(timezone.utc)

    def deactivate(self) -> None:
        """Deactivate user in organization."""
        self.status = OrganizationUserStatus.INACTIVE.value

    def suspend(self) -> None:
        """Suspend user in organization."""
        self.status = OrganizationUserStatus.SUSPENDED.value

    @property
    def is_active(self) -> bool:
        """Check if user is active in organization."""
        return self.status == OrganizationUserStatus.ACTIVE.value
