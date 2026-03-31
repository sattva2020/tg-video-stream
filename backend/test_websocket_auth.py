#!/usr/bin/env python3
"""
Manual testing script for WebSocket JSON-RPC JWT authentication.

This script tests:
1. JWT token generation
2. WebSocket connection with valid token
3. WebSocket connection rejection with missing/invalid token
"""
import asyncio
import os
import sys
import uuid
from typing import Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import websockets
from jose import jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

JWT_SECRET = os.getenv("JWT_SECRET", "change_this_secure_jwt_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
WS_URL = "ws://localhost:8000/api/ws/jsonrpc"


def generate_test_token(user_id: Optional[str] = None, expire_minutes: int = 15) -> str:
    """Generate a test JWT token."""
    if user_id is None:
        user_id = str(uuid.uuid4())

    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": user_id,
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
        "type": "access"
    }

    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return token


def generate_invalid_token() -> str:
    """Generate an invalid token (wrong signature)."""
    payload = {
        "sub": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
    }
    # Use wrong secret
    return jwt.encode(payload, "wrong_secret", algorithm=ALGORITHM)


async def test_connection_with_token(url: str, token: Optional[str] = None, test_name: str = "Test"):
    """Test WebSocket connection with optional token."""
    if token:
        ws_url = f"{url}?token={token}"
        print(f"\n{'='*70}")
        print(f"{test_name}")
        print(f"{'='*70}")
        print(f"Connecting to: {ws_url[:70]}...")
        print(f"Token: {token[:30]}..." if len(token) > 30 else f"Token: {token}")
    else:
        ws_url = url
        print(f"\n{'='*70}")
        print(f"{test_name}")
        print(f"{'='*70}")
        print(f"Connecting to: {ws_url}")
        print(f"Token: None")

    try:
        async with websockets.connect(ws_url, close_timeout=5) as websocket:
            print(f"✅ Connection accepted!")
            print(f"Connection state: {websocket.state}")

            # Try to send a simple JSON-RPC ping
            ping_request = '{"jsonrpc": "2.0", "method": "get_stream_status", "params": {"channel_id": 123}, "id": 1}'
            print(f"\nSending JSON-RPC request: {ping_request}")
            await websocket.send(ping_request)

            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"📨 Received response: {response[:200]}...")
            except asyncio.TimeoutError:
                print("⏱️  No response received within 5 seconds (connection may be waiting)")

            await websocket.close()
            print(f"Connection closed gracefully")
            return True

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Connection rejected with status code: {e.status_code}")
        if hasattr(e, 'headers') and e.headers:
            print(f"   Headers: {dict(e.headers)}")
        if e.status_code == 1008:
            print(f"   Reason: Policy Violation (authentication failed)")
            return "rejected_auth"
        elif e.status_code == 4001:
            print(f"   Reason: Custom - Token expired")
            return "rejected_expired"
        return False

    except ConnectionRefusedError:
        print(f"❌ Connection refused - is the backend server running?")
        print(f"   Start it with: cd backend && uvicorn src.main:app --reload --port 8000")
        return False

    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all WebSocket authentication tests."""
    print("\n" + "="*70)
    print("WebSocket JSON-RPC JWT Authentication Tests")
    print("="*70)
    print(f"\nJWT_SECRET: {JWT_SECRET[:20]}...")
    print(f"ALGORITHM: {ALGORITHM}")
    print(f"WS_URL: {WS_URL}")

    # Test 1: Connection without token (should be rejected)
    result1 = await test_connection_with_token(
        WS_URL,
        token=None,
        test_name="Test 1: Connection WITHOUT token (should be rejected)"
    )

    # Test 2: Connection with invalid token (should be rejected)
    invalid_token = generate_invalid_token()
    result2 = await test_connection_with_token(
        WS_URL,
        token=invalid_token,
        test_name="Test 2: Connection with INVALID token (should be rejected)"
    )

    # Test 3: Connection with valid token (should be accepted)
    valid_token = generate_test_token()
    result3 = await test_connection_with_token(
        WS_URL,
        token=valid_token,
        test_name="Test 3: Connection with VALID token (should be accepted)"
    )

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Test 1 (No token):        {'✅ PASS' if result1 == 'rejected_auth' else '❌ FAIL'} - Rejected as expected")
    print(f"Test 2 (Invalid token):   {'✅ PASS' if result2 == 'rejected_auth' else '❌ FAIL'} - Rejected as expected")
    print(f"Test 3 (Valid token):     {'✅ PASS' if result3 is True else '❌ FAIL'} - Accepted as expected")

    all_passed = (result1 == 'rejected_auth' and
                  result2 == 'rejected_auth' and
                  result3 is True)

    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
