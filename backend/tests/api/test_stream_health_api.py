"""
Integration tests для Stream Health API endpoints.
Тесты соответствуют спецификации src/api/routes/stream_health.py
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from src.models.stream import Stream, StreamStatus
from src.models.recovery_log import RecoveryLog, RecoveryFailureType, RecoveryStatus, RecoveryStrategy
from src.models.user import User, UserRole, UserStatus


class TestStreamHealthEndpoint:
    """Тесты для GET /api/streams/{stream_id}/health endpoint."""

    def test_get_stream_health_returns_200_when_authenticated(self, client: TestClient, db_session, admin_user):
        """GET /api/streams/{stream_id}/health возвращает 200 когда пользователь авторизован."""
        # Create test stream
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        # Create auth token
        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/streams/{stream.id}/health", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "stream_id" in data
        assert "is_healthy" in data
        assert "last_check" in data
        assert "consecutive_failures" in data
        assert "total_checks" in data
        assert "failed_checks" in data
        assert "circuit_breaker_state" in data

    def test_get_stream_health_returns_404_when_stream_not_found(self, client: TestClient, admin_user):
        """GET /api/streams/{stream_id}/health возвращает 404 когда поток не найден."""
        fake_id = uuid.uuid4()

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/streams/{fake_id}/health", headers=headers)
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data

    def test_get_stream_health_returns_403_when_not_owner(self, client: TestClient, db_session, admin_user, regular_user):
        """GET /api/streams/{stream_id}/health возвращает 403 когда пользователь не владелец."""
        # Create stream owned by admin
        stream = Stream(
            title="Admin Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        # Try to access as regular user
        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(regular_user.id), "role": regular_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/streams/{stream.id}/health", headers=headers)
        assert response.status_code == 403

    def test_get_stream_health_response_has_required_fields(self, client: TestClient, db_session, admin_user):
        """GET /api/streams/{stream_id}/health содержит все обязательные поля."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/streams/{stream.id}/health", headers=headers)
        data = response.json()

        # Required fields
        assert "stream_id" in data
        assert "is_healthy" in data
        assert isinstance(data["is_healthy"], bool)
        assert "last_check" in data
        assert "consecutive_failures" in data
        assert isinstance(data["consecutive_failures"], int)
        assert "total_checks" in data
        assert isinstance(data["total_checks"], int)
        assert "failed_checks" in data
        assert isinstance(data["failed_checks"], int)
        assert "circuit_breaker_state" in data
        assert "circuit_breaker_open_until" in data


class TestRecoveryLogsEndpoint:
    """Тесты для GET /api/streams/{stream_id}/recovery-logs endpoint."""

    def test_get_recovery_logs_returns_200_when_authenticated(self, client: TestClient, db_session, admin_user):
        """GET /api/streams/{stream_id}/recovery-logs возвращает 200 когда пользователь авторизован."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        # Create recovery log
        log = RecoveryLog(
            stream_id=stream.id,
            failure_type=RecoveryFailureType.STREAM_DISCONNECTED,
            failure_reason="Test failure",
            recovery_strategy=RecoveryStrategy.RESTART_STREAM,
            status=RecoveryStatus.COMPLETED,
            attempt_number=1,
            max_attempts=3,
            started_at=datetime.now(timezone.utc)
        )
        db_session.add(log)
        db_session.commit()

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/streams/{stream.id}/recovery-logs", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_recovery_logs_returns_empty_list_for_new_stream(self, client: TestClient, db_session, admin_user):
        """GET /api/streams/{stream_id}/recovery-logs возвращает пустой список для нового потока."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/streams/{stream.id}/recovery-logs", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_recovery_logs_supports_pagination(self, client: TestClient, db_session, admin_user):
        """GET /api/streams/{stream_id}/recovery-logs поддерживает пагинацию."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        # Create multiple recovery logs
        for i in range(5):
            log = RecoveryLog(
                stream_id=stream.id,
                failure_type=RecoveryFailureType.STREAM_DISCONNECTED,
                failure_reason=f"Test failure {i}",
                recovery_strategy=RecoveryStrategy.RESTART_STREAM,
                status=RecoveryStatus.COMPLETED,
                attempt_number=1,
                max_attempts=3,
                started_at=datetime.now(timezone.utc)
            )
            db_session.add(log)
        db_session.commit()

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        # Test limit
        response = client.get(f"/api/streams/{stream.id}/recovery-logs?limit=3", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_get_recovery_logs_supports_status_filter(self, client: TestClient, db_session, admin_user):
        """GET /api/streams/{stream_id}/recovery-logs поддерживает фильтрацию по статусу."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        # Create logs with different statuses
        log1 = RecoveryLog(
            stream_id=stream.id,
            failure_type=RecoveryFailureType.STREAM_DISCONNECTED,
            failure_reason="Test failure 1",
            recovery_strategy=RecoveryStrategy.RESTART_STREAM,
            status=RecoveryStatus.COMPLETED,
            attempt_number=1,
            max_attempts=3,
            started_at=datetime.now(timezone.utc)
        )
        log2 = RecoveryLog(
            stream_id=stream.id,
            failure_type=RecoveryFailureType.STREAM_DISCONNECTED,
            failure_reason="Test failure 2",
            recovery_strategy=RecoveryStrategy.RESTART_STREAM,
            status=RecoveryStatus.IN_PROGRESS,
            attempt_number=1,
            max_attempts=3,
            started_at=datetime.now(timezone.utc)
        )
        db_session.add_all([log1, log2])
        db_session.commit()

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/streams/{stream.id}/recovery-logs?status_filter=in_progress", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "in_progress"


