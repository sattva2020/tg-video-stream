import pyotp
from fastapi import status

from src.models.user import User
from src.services.auth_service import auth_service


def test_totp_setup_verify_and_disable(client, db_session, admin_auth_headers):
    # Setup: получить секрет и otpauth_url
    resp = client.post("/api/auth/totp/setup", headers=admin_auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    secret = data["secret"]
    assert secret
    assert "otpauth://" in data["otpauth_url"]

    # Verify: активировать 2FA
    code = pyotp.TOTP(secret).now()
    verify = client.post(
        "/api/auth/totp/verify",
        headers=admin_auth_headers,
        json={"code": code},
    )
    assert verify.status_code == status.HTTP_200_OK
    assert verify.json()["status"] == "enabled"

    # Убеждаемся, что в БД включен флаг
    db_session.expire_all()
    user = db_session.query(User).filter(User.email == "admin@test").first()
    assert user.totp_enabled is True
    assert user.totp_secret is not None

    # Disable: отключить с проверкой кода
    disable = client.post(
        "/api/auth/totp/disable",
        headers=admin_auth_headers,
        json={"code": pyotp.TOTP(secret).now()},
    )
    assert disable.status_code == status.HTTP_200_OK
    db_session.expire_all()
    user = db_session.query(User).filter(User.email == "admin@test").first()
    assert user.totp_enabled is False
    assert user.totp_secret is None


def test_login_requires_totp_when_enabled(client, db_session):
    password = "StrongPass123!"
    hashed = auth_service.hash_password(password)
    secret = pyotp.random_base32()

    user = User(
        email="2fa@test.com",
        hashed_password=hashed,
        status="approved",
        role="user",
        totp_secret=secret,
        totp_enabled=True,
    )
    db_session.add(user)
    db_session.commit()

    # Без кода должен быть отказ
    resp = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": password},
    )
    assert resp.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_422_UNPROCESSABLE_ENTITY}

    # С правильным кодом логин проходит
    code = pyotp.TOTP(secret).now()
    resp_ok = client.post(
        "/api/auth/login",
        json={"email": user.email, "password": password, "totp_code": code},
    )
    assert resp_ok.status_code == status.HTTP_200_OK
    body = resp_ok.json()
    assert body.get("access_token")
    assert body.get("token_type") == "bearer"
