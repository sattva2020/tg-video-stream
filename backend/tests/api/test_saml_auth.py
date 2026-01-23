"""
Unit tests for SAML 2.0 authentication flow.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.models.saml_config import SAMLConfig
from src.models.user import User


# ============================================================================
# SAML Login Tests
# ============================================================================

def test_saml_login_redirect_when_disabled(client: TestClient, db_session: Session):
    """Test SAML login returns 501 when SAML is not configured."""
    # Mock saml_service as None to simulate SAML not available
    with patch('src.api.auth.saml.saml_service', None):
        response = client.get("/api/auth/saml/login")
        assert response.status_code == 501
        assert "SAML is not available" in response.json()["detail"]


def test_saml_login_no_active_config(client: TestClient, db_session: Session):
    """Test SAML login returns error when no active config exists."""
    with patch('src.api.auth.saml.saml_service', Mock()):
        # Mock get_saml_config to raise 503
        with patch('src.api.auth.saml.get_saml_config') as mock_get_config:
            from fastapi import HTTPException
            mock_get_config.side_effect = HTTPException(status_code=503, detail="SAML authentication is currently disabled.")

            response = client.get("/api/auth/saml/login")
            assert response.status_code == 503


def test_saml_login_initiates_redirect(client: TestClient, db_session: Session):
    """Test SAML login redirects to IdP when configured properly."""
    mock_saml_service = Mock()
    mock_saml_service.initiate_login.return_value = "https://idp.example.com/sso"

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api.auth.saml.get_saml_config') as mock_get_config:
            # Create a mock SAML config
            mock_config = Mock(spec=SAMLConfig)
            mock_config.name = "Test IdP"
            mock_config.is_active.return_value = True
            mock_get_config.return_value = mock_config

            response = client.get("/api/auth/saml/login?return_to=/dashboard")

            # Should redirect to IdP
            assert response.status_code == 307  # Temporary redirect
            assert "idp.example.com" in response.headers.get("location", "")


def test_saml_login_with_return_to(client: TestClient, db_session: Session):
    """Test SAML login preserves return_to parameter."""
    mock_saml_service = Mock()
    mock_saml_service.initiate_login.return_value = "https://idp.example.com/sso"

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api.auth.saml.get_saml_config') as mock_get_config:
            mock_config = Mock(spec=SAMLConfig)
            mock_config.name = "Test IdP"
            mock_get_config.return_value = mock_config

            return_to_url = "/admin/settings"
            response = client.get(f"/api/auth/saml/login?return_to={return_to_url}")

            # Verify initiate_login was called with return_to
            mock_saml_service.initiate_login.assert_called_once()
            call_args = mock_saml_service.initiate_login.call_args
            assert call_args[0][0] == mock_config  # config
            assert call_args[0][2] == return_to_url  # return_to


# ============================================================================
# SAML ACS (Assertion Consumer Service) Tests
# ============================================================================

def test_saml_acs_no_saml_service(client: TestClient, db_session: Session):
    """Test ACS returns redirect when SAML service is unavailable."""
    with patch('src.api.auth.saml.saml_service', None):
        response = client.post("/api/auth/saml/acs")
        assert response.status_code == 307  # Redirect to frontend with error
        assert "login?error=saml_not_available" in response.headers.get("location", "")


def test_saml_acs_processes_successful_auth(client: TestClient, db_session: Session):
    """Test ACS processes successful SAML response and creates user."""
    mock_saml_service = Mock()
    mock_saml_service.process_response.return_value = {
        'name_id': 'user@example.com',
        'attributes': {
            'email': ['user@example.com'],
            'displayName': ['Test User']
        },
        'session_index': 'session123'
    }

    # Mock user creation
    mock_user = Mock(spec=User)
    mock_user.id = "user-123"
    mock_user.email = "user@example.com"
    mock_user.status = "active"
    mock_user.saml_name_id = "user@example.com"

    mock_saml_service.get_or_create_user.return_value = (mock_user, True)

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api.auth.saml.get_saml_config') as mock_get_config:
            with patch('src.api.auth.saml.auth_service') as mock_auth_service:
                mock_config = Mock(spec=SAMLConfig)
                mock_get_config.return_value = mock_config
                mock_auth_service.create_jwt_for_user.return_value = "test_jwt_token"

                response = client.post("/api/auth/saml/acs", data={"SAMLResponse": "test_response"})

                # Should redirect to frontend with token
                assert response.status_code == 307
                location = response.headers.get("location", "")
                assert "auth/callback" in location
                assert "token=test_jwt_token" in location


def test_saml_acs_existing_user_updates_data(client: TestClient, db_session: Session):
    """Test ACS updates existing user data on login."""
    mock_saml_service = Mock()
    mock_saml_service.process_response.return_value = {
        'name_id': 'existing@example.com',
        'attributes': {'email': ['existing@example.com'], 'displayName': ['Updated Name']},
        'session_index': 'session123'
    }

    mock_user = Mock(spec=User)
    mock_user.id = "existing-user"
    mock_user.email = "existing@example.com"
    mock_user.status = "active"

    mock_saml_service.get_or_create_user.return_value = (mock_user, False)

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api.auth.saml.get_saml_config') as mock_get_config:
            with patch('src.api.auth.saml.auth_service') as mock_auth_service:
                mock_config = Mock(spec=SAMLConfig)
                mock_get_config.return_value = mock_config
                mock_auth_service.create_jwt_for_user.return_value = "jwt_token"

                response = client.post("/api/auth/saml/acs", data={"SAMLResponse": "response"})

                # Should redirect with token
                assert response.status_code == 307
                assert "jwt_token" in response.headers.get("location", "")


def test_saml_acs_pending_user_status(client: TestClient, db_session: Session):
    """Test ACS handles pending user status correctly."""
    mock_saml_service = Mock()
    mock_saml_service.process_response.return_value = {
        'name_id': 'new@example.com',
        'attributes': {'email': ['new@example.com']},
        'session_index': 'session123'
    }

    mock_user = Mock(spec=User)
    mock_user.id = "new-user"
    mock_user.email = "new@example.com"
    mock_user.status = "pending"

    mock_saml_service.get_or_create_user.return_value = (mock_user, True)

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api.auth.saml.get_saml_config') as mock_get_config:
            with patch('src.api.auth.saml.auth_service') as mock_auth_service:
                mock_config = Mock(spec=SAMLConfig)
                mock_get_config.return_value = mock_config
                mock_auth_service.create_jwt_for_user.return_value = "temp_token"

                response = client.post("/api/auth/saml/acs", data={"SAMLResponse": "response"})

                # Should redirect with status=pending
                location = response.headers.get("location", "")
                assert "status=pending" in location


# ============================================================================
# SAML Metadata Tests
# ============================================================================

def test_saml_metadata_returns_xml(client: TestClient, db_session: Session):
    """Test metadata endpoint returns XML with SP information."""
    mock_saml_service = Mock()
    mock_saml_service.get_metadata.return_value = """<?xml version="1.0"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata">
  <SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="https://example.com/api/auth/saml/acs"/>
  </SPSSODescriptor>
