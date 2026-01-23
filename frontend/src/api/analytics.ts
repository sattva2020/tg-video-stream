/**
 * Analytics API Client
 * Feature: 021-admin-analytics-menu
 * 
 * Клиент для работы с эндпоинтами аналитики.
 */

import { client } from './client';
import type {
  AnalyticsPeriod,
  HistoryInterval,
  AnalyticsSummaryResponse,
  ListenerStatsResponse,
  ListenerHistoryResponse,
  TopTracksResponse,
  EngagementMetricsResponse,
  StreamPerformanceResponse,
  ContentInsightsResponse,
} from '../types/analytics';

/**
 * Получить сводную статистику.
 * 
 * @param period - Период данных (7d, 30d, 90d, all)
 * @returns Сводная статистика
 */
export async function getSummary(period: AnalyticsPeriod = '7d'): Promise<AnalyticsSummaryResponse> {
  const response = await client.get<AnalyticsSummaryResponse>('/api/analytics/summary', {
    params: { period },
  });
  return response.data;
}

/**
 * Получить статистику слушателей.
 * 
 * @returns Текущие, пиковые и средние значения слушателей
 */
export async function getListenerStats(): Promise<ListenerStatsResponse> {
  const response = await client.get<ListenerStatsResponse>('/api/analytics/listeners');
  return response.data;
}

/**
 * Получить историю слушателей для графиков.
 * 
 * @param period - Период данных
 * @param interval - Интервал агрегации (hour, day)
 * @returns Данные для графика
 */
export async function getListenerHistory(
  period: AnalyticsPeriod = '7d',
  interval: HistoryInterval = 'day'
): Promise<ListenerHistoryResponse> {
  const response = await client.get<ListenerHistoryResponse>('/api/analytics/listeners/history', {
    params: { period, interval },
  });
  return response.data;
}

/**
 * Получить топ треков.
 *
 * @param period - Период данных
 * @param limit - Количество треков (1-50)
 * @returns Список топ треков
 */
export async function getTopTracks(
  period: AnalyticsPeriod = '7d',
  limit: number = 5
): Promise<TopTracksResponse> {
  const response = await client.get<TopTracksResponse>('/api/analytics/top-tracks', {
    params: { period, limit },
  });
  return response.data;
}

/**
 * Получить метрики вовлеченности.
 *
 * @param period - Период данных (7d, 30d, 90d, all)
 * @returns Метрики вовлеченности
 */
export async function getEngagement(period: AnalyticsPeriod = '7d'): Promise<EngagementMetricsResponse> {
  const response = await client.get<EngagementMetricsResponse>('/api/analytics/engagement', {
    params: { period },
  });
  return response.data;
}

/**
 * Получить показатели производительности потока.
 *
 * @param period - Период данных (7d, 30d, 90d, all)
 * @returns Показатели производительности потока
 */
export async function getStreamPerformance(period: AnalyticsPeriod = '7d'): Promise<StreamPerformanceResponse> {
  const response = await client.get<StreamPerformanceResponse>('/api/analytics/stream-performance', {
    params: { period },
  });
  return response.data;
}

/**
 * Получить аналитику контента.
 *
 * @param period - Период данных (7d, 30d, 90d, all)
 * @returns Аналитика контента
 */
export async function getContentInsights(period: AnalyticsPeriod = '7d'): Promise<ContentInsightsResponse> {
  const response = await client.get<ContentInsightsResponse>('/api/analytics/content-insights', {
    params: { period },
  });
  return response.data;
}
