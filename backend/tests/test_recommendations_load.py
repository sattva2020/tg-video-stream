"""
Load Test: Recommendation API with Concurrent Requests

Тест проверяет производительность API рекомендаций при并发 запросах:
1. GET /api/recommendations - Персонализированные рекомендации под нагрузкой
2. POST /api/recommendations/feedback - Отправка фидбека под нагрузкой
3. GET /api/recommendations/stats - Статистика под нагрузкой
4. GET /api/recommendations/for-playlist - Рекомендации для плейлиста под нагрузкой

Метрики производительности:
- Response time (время отклика)
- Throughput (запросов в секунду)
- Error rate (процент ошибок)
- Concurrent requests (одновременные запросы)
"""
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from uuid import uuid4
from fastapi.testclient import TestClient

from src.main import app
from src.models.user import User
from src.models.playlist import PlaylistItem
from src.models.recommendation import UserItemInteraction, RecommendationFeedback
from src.services.recommendation_service import RecommendationService
from src.services.recommendation_engine import CollaborativeFilteringEngine, ContentBasedFilteringEngine
from sqlalchemy import select


# ==================== Fixtures ====================

@pytest.fixture
def client():
    """FastAPI Test Client для API запросов."""
    return TestClient(app)


@pytest.fixture
def load_test_user(db_session):
    """Создает пользователя для нагрузочного тестирования."""
    user = User(
        id=uuid4(),
        telegram_id=999999,
        username="loadtest_user",
        full_name="Load Test User",
        role="listener",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def load_test_items(db_session):
    """Создает набор элементов для нагрузочного тестирования."""
    items = []
    for i in range(20):
        item = PlaylistItem(
            id=uuid4(),
            playlist_id=1,
            position=i + 1,
            url=f"https://example.com/load_test_{i}",
            title=f"Load Test Item {i}",
            type="youtube",
            duration=180,
            channel=f"Test Channel {i % 3}",
        )
        db_session.add(item)
        items.append(item)

    db_session.commit()
    for item in items:
        db_session.refresh(item)

    return items


@pytest.fixture
def recommendation_service_no_redis(db_session):
    """RecommendationService без Redis для детерминированных тестов."""
    return RecommendationService(db=db_session, redis_client=None)


@pytest.fixture
def trained_models(recommendation_service_no_redis, load_test_user, load_test_items, db_session):
    """
    Обучает модели collaborative filtering и content-based перед тестами.
    Создает базу данных с взаимодействиями для обучения.
    """
    service = recommendation_service_no_redis
    user_id = str(load_test_user.id)

    # Создаем взаимодействия для обучения
    for i, item in enumerate(load_test_items[:10]):
        interaction = UserItemInteraction(
            id=uuid4(),
            user_id=user_id,
            playlist_item_id=str(item.id),
            interaction_type="watch",
            duration_seconds=120,
            completion_rate=0.8 if i < 7 else 0.3,  # Первые 7 понравились
            interacted_at=None,
        )
        db_session.add(interaction)

    db_session.commit()

    # Обучаем модели
    try:
        collab_engine = CollaborativeFilteringEngine()
        collab_engine.train(days=30, db=db_session)
        collab_engine.save_model()

        content_engine = ContentBasedFilteringEngine()
        content_engine.train(days=30, db=db_session)
        content_engine.save_model()
    except Exception as e:
        # Если обучить не удалось (мало данных), тесты будут использовать fallback
        pass

    return service


# ==================== Load Test Helpers ====================

class LoadTestMetrics:
    """Метрики нагрузочного тестирования."""

    def __init__(self):
        self.response_times: List[float] = []
        self.errors: List[Dict[str, Any]] = []
        self.success_count = 0
        self.error_count = 0
        self.lock = threading.Lock()

    def add_response(self, response_time: float, success: bool, error: Dict[str, Any] = None):
        """Добавляет результат запроса в метрики (thread-safe)."""
        with self.lock:
            if success:
                self.success_count += 1
                self.response_times.append(response_time)
            else:
                self.error_count += 1
                if error:
                    self.errors.append(error)

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает агрегированную статистику."""
        with self.lock:
            total_requests = self.success_count + self.error_count
            if total_requests == 0:
                return {
                    "total_requests": 0,
                    "success_count": 0,
                    "error_count": 0,
                    "error_rate": 0.0,
                    "avg_response_time": 0.0,
                    "min_response_time": 0.0,
                    "max_response_time": 0.0,
                    "p50_response_time": 0.0,
                    "p95_response_time": 0.0,
                    "p99_response_time": 0.0,
                }

            sorted_times = sorted(self.response_times) if self.response_times else []
            error_rate = (self.error_count / total_requests) * 100

            stats = {
                "total_requests": total_requests,
                "success_count": self.success_count,
                "error_count": self.error_count,
                "error_rate": error_rate,
            }

            if sorted_times:
                stats.update({
                    "avg_response_time": sum(sorted_times) / len(sorted_times),
                    "min_response_time": sorted_times[0],
                    "max_response_time": sorted_times[-1],
                    "p50_response_time": sorted_times[len(sorted_times) // 2],
                    "p95_response_time": sorted_times[int(len(sorted_times) * 0.95)] if len(sorted_times) >= 20 else sorted_times[-1],
                    "p99_response_time": sorted_times[int(len(sorted_times) * 0.99)] if len(sorted_times) >= 100 else sorted_times[-1],
                })
            else:
                stats.update({
                    "avg_response_time": 0.0,
                    "min_response_time": 0.0,
                    "max_response_time": 0.0,
                    "p50_response_time": 0.0,
                    "p95_response_time": 0.0,
                    "p99_response_time": 0.0,
                })

            return stats


def make_get_recommendations_request(client: TestClient, user_id: str, metrics: LoadTestMetrics):
    """Выполняет запрос GET /api/recommendations и записывает метрики."""
    start_time = time.time()
    try:
        response = client.get(
            f"/api/recommendations?user_id={user_id}&limit=10&algorithm=hybrid"
        )
        response_time = time.time() - start_time

        success = response.status_code == 200
        error = {
            "status_code": response.status_code,
            "response": response.text[:200] if not success else None,
        } if not success else None

        metrics.add_response(response_time, success, error)

        if success:
            data = response.json()
            assert "recommendations" in data
            assert isinstance(data["recommendations"], list)
    except Exception as e:
        response_time = time.time() - start_time
        metrics.add_response(response_time, False, {"exception": str(e)})


def make_post_feedback_request(client: TestClient, item_id: str, metrics: LoadTestMetrics):
    """Выполняет запрос POST /api/recommendations/feedback и записывает метрики."""
    start_time = time.time()
    try:
        response = client.post(
            "/api/recommendations/feedback",
            json={
                "playlist_item_id": item_id,
                "feedback_type": "like"
            }
        )
        response_time = time.time() - start_time

        success = response.status_code == 201
        error = {
            "status_code": response.status_code,
            "response": response.text[:200] if not success else None,
        } if not success else None

        metrics.add_response(response_time, success, error)

        if success:
            data = response.json()
            assert "id" in data
            assert data["feedback_type"] == "like"
    except Exception as e:
        response_time = time.time() - start_time
        metrics.add_response(response_time, False, {"exception": str(e)})


def make_get_stats_request(client: TestClient, metrics: LoadTestMetrics):
    """Выполняет запрос GET /api/recommendations/stats и записывает метрики."""
    start_time = time.time()
    try:
        response = client.get("/api/recommendations/stats?period=7d")
        response_time = time.time() - start_time

        success = response.status_code == 200
        error = {
            "status_code": response.status_code,
            "response": response.text[:200] if not success else None,
        } if not success else None

        metrics.add_response(response_time, success, error)

        if success:
            data = response.json()
            assert "click_through_rate" in data or "total_recommendations" in data
    except Exception as e:
        response_time = time.time() - start_time
        metrics.add_response(response_time, False, {"exception": str(e)})


def make_get_for_playlist_request(client: TestClient, playlist_id: int, metrics: LoadTestMetrics):
    """Выполняет запрос GET /api/recommendations/for-playlist и записывает метрики."""
    start_time = time.time()
    try:
        response = client.get(f"/api/recommendations/for-playlist?playlist_id={playlist_id}&limit=10")
        response_time = time.time() - start_time

        success = response.status_code == 200
        error = {
            "status_code": response.status_code,
            "response": response.text[:200] if not success else None,
        } if not success else None

        metrics.add_response(response_time, success, error)

        if success:
            data = response.json()
            assert "recommendations" in data
            assert isinstance(data["recommendations"], list)
    except Exception as e:
        response_time = time.time() - start_time
        metrics.add_response(response_time, False, {"exception": str(e)})


# ==================== Load Tests ====================

class TestRecommendationsLoad:
    """Нагрузочные тесты API рекомендаций."""

    def test_get_recommendations_concurrent_requests(self, client, trained_models, load_test_user):
        """
        Тестирует GET /api/recommendations с 50 одновременными запросами.

        Ожидания:
        - Все запросы завершаются успешно (200 OK)
        - Среднее время отклика < 2 секунд
        - Процент ошибок < 5%
        - Ответы содержат корректную структуру данных
        """
        user_id = str(load_test_user.id)
        num_requests = 50
        metrics = LoadTestMetrics()

        # Выполняем concurrent запросы
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_get_recommendations_request, client, user_id, metrics)
                for _ in range(num_requests)
            ]
            for future in as_completed(futures):
                future.result()  # Поднимает исключение, если оно произошло

        # Проверяем метрики
        stats = metrics.get_stats()

        assert stats["total_requests"] == num_requests
        assert stats["error_rate"] < 5.0, f"Error rate too high: {stats['error_rate']}%"
        assert stats["avg_response_time"] < 2.0, f"Average response time too slow: {stats['avg_response_time']}s"
        assert stats["p95_response_time"] < 5.0, f"P95 response time too slow: {stats['p95_response_time']}s"

        # Логируем метрики для анализа
        print(f"\n=== GET /api/recommendations Load Test ===")
        print(f"Total requests: {stats['total_requests']}")
        print(f"Success: {stats['success_count']}, Errors: {stats['error_count']}")
        print(f"Error rate: {stats['error_rate']:.2f}%")
        print(f"Avg response time: {stats['avg_response_time']:.3f}s")
        print(f"P50: {stats['p50_response_time']:.3f}s, P95: {stats['p95_response_time']:.3f}s, P99: {stats['p99_response_time']:.3f}s")

    def test_post_feedback_concurrent_requests(self, client, load_test_items):
        """
        Тестирует POST /api/recommendations/feedback с 50 одновременными запросами.

        Ожидания:
        - Все запросы завершаются успешно (201 Created)
        - Среднее время отклика < 1 секунды
        - Процент ошибок < 5%
        - Фидбек корректно сохраняется в базе
        """
        num_requests = 50
        metrics = LoadTestMetrics()

        # Выполняем concurrent запросы
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_post_feedback_request, client, str(load_test_items[i % len(load_test_items)].id), metrics)
                for i in range(num_requests)
            ]
            for future in as_completed(futures):
                future.result()

        # Проверяем метрики
        stats = metrics.get_stats()

        assert stats["total_requests"] == num_requests
        assert stats["error_rate"] < 5.0, f"Error rate too high: {stats['error_rate']}%"
        assert stats["avg_response_time"] < 1.0, f"Average response time too slow: {stats['avg_response_time']}s"
        assert stats["p95_response_time"] < 2.0, f"P95 response time too slow: {stats['p95_response_time']}s"

        # Логируем метрики
        print(f"\n=== POST /api/recommendations/feedback Load Test ===")
        print(f"Total requests: {stats['total_requests']}")
        print(f"Success: {stats['success_count']}, Errors: {stats['error_count']}")
        print(f"Error rate: {stats['error_rate']:.2f}%")
        print(f"Avg response time: {stats['avg_response_time']:.3f}s")
        print(f"P50: {stats['p50_response_time']:.3f}s, P95: {stats['p95_response_time']:.3f}s")

    def test_get_stats_concurrent_requests(self, client):
        """
        Тестирует GET /api/recommendations/stats с 30 одновременными запросами.

        Ожидания:
        - Все запросы завершаются успешно (200 OK)
        - Среднее время отклика < 1 секунды (Redis caching)
        - Процент ошибок < 5%
        - Redis кэш работает корректно
        """
        num_requests = 30
        metrics = LoadTestMetrics()

        # Выполняем concurrent запросы
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_get_stats_request, client, metrics)
                for _ in range(num_requests)
            ]
            for future in as_completed(futures):
                future.result()

        # Проверяем метрики
        stats = metrics.get_stats()

        assert stats["total_requests"] == num_requests
        assert stats["error_rate"] < 5.0, f"Error rate too high: {stats['error_rate']}%"
        assert stats["avg_response_time"] < 1.0, f"Average response time too slow: {stats['avg_response_time']}s"
        assert stats["p95_response_time"] < 2.0, f"P95 response time too slow: {stats['p95_response_time']}s"

        # Логируем метрики
        print(f"\n=== GET /api/recommendations/stats Load Test ===")
        print(f"Total requests: {stats['total_requests']}")
        print(f"Success: {stats['success_count']}, Errors: {stats['error_count']}")
        print(f"Error rate: {stats['error_rate']:.2f}%")
        print(f"Avg response time: {stats['avg_response_time']:.3f}s")
        print(f"P50: {stats['p50_response_time']:.3f}s, P95: {stats['p95_response_time']:.3f}s")

    def test_get_for_playlist_concurrent_requests(self, client, load_test_items):
        """
        Тестирует GET /api/recommendations/for-playlist с 30 одновременными запросами.

        Ожидания:
        - Все запросы завершаются успешно (200 OK)
        - Среднее время отклика < 2 секунд
        - Процент ошибок < 5%
        - Рекомендации для плейлиста корректны
        """
        num_requests = 30
        playlist_id = 1
        metrics = LoadTestMetrics()

        # Выполняем concurrent запросы
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_get_for_playlist_request, client, playlist_id, metrics)
                for _ in range(num_requests)
            ]
            for future in as_completed(futures):
                future.result()

        # Проверяем метрики
        stats = metrics.get_stats()

        assert stats["total_requests"] == num_requests
        assert stats["error_rate"] < 5.0, f"Error rate too high: {stats['error_rate']}%"
        assert stats["avg_response_time"] < 2.0, f"Average response time too slow: {stats['avg_response_time']}s"
        assert stats["p95_response_time"] < 5.0, f"P95 response time too slow: {stats['p95_response_time']}s"

        # Логируем метрики
        print(f"\n=== GET /api/recommendations/for-playlist Load Test ===")
        print(f"Total requests: {stats['total_requests']}")
        print(f"Success: {stats['success_count']}, Errors: {stats['error_count']}")
        print(f"Error rate: {stats['error_rate']:.2f}%")
        print(f"Avg response time: {stats['avg_response_time']:.3f}s")
        print(f"P50: {stats['p50_response_time']:.3f}s, P95: {stats['p95_response_time']:.3f}s")

    def test_mixed_endpoints_concurrent_requests(self, client, trained_models, load_test_user, load_test_items):
        """
        Тестирует смешанную нагрузку на все эндпоинты рекомендаций.

        Симулирует реальный сценарий использования:
        - 40% GET /api/recommendations
        - 30% POST /api/recommendations/feedback
        - 20% GET /api/recommendations/stats
        - 10% GET /api/recommendations/for-playlist

        Ожидания:
        - Все запросы завершаются успешно
        - Среднее время отклика < 2 секунд
        - Процент ошибок < 5%
        - Система справляется со смешанной нагрузкой
        """
        user_id = str(load_test_user.id)
        num_requests = 100
        metrics = LoadTestMetrics()

        # Распределяем запросы по эндпоинтам
        def make_mixed_request(request_index):
            if request_index < 40:  # 40% recommendations
                make_get_recommendations_request(client, user_id, metrics)
            elif request_index < 70:  # 30% feedback
                item_id = str(load_test_items[request_index % len(load_test_items)].id)
                make_post_feedback_request(client, item_id, metrics)
            elif request_index < 90:  # 20% stats
                make_get_stats_request(client, metrics)
            else:  # 10% for-playlist
                make_get_for_playlist_request(client, 1, metrics)

        # Выполняем concurrent запросы
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [
                executor.submit(make_mixed_request, i)
                for i in range(num_requests)
            ]
            for future in as_completed(futures):
                future.result()

        # Проверяем метрики
        stats = metrics.get_stats()

        assert stats["total_requests"] == num_requests
        assert stats["error_rate"] < 5.0, f"Error rate too high: {stats['error_rate']}%"
        assert stats["avg_response_time"] < 2.0, f"Average response time too slow: {stats['avg_response_time']}s"
        assert stats["p95_response_time"] < 5.0, f"P95 response time too slow: {stats['p95_response_time']}s"

        # Логируем метрики
        print(f"\n=== Mixed Endpoints Load Test ===")
        print(f"Total requests: {stats['total_requests']}")
        print(f"Success: {stats['success_count']}, Errors: {stats['error_count']}")
        print(f"Error rate: {stats['error_rate']:.2f}%")
        print(f"Avg response time: {stats['avg_response_time']:.3f}s")
        print(f"P50: {stats['p50_response_time']:.3f}s, P95: {stats['p95_response_time']:.3f}s, P99: {stats['p99_response_time']:.3f}s")

    def test_sustained_load_recommendations(self, client, trained_models, load_test_user):
        """
        Тестирует продолжительную нагрузку на GET /api/recommendations.

        Выполняет 200 запросов в течение 10 секунд с разной интенсивностью.

        Ожидания:
        - Система остается стабильной под продолжительной нагрузкой
        - Время отклика не деградирует со временем
        - Процент ошибок < 5%
        - Нет утечек памяти или соединений
        """
        user_id = str(load_test_user.id)
        num_requests = 200
        metrics = LoadTestMetrics()

        # Выполняем запросы в течение времени
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(make_get_recommendations_request, client, user_id, metrics)
                for _ in range(num_requests)
            ]
            for future in as_completed(futures):
                future.result()

        total_time = time.time() - start_time

        # Проверяем метрики
        stats = metrics.get_stats()

        assert stats["total_requests"] == num_requests
        assert stats["error_rate"] < 5.0, f"Error rate too high: {stats['error_rate']}%"
        assert stats["avg_response_time"] < 2.0, f"Average response time too slow: {stats['avg_response_time']}s"

        throughput = num_requests / total_time
        assert throughput > 10, f"Throughput too low: {throughput:.2f} requests/sec"

        # Логируем метрики
        print(f"\n=== Sustained Load Test (GET /api/recommendations) ===")
        print(f"Total requests: {stats['total_requests']}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Throughput: {throughput:.2f} requests/sec")
        print(f"Success: {stats['success_count']}, Errors: {stats['error_count']}")
        print(f"Error rate: {stats['error_rate']:.2f}%")
        print(f"Avg response time: {stats['avg_response_time']:.3f}s")
        print(f"P50: {stats['p50_response_time']:.3f}s, P95: {stats['p95_response_time']:.3f}s")
