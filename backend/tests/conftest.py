import os
import sys
import warnings

import pytest
import redis
import redis.asyncio as redis_async
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from fakeredis import FakeRedis, FakeServer
from fakeredis import aioredis as fakeredis_aioredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set encryption key for tests
if not os.getenv("SESSION_ENCRYPTION_KEY"):
    os.environ["SESSION_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

# Set JWT secret for tests
if not os.getenv("JWT_SECRET"):
    os.environ["JWT_SECRET"] = "test_jwt_secret_key_for_testing_only"

# Add backend/src and project root to sys.path so tests can import all packages
backend_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, backend_root)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Third-party dependency noise (Python 3.12 deprecates audioop but shazamio/pydub still import it)
warnings.filterwarnings(
    "ignore",
    message="'audioop' is deprecated",
    category=DeprecationWarning,
)

# Pydantic v2: игнорируем предупреждения Config класс/orm_mode для совместимости.
try:
    import pydantic.warnings as pyd_warnings

    warnings.filterwarnings(
        "ignore",
        category=pyd_warnings.PydanticDeprecatedSince20,
    )
except Exception:
    pass

# Test Redis factory ---------------------------------------------------------


class _AwaitableFakeRedis(fakeredis_aioredis.FakeRedis):
    """fakeredis client that works with both sync and await callers."""

    def __await__(self):
        async def _inner():
            return self

        return _inner().__await__()


# Create shared in-memory Redis servers for sync/async code paths.
_FAKEREDIS_SERVER = FakeServer()
_TEST_SYNC_REDIS = FakeRedis(server=_FAKEREDIS_SERVER)
_TEST_ASYNC_REDIS = _AwaitableFakeRedis(
    server=_FAKEREDIS_SERVER,
    decode_responses=True,
    encoding="utf-8",
)


def _sync_from_url(*_args, **_kwargs):
    return _TEST_SYNC_REDIS


def _async_from_url(*_args, **_kwargs):
    return _TEST_ASYNC_REDIS


# Patch redis helpers at import time so any module importing redis uses fakeredis.
redis.from_url = _sync_from_url
redis.Redis.from_url = classmethod(lambda cls, *args, **kwargs: _TEST_SYNC_REDIS)
redis_async.from_url = _async_from_url
redis_async.Redis.from_url = classmethod(lambda cls, *args, **kwargs: _TEST_ASYNC_REDIS)


@pytest.fixture(autouse=True)
def reset_fake_redis_state():
    """Ensure fakeredis storage is cleared between tests."""

    _TEST_SYNC_REDIS.flushall()
    yield
    _TEST_SYNC_REDIS.flushall()

# Import Base from src.database to match models' Base
from src.database import Base

# Import all models to register them with Base.metadata
from src.models.user import User
from src.models.audit_log import AdminAuditLog
from src.models.telegram import TelegramAccount, Channel
from src.models.schedule import ScheduleSlot, ScheduleTemplate, Playlist
from src.models.playlist import PlaylistItem

test_db_url = None
test_engine = None
test_session_factory = None