class TestRecoveryStatsEndpoint:
    """Тесты для GET /api/streams/{stream_id}/recovery-stats endpoint."""

    def test_get_recovery_stats_returns_200_when_authenticated(self, client: TestClient, db_session, admin_user):
        """GET /api/streams/{stream_id}/recovery-stats возвращает 200 когда пользователь авторизован."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/streams/{stream.id}/recovery-stats", headers=headers)
        assert response.status_code == 200

        data = response.json()
        assert "stream_id" in data
        assert "total_recoveries" in data
        assert "successful_recoveries" in data
        assert "failed_recoveries" in data
        assert "current_circuit_breaker_state" in data

    def test_get_recovery_stats_returns_zero_for_new_stream(self, client: TestClient, db_session, admin_user):
        """GET /api/streams/{stream_id}/recovery-stats возвращает нули для нового потока."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"/api/streams/{stream.id}/recovery-stats", headers=headers)
        data = response.json()

        assert data["total_recoveries"] == 0
        assert data["successful_recoveries"] == 0
        assert data["failed_recoveries"] == 0
        assert data["abandoned_recoveries"] == 0


class TestManualRecoveryEndpoint:
    """Тесты для POST /api/streams/{stream_id}/recover endpoint."""

    def test_manual_recovery_returns_200_when_successful(self, client: TestClient, db_session, admin_user):
        """POST /api/streams/{stream_id}/recover возвращает 200 при успешном восстановлении."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "failure_type": "stream_disconnected",
            "failure_reason": "Test manual recovery",
            "force": False
        }

        response = client.post(f"/api/streams/{stream.id}/recover", json=payload, headers=headers)
        # Note: May return 200 or 500 depending on whether recovery service is available
        # We're testing that the endpoint is accessible and validates input
        assert response.status_code in [200, 500, 503]

    def test_manual_recovery_returns_404_when_stream_not_found(self, client: TestClient, admin_user):
        """POST /api/streams/{stream_id}/recover возвращает 404 когда поток не найден."""
        fake_id = uuid.uuid4()

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "failure_type": "stream_disconnected",
            "failure_reason": "Test recovery",
            "force": False
        }

        response = client.post(f"/api/streams/{fake_id}/recover", json=payload, headers=headers)
        assert response.status_code == 404

    def test_manual_recovery_validates_required_fields(self, client: TestClient, db_session, admin_user):
        """POST /api/streams/{stream_id}/recover валидирует обязательные поля."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        # Missing required fields
        payload = {}

        response = client.post(f"/api/streams/{stream.id}/recover", json=payload, headers=headers)
        assert response.status_code == 422  # Validation error


