/**
 * Типы для системы сбора логов и инцидентов
 */

// Уровни логов
export type LogLevel = 'error' | 'warn' | 'info' | 'debug';

// Типы логов
export type LogType = 'console' | 'network' | 'action' | 'performance';

// Лог консоли
export interface ConsoleLog {
  type: 'console';
  level: LogLevel;
  message: string;
  stack?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// Лог сетевого запроса
export interface NetworkLog {
  type: 'network';
  url: string;
  method: string;
  statusCode?: number;
  responseTimeMs?: number;
  error?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// Лог действия пользователя
export interface ActionLog {
  type: 'action';
  action: string;
  element?: string;
  value?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// Лог производительности
export interface PerformanceLog {
  type: 'performance';
  metric: string;
  value: number;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

// Объединённый тип лога
export type LogEntry = ConsoleLog | NetworkLog | ActionLog | PerformanceLog;

// Информация о браузере
export interface BrowserInfo {
  name: string;
  version: string;
  os: string;
  platform: string;
  userAgent: string;
  language: string;
  screenResolution: string;
  viewportSize: string;
  colorDepth: number;
  timezone: string;
}

// Статусы инцидента
export type IncidentStatus = 
  | 'new' 
  | 'in_progress' 
  | 'waiting_user' 
  | 'resolved' 
  | 'closed' 
  | 'duplicate';

// Приоритеты инцидента
export type IncidentPriority = 'low' | 'medium' | 'high' | 'critical';

// Категории инцидента
export type IncidentCategory = 
  | 'bug' 
  | 'feature' 
  | 'question' 
  | 'performance' 
  | 'security' 
  | 'ui_ux' 
  | 'other';

// Данные для создания инцидента
export interface CreateIncidentData {
  title: string;
  description: string;
  logs: LogEntry[];
  browserInfo: BrowserInfo;
  pageUrl: string;
  screenshot?: string; // Base64
  tags?: string[];
}

// Ответ API создания инцидента
export interface CreateIncidentResponse {
  id: string;
  title: string;
  status: IncidentStatus;
  priority: IncidentPriority;
  category?: IncidentCategory;
  aiSuggestedSolution?: string;
  similarIncidents?: SimilarIncident[];
  createdAt: string;
}

// Похожий инцидент
export interface SimilarIncident {
  id: string;
  title: string;
  status: IncidentStatus;
  similarity: number; // 0.0 - 1.0
  solution?: string;
}

// Комментарий к инциденту
export interface IncidentComment {
  id: string;
  incidentId: string;
  userId?: string;
  userName?: string;
  content: string;
  isInternal: boolean;
  isAiGenerated: boolean;
  attachments: Attachment[];
  createdAt: string;
}

// Вложение
export interface Attachment {
  filename: string;
  url: string;
  mimeType: string;
  size: number;
}

// Полная модель инцидента
export interface Incident {
  id: string;
  userId?: string;
  title: string;
  description: string;
  status: IncidentStatus;
  priority: IncidentPriority;
  category?: IncidentCategory;
  browserInfo?: BrowserInfo;
  pageUrl?: string;
  aiAnalysis?: Record<string, unknown>;
  aiSuggestedSolution?: string;
  aiConfidence?: number;
  similarIncidentId?: string;
  tags: string[];
  assignedToId?: string;
  assignedToName?: string;
  createdAt: string;
  updatedAt?: string;
  resolvedAt?: string;
  comments: IncidentComment[];
  logsCount: number;
}

// Настройки коллектора логов
export interface LogCollectorConfig {
  maxLogs: number;           // Максимальное количество хранимых логов
  captureConsole: boolean;   // Перехватывать console.log/error/warn
  captureNetwork: boolean;   // Перехватывать fetch/XHR
  captureActions: boolean;   // Отслеживать клики и ввод
  capturePerformance: boolean; // Метрики производительности
  ignoredUrls: string[];     // URL-паттерны для игнорирования (например, аналитика)
  sensitiveKeys: string[];   // Ключи для маскировки (пароли, токены)
}

// Контекст коллектора
export interface LogCollectorState {
  logs: LogEntry[];
  browserInfo: BrowserInfo;
  isCollecting: boolean;
  lastError?: LogEntry;
}
