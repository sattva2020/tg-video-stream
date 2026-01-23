"""
Тесты для API оптимизации расписания.

Покрывает:
- Предпросмотр оптимизации расписания
- Обнаружение пробелов
- Обнаружение конфликтов
- Расчет метрик
"""

import pytest
from datetime import date, timedelta
from uuid import uuid4
from httpx import AsyncClient

from src.models.schedule import ScheduleSlot, Playlist, RepeatType
from src.models.user import User, UserRole, UserStatus

# Import test constants
TEST_CHANNEL_ID = "12345678-1234-5678-1234-567812345678"


# ==================== Fixtures ====================

@pytest.fixture
def admin_user(db_session) -> User:
    """Создаёт администратора для тестов."""
    user = User(
        email="admin@test.com",
        hashed_password="hashed",
        role=UserRole.ADMIN,
        status=UserStatus.APPROVED,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_playlist(db_session, admin_user: User) -> Playlist:
    """Создаёт тестовый плейлист."""
    playlist = Playlist(
        name="Test Playlist",
        description="Playlist for testing",
        user_id=admin_user.id,
        items=[
            {"url": "https://youtube.com/watch?v=123", "title": "Test Video 1", "duration": 180},
            {"url": "https://youtube.com/watch?v=456", "title": "Test Video 2", "duration": 240},
        ],
    )
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)
    return playlist


@pytest.fixture
def test_slot(db_session, admin_user: User, test_playlist: Playlist) -> ScheduleSlot:
    """Создаёт тестовый слот расписания."""
    slot = ScheduleSlot(
        channel_id=TEST_CHANNEL_ID,
        playlist_id=test_playlist.id,
        start_date=date.today(),
        start_time="10:00",
        end_time="12:00",
        title="Morning Show",
        repeat_type=RepeatType.NONE,
        is_active=True,
    )
    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)
    return slot


# ==================== Optimization Preview Tests ====================

class TestScheduleOptimizationPreview:
    """Тесты для предпросмотра оптимизации расписания."""

    @pytest.mark.asyncio
    async def test_preview_optimization_empty_schedule(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Предпросмотр оптимизации для пустого расписания."""
        response = await async_client.post(
            "/api/schedule-ai/optimize/preview",
            json={
                "channel_id": TEST_CHANNEL_ID,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=7)),
                "parameters": {
                    "maximize_engagement": True,
                    "minimize_gaps": True,
                    "balance_variety": True,
                    "respect_priority": True,
                    "target_hours": 24,
                }
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["channel_id"] == TEST_CHANNEL_ID
        assert data["status"] == "pending"
        assert "metrics" in data
        assert "warnings" in data
        assert isinstance(data["warnings"], list)

    @pytest.mark.asyncio
    async def test_preview_optimization_with_slot(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_slot: ScheduleSlot,
    ):
        """Предпросмотр оптимизации с существующим слотом."""
        response = await async_client.post(
            "/api/schedule-ai/optimize/preview",
            json={
                "channel_id": TEST_CHANNEL_ID,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=1)),
                "parameters": {
                    "maximize_engagement": True,
                    "minimize_gaps": True,
                    "balance_variety": True,
                }
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "pending"
        assert "metrics" in data
        # Должны быть метрики с ненулевым покрытием
        assert data["metrics"]["total_slots"] >= 1

    @pytest.mark.asyncio
    async def test_preview_optimization_invalid_channel(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Предпросмотр оптимизации с невалидным ID канала."""
        invalid_channel_id = str(uuid4())
        response = await async_client.post(
            "/api/schedule-ai/optimize/preview",
            json={
                "channel_id": invalid_channel_id,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=7)),
            },
            headers=admin_auth_headers,
        )
        # Должен вернуть 200 даже если канал не существует (создаст пустую оптимизацию)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_preview_optimization_unauthorized(
        self,
        async_client: AsyncClient,
    ):
        """Предпросмотр оптимизации без авторизации."""
        response = await async_client.post(
            "/api/schedule-ai/optimize/preview",
            json={
                "channel_id": TEST_CHANNEL_ID,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=7)),
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_preview_optimization_default_parameters(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Предпросмотр оптимизации с параметрами по умолчанию."""
        response = await async_client.post(
            "/api/schedule-ai/optimize/preview",
            json={
                "channel_id": TEST_CHANNEL_ID,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=1)),
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Параметры должны быть установлены по умолчанию
        assert "parameters" in data
        assert data["parameters"]["maximize_engagement"] is True
        assert data["parameters"]["minimize_gaps"] is True
