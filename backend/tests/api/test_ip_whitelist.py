"""
Unit tests for IP whitelist enforcement.

Tests for IPWhitelistService, IPWhitelistMiddleware, and IP whitelist API endpoints.
"""

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import uuid

from src.services.ip_whitelist_service import ip_whitelist_service
from src.models.ip_whitelist import IPWhitelist
from src.models.user import User, UserRole, UserStatus


# ============================================================================
# IPWhitelistService Tests
# ============================================================================

class TestIPWhitelistServiceValidateCIDR:
    """Tests for IPWhitelistService.validate_cidr method."""

    def test_validate_valid_ipv4(self):
        """Test validation of valid IPv4 addresses."""
        assert ip_whitelist_service.validate_cidr("192.168.1.1") is True
        assert ip_whitelist_service.validate_cidr("10.0.0.1") is True
        assert ip_whitelist_service.validate_cidr("172.16.0.1") is True

    def test_validate_valid_ipv4_cidr(self):
        """Test validation of valid IPv4 CIDR ranges."""
        assert ip_whitelist_service.validate_cidr("192.168.1.0/24") is True
        assert ip_whitelist_service.validate_cidr("10.0.0.0/8") is True
        assert ip_whitelist_service.validate_cidr("172.16.0.0/12") is True
        assert ip_whitelist_service.validate_cidr("0.0.0.0/0") is True

    def test_validate_valid_ipv6(self):
        """Test validation of valid IPv6 addresses."""
        assert ip_whitelist_service.validate_cidr("::1") is True
        assert ip_whitelist_service.validate_cidr("2001:db8::1") is True
        assert ip_whitelist_service.validate_cidr("fe80::1") is True

    def test_validate_valid_ipv6_cidr(self):
        """Test validation of valid IPv6 CIDR ranges."""
        assert ip_whitelist_service.validate_cidr("2001:db8::/32") is True
        assert ip_whitelist_service.validate_cidr("fe80::/10") is True
        assert ip_whitelist_service.validate_cidr("::/0") is True

    def test_validate_invalid_cidr(self):
        """Test validation of invalid CIDR formats."""
        assert ip_whitelist_service.validate_cidr("") is False
        assert ip_whitelist_service.validate_cidr(None) is False
        assert ip_whitelist_service.validate_cidr("invalid") is False
        assert ip_whitelist_service.validate_cidr("256.256.256.256") is False
        assert ip_whitelist_service.validate_cidr("192.168.1.1/33") is False
        assert ip_whitelist_service.validate_cidr("192.168.1.1/-1") is False
        assert ip_whitelist_service.validate_cidr("192.168.1.1/24/32") is False
        assert ip_whitelist_service.validate_cidr(123) is False


