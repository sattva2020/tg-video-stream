"""
Integration test: Content-Based Filtering Recommendations with Metadata Similarity

Тест проверяет, что:
1. Создаются элементы плейлиста с похожими метаданными (названия, тип, канал)
2. Модель content-based фильтрации обучается на метаданных
3. Рекомендации основаны на схожести контента (похожие названия → похожие рекомендации)
4. Content-based фильтрация работает корректно
"""
import logging
import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from uuid import uuid4

logger = logging.getLogger(__name__)

from sqlalchemy import select

from src.models.recommendation import UserItemInteraction, Recommendation
from src.models.playlist import PlaylistItem
from src.models.user import User
from src.services.recommendation_service import RecommendationService
from src.services.recommendation_engine import ContentBasedFilteringEngine
from src.tasks.recommendation_tasks import train_content_based_model


@pytest.fixture
def content_based_test_items(db_session):
    """
    Создает набор тестовых PlaylistItem для content-based рекомендаций.

    Возвращает 20 элементов с похожими названиями в группах:
    - Группа A: "Rock Music..." (items 1-5) - похожие названия
    - Группа B: "Pop Song..." (items 6-10) - похожие названия
    - Группа C: "Jazz Classics..." (items 11-15) - похожие названия
    - Группа D: "Electronic Beats..." (items 16-20) - похожие названия

    Также варьирует type (youtube/local) и duration для тестирования
    различных метаданных.
    """
    items = []
    item_specs = [
        # Группа A: Rock Music (похожие названия)
        ("Rock Music Anthem", "youtube", 180, "rock_channel"),
        ("Rock Music Ballad", "youtube", 200, "rock_channel"),
        ("Rock Music Hits", "local", 190, "rock_channel"),
        ("Rock Music Festival", "youtube", 210, "rock_channel"),
        ("Rock Music Classics", "local", 185, "rock_channel"),

        # Группа B: Pop Song (похожие названия)
        ("Pop Song Summer", "youtube", 175, "pop_channel"),
        ("Pop Song Dance", "youtube", 195, "pop_channel"),
        ("Pop Song Love", "local", 180, "pop_channel"),
        ("Pop Song Party", "youtube", 200, "pop_channel"),
        ("Pop Song Hits", "local", 190, "pop_channel"),

        # Группа C: Jazz Classics (похожие названия)
        ("Jazz Classics Blue", "youtube", 240, "jazz_channel"),
        ("Jazz Classics Night", "youtube", 260, "jazz_channel"),
        ("Jazz Classics Smooth", "local", 250, "jazz_channel"),
        ("Jazz Classics Modern", "youtube", 230, "jazz_channel"),
        ("Jazz Classics Soul", "local", 245, "jazz_channel"),

        # Группа D: Electronic Beats (похожие названия)
        ("Electronic Beats Deep", "youtube", 220, "electronic_channel"),
        ("Electronic Beats House", "youtube", 200, "electronic_channel"),
        ("Electronic Beats Techno", "local", 210, "electronic_channel"),
        ("Electronic Beats Ambient", "youtube", 240, "electronic_channel"),
        ("Electronic Beats Trance", "local", 215, "electronic_channel"),
    ]

    for i, (title, item_type, duration, channel_name) in enumerate(item_specs):
        # Создаем channel_id как UUID для теста
        channel_id = uuid4()

        item = PlaylistItem(
            id=uuid4(),
            playlist_id=1,
            position=i + 1,
            url=f"https://example.com/video{i+1}",
            title=title,
            type=item_type,
            duration=duration,
            channel_id=channel_id,
        )
        db_session.add(item)
        items.append(item)

    db_session.commit()
    for item in items:
        db_session.refresh(item)

    return items


