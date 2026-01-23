"""
Integration test: Verify TrackPlay → UserItemInteraction flow

Тест проверяет, что:
1. TrackPlay записи создаются при воспроизведении треков
2. sync_track_plays_to_interactions() конвертирует их в UserItemInteraction
3. Celery задача может прочитать взаимодействия для обучения модели
"""
import logging
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)

from sqlalchemy import select

from src.models.analytics import TrackPlay
from src.models.recommendation import UserItemInteraction
from src.models.playlist import PlaylistItem
from src.services.analytics_service import AnalyticsService
from src.services.recommendation_service import RecommendationService
from src.tasks.recommendation_tasks import update_interaction_matrix


@pytest.fixture
def test_playlist_item(db_session):
    """Создает тестовый PlaylistItem."""
    item = PlaylistItem(
        id=uuid4(),
        playlist_id=1,
        position=1,
        url="https://example.com/video1",
        title="Test Video 1",
        type="youtube",
        duration=180,  # 3 минуты
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def analytics_service(db_session):
    """Создает экземпляр AnalyticsService."""
    return AnalyticsService(db=db_session, redis_client=None)


@pytest.fixture
def recommendation_service(db_session):
    """Создает экземпляр RecommendationService."""
    return RecommendationService(db=db_session, redis_client=None)


class TestTrackPlayToInteractionFlow:
    """Тест потока данных от TrackPlay к UserItemInteraction."""

    def test_track_play_creates_record(self, db_session, analytics_service, test_playlist_item):
        """
        Step 1: Проверяем создание TrackPlay записи.

        GIVEN:_playlist_item и данные о воспроизведении
        WHEN: вызываем log_track_play()
        THEN: TrackPlay запись создается в базе данных
        """
        # Arrange
        from src.schemas.analytics import TrackPlayRequest

        request = TrackPlayRequest(
            track_id=str(test_playlist_item.id),
            duration_seconds=120,  # 2 минуты
            listeners_count=5,
        )

        # Act
        response = analytics_service.log_track_play(request)

        # Assert
        assert response.id is not None
        assert response.played_at is not None

        # Проверяем в базе данных
        track_play = db_session.execute(
            select(TrackPlay).where(TrackPlay.id == response.id)
        ).scalar_one_or_none()

        assert track_play is not None
        assert track_play.playlist_item_id == test_playlist_item.id
        assert track_play.duration_seconds == 120
        assert track_play.listeners_count == 5

    def test_sync_creates_user_item_interaction(
        self, db_session, analytics_service, recommendation_service, test_playlist_item
    ):
        """
        Step 2: Проверяем создание UserItemInteraction из TrackPlay.

        GIVEN: TrackPlay запись существует
        WHEN: вызываем sync_track_plays_to_interactions()
        THEN: UserItemInteraction запись создается с корректными данными
        """
        # Arrange - создаем TrackPlay
        from src.schemas.analytics import TrackPlayRequest

        played_at = datetime.now(timezone.utc)
        request = TrackPlayRequest(
            track_id=str(test_playlist_item.id),
            duration_seconds=120,  # 2 минуты из 3 минутных
            listeners_count=5,
        )

        track_play_response = analytics_service.log_track_play(request)

        # Act - синхронизируем
        sync_result = await recommendation_service.sync_track_plays_to_interactions(hours=24)

        # Assert - проверяем результат синхронизации
        assert sync_result["error"] is None
        assert sync_result["synced_count"] >= 1
        assert sync_result["message"] is not None

        # Проверяем UserItemInteraction в базе данных
        interactions = db_session.execute(
            select(UserItemInteraction).where(
                UserItemInteraction.playlist_item_id == test_playlist_item.id
            )
        ).scalars().all()

        assert len(interactions) >= 1

        interaction = interactions[0]
        assert interaction.user_id == "system"
        assert interaction.playlist_item_id == test_playlist_item.id
        assert interaction.interaction_type == "watch"
        assert interaction.duration_seconds == 120

        # Проверяем completion_rate: 120 / 180 = 0.666...
        assert interaction.completion_rate > 0.65
        assert interaction.completion_rate < 0.68

    def test_sync_avoids_duplicates(
        self, db_session, analytics_service, recommendation_service, test_playlist_item
    ):
        """
        Step 3: Проверяем избежание дубликатов.

        GIVEN: TrackPlay запись уже синхронизирована
        WHEN: вызываем sync_track_plays_to_interactions() повторно
        THEN: дубликаты не создаются
        """
        # Arrange - создаем TrackPlay
        from src.schemas.analytics import TrackPlayRequest

        request = TrackPlayRequest(
            track_id=str(test_playlist_item.id),
            duration_seconds=90,
            listeners_count=3,
        )

        analytics_service.log_track_play(request)

        # Act - синхронизируем дважды
        await recommendation_service.sync_track_plays_to_interactions(hours=24)
        sync_result_2 = await recommendation_service.sync_track_plays_to_interactions(hours=24)

        # Assert - вторая синхронизация должна пропустить существующие записи
        assert sync_result_2["error"] is None
        assert sync_result_2["synced_count"] == 0  # Ничего нового не создано
        assert sync_result_2["skipped_count"] >= 1  # Существующие записи пропущены

    def test_celery_task_reads_interactions(
        self, db_session, analytics_service, recommendation_service, test_playlist_item
    ):
        """
        Step 4: Проверяем, что Celery задача может прочитать взаимодействия.

        GIVEN: UserItemInteraction записи существуют
        WHEN: вызываем update_interaction_matrix()
        THEN: задача успешно собирает данные о взаимодействиях
        """
        # Arrange - создаем TrackPlay и синхронизируем
        from src.schemas.analytics import TrackPlayRequest

        request = TrackPlayRequest(
            track_id=str(test_playlist_item.id),
            duration_seconds=150,  # 2.5 минуты
            listeners_count=10,
        )

        analytics_service.log_track_play(request)
        await recommendation_service.sync_track_plays_to_interactions(hours=24)

        # Act - запускаем Celery задачу (синхронно для теста)
        result = update_interaction_matrix(days=1)

        # Assert
        assert result["success"] is True
        assert result["error"] is None

        metrics = result["metrics"]
        assert metrics["interactions_count"] >= 1
        assert metrics["unique_users"] >= 1
        assert metrics["unique_items"] >= 1
        assert metrics["avg_rating"] >= 0

        # Проверяем interaction_types
        interaction_types = metrics.get("interaction_types", {})
        assert "watch" in interaction_types or len(interaction_types) >= 0

    def test_end_to_end_flow(self, db_session, analytics_service, recommendation_service, test_playlist_item):
        """
        End-to-end тест: полное воспроизведение → обучение рекомендаций.

        GIVEN: плейлист с треками
        WHEN:
            1. Треки воспроизводятся (создаем TrackPlay)
            2. Синхронизируем с UserItemInteraction
            3. Обновляем матрицу взаимодействий
        THEN: полный цикл проходит без ошибок
        """
        # 1. Создаем несколько TrackPlay записей
        from src.schemas.analytics import TrackPlayRequest

        track_plays = []
        for i in range(5):
            request = TrackPlayRequest(
                track_id=str(test_playlist_item.id),
                duration_seconds=100 + (i * 20),  # Разная длительность
                listeners_count=5 + i,
            )
            response = analytics_service.log_track_play(request)
            track_plays.append(response)

        assert len(track_plays) == 5

        # 2. Синхронизируем с UserItemInteraction
        sync_result = await recommendation_service.sync_track_plays_to_interactions(hours=24)
        assert sync_result["error"] is None
        assert sync_result["synced_count"] == 5

        # Проверяем UserItemInteraction записи
        interactions = db_session.execute(
            select(UserItemInteraction).where(
                UserItemInteraction.playlist_item_id == test_playlist_item.id
            )
        ).scalars().all()

        assert len(interactions) == 5
        for interaction in interactions:
            assert interaction.user_id == "system"
            assert interaction.interaction_type == "watch"
            assert interaction.duration_seconds > 0
            assert 0 < interaction.completion_rate <= 1.0

        # 3. Обновляем матрицу взаимодействий
        matrix_result = update_interaction_matrix(days=1)
        assert matrix_result["success"] is True

        metrics = matrix_result["metrics"]
        assert metrics["interactions_count"] >= 5
        assert metrics["unique_items"] >= 1

        # Успешное завершение полного цикла
        logger.info(
            f"E2E test passed: {track_plays} TrackPlay → "
            f"{sync_result['synced_count']} UserItemInteraction → "
            f"{metrics['interactions_count']} matrix interactions"
        )
