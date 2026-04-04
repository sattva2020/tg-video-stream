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

// === Engagement Metrics Types ===

/** Точка на графике вовлеченности */
export interface EngagementTrendPoint {
  /** Временная метка */
  timestamp: string;
  /** Количество сообщений в чате */
  message_count: number;
  /** Количество реакций */
  reaction_count: number;
  /** Количество уникальных пользователей */
  unique_users: number;
}

/** Активный пользователь в рейтинге */
export interface ActiveUserItem {
  /** ID пользователя */
  user_id: number | null;
  /** Имя пользователя */
  username: string | null;
  /** Количество сообщений */
  message_count: number;
  /** Количество реакций */
  reaction_count: number;
  /** Время последней активности */
  last_activity: string;
}

/** Метрики вовлеченности за период */
export interface EngagementMetricsResponse {
  /** Период данных */
  period: AnalyticsPeriod;
  /** Общее количество сообщений */
  total_messages: number;
  /** Общее количество реакций */
  total_reactions: number;
  /** Общее количество комментариев */
  total_comments: number;
  /** Количество уникальных пользователей */
  unique_users: number;
  /** Среднее количество событий в день */
  average_daily: number;
  /** Топ активных пользователей */
  top_active_users: ActiveUserItem[];
  /** Данные для графика */
  engagement_over_time: EngagementTrendPoint[];
  /** Время кэширования */
  cached_at: string;
}

// === Stream Performance Types ===

/** Распределение по качеству */
export interface QualityDistributionItem {
  /** Уровень качества */
  quality: string;
  /** Количество записей */
  count: number;
  /** Процент от общего количества */
  percentage: number;
}

/** Точка на графике качества потока */
export interface QualityTrendPoint {
  /** Временная метка */
  timestamp: string;
  /** Общее качество */
  overall_quality: string;
  /** Аудио битрейт */
  audio_bitrate_kbps: number | null;
  /** Видео битрейт */
  video_bitrate_kbps: number | null;
  /** Процент буферизации */
  buffering_percentage: number | null;
}

/** Показатели производительности потока */
export interface StreamPerformanceResponse {
  /** Период данных */
  period: AnalyticsPeriod;
  /** Процент аптайма */
  uptime_percentage: number;
  /** Аптайм в часах */
  uptime_hours: number;
  /** Средний процент буферизации */
  average_buffering_percentage: number;
  /** Количество изменений качества */
  quality_changes_count: number;
  /** Использование полосы пропускания */
  bandwidth_usage_mbps: number | null;
  /** Текущее качество потока */
  current_quality: string;
  /** Распределение по качеству */
  quality_distribution: QualityDistributionItem[];
  /** Данные для графика */
  quality_over_time: QualityTrendPoint[];
  /** Время кэширования */
  cached_at: string;
}

// === Content Insights Types ===

/** Элемент контента в рейтинге */
export interface ContentPerformanceItem {
  /** ID контента */
  content_id: string;
  /** Название контента */
  title: string;
  /** Общее количество просмотров */
  total_views: number;
  /** Средний процент досмотра */
  average_completion_percentage: number;
  /** Общее время просмотра в минутах */
  total_watch_time_minutes: number;
  /** Средняя длительность просмотра */
  average_watch_duration_seconds: number;
}

/** Точка отказа (drop-off point) */
export interface DropOffPoint {
  /** Позиция в секундах */
  position_seconds: number;
  /** Процент зрителей, остановившихся здесь */
  percentage: number;
  /** Количество зрителей */
  viewers_count: number;
  /** Кумулятивный процент отказа */
  cumulative_drop_off: number;
}

/** Аналитика контента */
export interface ContentInsightsResponse {
  /** Период данных */
  period: AnalyticsPeriod;
  /** Самый просматриваемый контент */
  most_watched: ContentPerformanceItem[];
  /** Точки отказа */
  drop_off_points: DropOffPoint[];
  /** Средний рейтинг завершения */
  average_completion_rate: number;
  /** Общее количество сессий */
  total_sessions: number;
  /** Средняя длительность сессии */
  average_session_duration_seconds: number;
  /** Время кэширования */
  cached_at: string;
}
