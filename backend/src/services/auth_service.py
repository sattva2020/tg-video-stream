from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer
import os

from models.user import User
from auth import jwt


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token serializer for password reset using the JWT secret
SECRET = os.getenv("JWT_SECRET")
if not SECRET:
    raise ValueError("JWT_SECRET must be set for token generation")

serializer = URLSafeTimedSerializer(SECRET)

class AuthService:
    def get_or_create_user(self, db: Session, user_info: dict) -> User:
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

        # If user doesn't exist and email is not taken, create a new user
        new_user = User(
            google_id=user_info["id"],
            email=user_info["email"],
            full_name=user_info.get("name"),
            profile_picture_url=user_info.get("picture"),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    def create_jwt_for_user(self, user: User) -> str:
        """
        Creates a JWT for a given user object.
        """
        access_token_data = {"sub": str(user.id)}
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

    def verify_password_reset_token(self, token: str, max_age: int = 3600) -> str | None:
        try:
            email = serializer.loads(token, salt="password-reset-salt", max_age=max_age)
            return email
        except Exception:
            return None

auth_service = AuthService()