"""
Вспомогательный скрипт для получения тестового JWT токена.
Создаёт тестового пользователя и генерирует токен для evaluation.
"""

import asyncio
import httpx
import os
import json
from pathlib import Path

from dotenv import load_dotenv

# Загрузить переменные окружения
load_dotenv(Path(__file__).parent / ".env.test")

BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")

# Тестовые credentials
TEST_USER_EMAIL = "test_eval@example.com"
TEST_USER_PASSWORD = "TestPassword123!"


async def get_test_token():
    """Получить JWT токен для тестирования."""
    
    async with httpx.AsyncClient() as client:
        # Попробовать войти с существующими credentials
        print(f"Attempting login as {TEST_USER_EMAIL}...")
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/auth/login",
                json={
                    "email": TEST_USER_EMAIL,
                    "password": TEST_USER_PASSWORD
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                print(f"✓ Login successful!")
                print(f"\nJWT Token:\n{token}\n")
                
                # Сохранить токен в env файл для runner
                env_file = Path(__file__).parent / ".env.test"
                with open(env_file, 'w') as f:
                    f.write(f"TEST_JWT_TOKEN={token}\n")
                    f.write(f"BACKEND_BASE_URL={BASE_URL}\n")
                print(f"✓ Token saved to {env_file}")
                
                return token
            
            elif response.status_code == 401:
                print(f"✗ Invalid credentials. Trying to register...")
                
                # Попробовать зарегистрировать нового пользователя
                reg_response = await client.post(
                    f"{BASE_URL}/api/auth/register",
                    json={
                        "email": TEST_USER_EMAIL,
                        "password": TEST_USER_PASSWORD
                    }
                )
                
                if reg_response.status_code in [200, 201]:
                    print(f"✓ User registered successfully!")
                    print(f"⚠ User status may be 'pending' - admin approval required")
                    print(f"   Manually approve user in admin panel or database")
                    return None
                else:
                    print(f"✗ Registration failed: {reg_response.status_code}")
                    print(f"   Response: {reg_response.text}")
                    return None
            
            else:
                print(f"✗ Unexpected status code: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return None


def main():
    """Точка входа."""
    print(f"Backend URL: {BASE_URL}")
    print(f"Test user: {TEST_USER_EMAIL}")
    print("-" * 60)
    
    token = asyncio.run(get_test_token())
    
    if token:
        print("\n" + "=" * 60)
        print("SUCCESS: Token obtained and saved!")
        print("You can now run: python collect_responses.py")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("MANUAL STEPS REQUIRED:")
        print("1. Start the backend server: cd backend && python -m src.main")
        print("2. Create test user or approve pending user")
        print("3. Run this script again to get token")
        print("=" * 60)


if __name__ == "__main__":
    main()
