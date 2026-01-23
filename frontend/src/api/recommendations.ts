/**
 * Recommendation API Client
 * Feature: 014-ai-powered-content-recommendations
 *
 * Клиент для работы с эндпоинтами рекомендаций.
 */

import { client } from './client';
import type {
  RecommendationAlgorithm,
  RecommendationRequest,
  RecommendationResponse,
  FeedbackRequest,
  FeedbackResponse,
  RecommendationStatsResponse,
} from '../types/recommendations';

/**
 * Получить персонализированные рекомендации.
 *
 * @param params - Параметры запроса
 * @param params.user_id - ID пользователя (опционально)
 * @param params.limit - Количество рекомендаций (1-100, default 10)
 * @param params.algorithm - Алгоритм рекомендации (collaborative_filtering, content_based, hybrid)
 * @param params.exclude_watched - Исключать уже просмотренное
 * @returns Список рекомендаций
 */
export async function getRecommendations(
  params: RecommendationRequest = {}
): Promise<RecommendationResponse> {
  const {
    user_id,
    limit = 10,
    algorithm = 'hybrid',
    exclude_watched = true,
  } = params;

  const response = await client.get<RecommendationResponse>('/api/recommendations', {
    params: {
      user_id,
      limit,
      algorithm,
      exclude_watched,
    },
  });
  return response.data;
}

/**
 * Получить рекомендации для плейлиста.
 *
 * @param playlist_id - ID плейлиста
 * @param limit - Количество рекомендаций (1-100, default 10)
 * @returns Список рекомендаций для плейлиста
 */
export async function getRecommendationsForPlaylist(
  playlist_id: number,
  limit: number = 10
): Promise<RecommendationResponse> {
  const response = await client.get<RecommendationResponse>('/api/recommendations/for-playlist', {
    params: { playlist_id, limit },
  });
  return response.data;
}

/**
 * Отправить обратную связь (like/dislike).
 *
 * @param data - Данные обратной связи
 * @param data.playlist_item_id - ID элемента плейлиста
 * @param data.feedback_type - Тип обратной связи (like или dislike)
 * @returns Результат добавления обратной связи
 */
export async function submitFeedback(
  data: FeedbackRequest
): Promise<FeedbackResponse> {
  const response = await client.post<FeedbackResponse>('/api/recommendations/feedback', data);
  return response.data;
}

/**
 * Получить статистику качества рекомендаций.
 *
 * @param period - Период данных (7d, 30d, 90d)
 * @returns Метрики качества рекомендаций
 */
export async function getRecommendationStats(
  period: '7d' | '30d' | '90d' = '7d'
): Promise<RecommendationStatsResponse> {
  const response = await client.get<RecommendationStatsResponse>('/api/recommendations/stats', {
    params: { period },
  });
  return response.data;
}
