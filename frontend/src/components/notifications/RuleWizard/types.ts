import type { SeverityLevel } from '../filters/SeverityPicker';
import type { TagCondition } from '../filters/TagFilterBuilder';
import type { HostCondition } from '../filters/HostFilterBuilder';

/**
 * Состояние формы правила уведомлений.
 * Используется wizard-ом и при редактировании.
 */
export interface RuleFormState {
  // ========== Шаг 1: Основные ==========
  /** Название правила */
  name: string;
  /** Описание правила */
  description: string;
  /** Правило включено */
  enabled: boolean;
  /** Приоритет (1 = высший) */
  priority: number;

  // ========== Шаг 2: Фильтры ==========
  /** Фильтр по уровням серьезности */
  severityLevels: SeverityLevel[];
  /** Фильтр по тегам */
  tagConditions: TagCondition[];
  /** Фильтр по хостам */
  hostConditions: HostCondition[];
  /** Лимит сообщений за окно */
  maxMessages: number;
  /** Окно лимита (секунды) */
  windowSec: number;
  /** Окно дедупликации (секунды) */
  dedupWindowSec: number;

  // ========== Шаг 3: Доставка ==========
  /** ID получателей */
  recipientIds: string[];
  /** ID каналов (порядок = приоритет, failover) */
  channelIds: string[];
  /** ID шаблона сообщения */
  templateId: string;
  /** Таймаут перед failover (секунды) */
  failoverTimeoutSec: number;
}

/**
 * Начальное состояние формы (пустое правило).
 */
export const emptyRuleFormState: RuleFormState = {
  name: '',
  description: '',
  enabled: true,
  priority: 100,

  severityLevels: [],
  tagConditions: [],
  hostConditions: [],
  maxMessages: 0,
  windowSec: 60,
  dedupWindowSec: 0,

  recipientIds: [],
  channelIds: [],
  templateId: '',
  failoverTimeoutSec: 30,
};

/**
 * Пресеты для быстрого создания правил.
 */
export interface RulePreset {
  id: string;
  name: string;
  description: string;
  icon: string;
  state: Partial<RuleFormState>;
}

export const RULE_PRESETS: RulePreset[] = [
  {
    id: 'critical-telegram',
    name: 'Критические → Telegram',
    description: 'Только critical события в Telegram',
    icon: '🚨',
    state: {
      name: 'Критические уведомления',
      enabled: true,
      severityLevels: ['critical'],
      maxMessages: 0,
    },
  },
  {
    id: 'all-email',
    name: 'Все → Email',
    description: 'Все события дублируются на email',
    icon: '📧',
    state: {
      name: 'Email дайджест',
      enabled: true,
      severityLevels: ['info', 'warning', 'critical', 'ok'],
      maxMessages: 100,
      windowSec: 3600,
    },
  },
  {
    id: 'prod-only',
    name: 'Только production',
    description: 'События только с production хостов',
    icon: '🏭',
    state: {
      name: 'Production мониторинг',
      enabled: true,
      hostConditions: [
        { id: '1', type: 'include', pattern: 'prod-*', matchType: 'wildcard' },
      ],
    },
  },
  {
    id: 'empty',
    name: 'Пустое правило',
    description: 'Начать с чистого листа',
    icon: '📝',
    state: {},
  },
];

/**
 * Шаги wizard-а.
 */
export type WizardStep = 1 | 2 | 3;

export interface WizardStepInfo {
  step: WizardStep;
  title: string;
  description: string;
}

export const WIZARD_STEPS: WizardStepInfo[] = [
  { step: 1, title: 'Основные', description: 'Название и настройки' },
  { step: 2, title: 'Фильтры', description: 'Когда отправлять' },
  { step: 3, title: 'Доставка', description: 'Кому и как' },
];
