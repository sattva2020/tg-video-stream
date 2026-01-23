/**
 * Adaptive Streaming Types
 * Spec: 009-adaptive-bitrate-streaming
 *
 * Типы для конфигурации адаптивного битрейта и мониторинга пропускной способности
 */

// ========== Enums ==========

/** Уровни качества потока */
export type QualityLevel = 'low' | 'medium' | 'high' | 'ultra';

/** Типы устройств для автоматической оптимизации */
export type DeviceType = 'mobile' | 'tablet' | 'desktop' | 'tv' | 'unknown';

/** Причина изменения качества */
export type QualityChangeReason = 'bandwidth' | 'device' | 'manual' | 'startup';

/** Метод измерения пропускной способности */
export type MeasurementMethod = 'http' | 'websocket' | 'webrtc';

// ========== Quality Profiles ==========

/** Профиль качества с настройками кодирования */
export interface QualityProfile {
  /** Разрешение в формате 'WIDTHxHEIGHT', например '1280x720' */
  resolution: string;
  /** Видеобитрейт в Kbps */
  video_bitrate_kbps: number;
  /** Аудиобитрейт в Kbps */
  audio_bitrate_kbps: number;
  /** Кадров в секунду */
  fps?: number;
  /** Видеокодек */
  codec?: string;
}

/** Правило для конкретного типа устройства */
export interface DeviceRule {
  /** Максимальное качество для этого устройства */
  max_quality: QualityLevel;
  /** Множитель пропускной способности (0.1-1.0) */
  bandwidth_multiplier: number;
  /** Предпочтительное разрешение */
  preferred_resolution?: string;
}

// ========== Bandwidth Detection ==========

/** Результат измерения пропускной способности */
export interface BandwidthMeasurement {
  /** Измеренная пропускная способность в Kbps */
  bandwidth_kbps: number;
  /** Задержка в миллисекундах */
  latency_ms?: number;
  /** Потеря пакетов (0-1) */
  packet_loss?: number;
  /** Время измерения */
  measured_at: string;
  /** Метод измерения: http, websocket, webrtc */
  measurement_method: MeasurementMethod;
  /** Уверенность в измерении (0-1) */
  confidence: number;
}

/** Статус пропускной способности сети */
export interface BandwidthStatus {
  /** Текущая пропускная способность в Kbps */
  current_bandwidth_kbps?: number;
  /** Сглаженная пропускная способность в Kbps */
  smoothed_bandwidth_kbps?: number;
  /** Рекомендуемое качество */
  recommended_quality?: QualityLevel;
  /** Текущее качество */
  current_quality?: QualityLevel;
  /** Тип устройства */
  device_type: DeviceType;
  /** Последнее измерение */
  last_measurement?: BandwidthMeasurement;
  /** Включена ли адаптация */
  adaptation_enabled: boolean;
  /** Секунд с последнего измерения */
  seconds_since_last_measurement?: number;
}

// ========== Adaptive Stream Config ==========

/** Базовая схема для конфигурации адаптивного стрима */
export interface AdaptiveStreamConfigBase {
  /** Включена ли адаптивная трансляция */
  enabled: boolean;
  /** Качество по умолчанию */
  default_quality: QualityLevel;
  /** Минимальное качество */
  min_quality: QualityLevel;
  /** Максимальное качество */
  max_quality: QualityLevel;

  // Bandwidth Thresholds (Kbps)
  /** Порог для low quality (Kbps) */
  bandwidth_threshold_low_kbps: number;
  /** Порог для medium quality (Kbps) */
  bandwidth_threshold_medium_kbps: number;
  /** Порог для high quality (Kbps) */
  bandwidth_threshold_high_kbps: number;
  /** Порог для ultra quality (Kbps) */
  bandwidth_threshold_ultra_kbps: number;

  // Adaptive Settings
  /** Интервал проверки пропускной способности (сек) */
  adaptation_interval_seconds: number;
  /** Коэффициент сглаживания (0-1) */
  bandwidth_smoothing_factor: number;
  /** Измерений для переключения качества */
  consecutive_measurements_required: number;

  // Device Rules
  /** Правила для устройств */
  device_rules?: Record<string, DeviceRule>;

  // Quality Profiles
  /** Пользовательские профили качества */
  quality_profiles?: Record<string, QualityProfile>;

  // Monitoring
  /** Включить мониторинг пропускной способности */
  enable_bandwidth_monitoring: boolean;
  /** Включить логирование изменений качества */
  enable_quality_logging: boolean;
}

/** Схема для создания конфигурации адаптивного стрима */
export interface AdaptiveStreamConfigCreate extends AdaptiveStreamConfigBase {
  /** ID потока (GUID) */
  stream_id: string;
}

/** Схема для обновления конфигурации адаптивного стрима */
export interface AdaptiveStreamConfigUpdate {
  /** Включена ли адаптивная трансляция */
  enabled?: boolean;
  /** Качество по умолчанию */
  default_quality?: QualityLevel;
  /** Минимальное качество */
  min_quality?: QualityLevel;
  /** Максимальное качество */
  max_quality?: QualityLevel;

