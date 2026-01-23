"""
Recommendation Engine Service
ML-сервис для рекомендаций контента на основе предпочтений пользователей.

Использует коллаборативную фильтрацию для рекомендации контента:
- User-based collaborative filtering (похожие пользователи)
- Item-based collaborative filtering (похожие элементы)
- Матричная факторизация для снижения размерности

Автор: Jarvis
Дата: 2026-01-23
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import json

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import joblib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scipy.sparse import csr_matrix

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/sattva')
MODEL_PATH = os.getenv('MODEL_PATH', '/app/models')
MIN_INTERACTIONS = int(os.getenv('MIN_INTERACTIONS', '5'))  # Минимальное количество взаимодействий для обучения
N_COMPONENTS = int(os.getenv('N_COMPONENTS', '50'))  # Количество компонент для SVD
N_RECOMMENDATIONS = int(os.getenv('N_RECOMMENDATIONS', '10'))  # Количество рекомендаций


class InteractionDataCollector:
    """Сбор данных о взаимодействиях пользователей с контентом."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)

    async def get_interactions_df(self, days: int = 30) -> pd.DataFrame:
        """
        Получить DataFrame с взаимодействиями пользователей.

        Args:
            days: Количество дней для сбора данных

        Returns:
            DataFrame с колонками: user_id, playlist_item_id, rating
        """
        try:
            from src.models.recommendation import UserItemInteraction

            session = self.SessionLocal()
            try:
                cutoff_date = datetime.now() - timedelta(days=days)

                # Получаем взаимодействия из базы данных
                interactions = session.query(
                    UserItemInteraction.user_id,
                    UserItemInteraction.playlist_item_id,
                    UserItemInteraction.interaction_type,
                    UserItemInteraction.duration_seconds,
                    UserItemInteraction.completion_rate
                ).filter(
                    UserItemInteraction.interacted_at >= cutoff_date
                ).all()

                if not interactions:
                    logger.warning(f"Нет взаимодействий за последние {days} дней")
                    return pd.DataFrame()

                # Преобразуем в DataFrame
                df = pd.DataFrame([{
                    'user_id': str(i.user_id),
                    'playlist_item_id': str(i.playlist_item_id),
                    'interaction_type': i.interaction_type,
                    'duration_seconds': i.duration_seconds or 0,
                    'completion_rate': float(i.completion_rate) if i.completion_rate else 0.0
                } for i in interactions])

                # Вычисляем рейтинг на основе типа взаимодействия
                df['rating'] = df.apply(self._calculate_rating, axis=1)

                logger.info(f"Загружено {len(df)} взаимодействий для {days} дней")
                return df

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Ошибка получения взаимодействий: {e}")
            return pd.DataFrame()

    def _calculate_rating(self, row: pd.Series) -> float:
        """
        Вычислить рейтинг на основе типа взаимодействия.

        Веса:
        - like: 5.0
        - share: 4.5
        - watch с полным просмотром: 4.0
        - watch с частичным просмотром: 2.0-3.9 (в зависимости от completion_rate)
        - click: 1.5
        - skip: 0.5
        """
        interaction_type = row['interaction_type']
        completion_rate = row['completion_rate']

        if interaction_type == 'like':
            return 5.0
        elif interaction_type == 'share':
            return 4.5
        elif interaction_type == 'watch':
            # Базовый рейтинг 2.0 + бонус за просмотр
            return 2.0 + (completion_rate * 2.0)
        elif interaction_type == 'click':
            return 1.5
        elif interaction_type == 'skip':
            return 0.5
        else:
            return 1.0

    async def get_user_interactions(self, user_id: str, days: int = 30) -> List[str]:
        """
        Получить список элементов, с которыми взаимодействовал пользователь.

        Args:
            user_id: ID пользователя
            days: Количество дней для сбора данных

        Returns:
            Список ID элементов плейлиста
        """
        try:
            from src.models.recommendation import UserItemInteraction

            session = self.SessionLocal()
            try:
                cutoff_date = datetime.now() - timedelta(days=days)

                interactions = session.query(
                    UserItemInteraction.playlist_item_id
                ).filter(
                    UserItemInteraction.user_id == user_id,
                    UserItemInteraction.interacted_at >= cutoff_date
                ).distinct().all()

                return [str(i[0]) for i in interactions]

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Ошибка получения взаимодействий пользователя: {e}")
            return []


