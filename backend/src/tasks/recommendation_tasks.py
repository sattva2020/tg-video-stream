"""
Celery tasks для обучения рекомендательных моделей.

Включает:
- Обучение коллаборативной фильтрации
- Обучение content-based модели
- Обновление матрицы взаимодействий
- Переобучение моделей по расписанию
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Lazy Celery import
try:
    from celery import Celery
    CELERY_AVAILABLE = True
except ImportError:
    Celery = None
    CELERY_AVAILABLE = False


def _get_celery_app():
    """Получает или создаёт Celery приложение."""
    broker = os.getenv('CELERY_BROKER_URL')
    if not broker:
        return None
    return Celery('tg_video_streamer', broker=broker)


def train_collaborative_model(days: int = 30) -> Dict[str, Any]:
    """
    Обучает модель коллаборативной фильтрации на данных взаимодействий.

    Args:
        days: Количество дней для сбора данных (по умолчанию 30)

    Returns:
        dict с результатами обучения: success, metrics, error
    """
    try:
        from src.services.recommendation_engine import InteractionDataCollector, CollaborativeFilteringEngine

        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return {"success": False, "error": "DATABASE_URL not set"}

        logger.info(f"[worker] Starting collaborative model training with {days} days of data")

        # Собираем данные
        collector = InteractionDataCollector(database_url)
        interactions_df = collector.get_interactions_df(days=days)

        if interactions_df.empty:
            return {
                "success": False,
                "error": f"No interaction data found for the last {days} days"
            }

        # Обучаем модель
        engine = CollaborativeFilteringEngine()
        success = engine.train(interactions_df)

        if not success:
            return {"success": False, "error": "Model training failed"}

        # Собираем метрики
        metrics = {
            "users_count": len(engine.user_ids),
            "items_count": len(engine.item_ids),
            "interactions_count": len(interactions_df),
            "explained_variance": float(engine.svd_model.explained_variance_ratio_.sum()) if engine.svd_model else 0.0,
            "trained_at": engine.trained_at.isoformat() if engine.trained_at else None
        }

        logger.info(
            f"[worker] Collaborative model trained successfully: "
            f"{metrics['users_count']} users, {metrics['items_count']} items, "
            f"explained variance: {metrics['explained_variance']:.3f}"
        )

        return {"success": True, "metrics": metrics}

    except ImportError as e:
        logger.error(f"Failed to import recommendation engine: {e}")
        return {"success": False, "error": f"Import error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Error training collaborative model")
        return {"success": False, "error": str(e)}


def train_content_based_model() -> Dict[str, Any]:
    """
    Обучает content-based модель на метаданных контента.

    Returns:
        dict с результатами обучения: success, metrics, error
    """
    try:
        from src.services.recommendation_engine import ContentBasedFilteringEngine

        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return {"success": False, "error": "DATABASE_URL not set"}

        logger.info("[worker] Starting content-based model training")

        # Обучаем модель (async function, но вызываем синхронно в Celery)
        import asyncio
        engine = ContentBasedFilteringEngine()
        success = asyncio.run(engine.train(database_url))

        if not success:
            return {"success": False, "error": "Model training failed"}

        # Собираем метрики
        metrics = {
            "items_count": len(engine.item_ids),
            "features_count": engine.item_features_matrix.shape[1] if engine.item_features_matrix is not None else 0,
            "trained_at": engine.trained_at.isoformat() if engine.trained_at else None
        }

        logger.info(
            f"[worker] Content-based model trained successfully: "
            f"{metrics['items_count']} items, {metrics['features_count']} features"
        )

        return {"success": True, "metrics": metrics}

    except ImportError as e:
        logger.error(f"Failed to import recommendation engine: {e}")
        return {"success": False, "error": f"Import error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Error training content-based model")
        return {"success": False, "error": str(e)}


def update_interaction_matrix(days: int = 7, batch_size: int = 1000) -> Dict[str, Any]:
    """
    Обновляет матрицу взаимодействий пользователей с элементами.

    Собирает новые взаимодействия из базы данных и обновляет матрицу
    для коллаборативной фильтрации.

    Args:
        days: Количество дней для сбора новых взаимодействий (по умолчанию 7)
        batch_size: Размер пакета для обработки (по умолчанию 1000)

    Returns:
        dict с результатами обновления: success, metrics, error
    """
    try:
        from src.services.recommendation_engine import InteractionDataCollector

        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return {"success": False, "error": "DATABASE_URL not set"}

        logger.info(f"[worker] Starting interaction matrix update with {days} days of data")

        # Собираем данные о взаимодействиях
        collector = InteractionDataCollector(database_url)
        import asyncio
        interactions_df = asyncio.run(collector.get_interactions_df(days=days))

        if interactions_df.empty:
            return {
                "success": False,
                "error": f"No interaction data found for the last {days} days"
            }

        # Собираем метрики обновления
        metrics = {
            "interactions_count": len(interactions_df),
            "unique_users": interactions_df['user_id'].nunique(),
            "unique_items": interactions_df['playlist_item_id'].nunique(),
            "avg_rating": float(interactions_df['rating'].mean()) if 'rating' in interactions_df.columns else 0.0,
            "interaction_types": interactions_df['interaction_type'].value_counts().to_dict() if 'interaction_type' in interactions_df.columns else {},
            "updated_at": datetime.utcnow().isoformat()
        }

        logger.info(
            f"[worker] Interaction matrix updated successfully: "
            f"{metrics['interactions_count']} interactions, "
            f"{metrics['unique_users']} users, {metrics['unique_items']} items, "
            f"avg rating: {metrics['avg_rating']:.2f}"
        )

        return {"success": True, "metrics": metrics}

    except ImportError as e:
        logger.error(f"Failed to import recommendation engine: {e}")
        return {"success": False, "error": f"Import error: {str(e)}"}
    except Exception as e:
        logger.exception(f"Error updating interaction matrix")
        return {"success": False, "error": str(e)}


# ============================================================================
# Celery Tasks (registered if Celery available)
# ============================================================================

if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
    celery_app = _get_celery_app()

    @celery_app.task(name='tasks.train_collaborative_model', bind=True, max_retries=3)
    def train_collaborative_model_task(self, days: int = 30):
        """
        Celery task: обучает модель коллаборативной фильтрации.

        Автоматически повторяет при ошибке (до 3 раз с экспоненциальной задержкой).

        Args:
            days: Количество дней для сбора данных (по умолчанию 30)
        """
        logger.info(f"[worker] train_collaborative_model_task started with {days} days of data")

        try:
            result = train_collaborative_model(days=days)

            if not result.get("success"):
                error = result.get("error", "Unknown error")

                # Retry на временных ошибках
                if any(err in error.lower() for err in ["timeout", "connection", "database", "temporary"]):
                    logger.warning(f"Retryable error for collaborative model training: {error}")
                    raise self.retry(countdown=60 * (self.request.retries + 1))

                logger.error(f"Non-retryable error for collaborative model training: {error}")
                return result

            logger.info("[worker] Collaborative model training task completed successfully")
            return result

        except Exception as e:
            logger.exception(f"Unhandled error in train_collaborative_model_task")
            raise self.retry(exc=e, countdown=120)

    @celery_app.task(name='tasks.train_content_based_model', bind=True, max_retries=3)
    def train_content_based_model_task(self):
        """
        Celery task: обучает content-based модель рекомендаций.

        Автоматически повторяет при ошибке (до 3 раз с экспоненциальной задержкой).
        """
        logger.info("[worker] train_content_based_model_task started")

        try:
            result = train_content_based_model()

            if not result.get("success"):
                error = result.get("error", "Unknown error")

                # Retry на временных ошибках
                if any(err in error.lower() for err in ["timeout", "connection", "database", "temporary"]):
                    logger.warning(f"Retryable error for content-based model training: {error}")
                    raise self.retry(countdown=60 * (self.request.retries + 1))

                logger.error(f"Non-retryable error for content-based model training: {error}")
                return result

            logger.info("[worker] Content-based model training task completed successfully")
            return result

        except Exception as e:
            logger.exception(f"Unhandled error in train_content_based_model_task")
            raise self.retry(exc=e, countdown=120)

    @celery_app.task(name='tasks.update_interaction_matrix', bind=True, max_retries=3)
    def update_interaction_matrix_task(self, days: int = 7, batch_size: int = 1000):
        """
        Celery task: обновляет матрицу взаимодействий пользователей с элементами.

        Автоматически повторяет при ошибке (до 3 раз с экспоненциальной задержкой).

        Args:
            days: Количество дней для сбора новых взаимодействий (по умолчанию 7)
            batch_size: Размер пакета для обработки (по умолчанию 1000)
        """
        logger.info(f"[worker] update_interaction_matrix_task started with {days} days of data")

        try:
            result = update_interaction_matrix(days=days, batch_size=batch_size)

            if not result.get("success"):
                error = result.get("error", "Unknown error")

                # Retry на временных ошибках
                if any(err in error.lower() for err in ["timeout", "connection", "database", "temporary"]):
                    logger.warning(f"Retryable error for interaction matrix update: {error}")
                    raise self.retry(countdown=30 * (self.request.retries + 1))

                logger.error(f"Non-retryable error for interaction matrix update: {error}")
                return result

            logger.info("[worker] Interaction matrix update task completed successfully")
            return result

        except Exception as e:
            logger.exception(f"Unhandled error in update_interaction_matrix_task")
            raise self.retry(exc=e, countdown=60)


# ============================================================================
# Public API
# ============================================================================

def train_collaborative_model_async(days: int = 30) -> bool:
    """
    Запускает асинхронное обучение коллаборативной модели.

    Использует Celery если доступен, иначе выполняет синхронно.

    Args:
        days: Количество дней для сбора данных

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.train_collaborative_model', args=[days])
            logger.info(f"Enqueued collaborative model training with {days} days of data")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info("Training collaborative model synchronously")
    result = train_collaborative_model(days=days)
    return result.get("success", False)


