import pytest


def test_register_conflict_returns_structured_error(client, db_session):
    # Create existing user with a password to simulate already-registered email
    from models.user import User
    from services.auth_service import auth_service

    u = User(email='exist@example.com', hashed_password=auth_service.hash_password('ValidPass123!'), status='approved')
    db_session.add(u)
    db_session.commit()

    resp = client.post('/api/auth/register', json={'email': 'exist@example.com', 'password': 'ValidPass123!'})
    assert resp.status_code == 409
    payload = resp.json()
    assert 'code' in payload and payload['code'] == 'conflict'
    assert 'hint' in payload
    # Either server returned localized message or message_key for client-side localization
    assert ('message' in payload) or ('message_key' in payload)


def test_register_google_conflict_returns_link_required(client, db_session):
    from models.user import User

    u = User(email='google@example.com', google_id='google-1234', hashed_password=None, status='pending')
    db_session.add(u)
    db_session.commit()

    resp = client.post('/api/auth/register', json={'email': 'google@example.com', 'password': 'SomePassw0rd!'})
    assert resp.status_code == 409
    payload = resp.json()
    assert payload.get('link_required') is True
    assert payload.get('code') == 'conflict'
    assert payload.get('hint') == 'link_account'
    assert ('message' in payload) or ('message_key' in payload)


def test_login_pending_returns_structured_403(client, db_session):
    from models.user import User
    from services.auth_service import auth_service

    pwd = 'ValidPass123!'
    u = User(email='pending@example.com', hashed_password=auth_service.hash_password(pwd), status='pending')
    db_session.add(u)
    db_session.commit()

    resp = client.post('/api/auth/login', json={'email': 'pending@example.com', 'password': pwd})
    assert resp.status_code == 403
    payload = resp.json()
    assert payload.get('code') == 'pending'
    assert payload.get('hint') == 'contact_admin'
    assert ('message' in payload) or ('message_key' in payload)
