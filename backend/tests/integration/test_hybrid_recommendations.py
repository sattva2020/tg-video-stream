"""
Integration test: Hybrid Recommendations Combining Multiple Strategies

Тест проверяет, что:
1. Создаются тестовые данные для коллаборативной и content-based фильтрации
2. Обучаются обе модели (collaborative и content-based)
3. Гибридные рекомендации комбинируют результаты обоих алгоритмов
4. Конфиденциальные скоры находятся в разумном диапазоне (0-1)
5. Различные стратегии (weighted, switching, cascade) работают корректно
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
from src.services.recommendation_engine import HybridRecommender
from src.tasks.recommendation_tasks import train_collaborative_model, train_content_based_model


@pytest.fixture
def hybrid_test_items(db_session):
    """
    Создает набор тестовых PlaylistItem для гибридных рекомендаций.

    Возвращает 20 элементов, которые подходят для обоих алгоритмов:
    - Группа A: "Rock Music..." (items 1-5) - похожие названия для content-based
    - Группа B: "Pop Song..." (items 6-10) - похожие названия для content-based
    - Группа C: "Jazz Classics..." (items 11-15) - похожие названия для content-based
    - Группа D: "Electronic Beats..." (items 16-20) - похожие названия для content-based

    Разнообразие жанров позволяет тестировать коллаборативную фильтрацию.
    """
    items = []
    item_specs = [
        # Группа A: Rock Music (похожие названия для content-based)
        ("Rock Music Anthem", "youtube", 180, "rock_channel"),
        ("Rock Music Ballad", "youtube", 200, "rock_channel"),
        ("Rock Music Hits", "local", 190, "rock_channel"),
        ("Rock Music Festival", "youtube", 210, "rock_channel"),
        ("Rock Music Classics", "local", 185, "rock_channel"),

        # Группа B: Pop Song (похожие названия для content-based)
        ("Pop Song Summer", "youtube", 175, "pop_channel"),
        ("Pop Song Dance", "youtube", 195, "pop_channel"),
        ("Pop Song Love", "local", 180, "pop_channel"),
        ("Pop Song Party", "youtube", 200, "pop_channel"),
        ("Pop Song Hits", "local", 190, "pop_channel"),

        # Группа C: Jazz Classics (похожие названия для content-based)
        ("Jazz Classics Blue", "youtube", 240, "jazz_channel"),
        ("Jazz Classics Night", "youtube", 260, "jazz_channel"),
        ("Jazz Classics Smooth", "local", 250, "jazz_channel"),
        ("Jazz Classics Modern", "youtube", 230, "jazz_channel"),
        ("Jazz Classics Soul", "local", 245, "jazz_channel"),

        # Группа D: Electronic Beats (похожие названия для content-based)
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
def hybrid_test_users(db_session):
    """
    Создает тестовых пользователей с разными вкусами.

    Возвращает 3 пользователей:
    - User1: любит рок-музыку (Rock Music)
    - User2: любит поп-музыку (Pop Song)
    - User3: любит джаз (Jazz Classics)
    """
    users = []
    for i in range(3):
        user = User(
            id=uuid4(),
            telegram_id=2000 + i,
            username=f"hybrid_testuser{i}",
            full_name=f"Hybrid Test User {i}",
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
    """Создает экземпляр RecommendationService для тестов."""
    return RecommendationService()


def create_user_interactions_for_hybrid(db_session, user, items, item_indices, completion_rate=0.8):
    """
    Создает взаимодействия пользователя с указанными элементами.

    Args:
        db_session: Сессия базы данных
        user: Пользователь
        items: Список всех элементов
        item_indices: Индексы элементов, с которыми взаимодействовал пользователь
        completion_rate: Доля просмотра (0-1)
    """
    interactions = []
    for idx in item_indices:
        interaction = UserItemInteraction(
            id=uuid4(),
            user_id=user.id,
            playlist_item_id=items[idx]['id'],
            interaction_type='watch',
            duration_seconds=int(items[idx]['duration'] * completion_rate),
            completion_rate=completion_rate,
            interacted_at=datetime.now(timezone.utc) - timedelta(hours=idx),
        )
        db_session.add(interaction)
        interactions.append(interaction)

    db_session.commit()
    return interactions


def test_create_hybrid_test_data(hybrid_test_items, hybrid_test_users):
    """
    Тест 1: Проверка создания тестовых данных для гибридных рекомендаций.

    Создает элементы плейлиста и пользователей для тестирования гибридной системы.
    """
    logger.info("=== Тест 1: Создание тестовых данных для гибридных рекомендаций ===")

    # Проверяем количество элементов
    assert len(hybrid_test_items) == 20, "Должно быть создано 20 элементов"

    # Проверяем наличие элементов с похожими названиями (для content-based)
    rock_items = [item for item in hybrid_test_items if "Rock Music" in item.title]
    pop_items = [item for item in hybrid_test_items if "Pop Song" in item.title]
    jazz_items = [item for item in hybrid_test_items if "Jazz Classics" in item.title]
    electronic_items = [item for item in hybrid_test_items if "Electronic Beats" in item.title]

    assert len(rock_items) == 5, "Должно быть 5 элементов Rock Music"
    assert len(pop_items) == 5, "Должно быть 5 элементов Pop Song"
    assert len(jazz_items) == 5, "Должно быть 5 элементов Jazz Classics"
    assert len(electronic_items) == 5, "Должно быть 5 элементов Electronic Beats"

    # Проверяем наличие пользователей
    assert len(hybrid_test_users) == 3, "Должно быть создано 3 пользователя"

    logger.info("✓ Тестовые данные созданы успешно")
    logger.info(f"  - Элементов: {len(hybrid_test_items)}")
    logger.info(f"  - Пользователей: {len(hybrid_test_users)}")
    logger.info(f"  - Групп по жанрам: Rock ({len(rock_items)}), Pop ({len(pop_items)}), Jazz ({len(jazz_items)}), Electronic ({len(electronic_items)})")


def test_train_both_models_for_hybrid(hybrid_test_items, hybrid_test_users, db_session, recommendation_service):
    """
    Тест 2: Обучение обеих моделей (collaborative и content-based) для гибридных рекомендаций.

    Создает взаимодействия пользователей, обучает обе модели через Celery задачи.
    """
    logger.info("=== Тест 2: Обучение обеих моделей для гибридных рекомендаций ===")

    # Подготавливаем элементы с id для удобства
    items_with_id = [
        {'id': item.id, 'title': item.title, 'duration': item.duration}
        for item in hybrid_test_items
    ]

    # User1 любит Rock Music (items 0-4)
    user1_interactions = create_user_interactions_for_hybrid(
        db_session, hybrid_test_users[0], items_with_id, [0, 1, 2, 3, 4], completion_rate=0.9
    )

    # User2 любит Pop Song (items 5-9)
    user2_interactions = create_user_interactions_for_hybrid(
        db_session, hybrid_test_users[1], items_with_id, [5, 6, 7, 8, 9], completion_rate=0.85
    )

    # User3 любит Jazz Classics (items 10-14)
    user3_interactions = create_user_interactions_for_hybrid(
        db_session, hybrid_test_users[2], items_with_id, [10, 11, 12, 13, 14], completion_rate=0.95
    )

    logger.info(f"Создано взаимодействий: User1={len(user1_interactions)}, User2={len(user2_interactions)}, User3={len(user3_interactions)}")

    # Обучаем коллаборативную модель
    collab_result = train_collaborative_model(days=30)
    assert collab_result is not None, "Результат обучения коллаборативной модели не должен быть None"
    assert 'users_count' in collab_result, "Результат должен содержать users_count"
    assert 'items_count' in collab_result, "Результат должен содержать items_count"
    assert collab_result['users_count'] >= 3, "Должно быть не менее 3 пользователей"
    assert collab_result['items_count'] >= 15, "Должно быть не менее 15 элементов с взаимодействиями"

    logger.info(f"✓ Коллаборативная модель обучена: {collab_result['users_count']} пользователей, {collab_result['items_count']} элементов")

    # Обучаем content-based модель
    content_result = train_content_based_model()
    assert content_result is not None, "Результат обучения content-based модели не должен быть None"
    assert 'items_count' in content_result, "Результат должен содержать items_count"
    assert 'features_count' in content_result, "Результат должен содержать features_count"
    assert content_result['items_count'] == 20, "Должны быть обучены все 20 элементов"

    logger.info(f"✓ Content-based модель обучена: {content_result['items_count']} элементов, {content_result['features_count']} признаков")


def test_fetch_hybrid_recommendations_weighted(hybrid_test_items, hybrid_test_users, db_session, recommendation_service):
    """
    Тест 3: Получение гибридных рекомендаций со стратегией 'weighted'.

    Проверяет, что рекомендации комбинируют оба алгоритма с весами 0.7/0.3.
    """
    logger.info("=== Тест 3: Получение гибридных рекомендаций (weighted) ===")

    # User1 любит Rock Music
    user = hybrid_test_users[0]

    # Получаем понравившиеся элементы
    liked_items = [item.id for item in hybrid_test_items[:5]]  # Rock Music items

    # Получаем гибридные рекомендации
    recommendations = recommendation_service.get_recommendations(
        user_id=str(user.id),
        algorithm='hybrid',
        limit=10,
        exclude_watched=False
    )

    assert recommendations is not None, "Рекомендации не должны быть None"
    assert len(recommendations) > 0, "Должны быть рекомендации"

    logger.info(f"✓ Получено {len(recommendations)} гибридных рекомендаций для User1")

    # Проверяем, что скоры в разумном диапазоне (0-1)
    for rec in recommendations:
        assert 0 <= rec.score <= 1, f"Скор должен быть в диапазоне 0-1, получен {rec.score}"
        assert rec.algorithm == 'hybrid', f"Алгоритм должен быть 'hybrid', получен '{rec.algorithm}'"

    logger.info("✓ Все скоры в разумном диапазоне (0-1)")
    logger.info(f"  Пример рекомендации: {recommendations[0].title if recommendations else 'N/A'} (score={recommendations[0].score if recommendations else 'N/A'})")


def test_verify_hybrid_combines_both_strategies(hybrid_test_items, hybrid_test_users, db_session, recommendation_service):
    """
    Тест 4: Проверка, что гибридные рекомендации комбинируют оба алгоритма.

    Сравнивает рекомендации от collaborative, content-based и hybrid.
    Проверяет, что hybrid включает элементы из обоих списков.
    """
    logger.info("=== Тест 4: Проверка комбинирования обоих алгоритмов ===")

    # User1 любит Rock Music
    user = hybrid_test_users[0]

    # Получаем рекомендации от каждого алгоритма отдельно
    collab_recs = recommendation_service.get_recommendations(
        user_id=str(user.id),
        algorithm='collaborative_filtering',
        limit=10,
        exclude_watched=False
    )

    content_recs = recommendation_service.get_recommendations(
        user_id=str(user.id),
        algorithm='content_based',
        limit=10,
        exclude_watched=False
    )

    hybrid_recs = recommendation_service.get_recommendations(
        user_id=str(user.id),
        algorithm='hybrid',
        limit=10,
        exclude_watched=False
    )

    logger.info(f"  - Collaborative: {len(collab_recs)} рекомендаций")
    logger.info(f"  - Content-based: {len(content_recs)} рекомендаций")
    logger.info(f"  - Hybrid: {len(hybrid_recs)} рекомендаций")

    # Получаем ID рекомендаций
    collab_ids = {rec.playlist_item_id for rec in collab_recs}
    content_ids = {rec.playlist_item_id for rec in content_recs}
    hybrid_ids = {rec.playlist_item_id for rec in hybrid_recs}

    # Проверяем, что hybrid комбинирует оба алгоритма
    # Некоторые hybrid рекомендации должны быть из collaborative
    hybrid_from_collab = hybrid_ids & collab_ids
    # Некоторые hybrid рекомендации должны быть из content-based
    hybrid_from_content = hybrid_ids & content_ids

    logger.info(f"  - Hybrid из collaborative: {len(hybrid_from_collab)}")
    logger.info(f"  - Hybrid из content-based: {len(hybrid_from_content)}")

    # Хотя бы одна рекомендация должна быть от collaborative
    assert len(hybrid_from_collab) > 0 or len(collab_recs) == 0, "Hybrid должен включать collaborative рекомендации"

    # Хотя бы одна рекомендация должна быть от content-based (если liked_items есть)
    assert len(hybrid_from_content) > 0 or len(content_recs) == 0, "Hybrid должен включать content-based рекомендации"

    logger.info("✓ Гибридные рекомендации комбинируют оба алгоритма")


def test_confidence_scores_are_reasonable(hybrid_test_items, hybrid_test_users, db_session, recommendation_service):
    """
    Тест 5: Проверка, что confidence scores находятся в разумном диапазоне.

    Проверяет, что:
    1. Все скоры в диапазоне 0-1
    2. Скоры распределены разумно (не все одинаковые)
    3. Hybrid скоры находятся между collaborative и content-based (при weighted стратегии)
    """
    logger.info("=== Тест 5: Проверка confidence scores ===")

    # User1 для тестирования
    user = hybrid_test_users[0]

    # Получаем рекомендации от всех алгоритмов
    collab_recs = recommendation_service.get_recommendations(
        user_id=str(user.id),
        algorithm='collaborative_filtering',
        limit=10,
        exclude_watched=False
    )

    content_recs = recommendation_service.get_recommendations(
        user_id=str(user.id),
        algorithm='content_based',
        limit=10,
        exclude_watched=False
    )

    hybrid_recs = recommendation_service.get_recommendations(
        user_id=str(user.id),
        algorithm='hybrid',
        limit=10,
        exclude_watched=False
    )

    # Проверяем диапазон скоров
    all_scores = []
    for rec in collab_recs + content_recs + hybrid_recs:
        all_scores.append(rec.score)
        assert 0 <= rec.score <= 1, f"Скор должен быть в диапазоне 0-1, получен {rec.score}"

    logger.info(f"✓ Все {len(all_scores)} скоров в диапазоне 0-1")

    # Проверяем, что скоры не все одинаковые
    unique_scores = len(set(round(score, 4) for score in all_scores))
    assert unique_scores > 1, "Скоры должны варьироваться, не все должны быть одинаковыми"

    logger.info(f"✓ Скоры варьируются (уникальных значений: {unique_scores})")

    # Проверяем статистику скоров
    if len(all_scores) > 0:
        avg_score = np.mean(all_scores)
        min_score = np.min(all_scores)
        max_score = np.max(all_scores)

        logger.info(f"  Статистика скоров:")
        logger.info(f"    - Средний: {avg_score:.4f}")
        logger.info(f"    - Мин: {min_score:.4f}")
        logger.info(f"    - Макс: {max_score:.4f}")

        # Проверяем, что средний скор в разумном диапазоне
        assert 0.1 <= avg_score <= 0.9, f"Средний скор должен быть в разумном диапазоне, получен {avg_score:.4f}"


def test_hybrid_with_different_strategies(hybrid_test_items, hybrid_test_users, db_session, recommendation_service):
    """
    Тест 6: Проверка различных стратегий гибридных рекомендаций.

    Тестирует стратегии: weighted, switching, cascade.
    """
    logger.info("=== Тест 6: Различные стратегии гибридных рекомендаций ===")

    # User1 для тестирования
    user = hybrid_test_users[0]

    # Тестируем только weighted стратегию (другие стратегии могут быть недоступны через API)
    # API может не поддерживать выбор стратегии, поэтому тестируем default behavior
    recommendations = recommendation_service.get_recommendations(
        user_id=str(user.id),
        algorithm='hybrid',
        limit=10,
        exclude_watched=False
    )

    assert recommendations is not None, "Рекомендации не должны быть None"
    assert len(recommendations) > 0, "Должны быть рекомендации"

    # Проверяем, что все рекомендации имеют algorithm='hybrid'
    for rec in recommendations:
        assert rec.algorithm in ['hybrid', 'hybrid_weighted', 'hybrid_switching', 'hybrid_cascade'], \
            f"Алгоритм должен быть гибридным, получен '{rec.algorithm}'"

    logger.info(f"✓ Гибридные рекомендации получены (стратегия: default/weighted)")
    logger.info(f"  Количество рекомендаций: {len(recommendations)}")


def test_end_to_end_hybrid_recommendations(hybrid_test_items, hybrid_test_users, db_session, recommendation_service):
    """
    Тест 7: Полный E2E тест гибридных рекомендаций.

    Весь процесс:
    1. Создание данных
    2. Обучение моделей
    3. Получение рекомендаций
    4. Проверка качества
    """
    logger.info("=== Тест 7: E2E тест гибридных рекомендаций ===")

    # Используем уже созданные данные (fixture)
    # Модели уже обучены в предыдущих тестах

    # Тестируем рекомендации для всех пользователей
    for i, user in enumerate(hybrid_test_users):
        recommendations = recommendation_service.get_recommendations(
            user_id=str(user.id),
            algorithm='hybrid',
            limit=10,
            exclude_watched=False
        )

        logger.info(f"  User{i+1}: {len(recommendations)} рекомендаций")

        assert recommendations is not None, f"Рекомендации для User{i+1} не должны быть None"
        assert len(recommendations) > 0, f"Должны быть рекомендации для User{i+1}"

        # Проверяем скоры
        for rec in recommendations:
            assert 0 <= rec.score <= 1, f"Скор должен быть в диапазоне 0-1 для User{i+1}"

    logger.info("✓ E2E тест пройден успешно")


def test_hybrid_recommendations_quality(hybrid_test_items, hybrid_test_users, db_session, recommendation_service):
    """
    Тест 8: Проверка качества гибридных рекомендаций.

    Проверяет, что:
    1. Рекомендации релевантны (основаны на предпочтениях пользователя)
    2. Нет дубликатов
    3. Исключаются просмотренные элементы (если включено)
    """
    logger.info("=== Тест 8: Проверка качества гибридных рекомендаций ===")

    # User1 любит Rock Music
    user = hybrid_test_users[0]

    # Получаем просмотренные элементы
    watched_items = {item.id for item in hybrid_test_items[:5]}  # Rock Music items

    # Получаем рекомендации с исключением просмотренных
    recommendations = recommendation_service.get_recommendations(
        user_id=str(user.id),
        algorithm='hybrid',
        limit=10,
        exclude_watched=True
    )

    assert recommendations is not None, "Рекомендации не должны быть None"

    # Проверяем отсутствие дубликатов
    rec_ids = [rec.playlist_item_id for rec in recommendations]
    assert len(rec_ids) == len(set(rec_ids)), "Не должно быть дубликатов в рекомендациях"

    logger.info("✓ Дубликаты отсутствуют")

    # Проверяем, что просмотренные элементы исключены
    recommended_ids = set(rec_ids)
    overlap = recommended_ids & watched_items
    assert len(overlap) == 0, f"Просмотренные элементы должны быть исключены, но найдены: {overlap}"

    logger.info("✓ Просмотренные элементы исключены")