def train_content_based_model_async() -> bool:
    """
    Запускает асинхронное обучение content-based модели.

    Использует Celery если доступен, иначе выполняет синхронно.

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.train_content_based_model')
            logger.info("Enqueued content-based model training")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info("Training content-based model synchronously")
    result = train_content_based_model()
    return result.get("success", False)


def update_interaction_matrix_async(days: int = 7, batch_size: int = 1000) -> bool:
    """
    Запускает асинхронное обновление матрицы взаимодействий.

    Использует Celery если доступен, иначе выполняет синхронно.

    Args:
        days: Количество дней для сбора новых взаимодействий
        batch_size: Размер пакета для обработки

    Returns:
        True если задача поставлена в очередь или выполнена успешно
    """
    if CELERY_AVAILABLE and os.getenv('CELERY_BROKER_URL'):
        app = _get_celery_app()
        try:
            app.send_task('tasks.update_interaction_matrix', args=[days, batch_size])
            logger.info(f"Enqueued interaction matrix update with {days} days of data")
            return True
        except Exception:
            logger.exception("Failed to enqueue Celery task, falling back to sync")

    # Sync fallback
    logger.info("Updating interaction matrix synchronously")
    result = update_interaction_matrix(days=days, batch_size=batch_size)
    return result.get("success", False)
