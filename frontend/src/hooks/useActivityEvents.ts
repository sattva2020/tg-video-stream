/**
 * useActivityEvents Hook
 * Spec: 015-real-system-monitoring
 * 
 * TanStack Query хук для получения событий активности.
 * Автоматически обновляется каждые 30 секунд.
 */

import { useQuery } from '@tanstack/react-query';
import { systemApi, GetActivityParams } from '../api/system';
import type { ActivityEventsResponse } from '../types/system';

/**
 * Query key для событий активности.
 */
export const ACTIVITY_EVENTS_QUERY_KEY = ['system', 'activity'] as const;

/**
 * Интервал автообновления событий (30 секунд).
 */
export const ACTIVITY_REFETCH_INTERVAL = 30 * 1000;

/**
 * Опции для хука useActivityEvents.
 */
export interface UseActivityEventsOptions {
  /** Количество записей на странице (1-100) */
  limit?: number;
  /** Смещение для пагинации */
  offset?: number;
  /** Фильтр по типу события */
  type?: string;
  /** Поиск по тексту сообщения */
  search?: string;
  /** Включить автообновление (по умолчанию true) */
  autoRefresh?: boolean;
}

/**
 * Хук для получения событий активности.
 * 
 * @param options - Параметры пагинации и фильтрации
 * 
 * @example
 * ```tsx
 * function ActivityTimeline() {
 *   const { data, isLoading, error } = useActivityEvents({ limit: 10 });
 *   
 *   if (isLoading) return <Skeleton />;
 *   if (error) return <ErrorMessage />;
 *   
 *   return (
 *     <ul>
 *       {data.events.map(event => (
 *         <li key={event.id}>{event.message}</li>
 *       ))}
 *     </ul>
 *   );
 * }
 * ```
 */
export function useActivityEvents(options: UseActivityEventsOptions = {}) {
  const {
    limit = 20,
    offset = 0,
    type,
    search,
    autoRefresh = true,
  } = options;

  const params: GetActivityParams = {
    limit,
    offset,
    type: type || undefined,
    search: search || undefined,
  };

  const query = useQuery({
    queryKey: [...ACTIVITY_EVENTS_QUERY_KEY, params] as const,
    queryFn: () => systemApi.getActivity(params),
    staleTime: ACTIVITY_REFETCH_INTERVAL / 2, // 15 секунд
    refetchInterval: autoRefresh ? ACTIVITY_REFETCH_INTERVAL : false,
    refetchOnWindowFocus: true,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  });

  return {
    ...query,
    // Алиасы для удобства
    events: query.data?.events ?? [],
    total: query.data?.total ?? 0,
    // Информация о пагинации
    hasMore: query.data ? offset + limit < query.data.total : false,
    currentPage: Math.floor(offset / limit) + 1,
    totalPages: query.data ? Math.ceil(query.data.total / limit) : 0,
  };
}

export default useActivityEvents;
