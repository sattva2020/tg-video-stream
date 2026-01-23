import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, func, Boolean, text, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class IPWhitelist(Base):
    """IP whitelist model for network access control.

    Stores IP addresses and CIDR ranges that are allowed to access the system.
    This provides enterprise-grade network security by restricting access to trusted networks.
    """
    __tablename__ = "ip_whitelist"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # IP address or CIDR range (e.g., "192.168.1.1" or "192.168.1.0/24")
    cidr = Column(String(45), nullable=False, unique=True, index=True)  # IPv6 can be up to 45 chars

    # Description of the whitelisted network (e.g., "Office Network", "VPN", "Data Center")
    description = Column(String(255), nullable=True)

    # Whether this whitelist entry is active
    is_active = Column(Boolean, nullable=False, server_default=text('true'), default=True)

    # Track who created this whitelist entry (for audit purposes)
    created_by_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    created_by = relationship("User", backref="ip_whitelist_entries")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<IPWhitelist(cidr='{self.cidr}', description='{self.description}', is_active={self.is_active})>"

    def is_valid_cidr(self) -> bool:
        """
        Validate if the CIDR notation is syntactically valid.
        Does not check if it's a valid IP range, just the format.

        Returns:
            bool: True if the CIDR format is valid, False otherwise
        """
        if not self.cidr:
            return False

        # Basic validation for CIDR format
        # Can contain single IP or CIDR range (e.g., 192.168.1.1 or 192.168.1.0/24)
        parts = self.cidr.split('/')

        if len(parts) > 2:
            return False

        if len(parts) == 2:
            # CIDR range - validate prefix length
            try:
                prefix_len = int(parts[1])
                if prefix_len < 0 or prefix_len > 128:
                    return False
            except ValueError:
                return False

        return True

    def activate(self) -> None:
        """Activate this whitelist entry."""
        self.is_active = True

    def deactivate(self) -> None:
        """Deactivate this whitelist entry."""
        self.is_active = False

    @property
    def is_ipv4(self) -> bool:
        """Check if this is an IPv4 address/range."""
        return ':' not in self.cidr

    @property
    def is_ipv6(self) -> bool:
        """Check if this is an IPv6 address/range."""
        return ':' in self.cidr
