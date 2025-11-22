import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from main import app
from database import Base, get_db
from models.user import User
from services.auth_service import auth_service

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_admin.db"
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
    db = TestingSessionLocal()
    db.query(User).delete()
    db.commit()
    db.close()
    yield
    db = TestingSessionLocal()
    db.query(User).delete()
    db.commit()
    db.close()


def create_admin(db, email='admin@example.com', password='AdminPassword123!'):
    hashed = auth_service.hash_password(password)
    admin = User(email=email, hashed_password=hashed, role='admin', status='approved')
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def test_list_pending_users_and_approve(client):
    db = TestingSessionLocal()
    # Create admin
    admin = create_admin(db)
    token = auth_service.create_jwt_for_user(admin)

    # Create two users, one pending
    u1 = User(email='pending1@example.com', hashed_password=auth_service.hash_password('pass1'), status='pending')
    u2 = User(email='approved1@example.com', hashed_password=auth_service.hash_password('pass2'), status='approved')
    db.add(u1); db.add(u2); db.commit(); db.refresh(u1); db.refresh(u2)

    headers = { 'Authorization': f'Bearer {token}' }
    r = client.get('/api/admin/users?status=pending', headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert any(item['email'] == 'pending1@example.com' for item in data)

    # Approve the pending user
    r2 = client.post(f'/api/admin/users/{u1.id}/approve', headers=headers)
    assert r2.status_code == 200
    assert r2.json().get('new_status') == 'approved'

    # Now try login for that user
    login_payload = { 'email': 'pending1@example.com', 'password': 'pass1' }
    login_resp = client.post('/api/auth/login', json=login_payload)
    # after approval, login should succeed -> 200
    assert login_resp.status_code == 200
    assert 'access_token' in login_resp.json()

    db.close()


def test_reject_user_blocks_login(client):
    db = TestingSessionLocal()
    admin = create_admin(db)
    token = auth_service.create_jwt_for_user(admin)

    # Create a pending user
    u = User(email='to.reject@example.com', hashed_password=auth_service.hash_password('pass3'), status='pending')
    db.add(u); db.commit(); db.refresh(u)

    headers = { 'Authorization': f'Bearer {token}' }
    r = client.post(f'/api/admin/users/{u.id}/reject', headers=headers)
    assert r.status_code == 200
    assert r.json().get('new_status') == 'rejected'

    # Attempt login should be blocked
    login_resp = client.post('/api/auth/login', json={'email': 'to.reject@example.com', 'password': 'pass3'})
    assert login_resp.status_code == 403

    db.close()
