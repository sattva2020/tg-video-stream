import React from 'react';
import { Sparkles, AlertCircle, AlertTriangle, Info } from 'lucide-react';
import type { AlertRuleFormState } from './types';
import { ALERT_RULE_PRESETS, ALERT_TYPES, SEVERITY_LEVELS } from './types';

interface AlertStepBasicProps {
  form: AlertRuleFormState;
  onChange: (updates: Partial<AlertRuleFormState>) => void;
  disabled?: boolean;
}

/**
 * Шаг 1: Основные настройки правила алерта.
 * - Название и описание
 * - Выбор пресета
 * - Тип алерта
 * - Уровень важности
 * - Статус активности
 */
export const AlertStepBasic: React.FC<AlertStepBasicProps> = ({
  form,
  onChange,
  disabled = false,
}) => {
  const [selectedPreset, setSelectedPreset] = React.useState<string | null>(null);

  const applyPreset = (presetId: string) => {
    const preset = ALERT_RULE_PRESETS.find((p) => p.id === presetId);
    if (preset) {
      setSelectedPreset(presetId);
      onChange(preset.state);
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return <AlertCircle className="w-4 h-4" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4" />;
      case 'info':
        return <Info className="w-4 h-4" />;
      default:
        return <AlertCircle className="w-4 h-4" />;
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
          placeholder="Например: Критические отказы стрима"
          className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-base focus:border-[color:var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]/20"
          autoFocus
        />
        <p className="text-xs text-[color:var(--color-text-secondary)]">
          Понятное название поможет быстро найти правило в списке
        </p>
      </div>

      {/* Описание */}
      <div className="space-y-2">
        <label className="block text-sm font-medium">Описание</label>
        <textarea
          value={form.description}
          onChange={(e) => onChange({ description: e.target.value })}
          disabled={disabled}
          placeholder="Дополнительная информация о правиле..."
          rows={3}
          className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-base focus:border-[color:var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]/20 resize-none"
        />
      </div>

      {/* Пресеты */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-[color:var(--color-accent)]" />
          <span className="text-sm font-medium">Быстрый старт</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {ALERT_RULE_PRESETS.map((preset) => (
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
              <div className="text-base font-medium mb-1">
                {preset.icon} {preset.name}
              </div>
              <div className="text-xs text-[color:var(--color-text-secondary)]">
                {preset.description}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Тип алерта */}
      <div className="space-y-2">
        <label className="block text-sm font-medium">
          Тип алерта <span className="text-red-400">*</span>
        </label>
        <select
          value={form.alert_type}
          onChange={(e) => onChange({ alert_type: e.target.value })}
          disabled={disabled}
          className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-base focus:border-[color:var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]/20"
        >
          <option value="">Выберите тип алерта...</option>
          {ALERT_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label} - {type.description}
            </option>
          ))}
        </select>
      </div>

      {/* Уровень важности */}
      <div className="space-y-2">
        <label className="block text-sm font-medium">
          Уровень важности <span className="text-red-400">*</span>
        </label>
        <div className="grid grid-cols-3 gap-3">
          {SEVERITY_LEVELS.map((level) => (
            <button
              key={level.value}
              type="button"
              onClick={() => onChange({ severity: level.value })}
              disabled={disabled}
              className={`
                flex items-center justify-center gap-2 rounded-lg border-2 px-4 py-3 transition-all duration-150
                ${form.severity === level.value
                  ? 'border-[color:var(--color-accent)] bg-[color:var(--color-accent)]/10'
                  : 'border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] hover:border-[color:var(--color-accent)]/50'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              <span className={level.color}>{getSeverityIcon(level.value)}</span>
              <span className="font-medium">{level.label}</span>
            </button>
          ))}
        </div>
        <p className="text-xs text-[color:var(--color-text-secondary)]">
          {SEVERITY_LEVELS.find(l => l.value === form.severity)?.description}
        </p>
      </div>

      {/* Категория */}
      <div className="space-y-2">
        <label className="block text-sm font-medium">Категория (опционально)</label>
        <input
          type="text"
          value={form.category}
          onChange={(e) => onChange({ category: e.target.value })}
          disabled={disabled}
          placeholder="Например: media, streams, system"
          className="w-full rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-4 py-3 text-sm focus:border-[color:var(--color-accent)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]/20"
        />
        <p className="text-xs text-[color:var(--color-text-secondary)]">
          Категория для группировки правил
        </p>
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

export default AlertStepBasic;