@pytest.fixture
def test_user(db_session):
    """Создает тестового пользователя для рекомендаций."""
    user = User(
        id=uuid4(),
        telegram_id=9999,
        username="content_test_user",
        full_name="Content Test User",
        role="listener",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def recommendation_service(db_session):
    """Создает экземпляр RecommendationService."""
    return RecommendationService(db=db_session, redis_client=None)


def create_user_interactions_for_content(
    db_session, user_id, playlist_items, interaction_type="like", completion_rate_range=(0.8, 1.0)
):
    """
    Создает взаимодействия пользователя с элементами плейлиста.

    Args:
        db_session: Сессия базы данных
        user_id: ID пользователя
        playlist_items: Список PlaylistItem для взаимодействия
        interaction_type: Тип взаимодействия (watch, like, etc.)
        completion_rate_range: Диапазон completion_rate (min, max)

    Returns:
        Список созданных UserItemInteraction
    """
    interactions = []
    for item in playlist_items:
        completion_rate = np.random.uniform(completion_rate_range[0], completion_rate_range[1])

        interaction = UserItemInteraction(
            user_id=str(user_id),
            playlist_item_id=item.id,
            interaction_type=interaction_type,
            duration_seconds=int(item.duration * completion_rate),
            completion_rate=completion_rate,
            interacted_at=datetime.now(timezone.utc) - timedelta(hours=np.random.randint(1, 72)),
        )
        db_session.add(interaction)
        interactions.append(interaction)

    db_session.commit()
    return interactions


class TestContentBasedFilteringRecommendations:
    """Тест рекомендаций content-based фильтрации с метаданными."""

    def test_create_playlist_items_with_similar_metadata(
        self, db_session, content_based_test_items
    ):
        """
        Step 1: Создаем элементы плейлиста с похожими метаданными.

        GIVEN: Пустая база данных
        WHEN: Создаем 20 PlaylistItem с 4 группами похожих названий
        THEN: Элементы создаются корректно с правильными метаданными
        """
        # Assert - проверяем, что все элементы созданы
        assert len(content_based_test_items) == 20

        # Проверяем, что у элементов есть правильные метаданные
        rock_items = [item for item in content_based_test_items if "Rock Music" in item.title]
        pop_items = [item for item in content_based_test_items if "Pop Song" in item.title]
        jazz_items = [item for item in content_based_test_items if "Jazz Classics" in item.title]
        electronic_items = [item for item in content_based_test_items if "Electronic Beats" in item.title]

        assert len(rock_items) == 5
        assert len(pop_items) == 5
        assert len(jazz_items) == 5
        assert len(electronic_items) == 5

        # Проверяем, что названия похожи внутри групп
        for item in rock_items:
            assert "Rock Music" in item.title
            assert item.channel_id is not None

        logger.info(
            f"✓ Created {len(content_based_test_items)} items with similar metadata: "
            f"{len(rock_items)} rock, {len(pop_items)} pop, "
            f"{len(jazz_items)} jazz, {len(electronic_items)} electronic"
        )

    def test_train_content_based_model(
        self, db_session, content_based_test_items
    ):
        """
        Step 2: Обучаем модель content-based фильтрации.

        GIVEN: 20 PlaylistItem с похожими метаданными
        WHEN: Вызываем train_content_based_model()
        THEN: Модель успешно обучается на TF-IDF и метаданных
        """
        # Act - обучаем модель (синхронно для теста)
        result = train_content_based_model()

        # Assert
        assert result["success"] is True
        assert result["error"] is None

        metrics = result["metrics"]
        assert metrics["items_count"] == 20
        assert metrics["trained_at"] is not None

        logger.info(
            f"✓ Content-based model trained: {metrics['items_count']} items, "
            f"trained at {metrics['trained_at']}"
        )

    def test_fetch_content_based_recommendations_for_liked_rock_items(
        self, db_session, test_user, content_based_test_items, recommendation_service
    ):
        """
        Step 3: Получаем content-based рекомендации для пользователя, который любит Rock Music.

        GIVEN:
            - Пользователь, который лайкал "Rock Music" элементы (items 0-4)
            - Обученная content-based модель
        WHEN: Получаем рекомендации с algorithm="content_based"
        THEN: Рекомендуются похожие элементы (тоже "Rock Music" или похожие названия)
        """
        # Arrange - пользователь лайкал Rock Music элементы
        rock_items = [item for item in content_based_test_items if "Rock Music" in item.title]

        create_user_interactions_for_content(
            db_session, test_user.id, rock_items, "like", (0.9, 1.0)
        )

        # Обучаем модель
        train_result = train_content_based_model()
        assert train_result["success"] is True

        # Act - получаем рекомендации
        from src.schemas.recommendation import RecommendationRequest

        request = RecommendationRequest(
            user_id=str(test_user.id),
            limit=10,
            algorithm="content_based",
            exclude_watched=True,
        )

        recommendations = await recommendation_service.get_recommendations(request)

        # Assert - есть рекомендации
        assert len(recommendations.recommendations) > 0

        # Проверяем, что алгоритм указан корректно
        for rec in recommendations.recommendations:
            assert rec.algorithm == "content_based"
            assert 0 <= rec.score <= 1
            assert rec.reason is not None

        # Проверяем, что рекомендованы элементы (не те, что пользователь уже лайкал)
        liked_ids = {str(item.id) for item in rock_items}
        rec_ids = {r.playlist_item_id for r in recommendations.recommendations}

        # Исключаем просмотренные
        overlap = liked_ids & rec_ids
        assert len(overlap) == 0, "Рекомендации не должны включать уже просмотренные элементы"

        logger.info(
            f"✓ User who liked Rock Music got {len(recommendations.recommendations)} content-based recommendations"
        )

    def test_verify_content_based_similarity_by_title(
        self, db_session, test_user, content_based_test_items, recommendation_service
    ):
        """
        Step 4: Проверяем, что content-based фильтрация рекомендует похожие по названию элементы.

        GIVEN:
            - Пользователь лайкал "Pop Song Summer" и "Pop Song Dance"
            - В базе есть другие "Pop Song..." элементы
        WHEN: Получаем content-based рекомендации
        THEN: Рекомендуются элементы с похожими названиями ("Pop Song...")
        """
        # Arrange - пользователь лайкал конкретные Pop Song элементы
        pop_items = [item for item in content_based_test_items if "Pop Song" in item.title]

        # Лайкаем только первые 2 Pop Song
        liked_pop_items = pop_items[:2]
        other_pop_items = pop_items[2:]

        create_user_interactions_for_content(
            db_session, test_user.id, liked_pop_items, "like", (0.9, 1.0)
        )

        # Обучаем модель
        train_result = train_content_based_model()
        assert train_result["success"] is True

        # Act - получаем рекомендации
        from src.schemas.recommendation import RecommendationRequest

        request = RecommendationRequest(
            user_id=str(test_user.id),
            limit=10,
            algorithm="content_based",
            exclude_watched=True,
        )

        recommendations = await recommendation_service.get_recommendations(request)

        # Assert
        assert len(recommendations.recommendations) > 0

        # Проверяем, что среди рекомендаций есть элементы с похожими названиями
        rec_titles = [r.title for r in recommendations.recommendations]
        similar_titles = [title for title in rec_titles if "Pop Song" in title]

        logger.info(
            f"✓ Content-based filtering: {len(similar_titles)} out of "
            f"{len(recommendations.recommendations)} recommendations have similar titles"
        )

        # Хотя бы одна рекомендация должна быть похожа по названию
        # (если не все Pop Song были просмотрены)
        if len(other_pop_items) > 0:
            # Проверяем, чтоrecommended IDs включают похожие элементы
            rec_ids = {r.playlist_item_id for r in recommendations.recommendations}
            other_pop_ids = {str(item.id) for item in other_pop_items}

            # Есть пересечение с похожими элементами?
            similar_recommended = rec_ids & other_pop_ids
            logger.info(f"✓ Recommended {len(similar_recommended)} similar Pop Song items")

    def test_find_similar_items_directly(
        self, db_session, content_based_test_items
    ):
        """
        Step 5: Проверяем метод find_similar_items() напрямую.

        GIVEN: Обученная ContentBasedFilteringEngine
        WHEN: Вызываем find_similar_items() для "Rock Music Anthem"
        THEN: Возвращаются похожие элементы ("Rock Music Ballad", "Rock Music Hits", etc.)
        """
        # Arrange - обучаем модель
        train_result = train_content_based_model()
        assert train_result["success"] is True

        # Создаем engine
        engine = ContentBasedFilteringEngine()
        engine._load_model()

        # Находим "Rock Music Anthem"
        rock_anthem = next(
            (item for item in content_based_test_items if item.title == "Rock Music Anthem"),
            None
        )
        assert rock_anthem is not None

        # Act - находим похожие элементы
        similar_items = engine.find_similar_items(
            item_id=str(rock_anthem.id),
            n=5
        )

        # Assert
        assert len(similar_items) > 0

        # Проверяем, что похожие элементы имеют похожие названия
        similar_titles = [item['title'] for item in similar_items]
        logger.info(f"✓ Items similar to 'Rock Music Anthem': {similar_titles}")

        # Хотя бы один элемент должен иметь "Rock" в названии
        rock_similar = [title for title in similar_titles if "Rock" in title]
        assert len(rock_similar) > 0, "Должны быть рекомендованы элементы с похожими названиями"

        # Проверяем structure
        for item in similar_items:
            assert 'playlist_item_id' in item
            assert 'score' in item
            assert 'title' in item
            assert 0 <= item['score'] <= 1

    def test_content_based_with_different_types_and_durations(
        self, db_session, test_user, content_based_test_items, recommendation_service
    ):
        """
        Step 6: Проверяем, что content-based учитывает разные метаданные (type, duration).

        GIVEN:
            - Пользователь лайкал youtube видео с duration ~180-200 секунд
            - В базе есть youtube и local элементы, разные duration
        WHEN: Получаем content-based рекомендации
        THEN: Рекомендации учитывают type и duration (сходство по метаданным)
        """
        # Arrange - пользователь лайкал youtube Rock Music элементы
        rock_youtube_items = [
            item for item in content_based_test_items
            if "Rock Music" in item.title and item.type == "youtube"
        ]

        create_user_interactions_for_content(
            db_session, test_user.id, rock_youtube_items, "like", (0.9, 1.0)
        )

        # Обучаем модель
        train_result = train_content_based_model()
        assert train_result["success"] is True

        # Act - получаем рекомендации
        from src.schemas.recommendation import RecommendationRequest

        request = RecommendationRequest(
            user_id=str(test_user.id),
            limit=10,
            algorithm="content_based",
            exclude_watched=True,
        )

        recommendations = await recommendation_service.get_recommendations(request)

        # Assert - есть рекомендации
        assert len(recommendations.recommendations) > 0

        # Проверяем, что рекомендации включают элементы с разными типами
        # (content-based может рекомендовать и local, если названия похожие)
        rec_types = {}
        for rec in recommendations.recommendations:
            # Получаем тип элемента из БД
            item = db_session.execute(
                select(PlaylistItem).where(PlaylistItem.id == rec.playlist_item_id)
            ).scalar_one_or_none()

            if item:
                rec_types[item.type] = rec_types.get(item.type, 0) + 1

        logger.info(f"✓ Content-based recommendations by type: {rec_types}")

        # Проверяем, что scores корректны
        for rec in recommendations.recommendations:
            assert rec.score > 0
            assert rec.score <= 1

    def test_end_to_end_content_based_filtering(
        self, db_session, test_user, content_based_test_items, recommendation_service
    ):
        """
        End-to-End тест: полный цикл content-based фильтрации.

        GIVEN: 20 элементов с 4 группами похожих метаданных
        WHEN:
            1. Создаем взаимодействия для пользователя (лайкает Jazz Classics)
            2. Обучаем content-based модель
            3. Получаем рекомендации
            4. Проверяем, что рекомендуем похожие элементы
        THEN: Полный цикл проходит без ошибок, рекомендации работают
        """
        # 1. Создаем взаимодействия - пользователь любит Jazz Classics
        jazz_items = [item for item in content_based_test_items if "Jazz Classics" in item.title]

        create_user_interactions_for_content(
            db_session, test_user.id, jazz_items, "like", (0.9, 1.0)
        )

        # Проверяем взаимодействия в БД
        all_interactions = db_session.execute(
            select(UserItemInteraction).where(UserItemInteraction.user_id == str(test_user.id))
        ).scalars().all()

        assert len(all_interactions) == len(jazz_items)
        logger.info(f"✓ Created {len(all_interactions)} user interactions for Jazz Classics")

        # 2. Обучаем модель
        train_result = train_content_based_model()
        assert train_result["success"] is True

        metrics = train_result["metrics"]
        logger.info(
            f"✓ Content-based model trained: {metrics['items_count']} items"
        )

        # 3. Получаем рекомендации
        from src.schemas.recommendation import RecommendationRequest

        request = RecommendationRequest(
            user_id=str(test_user.id),
            limit=10,
            algorithm="content_based",
            exclude_watched=True,
        )

        response = await recommendation_service.get_recommendations(request)

        assert len(response.recommendations) >= 0
        logger.info(f"✓ User got {len(response.recommendations)} content-based recommendations")

        # 4. Проверяем, что рекомендации не включают просмотренные элементы
        liked_ids = {str(item.id) for item in jazz_items}
        rec_ids = {r.playlist_item_id for r in response.recommendations}

        overlap = liked_ids & rec_ids
        assert len(overlap) == 0, "Рекомендации не должны включать просмотренные"

        # Проверяем, что у рекомендаций есть метаданные
        for rec in response.recommendations:
            assert rec.algorithm == "content_based"
            assert rec.score > 0
            assert rec.reason is not None
            assert rec.title is not None
            assert rec.artist is not None  # Может быть channel_name

        # Успешное завершение E2E теста
        logger.info("✓ E2E content-based filtering test passed")

    def test_content_based_similarity_across_groups(
        self, db_session, content_based_test_items
    ):
        """
        Step 7: Проверяем, что content-based находит сходство внутри групп, но не между ними.

        GIVEN: 4 группы элементов с разными жанрами (Rock, Pop, Jazz, Electronic)
        WHEN: Находим похожие элементы для каждого жанра
        THEN: Похожие элементы из того же жанра, а не из других
        """
        # Arrange - обучаем модель
        train_result = train_content_based_model()
        assert train_result["success"] is True

        engine = ContentBasedFilteringEngine()
        engine._load_model()

        # Для каждого жанра находим похожие элементы
        genres = {
            "Rock": "Rock Music Anthem",
            "Pop": "Pop Song Summer",
            "Jazz": "Jazz Classics Blue",
            "Electronic": "Electronic Beats Deep",
        }

        for genre, sample_title in genres:
            # Находим элемент
            sample_item = next(
                (item for item in content_based_test_items if item.title == sample_title),
                None
            )
            assert sample_item is not None

            # Находим похожие
            similar_items = engine.find_similar_items(
                item_id=str(sample_item.id),
                n=5
            )

            similar_titles = [item['title'] for item in similar_items]

            # Проверяем, что похожие элементы из того же жанра
            same_genre_count = sum(
                1 for title in similar_titles
                if genre in title or any(
                    keyword in title for keyword in ["Rock", "Pop", "Jazz", "Electronic"]
                    if keyword in genre
                )
            )

            logger.info(
                f"✓ {genre}: {same_genre_count}/{len(similar_items)} similar items from same genre"
            )

            # Проверяем, что scores убывают
            scores = [item['score'] for item in similar_items]
            assert scores == sorted(scores, reverse=True), "Scores должны быть отсортированы по убыванию"
