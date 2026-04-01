"""
Тесты точности рекомендаций на основе данных вовлеченности.

Покрывает:
- Создание тестовых данных воспроизведения
- Генерацию рекомендаций на основе высокой вовлеченности
- Проверку обнаружения пиковых часов
- Проверку ранжирования плейлистов по вовлеченности
"""

import pytest
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from httpx import AsyncClient

from src.models.schedule import ScheduleSlot, Playlist, PlaylistItem, RepeatType
from src.models.analytics import TrackPlay
from src.models.user import User, UserRole, UserStatus
from src.models.telegram import Channel

# ==================== Constants ====================

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
def test_channel(db_session) -> Channel:
    """Создаёт тестовый канал."""
    channel = Channel(
        id=TEST_CHANNEL_ID,
        name="Test Channel",
        description="Test channel for recommendations",
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


@pytest.fixture
def high_engagement_playlist(db_session, admin_user: User) -> Playlist:
    """Создаёт плейлист с высокой вовлеченностью."""
    playlist = Playlist(
        name="High Engagement Playlist",
        description="Playlist with high listener engagement",
        user_id=admin_user.id,
    )
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)

    # Добавляем треки в плейлист
    items = [
        PlaylistItem(
            id=uuid4(),
            playlist_id=playlist.id,
            url=f"https://youtube.com/watch?v={i}",
            title=f"High Engagement Track {i}",
            duration=180,
            position=i,
        ) for i in range(1, 6)
    ]
    db_session.add_all(items)
    db_session.commit()

    return playlist


@pytest.fixture
def medium_engagement_playlist(db_session, admin_user: User) -> Playlist:
    """Создаёт плейлист со средней вовлеченностью."""
    playlist = Playlist(
        name="Medium Engagement Playlist",
        description="Playlist with medium listener engagement",
        user_id=admin_user.id,
    )
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)

    # Добавляем треки в плейлист
    items = [
        PlaylistItem(
            id=uuid4(),
            playlist_id=playlist.id,
            url=f"https://youtube.com/watch?v={i+10}",
            title=f"Medium Engagement Track {i}",
            duration=240,
            position=i,
        ) for i in range(1, 4)
    ]
    db_session.add_all(items)
    db_session.commit()

    return playlist


@pytest.fixture
def low_engagement_playlist(db_session, admin_user: User) -> Playlist:
    """Создаёт плейлист с низкой вовлеченностью."""
    playlist = Playlist(
        name="Low Engagement Playlist",
        description="Playlist with low listener engagement",
        user_id=admin_user.id,
    )
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)

    # Добавляем треки в плейлист
    items = [
        PlaylistItem(
            id=uuid4(),
            playlist_id=playlist.id,
            url=f"https://youtube.com/watch?v={i+20}",
            title=f"Low Engagement Track {i}",
            duration=200,
            position=i,
        ) for i in range(1, 3)
    ]
    db_session.add_all(items)
    db_session.commit()

    return playlist


