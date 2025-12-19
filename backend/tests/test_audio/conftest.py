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
import os
from dotenv import load_dotenv
from sqlalchemy.pool import StaticPool

# Загрузить .env.test для тестов
test_env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env.test')
if os.path.exists(test_env_path):
    load_dotenv(test_env_path, override=True)
else:
    print("⚠️  Warning: .env.test not found, using default .env")

# Динамический импорт test_app для избежания проблем с путями
import sys
test_audio_dir = os.path.dirname(__file__)
if test_audio_dir not in sys.path:
    sys.path.insert(0, test_audio_dir)

from test_app import app  # Test-specific app
from src.database import Base, get_db as src_get_db
from src.models.user import User
from src.models.playback_settings import PlaybackSettings
from services.auth_service import auth_service


# Test database configuration
# По умолчанию тесты должны быть самодостаточными и не зависеть от внешней БД.
# Для интеграционных прогонов с PostgreSQL нужно ЯВНО включить флаг и задать URL.
TEST_USE_POSTGRES = os.getenv("TEST_USE_POSTGRES", "").strip().lower() in {"1", "true", "yes"}
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
DATABASE_URL = TEST_DATABASE_URL or os.getenv("DATABASE_URL") or "sqlite+pysqlite:///:memory:"

if TEST_USE_POSTGRES and DATABASE_URL.startswith("postgresql"):
    # PostgreSQL (интеграционные тесты) — включается только явно
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )
    try:
        db_host_hint = DATABASE_URL.split("@", 1)[1]
    except Exception:
        db_host_hint = "<masked>"
    print(f"✅ Тесты используют PostgreSQL (TEST_USE_POSTGRES=true): {db_host_hint}")
else:
    # SQLite in-memory для быстрых локальных прогонов
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    print("✅ Тесты используют SQLite in-memory (self-contained)")

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    # Создать таблицы если их нет (для первого запуска)
    Base.metadata.create_all(bind=engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        # Cleanup: удалить тестовые данные
        session.rollback()
        
        # Очистить только тестовые данные (по email паттерну)
        try:
            session.query(PlaybackSettings).filter(
                PlaybackSettings.user_id.in_(
                    session.query(User.id).filter(User.email.like('test%@example.com'))
                )
            ).delete(synchronize_session=False)
            
            session.query(User).filter(User.email.like('test%@example.com')).delete(synchronize_session=False)
            session.commit()
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
            session.rollback()
        finally:
            session.close()


@pytest.fixture(scope="function")
def override_get_db(db_session, test_user):
    """Override FastAPI database dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    
    def _override_get_current_user():
        return test_user
    
    from src.api.auth.dependencies import get_current_user as real_get_current_user

    # ВАЖНО: в кодовой базе встречаются оба варианта импорта get_db:
    # - `from database import get_db`
    # - `from src.database import get_db`
    # Это создаёт два разных объекта функции и без двойного override тесты
    # могут внезапно ходить в реальную БД.
    try:
        from database import get_db as root_get_db
        app.dependency_overrides[root_get_db] = _override_get_db
    except Exception as e:
        print(f"⚠️  Не удалось импортировать database.get_db для override: {e}")

    app.dependency_overrides[src_get_db] = _override_get_db
    app.dependency_overrides[real_get_current_user] = _override_get_current_user
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
    
    token = auth_service.create_jwt_for_user(test_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(override_get_db):
    """Create FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_httpx_client():
    """Mock httpx AsyncClient for rust-transcoder calls."""
    mock_client = AsyncMock()
    
    # ВАЖНО: response должен быть обычным Mock, не AsyncMock
    # потому что response.json() и response.raise_for_status() - синхронные методы в httpx
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.json = Mock(return_value={
        "session_id": "test-session-123",
        "message": "Transcoding started",
        "status": "processing"
    })
    mock_response.headers = {"content-type": "application/json"}
    mock_response.raise_for_status = Mock()  # Синхронный метод в httpx
    
    # post() и get() возвращают awaitable mock response
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value = mock_client  # Для async context manager
    mock_client.__aexit__.return_value = AsyncMock()
    
    return mock_client


@pytest.fixture
def mock_rust_transcoder(mock_httpx_client):
    """Patch httpx.AsyncClient to use mock."""
    # Patch для async context manager
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value = mock_httpx_client
        yield mock_httpx_client
