"""
Tests for auto-pilot schedule generation endpoint.
Feature: 015-smart-scheduling-auto-pilot-mode
"""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.main import app
from src.services.auto_pilot_service import AutoPilotService
from src.schemas.schedule_ai import AutoPilotRequest, AutoPilotResponse


@pytest.fixture
def client(db_session: Session):
    """Test client with database session."""
    return TestClient(app)


@pytest.fixture
def admin_user(db_session: Session):
    """Create admin user for testing."""
    from src.models.user import User
    from src.api.auth import get_password_hash

    user = User(
        username="admin_test",
        email="admin@test.com",
        hashed_password=get_password_hash("testpass"),
        role="ADMIN",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(client, admin_user):
    """Get admin auth token."""
    response = client.post(
        "/api/auth/login",
        data={"username": "admin_test", "password": "testpass"}
    )
    return response.json()["access_token"]


class TestAutoPilotGenerateEndpoint:
    """Tests for POST /api/schedule-ai/auto-pilot/generate"""

    def test_auto_pilot_generate_success(
        self, client: TestClient, admin_token: str, db_session: Session
    ):
        """Test successful schedule generation."""
        # Mock the service response
        mock_response = AutoPilotResponse(
            task_id="test-task-123",
            channel_id="test-channel-id",
            status="completed",
            date_range={"start": "2025-01-23", "end": "2025-01-30"},
            slots_created=5,
            gaps_filled=2,
            conflicts_resolved=1,
            created_at=datetime.utcnow()
        )

        with patch.object(
            AutoPilotService,
            'generate_schedule',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
            response = client.post(
                "/api/schedule-ai/auto-pilot/generate",
                json={
                    "channel_id": "test-channel-id",
                    "date_range": {
                        "start": "2025-01-23",
                        "end": "2025-01-30"
                    },
                    "use_ai_recommendations": True,
                    "fill_gaps": True,
                    "resolve_conflicts": True
                },
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 201
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["channel_id"] == "test-channel-id"
        assert data["status"] == "completed"
        assert data["slots_created"] == 5
        assert data["gaps_filled"] == 2
        assert data["conflicts_resolved"] == 1

    def test_auto_pilot_generate_unauthorized(
        self, client: TestClient, db_session: Session
    ):
        """Test that unauthorized users cannot generate schedules."""
        response = client.post(
            "/api/schedule-ai/auto-pilot/generate",
            json={
                "channel_id": "test-channel-id",
                "date_range": {
                    "start": "2025-01-23",
                    "end": "2025-01-30"
                }
            }
        )

        assert response.status_code == 401

    def test_auto_pilot_generate_non_admin(
        self, client: TestClient, db_session: Session
    ):
        """Test that non-admin users cannot generate schedules."""
        # Create regular user
        from src.models.user import User
        from src.api.auth import get_password_hash

        user = User(
            username="user_test",
            email="user@test.com",
            hashed_password=get_password_hash("testpass"),
            role="USER",
            is_active=True
        )
        db_session.add(user)
        db_session.commit()

        # Login as regular user
        login_response = client.post(
            "/api/auth/login",
            data={"username": "user_test", "password": "testpass"}
        )
        token = login_response.json()["access_token"]

        # Try to generate schedule
        response = client.post(
            "/api/schedule-ai/auto-pilot/generate",
            json={
                "channel_id": "test-channel-id",
                "date_range": {
                    "start": "2025-01-23",
                    "end": "2025-01-30"
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    def test_auto_pilot_generate_invalid_date_range(
        self, client: TestClient, admin_token: str
    ):
        """Test that invalid date ranges are rejected."""
        response = client.post(
            "/api/schedule-ai/auto-pilot/generate",
            json={
                "channel_id": "test-channel-id",
                "date_range": {
                    "start": "2025-01-30",
                    "end": "2025-01-23"  # End before start
                }
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Should return 500 due to validation error in service
        assert response.status_code == 500

    def test_auto_pilot_generate_missing_channel_id(
        self, client: TestClient, admin_token: str
    ):
        """Test that missing channel_id is rejected."""
        response = client.post(
            "/api/schedule-ai/auto-pilot/generate",
            json={
                "date_range": {
                    "start": "2025-01-23",
                    "end": "2025-01-30"
                }
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 422  # Validation error


class TestAutoPilotPreviewEndpoint:
    """Tests for POST /api/schedule-ai/auto-pilot/preview"""

    def test_auto_pilot_preview_success(
        self, client: TestClient, admin_token: str, db_session: Session
    ):
        """Test successful schedule preview."""
        mock_suggestions = [
            {
                "date": "2025-01-23",
                "start_time": "09:00",
                "end_time": "12:00",
                "playlist_id": "playlist-123"
            }
        ]

        with patch.object(
            AutoPilotService,
            'preview_schedule',
            new_callable=AsyncMock,
            return_value=mock_suggestions
        ):
            response = client.post(
                "/api/schedule-ai/auto-pilot/preview",
                json={
                    "channel_id": "test-channel-id",
                    "date_range": {
                        "start": "2025-01-23",
                        "end": "2025-01-30"
                    },
                    "use_ai_recommendations": True
                },
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["channel_id"] == "test-channel-id"
        assert data["date_range"]["start"] == "2025-01-23"
        assert data["preview"] == mock_suggestions
        assert "generated_at" in data