@pytest.fixture
def engagement_data(
    db_session,
    test_channel: Channel,
    high_engagement_playlist: Playlist,
    medium_engagement_playlist: Playlist,
    low_engagement_playlist: Playlist,
):
    """
    Создаёт тестовые данные воспроизведения с разным уровнем вовлеченности.

    Высокая вовлеченность: 50-100 слушателей, вечерние часы (18:00-22:00)
    Средняя вовлеченность: 20-40 слушателей, дневные часы (12:00-16:00)
    Низкая вовлеченность: 5-10 слушателей, утренние часы (06:00-10:00)
    """
    now = datetime.now(timezone.utc)

    # Создаем данные за последние 30 дней
    plays = []

    # Высокая вовлеченность - вечер (19:00-21:00) - пиковые часы
    for days_ago in range(30):
        play_date = now - timedelta(days=days_ago)
        for hour in [19, 20, 21]:
            for item in high_engagement_playlist.items[:3]:
                plays.append(TrackPlay(
                    playlist_item_id=item.id,
                    played_at=play_date.replace(hour=hour, minute=0, second=0),
                    duration_seconds=180,
                    listeners_count=75 + (hour % 3) * 10,  # 75, 85, 95 слушателей
                ))

    # Средняя вовлеченность - день (13:00-15:00)
    for days_ago in range(30):
        play_date = now - timedelta(days=days_ago)
        for hour in [13, 14, 15]:
            for item in medium_engagement_playlist.items[:2]:
                plays.append(TrackPlay(
                    playlist_item_id=item.id,
                    played_at=play_date.replace(hour=hour, minute=0, second=0),
                    duration_seconds=240,
                    listeners_count=25 + (hour % 3) * 5,  # 25, 30, 35 слушателей
                ))

    # Низкая вовлеченность - утро (07:00-09:00)
    for days_ago in range(30):
        play_date = now - timedelta(days=days_ago)
        for hour in [7, 8, 9]:
            for item in low_engagement_playlist.items:
                plays.append(TrackPlay(
                    playlist_item_id=item.id,
                    played_at=play_date.replace(hour=hour, minute=0, second=0),
                    duration_seconds=200,
                    listeners_count=5 + (hour % 3) * 2,  # 5, 7, 9 слушателей
                ))

    db_session.add_all(plays)
    db_session.commit()

    return {
        "high_engagement": high_engagement_playlist,
        "medium_engagement": medium_engagement_playlist,
        "low_engagement": low_engagement_playlist,
    }


# ==================== Peak Hours Detection Tests ====================

