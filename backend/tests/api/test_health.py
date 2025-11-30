"""
Contract tests для Health API endpoints.
Тесты соответствуют спецификации contracts/health-api.yaml
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.api.health import DependencyHealth


class TestHealthEndpoint:
    """Тесты для /health endpoint."""
    
    def test_health_returns_200_when_all_dependencies_healthy(self, client):
        """GET /health возвращает 200 когда все зависимости работают."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0
        assert "timestamp" in data
        assert "dependencies" in data
        assert isinstance(data["dependencies"], list)
        assert len(data["dependencies"]) >= 2  # db и redis минимум
        
    @pytest.mark.xfail(reason="Mock не работает с уже загруженным app - требуется DI рефакторинг")
    def test_health_returns_503_when_database_down(self, client):
        """GET /health возвращает 503 когда БД недоступна."""
        with patch('src.api.health.check_database') as mock_db:
            mock_db.return_value = DependencyHealth(
                name="database",
                status="down",
                latency_ms=-1,
                message="Connection refused",
                last_check=datetime.now(timezone.utc).isoformat()
            )
            response = client.get("/health")
            assert response.status_code == 503
            
            data = response.json()
            assert data["status"] == "unhealthy"
            
    def test_health_response_has_required_fields(self, client):
        """GET /health содержит все обязательные поля согласно контракту."""
        response = client.get("/health")
        data = response.json()
        
        # Required fields
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "version" in data
        assert isinstance(data["version"], str)
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], (int, float))
        assert "timestamp" in data
        assert "dependencies" in data
        
        # Dependency fields
        for dep in data["dependencies"]:
            assert "name" in dep
            assert "status" in dep
            assert dep["status"] in ["up", "down", "degraded"]
            assert "latency_ms" in dep
            assert "last_check" in dep
            
    def test_health_timestamp_is_iso8601(self, client):
        """GET /health timestamp соответствует формату ISO 8601."""
        response = client.get("/health")
        data = response.json()
        
        # Должен парситься без ошибок
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


class TestLivenessProbe:
    """Тесты для /health/live endpoint."""
    
    def test_liveness_returns_200(self, client):
        """GET /health/live возвращает 200 если приложение запущено."""
        response = client.get("/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"
        
    def test_liveness_does_not_check_dependencies(self, client):
        """GET /health/live не проверяет зависимости."""
        # Даже если БД недоступна, liveness должен возвращать 200
        with patch('src.api.health.check_database') as mock_db:
            mock_db.side_effect = Exception("DB connection failed")
            response = client.get("/health/live")
            assert response.status_code == 200


class TestReadinessProbe:
    """Тесты для /health/ready endpoint."""
    
    def test_readiness_returns_200_when_ready(self, client):
        """GET /health/ready возвращает 200 когда сервис готов."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ready"
        
    @pytest.mark.xfail(reason="Mock не работает с уже загруженным app - требуется DI рефакторинг")
    def test_readiness_returns_503_when_db_down(self, client):
        """GET /health/ready возвращает 503 когда БД недоступна."""
        with patch('src.api.health.check_database') as mock_db:
            mock_db.return_value = DependencyHealth(
                name="database",
                status="down",
                latency_ms=-1,
                message="Connection refused",
                last_check=datetime.now(timezone.utc).isoformat()
            )
            response = client.get("/health/ready")
            assert response.status_code == 503
            
            data = response.json()
            assert data["status"] == "not_ready"
            assert "reason" in data


class TestDependencyHealth:
    """Тесты для проверки здоровья зависимостей."""
    
    def test_database_dependency_is_checked(self, client):
        """Зависимость database присутствует в ответе /health."""
        response = client.get("/health")
        data = response.json()
        
        dep_names = [d["name"] for d in data["dependencies"]]
        assert "database" in dep_names
        
    def test_redis_dependency_is_checked(self, client):
        """Зависимость redis присутствует в ответе /health."""
        response = client.get("/health")
        data = response.json()
        
        dep_names = [d["name"] for d in data["dependencies"]]
        assert "redis" in dep_names
        
    @pytest.mark.xfail(reason="Mock не работает с уже загруженным app - требуется DI рефакторинг")
    def test_degraded_status_on_high_latency(self, client):
        """Статус degraded при высокой latency."""
        with patch('src.api.health.check_redis') as mock_redis:
            mock_redis.return_value = DependencyHealth(
                name="redis",
                status="degraded",
                latency_ms=150.0,
                message="High latency detected",
                last_check=datetime.now(timezone.utc).isoformat()
            )
            with patch('src.api.health.check_database') as mock_db:
                mock_db.return_value = DependencyHealth(
                    name="database",
                    status="up",
                    latency_ms=5.0,
                    last_check=datetime.now(timezone.utc).isoformat()
                )
                response = client.get("/health")
                data = response.json()
                
                # Один degraded -> общий статус degraded
                assert data["status"] == "degraded"
