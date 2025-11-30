/**
 * System Monitoring API Client
 * Spec: 015-real-system-monitoring
 * 
 * Клиент для работы с эндпоинтами мониторинга системы.
 */

import { client } from './client';
import type { SystemMetrics, ActivityEventsResponse } from '../types/system';

/**
 * Получить текущие системные метрики.
 * 
 * @returns Метрики CPU, RAM, Disk, DB connections, uptime
 */
export async function getMetrics(): Promise<SystemMetrics> {
  const response = await client.get<SystemMetrics>('/api/system/metrics');
  return response.data;
}

/**
 * Параметры запроса для получения событий активности.
 */
export interface GetActivityParams {
  limit?: number;
  offset?: number;
  type?: string;
  search?: string;
}

/**
 * Получить список событий активности.
 * 
 * @param params - Параметры пагинации и фильтрации
 * @returns Список событий и общее количество
 */
export async function getActivity(params?: GetActivityParams): Promise<ActivityEventsResponse> {
  const response = await client.get<ActivityEventsResponse>('/api/system/activity', {
    params: {
      limit: params?.limit ?? 20,
      offset: params?.offset ?? 0,
      type: params?.type,
      search: params?.search,
    },
  });
  return response.data;
}

/**
 * Объект API для системного мониторинга.
 */
export const systemApi = {
  getMetrics,
  getActivity,
};

export default systemApi;
