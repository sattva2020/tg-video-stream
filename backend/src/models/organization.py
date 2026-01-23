import uuid
from sqlalchemy import Column, String, DateTime, func, Boolean
from src.database import Base, GUID


class Organization(Base):
    """Organization model for multi-tenant support."""
    __tablename__ = "organizations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=True, index=True)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), nullable=True)  # Hex color
    secondary_color = Column(String(7), nullable=True)  # Hex color
    custom_domain = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default='true')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Organization(id='{self.id}', name='{self.name}')>"