class CollaborativeFilteringEngine:
    """ML-модель для коллаборативной фильтрации."""

    def __init__(self):
        self.svd_model: Optional[TruncatedSVD] = None
        self.user_item_matrix: Optional[csr_matrix] = None
        self.user_ids: List[str] = []
        self.item_ids: List[str] = []
        self.user_mapping: Dict[str, int] = {}  # user_id -> matrix index
        self.item_mapping: Dict[str, int] = {}  # item_id -> matrix index
        self.reverse_item_mapping: Dict[int, str] = {}  # matrix index -> item_id
        self.trained_at: Optional[datetime] = None

    def train(self, interactions_df: pd.DataFrame) -> bool:
        """
        Обучить модель на данных взаимодействий.

        Args:
            interactions_df: DataFrame с колонками user_id, playlist_item_id, rating

        Returns:
            True если обучение прошло успешно
        """
        try:
            if interactions_df.empty or len(interactions_df) < MIN_INTERACTIONS:
                logger.warning(f"Недостаточно данных для обучения: {len(interactions_df)} < {MIN_INTERACTIONS}")
                return False

            logger.info(f"Начало обучения на {len(interactions_df)} взаимодействиях")

            # Создаем маппинги user_id и item_id в индексы матрицы
            unique_users = interactions_df['user_id'].unique()
            unique_items = interactions_df['playlist_item_id'].unique()

            self.user_ids = list(unique_users)
            self.item_ids = list(unique_items)

            self.user_mapping = {user_id: idx for idx, user_id in enumerate(self.user_ids)}
            self.item_mapping = {item_id: idx for idx, item_id in enumerate(self.item_ids)}
            self.reverse_item_mapping = {idx: item_id for item_id, idx in self.item_mapping.items()}

            # Создаем user-item матрицу (разреженную)
            row_indices = interactions_df['user_id'].map(self.user_mapping)
            col_indices = interactions_df['playlist_item_id'].map(self.item_mapping)
            ratings = interactions_df['rating'].values

            self.user_item_matrix = csr_matrix(
                (ratings, (row_indices, col_indices)),
                shape=(len(self.user_ids), len(self.item_ids))
            )

            # Обучаем SVD для матричной факторизации
            self.svd_model = TruncatedSVD(
                n_components=min(N_COMPONENTS, min(len(self.user_ids), len(self.item_ids)) - 1),
                random_state=42
            )
            self.svd_model.fit(self.user_item_matrix)

            # Сохраняем модель
            self._save_model()

            self.trained_at = datetime.now()
            logger.info(
                f"Модель обучена: {len(self.user_ids)} пользователей, "
                f"{len(self.item_ids)} элементов, "
                f"explained variance: {self.svd_model.explained_variance_ratio_.sum():.3f}"
            )
            return True

        except Exception as e:
            logger.error(f"Ошибка обучения модели: {e}")
            return False

    def predict_for_user(self, user_id: str, exclude_items: Optional[List[str]] = None, n: int = N_RECOMMENDATIONS) -> List[Dict[str, Any]]:
        """
        Сгенерировать рекомендации для пользователя.

        Args:
            user_id: ID пользователя
            exclude_items: Список ID элементов для исключения (уже просмотренные)
            n: Количество рекомендаций

        Returns:
            Список рекомендаций с полями: playlist_item_id, score, reason
        """
        if self.svd_model is None or self.user_item_matrix is None:
            self._load_model()

        if self.svd_model is None:
            logger.warning("Модель не обучена")
            return []

        try:
            # Проверяем, есть ли пользователь в обучающей выборке
            if user_id not in self.user_mapping:
                logger.warning(f"Пользователь {user_id} не найден в обучающей выборке")
                return []

            user_idx = self.user_mapping[user_id]
            exclude_set = set(exclude_items) if exclude_items else set()

            # Получаем вектор пользователя в latent space
            user_vector = self.user_item_matrix[user_idx]
            user_latent = self.svd_model.transform(user_vector)

            # Реконструируем рейтинги для всех элементов
            reconstructed_ratings = self.svd_model.inverse_transform(user_latent)[0]

            # Находим элементы с наивысшими предсказанными рейтингами
            item_scores = []
            for item_idx, score in enumerate(reconstructed_ratings):
                item_id = self.reverse_item_mapping[item_idx]
                if item_id not in exclude_set:
                    item_scores.append({
                        'playlist_item_id': item_id,
                        'score': float(min(score / 5.0, 1.0))  # Нормализуем в 0-1
                    })

            # Сортируем по score и берем топ-n
            item_scores.sort(key=lambda x: x['score'], reverse=True)
            recommendations = item_scores[:n]

            # Добавляем причину рекомендации
            for rec in recommendations:
                rec['reason'] = 'Рекомендовано на основе ваших предпочтений'
                rec['algorithm'] = 'collaborative_filtering'

            logger.info(f"Сгенерировано {len(recommendations)} рекомендаций для пользователя {user_id}")
            return recommendations

        except Exception as e:
            logger.error(f"Ошибка генерации рекомендаций: {e}")
            return []

    def find_similar_users(self, user_id: str, n: int = 5) -> List[Tuple[str, float]]:
        """
        Найти пользователей с похожими предпочтениями.

        Args:
            user_id: ID пользователя
            n: Количество похожих пользователей

        Returns:
            Список пар (user_id, similarity_score)
        """
        if self.svd_model is None or self.user_item_matrix is None:
            self._load_model()

        if self.svd_model is None or user_id not in self.user_mapping:
            return []

        try:
            user_idx = self.user_mapping[user_id]

            # Трансформируем все пользователей в latent space
            all_users_latent = self.svd_model.transform(self.user_item_matrix)
            user_latent = all_users_latent[user_idx:user_idx + 1]

            # Вычисляем косинусное сходство
            similarities = cosine_similarity(user_latent, all_users_latent)[0]

            # Находим топ-n похожих пользователей (исключая самого себя)
            similar_indices = np.argsort(similarities)[::-1][1:n + 1]

            similar_users = [
                (self.user_ids[idx], float(similarities[idx]))
                for idx in similar_indices
            ]

            return similar_users

        except Exception as e:
            logger.error(f"Ошибка поиска похожих пользователей: {e}")
            return []

    def _save_model(self):
        """Сохранить модель на диск."""
        try:
            os.makedirs(MODEL_PATH, exist_ok=True)

            model_data = {
                'svd_model': self.svd_model,
                'user_mapping': self.user_mapping,
                'item_mapping': self.item_mapping,
                'reverse_item_mapping': self.reverse_item_mapping,
                'user_ids': self.user_ids,
                'item_ids': self.item_ids,
                'trained_at': self.trained_at.isoformat() if self.trained_at else None
            }

            joblib.dump(model_data, f'{MODEL_PATH}/collaborative_filtering_model.joblib')
            logger.info("Модель сохранена")

        except Exception as e:
            logger.error(f"Ошибка сохранения модели: {e}")

    def _load_model(self):
        """Загрузить модель с диска."""
        try:
            model_file = f'{MODEL_PATH}/collaborative_filtering_model.joblib'

            if os.path.exists(model_file):
                model_data = joblib.load(model_file)

                self.svd_model = model_data['svd_model']
                self.user_mapping = model_data['user_mapping']
                self.item_mapping = model_data['item_mapping']
                self.reverse_item_mapping = model_data['reverse_item_mapping']
                self.user_ids = model_data['user_ids']
                self.item_ids = model_data['item_ids']
                self.trained_at = datetime.fromisoformat(model_data['trained_at']) if model_data.get('trained_at') else None

                logger.info(f"Модель загружена (обучена {self.trained_at})")
            else:
                logger.warning("Файл модели не найден")

        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")


