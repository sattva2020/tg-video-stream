"""
Скрипт для сбора ответов от audio API для evaluation.
Запускает тестовые запросы и сохраняет реальные ответы системы.
"""

import json
import asyncio
import httpx
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from dotenv import load_dotenv

# Загрузить переменные окружения
load_dotenv(Path(__file__).parent / ".env.test")

# Конфигурация
BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
QUERIES_FILE = Path(__file__).parent / "audio_test_queries.json"
RESPONSES_FILE = Path(__file__).parent / "audio_test_responses.json"

# Тестовый JWT токен (в реальности нужно получить через auth)
# Для тестов можно создать тестового пользователя или использовать mock
TEST_TOKEN = os.getenv("TEST_JWT_TOKEN", "")


async def load_queries() -> List[Dict[str, Any]]:
    """Загрузить тестовые запросы из JSON файла."""
    with open(QUERIES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


async def execute_query(client: httpx.AsyncClient, query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выполнить один тестовый запрос к API.
    
    Args:
        client: HTTP клиент
        query: Тестовый запрос с параметрами
        
    Returns:
        Словарь с результатами запроса
    """
    query_id = query.get("query_id")
    endpoint = query.get("endpoint")
    method = query.get("method", "GET").upper()
    payload = query.get("payload", {})
    query_params = query.get("query_params", {})
    
    url = f"{BASE_URL}{endpoint}"
    headers = {}
    
    # Добавить JWT токен если доступен
    if TEST_TOKEN:
        headers["Authorization"] = f"Bearer {TEST_TOKEN}"
    
    print(f"Executing {query_id}: {method} {endpoint}")
    
    try:
        # Выполнить запрос в зависимости от метода
        if method == "POST":
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
        elif method == "PUT":
            response = await client.put(url, json=payload, headers=headers, timeout=30.0)
        elif method == "GET":
            # Для streaming endpoint не пытаемся читать весь response
            if "stream" in endpoint:
                response = await client.get(url, params=query_params, headers=headers, timeout=30.0)
                # Читаем только первые несколько байт для проверки
                content_sample = await response.aread()
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content_length": len(content_sample),
                    "content_type": response.headers.get("content-type"),
                    "is_streaming": True
                }
            else:
                response = await client.get(url, params=query_params, headers=headers, timeout=30.0)
                response_data = {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                }
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        # Собрать результаты
        result = {
            "query_id": query_id,
            "endpoint": endpoint,
            "method": method,
            "timestamp": datetime.utcnow().isoformat(),
            "input": {
                "payload": payload,
                "query_params": query_params
            },
            "response": response_data if "stream" in endpoint else {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
            },
            "success": response.is_success,
            "execution_time_ms": None  # Можно добавить замеры времени
        }
        
        print(f"✓ {query_id}: Status {response.status_code}")
        return result
        
    except httpx.TimeoutException as e:
        print(f"✗ {query_id}: Timeout - {str(e)}")
        return {
            "query_id": query_id,
            "endpoint": endpoint,
            "method": method,
            "timestamp": datetime.utcnow().isoformat(),
            "input": {"payload": payload, "query_params": query_params},
            "response": None,
            "success": False,
            "error": f"Timeout: {str(e)}"
        }
    except Exception as e:
        print(f"✗ {query_id}: Error - {str(e)}")
        return {
            "query_id": query_id,
            "endpoint": endpoint,
            "method": method,
            "timestamp": datetime.utcnow().isoformat(),
            "input": {"payload": payload, "query_params": query_params},
            "response": None,
            "success": False,
            "error": str(e)
        }


async def collect_responses():
    """Собрать ответы для всех тестовых запросов."""
    print(f"Loading queries from {QUERIES_FILE}")
    queries = await load_queries()
    print(f"Found {len(queries)} test queries")
    
    responses = []
    
    async with httpx.AsyncClient() as client:
        for query in queries:
            result = await execute_query(client, query)
            responses.append(result)
            # Небольшая задержка между запросами
            await asyncio.sleep(0.5)
    
    # Сохранить результаты
    print(f"\nSaving responses to {RESPONSES_FILE}")
    with open(RESPONSES_FILE, 'w', encoding='utf-8') as f:
        json.dump(responses, f, indent=2, ensure_ascii=False)
    
    # Статистика
    success_count = sum(1 for r in responses if r.get("success"))
    print(f"\n{'='*60}")
    print(f"Response Collection Summary:")
    print(f"  Total queries: {len(responses)}")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {len(responses) - success_count}")
    print(f"  Responses saved to: {RESPONSES_FILE}")
    print(f"{'='*60}")


def main():
    """Точка входа."""
    if not QUERIES_FILE.exists():
        print(f"Error: Queries file not found: {QUERIES_FILE}")
        return
    
    if not TEST_TOKEN:
        print("Warning: TEST_JWT_TOKEN not set. API calls may fail due to authentication.")
        print("Set TEST_JWT_TOKEN environment variable or use mock authentication.")
    
    asyncio.run(collect_responses())


if __name__ == "__main__":
    main()