</EntityDescriptor>"""

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api.auth.saml.get_saml_config') as mock_get_config:
            mock_config = Mock(spec=SAMLConfig)
            mock_config.name = "Test SP"
            mock_get_config.return_value = mock_config

            response = client.get("/api/auth/saml/metadata")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/xml; charset=utf-8"
            assert "EntityDescriptor" in response.text


def test_saml_metadata_unavailable_saml(client: TestClient, db_session: Session):
    """Test metadata returns 501 when SAML is not available."""
    with patch('src.api.auth.saml.saml_service', None):
        response = client.get("/api/auth/saml/metadata")
        assert response.status_code == 501


def test_saml_metadata_content_disposition(client: TestClient, db_session: Session):
    """Test metadata has proper content-disposition header."""
    mock_saml_service = Mock()
    mock_saml_service.get_metadata.return_value = "<xml>metadata</xml>"

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api.auth.saml.get_saml_config') as mock_get_config:
            mock_config = Mock(spec=SAMLConfig)
            mock_get_config.return_value = mock_config

            response = client.get("/api/auth/saml/metadata")

            content_disp = response.headers.get("content-disposition", "")
            assert "attachment" in content_disp
            assert "saml-metadata.xml" in content_disp


# ============================================================================
# SAML Logout Tests
# ============================================================================

def test_saml_logout_initiates_slo(client: TestClient, db_session: Session):
    """Test logout initiates SLO when configured."""
    mock_saml_service = Mock()
    mock_saml_service.initiate_logout.return_value = "https://idp.example.com/logout"

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api.auth.saml.get_saml_config') as mock_get_config:
            mock_config = Mock(spec=SAMLConfig)
            mock_get_config.return_value = mock_config

            response = client.get("/api/auth/saml/logout?name_id=user@example.com&session_index=abc123")

            # Should redirect to IdP logout
            assert response.status_code == 307
            location = response.headers.get("location", "")
            assert "idp.example.com/logout" in location


def test_saml_logout_no_slo_configured(client: TestClient, db_session: Session):
    """Test logout redirects to frontend when SLO is not configured."""
    mock_saml_service = Mock()
    mock_saml_service.initiate_logout.return_value = None  # No SLO URL

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api/auth/saml.get_saml_config') as mock_get_config:
            mock_config = Mock(spec=SAMLConfig)
            mock_get_config.return_value = mock_config

            response = client.get("/api/auth/saml/logout")

            # Should redirect to frontend login
            assert response.status_code == 307
            assert "/login" in response.headers.get("location", "")


def test_saml_slo_callback_processes(client: TestClient, db_session: Session):
    """Test SLO callback processes logout response."""
    mock_saml_service = Mock()
    mock_saml_service.process_logout_response.return_value = True

    with patch('src.api.auth.saml.saml_service', mock_saml_service):
        with patch('src.api/auth.saml.get_saml_config') as mock_get_config:
            mock_config = Mock(spec=SAMLConfig)
            mock_get_config.return_value = mock_config

            response = client.get("/api/auth/saml/slo")

            # Should redirect to frontend with logged_out=true
            assert response.status_code == 307
            location = response.headers.get("location", "")
            assert "logged_out=true" in location


# ============================================================================
# SAML Service Unit Tests
# ============================================================================

def test_saml_service_initiate_login_success(db_session: Session):
    """Test SAMLService.initiate_login returns IdP URL."""
    from src.services.saml_service import SAMLService

    mock_config = Mock(spec=SAMLConfig)
    mock_config.is_active.return_value = True

    mock_auth = Mock()
    mock_auth.login.return_value = "https://idp.example.com/sso"

    service = SAMLService()

    with patch.object(service, '_prepare_saml_auth', return_value=mock_auth):
        url = service.initiate_login(mock_config, {'http_host': 'example.com'}, None)
        assert url == "https://idp.example.com/sso"


def test_saml_service_initiate_login_inactive_config(db_session: Session):
    """Test SAMLService.initiate_login raises error for inactive config."""
    from src.services.saml_service import SAMLService
    from fastapi import HTTPException

    mock_config = Mock(spec=SAMLConfig)
    mock_config.is_active.return_value = False

    service = SAMLService()

    with pytest.raises(HTTPException) as exc_info:
        service.initiate_login(mock_config, {}, None)

    assert exc_info.value.status_code == 400
    assert "not enabled" in exc_info.value.detail


def test_saml_service_process_response_success(db_session: Session):
    """Test SAMLService.process_response extracts user attributes."""
    from src.services.saml_service import SAMLService

    mock_config = Mock(spec=SAMLConfig)

    mock_auth = Mock()
    mock_auth.get_errors.return_value = []
    mock_auth.is_authenticated.return_value = True
    mock_auth.get_attributes.return_value = {'email': ['user@example.com']}
    mock_auth.get_nameid.return_value = 'user@example.com'
    mock_auth.get_session_index.return_value = 'session123'

    service = SAMLService()

    with patch.object(service, '_prepare_saml_auth', return_value=mock_auth):
        result = service.process_response(mock_config, {})

        assert result['name_id'] == 'user@example.com'
        assert result['attributes']['email'] == ['user@example.com']
        assert result['session_index'] == 'session123'


def test_saml_service_process_response_auth_failure(db_session: Session):
    """Test SAMLService.process_response raises error on auth failure."""
    from src.services.saml_service import SAMLService
    from fastapi import HTTPException

    mock_config = Mock(spec=SAMLConfig)

    mock_auth = Mock()
    mock_auth.get_errors.return_value = ['invalid_signature']
    mock_auth.get_last_error_reason.return_value = 'Invalid signature'

    service = SAMLService()

    with patch.object(service, '_prepare_saml_auth', return_value=mock_auth):
        with pytest.raises(HTTPException) as exc_info:
            service.process_response(mock_config, {})

        assert exc_info.value.status_code == 401


def test_saml_service_get_or_create_user_new_user(db_session: Session):
    """Test SAMLService.get_or_create_user creates new user."""
    from src.services.saml_service import SAMLService

    mock_config = Mock(spec=SAMLConfig)
    mock_config.id = "config1"
    mock_config.role_mapping = None

    # Mock attribute mapping
    mock_config.get_attribute_mapping.return_value = {
        'email': 'email',
        'full_name': 'displayName'
    }

    saml_data = {
        'name_id': 'newuser@example.com',
        'attributes': {
            'email': ['newuser@example.com'],
            'displayName': ['New User']
        }
    }

    service = SAMLService()

    # Mock db query to return None (user doesn't exist)
    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = None
    db_session.query.return_value = mock_query

    with patch.object(db_session, 'add') as mock_add:
        with patch.object(db_session, 'commit'):
            with patch.object(db_session, 'refresh'):
                user, is_new = service.get_or_create_user(db_session, saml_data, mock_config)

                assert is_new is True
                mock_add.assert_called_once()


def test_saml_service_get_or_create_user_existing_user(db_session: Session):
    """Test SAMLService.get_or_create_user returns existing user."""
    from src.services.saml_service import SAMLService

    mock_config = Mock(spec=SAMLConfig)
    mock_config.get_attribute_mapping.return_value = {'email': 'email', 'full_name': 'displayName'}

    existing_user = Mock(spec=User)
    existing_user.id = "existing123"
    existing_user.email = "existing@example.com"

    saml_data = {
        'name_id': 'existing@example.com',
        'attributes': {'email': ['existing@example.com'], 'displayName': ['Existing User']}
    }

    service = SAMLService()

    # Mock db query to return existing user
    mock_query = Mock()
    mock_query.filter.return_value.first.return_value = existing_user
    db_session.query.return_value = mock_query

    with patch.object(db_session, 'commit'):
        with patch.object(db_session, 'refresh'):
            user, is_new = service.get_or_create_user(db_session, saml_data, mock_config)

            assert is_new is False
            assert user.id == "existing123"


def test_saml_service_extract_attribute_simple(db_session: Session):
    """Test SAMLService._extract_attribute with simple key."""
    from src.services.saml_service import SAMLService

    service = SAMLService()
    attributes = {'email': ['user@example.com']}

    result = service._extract_attribute(attributes, 'email')
    assert result == 'user@example.com'


def test_saml_service_extract_attribute_list(db_session: Session):
    """Test SAMLService._extract_attribute with list value."""
    from src.services.saml_service import SAMLService

    service = SAMLService()
    attributes = {'groups': ['admin', 'user']}

    result = service._extract_attribute(attributes, 'groups')
    assert result == 'admin'


def test_saml_service_extract_attribute_concatenation(db_session: Session):
    """Test SAMLService._extract_attribute with concatenation."""
    from src.services.saml_service import SAMLService

    service = SAMLService()
    attributes = {
        'firstName': ['John'],
        'lastName': ['Doe']
    }

    result = service._extract_attribute(attributes, "firstName + ' ' + lastName")
    assert result == 'John Doe'


def test_saml_service_map_user_role_default(db_session: Session):
    """Test SAMLService._map_user_role returns default role."""
    from src.services.saml_service import SAMLService

    service = SAMLService()
    attributes = {'groups': ['users']}

    role = service._map_user_role(attributes, None)
    assert role == 'user'


def test_saml_service_map_user_role_with_mapping(db_session: Session):
    """Test SAMLService._map_user_role with role mapping."""
    from src.services.saml_service import SAMLService

    service = SAMLService()
    attributes = {'groups': ['admins', 'users']}

    role_mapping = {
        'admin': ['admins', 'superadmins'],
        'moderator': ['moderators']
    }

    role = service._map_user_role(attributes, role_mapping)
    assert role == 'admin'


def test_saml_service_initiate_logout_no_slo(db_session: Session):
    """Test SAMLService.initiate_logout returns None when SLO not configured."""
    from src.services.saml_service import SAMLService

    mock_config = Mock(spec=SAMLConfig)
    mock_config.idp_slo_url = None

    service = SAMLService()

    result = service.initiate_logout(mock_config, {}, 'user@example.com', 'session123')
    assert result is None


def test_saml_service_get_metadata_generates_xml(db_session: Session):
    """Test SAMLService.get_metadata generates XML."""
    from src.services.saml_service import SAMLService

    mock_config = Mock(spec=SAMLConfig)
    mock_config.sp_entity_id = "https://example.com/sp"
    mock_config.sp_acs_url = "https://example.com/api/auth/saml/acs"
    mock_config.sp_slo_url = "https://example.com/api/auth/saml/slo"
    mock_config.get_name_id_format.return_value = "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
    mock_config.get_security_config.return_value = {}

    service = SAMLService()

    with patch('src.services.saml_service.SAML_AVAILABLE', True):
        with patch('src.services.saml_service.OneLogin_Saml2_Metadata') as mock_metadata:
            mock_metadata.build.return_value = "<?xml version='1.0'?><EntityDescriptor/>"

            result = service.get_metadata(mock_config)

            assert "<?xml" in result
            mock_metadata.build.assert_called_once()


# ============================================================================
# SAML Config Helper Tests
# ============================================================================

def test_get_saml_config_from_env(client: TestClient, db_session: Session):
    """Test get_saml_config retrieves config from environment variable."""
    with patch('src.api.auth.saml.SAML_CONFIG_ID', 'config-id-123'):
        with patch('src.api.auth.saml.saml_service', Mock()):
            from src.api.auth.saml import get_saml_config

            # Create a mock SAML config in database
            mock_config = Mock(spec=SAMLConfig)
            mock_config.id = 'config-id-123'
            mock_config.enabled = True
            mock_config.is_active.return_value = True

            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = mock_config
            db_session.query.return_value = mock_query

            result = get_saml_config(db_session)
            assert result.id == 'config-id-123'


def test_get_saml_config_no_active_config(client: TestClient, db_session: Session):
    """Test get_saml_config raises error when no active config exists."""
    from fastapi import HTTPException
    from src.api.auth.saml import get_saml_config

    with patch('src.api.auth.saml.SAML_CONFIG_ID', None):
        # Mock query to return None (no active config)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        db_session.query.return_value = mock_query

        with pytest.raises(HTTPException) as exc_info:
            get_saml_config(db_session)

        assert exc_info.value.status_code == 501


def test_prepare_request_data_from_request(client: TestClient, db_session: Session):
    """Test prepare_request_data extracts correct data from FastAPI request."""
    from src.api.auth.saml import prepare_request_data
    from fastapi import Request

    # Create a mock request
    mock_request = Mock(spec=Request)
    mock_request.url = Mock()
    mock_request.url.hostname = "example.com"
    mock_request.url.port = 443
    mock_request.url.path = "/api/auth/saml/login"
    mock_request.url.scheme = "https"
    mock_request.url.query = "return_to=/dashboard"
    mock_request.query_params = {'return_to': '/dashboard'}

    async def mock_form():
        return {}
    mock_request.form = mock_form
    mock_request.method = "GET"

    # Get the event loop to run async function
    import asyncio
    request_data = asyncio.run(prepare_request_data(mock_request))

    assert request_data['http_host'] == 'example.com'
    assert request_data['script_name'] == '/api/auth/saml/login'
    assert request_data['server_port'] == 443
    assert request_data['https'] == 'on'


# ============================================================================
# Skeleton Tests (following test_admin.py pattern)
# ============================================================================

def test_saml_login_skeleton(client: TestClient, mocker):
    """Skeleton for SAML login tests."""
    # This is a placeholder following the pattern from test_admin.py
    # Will be expanded with more comprehensive tests
    assert True


def test_saml_acs_skeleton(client: TestClient, mocker):
    """Skeleton for SAML ACS tests."""
    assert True


def test_saml_metadata_skeleton(client: TestClient, mocker):
    """Skeleton for SAML metadata tests."""
    assert True


def test_saml_logout_skeleton(client: TestClient, mocker):
    """Skeleton for SAML logout tests."""
    assert True
