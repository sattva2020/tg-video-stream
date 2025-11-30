import pytest
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.models.user import User
from services.auth_service import auth_service

def create_admin(db, email='admin@example.com', password='AdminPassword123!'):
    hashed = auth_service.hash_password(password)
    admin = User(email=email, hashed_password=hashed, role='admin', status='approved')
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def test_list_pending_users_and_approve(client, db_session):
    # Create admin
    admin = create_admin(db_session)
    token = auth_service.create_jwt_for_user(admin)

    # Create two users, one pending
    u1 = User(email='pending1@example.com', hashed_password=auth_service.hash_password('pass1'), status='pending')
    u2 = User(email='approved1@example.com', hashed_password=auth_service.hash_password('pass2'), status='approved')
    db_session.add(u1); db_session.add(u2); db_session.commit(); db_session.refresh(u1); db_session.refresh(u2)

    headers = { 'Authorization': f'Bearer {token}' }
    r = client.get('/api/admin/users?status=pending', headers=headers)
    assert r.status_code == 200
    data = r.json()
    items = data.get('items', data) if isinstance(data, dict) else data
    assert any(item['email'] == 'pending1@example.com' for item in items)

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


def test_reject_user_blocks_login(client, db_session):
    admin = create_admin(db_session)
    token = auth_service.create_jwt_for_user(admin)

    # Create a pending user
    u = User(email='to.reject@example.com', hashed_password=auth_service.hash_password('pass3'), status='pending')
    db_session.add(u); db_session.commit(); db_session.refresh(u)

    headers = { 'Authorization': f'Bearer {token}' }
    r = client.post(f'/api/admin/users/{u.id}/reject', headers=headers)
    assert r.status_code == 200
    assert r.json().get('new_status') == 'rejected'

    # Attempt login should be blocked
    login_resp = client.post('/api/auth/login', json={'email': 'to.reject@example.com', 'password': 'pass3'})
    assert login_resp.status_code == 403