class ContentBasedFilteringEngine:
    """
    ML-модель для контент-based рекомендаций.
    Базируется на схожести метаданных контента.
    """

    def __init__(self):
        self.item_features: Optional[pd.DataFrame] = None
        self.item_similarity_matrix: Optional[np.ndarray] = None
        self.item_ids: List[str] = []
        self.trained_at: Optional[datetime] = None

    async def train(self, database_url: str) -> bool:
        """
        Обучить модель на метаданных контента.

        Args:
            database_url: URL базы данных

        Returns:
            True если обучение прошло успешно
        """
        try:
            # TODO: Реализация в следующем сабтаске
            logger.info("Content-based фильтрация будет реализована в следующем сабтаске")
            return False

        except Exception as e:
            logger.error(f"Ошибка обучения content-based модели: {e}")
            return False

    def predict_for_user(self, user_id: str, liked_items: List[str], n: int = N_RECOMMENDATIONS) -> List[Dict[str, Any]]:
        """
        Сгенерировать рекомендации на основе похожести контента.

        Args:
            user_id: ID пользователя
            liked_items: Список элементов, которые понравились пользователю
            n: Количество рекомендаций

        Returns:
            Список рекомендаций
        """
        # TODO: Реализация в следующем сабтаске
        return []


class HybridRecommender:
    """
    Гибридная рекомендательная система.
    Комбинирует коллаборативную фильтрацию и content-based подходы.
    """

    def __init__(self, collaborative_engine: CollaborativeFilteringEngine, content_engine: ContentBasedFilteringEngine):
        self.collaborative = collaborative_engine
        self.content = content_engine
        self.collaborative_weight = 0.7  # Вес коллаборативной фильтрации
        self.content_weight = 0.3  # Вес content-based

    def predict_for_user(
        self,
        user_id: str,
        exclude_items: Optional[List[str]] = None,
        n: int = N_RECOMMENDATIONS
    ) -> List[Dict[str, Any]]:
        """
        Сгенерировать гибридные рекомендации.

        Args:
            user_id: ID пользователя
            exclude_items: Список ID элементов для исключения
            n: Количество рекомендаций

        Returns:
            Список рекомендаций
        """
        # TODO: Реализация в следующем сабтаске
        logger.info("Гибридная рекомендация будет реализована в следующем сабтаске")
        return self.collaborative.predict_for_user(user_id, exclude_items, n)
