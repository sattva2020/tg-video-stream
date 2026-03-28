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
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from scipy.sparse import csr_matrix, hstack as sparse_hstack

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

    Использует:
    - TF-IDF для текстовых признаков (название)
    - One-hot encoding для категориальных признаков (тип, канал)
    - Косинусное сходство для поиска похожих элементов
    """

    def __init__(self):
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.item_features_matrix: Optional[csr_matrix] = None
        self.item_similarity_matrix: Optional[np.ndarray] = None
        self.item_ids: List[str] = []
        self.item_mapping: Dict[str, int] = {}  # item_id -> matrix index
        self.reverse_item_mapping: Dict[int, str] = {}  # matrix index -> item_id
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
            from src.models.playlist import PlaylistItem

            engine = create_engine(database_url)
            SessionLocal = sessionmaker(bind=engine)

            session = SessionLocal()
            try:
                # Получаем все элементы плейлиста с метаданными
                items = session.query(
                    PlaylistItem.id,
                    PlaylistItem.title,
                    PlaylistItem.type,
                    PlaylistItem.duration,
                    PlaylistItem.channel_id
                ).all()

                if not items or len(items) < 2:
                    logger.warning(f"Недостаточно элементов для обучения: {len(items) if items else 0}")
                    return False

                logger.info(f"Начало обучения на {len(items)} элементах")

                # Подготовка данных
                item_data = []
                for item in items:
                    item_data.append({
                        'id': str(item.id),
                        'title': item.title or '',
                        'type': item.type or 'youtube',
                        'duration': float(item.duration) if item.duration else 0.0,
                        'channel_id': str(item.channel_id) if item.channel_id else 'unknown'
                    })

                df = pd.DataFrame(item_data)

                # Создаем маппинги
                self.item_ids = df['id'].tolist()
                self.item_mapping = {item_id: idx for idx, item_id in enumerate(self.item_ids)}
                self.reverse_item_mapping = {idx: item_id for item_id, idx in self.item_mapping.items()}

                # 1. TF-IDF для текстовых признаков (название)
                self.tfidf_vectorizer = TfidfVectorizer(
                    max_features=100,
                    ngram_range=(1, 2),
                    min_df=1,
                    stop_words='english'
                )
                title_features = self.tfidf_vectorizer.fit_transform(df['title'].fillna(''))

                # 2. One-hot encoding для категориальных признаков
                # Type (youtube, local, stream)
                type_features = pd.get_dummies(df['type'], prefix='type').values

                # Channel ID (закодирован как индекс)
                unique_channels = df['channel_id'].unique()
                channel_mapping = {ch: idx for idx, ch in enumerate(unique_channels)}
                channel_features = np.array([[channel_mapping.get(ch, 0)] for ch in df['channel_id']])

                # 3. Нормализуем числовые признаки
                duration_features = df[['duration']].values
                scaler = StandardScaler()
                duration_features_scaled = scaler.fit_transform(duration_features)

                # Объединяем все признаки в разреженную матрицу
                from scipy.sparse import csr_matrix
                type_sparse = csr_matrix(type_features)
                channel_sparse = csr_matrix(channel_features)
                duration_sparse = csr_matrix(duration_features_scaled)

                # Комбинируем все признаки
                self.item_features_matrix = sparse_hstack([
                    title_features,
                    type_sparse,
                    channel_sparse,
                    duration_sparse
                ])

                # Вычисляем матрицу сходства (косинусное сходство)
                self.item_similarity_matrix = cosine_similarity(self.item_features_matrix)

                # Сохраняем модель
                self._save_model()

                self.trained_at = datetime.now()
                logger.info(
                    f"Модель обучена: {len(self.item_ids)} элементов, "
                    f"признаков: {self.item_features_matrix.shape[1]}"
                )
                return True

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Ошибка обучения content-based модели: {e}")
            return False

    def predict_for_user(
        self,
        user_id: str,
        liked_items: List[str],
        exclude_items: Optional[List[str]] = None,
        n: int = N_RECOMMENDATIONS
    ) -> List[Dict[str, Any]]:
        """
        Сгенерировать рекомендации на основе похожести контента.

        Args:
            user_id: ID пользователя
            liked_items: Список элементов, которые понравились пользователю
            exclude_items: Список ID элементов для исключения
            n: Количество рекомендаций

        Returns:
            Список рекомендаций с полями: playlist_item_id, score, reason
        """
        if self.item_similarity_matrix is None:
            self._load_model()

        if self.item_similarity_matrix is None:
            logger.warning("Модель не обучена")
            return []

        try:
            if not liked_items:
                logger.warning(f"Нет понравившихся элементов для пользователя {user_id}")
                return []

            # Фильтруем понравившиеся элементы, которые есть в модели
            valid_liked_items = [item_id for item_id in liked_items if item_id in self.item_mapping]

            if not valid_liked_items:
                logger.warning(f"Нет валидных понравившихся элементов для пользователя {user_id}")
                return []

            exclude_set = set(exclude_items) if exclude_items else set()
            exclude_set.update(liked_items)  # Исключаем уже понравившиеся

            # Вычисляем среднее сходство со всеми понравившимися элементами
            item_scores = {}

            for liked_item_id in valid_liked_items:
                liked_idx = self.item_mapping[liked_item_id]

                # Получаем сходства со всеми элементами
                similarities = self.item_similarity_matrix[liked_idx]

                # Добавляем к общему скору
                for item_idx, similarity in enumerate(similarities):
                    item_id = self.reverse_item_mapping[item_idx]
                    if item_id not in exclude_set:
                        if item_id not in item_scores:
                            item_scores[item_id] = []
                        item_scores[item_id].append(float(similarity))

            # Усредняем сходства от всех понравившихся элементов
            recommendations = []
            for item_id, similarities in item_scores.items():
                avg_similarity = np.mean(similarities)
                recommendations.append({
                    'playlist_item_id': item_id,
                    'score': float(avg_similarity)
                })

            # Сортируем по score и берем топ-n
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            recommendations = recommendations[:n]

            # Добавляем причину рекомендации
            for rec in recommendations:
                rec['reason'] = 'Похоже на то, что вам нравилось ранее'
                rec['algorithm'] = 'content_based'

            logger.info(f"Сгенерировано {len(recommendations)} content-based рекомендаций для пользователя {user_id}")
            return recommendations

        except Exception as e:
            logger.error(f"Ошибка генерации content-based рекомендаций: {e}")
            return []

    def find_similar_items(self, item_id: str, n: int = 5) -> List[Tuple[str, float]]:
        """
        Найти похожие элементы на основе метаданных.

        Args:
            item_id: ID элемента
            n: Количество похожих элементов

        Returns:
            Список пар (item_id, similarity_score)
        """
        if self.item_similarity_matrix is None:
            self._load_model()

        if self.item_similarity_matrix is None or item_id not in self.item_mapping:
            return []

        try:
            item_idx = self.item_mapping[item_id]

            # Получаем сходства для этого элемента
            similarities = self.item_similarity_matrix[item_idx]

            # Находим топ-n похожих элементов (исключая сам элемент)
            similar_indices = np.argsort(similarities)[::-1][1:n + 1]

            similar_items = [
                (self.reverse_item_mapping[idx], float(similarities[idx]))
                for idx in similar_indices
            ]

            return similar_items

        except Exception as e:
            logger.error(f"Ошибка поиска похожих элементов: {e}")
            return []

    def _save_model(self):
        """Сохранить модель на диск."""
        try:
            os.makedirs(MODEL_PATH, exist_ok=True)

            model_data = {
                'tfidf_vectorizer': self.tfidf_vectorizer,
                'item_features_matrix': self.item_features_matrix,
                'item_similarity_matrix': self.item_similarity_matrix,
                'item_mapping': self.item_mapping,
                'reverse_item_mapping': self.reverse_item_mapping,
                'item_ids': self.item_ids,
                'trained_at': self.trained_at.isoformat() if self.trained_at else None
            }

            joblib.dump(model_data, f'{MODEL_PATH}/content_based_model.joblib')
            logger.info("Content-based модель сохранена")

        except Exception as e:
            logger.error(f"Ошибка сохранения content-based модели: {e}")

    def _load_model(self):
        """Загрузить модель с диска."""
        try:
            model_file = f'{MODEL_PATH}/content_based_model.joblib'

            if os.path.exists(model_file):
                model_data = joblib.load(model_file)

                self.tfidf_vectorizer = model_data['tfidf_vectorizer']
                self.item_features_matrix = model_data['item_features_matrix']
                self.item_similarity_matrix = model_data['item_similarity_matrix']
                self.item_mapping = model_data['item_mapping']
                self.reverse_item_mapping = model_data['reverse_item_mapping']
                self.item_ids = model_data['item_ids']
                self.trained_at = datetime.fromisoformat(model_data['trained_at']) if model_data.get('trained_at') else None

                logger.info(f"Content-based модель загружена (обучена {self.trained_at})")
            else:
                logger.warning("Файл content-based модели не найден")

        except Exception as e:
            logger.error(f"Ошибка загрузки content-based модели: {e}")


class HybridRecommender:
    """
    Гибридная рекомендательная система.
    Комбинирует коллаборативную фильтрацию и content-based подходы.

    Стратегии комбинирования:
    - Weighted hybrid: взвешенная сумма скоров обоих алгоритмов
    - Switching hybrid: выбор одного алгоритма в зависимости от ситуации
    - Cascade hybrid: сначала один алгоритм, затем другой для уточнения
    """

    def __init__(self, collaborative_engine: CollaborativeFilteringEngine, content_engine: ContentBasedFilteringEngine):
        self.collaborative = collaborative_engine
        self.content = content_engine
        self.collaborative_weight = 0.7  # Вес коллаборативной фильтрации
        self.content_weight = 0.3  # Вес content-based
        self.min_collaborative_score = 0.3  # Минимальный скор для использования коллаборативной фильтрации

    async def predict_for_user(
        self,
        user_id: str,
        liked_items: Optional[List[str]] = None,
        exclude_items: Optional[List[str]] = None,
        n: int = N_RECOMMENDATIONS,
        strategy: str = 'weighted'
    ) -> List[Dict[str, Any]]:
        """
        Сгенерировать гибридные рекомендации.

        Args:
            user_id: ID пользователя
            liked_items: Список элементов, понравившихся пользователю
            exclude_items: Список ID элементов для исключения
            n: Количество рекомендаций
            strategy: Стратегия комбинирования ('weighted', 'switching', 'cascade')

        Returns:
            Список рекомендаций с полями: playlist_item_id, score, reason, algorithm
        """
        try:
            logger.info(f"Генерация {n} гибридных рекомендаций для пользователя {user_id} (стратегия: {strategy})")

            # Получаем рекомендации от обоих алгоритмов
            collaborative_recs = self.collaborative.predict_for_user(
                user_id=user_id,
                exclude_items=exclude_items,
                n=n * 2  # Берем больше, чтобы потом выбрать лучшие
            )

            content_recs = []
            if liked_items:
                content_recs = self.content.predict_for_user(
                    user_id=user_id,
                    liked_items=liked_items,
                    exclude_items=exclude_items,
                    n=n * 2
                )

            # Выбираем стратегию комбинирования
            if strategy == 'weighted':
                recommendations = self._weighted_hybrid(collaborative_recs, content_recs, n)
            elif strategy == 'switching':
                recommendations = self._switching_hybrid(collaborative_recs, content_recs, n, user_id)
            elif strategy == 'cascade':
                recommendations = self._cascade_hybrid(collaborative_recs, content_recs, n)
            else:
                logger.warning(f"Неизвестная стратегия: {strategy}, используем weighted")
                recommendations = self._weighted_hybrid(collaborative_recs, content_recs, n)

            logger.info(f"Сгенерировано {len(recommendations)} гибридных рекомендаций для пользователя {user_id}")
            return recommendations

        except Exception as e:
            logger.error(f"Ошибка генерации гибридных рекомендаций: {e}")
            # Fallback: возвращаем только коллаборативные рекомендации
            return self.collaborative.predict_for_user(user_id, exclude_items, n)

    def _weighted_hybrid(
        self,
        collaborative_recs: List[Dict[str, Any]],
        content_recs: List[Dict[str, Any]],
        n: int
    ) -> List[Dict[str, Any]]:
        """
        Weighted hybrid: взвешенная сумма скоров.

        Формула: final_score = w1 * collaborative_score + w2 * content_score
        """
        try:
            # Создаем словарь для агрегации скоров
            item_scores: Dict[str, Dict[str, Any]] = {}

            # Добавляем коллаборативные рекомендации
            for rec in collaborative_recs:
                item_id = rec['playlist_item_id']
                if item_id not in item_scores:
                    item_scores[item_id] = {
                        'collaborative_score': 0.0,
                        'content_score': 0.0,
                        'algorithms': []
                    }
                item_scores[item_id]['collaborative_score'] = rec['score']
                item_scores[item_id]['algorithms'].append('collaborative')

            # Добавляем content-based рекомендации
            for rec in content_recs:
                item_id = rec['playlist_item_id']
                if item_id not in item_scores:
                    item_scores[item_id] = {
                        'collaborative_score': 0.0,
                        'content_score': 0.0,
                        'algorithms': []
                    }
                item_scores[item_id]['content_score'] = rec['score']
                if 'content' not in item_scores[item_id]['algorithms']:
                    item_scores[item_id]['algorithms'].append('content')

            # Вычисляем гибридный скор
            recommendations = []
            for item_id, scores in item_scores.items():
                # Нормализуем скоры (если отсутствуют, считаем равными 0)
                collab_score = scores['collaborative_score']
                content_score = scores['content_score']

                # Weighted combination
                hybrid_score = (
                    self.collaborative_weight * collab_score +
                    self.content_weight * content_score
                )

                # Определяем причину рекомендации
                if collab_score > 0 and content_score > 0:
                    reason = 'Рекомендовано на основе ваших предпочтений и похожего контента'
                elif collab_score > 0:
                    reason = 'Рекомендовано на основе ваших предпочтений'
                else:
                    reason = 'Похоже на то, что вам нравилось ранее'

                recommendations.append({
                    'playlist_item_id': item_id,
                    'score': float(hybrid_score),
                    'reason': reason,
                    'algorithm': 'hybrid_weighted',
                    'algorithms_used': scores['algorithms']
                })

            # Сортируем по гибридному скору и берем топ-n
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:n]

        except Exception as e:
            logger.error(f"Ошибка в weighted hybrid: {e}")
            # Fallback: возвращаем коллаборативные рекомендации
            return collaborative_recs[:n]

    def _switching_hybrid(
        self,
        collaborative_recs: List[Dict[str, Any]],
        content_recs: List[Dict[str, Any]],
        n: int,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Switching hybrid: выбор алгоритма в зависимости от ситуации.

        Логика:
        - Если пользователь в системе достаточно давно и есть хорошие коллаборативные рекомендации → используем их
        - Если новый пользователь или коллаборативные рекомендации слабые → используем content-based
        """
        try:
            # Проверяем качество коллаборативных рекомендаций
            if collaborative_recs and len(collaborative_recs) > 0:
                avg_collab_score = np.mean([rec['score'] for rec in collaborative_recs])

                # Если средний скор достаточно высок, используем коллаборативную фильтрацию
                if avg_collab_score >= self.min_collaborative_score:
                    logger.info(f"Используем коллаборативную фильтрацию для пользователя {user_id} (score: {avg_collab_score:.3f})")
                    recommendations = collaborative_recs[:n]
                    for rec in recommendations:
                        rec['algorithm'] = 'hybrid_switching_collaborative'
                    return recommendations

            # Иначе используем content-based
            logger.info(f"Используем content-based для пользователя {user_id}")
            recommendations = content_recs[:n] if content_recs else []
            for rec in recommendations:
                rec['algorithm'] = 'hybrid_switching_content'
            return recommendations

        except Exception as e:
            logger.error(f"Ошибка в switching hybrid: {e}")
            return collaborative_recs[:n]

    def _cascade_hybrid(
        self,
        collaborative_recs: List[Dict[str, Any]],
        content_recs: List[Dict[str, Any]],
        n: int
    ) -> List[Dict[str, Any]]:
        """
        Cascade hybrid: сначала коллаборативная фильтрация, затем content-based для заполнения.

        Логика:
        1. Берем топ-k рекомендаций из коллаборативной фильтрации
        2. Если недостаточно, дополняем content-based рекомендациями
        3. Ранжируем и берем топ-n
        """
        try:
            recommendations = []

            # Сначала добавляем коллаборативные рекомендации
            collab_count = min(int(n * 0.7), len(collaborative_recs))  # 70% от коллаборативных
            for rec in collaborative_recs[:collab_count]:
                rec_copy = rec.copy()
                rec_copy['algorithm'] = 'hybrid_cascade_collaborative'
                rec_copy['algorithms_used'] = ['collaborative']
                recommendations.append(rec_copy)

            # Затем дополняем content-based
            remaining = n - len(recommendations)
            if remaining > 0 and content_recs:
                # Исключаем уже рекомендованные элементы
                recommended_ids = {rec['playlist_item_id'] for rec in recommendations}

                for rec in content_recs:
                    if len(recommendations) >= n:
                        break
                    if rec['playlist_item_id'] not in recommended_ids:
                        rec_copy = rec.copy()
                        rec_copy['algorithm'] = 'hybrid_cascade_content'
                        rec_copy['algorithms_used'] = ['content']
                        recommendations.append(rec_copy)

            return recommendations

        except Exception as e:
            logger.error(f"Ошибка в cascade hybrid: {e}")
            return collaborative_recs[:n]
