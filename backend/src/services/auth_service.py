from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
import os
from fastapi_mail import FastMail, MessageSchema
from pydantic import BaseModel

from models.user import User
from auth import jwt


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token serializer for password reset using the JWT secret
SECRET = os.getenv("JWT_SECRET")
if not SECRET:
    raise ValueError("JWT_SECRET must be set for token generation")

serializer = URLSafeTimedSerializer(SECRET)

class ResetEmail(BaseModel):
    email: str
    token: str

def send_password_reset_email_sendgrid(to: str, token: str):
    # This helper uses FastAPI-Mail if SMTP configured; otherwise logs token for dev
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        # dev mode - return token so caller can show it or log
        return None
    fm = FastMail(
        config={
            "MAIL_USERNAME": os.getenv("SMTP_USER"),
            "MAIL_PASSWORD": os.getenv("SMTP_PASS"),
            "MAIL_FROM": os.getenv("SMTP_FROM", "no-reply@example.com"),
            "MAIL_PORT": int(os.getenv("SMTP_PORT", 587)),
            "MAIL_SERVER": smtp_host,
            "MAIL_TLS": True,
            "MAIL_SSL": False
        }
    )
    message = MessageSchema(
        subject="Password Reset",
        recipients=[to],
        body=f"Reset token: {token}",
        subtype="plain"
    )
    fm.send_message(message)
    return True

def send_account_link_email(to: str, token: str):
    # In production, we will send a proper HTML email with a link
    # For development we return None and allow the caller to return token
    smtp_host = os.getenv("SMTP_HOST")
    if not smtp_host:
        return None
    # Build simple message for now
    fm = FastMail(
        config={
            "MAIL_USERNAME": os.getenv("SMTP_USER"),
            "MAIL_PASSWORD": os.getenv("SMTP_PASS"),
            "MAIL_FROM": os.getenv("SMTP_FROM", "no-reply@example.com"),
            "MAIL_PORT": int(os.getenv("SMTP_PORT", 587)),
            "MAIL_SERVER": smtp_host,
            "MAIL_TLS": True,
            "MAIL_SSL": False
        }
    )
    message = MessageSchema(
        subject="Link your account",
        recipients=[to],
        body=f"Link token: {token}",
        subtype="plain"
    )
    fm.send_message(message)
    return True

class AuthService:
    def get_or_create_user(self, db: Session, user_info: dict) -> tuple[User, bool]:
        """
        Retrieves a user based on Google ID, or creates a new one if they don't exist.
        Also handles the edge case where the email is already in use.
        """
        # Check if a user with this google_id already exists
        user = db.query(User).filter(User.google_id == user_info["id"]).first()
        if user:
            # Update user info on login
            user.full_name = user_info.get("name")
            user.profile_picture_url = user_info.get("picture")
            db.commit()
            db.refresh(user)
            return user

        # If no user with that google_id, check if the email is already in use
        existing_user_with_email = db.query(User).filter(User.email == user_info["email"]).first()
        if existing_user_with_email:
            # This email is taken by a non-Google account.
            # As per ECR-001, we must block this.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Please sign in with your original method.",
            )

        # If user doesn't exist and email is not taken, create a new user.
        # New users created via OAuth should be pending until an admin approves them.
        new_user = User(
            google_id=user_info["id"],
            email=user_info["email"],
            full_name=user_info.get("name"),
            profile_picture_url=user_info.get("picture"),
            status='pending'
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user, True

    def create_jwt_for_user(self, user: User) -> str:
        """
        Creates a JWT for a given user object.
        """
        access_token_data = {"sub": str(user.id), "role": user.role}
        access_token = jwt.create_access_token(data=access_token_data)
        return access_token

    # Password helpers
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    # Password reset token helpers
    def generate_password_reset_token(self, email: str) -> str:
        return serializer.dumps(email, salt="password-reset-salt")

    def generate_link_account_token(self, email: str) -> str:
        return serializer.dumps(email, salt="link-account-salt")

    def generate_email_verification_token(self, email: str) -> str:
        return serializer.dumps(email, salt="email-verify-salt")

    def verify_password_reset_token(self, token: str, max_age: int = 3600) -> str | None:
        try:
            email = serializer.loads(token, salt="password-reset-salt", max_age=max_age)
            return email
        except Exception:
            return None

    def verify_link_account_token(self, token: str, max_age: int = 3600) -> str | None:
        try:
            email = serializer.loads(token, salt="link-account-salt", max_age=max_age)
            return email
        except Exception:
            return None

    def verify_email_verification_token(self, token: str, max_age: int = 3600) -> str | None:
        try:
            email = serializer.loads(token, salt="email-verify-salt", max_age=max_age)
            return email
        except Exception:
            return None

    def send_password_reset_email(self, to: str, token: str):
        """Convenience wrapper to send password reset email via configured provider.

        For now delegates to send_password_reset_email_sendgrid which returns None in dev mode
        and True when sending succeeds.
        """
        return send_password_reset_email_sendgrid(to, token)

    def send_account_link_email(self, to: str, token: str):
        return send_account_link_email(to, token)

    def send_email_verification(self, to: str, token: str):
        # Reuse send_account_link_email for now; we will swap templates later
        return send_account_link_email(to, token)

auth_service = AuthService()

def _password_policy_regex():
    # At least 12 chars, upper, lower, digit, special
    import re
    return re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$')

def check_password_policy(password: str) -> bool:
    return bool(_password_policy_regex().match(password))

def is_password_pwned(password: str) -> bool:
    # Use HaveIBeenPwned k-anonymity API - no extra deps
    import hashlib
    import requests

    sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    prefix = sha1[:5]
    suffix = sha1[5:]
    url = f'https://api.pwnedpasswords.com/range/{prefix}'
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return False
        lines = resp.text.splitlines()
        for line in lines:
            if line.split(':')[0] == suffix:
                return True
        return False
    except Exception:
        # If external check fails, treat as not pwned (but log)
        return False