@pytest.fixture(scope="function")
def db_session():
    """
    Creates a new database session for a test.
    """
    # Create unique temp file for each test
    import tempfile
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db_file.close()
    
    global test_db_url, test_engine
    test_db_url = f"sqlite:///{temp_db_file.name}"
    
    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    # expose the session factory for the client fixture so API requests get sessions bound to the same engine
    global test_session_factory
    test_session_factory = TestingSessionLocal
    
    # make app/database modules use the test engine/session factory
    # patch both 'src.database' and bare-module 'database' if present (app imports use both styles)
    try:
        import src.database as _database_module
        _database_module.engine = test_engine
        _database_module.SessionLocal = TestingSessionLocal
    except Exception:
        pass
    try:
        import database as _bare_database_module
        _bare_database_module.engine = test_engine
        _bare_database_module.SessionLocal = TestingSessionLocal
    except Exception:
        pass

    # Create tables for the models already imported above
    Base.metadata.create_all(bind=test_engine)
    
    session = TestingSessionLocal()

    # Create a default TelegramAccount and Channel so schedule tests referencing
    # a known TEST_CHANNEL_ID will find a channel. Use fixed UUID string so tests
    # relying on TEST_CHANNEL_ID can query it.
    try:
        from src.models.user import User
        from src.models.telegram import TelegramAccount, Channel
        import uuid

        u = User(email='test-owner@example.com', hashed_password='x', role='admin', status='approved')
        session.add(u)
        session.commit()
        session.refresh(u)

        account = TelegramAccount(user_id=u.id, phone='000000', encrypted_session='x', tg_user_id=12345)
        session.add(account)
        session.commit()
        session.refresh(account)

        # Create channel using the same fixed UUID used in tests
        channel_id = '12345678-1234-5678-1234-567812345678'
        ch = Channel(id=uuid.UUID(channel_id), account_id=account.id, chat_id=12345, name='Test Channel')
        session.add(ch)
        session.commit()
    except Exception:
        # If anything goes wrong, keep tests running; many tests may still pass
        # because they create their own channels
        pass

    # Wrap the synchronous SQLAlchemy Session so tests can use either
    # sync calls (session.commit()) or awaitable calls (await session.commit()).
    class _Awaitable:
        def __init__(self, value=None):
            self._value = value

        def __await__(self):
            async def _inner():
                return self._value
            return _inner().__await__()

    class _ExecAwaitable:
        def __init__(self, result):
            self._result = result

        def __await__(self):
            async def _inner():
                return self._result
            return _inner().__await__()

        def __getattr__(self, name):
            return getattr(self._result, name)

    class SessionShim:
        def __init__(self, session):
            self._session = session

        def add(self, obj):
            return self._session.add(obj)

        def commit(self):
            # perform immediate sync commit, return awaitable that resolves immediately
            res = self._session.commit()
            return _Awaitable(res)

        def rollback(self):
            res = self._session.rollback()
            return _Awaitable(res)

        def refresh(self, obj):
            res = self._session.refresh(obj)
            return _Awaitable(res)

        def delete(self, obj):
            res = self._session.delete(obj)
            return _Awaitable(res)

        def execute(self, *args, **kwargs):
            res = self._session.execute(*args, **kwargs)
            return _ExecAwaitable(res)

        def expire_all(self):
            return self._session.expire_all()

        def close(self):
            return self._session.close()

        def __getattr__(self, name):
            return getattr(self._session, name)

    shim_session = SessionShim(session)

    yield shim_session

    session.close()
    # Drop all tables
    Base.metadata.drop_all(bind=test_engine)
    
    # Clean up temp file
    import os
    try:
        os.unlink(temp_db_file.name)
    except Exception:
        pass

@pytest.fixture(scope="function")
def client(db_session):
    """
    Test client that uses the test database.
    """
    from src.main import app
    from src.database import get_db
    
    # Get the underlying session from the shim
    actual_session = db_session._session if hasattr(db_session, '_session') else db_session
    
    # override get_db to yield the same test session
    def _override_get_db():
        # Use the same session as db_session fixture for consistency
        # This ensures test modifications are visible to the API
        try:
            yield actual_session
        finally:
            pass  # Don't close - managed by db_session fixture

    # Override the get_db dependency directly
    app.dependency_overrides[get_db] = _override_get_db

    try:
        with TestClient(app) as client:
            yield client
    finally:
        # remove override
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
def async_client(db_session):
    """Compatibility fixture: provides an async-like client for tests.
    Uses a synchronous TestClient under the hood but exposes async methods
    (.get, .post, .put, .delete) so tests using `await async_client.get(...)`
    continue to work without requiring pytest-asyncio to await the fixture itself.
    """
    from src.main import app
    from fastapi.testclient import TestClient

    def _override_get_db():
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    # override all get_db callables used by routes
    overridden_keys = []
    for r in app.routes:
        if hasattr(r, 'dependant'):
            for d in r.dependant.dependencies:
                fn = getattr(d, 'call', None)
                if fn and getattr(fn, '__name__', None) == 'get_db':
                    app.dependency_overrides[fn] = _override_get_db
                    overridden_keys.append(fn)

    # create a synchronous TestClient bound to the test app
    client = TestClient(app)

    class AsyncLikeClient:
        def __init__(self, client):
            self._client = client

        async def get(self, *args, **kwargs):
            return self._client.get(*args, **kwargs)

        async def post(self, *args, **kwargs):
            return self._client.post(*args, **kwargs)

        async def put(self, *args, **kwargs):
            return self._client.put(*args, **kwargs)

        async def delete(self, *args, **kwargs):
            return self._client.delete(*args, **kwargs)

        # support context manager if needed
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

    try:
        yield AsyncLikeClient(client)
    finally:
        client.close()
        for k in overridden_keys:
            app.dependency_overrides.pop(k, None)


