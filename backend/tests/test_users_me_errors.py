import pytest


def test_users_me_pending_returns_403_structured(client, db_session):
    from src.models.user import User
    from services.auth_service import auth_service

    u = User(email='me-pending@example.com', hashed_password=auth_service.hash_password('SomePassword1!'), status='pending')
    db_session.add(u)
    db_session.commit()

    # Create token for user (tests simulate possible scenario)
    token = auth_service.create_jwt_for_user(u)
    headers = {'Authorization': f'Bearer {token}'}

    resp = client.get('/api/users/me', headers=headers)
    assert resp.status_code == 403
    payload = resp.json()
    detail = payload.get('detail', payload)
    assert detail.get('code') == 'pending'
    assert detail.get('hint') == 'contact_admin'
    assert ('message' in detail) or ('message_key' in detail)


def test_users_me_rejected_returns_403_structured(client, db_session):
    from src.models.user import User
    from services.auth_service import auth_service

    u = User(email='rejected@example.com', hashed_password=auth_service.hash_password('SomePassword1!'), status='rejected')
    db_session.add(u)
    db_session.commit()

    token = auth_service.create_jwt_for_user(u)
    headers = {'Authorization': f'Bearer {token}'}

    resp = client.get('/api/users/me', headers=headers)
    assert resp.status_code == 403
    payload = resp.json()
    detail = payload.get('detail', payload)
    assert detail.get('code') == 'rejected'
    assert detail.get('hint') == 'contact_admin'
    assert ('message' in detail) or ('message_key' in detail)
