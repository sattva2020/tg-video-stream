import pytest


@pytest.mark.xfail(reason="Migration to always-provide message_key is not enabled yet; flip when migrating to MUST", strict=False)
def test_auth_error_includes_message_key_for_conflict(client, db_session):
    """Contract test for planned migration: ensure server includes message_key for conflict responses.

    This test is marked xfail — it will be turned green (unmarked) when the team agrees to require
    `message_key` in responses and the server is switched to the stricter behavior.
    """
    # prepare existing user
    from src.models.user import User
    from services.auth_service import auth_service

    u = User(email='migrate@example.com', hashed_password=auth_service.hash_password('ValidPass123!'), status='approved')
    db_session.add(u)
    db_session.commit()

    resp = client.post('/api/auth/register', json={'email': 'migrate@example.com', 'password': 'ValidPass123!'})
    assert resp.status_code == 409
    payload = resp.json()

    # EXPECTATION UNDER MIGRATION: message_key should be present (xfail until enabled)
    assert 'message_key' in payload
