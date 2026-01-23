import pytest
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from models.user import User

def test_register_sets_pending(client, db_session):
    payload = {"email": "pending.user@example.com", "password": "GoodPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    # API should accept registration
    assert resp.status_code in (200, 201)

    # Verify DB entry status == 'pending'
    u = db_session.query(User).filter(User.email == payload['email']).first()
    assert u is not None, "User should be created in DB"
    assert u.status == 'pending'


def test_pending_user_blocked_login(client, db_session):
    # Create user directly with pending status
    u = User(email='blocked.user@example.com', hashed_password='fakehash', status='pending')
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    # Attempt login should be blocked (403)
    payload = {"email": "blocked.user@example.com", "password": "doesnotmatter"}
    r = client.post('/api/auth/login', json=payload)
    assert r.status_code == 403


def test_register_enqueues_notification(monkeypatch, client):
    called = {}

    def fake_notify(user_id):
        called['id'] = user_id
        return True

    # Patch the function where it is USED, not where it is defined, because of "from ... import ..."
    monkeypatch.setattr('api.auth.notify_admins_async', fake_notify)
    
    payload = {"email": "notify.user@example.com", "password": "GoodPassword123!"}
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code in (200, 201)
    assert 'id' in called
