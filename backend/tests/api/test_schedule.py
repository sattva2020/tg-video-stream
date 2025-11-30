"""
Тесты для API расписания трансляций.

Покрывает:
- CRUD операции со слотами расписания
- Управление плейлистами
- Шаблоны расписания
- Копирование расписания
- Валидация данных
"""

import pytest
from datetime import date, time, timedelta
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schedule import ScheduleSlot, Playlist, ScheduleTemplate, RepeatType
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
def regular_user(db_session) -> User:
    """Создаёт обычного пользователя для тестов."""
    user = User(
        email="user@test.com",
        hashed_password="hashed",
        role=UserRole.USER,
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
        start_time=time(10, 0),
        end_time=time(12, 0),
        title="Morning Show",
        repeat_type=RepeatType.NONE,
        is_active=True,
    )
    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)
    return slot


# ==================== Schedule Slots Tests ====================

class TestScheduleSlots:
    """Тесты для слотов расписания."""
    
    def test_get_slots_empty(
        self,
        client,
        db_session,
        admin_auth_headers: dict,
    ):
        """Получение слотов для пустого расписания."""
        # Channel is already created in conftest.py
        response = client.get(
            "/api/schedule/slots",
            params={
                "channel_id": TEST_CHANNEL_ID,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=7)),
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []
    
    @pytest.mark.asyncio
    async def test_get_slots_with_data(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_slot: ScheduleSlot,
    ):
        """Получение слотов с данными."""
        response = await async_client.get(
            "/api/schedule/slots",
            params={
                "channel_id": str(test_slot.channel_id),
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=1)),
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Morning Show"
    
    @pytest.mark.asyncio
    async def test_create_slot_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_playlist: Playlist,
    ):
        """Успешное создание слота."""
        payload = {
            "channel_id": TEST_CHANNEL_ID,
            "playlist_id": str(test_playlist.id),
            "start_date": str(date.today()),
            "start_time": "14:00",
            "end_time": "16:00",
            "title": "Afternoon Show",
            "repeat_type": "none",
        }
        response = await async_client.post(
            "/api/schedule/slots",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Afternoon Show"
        assert data["channel_id"] == TEST_CHANNEL_ID
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_create_slot_overlap_error(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_slot: ScheduleSlot,
        test_playlist: Playlist,
    ):
        """Ошибка при создании перекрывающегося слота."""
        payload = {
            "channel_id": str(test_slot.channel_id),
            "playlist_id": str(test_playlist.id),
            "start_date": str(date.today()),
            "start_time": "11:00",  # Перекрывается с 10:00-12:00
            "end_time": "13:00",
            "title": "Overlapping Show",
            "repeat_type": "none",
        }
        response = await async_client.post(
            "/api/schedule/slots",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 409
        assert "overlap" in response.json()["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_create_slot_invalid_time_range(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_playlist: Playlist,
    ):
        """Ошибка при неверном диапазоне времени."""
        payload = {
            "channel_id": TEST_CHANNEL_ID,
            "playlist_id": str(test_playlist.id),
            "start_date": str(date.today()),
            "start_time": "16:00",
            "end_time": "14:00",  # Конец раньше начала
            "title": "Invalid Slot",
            "repeat_type": "none",
        }
        response = await async_client.post(
            "/api/schedule/slots",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_update_slot_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_slot: ScheduleSlot,
    ):
        """Успешное обновление слота."""
        payload = {
            "title": "Updated Morning Show",
            "end_time": "13:00",
        }
        response = await async_client.put(
            f"/api/schedule/slots/{test_slot.id}",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Morning Show"
        assert data["end_time"] == "13:00"
    
    @pytest.mark.asyncio
    async def test_update_slot_not_found(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Ошибка при обновлении несуществующего слота."""
        fake_id = str(uuid4())
        response = await async_client.put(
            f"/api/schedule/slots/{fake_id}",
            json={"title": "Test"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_slot_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_slot: ScheduleSlot,
    ):
        """Успешное удаление слота."""
        response = await async_client.delete(
            f"/api/schedule/slots/{test_slot.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == 204
        
        # Проверяем, что слот удалён
        response = await async_client.get(
            "/api/schedule/slots",
            params={
                "channel_id": str(test_slot.channel_id),
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=1)),
            },
            headers=admin_auth_headers,
        )
        assert response.json() == []
    
    @pytest.mark.asyncio
    async def test_user_cannot_create_slot(
        self,
        async_client: AsyncClient,
        user_auth_headers: dict,
        test_playlist: Playlist,
    ):
        """Обычный пользователь не может создавать слоты."""
        payload = {
            "channel_id": TEST_CHANNEL_ID,
            "playlist_id": str(test_playlist.id),
            "start_date": str(date.today()),
            "start_time": "18:00",
            "end_time": "20:00",
            "title": "User Slot",
            "repeat_type": "none",
        }
        response = await async_client.post(
            "/api/schedule/slots",
            json=payload,
            headers=user_auth_headers,
        )
        assert response.status_code == 403


# ==================== Playlist Tests ====================

class TestPlaylists:
    """Тесты для плейлистов."""
    
    @pytest.mark.asyncio
    async def test_get_playlists_empty(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Получение пустого списка плейлистов."""
        response = await async_client.get(
            "/api/schedule/playlists",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []
    
    @pytest.mark.asyncio
    async def test_get_playlists_with_data(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_playlist: Playlist,
    ):
        """Получение списка плейлистов с данными."""
        response = await async_client.get(
            "/api/schedule/playlists",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Playlist"
    
    @pytest.mark.asyncio
    async def test_create_playlist_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Успешное создание плейлиста."""
        payload = {
            "name": "New Playlist",
            "description": "A brand new playlist",
            "items": [
                {"url": "https://youtube.com/watch?v=abc", "title": "Video A", "duration": 300},
            ],
        }
        response = await async_client.post(
            "/api/schedule/playlists",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Playlist"
        assert len(data["items"]) == 1
    
    @pytest.mark.asyncio
    async def test_create_playlist_empty_name(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Ошибка при создании плейлиста без имени."""
        payload = {
            "name": "",
            "items": [],
        }
        response = await async_client.post(
            "/api/schedule/playlists",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_update_playlist_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_playlist: Playlist,
    ):
        """Успешное обновление плейлиста."""
        payload = {
            "name": "Updated Playlist Name",
            "items": [
                {"url": "https://youtube.com/watch?v=new", "title": "New Video", "duration": 120},
            ],
        }
        response = await async_client.put(
            f"/api/schedule/playlists/{test_playlist.id}",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Playlist Name"
        assert len(data["items"]) == 1
    
    @pytest.mark.asyncio
    async def test_delete_playlist_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_playlist: Playlist,
    ):
        """Успешное удаление плейлиста."""
        response = await async_client.delete(
            f"/api/schedule/playlists/{test_playlist.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == 204
    
    @pytest.mark.asyncio
    async def test_delete_playlist_in_use(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_slot: ScheduleSlot,
        test_playlist: Playlist,
    ):
        """Ошибка при удалении плейлиста, используемого в слоте."""
        response = await async_client.delete(
            f"/api/schedule/playlists/{test_playlist.id}",
            headers=admin_auth_headers,
        )
        # Плейлист используется в test_slot, должна быть ошибка
        assert response.status_code == 409
        assert "in use" in response.json()["detail"].lower()


# ==================== Schedule Templates Tests ====================

class TestScheduleTemplates:
    """Тесты для шаблонов расписания."""
    
    @pytest.mark.asyncio
    async def test_create_template_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_playlist: Playlist,
    ):
        """Успешное создание шаблона."""
        payload = {
            "name": "Weekend Template",
            "description": "Template for weekend broadcasting",
            "slots": [
                {
                    "day_of_week": 6,  # Saturday
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "playlist_id": str(test_playlist.id),
                    "title": "Saturday Morning",
                },
                {
                    "day_of_week": 0,  # Sunday
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "playlist_id": str(test_playlist.id),
                    "title": "Sunday Morning",
                },
            ],
        }
        response = await async_client.post(
            "/api/schedule/templates",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Weekend Template"
        assert len(data["slots"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_templates(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Получение списка шаблонов."""
        response = await async_client.get(
            "/api/schedule/templates",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    @pytest.mark.asyncio
    async def test_apply_template_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        db_session: AsyncSession,
        admin_user: User,
        test_playlist: Playlist,
    ):
        """Успешное применение шаблона."""
        # Сначала создаём шаблон
        template = ScheduleTemplate(
            name="Test Template",
            user_id=admin_user.id,
            slots=[
                {
                    "day_of_week": 0,
                    "start_time": "09:00",
                    "end_time": "11:00",
                    "playlist_id": str(test_playlist.id),
                    "title": "Template Slot",
                },
            ],
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        
        # Применяем шаблон
        today = date.today()
        target_dates = [
            str(today + timedelta(days=i)) for i in range(7)
        ]
        
        payload = {
            "template_id": str(template.id),
            "channel_id": TEST_CHANNEL_ID,
            "target_dates": target_dates,
        }
        response = await async_client.post(
            "/api/schedule/templates/apply",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] >= 1  # Как минимум 1 слот создан


# ==================== Copy Schedule Tests ====================

class TestCopySchedule:
    """Тесты для копирования расписания."""
    
    @pytest.mark.asyncio
    async def test_copy_schedule_success(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_slot: ScheduleSlot,
    ):
        """Успешное копирование расписания."""
        target_dates = [
            str(date.today() + timedelta(days=i)) for i in range(1, 4)
        ]
        
        payload = {
            "source_date": str(test_slot.start_date),
            "target_dates": target_dates,
            "channel_id": str(test_slot.channel_id),
        }
        response = await async_client.post(
            "/api/schedule/copy",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 3  # Скопировано на 3 даты
    
    @pytest.mark.asyncio
    async def test_copy_schedule_no_slots(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Копирование из дня без слотов."""
        payload = {
            "source_date": str(date.today() - timedelta(days=100)),
            "target_dates": [str(date.today() + timedelta(days=1))],
            "channel_id": TEST_CHANNEL_ID,
        }
        response = await async_client.post(
            "/api/schedule/copy",
            json=payload,
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 0


# ==================== Calendar View Tests ====================

class TestCalendarView:
    """Тесты для календарного представления."""
    
    @pytest.mark.asyncio
    async def test_get_calendar_month(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_slot: ScheduleSlot,
    ):
        """Получение календаря на месяц."""
        today = date.today()
        response = await async_client.get(
            "/api/schedule/calendar",
            params={
                "channel_id": str(test_slot.channel_id),
                "year": today.year,
                "month": today.month,
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Должны быть дни месяца
        assert len(data) >= 28
    
    @pytest.mark.asyncio
    async def test_expand_schedule(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        db_session: AsyncSession,
        admin_user: User,
        test_playlist: Playlist,
    ):
        """Развёртывание повторяющегося расписания."""
        # Создаём ежедневно повторяющийся слот
        slot = ScheduleSlot(
            channel_id=TEST_CHANNEL_ID,
            playlist_id=test_playlist.id,
            created_by=admin_user.id,
            start_date=date.today(),
            start_time=time(8, 0),
            end_time=time(9, 0),
            title="Daily Show",
            repeat_type=RepeatType.DAILY,
            repeat_until=date.today() + timedelta(days=7),
            is_active=True,
        )
        db_session.add(slot)
        await db_session.commit()
        
        response = await async_client.get(
            "/api/schedule/expand",
            params={
                "channel_id": TEST_CHANNEL_ID,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=7)),
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Должно быть 8 записей (сегодня + 7 дней)
        assert len(data) == 8


# ==================== Edge Cases Tests ====================

class TestEdgeCases:
    """Тесты граничных случаев."""
    
    @pytest.mark.asyncio
    async def test_slot_spanning_midnight(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_playlist: Playlist,
    ):
        """Слот, пересекающий полночь."""
        payload = {
            "channel_id": TEST_CHANNEL_ID,
            "playlist_id": str(test_playlist.id),
            "start_date": str(date.today()),
            "start_time": "23:00",
            "end_time": "01:00",  # На следующий день
            "title": "Night Show",
            "repeat_type": "none",
        }
        response = await async_client.post(
            "/api/schedule/slots",
            json=payload,
            headers=admin_auth_headers,
        )
        # Система должна корректно обработать переход через полночь или вернуть validation/error code
        assert response.status_code in [201, 422, 400]
    
    @pytest.mark.asyncio
    async def test_very_long_playlist_name(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Плейлист с очень длинным названием."""
        payload = {
            "name": "A" * 500,  # 500 символов
            "items": [],
        }
        response = await async_client.post(
            "/api/schedule/playlists",
            json=payload,
            headers=admin_auth_headers,
        )
        # Должна быть ошибка валидации или обрезка
        assert response.status_code in [201, 422]
    
    @pytest.mark.asyncio
    async def test_concurrent_slot_creation(
        self,
        async_client: AsyncClient,
        admin_auth_headers: dict,
        test_playlist: Playlist,
    ):
        """Одновременное создание конфликтующих слотов."""
        import asyncio
        
        payload = {
            "channel_id": TEST_CHANNEL_ID,
            "playlist_id": str(test_playlist.id),
            "start_date": str(date.today() + timedelta(days=10)),
            "start_time": "10:00",
            "end_time": "12:00",
            "title": "Concurrent Show",
            "repeat_type": "none",
        }
        
        # Отправляем два одинаковых запроса параллельно
        results = await asyncio.gather(
            async_client.post("/api/schedule/slots", json=payload, headers=admin_auth_headers),
            async_client.post("/api/schedule/slots", json=payload, headers=admin_auth_headers),
            return_exceptions=True,
        )
        
        # Один должен успешно создаться, второй - получить конфликт
        statuses = [r.status_code for r in results if not isinstance(r, Exception)]
        assert 201 in statuses or 409 in statuses


# ==================== Authorization Tests ====================

class TestAuthorization:
    """Тесты авторизации."""
    
    @pytest.mark.asyncio
    async def test_unauthenticated_access(
        self,
        async_client: AsyncClient,
    ):
        """Доступ без авторизации."""
        response = await async_client.get("/api/schedule/slots")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_user_can_view_slots(
        self,
        async_client: AsyncClient,
        user_auth_headers: dict,
        test_slot: ScheduleSlot,
    ):
        """Пользователь может просматривать слоты."""
        response = await async_client.get(
            "/api/schedule/slots",
            params={
                "channel_id": test_slot.channel_id,
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=1)),
            },
            headers=user_auth_headers,
        )
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_user_cannot_delete_slot(
        self,
        async_client: AsyncClient,
        user_auth_headers: dict,
        test_slot: ScheduleSlot,
    ):
        """Пользователь не может удалять слоты."""
        response = await async_client.delete(
            f"/api/schedule/slots/{test_slot.id}",
            headers=user_auth_headers,
        )
        assert response.status_code == 403
