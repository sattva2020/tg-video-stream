"""
JWT authentication utilities for JSON-RPC WebSocket connections.
"""
import logging
import uuid
from typing import Optional

from jose import JWTError
from sqlalchemy.orm import Session

from auth import jwt as auth_jwt
from database import get_db
from src.models.user import User

logger = logging.getLogger(__name__)


def validate_websocket_token(token: str, db: Session) -> Optional[User]:
    """
    Validate JWT token for WebSocket connections and return the user.

    Args:
        token: JWT token string
        db: Database session

    Returns:
        User object if token is valid, None otherwise
    """
    if not token:
        logger.warning("WebSocket connection attempted without token")
        return None

    # Decode JWT token
    payload = auth_jwt.decode_access_token(token)
    if payload is None:
        logger.warning("Token decoding failed for WebSocket connection")
        return None

    # Extract user_id from payload
    user_id: str = payload.get("sub") or payload.get("user_id")
    if user_id is None:
        logger.warning("Token payload missing 'sub' or 'user_id'")
        return None

    # Validate UUID format
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid UUID in token: {user_id}")
        return None

    # Fetch user from database
    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        logger.warning(f"User not found for ID: {user_id}")
        return None

    logger.debug(f"WebSocket token validated for user: {user_id}")
    return user


def get_token_payload(token: str) -> Optional[dict]:
    """
    Extract payload from JWT token without database lookup.

    Args:
        token: JWT token string

    Returns:
        Token payload dict if valid, None otherwise
    """
    if not token:
        return None

    payload = auth_jwt.decode_access_token(token)
    return payload
