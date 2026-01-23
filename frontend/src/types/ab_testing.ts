/**
 * A/B Testing types for admin dashboard
 * Feature: 016-a-b-testing-framework-for-content
 */

/** Статус A/B теста */
export type ABTestStatus = 'draft' | 'running' | 'paused' | 'completed' | 'stopped';

/** Тип метрики A/B теста */
export type ABTestMetricType = 'impressions' | 'clicks' | 'conversions' | 'watch_time_seconds' | 'peak_listeners' | 'avg_view_duration';

/** Базовые поля варианта A/B теста */
export interface ABTestVariantBase {
  /** Название варианта */
  name: string;
  /** Описание варианта */
  description?: string;
  /** Процент трафика (0-100) */
  traffic_allocation: number;
  /** Конфигурация варианта (playlist_id, schedule_settings, etc.) */
  configuration: Record<string, unknown>;
}

/** Создание варианта A/B теста */
export interface ABTestVariantCreate extends ABTestVariantBase {
  /** Порядок отображения */
  position: number;
}

/** Обновление варианта A/B теста */
export interface ABTestVariantUpdate {
  /** Название варианта */
  name?: string;
  /** Описание варианта */
  description?: string;
  /** Процент трафика (0-100) */
  traffic_allocation?: number;
  /** Конфигурация варианта */
  configuration?: Record<string, unknown>;
}

/** Вариант A/B теста с результатами */
export interface ABTestVariantResponse extends ABTestVariantBase {
  /** ID варианта */
  id: string;
  /** ID теста */
  test_id: string;
  /** Порядок отображения */
  position: number;
  /** Является ли победителем */
  is_winner: boolean;
  /** Конверсия (0.0 - 1.0) */
  conversion_rate?: number;
  /** Улучшение в % относительно baseline */
  improvement?: number;
  /** Время создания */
  created_at: string;
  /** Время обновления */
  updated_at?: string;
}

/** Базовые поля метрики A/B теста */
export interface ABTestMetricBase {
  /** Тип метрики */
  metric_type: ABTestMetricType;
  /** Значение метрики */
  metric_value: number;
}

/** Создание метрики A/B теста */
export interface ABTestMetricCreate extends ABTestMetricBase {
  /** ID варианта */
  variant_id: string;
  /** Дополнительные данные */
  metadata?: Record<string, unknown>;
}

/** Метрика A/B теста */
export interface ABTestMetricResponse extends ABTestMetricBase {
  /** ID метрики */
  id: number;
  /** ID варианта */
  variant_id: string;
  /** Время записи */
  recorded_at: string;
  /** Дополнительные данные */
  metadata?: Record<string, unknown>;
}

/** Базовые поля A/B теста */
export interface ABTestBase {
  /** Название теста */
  name: string;
  /** Описание теста */
  description?: string;
  /** Гипотеза теста */
  hypothesis?: string;
}

/** Создание A/B теста */
export interface ABTestCreate extends ABTestBase {
  /** ID канала */
  channel_id: string;
  /** Планируемая длительность в часах */
  planned_duration_hours?: number;
  /** Конфигурация распределения трафика */
  traffic_config?: Record<string, unknown>;
  /** Варианты теста (минимум 2) */
  variants: ABTestVariantCreate[];
}

/** Обновление A/B теста */
export interface ABTestUpdate {
  /** Название теста */
  name?: string;
  /** Описание теста */
  description?: string;
  /** Гипотеза теста */
  hypothesis?: string;
  /** Планируемая длительность в часах */
  planned_duration_hours?: number;
  /** Конфигурация распределения трафика */
  traffic_config?: Record<string, unknown>;
}

/** A/B тест с результатами */
export interface ABTestResponse extends ABTestBase {
  /** ID теста */
  id: string;
  /** ID канала */
  channel_id: string;
  /** Статус теста */
  status: ABTestStatus;
  /** Время запуска */
  start_time?: string;
  /** Время завершения */
  end_time?: string;
  /** Планируемая длительность в часах */
  planned_duration_hours?: number;
  /** Конфигурация распределения трафика */
  traffic_config?: Record<string, unknown>;
  /** ID варианта-победителя */
  winner_variant_id?: string;
  /** Уровень доверия (0-100) */
  confidence_level?: number;
  /** Статистически значимый результат */
  is_significant?: boolean;
  /** Время создания */
  created_at: string;
  /** Время обновления */
  updated_at?: string;
  /** ID создателя */
  created_by?: string;
  /** Варианты теста */
  variants: ABTestVariantResponse[];
}

/** Список A/B тестов (без вариантов) */
export interface ABTestListResponse {
  /** ID теста */
  id: string;
  /** ID канала */
  channel_id: string;
  /** Название теста */
  name: string;
  /** Статус теста */
  status: ABTestStatus;
  /** Время запуска */
  start_time?: string;
  /** Время завершения */
  end_time?: string;
  /** ID варианта-победителя */
  winner_variant_id?: string;
  /** Статистически значимый результат */
  is_significant?: boolean;
  /** Время создания */
  created_at: string;
  /** Количество вариантов */
  variant_count: number;
}

/** Коллекция A/B тестов */
export interface ABTestCollectionResponse {
  /** Список тестов */
  tests: ABTestListResponse[];
  /** Общее количество */
  total: number;
}

/** Статистика варианта для анализа */
export interface ABTestStatistics {
  /** ID варианта */
  variant_id: string;
  /** Название варианта */
  variant_name: string;
  /** Количество показов */
  impressions: number;
  /** Количество конверсий */
  conversions: number;
  /** Конверсия (0.0 - 1.0) */
  conversion_rate: number;
  /** Нижняя граница доверительного интервала */
  confidence_interval_lower?: number;
  /** Верхняя граница доверительного интервала */
  confidence_interval_upper?: number;
}

/** Результаты статистического анализа A/B теста */
export interface ABTestAnalysisResponse {
  /** ID теста */
  test_id: string;
  /** Название теста */
  test_name: string;
  /** Статус теста */
  status: ABTestStatus;
  /** Статистика по вариантам */
  variants: ABTestStatistics[];
  /** ID варианта-победителя */
  winner_variant_id?: string;
  /** Уровень доверия (0-100) */
  confidence_level: number;
  /** Статистически значимый результат */
  is_significant: boolean;
  /** P-value */
  p_value?: number;
  /** Рекомендованное действие */
  recommended_action?: string;
  /** Время анализа */
  analyzed_at: string;
}

/** Запрос на запуск A/B теста */
export interface ABTestStartRequest {
  /** ID теста */
  test_id: string;
}

/** Ответ на запуск A/B теста */
export interface ABTestStartResponse {
  /** ID теста */
  test_id: string;
  /** Новый статус */
  status: ABTestStatus;
  /** Время запуска */
  start_time: string;
}

/** Запрос на остановку A/B теста */
export interface ABTestStopRequest {
  /** ID теста */
  test_id: string;
  /** Автоматически выбрать победителя */
  select_winner?: boolean;
}

/** Ответ на остановку A/B теста */
export interface ABTestStopResponse {
  /** ID теста */
  test_id: string;
  /** Новый статус */
  status: ABTestStatus;
  /** Время остановки */
  end_time: string;
  /** ID выбранного победителя */
  winner_variant_id?: string;
  /** Уровень доверия результата */
  confidence_level?: number;
}
