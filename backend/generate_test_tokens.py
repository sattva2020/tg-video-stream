#!/usr/bin/env python3
"""
Helper scripts to generate JWT tokens for testing WebSocket authentication.
"""
import sys
import os
from datetime import datetime, timedelta, timezone
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from jose import jwt

# Try to load from .env file manually
env_path = os.path.join(os.path.dirname(__file__), '.env')
JWT_SECRET = "change_this_secure_jwt_secret"
ALGORITHM = "HS256"

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('JWT_SECRET='):
                JWT_SECRET = line.split('=', 1)[1].strip()
            elif line.startswith('ALGORITHM='):
                ALGORITHM = line.split('=', 1)[1].strip()


def generate_valid_token(user_id: str = None, expire_minutes: int = 15) -> str:
    """Generate a valid JWT token for testing."""
    if user_id is None:
        user_id = str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
        "type": "access",
        "iat": datetime.now(timezone.utc)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return token, payload


def generate_invalid_token() -> str:
    """Generate a token with invalid signature (wrong secret)."""
    payload = {
        "sub": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
    }

    # Use wrong secret to create invalid signature
    token = jwt.encode(payload, "wrong_secret", algorithm=ALGORITHM)
    return token


def generate_expired_token() -> str:
    """Generate an expired token."""
    user_id = str(uuid.uuid4())

    payload = {
        "sub": user_id,
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),  # Expired 1 minute ago
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(hours=1)
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return token, payload


def generate_malformed_token() -> str:
    """Generate a completely malformed token."""
    return "not.even.a.token"


def main():
    """Generate all test tokens."""
    print("="*70)
    print("JWT Test Token Generator")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  JWT_SECRET: {JWT_SECRET[:20]}...")
    print(f"  ALGORITHM: {ALGORITHM}\n")

    # Valid token
    print("1. VALID TOKEN (use for positive test)")
    print("-" * 70)
    valid_token, valid_payload = generate_valid_token()
    print(f"Token: {valid_token}")
    print(f"\nPayload:")
    for key, value in valid_payload.items():
        print(f"  {key}: {value}")
    print(f"\nTest command:")
    print(f'  wscat -c "ws://localhost:8000/api/ws/jsonrpc?token={valid_token}"')

    # Invalid token
    print("\n2. INVALID TOKEN (wrong signature - should be rejected)")
    print("-" * 70)
    invalid_token = generate_invalid_token()
    print(f"Token: {invalid_token}")
    print(f"\nTest command:")
    print(f'  wscat -c "ws://localhost:8000/api/ws/jsonrpc?token={invalid_token}"')

    # Expired token
    print("\n3. EXPIRED TOKEN (should be rejected)")
    print("-" * 70)
    expired_token, expired_payload = generate_expired_token()
    print(f"Token: {expired_token}")
    print(f"\nPayload:")
    for key, value in expired_payload.items():
        print(f"  {key}: {value}")
    print(f"\nTest command:")
    print(f'  wscat -c "ws://localhost:8000/api/ws/jsonrpc?token={expired_token}"')

    # Malformed token
    print("\n4. MALFORMED TOKEN (should be rejected)")
    print("-" * 70)
    malformed_token = generate_malformed_token()
    print(f"Token: {malformed_token}")
    print(f"\nTest command:")
    print(f'  wscat -c "ws://localhost:8000/api/ws/jsonrpc?token={malformed_token}"')

    # No token
    print("\n5. NO TOKEN (should be rejected)")
    print("-" * 70)
    print(f"Test command:")
    print(f'  wscat -c "ws://localhost:8000/api/ws/jsonrpc"')

    print("\n" + "="*70)
    print("Usage Examples")
    print("="*70)
    print("\nSave valid token to environment variable:")
    print(f'  export TOKEN="{valid_token}"')
    print(f'  wscat -c "ws://localhost:8000/api/ws/jsonrpc?token=$TOKEN"')
    print("\nOr copy token directly:")
    print(f'  wscat -c "ws://localhost:8000/api/ws/jsonrpc?token={valid_token}"')

    print("\n" + "="*70)
    print("Copy-Paste Ready Tokens")
    print("="*70)
    print(f"\n✅ VALID:\n{valid_token}")
    print(f"\n❌ INVALID:\n{invalid_token}")
    print(f"\n⏰ EXPIRED:\n{expired_token}")
    print(f"\n🔀 MALFORMED:\n{malformed_token}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Token generation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
