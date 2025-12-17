import React from 'react';
import { Sparkles } from 'lucide-react';
import type { RuleFormState } from './types';

interface StepBasicProps {
  form: RuleFormState;
  onChange: (updates: Partial<RuleFormState>) => void;
  disabled?: boolean;
}

/** Пресеты правил для быстрого старта */
const RULE_PRESETS = [
  {
    id: 'critical-telegram',
    name: '🔴 Критические → Telegram',
    description: 'Только critical события отправляются в Telegram',
    apply: (): Partial<RuleFormState> => ({
      name: 'Критические алерты',
      severityLevels: ['critical'],
      tagConditions: [],
      hostConditions: [],
      rateLimitMessages: 0,
      dedupWindowSec: 300,
    }),
  },
  {
    id: 'all-email',
    name: '📧 Все проблемы → Email',
    description: 'Critical и Warning отправляются на Email',
    apply: (): Partial<RuleFormState> => ({
      name: 'Все проблемы на Email',
      severityLevels: ['critical', 'warning'],
      tagConditions: [],
      hostConditions: [],
      rateLimitMessages: 10,
      rateLimitWindowSec: 60,
      dedupWindowSec: 600,
    }),
  },
  {
    id: 'prod-only',
    name: '🏭 Только production',
    description: 'События только с тегом env=production',
    apply: (): Partial<RuleFormState> => ({
      name: 'Production алерты',
      severityLevels: ['critical', 'warning'],
      tagConditions: [
        { id: 'preset-1', key: 'env', operator: 'equals', value: 'production' },
      ],
      hostConditions: [],
    }),
  },
  {
    id: 'empty',
    name: '📝 Пустое правило',
    description: 'Настроить всё вручную',
    apply: (): Partial<RuleFormState> => ({
      name: '',
      severityLevels: [],
      tagConditions: [],
      hostConditions: [],
    }),
  },
];

/**
 * Шаг 1: Основные настройки правила.
 * - Название
 * - Выбор пресета
 * - Активность правила
 */
export const StepBasic: React.FC<StepBasicProps> = ({
  form,
  onChange,
  disabled = false,
}) => {
  const [selectedPreset, setSelectedPreset] = React.useState<string | null>(null);

  const applyPreset = (presetId: string) => {
    const preset = RULE_PRESETS.find((p) => p.id === presetId);
    if (preset) {
      setSelectedPreset(presetId);
      onChange(preset.apply());
    }
  };

  return (
    <div className="space-y-6">
      {/* Название правила */}
      <div className="space-y-2">
        <label className="block text-sm font-medium">
          Название правила <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={form.name}
          onChange={(e) => onChange({ name: e.target.value })}
          disabled={disabled}
          placeholder="Например: Критические алерты на Telegram"
          className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-base focus:border-[color:var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]/20"
          autoFocus
        />
        <p className="text-xs text-[color:var(--color-text-secondary)]">
          Понятное название поможет быстро найти правило в списке
        </p>
      </div>

      {/* Пресеты */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[color:var(--color-accent)]" />
          <span className="text-sm font-medium">Быстрый старт</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {RULE_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => applyPreset(preset.id)}
              disabled={disabled}
              className={`
                text-left rounded-lg border-2 p-4 transition-all duration-150
                ${selectedPreset === preset.id
                  ? 'border-[color:var(--color-accent)] bg-[color:var(--color-accent)]/10'
                  : 'border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] hover:border-[color:var(--color-accent)]/50'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              <div className="text-base font-medium mb-1">{preset.name}</div>
              <div className="text-xs text-[color:var(--color-text-secondary)]">
                {preset.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Статус активности */}
      <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => onChange({ enabled: e.target.checked })}
            disabled={disabled}
            className="w-5 h-5 rounded border-[color:var(--color-border)] text-[color:var(--color-accent)] focus:ring-[color:var(--color-accent)]"
          />
          <div>
            <span className="font-medium">Правило активно</span>
            <p className="text-xs text-[color:var(--color-text-secondary)] mt-0.5">
              Неактивные правила не будут обрабатывать события
            </p>
          </div>
        </label>
      </div>
    </div>
  );
};

export default StepBasic;