  /** Порог для low quality (Kbps) */
  bandwidth_threshold_low_kbps?: number;
  /** Порог для medium quality (Kbps) */
  bandwidth_threshold_medium_kbps?: number;
  /** Порог для high quality (Kbps) */
  bandwidth_threshold_high_kbps?: number;
  /** Порог для ultra quality (Kbps) */
  bandwidth_threshold_ultra_kbps?: number;

  /** Интервал проверки пропускной способности (сек) */
  adaptation_interval_seconds?: number;
  /** Коэффициент сглаживания (0-1) */
  bandwidth_smoothing_factor?: number;
  /** Измерений для переключения качества */
  consecutive_measurements_required?: number;

  /** Правила для устройств */
  device_rules?: Record<string, DeviceRule>;
  /** Пользовательские профили качества */
  quality_profiles?: Record<string, QualityProfile>;

  /** Включить мониторинг пропускной способности */
  enable_bandwidth_monitoring?: boolean;
  /** Включить логирование изменений качества */
  enable_quality_logging?: boolean;
}

/** Схема ответа с конфигурацией адаптивного стрима */
export interface AdaptiveStreamConfigResponse extends AdaptiveStreamConfigBase {
  /** ID конфигурации */
  id: number;
  /** ID потока */
  stream_id: string;
  /** Статистика адаптивной трансляции */
  statistics?: Record<string, unknown>;
  /** Время создания */
  created_at: string;
  /** Время обновления */
  updated_at: string;
}

// ========== Quality Change Events ==========

/** Событие изменения качества потока */
export interface QualityChangeEvent {
  /** ID события */
  id: number;
  /** ID потока */
  stream_id: string;
  /** Предыдущее качество */
  previous_quality?: QualityLevel;
  /** Новое качество */
  new_quality: QualityLevel;
  /** Пропускная способность в Kbps */
  bandwidth_kbps?: number;
  /** Причина изменения: bandwidth, device, manual, startup */
  reason: QualityChangeReason;
  /** Тип устройства */
  device_type?: DeviceType;
  /** Время-trigger */
  triggered_at: string;
}

/** История изменений качества для потока */
export interface QualityChangeHistory {
  /** ID потока */
  stream_id: string;
  /** Название потока */
  stream_name?: string;
  /** Список событий */
  events: QualityChangeEvent[];
  /** Общее количество изменений */
  total_changes: number;
  /** Текущее качество */
  current_quality: QualityLevel;
  /** Начало периода */
  period_start?: string;
  /** Конец периода */
  period_end?: string;
}

// ========== Adaptive Streaming Status ==========

/** Полный статус адаптивного стрима для потока */
export interface AdaptiveStreamingStatus {
  /** ID потока */
  stream_id: string;
  /** Название потока */
  stream_name?: string;

  // Configuration
  /** Конфигурация адаптивного стрима */
  config?: AdaptiveStreamConfigResponse;

  // Current State
  /** Текущее качество */
  current_quality: QualityLevel;
  /** Текущая пропускная способность в Kbps */
  current_bandwidth_kbps?: number;
  /** Сглаженная пропускная способность в Kbps */
  smoothed_bandwidth_kbps?: number;
  /** Тип устройства */
  device_type: DeviceType;

  // Status Flags
  /** Включена ли адаптация */
  adaptive_enabled: boolean;
  /** Включен ли мониторинг */
  monitoring_enabled: boolean;
  /** Происходит ли адаптация */
  is_adapting: boolean;

  // Statistics
  /** Общее количество изменений качества */
  total_quality_changes: number;
  /** Последнее изменение качества */
  last_quality_change?: string;
  /** Последнее измерение пропускной способности */
  last_bandwidth_measurement?: string;

  // Recommended Actions
  /** Рекомендуемое качество */
  recommended_quality?: QualityLevel;
  /** Рекомендуемое действие */
  recommended_action?: string;

  /** Время обновления */
  updated_at: string;
}

// ========== Bandwidth Detection ==========

/** Запрос на измерение пропускной способности */
export interface BandwidthDetectionRequest {
  /** ID потока */
  stream_id: string;
  /** Таймаут измерения */
  timeout_seconds?: number;
  /** Метод: http, websocket, webrtc */
  measurement_method?: MeasurementMethod;
  /** Принудительное измерение (игнорировать кэш) */
  force_measurement?: boolean;
}

/** Результат измерения пропускной способности */
export interface BandwidthDetectionResponse {
  /** ID потока */
  stream_id: string;
  /** Измерение */
  measurement: BandwidthMeasurement;
  /** Рекомендуемое качество */
  recommended_quality: QualityLevel;
  /** Текущая конфигурация */
  current_config?: AdaptiveStreamConfigResponse;
  /** Тип устройства */
  device_type: DeviceType;
  /** Успешно */
  success: boolean;
  /** Сообщение об ошибке */
  error_message?: string;
}