@pytest.fixture(scope="function")
def admin_auth_headers(db_session, request):
    """Create Authorization header for an admin user fixture (if provided by test).
    If the test provides an `admin_user` fixture, use it; otherwise create a quick admin user.
    """
    from src.auth.jwt import create_access_token
    # If test provides admin_user fixture, pytest will inject it; otherwise create one ad-hoc
    admin_user = None
    try:
        admin_user = request.getfixturevalue('admin_user')
    except Exception:
        from src.models.user import User, UserRole, UserStatus
        admin_user = User(email='admin@test', hashed_password='x', role=UserRole.ADMIN, status=UserStatus.APPROVED)
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    token = create_access_token(data={"sub": str(admin_user.id), "role": getattr(admin_user, 'role', 'admin')})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def user_auth_headers(db_session, request):
    from src.auth.jwt import create_access_token
    try:
        user = request.getfixturevalue('regular_user')
    except Exception:
        from src.models.user import User, UserRole, UserStatus
        user = User(email='user@test', hashed_password='x', role=UserRole.USER, status=UserStatus.APPROVED)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    token = create_access_token(data={"sub": str(user.id), "role": getattr(user, 'role', 'user')})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_user(db_session):
    from src.models.user import User, UserRole, UserStatus
    user = User(email='admin@test', hashed_password='x', role=UserRole.ADMIN, status=UserStatus.APPROVED)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def regular_user(db_session):
    from src.models.user import User, UserRole, UserStatus
    user = User(email='user@test', hashed_password='x', role=UserRole.USER, status=UserStatus.APPROVED)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user(regular_user):
    """Backward-compatible alias so tests using legacy fixture keep working."""
    return regular_user


@pytest.fixture(autouse=True)
def clear_rate_limit_storage():
    """Clear in-memory rate limit storage before and after each test to avoid cross-test pollution."""
    # _rate_limit_storage is implemented inside the dependencies module
    # depending on how it's imported in tests/app code the module path
    # may be 'src.api.auth.dependencies' or 'api.auth.dependencies'. Clear
    # both if present to ensure test isolation.
    try:
        import src.api.auth.dependencies as deps
        deps._rate_limit_storage.clear()
    except Exception:
        pass
    try:
        import api.auth.dependencies as bare_deps
        bare_deps._rate_limit_storage.clear()
    except Exception:
        pass
    yield
    try:
        import src.api.auth.dependencies as deps
        deps._rate_limit_storage.clear()
    except Exception:
        pass
    try:
        import api.auth.dependencies as bare_deps
        bare_deps._rate_limit_storage.clear()
    except Exception:
        pass


@pytest.fixture(scope="function")
def test_playlist(db_session, admin_user: User) -> Playlist:
    """Global test playlist fixture used in multiple model tests."""
    playlist = Playlist(
        name="Test Playlist",
        description="Playlist for testing",
        user_id=admin_user.id,
        items=[
            {"url": "https://youtube.com/watch?v=123", "title": "Test Video 1", "duration": 180},
            {"url": "https://youtube.com/watch?v=456", "title": "Test Video 2", "duration": 240},
        ],
    )
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)
    return playlist


