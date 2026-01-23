from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List
import ipaddress

from src.models.ip_whitelist import IPWhitelist
from src.models.user import User


class IPWhitelistService:
    def validate_cidr(self, cidr: str) -> bool:
        """
        Validate if a CIDR notation is syntactically valid.

        Args:
            cidr: IP address or CIDR range (e.g., "192.168.1.1" or "192.168.1.0/24")

        Returns:
            bool: True if valid, False otherwise
        """
        if not cidr or not isinstance(cidr, str):
            return False

        try:
            # Try to parse as IPv4Network or IPv6Network
            # Use strict=False to allow single IPs without network mask
            if '/' in cidr:
                ipaddress.ip_network(cidr, strict=False)
            else:
                ipaddress.ip_address(cidr)
            return True
        except ValueError:
            return False

    def is_ip_whitelisted(self, db: Session, ip: str, check_active_only: bool = True) -> bool:
        """
        Check if an IP address is in any whitelisted range.

        Args:
            db: Database session
            ip: IP address to check (e.g., "192.168.1.100")
            check_active_only: If True, only check active whitelist entries

        Returns:
            bool: True if IP is whitelisted, False otherwise
        """
        if not ip:
            return False

        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            # Invalid IP address
            return False

        # Get all whitelist entries
        query = db.query(IPWhitelist)
        if check_active_only:
            query = query.filter(IPWhitelist.is_active == True)

        whitelist_entries = query.all()

        # Check if IP matches any whitelist entry
        for entry in whitelist_entries:
            if not entry.cidr:
                continue

            try:
                if '/' in entry.cidr:
                    # CIDR range - check if IP is in network
                    network = ipaddress.ip_network(entry.cidr, strict=False)
                    if ip_obj in network:
                        return True
                else:
                    # Single IP - check exact match
                    if str(ip_obj) == entry.cidr:
                        return True
            except ValueError:
                # Invalid CIDR in database, skip this entry
                continue

        return False

    def create_whitelist_entry(
        self,
        db: Session,
        cidr: str,
        description: str | None = None,
        created_by: User | None = None,
        is_active: bool = True
    ) -> IPWhitelist:
        """
        Create a new IP whitelist entry.

        Args:
            db: Database session
            cidr: IP address or CIDR range
            description: Optional description of the network
            created_by: User who is creating this entry
            is_active: Whether the entry should be active

        Returns:
            IPWhitelist: Created whitelist entry

        Raises:
            HTTPException: If CIDR is invalid or already exists
        """
        # Validate CIDR format
        if not self.validate_cidr(cidr):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid CIDR format: {cidr}"
            )

        # Check if CIDR already exists
        existing = db.query(IPWhitelist).filter(IPWhitelist.cidr == cidr).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"IP whitelist entry already exists for: {cidr}"
            )

        # Create new whitelist entry
        whitelist_entry = IPWhitelist(
            cidr=cidr,
            description=description,
            created_by_id=created_by.id if created_by else None,
            is_active=is_active
        )

        db.add(whitelist_entry)
        db.commit()
        db.refresh(whitelist_entry)

        return whitelist_entry

    def get_whitelist_entry(self, db: Session, entry_id: str) -> IPWhitelist:
        """
        Get a specific IP whitelist entry by ID.

        Args:
            db: Database session
            entry_id: UUID of the whitelist entry

        Returns:
            IPWhitelist: The whitelist entry

        Raises:
            HTTPException: If entry not found
        """
        entry = db.query(IPWhitelist).filter(IPWhitelist.id == entry_id).first()
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"IP whitelist entry not found: {entry_id}"
            )
        return entry

    def get_all_whitelist_entries(
        self,
        db: Session,
        active_only: bool = False,
        include_ipv4: bool = True,
        include_ipv6: bool = True
    ) -> List[IPWhitelist]:
        """
        Get all IP whitelist entries with optional filtering.

        Args:
            db: Database session
            active_only: If True, only return active entries
            include_ipv4: If False, exclude IPv4 entries
            include_ipv6: If False, exclude IPv6 entries

        Returns:
            List[IPWhitelist]: List of whitelist entries
        """
        query = db.query(IPWhitelist)

        if active_only:
            query = query.filter(IPWhitelist.is_active == True)

        entries = query.all()

        # Filter by IP type if specified
        if not include_ipv4 or not include_ipv6:
            filtered_entries = []
            for entry in entries:
                if include_ipv4 and entry.is_ipv4:
                    filtered_entries.append(entry)
                elif include_ipv6 and entry.is_ipv6:
                    filtered_entries.append(entry)
            entries = filtered_entries

        return entries

    def update_whitelist_entry(
        self,
        db: Session,
        entry_id: str,
        description: str | None = None,
        is_active: bool | None = None
    ) -> IPWhitelist:
        """
        Update an existing IP whitelist entry.

        Args:
            db: Database session
            entry_id: UUID of the whitelist entry
            description: New description (optional)
            is_active: New active status (optional)

        Returns:
            IPWhitelist: Updated whitelist entry

        Raises:
            HTTPException: If entry not found
        """
        entry = self.get_whitelist_entry(db, entry_id)

        if description is not None:
            entry.description = description

        if is_active is not None:
            entry.is_active = is_active

        db.commit()
        db.refresh(entry)

        return entry

    def delete_whitelist_entry(self, db: Session, entry_id: str) -> None:
        """
        Delete an IP whitelist entry.

        Args:
            db: Database session
            entry_id: UUID of the whitelist entry

        Raises:
            HTTPException: If entry not found
        """
        entry = self.get_whitelist_entry(db, entry_id)
        db.delete(entry)
        db.commit()

    def activate_whitelist_entry(self, db: Session, entry_id: str) -> IPWhitelist:
        """
        Activate an IP whitelist entry.

        Args:
            db: Database session
            entry_id: UUID of the whitelist entry

        Returns:
            IPWhitelist: Updated whitelist entry
        """
        entry = self.get_whitelist_entry(db, entry_id)
        entry.activate()
        db.commit()
        db.refresh(entry)
        return entry

    def deactivate_whitelist_entry(self, db: Session, entry_id: str) -> IPWhitelist:
        """
        Deactivate an IP whitelist entry.

        Args:
            db: Database session
            entry_id: UUID of the whitelist entry

        Returns:
            IPWhitelist: Updated whitelist entry
        """
        entry = self.get_whitelist_entry(db, entry_id)
        entry.deactivate()
        db.commit()
        db.refresh(entry)
        return entry

    def normalize_cidr(self, cidr: str) -> str:
        """
        Normalize a CIDR string to a consistent format.

        Args:
            cidr: IP address or CIDR range

        Returns:
            str: Normalized CIDR string

        Raises:
            ValueError: If CIDR is invalid
        """
        if not self.validate_cidr(cidr):
            raise ValueError(f"Invalid CIDR: {cidr}")

        try:
            if '/' in cidr:
                network = ipaddress.ip_network(cidr, strict=False)
                return str(network)
            else:
                ip = ipaddress.ip_address(cidr)
                return str(ip)
        except ValueError as e:
            raise ValueError(f"Error normalizing CIDR: {e}")

    def get_whitelist_info(self, db: Session) -> dict:
        """
        Get summary information about the IP whitelist.

        Args:
            db: Database session

        Returns:
            dict: Summary statistics
        """
        all_entries = db.query(IPWhitelist).all()
        active_entries = [e for e in all_entries if e.is_active]
        ipv4_entries = [e for e in all_entries if e.is_ipv4]
        ipv6_entries = [e for e in all_entries if e.is_ipv6]

        return {
            "total_entries": len(all_entries),
            "active_entries": len(active_entries),
            "inactive_entries": len(all_entries) - len(active_entries),
            "ipv4_entries": len(ipv4_entries),
            "ipv6_entries": len(ipv6_entries)
        }


ip_whitelist_service = IPWhitelistService()
