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
