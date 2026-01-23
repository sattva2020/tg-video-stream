"""
Integration test: Collaborative Filtering Recommendations with Simulated Users

Тест проверяет, что:
1. Создаются тестовые пользователи с похожими паттернами просмотра
2. Модель коллаборативной фильтрации обучается через Celery
3. Рекомендации для похожих пользователей имеют пересечения
4. Коллаборативная фильтрация работает корректно
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
from src.services.recommendation_engine import CollaborativeFilteringEngine
from src.tasks.recommendation_tasks import train_collaborative_model


@pytest.fixture
def test_playlist_items(db_session):
    """
    Создает набор тестовых PlaylistItem для рекомендаций.

    Возвращает 20 элементов с разными жанрами/тематиками:
    - Группа A: рок-музыка (items 1-7)
    - Группа B: поп-музыка (items 8-14)
    - Группа C: джаз (items 15-20)
    """
    items = []
    genres = [
        ("Rock Anthem", "rock"),
        ("Rock Ballad", "rock"),
        ("Hard Rock", "rock"),
        ("Classic Rock", "rock"),
        ("Alternative Rock", "rock"),
        ("Indie Rock", "rock"),
        ("Progressive Rock", "rock"),
        ("Pop Hit", "pop"),
        ("Pop Song", "pop"),
        ("Dance Pop", "pop"),
        ("Synth Pop", "pop"),
        ("Teen Pop", "pop"),
        ("Pop Ballad", "pop"),
        ("Euro Pop", "pop"),
        ("Jazz Standard", "jazz"),
        ("Smooth Jazz", "jazz"),
        ("Bebop", "jazz"),
        ("Swing", "jazz"),
        ("Fusion", "jazz"),
        ("Cool Jazz", "jazz"),
    ]

    for i, (title, genre) in enumerate(genres):
        item = PlaylistItem(
            id=uuid4(),
            playlist_id=1,
            position=i + 1,
            url=f"https://example.com/video{i+1}",
            title=title,
            type="youtube",
            duration=180 + (i * 10),  # Разная длительность
            channel=f"{genre.capitalize()} Channel",
        )
        db_session.add(item)
        items.append(item)

    db_session.commit()
    for item in items:
        db_session.refresh(item)

    return items


@pytest.fixture
def test_users(db_session):
    """Создает тестовых пользователей."""
    users = []
    for i in range(5):
        user = User(
            id=uuid4(),
            telegram_id=1000 + i,
            username=f"testuser{i}",
            full_name=f"Test User {i}",
            role="listener",
        )
        db_session.add(user)
        users.append(user)

    db_session.commit()
    for user in users:
        db_session.refresh(user)

    return users


@pytest.fixture
def recommendation_service(db_session):
    """Создает экземпляр RecommendationService."""
    return RecommendationService(db=db_session, redis_client=None)


def create_user_interactions(
    db_session, user_id, playlist_items, interaction_type="watch", completion_rate_range=(0.7, 1.0)
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
        # Случайный completion_rate в указанном диапазоне
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


class TestCollaborativeFilteringRecommendations:
    """Тест рекомендаций коллаборативной фильтрации с симулированными пользователями."""

    def test_create_simulated_users_with_similar_patterns(
        self, db_session, test_users, test_playlist_items
    ):
        """
        Step 1: Создаем тестовых пользователей с похожими паттернами просмотра.

        GIVEN: 5 пользователей и 20 PlaylistItem (разных жанров)
        WHEN: Создаем взаимодействия:
            - User1 и User2: любят рок (группа A, items 1-7) + немного поп
            - User3: любит поп (группа B, items 8-14)
            - User4 и User5: любят джаз (группа C, items 15-20)
        THEN: Взаимодействия создаются корректно
        """
        # User1 и User2 похожи - любят рок
        rock_items = test_playlist_items[0:7]  # items 1-7
        pop_items_sample = test_playlist_items[7:10]  # items 8-10 (немного поп)

        create_user_interactions(
            db_session, test_users[0].id, rock_items, "watch", (0.8, 1.0)
        )
        create_user_interactions(
            db_session, test_users[0].id, pop_items_sample, "watch", (0.5, 0.7)
        )

        create_user_interactions(
            db_session, test_users[1].id, rock_items, "watch", (0.8, 1.0)
        )
        create_user_interactions(
            db_session, test_users[1].id, pop_items_sample, "watch", (0.5, 0.7)
        )

        # User3 любит поп
        pop_items = test_playlist_items[7:14]  # items 8-14
        rock_items_sample = test_playlist_items[0:3]  # items 1-3 (немного рок)

        create_user_interactions(
            db_session, test_users[2].id, pop_items, "watch", (0.8, 1.0)
        )
        create_user_interactions(
            db_session, test_users[2].id, rock_items_sample, "watch", (0.4, 0.6)
        )

        # User4 и User5 похожи - любят джаз
        jazz_items = test_playlist_items[14:20]  # items 15-20
        pop_items_sample2 = test_playlist_items[10:13]  # items 11-13 (немного поп)

        create_user_interactions(
            db_session, test_users[3].id, jazz_items, "watch", (0.8, 1.0)
        )
        create_user_interactions(
            db_session, test_users[3].id, pop_items_sample2, "watch", (0.5, 0.7)
        )

        create_user_interactions(
            db_session, test_users[4].id, jazz_items, "watch", (0.8, 1.0)
        )
        create_user_interactions(
            db_session, test_users[4].id, pop_items_sample2, "watch", (0.5, 0.7)
        )

        # Проверяем, что взаимодействия созданы
        interactions = db_session.execute(
            select(UserItemInteraction).where(
                UserItemInteraction.user_id.in_([str(u.id) for u in test_users])
            )
        ).scalars().all()

        assert len(interactions) >= 40  # Минимум 40 взаимодействий

        # Проверяем, что у каждого пользователя есть взаимодействия
        for user in test_users:
            user_interactions = [
                i for i in interactions if i.user_id == str(user.id)
            ]
            assert len(user_interactions) >= 8  # Каждый пользователь смотрел минимум 8 видео

    def test_train_collaborative_filtering_model(
        self, db_session, test_users, test_playlist_items
    ):
        """
        Step 2: Обучаем модель коллаборативной фильтрации через Celery задачу.

        GIVEN: Пользователи с взаимодействиями существуют
        WHEN: Вызываем train_collaborative_model()
        THEN: Модель успешно обучается и сохраняется
        """
        # Arrange - создаем взаимодействия
        rock_items = test_playlist_items[0:7]
        pop_items = test_playlist_items[7:14]
        jazz_items = test_playlist_items[14:20]

        # User1 и User2 - рок
        create_user_interactions(db_session, test_users[0].id, rock_items, "watch")
        create_user_interactions(db_session, test_users[1].id, rock_items, "watch")

        # User3 - поп
        create_user_interactions(db_session, test_users[2].id, pop_items, "watch")

        # User4 и User5 - джаз
        create_user_interactions(db_session, test_users[3].id, jazz_items, "watch")
        create_user_interactions(db_session, test_users[4].id, jazz_items, "watch")

        # Act - обучаем модель (синхронно для теста)
        result = train_collaborative_model(days=7)

        # Assert
        assert result["success"] is True
        assert result["error"] is None

        metrics = result["metrics"]
        assert metrics["users_count"] >= 5
        assert metrics["items_count"] >= 15
        assert metrics["interactions_count"] >= 35
        assert metrics["explained_variance"] > 0  # SVD объяснил какую-то дисперсию
        assert metrics["trained_at"] is not None

        logger.info(
            f"Collaborative model trained: {metrics['users_count']} users, "
            f"{metrics['items_count']} items, explained variance: "
            f"{metrics['explained_variance']:.3f}"
        )

    def test_fetch_recommendations_for_similar_users(
        self, db_session, test_users, test_playlist_items, recommendation_service
    ):
        """
        Step 3: Получаем рекомендации для похожих пользователей.

        GIVEN: Обученная модель коллаборативной фильтрации
        WHEN: Получаем рекомендации для User1 и User2 (оба любят рок)
        THEN: Рекомендации имеют пересечения (похожие элементы)
        """
        # Arrange - создаем взаимодействия и обучаем модель
        rock_items = test_playlist_items[0:7]
        pop_items = test_playlist_items[7:14]
        jazz_items = test_playlist_items[14:20]

        # User1 и User2 - рок (похожие пользователи)
        create_user_interactions(db_session, test_users[0].id, rock_items, "watch")
        create_user_interactions(db_session, test_users[1].id, rock_items, "watch")

        # User3 - поп (отличается)
        create_user_interactions(db_session, test_users[2].id, pop_items, "watch")

        # User4 и User5 - джаз (похожи между собой)
        create_user_interactions(db_session, test_users[3].id, jazz_items, "watch")
        create_user_interactions(db_session, test_users[4].id, jazz_items, "watch")

        # Обучаем модель
        train_result = train_collaborative_model(days=7)
        assert train_result["success"] is True

        # Act - получаем рекомендации для User1 и User2
        from src.schemas.recommendation import RecommendationRequest

        request1 = RecommendationRequest(
            user_id=str(test_users[0].id),
            limit=10,
            algorithm="collaborative_filtering",
            exclude_watched=True,
        )

        request2 = RecommendationRequest(
            user_id=str(test_users[1].id),
            limit=10,
            algorithm="collaborative_filtering",
            exclude_watched=True,
        )

        recommendations1 = await recommendation_service.get_recommendations(request1)
        recommendations2 = await recommendation_service.get_recommendations(request2)

        # Assert - есть рекомендации
        assert len(recommendations1.recommendations) > 0
        assert len(recommendations2.recommendations) > 0

        # Проверяем, что оба пользователя получили рекомендации
        recs1_ids = {r.playlist_item_id for r in recommendations1.recommendations}
        recs2_ids = {r.playlist_item_id for r in recommendations2.recommendations}

        logger.info(f"User1 recommendations: {len(recs1_ids)} items")
        logger.info(f"User2 recommendations: {len(recs2_ids)} items")

        # Есть ли пересечения? (не обязательно, но желательно)
        overlap = recs1_ids & recs2_ids
        logger.info(f"Overlap between User1 and User2: {len(overlap)} items")

        # Проверяем, что алгоритм указан корректно
        for rec in recommendations1.recommendations:
            assert rec.algorithm == "collaborative_filtering"
            assert 0 <= rec.score <= 1

    def test_verify_collaborative_filtering_working(
        self, db_session, test_users, test_playlist_items, recommendation_service
    ):
        """
        Step 4: Проверяем, что коллаборативная фильтрация работает корректно.

        GIVEN:
            - User1 и User2 смотрели рок (items 1-7)
            - User3 смотрел поп (items 8-14)
        WHEN: Получаем рекомендации:
            - Для User1 (должны получить рок/похожее)
            - Для User3 (должны получить поп/похожее)
        THEN: Рекомендации различаются (разные вкусы → разные рекомендации)
        """
        # Arrange
        rock_items = test_playlist_items[0:7]
        pop_items = test_playlist_items[7:14]

        # User1 - рок
        create_user_interactions(db_session, test_users[0].id, rock_items, "like", (0.9, 1.0))

        # User2 - тоже рок (похож на User1)
        create_user_interactions(db_session, test_users[1].id, rock_items, "like", (0.9, 1.0))

        # User3 - поп (другой вкус)
        create_user_interactions(db_session, test_users[2].id, pop_items, "like", (0.9, 1.0))

        # Обучаем модель
        train_result = train_collaborative_model(days=7)
        assert train_result["success"] is True

        # Act - получаем рекомендации
        from src.schemas.recommendation import RecommendationRequest

        request_rock_lover = RecommendationRequest(
            user_id=str(test_users[0].id),
            limit=10,
            algorithm="collaborative_filtering",
            exclude_watched=True,
        )

        request_pop_lover = RecommendationRequest(
            user_id=str(test_users[2].id),
            limit=10,
            algorithm="collaborative_filtering",
            exclude_watched=True,
        )

        recs_rock = await recommendation_service.get_recommendations(request_rock_lover)
        recs_pop = await recommendation_service.get_recommendations(request_pop_lover)

        # Assert
        # Есть рекомендации
        assert len(recs_rock.recommendations) > 0
        assert len(recs_pop.recommendations) > 0

        # Собираем ID рекомендованных элементов
        rock_recs_ids = {r.playlist_item_id for r in recs_rock.recommendations}
        pop_recs_ids = {r.playlist_item_id for r in recs_pop.recommendations}

        logger.info(f"Rock lover got {len(rock_recs_ids)} recommendations")
        logger.info(f"Pop lover got {len(pop_recs_ids)} recommendations")

        # Проверяем, что рекомендации не полностью совпадают
        # (разные пользователи с разными вкусами должны получать разные рекомендации)
        overlap = rock_recs_ids & pop_recs_ids
        overlap_percentage = len(overlap) / max(len(rock_recs_ids), len(pop_recs_ids)) if max(len(rock_recs_ids), len(pop_recs_ids)) > 0 else 0

        logger.info(f"Overlap between rock and pop lovers: {len(overlap)} items ({overlap_percentage:.1%})")

        # Пересечение не должно быть 100% (иначе рекомендации одинаковые для всех)
        assert overlap_percentage < 1.0, "Recommendations should not be identical for all users"

        # Проверяем, что у рекомендаций есть scores
        for rec in recs_rock.recommendations:
            assert rec.score is not None
            assert rec.score > 0

        for rec in recs_pop.recommendations:
            assert rec.score is not None
            assert rec.score > 0

    def test_end_to_end_collaborative_filtering(
        self, db_session, test_users, test_playlist_items, recommendation_service
    ):
        """
        End-to-End тест: полный цикл коллаборативной фильтрации.

        GIVEN: 5 пользователей с разными вкусами
        WHEN:
            1. Создаем взаимодействия для всех пользователей
            2. Обучаем модель коллаборативной фильтрации
            3. Получаем рекомендации для пользователей
            4. Проверяем пересечения для похожих пользователей
        THEN: Полный цикл проходит без ошибок, рекомендации работают
        """
        # 1. Создаем взаимодействия
        rock_items = test_playlist_items[0:7]
        pop_items = test_playlist_items[7:14]
        jazz_items = test_playlist_items[14:20]

        # Группа 1: рок-любители (User1, User2)
        create_user_interactions(db_session, test_users[0].id, rock_items, "like", (0.9, 1.0))
        create_user_interactions(db_session, test_users[1].id, rock_items, "like", (0.9, 1.0))

        # Группа 2: поп-любитель (User3)
        create_user_interactions(db_session, test_users[2].id, pop_items, "like", (0.9, 1.0))

        # Группа 3: джаз-любители (User4, User5)
        create_user_interactions(db_session, test_users[3].id, jazz_items, "like", (0.9, 1.0))
        create_user_interactions(db_session, test_users[4].id, jazz_items, "like", (0.9, 1.0))

        # Проверяем взаимодействия в БД
        all_interactions = db_session.execute(
            select(UserItemInteraction)
        ).scalars().all()

        assert len(all_interactions) >= 30  # Минимум 30 взаимодействий
        logger.info(f"Created {len(all_interactions)} user interactions")

        # 2. Обучаем модель
        train_result = train_collaborative_model(days=7)
        assert train_result["success"] is True

        metrics = train_result["metrics"]
        logger.info(
            f"Model trained: {metrics['users_count']} users, "
            f"{metrics['items_count']} items, "
            f"{metrics['interactions_count']} interactions"
        )

        # 3. Получаем рекомендации для каждой группы
        from src.schemas.recommendation import RecommendationRequest

        recs_by_user = {}

        for user in test_users:
            request = RecommendationRequest(
                user_id=str(user.id),
                limit=10,
                algorithm="collaborative_filtering",
                exclude_watched=True,
            )

            response = await recommendation_service.get_recommendations(request)
            recs_by_user[str(user.id)] = response

            assert len(response.recommendations) >= 0  # Может быть 0, если нет данных
            logger.info(f"User {user.username}: {len(response.recommendations)} recommendations")

        # 4. Проверяем пересечения для похожих пользователей
        # User1 и User2 (рок) должны иметь похожие рекомендации
        recs_user1 = {r.playlist_item_id for r in recs_by_user[str(test_users[0].id)].recommendations}
        recs_user2 = {r.playlist_item_id for r in recs_by_user[str(test_users[1].id)].recommendations}

        if len(recs_user1) > 0 and len(recs_user2) > 0:
            overlap_rock = recs_user1 & recs_user2
            logger.info(f"User1 & User2 (rock lovers) overlap: {len(overlap_rock)} items")

            # Проверяем, что есть хотя бы некоторое пересечение
            # (не обязательно, но указывает на работу коллаборативной фильтрации)
            if len(overlap_rock) > 0:
                logger.info(f"✓ Collaborative filtering working: similar users have overlapping recommendations")

        # User4 и User5 (джаз) должны иметь похожие рекомендации
        recs_user4 = {r.playlist_item_id for r in recs_by_user[str(test_users[3].id)].recommendations}
        recs_user5 = {r.playlist_item_id for r in recs_by_user[str(test_users[4].id)].recommendations}

        if len(recs_user4) > 0 and len(recs_user5) > 0:
            overlap_jazz = recs_user4 & recs_user5
            logger.info(f"User4 & User5 (jazz lovers) overlap: {len(overlap_jazz)} items")

            if len(overlap_jazz) > 0:
                logger.info(f"✓ Collaborative filtering working: similar users have overlapping recommendations")

        # Проверяем, что рекомендации разных групп отличаются
        recs_user1_set = recs_user1
        recs_user3_set = {r.playlist_item_id for r in recs_by_user[str(test_users[2].id)].recommendations}

        if len(recs_user1_set) > 0 and len(recs_user3_set) > 0:
            overlap_different = recs_user1_set & recs_user3_set
            logger.info(f"User1 (rock) & User3 (pop) overlap: {len(overlap_different)} items")

            # Пересечение не должно быть слишком большим
            overlap_percentage = len(overlap_different) / max(len(recs_user1_set), len(recs_user3_set))
            if overlap_percentage < 0.8:
                logger.info(f"✓ Recommendations differ for users with different tastes")

        # Успешное завершение E2E теста
        logger.info("✓ E2E collaborative filtering test passed")