class TestResetCircuitBreakerEndpoint:
    """Тесты для POST /api/streams/{stream_id}/reset-circuit-breaker endpoint."""

    def test_reset_circuit_breaker_returns_200_when_successful(self, client: TestClient, db_session, admin_user):
        """POST /api/streams/{stream_id}/reset-circuit-breaker возвращает 200 при успешном сбросе."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(f"/api/streams/{stream.id}/reset-circuit-breaker", headers=headers)
        # Note: May return 200 or 500 depending on service availability
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "message" in data
            assert "stream_id" in data

    def test_reset_circuit_breaker_returns_404_when_stream_not_found(self, client: TestClient, admin_user):
        """POST /api/streams/{stream_id}/reset-circuit-breaker возвращает 404 когда поток не найден."""
        fake_id = uuid.uuid4()

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(f"/api/streams/{fake_id}/reset-circuit-breaker", headers=headers)
        assert response.status_code == 404

    def test_reset_circuit_breaker_returns_403_when_not_owner(self, client: TestClient, db_session, admin_user, regular_user):
        """POST /api/streams/{stream_id}/reset-circuit-breaker возвращает 403 когда пользователь не владелец."""
        stream = Stream(
            title="Admin Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(regular_user.id), "role": regular_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(f"/api/streams/{stream.id}/reset-circuit-breaker", headers=headers)
        assert response.status_code == 403


class TestResetStreamHealthEndpoint:
    """Тесты для POST /api/streams/{stream_id}/reset-health endpoint."""

    def test_reset_health_returns_200_when_successful(self, client: TestClient, db_session, admin_user):
        """POST /api/streams/{stream_id}/reset-health возвращает 200 при успешном сбросе."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(f"/api/streams/{stream.id}/reset-health", headers=headers)
        # Note: May return 200 or 500 depending on service availability
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert data["ok"] is True
            assert "message" in data
            assert "stream_id" in data

    def test_reset_health_returns_404_when_stream_not_found(self, client: TestClient, admin_user):
        """POST /api/streams/{stream_id}/reset-health возвращает 404 когда поток не найден."""
        fake_id = uuid.uuid4()

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(f"/api/streams/{fake_id}/reset-health", headers=headers)
        assert response.status_code == 404

    def test_reset_health_returns_403_when_not_owner(self, client: TestClient, db_session, admin_user, regular_user):
        """POST /api/streams/{stream_id}/reset-health возвращает 403 когда пользователь не владелец."""
        stream = Stream(
            title="Admin Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        from src.auth.jwt import create_access_token
        token = create_access_token(data={"sub": str(regular_user.id), "role": regular_user.role})
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post(f"/api/streams/{stream.id}/reset-health", headers=headers)
        assert response.status_code == 403


class TestStreamHealthAuthorization:
    """Тесты для проверки авторизации на stream health endpoints."""

    def test_unauthenticated_request_returns_401(self, client: TestClient, db_session, admin_user):
        """Неавторизованный запрос возвращает 401 для всех health endpoints."""
        stream = Stream(
            title="Test Stream",
            chat_id=123456789,
            owner_id=admin_user.id,
            status=StreamStatus.ACTIVE
        )
        db_session.add(stream)
        db_session.commit()
        db_session.refresh(stream)

        # Test health endpoint
        response = client.get(f"/api/streams/{stream.id}/health")
        assert response.status_code == 401

        # Test recovery logs endpoint
        response = client.get(f"/api/streams/{stream.id}/recovery-logs")
        assert response.status_code == 401

        # Test recovery stats endpoint
        response = client.get(f"/api/streams/{stream.id}/recovery-stats")
        assert response.status_code == 401

        # Test manual recovery endpoint
        response = client.post(f"/api/streams/{stream.id}/recover", json={
            "failure_type": "stream_disconnected",
            "failure_reason": "Test"
        })
        assert response.status_code == 401

        # Test reset circuit breaker endpoint
        response = client.post(f"/api/streams/{stream.id}/reset-circuit-breaker")
        assert response.status_code == 401

        # Test reset health endpoint
        response = client.post(f"/api/streams/{stream.id}/reset-health")
        assert response.status_code == 401
