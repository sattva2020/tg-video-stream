import pytest


def test_register_conflict_returns_structured_error(client, db_session):
    # Create existing user with a password to simulate already-registered email
    from src.models.user import User
    from services.auth_service import auth_service

    u = User(email='exist@example.com', hashed_password=auth_service.hash_password('ValidPass123!'), status='approved')
    db_session.add(u)
    db_session.commit()

    resp = client.post('/api/auth/register', json={'email': 'exist@example.com', 'password': 'ValidPass123!'})
    assert resp.status_code == 409
    payload = resp.json()
    assert 'code' in payload['detail'] and payload['detail']['code'] == 'conflict'
    assert 'hint' in payload['detail']
    # Either server returned localized message or message_key for client-side localization
    assert ('message' in payload['detail']) or ('message_key' in payload['detail'])


def test_register_conflict_returns_localized_message_when_accept_language_ru(client, db_session):
    # create existing user
    from src.models.user import User
    from services.auth_service import auth_service

    u = User(email='exist2@example.com', hashed_password=auth_service.hash_password('ValidPass123!'), status='approved')
    db_session.add(u)
    db_session.commit()

    resp = client.post('/api/auth/register', json={'email': 'exist2@example.com', 'password': 'ValidPass123!'}, headers={'accept-language': 'ru'})
    assert resp.status_code == 409
    payload = resp.json()
    detail = payload.get('detail', payload)
    assert 'code' in detail and detail['code'] == 'conflict'
    # when Accept-Language: ru server should return localized `message`
    assert 'message' in detail and isinstance(detail['message'], str)


def test_register_google_conflict_returns_link_required(client, db_session):
    from src.models.user import User

    u = User(email='google@example.com', google_id='google-1234', hashed_password=None, status='pending')
    db_session.add(u)
    db_session.commit()

    resp = client.post('/api/auth/register', json={'email': 'google@example.com', 'password': 'SomePassw0rd!'})
    assert resp.status_code == 409
    payload = resp.json()
    detail = payload.get('detail', payload)
    assert detail.get('link_required') is True
    assert detail.get('code') == 'conflict'
    assert detail.get('hint') == 'link_account'
    assert ('message' in detail) or ('message_key' in detail)


def test_login_pending_returns_structured_403(client, db_session):
    from src.models.user import User
    from services.auth_service import auth_service

    pwd = 'ValidPass123!'
    u = User(email='pending@example.com', hashed_password=auth_service.hash_password(pwd), status='pending')
    db_session.add(u)
    db_session.commit()

    resp = client.post('/api/auth/login', json={'email': 'pending@example.com', 'password': pwd})
    assert resp.status_code == 403
    payload = resp.json()
    detail = payload.get('detail', payload)
    assert detail.get('code') == 'pending'
    assert detail.get('hint') == 'contact_admin'
    assert ('message' in detail) or ('message_key' in detail)


def test_login_pending_returns_localized_message_when_accept_language_ru(client, db_session):
    from src.models.user import User
    from services.auth_service import auth_service

    pwd = 'ValidPass123!'
    u = User(email='pending2@example.com', hashed_password=auth_service.hash_password(pwd), status='pending')
    db_session.add(u)
    db_session.commit()

    resp = client.post('/api/auth/login', json={'email': 'pending2@example.com', 'password': pwd}, headers={'accept-language': 'ru'})
    assert resp.status_code == 403
    payload = resp.json()
    detail = payload.get('detail', payload)
    assert detail.get('code') == 'pending'
    assert detail.get('hint') == 'contact_admin'
    # Expect server to return localized message when Accept-Language requests ru
    assert 'message' in detail and isinstance(detail['message'], str)
