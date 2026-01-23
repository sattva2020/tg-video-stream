/**
 * Состояние формы правила алертов.
 * Используется wizard-ом и при редактировании.
 */
export interface AlertRuleFormState {
  // ========== Шаг 1: Основные ==========
  /** Название правила */
  name: string;
  /** Описание правила */
  description: string;
  /** Правило включено */
  enabled: boolean;
  /** Тип алерта (stream_failure, low_viewers, api_rate_limit, etc.) */
  alert_type: string;
  /** Уровень важности */
  severity: string;
  /** Категория (опционально) */
  category: string;

  // ========== Шаг 2: Условия ==========
  /** Условия срабатывания (гибкий JSON) */
  conditions: Record<string, unknown>;
  /** Cooldown между алертами (секунды) */
  cooldown_sec: number;
  /** Rate limit: количество */
  rate_limit_count: number;
  /** Rate limit: период (минуты) */
  rate_limit_minutes: number;

  // ========== Шаг 3: Уведомления ==========
  /** ID каналов уведомлений */
  channelIds: string[];
  /** Уведомлять о восстановлении */
  notify_on_recovery: boolean;
  /** Автоматически разрешать алерт */
  auto_resolve: boolean;
  /** Эскалация включена */
  escalation_enabled: boolean;
}

/**
 * Начальное состояние формы (пустое правило).
 */
export const emptyAlertRuleFormState: AlertRuleFormState = {
  name: '',
  description: '',
  enabled: true,
  alert_type: '',
  severity: 'warning',
  category: '',

  conditions: {},
  cooldown_sec: 300,
  rate_limit_count: 0,
  rate_limit_minutes: 0,

  channelIds: [],
  notify_on_recovery: true,
  auto_resolve: false,
  escalation_enabled: false,
};

/**
 * Пресеты для быстрого создания правил алертов.
 */
export interface AlertRulePreset {
  id: string;
  name: string;
  description: string;
  icon: string;
  state: Partial<AlertRuleFormState>;
}

export const ALERT_RULE_PRESETS: AlertRulePreset[] = [
  {
    id: 'stream-failure',
    name: 'Отказ стрима',
    description: 'Критические алерты при отказе стрима',
    icon: '📡',
    state: {
      name: 'Отказ стрима',
      alert_type: 'stream_failure',
      severity: 'critical',
      enabled: true,
      cooldown_sec: 300,
      notify_on_recovery: true,
      auto_resolve: true,
    },
  },
  {
    id: 'low-viewers',
    name: 'Падение зрителей',
    description: 'Предупреждение при низкой аудитории',
    icon: '📉',
    state: {
      name: 'Низкое количество зрителей',
      alert_type: 'low_viewers',
      severity: 'warning',
      enabled: true,
      cooldown_sec: 600,
      notify_on_recovery: true,
      auto_resolve: false,
    },
  },
  {
    id: 'api-rate-limit',
    name: 'API Rate Limit',
    description: 'Предупреждение о приближении к лимитам API',
    icon: '⚠️',
    state: {
      name: 'API Rate Limit Warning',
      alert_type: 'api_rate_limit',
      severity: 'warning',
      enabled: true,
      cooldown_sec: 900,
      notify_on_recovery: false,
      auto_resolve: false,
    },
  },
  {
    id: 'resource-alert',
    name: 'Ресурсы сервера',
    description: 'Алерты по использованию CPU/памяти/диска',
    icon: '💻',
    state: {
      name: 'Высокая нагрузка на сервер',
      alert_type: 'resource_usage',
      severity: 'warning',
      enabled: true,
      cooldown_sec: 600,
      notify_on_recovery: true,
      auto_resolve: true,
    },
  },
  {
    id: 'empty',
    name: 'Пустое правило',
    description: 'Настроить всё вручную',
    icon: '📝',
    state: {},
  },
];

/**
 * Типы алертов.
 */
export const ALERT_TYPES = [
  { value: 'stream_failure', label: 'Отказ стрима', description: 'Стрим остановился или недоступен' },
  { value: 'low_viewers', label: 'Низкие зрители', description: 'Количество зрителей упало ниже порога' },
  { value: 'api_rate_limit', label: 'API Rate Limit', description: 'Превышение лимитов API' },
  { value: 'resource_usage', label: 'Ресурсы', description: 'Высокое использование CPU/памяти/диска' },
  { value: 'disk_space', label: 'Дисковое пространство', description: 'Мало свободного места на диске' },
  { value: 'custom', label: 'Кастомный', description: 'Пользовательское условие' },
];

/**
 * Уровни важности.
 */
export const SEVERITY_LEVELS = [
  { value: 'info', label: 'Info', color: 'text-blue-500', description: 'Информационное сообщение' },
  { value: 'warning', label: 'Warning', color: 'text-yellow-500', description: 'Предупреждение' },
  { value: 'critical', label: 'Critical', color: 'text-red-500', description: 'Критическая проблема' },
];

/**
 * Шаги wizard-а.
 */
export type AlertWizardStep = 1 | 2 | 3;

export interface AlertWizardStepInfo {
  step: AlertWizardStep;
  title: string;
  description: string;
}

export const ALERT_WIZARD_STEPS: AlertWizardStepInfo[] = [
  { step: 1, title: 'Основные', description: 'Тип и важность' },
  { step: 2, title: 'Условия', description: 'Когда срабатывать' },
  { step: 3, title: 'Уведомления', description: 'Куда отправлять' },
];
