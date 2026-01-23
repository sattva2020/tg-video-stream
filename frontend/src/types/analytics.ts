/**
 * Analytics types for admin dashboard
 * Feature: 021-admin-analytics-menu
 */

/** Период для фильтрации данных аналитики */
export type AnalyticsPeriod = '7d' | '30d' | '90d' | 'all';

/** Интервал агрегации для истории слушателей */
export type HistoryInterval = 'hour' | 'day';

/** Статистика слушателей */
export interface ListenerStats {
  /** Текущее количество слушателей */
  current: number;
  /** Пиковое значение за сегодня */
  peak_today: number;
  /** Пиковое значение за неделю */
  peak_week: number;
  /** Среднее за неделю */
  average_week: number;
}

/** Точка на графике истории слушателей */
export interface ListenerHistoryPoint {
  /** Временная метка */
  timestamp: string;
  /** Количество слушателей */
  count: number;
}

/** Ответ с историей слушателей */
export interface ListenerHistoryResponse {
  /** Период данных */
  period: AnalyticsPeriod;
  /** Данные для графика */
  data: ListenerHistoryPoint[];
}

/** Ответ со статистикой слушателей */
export interface ListenerStatsResponse extends ListenerStats {
  /** Кэшировано в */
  cached_at?: string;
}

/** Трек в топе */
export interface TopTrackItem {
  /** ID трека */
  track_id: number;
  /** Название трека */
  title: string;
  /** Исполнитель */
  artist: string | null;
  /** Количество воспроизведений */
  play_count: number;
  /** Общая длительность воспроизведения в секундах */
  total_duration_seconds: number;
}

/** Ответ с топом треков */
export interface TopTracksResponse {
  /** Период данных */
  period: AnalyticsPeriod;
  /** Список треков */
  tracks: TopTrackItem[];
}

/** Сводная статистика */
export interface AnalyticsSummaryResponse {
  /** Период данных */
  period: AnalyticsPeriod;
  /** Общее количество воспроизведений */
  total_plays: number;
  /** Общее время вещания в часах */
  total_duration_hours: number;
  /** Количество уникальных треков */
  unique_tracks: number;
  /** Статистика слушателей */
  listeners: ListenerStats;
  /** Время кэширования */
  cached_at: string;
}

/** Запрос на запись воспроизведения трека (internal) */
export interface TrackPlayRequest {
  /** ID трека */
  track_id: number;
  /** Длительность в секундах */
  duration_seconds?: number;
  /** Количество слушателей */
  listeners_count: number;
}

/** Ответ на запись воспроизведения трека */
export interface TrackPlayResponse {
  /** ID записи */
  id: number;
  /** Время записи */
  played_at: string;
}

/** Метрики платформы */
export interface PlatformMetrics {
  /** ID платформы */
  platform_id: string;
  /** Тип платформы */
  platform_type: 'youtube' | 'twitch' | 'twitter' | 'discord' | 'custom_rtmp';
  /** Название платформы */
  platform_name: string;
  /** Статус платформы */
  status: 'inactive' | 'active' | 'error';
  /** Количество стримов */
  stream_count: number;
  /** Общее время стриминга в часах */
  total_stream_hours: number;
  /** Количество постов */
  post_count: number;
  /** Успешные посты */
  successful_posts: number;
  /** Неудачные посты */
  failed_posts: number;
  /** Последняя активность */
  last_activity?: string;
}

/** Ответ с мультиплатформенной аналитикой */
export interface MultiPlatformAnalyticsResponse {
  /** Период данных */
  period: AnalyticsPeriod;
  /** Общее количество платформ */
  total_platforms: number;
  /** Активные платформы */
  active_platforms: number;
  /** Список платформ */
  platforms: PlatformMetrics[];
  /** Общее количество стримов */
  total_streams: number;
  /** Общее время стриминга в часах */
  total_stream_hours: number;
  /** Общее количество постов */
  total_posts: number;
  /** Успешные посты rate */
  successful_posts_rate: number;
  /** Время кэширования */
  cached_at: string;
}
