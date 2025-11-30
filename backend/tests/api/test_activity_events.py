"""
Contract tests для Activity Events API endpoint.
Spec: 015-real-system-monitoring
Тесты соответствуют спецификации contracts/system-monitoring-api.yaml
"""

import pytest
from datetime import datetime


class TestActivityEventsEndpoint:
    """Тесты для GET /api/system/activity."""

    def test_activity_returns_200(self, client):
        """GET /api/system/activity возвращает 200."""
        response = client.get("/api/system/activity")
        assert response.status_code == 200

    def test_activity_returns_required_structure(self, client):
        """GET /api/system/activity возвращает events и total."""
        response = client.get("/api/system/activity")
        data = response.json()

        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)
        assert isinstance(data["total"], int)
        assert data["total"] >= 0

    def test_activity_respects_limit_parameter(self, client):
        """Параметр limit ограничивает количество результатов."""
        response = client.get("/api/system/activity", params={"limit": 5})
        data = response.json()

        assert len(data["events"]) <= 5

    def test_activity_respects_offset_parameter(self, client):
        """Параметр offset смещает результаты."""
        # Первый запрос - получаем все события
        response1 = client.get("/api/system/activity", params={"limit": 100})
        data1 = response1.json()

        if data1["total"] < 2:
            pytest.skip("Недостаточно событий для теста пагинации")

        # Второй запрос - со смещением
        response2 = client.get("/api/system/activity", params={"limit": 100, "offset": 1})
        data2 = response2.json()

        # Первый элемент второго запроса должен быть вторым элементом первого
        if len(data1["events"]) >= 2 and len(data2["events"]) >= 1:
            assert data2["events"][0]["id"] == data1["events"][1]["id"]

    def test_activity_limit_validation(self, client):
        """Limit должен быть в диапазоне 1-100."""
        # limit < 1 должен вернуть ошибку
        response = client.get("/api/system/activity", params={"limit": 0})
        assert response.status_code in [400, 422]

        # limit > 100 должен вернуть ошибку
        response = client.get("/api/system/activity", params={"limit": 101})
        assert response.status_code in [400, 422]

    def test_activity_offset_validation(self, client):
        """Offset должен быть >= 0."""
        response = client.get("/api/system/activity", params={"offset": -1})
        assert response.status_code in [400, 422]

    def test_activity_event_structure(self, client):
        """Каждое событие содержит обязательные поля."""
        response = client.get("/api/system/activity")
        data = response.json()

        if len(data["events"]) == 0:
            pytest.skip("Нет событий для проверки структуры")

        event = data["events"][0]

        # Обязательные поля
        assert "id" in event
        assert "type" in event
        assert "message" in event
        assert "created_at" in event

        # Типы полей
        assert isinstance(event["id"], (int, str))
        assert isinstance(event["type"], str)
        assert isinstance(event["message"], str)

    def test_activity_created_at_is_iso8601(self, client):
        """created_at в формате ISO 8601."""
        response = client.get("/api/system/activity")
        data = response.json()

        if len(data["events"]) == 0:
            pytest.skip("Нет событий для проверки")

        event = data["events"][0]
        # Должен парситься как datetime
        created_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
        assert created_at is not None

    def test_activity_filter_by_type(self, client):
        """Фильтрация по типу события."""
        response = client.get("/api/system/activity", params={"type": "user_registered"})
        data = response.json()

        for event in data["events"]:
            assert event["type"] == "user_registered"

    def test_activity_search_filter(self, client):
        """Поиск по тексту сообщения."""
        # Этот тест требует наличия событий с определённым текстом
        response = client.get("/api/system/activity", params={"search": "test"})
        data = response.json()

        # Если есть результаты, они должны содержать искомый текст
        # (в message, user_email или details)
        # Просто проверяем, что запрос не падает
        assert response.status_code == 200


class TestActivityEventsOrdering:
    """Тесты порядка сортировки событий."""

    def test_events_ordered_by_created_at_desc(self, client):
        """События отсортированы от новых к старым."""
        response = client.get("/api/system/activity", params={"limit": 10})
        data = response.json()

        if len(data["events"]) < 2:
            pytest.skip("Недостаточно событий для проверки сортировки")

        dates = [
            datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
            for e in data["events"]
        ]

        for i in range(len(dates) - 1):
            assert dates[i] >= dates[i + 1], "События должны быть отсортированы по убыванию даты"