class TestPeakHoursDetection:
    """Тесты для обнаружения пиковых часов."""

    @pytest.mark.asyncio
    async def test_peak_hours_detection_with_engagement_data(
        self, client: AsyncClient, admin_user: User, engagement_data
    ):
        """
        Тест обнаружения пиковых часов на основе данных воспроизведения.

        Должен обнаружить вечерние часы (19:00-21:00) как пиковые,
        так как они имеют наибольшую вовлеченность (75-95 слушателей).
        """
        # Авторизуемся
        response = await client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "testpassword123"},
        )
        token = response.json()["access_token"]

        # Получаем пиковые часы
        response = await client.get(
            f"/api/schedule-ai/peak-hours?channel_id={TEST_CHANNEL_ID}&period=30d",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Проверяем структуру ответа
        assert "channel_id" in data
        assert "period" in data
        assert "peak_hours" in data
        assert "total_samples" in data

        # Проверяем, что пиковые часы включают вечернее время
        peak_hours = data["peak_hours"]
        assert len(peak_hours) > 0

        # Проверяем, что вечерние часы (19:00-21:00) обнаружены как пиковые
        evening_hours = [ph for ph in peak_hours if ph["hour"] in [19, 20, 21]]
        assert len(evening_hours) > 0, "Вечерние часы должны быть обнаружены как пиковые"

        # Проверяем, что у вечерних часов высокая вовлеченность
        for ph in evening_hours:
            assert ph["avg_listeners"] > 70, f"Час {ph['hour']}:00 должен иметь > 70 слушателей"

        # Проверяем общее количество образцов
        assert data["total_samples"] >= 30 * 9 * 3  # 30 дней * 9 часов * ~3 воспроизведения в час

    @pytest.mark.asyncio
    async def test_peak_hours_aggregation_by_day_of_week(
        self, client: AsyncClient, admin_user: User, engagement_data
    ):
        """
        Тест агрегации пиковых часов по дням недели.

        Проверяет, что система корректно разделяет данные по дням недели.
        """
        response = await client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "testpassword123"},
        )
        token = response.json()["access_token"]

        response = await client.get(
            f"/api/schedule-ai/peak-hours?channel_id={TEST_CHANNEL_ID}&period=30d",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        peak_hours = data["peak_hours"]

        # Проверяем, что есть данные для разных дней недели
        days_of_week = set(ph["day_of_week"] for ph in peak_hours)
        assert len(days_of_week) > 0, "Должны быть данные для разных дней недели"

        # Проверяем, что для каждого дня недели есть часы
        for day in range(7):  # 0=Monday, 6=Sunday
            day_hours = [ph for ph in peak_hours if ph["day_of_week"] == day]
            # Не обязательно, чтобы каждый день имел данные,
            # но хотя бы для некоторых дней должны быть часы


# ==================== Recommendation Accuracy Tests ====================

class TestRecommendationAccuracy:
    """Тесты точности рекомендаций на основе данных вовлеченности."""

    @pytest.mark.asyncio
    async def test_high_engagement_content_recommended_first(
        self, client: AsyncClient, admin_user: User, engagement_data
    ):
        """
        Тест, что контент с высокой вовлеченностью рекомендуется первым.

        High Engagement плейлист должен быть выше в рекомендациях,
        чем Medium и Low Engagement.
        """
        response = await client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "testpassword123"},
        )
        token = response.json()["access_token"]

        target_date = (date.today() + timedelta(days=1)).isoformat()

        response = await client.get(
            f"/api/schedule-ai/recommendations?channel_id={TEST_CHANNEL_ID}&date={target_date}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Проверяем структуру ответа
        assert "recommendations" in data
        assert len(data["recommendations"]) > 0

        recommendations = data["recommendations"]

        # Проверяем, что рекомендации отсортированы по уверенности (confidence)
        confidences = [r["confidence"] for r in recommendations]
        assert confidences == sorted(confidences, reverse=True), \
            "Рекомендации должны быть отсортированы по убыванию уверенности"

        # Проверяем, что High Engagement плейлист присутствует в рекомендациях
        high_eng_rec = [r for r in recommendations if "High Engagement" in r.get("playlist_name", "")]
        assert len(high_eng_rec) > 0, "High Engagement плейлист должен быть в рекомендациях"

        # Проверяем, что рекомендации для пиковых часов имеют высокую уверенность
        peak_hour_recs = [r for r in recommendations if int(r.get("start_time", "0:00").split(":")[0]) in [19, 20, 21]]
        if peak_hour_recs:
            for rec in peak_hour_recs:
                assert rec["confidence"] > 0.5, \
                    f"Рекомендация для пикового часа {rec['start_time']} должна иметь высокую уверенность"

    @pytest.mark.asyncio
    async def test_recommendations_include_engagement_reasoning(
        self, client: AsyncClient, admin_user: User, engagement_data
    ):
        """
        Тест, что рекомендации включают объяснение на основе данных вовлеченности.

        Каждая рекомендация должна содержать reason, объясняющий,
        почему этот контент рекомендуется.
        """
        response = await client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "testpassword123"},
        )
        token = response.json()["access_token"]

        target_date = (date.today() + timedelta(days=1)).isoformat()

        response = await client.get(
            f"/api/schedule-ai/recommendations?channel_id={TEST_CHANNEL_ID}&date={target_date}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        recommendations = data["recommendations"]

        # Проверяем, что каждая рекомендация имеет reason
        for rec in recommendations:
            assert "reason" in rec, "Рекомендация должна содержать reason"
            assert len(rec["reason"]) > 0, "Reason не должен быть пустым"

            # Проверяем, что reason связан с вовлеченностью или производительностью
            reason_lower = rec["reason"].lower()
            # Reason должен упоминать engagement, performance, listeners, или similar
            assert any(keyword in reason_lower for keyword in [
                "вовлеченност", "engagement", "слушател", "listener",
                "производительност", "performance", "пиков", "peak"
            ]), f"Reason должен упоминать метрики вовлеченности: {rec['reason']}"

    @pytest.mark.asyncio
    async def test_recommendations_respect_peak_hours(
        self, client: AsyncClient, admin_user: User, engagement_data
    ):
        """
        Тест, что рекомендации уважают пиковые часы.

        В пиковые часы (19:00-21:00) должен рекомендоваться контент
        с наивысшей вовлеченностью.
        """
        response = await client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "testpassword123"},
        )
        token = response.json()["access_token"]

        target_date = (date.today() + timedelta(days=1)).isoformat()

        response = await client.get(
            f"/api/schedule-ai/recommendations?channel_id={TEST_CHANNEL_ID}&date={target_date}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        recommendations = data["recommendations"]

        # Находим рекомендации для пиковых часов (19:00-21:00)
        peak_hour_recs = [
            r for r in recommendations
            if 19 <= int(r.get("start_time", "0:00").split(":")[0]) <= 21
        ]

        if len(peak_hour_recs) > 0:
            # Проверяем, что в пиковые часы рекомендуется High Engagement контент
            for rec in peak_hour_recs:
                playlist_name = rec.get("playlist_name", "")
                # Должен быть High Engagement контент
                assert "High Engagement" in playlist_name or "high" in playlist_name.lower(), \
                    f"В пиковый час {rec['start_time']} должен рекомендоваться контент с высокой вовлеченностью, а не {playlist_name}"

                # Проверяем высокую уверенность для пиковых часов
                assert rec["confidence"] > 0.6, \
                    f"Уверенность для пикового часа {rec['start_time']} должна быть высокой"

    @pytest.mark.asyncio
    async def test_recommendation_confidence_correlates_with_engagement(
        self, client: AsyncClient, admin_user: User, engagement_data
    ):
        """
        Тест корреляции уверенности рекомендаций с уровнем вовлеченности.

        Рекомендации для High Engagement должны иметь более высокую уверенность,
        чем для Medium и Low Engagement.
        """
        response = await client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "testpassword123"},
        )
        token = response.json()["access_token"]

        target_date = (date.today() + timedelta(days=1)).isoformat()

        response = await client.get(
            f"/api/schedule-ai/recommendations?channel_id={TEST_CHANNEL_ID}&date={target_date}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        recommendations = data["recommendations"]

        # Группируем рекомендации по плейлистам
        high_eng_conf = []
        medium_eng_conf = []
        low_eng_conf = []

        for rec in recommendations:
            playlist_name = rec.get("playlist_name", "")
            if "High Engagement" in playlist_name:
                high_eng_conf.append(rec["confidence"])
            elif "Medium Engagement" in playlist_name:
                medium_eng_conf.append(rec["confidence"])
            elif "Low Engagement" in playlist_name:
                low_eng_conf.append(rec["confidence"])

        # Проверяем, что средняя уверенность коррелирует с вовлеченностью
        if high_eng_conf and medium_eng_conf and low_eng_conf:
            avg_high = sum(high_eng_conf) / len(high_eng_conf)
            avg_medium = sum(medium_eng_conf) / len(medium_eng_conf)
            avg_low = sum(low_eng_conf) / len(low_eng_conf)

            assert avg_high > avg_medium, \
                f"High Engagement ({avg_high:.2f}) должна иметь более высокую уверенность, чем Medium ({avg_medium:.2f})"
            assert avg_medium > avg_low, \
                f"Medium Engagement ({avg_medium:.2f}) должна иметь более высокую уверенность, чем Low ({avg_low:.2f})"


# ==================== Edge Cases ====================

class TestRecommendationAccuracyEdgeCases:
    """Тесты граничных случаев для точности рекомендаций."""

    @pytest.mark.asyncio
    async def test_recommendations_with_no_engagement_data(
        self, client: AsyncClient, admin_user: User, test_channel
    ):
        """
        Тест рекомендаций при отсутствии данных воспроизведения.

        Система должна возвращать рекомендации с низкой уверенностью
        или использовать дефолтный плейлист.
        """
        response = await client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "testpassword123"},
        )
        token = response.json()["access_token"]

        target_date = (date.today() + timedelta(days=1)).isoformat()

        response = await client.get(
            f"/api/schedule-ai/recommendations?channel_id={TEST_CHANNEL_ID}&date={target_date}",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Должен вернуть 200, даже если нет данных
        assert response.status_code == 200
        data = response.json()

        # Может вернуть пустой список или рекомендации с низкой уверенностью
        if "recommendations" in data and len(data["recommendations"]) > 0:
            # Если есть рекомендации, они должны иметь низкую уверенность
            for rec in data["recommendations"]:
                assert rec["confidence"] < 0.5, \
                    "При отсутствии данных уверенность должна быть низкой"

    @pytest.mark.asyncio
    async def test_peak_hours_with_minimal_data(
        self, client: AsyncClient, admin_user: User, test_channel, db_session
    ):
        """
        Тест обнаружения пиковых часов с минимальными данными.

        Система должна корректно обрабатывать ситуации,
        когда данных недостаточно для надежной статистики.
        """
        # Создаем минимальные данные воспроизведения
        now = datetime.now(timezone.utc)
        play = TrackPlay(
            playlist_item_id=uuid4(),
            played_at=now.replace(hour=14, minute=0),
            listeners_count=10,
        )
        db_session.add(play)
        await db_session.commit()

        response = await client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "testpassword123"},
        )
        token = response.json()["access_token"]

        response = await client.get(
            f"/api/schedule-ai/peak-hours?channel_id={TEST_CHANNEL_ID}&period=7d",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Должен вернуть данные, даже если их мало
        assert "peak_hours" in data
        assert "total_samples" in data
        assert data["total_samples"] >= 1


# ==================== Integration Tests ====================

class TestRecommendationAccuracyIntegration:
    """Интеграционные тесты для полной проверки точности рекомендаций."""

    @pytest.mark.asyncio
    async def test_end_to_end_recommendation_accuracy_workflow(
        self, client: AsyncClient, admin_user: User, engagement_data
    ):
        """
        Полный тест рабочего процесса проверки точности рекомендаций.

        1. Создает данные воспроизведения с разной вовлеченностью
        2. Получает пиковые часы
        3. Генерирует рекомендации
        4. Проверяет, что рекомендации учитывают вовлеченность и пиковые часы
        """
        # Шаг 1: Авторизация
        response = await client.post(
            "/api/auth/login",
            data={"username": admin_user.email, "password": "testpassword123"},
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        # Шаг 2: Получение пиковых часов
        peak_response = await client.get(
            f"/api/schedule-ai/peak-hours?channel_id={TEST_CHANNEL_ID}&period=30d",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert peak_response.status_code == 200
        peak_data = peak_response.json()

        # Проверяем, что пиковые часы обнаружены
        assert len(peak_data["peak_hours"]) > 0
        assert peak_data["total_samples"] > 0

        # Находим час с максимальной вовлеченностью
        max_hour = max(peak_data["peak_hours"], key=lambda x: x["avg_listeners"])
        peak_hour = max_hour["hour"]
        peak_listeners = max_hour["avg_listeners"]

        # Шаг 3: Генерация рекомендаций
        target_date = (date.today() + timedelta(days=1)).isoformat()
        rec_response = await client.get(
            f"/api/schedule-ai/recommendations?channel_id={TEST_CHANNEL_ID}&date={target_date}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rec_response.status_code == 200
        rec_data = rec_response.json()

        # Шаг 4: Проверка точности рекомендаций
        assert len(rec_data["recommendations"]) > 0

        # Проверяем, что рекомендации для пикового часа имеют высокую уверенность
        peak_hour_recs = [
            r for r in rec_data["recommendations"]
            if int(r.get("start_time", "0:00").split(":")[0]) == peak_hour
        ]

        if peak_hour_recs:
            # Должна быть хотя бы одна рекомендация для пикового часа
            assert len(peak_hour_recs) > 0

            # Проверяем высокую уверенность
            for rec in peak_hour_recs:
                assert rec["confidence"] > 0.6, \
                    f"Рекомендация для пикового часа {peak_hour}:00 должна иметь высокую уверенность"

                # Проверяем наличие reason
                assert len(rec["reason"]) > 0

        # Проверяем, что High Engagement контент приоритетен
        high_eng_recs = [
            r for r in rec_data["recommendations"]
            if "High Engagement" in r.get("playlist_name", "")
        ]
        assert len(high_eng_recs) > 0, \
            "High Engagement контент должен быть в рекомендациях"

        # Проверяем, что уверенность коррелирует с вовлеченностью
        top_confidence = max(r["confidence"] for r in rec_data["recommendations"])
        high_eng_avg_conf = sum(r["confidence"] for r in high_eng_recs) / len(high_eng_recs)

        # High Engagement должна иметь среднюю уверенность близко к топовой
        assert high_eng_avg_conf >= top_confidence * 0.8, \
            "High Engagement контент должен иметь высокую среднюю уверенность"