class TestIPWhitelistServiceIsIPWhitelisted:
    """Tests for IPWhitelistService.is_ip_whitelisted method."""

    def test_single_ip_match(self, db_session):
        """Test checking if a single IP matches whitelist entry."""
        # Create a whitelist entry for a single IP
        entry = IPWhitelist(cidr="192.168.1.100", description="Test IP", is_active=True)
        db_session.add(entry)
        db_session.commit()

        # Test exact match
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "192.168.1.100") is True

        # Test non-matching IP
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "192.168.1.101") is False
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "10.0.0.1") is False

    def test_cidr_range_match(self, db_session):
        """Test checking if IP falls within CIDR range."""
        # Create a whitelist entry for a CIDR range
        entry = IPWhitelist(cidr="192.168.1.0/24", description="Office Network", is_active=True)
        db_session.add(entry)
        db_session.commit()

        # Test IPs within range
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "192.168.1.1") is True
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "192.168.1.100") is True
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "192.168.1.254") is True

        # Test IPs outside range
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "192.168.2.1") is False
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "10.0.0.1") is False

    def test_ipv6_cidr_range_match(self, db_session):
        """Test checking if IPv6 address falls within CIDR range."""
        # Create a whitelist entry for IPv6 CIDR range
        entry = IPWhitelist(cidr="2001:db8::/32", description="IPv6 Network", is_active=True)
        db_session.add(entry)
        db_session.commit()

        # Test IPv6 addresses within range
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "2001:db8::1") is True
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "2001:db8::ffff") is True
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "2001:db8:1::1") is False

    def test_inactive_entries_ignored(self, db_session):
        """Test that inactive whitelist entries are ignored."""
        # Create an inactive whitelist entry
        entry = IPWhitelist(cidr="192.168.1.0/24", description="Inactive Network", is_active=False)
        db_session.add(entry)
        db_session.commit()

        # Should not match inactive entry
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "192.168.1.1") is False

        # When checking all entries (including inactive)
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "192.168.1.1", check_active_only=False) is True

    def test_invalid_ip_address(self, db_session):
        """Test checking invalid IP address returns False."""
        entry = IPWhitelist(cidr="192.168.1.0/24", is_active=True)
        db_session.add(entry)
        db_session.commit()

        assert ip_whitelist_service.is_ip_whitelisted(db_session, "invalid") is False
        assert ip_whitelist_service.is_ip_whitelisted(db_session, "") is False
        assert ip_whitelist_service.is_ip_whitelisted(db_session, None) is False


