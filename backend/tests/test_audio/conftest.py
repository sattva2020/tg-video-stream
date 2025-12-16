"""
Pytest fixtures для audio API тестов.

Предоставляет:
- Mock rust-transcoder client
- Mock database session
- Test user authentication
- FastAPI test client
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, AsyncMock, patch
import uuid

from tests.test_audio.test_app import app  # Test-specific app
from src.database import Base, get_db
from src.models.user import User
from src.models.playback_settings import PlaybackSettings
from services.auth_service import auth_service


# Test database (in-memory SQLite)
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Override FastAPI database dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password=auth_service.hash_password("testpassword123"),
        status="approved",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_settings(db_session, test_user):
    """Create test user playback settings."""
    settings = PlaybackSettings(
        user_id=test_user.id,
        speed=1.0,
        pitch_correction=False,
        equalizer_preset="flat",
        equalizer_custom=None,
        language="en",
        theme="system"
    )
    db_session.add(settings)
    db_session.commit()
    db_session.refresh(settings)
    return settings


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers with JWT token."""
    from services.auth_service import auth_service
    
    token = auth_service.create_access_token(
        data={"sub": str(test_user.id), "role": test_user.role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(override_get_db):
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for rust-transcoder calls."""
    mock_client = AsyncMock()
    
    # Default successful responses
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.json.return_value = {
        "session_id": "test-session-123",
        "message": "Transcoding started",
        "status": "processing"
    }
    mock_response.headers = {"content-type": "application/json"}
    
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_rust_transcoder(mock_httpx_client):
    """Patch httpx.AsyncClient to use mock."""
    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        yield mock_httpx_client
