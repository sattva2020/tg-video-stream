"""
Contract tests для System Metrics API endpoint.
Spec: 015-real-system-monitoring
Тесты соответствуют спецификации contracts/system-monitoring-api.yaml
"""

import pytest
from datetime import datetime


class TestSystemMetricsEndpoint:
    """Тесты для GET /api/system/metrics."""

    def test_metrics_returns_200(self, client):
        """GET /api/system/metrics возвращает 200."""
        response = client.get("/api/system/metrics")
        assert response.status_code == 200

    def test_metrics_returns_required_fields(self, client):
        """GET /api/system/metrics содержит все обязательные поля."""
        response = client.get("/api/system/metrics")
        data = response.json()

        # Обязательные поля согласно контракту
        assert "cpu_percent" in data
        assert "ram_percent" in data
        assert "disk_percent" in data
        assert "db_connections_active" in data
        assert "db_connections_idle" in data
        assert "uptime_seconds" in data
        assert "collected_at" in data

    def test_metrics_values_in_valid_range(self, client):
        """Метрики CPU, RAM, Disk в диапазоне 0-100."""
        response = client.get("/api/system/metrics")
        data = response.json()

        # CPU
        assert 0 <= data["cpu_percent"] <= 100
        assert isinstance(data["cpu_percent"], (int, float))

        # RAM
        assert 0 <= data["ram_percent"] <= 100
        assert isinstance(data["ram_percent"], (int, float))

        # Disk
        assert 0 <= data["disk_percent"] <= 100
        assert isinstance(data["disk_percent"], (int, float))

    def test_metrics_db_connections_non_negative(self, client):
        """DB connections >= 0."""
        response = client.get("/api/system/metrics")
        data = response.json()

        assert data["db_connections_active"] >= 0
        assert data["db_connections_idle"] >= 0
        assert isinstance(data["db_connections_active"], int)
        assert isinstance(data["db_connections_idle"], int)

    def test_metrics_uptime_non_negative(self, client):
        """Uptime >= 0."""
        response = client.get("/api/system/metrics")
        data = response.json()

        assert data["uptime_seconds"] >= 0
        assert isinstance(data["uptime_seconds"], int)

    def test_metrics_collected_at_is_iso8601(self, client):
        """collected_at в формате ISO 8601."""
        response = client.get("/api/system/metrics")
        data = response.json()

        # Должен парситься как datetime
        collected_at = datetime.fromisoformat(data["collected_at"].replace("Z", "+00:00"))
        assert collected_at is not None

    def test_metrics_collected_at_is_recent(self, client):
        """collected_at не старше 10 секунд."""
        response = client.get("/api/system/metrics")
        data = response.json()

        collected_at = datetime.fromisoformat(data["collected_at"].replace("Z", "+00:00"))
        now = datetime.now(collected_at.tzinfo)
        
        # Разница не более 10 секунд
        delta = abs((now - collected_at).total_seconds())
        assert delta < 10, f"collected_at слишком старое: {delta} секунд назад"

    def test_metrics_multiple_requests_consistent(self, client):
        """Повторные запросы возвращают консистентные данные."""
        response1 = client.get("/api/system/metrics")
        response2 = client.get("/api/system/metrics")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Оба ответа имеют одинаковую структуру
        data1 = response1.json()
        data2 = response2.json()

        assert set(data1.keys()) == set(data2.keys())


class TestSystemMetricsResponseType:
    """Тесты типов данных в ответе."""

    def test_cpu_percent_is_float(self, client):
        """cpu_percent возвращается как float (с одним знаком после запятой)."""
        response = client.get("/api/system/metrics")
        data = response.json()
        
        # Проверяем, что значение округлено до одного знака
        cpu = data["cpu_percent"]
        assert cpu == round(cpu, 1)

    def test_ram_percent_is_float(self, client):
        """ram_percent возвращается как float (с одним знаком после запятой)."""
        response = client.get("/api/system/metrics")
        data = response.json()
        
        ram = data["ram_percent"]
        assert ram == round(ram, 1)

    def test_disk_percent_is_float(self, client):
        """disk_percent возвращается как float (с одним знаком после запятой)."""
        response = client.get("/api/system/metrics")
        data = response.json()
        
        disk = data["disk_percent"]
        assert disk == round(disk, 1)