class TestIPWhitelistServiceCreateWhitelistEntry:
    """Tests for IPWhitelistService.create_whitelist_entry method."""

    def test_create_single_ip_entry(self, db_session, admin_user):
        """Test creating a whitelist entry for a single IP."""
        entry = ip_whitelist_service.create_whitelist_entry(
            db_session,
            cidr="192.168.1.100",
            description="Single IP",
            created_by=admin_user,
            is_active=True
        )

        assert entry.cidr == "192.168.1.100"
        assert entry.description == "Single IP"
        assert entry.is_active is True
        assert entry.created_by_id == admin_user.id
        assert entry.is_ipv4 is True
        assert entry.is_ipv6 is False

    def test_create_cidr_range_entry(self, db_session, admin_user):
        """Test creating a whitelist entry for a CIDR range."""
        entry = ip_whitelist_service.create_whitelist_entry(
            db_session,
            cidr="10.0.0.0/8",
            description="Private Network",
            created_by=admin_user
        )

        assert entry.cidr == "10.0.0.0/8"
        assert entry.description == "Private Network"
        assert entry.is_active is True

    def test_create_ipv6_entry(self, db_session, admin_user):
        """Test creating a whitelist entry for IPv6."""
        entry = ip_whitelist_service.create_whitelist_entry(
            db_session,
            cidr="2001:db8::/32",
            description="IPv6 Network",
            created_by=admin_user
        )

        assert entry.cidr == "2001:db8::/32"
        assert entry.is_ipv4 is False
        assert entry.is_ipv6 is True

    def test_create_invalid_cidr_raises_error(self, db_session, admin_user):
        """Test that creating entry with invalid CIDR raises HTTPException."""
        with pytest.raises(HTTPException) as exc_info:
            ip_whitelist_service.create_whitelist_entry(
                db_session,
                cidr="invalid-ip",
                created_by=admin_user
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid CIDR format" in exc_info.value.detail

    def test_create_duplicate_cidr_raises_error(self, db_session, admin_user):
        """Test that creating duplicate CIDR entry raises HTTPException."""
        # Create first entry
        ip_whitelist_service.create_whitelist_entry(
            db_session,
            cidr="192.168.1.0/24",
            created_by=admin_user
        )

        # Try to create duplicate
        with pytest.raises(HTTPException) as exc_info:
            ip_whitelist_service.create_whitelist_entry(
                db_session,
                cidr="192.168.1.0/24",
                created_by=admin_user
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in exc_info.value.detail


class TestIPWhitelistServiceGetWhitelistEntry:
    """Tests for IPWhitelistService.get_whitelist_entry method."""

    def test_get_existing_entry(self, db_session):
        """Test getting an existing whitelist entry."""
        entry = IPWhitelist(cidr="192.168.1.0/24", description="Test")
        db_session.add(entry)
        db_session.commit()
        db_session.refresh(entry)

        retrieved = ip_whitelist_service.get_whitelist_entry(db_session, str(entry.id))
        assert retrieved.id == entry.id
        assert retrieved.cidr == "192.168.1.0/24"

    def test_get_nonexistent_entry_raises_error(self, db_session):
        """Test that getting nonexistent entry raises HTTPException."""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            ip_whitelist_service.get_whitelist_entry(db_session, str(fake_id))

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in exc_info.value.detail


class TestIPWhitelistServiceGetAllWhitelistEntries:
    """Tests for IPWhitelistService.get_all_whitelist_entries method."""

    def test_get_all_entries(self, db_session):
        """Test getting all whitelist entries."""
        # Create multiple entries
        entries = [
            IPWhitelist(cidr="192.168.1.0/24", description="Network 1", is_active=True),
            IPWhitelist(cidr="10.0.0.0/8", description="Network 2", is_active=False),
            IPWhitelist(cidr="172.16.0.0/12", description="Network 3", is_active=True),
        ]
        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        # Get all entries
        all_entries = ip_whitelist_service.get_all_whitelist_entries(db_session)
        assert len(all_entries) == 3

    def test_get_active_only(self, db_session):
        """Test getting only active entries."""
        entries = [
            IPWhitelist(cidr="192.168.1.0/24", is_active=True),
            IPWhitelist(cidr="10.0.0.0/8", is_active=False),
        ]
        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        active_entries = ip_whitelist_service.get_all_whitelist_entries(db_session, active_only=True)
        assert len(active_entries) == 1
        assert active_entries[0].cidr == "192.168.1.0/24"

    def test_filter_ipv4_only(self, db_session):
        """Test filtering only IPv4 entries."""
        entries = [
            IPWhitelist(cidr="192.168.1.0/24"),  # IPv4
            IPWhitelist(cidr="2001:db8::/32"),  # IPv6
        ]
        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        ipv4_entries = ip_whitelist_service.get_all_whitelist_entries(
            db_session,
            include_ipv4=True,
            include_ipv6=False
        )
        assert len(ipv4_entries) == 1
        assert ipv4_entries[0].is_ipv4 is True

    def test_filter_ipv6_only(self, db_session):
        """Test filtering only IPv6 entries."""
        entries = [
            IPWhitelist(cidr="192.168.1.0/24"),  # IPv4
            IPWhitelist(cidr="2001:db8::/32"),  # IPv6
        ]
        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        ipv6_entries = ip_whitelist_service.get_all_whitelist_entries(
            db_session,
            include_ipv4=False,
            include_ipv6=True
        )
        assert len(ipv6_entries) == 1
        assert ipv6_entries[0].is_ipv6 is True


class TestIPWhitelistServiceUpdateWhitelistEntry:
    """Tests for IPWhitelistService.update_whitelist_entry method."""

    def test_update_entry_description(self, db_session):
        """Test updating entry description."""
        entry = IPWhitelist(cidr="192.168.1.0/24", description="Old description")
        db_session.add(entry)
        db_session.commit()

        updated = ip_whitelist_service.update_whitelist_entry(
            db_session,
            str(entry.id),
            description="New description"
        )

        assert updated.description == "New description"
        assert updated.cidr == "192.168.1.0/24"

    def test_update_entry_active_status(self, db_session):
        """Test updating entry active status."""
        entry = IPWhitelist(cidr="192.168.1.0/24", is_active=True)
        db_session.add(entry)
        db_session.commit()

        updated = ip_whitelist_service.update_whitelist_entry(
            db_session,
            str(entry.id),
            is_active=False
        )

        assert updated.is_active is False

    def test_update_nonexistent_entry_raises_error(self, db_session):
        """Test that updating nonexistent entry raises HTTPException."""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            ip_whitelist_service.update_whitelist_entry(
                db_session,
                str(fake_id),
                description="Test"
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestIPWhitelistServiceDeleteWhitelistEntry:
    """Tests for IPWhitelistService.delete_whitelist_entry method."""

    def test_delete_entry(self, db_session):
        """Test deleting a whitelist entry."""
        entry = IPWhitelist(cidr="192.168.1.0/24")
        db_session.add(entry)
        db_session.commit()
        entry_id = str(entry.id)

        ip_whitelist_service.delete_whitelist_entry(db_session, entry_id)

        # Verify entry is deleted
        deleted = db_session.query(IPWhitelist).filter(IPWhitelist.id == entry_id).first()
        assert deleted is None

    def test_delete_nonexistent_entry_raises_error(self, db_session):
        """Test that deleting nonexistent entry raises HTTPException."""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            ip_whitelist_service.delete_whitelist_entry(db_session, str(fake_id))

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestIPWhitelistServiceActivateDeactivate:
    """Tests for activate_whitelist_entry and deactivate_whitelist_entry methods."""

    def test_activate_entry(self, db_session):
        """Test activating a whitelist entry."""
        entry = IPWhitelist(cidr="192.168.1.0/24", is_active=False)
        db_session.add(entry)
        db_session.commit()

        activated = ip_whitelist_service.activate_whitelist_entry(db_session, str(entry.id))
        assert activated.is_active is True

    def test_deactivate_entry(self, db_session):
        """Test deactivating a whitelist entry."""
        entry = IPWhitelist(cidr="192.168.1.0/24", is_active=True)
        db_session.add(entry)
        db_session.commit()

        deactivated = ip_whitelist_service.deactivate_whitelist_entry(db_session, str(entry.id))
        assert deactivated.is_active is False


class TestIPWhitelistServiceNormalizeCIDR:
    """Tests for IPWhitelistService.normalize_cidr method."""

    def test_normalize_single_ipv4(self):
        """Test normalizing single IPv4 address."""
        assert ip_whitelist_service.normalize_cidr("192.168.1.1") == "192.168.1.1"

    def test_normalize_ipv4_cidr(self):
        """Test normalizing IPv4 CIDR range."""
        # Normalization should expand the network address
        result = ip_whitelist_service.normalize_cidr("192.168.1.0/24")
        assert result == "192.168.1.0/24"

    def test_normalize_ipv6(self):
        """Test normalizing IPv6 address."""
        assert ip_whitelist_service.normalize_cidr("::1") == "::1"

    def test_normalize_invalid_cidr_raises_error(self):
        """Test that normalizing invalid CIDR raises ValueError."""
        with pytest.raises(ValueError):
            ip_whitelist_service.normalize_cidr("invalid-ip")


class TestIPWhitelistServiceGetWhitelistInfo:
    """Tests for IPWhitelistService.get_whitelist_info method."""

    def test_get_whitelist_info(self, db_session):
        """Test getting whitelist summary information."""
        # Create entries
        entries = [
            IPWhitelist(cidr="192.168.1.0/24", is_active=True),  # IPv4, active
            IPWhitelist(cidr="10.0.0.0/8", is_active=False),  # IPv4, inactive
            IPWhitelist(cidr="2001:db8::/32", is_active=True),  # IPv6, active
        ]
        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        info = ip_whitelist_service.get_whitelist_info(db_session)

        assert info["total_entries"] == 3
        assert info["active_entries"] == 2
        assert info["inactive_entries"] == 1
        assert info["ipv4_entries"] == 2
        assert info["ipv6_entries"] == 1

    def test_get_whitelist_info_empty(self, db_session):
        """Test getting whitelist info when empty."""
        info = ip_whitelist_service.get_whitelist_info(db_session)

        assert info["total_entries"] == 0
        assert info["active_entries"] == 0
        assert info["inactive_entries"] == 0
        assert info["ipv4_entries"] == 0
        assert info["ipv6_entries"] == 0


# ============================================================================
# IP Whitelist API Endpoint Tests
# ============================================================================

class TestIPWhitelistAPIListEntries:
    """Tests for GET /api/admin/ip-whitelist/entries endpoint."""

    def test_list_entries_as_admin(self, client: TestClient, admin_user, db_session, admin_auth_headers):
        """Test listing entries as admin user."""
        # Create test entries
        entries = [
            IPWhitelist(cidr="192.168.1.0/24", description="Network 1", is_active=True),
            IPWhitelist(cidr="10.0.0.0/8", description="Network 2", is_active=False),
        ]
        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        response = client.get("/api/admin/ip-whitelist/entries", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["cidr"] in ["192.168.1.0/24", "10.0.0.0/8"]

    def test_list_entries_active_only_filter(self, client: TestClient, admin_user, db_session, admin_auth_headers):
        """Test listing entries with active_only filter."""
        entries = [
            IPWhitelist(cidr="192.168.1.0/24", is_active=True),
            IPWhitelist(cidr="10.0.0.0/8", is_active=False),
        ]
        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        response = client.get("/api/admin/ip-whitelist/entries?active_only=true", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_active"] is True

    def test_list_entries_unauthorized(self, client: TestClient):
        """Test listing entries without authentication."""
        response = client.get("/api/admin/ip-whitelist/entries")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestIPWhitelistAPICreateEntry:
    """Tests for POST /api/admin/ip-whitelist/entries endpoint."""

    def test_create_entry_as_admin(self, client: TestClient, db_session, admin_auth_headers):
        """Test creating entry as admin."""
        response = client.post(
            "/api/admin/ip-whitelist/entries",
            json={
                "cidr": "192.168.1.0/24",
                "description": "Office Network",
                "is_active": True
            },
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["cidr"] == "192.168.1.0/24"
        assert data["description"] == "Office Network"
        assert data["is_active"] is True

    def test_create_entry_invalid_cidr(self, client: TestClient, admin_auth_headers):
        """Test creating entry with invalid CIDR."""
        response = client.post(
            "/api/admin/ip-whitelist/entries",
            json={"cidr": "invalid-ip"},
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_entry_duplicate_cidr(self, client: TestClient, db_session, admin_auth_headers):
        """Test creating entry with duplicate CIDR."""
        # Create first entry
        entry = IPWhitelist(cidr="192.168.1.0/24")
        db_session.add(entry)
        db_session.commit()

        # Try to create duplicate
        response = client.post(
            "/api/admin/ip-whitelist/entries",
            json={"cidr": "192.168.1.0/24"},
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_409_CONFLICT


class TestIPWhitelistAPIGetEntry:
    """Tests for GET /api/admin/ip-whitelist/entries/{entry_id} endpoint."""

    def test_get_entry_as_admin(self, client: TestClient, db_session, admin_auth_headers):
        """Test getting specific entry as admin."""
        entry = IPWhitelist(cidr="192.168.1.0/24", description="Test Network")
        db_session.add(entry)
        db_session.commit()

        response = client.get(f"/api/admin/ip-whitelist/entries/{entry.id}", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["cidr"] == "192.168.1.0/24"
        assert data["description"] == "Test Network"

    def test_get_entry_not_found(self, client: TestClient, admin_auth_headers):
        """Test getting nonexistent entry."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/admin/ip-whitelist/entries/{fake_id}", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestIPWhitelistAPIUpdateEntry:
    """Tests for PUT /api/admin/ip-whitelist/entries/{entry_id} endpoint."""

    def test_update_entry_as_admin(self, client: TestClient, db_session, admin_auth_headers):
        """Test updating entry as admin."""
        entry = IPWhitelist(cidr="192.168.1.0/24", description="Old Description")
        db_session.add(entry)
        db_session.commit()

        response = client.put(
            f"/api/admin/ip-whitelist/entries/{entry.id}",
            json={"description": "New Description"},
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["description"] == "New Description"

    def test_update_entry_not_found(self, client: TestClient, admin_auth_headers):
        """Test updating nonexistent entry."""
        fake_id = uuid.uuid4()
        response = client.put(
            f"/api/admin/ip-whitelist/entries/{fake_id}",
            json={"description": "Test"},
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestIPWhitelistAPIDeleteEntry:
    """Tests for DELETE /api/admin/ip-whitelist/entries/{entry_id} endpoint."""

    def test_delete_entry_as_admin(self, client: TestClient, db_session, admin_auth_headers):
        """Test deleting entry as admin."""
        entry = IPWhitelist(cidr="192.168.1.0/24")
        db_session.add(entry)
        db_session.commit()
        entry_id = str(entry.id)

        response = client.delete(f"/api/admin/ip-whitelist/entries/{entry_id}", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"

        # Verify deletion
        deleted = db_session.query(IPWhitelist).filter(IPWhitelist.id == entry_id).first()
        assert deleted is None

    def test_delete_entry_not_found(self, client: TestClient, admin_auth_headers):
        """Test deleting nonexistent entry."""
        fake_id = uuid.uuid4()
        response = client.delete(f"/api/admin/ip-whitelist/entries/{fake_id}", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestIPWhitelistAPIActivateDeactivate:
    """Tests for activate/deactivate endpoints."""

    def test_activate_entry(self, client: TestClient, db_session, admin_auth_headers):
        """Test activating an entry."""
        entry = IPWhitelist(cidr="192.168.1.0/24", is_active=False)
        db_session.add(entry)
        db_session.commit()

        response = client.post(f"/api/admin/ip-whitelist/entries/{entry.id}/activate", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is True

    def test_deactivate_entry(self, client: TestClient, db_session, admin_auth_headers):
        """Test deactivating an entry."""
        entry = IPWhitelist(cidr="192.168.1.0/24", is_active=True)
        db_session.add(entry)
        db_session.commit()

        response = client.post(f"/api/admin/ip-whitelist/entries/{entry.id}/deactivate", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False


class TestIPWhitelistAPICheckIP:
    """Tests for POST /api/admin/ip-whitelist/check endpoint."""

    def test_check_whitelisted_ip(self, client: TestClient, db_session, admin_auth_headers):
        """Test checking a whitelisted IP."""
        entry = IPWhitelist(cidr="192.168.1.0/24", is_active=True)
        db_session.add(entry)
        db_session.commit()

        response = client.post(
            "/api/admin/ip-whitelist/check?ip=192.168.1.100",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ip"] == "192.168.1.100"
        assert data["is_whitelisted"] is True

    def test_check_non_whitelisted_ip(self, client: TestClient, admin_auth_headers):
        """Test checking a non-whitelisted IP."""
        response = client.post(
            "/api/admin/ip-whitelist/check?ip=10.0.0.1",
            headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_whitelisted"] is False


class TestIPWhitelistAPIGetInfo:
    """Tests for GET /api/admin/ip-whitelist/entries/info endpoint."""

    def test_get_whitelist_info(self, client: TestClient, db_session, admin_auth_headers):
        """Test getting whitelist summary info."""
        entries = [
            IPWhitelist(cidr="192.168.1.0/24", is_active=True),
            IPWhitelist(cidr="10.0.0.0/8", is_active=False),
            IPWhitelist(cidr="2001:db8::/32", is_active=True),
        ]
        for entry in entries:
            db_session.add(entry)
        db_session.commit()

        response = client.get("/api/admin/ip-whitelist/entries/info", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_entries"] == 3
        assert data["active_entries"] == 2
        assert data["inactive_entries"] == 1
        assert data["ipv4_entries"] == 2
        assert data["ipv6_entries"] == 1


# ============================================================================
# IPWhitelistMiddleware Tests
# ============================================================================

class TestIPWhitelistMiddleware:
    """Tests for IP whitelist middleware."""

    def test_middleware_allows_whitelisted_ip(self, client: TestClient, db_session):
        """Test that middleware allows whitelisted IP."""
        # Add IP to whitelist
        entry = IPWhitelist(cidr="192.168.1.0/24", is_active=True)
        db_session.add(entry)
        db_session.commit()

        # Make request from whitelisted IP
        response = client.get(
            "/api/health",
            headers={"X-Forwarded-For": "192.168.1.100"}
        )

        # Should succeed (or get the actual health endpoint response)
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_middleware_blocks_non_whitelisted_ip_in_strict_mode(self, client: TestClient, db_session, mocker):
        """Test that middleware blocks non-whitelisted IP in strict mode."""
        # Mock settings to enable strict mode
        mock_settings = mocker.Mock()
        mock_settings.IP_WHITELIST_ENABLED = True
        mock_settings.IP_WHITELIST_STRICT_MODE = True
        mock_settings.IP_WHITELIST_ALLOW_LOOPBACK = False

        with patch('src.frameworks.http.middleware.ip_whitelist.settings', mock_settings):
            # Make request from non-whitelisted IP
            response = client.get(
                "/api/protected-endpoint",
                headers={"X-Forwarded-For": "10.0.0.1"}
            )

            # Should be blocked
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_middleware_allows_loopback(self, client: TestClient, mocker):
        """Test that middleware allows loopback addresses when configured."""
        mock_settings = mocker.Mock()
        mock_settings.IP_WHITELIST_ENABLED = True
        mock_settings.IP_WHITELIST_STRICT_MODE = True
        mock_settings.IP_WHITELIST_ALLOW_LOOPBACK = True

        with patch('src.frameworks.http.middleware.ip_whitelist.settings', mock_settings):
            response = client.get(
                "/api/health",
                headers={"X-Forwarded-For": "127.0.0.1"}
            )

            assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_middleware_skips_health_check(self, client: TestClient):
        """Test that middleware skips health check endpoint."""
        response = client.get("/api/health")

        # Health check should always be accessible
        assert response.status_code != status.HTTP_403_FORBIDDEN

    def test_middleware_extracts_ip_from_x_forwarded_for(self):
        """Test that middleware extracts IP from X-Forwarded-For header."""
        from src.frameworks.http.middleware.ip_whitelist import IPWhitelistMiddleware

        middleware = IPWhitelistMiddleware(app=None)
        mock_request = Mock()
        mock_request.headers = {"X-Forwarded-For": "192.168.1.100, 10.0.0.1"}
        mock_request.client = None

        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_middleware_extracts_ip_from_x_real_ip(self):
        """Test that middleware extracts IP from X-Real-IP header."""
        from src.frameworks.http.middleware.ip_whitelist import IPWhitelistMiddleware

        middleware = IPWhitelistMiddleware(app=None)
        mock_request = Mock()
        mock_request.headers = {"X-Real-IP": "192.168.1.100"}
        mock_request.client = None

        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_middleware_extracts_ip_from_client(self):
        """Test that middleware extracts IP from request.client."""
        from src.frameworks.http.middleware.ip_whitelist import IPWhitelistMiddleware

        middleware = IPWhitelistMiddleware(app=None)
        mock_request = Mock()
        mock_request.headers = {}
        mock_client = Mock()
        mock_client.host = "192.168.1.100"
        mock_request.client = mock_client

        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_middleware_is_loopback(self):
        """Test loopback address detection."""
        from src.frameworks.http.middleware.ip_whitelist import IPWhitelistMiddleware

        middleware = IPWhitelistMiddleware(app=None)

        assert middleware._is_loopback("127.0.0.1") is True
        assert middleware._is_loopback("127.0.0.2") is True
        assert middleware._is_loopback("::1") is True
        assert middleware._is_loopback("localhost") is True
        assert middleware._is_loopback("192.168.1.1") is False
