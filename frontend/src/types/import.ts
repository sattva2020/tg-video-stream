/**
 * Import types for content import & migration tools
 * Feature: 011-content-import-migration-tools
 */

/** Платформа для импорта контента */
export type ImportPlatform = 'youtube' | 'vimeo' | 'local';

/** Статус задания импорта */
export type ImportStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled' | 'paused';

/** Опции импорта */
export interface ImportOptions {
  /** Искать дубликаты перед импортом */
  deduplicate?: boolean;
  /** Качество видео для Vimeo (best, high, medium, low) */
  quality?: 'best' | 'high' | 'medium' | 'low';
  /** Загружать метаданные */
  fetch_metadata?: boolean;
  /** Рекурсивный扫描 для локальных файлов */
  recursive?: boolean;
}

/** Запрос на создание задания импорта */
export interface ImportCreateRequest {
  /** Платформа для импорта */
  platform: ImportPlatform;
  /** URL источника для YouTube или Vimeo */
  source_url?: string;
  /** Локальный путь к файлам или папке */
  source_path?: string;
  /** ID канала для импорта (опционально) */
  channel_id?: string;
  /** Опции импорта */
  options?: ImportOptions;
}

/** Ответ с информацией о задании импорта */
export interface ImportJob {
  /** ID задания */
  id: string;
  /** ID пользователя */
  user_id: string;
  /** ID канала */
  channel_id?: string;
  /** Платформа импорта */
  platform: ImportPlatform;
  /** URL источника */
  source_url?: string;
  /** Локальный путь */
  source_path?: string;
  /** Статус задания */
  status: ImportStatus;
  /** Общее количество элементов */
  total_items?: number;
  /** Обработано элементов */
  processed_items: number;
  /** Успешно импортировано */
  successful_items: number;
  /** Не удалось импортировать */
  failed_items: number;
  /** Пропущено (дубликаты) */
  skipped_items: number;
  /** Процент выполнения (0-100) */
  progress_percentage: number;
  /** Сообщение об ошибке */
  error_message?: string;
  /** Детали ошибки */
  error_details?: Record<string, unknown>;
  /** Опции импорта */
  options: Record<string, unknown>;
  /** Метаданные */
  metadata: Record<string, unknown>;
  /** Результаты импорта */
  results: Record<string, unknown>;
  /** Дата создания */
  created_at: string;
  /** Дата начала */
  started_at?: string;
  /** Дата завершения */
  completed_at?: string;
  /** Дата обновления */
  updated_at?: string;
}

/** Ответ со списком заданий импорта */
export interface ImportJobListResponse {
  /** Список заданий */
  items: ImportJob[];
  /** Общее количество */
  total: number;
  /** Текущая страница */
  page: number;
  /** Размер страницы */
  page_size: number;
}

/** Запрос на обновление задания импорта */
export interface ImportJobUpdateRequest {
  /** Новый статус (paused, in_progress, cancelled) */
  status: ImportStatus;
}

/** Сводка результатов импорта */
export interface ImportSummary {
  /** ID задания */
  job_id: string;
  /** Платформа */
  platform: ImportPlatform;
  /** Статус */
  status: ImportStatus;
  /** Общее количество элементов */
  total_items: number;
  /** Количество импортированных */
  imported_count: number;
  /** Количество дубликатов */
  duplicate_count: number;
  /** Количество неудачных */
  failed_count: number;
  /** Длительность в секундах */
  duration_seconds?: number;
  /** Список ошибок */
  errors: string[];
}

/** Элемент прогресса импорта */
export interface ImportProgressUpdate {
  /** ID задания */
  job_id: string;
  /** Обработано элементов */
  processed_items: number;
  /** Успешно импортировано */
  successful_items?: number;
  /** Не удалось импортировать */
  failed_items?: number;
  /** Пропущено (дубликаты) */
  skipped_items?: number;
  /** Сообщение об ошибке */
  error_message?: string;
  /** Процент выполнения */
  progress_percentage: number;
  /** Текущий статус */
  status: ImportStatus;
}

/** Ошибка валидации при импорте */
export interface ImportValidationError {
  /** Поле с ошибкой */
  field: string;
  /** Сообщение об ошибке */
  message: string;
  /** Код ошибки */
  code: string;
}

/** Результат импорта элемента */
export interface ImportItemResult {
  /** ID элемента */
  id: string;
  /** Название */
  title: string;
  /** Успешно импортирован */
  success: boolean;
  /** Причина пропуска/ошибки */
  reason?: string;
  /** Дубликат */
  is_duplicate?: boolean;
}
