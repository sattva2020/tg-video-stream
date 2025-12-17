import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Filter } from 'lucide-react';
import { SeverityPicker, TagFilterBuilder, HostFilterBuilder, RateLimitConfig } from '../filters';
import type { RuleFormState } from './types';

interface StepFiltersProps {
  form: RuleFormState;
  onChange: (updates: Partial<RuleFormState>) => void;
  disabled?: boolean;
}

/**
 * Шаг 2: Настройка фильтров.
 * - Severity
 * - Теги
 * - Хосты
 * - Rate limiting (расширенные)
 */
export const StepFilters: React.FC<StepFiltersProps> = ({
  form,
  onChange,
  disabled = false,
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Подсчёт активных фильтров
  const activeFiltersCount = 
    (form.severityLevels.length > 0 ? 1 : 0) +
    (form.tagConditions.length > 0 ? 1 : 0) +
    (form.hostConditions.length > 0 ? 1 : 0);

  return (
    <div className="space-y-6">
      {/* Заголовок с счётчиком */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-[color:var(--color-accent)]" />
          <span className="font-medium">Фильтры событий</span>
        </div>
        {activeFiltersCount > 0 && (
          <span className="text-xs bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] px-2 py-1 rounded-full">
            {activeFiltersCount} активных
          </span>
        )}
      </div>

      <p className="text-sm text-[color:var(--color-text-secondary)]">
        Определите, какие события будут обрабатываться этим правилом. 
        Если фильтр не задан — правило применяется ко всем событиям.
      </p>

      {/* Severity Picker */}
      <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4">
        <SeverityPicker
          selected={form.severityLevels}
          onChange={(severityLevels) => onChange({ severityLevels })}
          disabled={disabled}
        />
      </div>

      {/* Tag Filter Builder */}
      <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4">
        <TagFilterBuilder
          conditions={form.tagConditions}
          onChange={(tagConditions) => onChange({ tagConditions })}
          disabled={disabled}
        />
      </div>

      {/* Host Filter Builder */}
      <div className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4">
        <HostFilterBuilder
          conditions={form.hostConditions}
          onChange={(hostConditions) => onChange({ hostConditions })}
          disabled={disabled}
        />
      </div>

      {/* Расширенные настройки */}
      <div className="border-t border-[color:var(--color-border)] pt-4">
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-[color:var(--color-accent)] hover:underline"
        >
          {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          {showAdvanced ? 'Скрыть расширенные настройки' : 'Показать расширенные настройки'}
        </button>

        {showAdvanced && (
          <div className="mt-4 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4">
            <RateLimitConfig
              maxMessages={form.maxMessages}
              windowSec={form.windowSec}
              dedupWindowSec={form.dedupWindowSec}
              onChange={({ maxMessages, windowSec, dedupWindowSec }) =>
                onChange({
                  maxMessages,
                  windowSec,
                  dedupWindowSec,
                })
              }
              disabled={disabled}
            />
          </div>
        )}
      </div>

      {/* Подсказка */}
      {activeFiltersCount === 0 && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4">
          <p className="text-sm text-yellow-300">
            💡 Совет: Без фильтров правило будет обрабатывать <strong>все</strong> события. 
            Рекомендуется указать хотя бы severity для ограничения потока уведомлений.
          </p>
        </div>
      )}
    </div>
  );
};

export default StepFilters;
