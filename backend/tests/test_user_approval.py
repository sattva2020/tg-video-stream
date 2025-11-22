import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from main import app
from database import Base, get_db
from models.user import User

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_approval.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def cleanup():
    # remove all rows before/after each test
    db = TestingSessionLocal()
    db.query(User).delete()
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    db.query(User).delete()
    db.commit()
    db.close()


def test_register_sets_pending(client):
    payload = {"email": "pending.user@example.com", "password": "GoodPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    # API should accept registration
    assert resp.status_code in (200, 201)

    # Verify DB entry status == 'pending'
    db = TestingSessionLocal()
    u = db.query(User).filter(User.email == payload['email']).first()
    assert u is not None, "User should be created in DB"
    assert u.status == 'pending'
    db.close()


def test_pending_user_blocked_login(client):
    # Create user directly with pending status
    db = TestingSessionLocal()
    u = User(email='blocked.user@example.com', hashed_password='fakehash', status='pending')
    db.add(u)
    db.commit()
    db.refresh(u)
    db.close()

    # Attempt login should be blocked (403)
    payload = {"email": "blocked.user@example.com", "password": "doesnotmatter"}
    r = client.post('/api/auth/login', json=payload)
    assert r.status_code == 403


def test_register_enqueues_notification(monkeypatch, client):
    called = {}

    def fake_notify(user_id):
        called['id'] = user_id
        return True

    monkeypatch.setattr('tasks.notifications.notify_admins_async', fake_notify)
    payload = {"email": "notify.user@example.com", "password": "GoodPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code in (200, 201)
    assert 'id' in called
