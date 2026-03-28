/**
 * Recommendation types for admin dashboard
 * Feature: 014-ai-powered-content-recommendations
 */

/** Алгоритм рекомендации */
export type RecommendationAlgorithm = 'collaborative_filtering' | 'content_based' | 'hybrid';

/** Тип обратной связи */
export type FeedbackType = 'like' | 'dislike';

/** Тип взаимодействия */
export type InteractionType = 'watch' | 'skip' | 'like' | 'share' | 'click';

/** Один рекомендованный элемент */
export interface RecommendationItem {
  /** ID элемента плейлиста */
  playlist_item_id: string;
  /** Название видео */
  title: string;
  /** Исполнитель/Автор */
  artist?: string | null;
  /** Уверенность рекомендации от 0 до 1 */
  score: number;
  /** Алгоритм рекомендации */
  algorithm: RecommendationAlgorithm;
  /** Причина рекомендации (например, 'Похоже на то, что вы смотрели') */
  reason?: string | null;
}

/** Запрос на получение рекомендаций */
export interface RecommendationRequest {
  /** ID пользователя (опционально, берется из auth) */
  user_id?: string | null;
  /** ID плейлиста для получения рекомендаций для плейлиста */
  playlist_id?: number | null;
  /** Количество рекомендаций (максимум 100) */
  limit?: number;
  /** Алгоритм рекомендации */
  algorithm?: RecommendationAlgorithm;
  /** Исключать уже просмотренное */
  exclude_watched?: boolean;
}

/** Список рекомендаций для пользователя */
export interface RecommendationResponse {
  /** Список рекомендаций */
  recommendations: RecommendationItem[];
  /** Общее количество рекомендаций */
  total_count: number;
  /** Использованный алгоритм */
  algorithm: RecommendationAlgorithm;
  /** Время генерации рекомендаций */
  generated_at: string;
}

/** Запрос на добавление обратной связи */
export interface FeedbackRequest {
  /** ID элемента плейлиста */
  playlist_item_id: string;
  /** Тип обратной связи: like или dislike */
  feedback_type: FeedbackType;
}

/** Ответ на добавление обратной связи */
export interface FeedbackResponse {
  /** ID записи обратной связи */
  id: number;
  /** ID элемента плейлиста */
  playlist_item_id: string;
  /** Тип обратной связи */
  feedback_type: FeedbackType;
  /** Время создания записи */
  created_at: string;
}

/** Запрос на запись взаимодействия */
export interface InteractionRequest {
  /** ID элемента плейлиста */
  playlist_item_id: string;
  /** Тип взаимодействия */
  interaction_type: InteractionType;
  /** Длительность в секундах */
  duration_seconds?: number | null;
  /** Доля просмотра от 0 до 1 */
  completion_rate?: number | null;
}

/** Ответ на запись взаимодействия */
export interface InteractionResponse {
  /** ID записи взаимодействия */
  id: number;
  /** ID элемента плейлиста */
  playlist_item_id: string;
  /** Тип взаимодействия */
  interaction_type: InteractionType;
  /** Время записи */
  interacted_at: string;
}

/** Метрики качества рекомендаций */
export interface RecommendationQualityMetrics {
  /** CTR (доля кликов по рекомендациям) */
  click_through_rate: number;
  /** Среднее время просмотра */
  average_watch_time_seconds: number;
  /** Доля положительной обратной связи */
  feedback_positive_rate: number;
  /** Общее количество показанных рекомендаций */
  total_recommendations_shown: number;
  /** Общее количество взаимодействий */
  total_interactions: number;
}

/** Статистика рекомендаций */
export interface RecommendationStatsResponse {
  /** Период данных (например, '7d', '30d') */
  period: string;
  /** Метрики качества */
  quality_metrics: RecommendationQualityMetrics;
  /** Производительность по алгоритмам */
  algorithm_performance: Array<Record<string, unknown>>;
  /** Время кэширования */
  cached_at: string;
}
