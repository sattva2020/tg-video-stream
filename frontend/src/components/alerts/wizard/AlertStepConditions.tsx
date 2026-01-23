import React from 'react';
import { Plus, Trash2, ChevronDown, ChevronUp, Sliders } from 'lucide-react';
import type { AlertRuleFormState } from './types';

interface AlertStepConditionsProps {
  form: AlertRuleFormState;
  onChange: (updates: Partial<AlertRuleFormState>) => void;
  disabled?: boolean;
}

/**
 * Условие для алерта.
 */
interface Condition {
  id: string;
  key: string;
  operator: string;
  value: string | number;
}

/**
 * Шаг 2: Настройка условий срабатывания.
 * - Условия (ключ/оператор/значение)
 * - Cooldown
 * - Rate limiting
 */
export const AlertStepConditions: React.FC<AlertStepConditionsProps> = ({
  form,
  onChange,
  disabled = false,
}) => {
  const [showAdvanced, setShowAdvanced] = React.useState(false);

  // Конвертируем conditions Record в Condition[] для редактирования
  const [conditions, setConditions] = React.useState<Condition[]>(() => {
    const entries = Object.entries(form.conditions || {});
    return entries.map(([key, value], idx) => ({
      id: `cond-${idx}`,
      key,
      operator: 'eq',
      value: String(value),
    }));
  });

  // Операторы сравнения
  const operators = [
    { value: 'eq', label: 'Равно' },
    { value: 'ne', label: 'Не равно' },
    { value: 'gt', label: 'Больше' },
    { value: 'lt', label: 'Меньше' },
    { value: 'gte', label: 'Больше или равно' },
    { value: 'lte', label: 'Меньше или равно' },
    { value: 'contains', label: 'Содержит' },
  ];

  // Добавить условие
  const addCondition = () => {
    const newCondition: Condition = {
      id: `cond-${Date.now()}`,
      key: '',
      operator: 'eq',
      value: '',
    };
    setConditions([...conditions, newCondition]);
  };

  // Удалить условие
  const removeCondition = (id: string) => {
    const updated = conditions.filter((c) => c.id !== id);
    setConditions(updated);
    updateConditionsRecord(updated);
  };

  // Обновить условие
  const updateCondition = (id: string, updates: Partial<Condition>) => {
    const updated = conditions.map((c) =>
      c.id === id ? { ...c, ...updates } : c
    );
    setConditions(updated);
    updateConditionsRecord(updated);
  };

  // Обновить conditions Record в форме
  const updateConditionsRecord = (conds: Condition[]) => {
    const record: Record<string, unknown> = {};
    conds.forEach((c) => {
      if (c.key && c.value !== '') {
        // Пробуем преобразовать в число
        const numValue = Number(c.value);
        record[c.key] = isNaN(numValue) ? c.value : numValue;
      }
    });
    onChange({ conditions: record });
  };

  return (
    <div className="space-y-6">
      {/* Заголовок */}
      <div className="flex items-center gap-2">
        <Sliders className="w-5 h-5 text-[color:var(--color-accent)]" />
        <span className="font-medium">Условия срабатывания</span>
        {conditions.length > 0 && (
          <span className="text-xs bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] px-2 py-1 rounded-full">
            {conditions.length} активных
          </span>
        )}
      </div>

      <p className="text-sm text-[color:var(--color-text-secondary)]">
        Определите условия, при которых алерт будет срабатывать.
        Условия зависят от типа алерта и проверяемых метрик.
      </p>

      {/* Список условий */}
      <div className="space-y-3">
        {conditions.map((condition, index) => (
          <div
            key={condition.id}
            className="rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-4"
          >
            <div className="flex items-start gap-3">
              <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Ключ */}
                <input
                  type="text"
                  value={condition.key}
                  onChange={(e) => updateCondition(condition.id, { key: e.target.value })}
                  disabled={disabled}
                  placeholder="metric_name"
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2 text-sm"
                />

                {/* Оператор */}
                <select
                  value={condition.operator}
                  onChange={(e) => updateCondition(condition.id, { operator: e.target.value })}
                  disabled={disabled}
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2 text-sm"
                >
                  {operators.map((op) => (
                    <option key={op.value} value={op.value}>
                      {op.label}
                    </option>
                  ))}
                </select>

                {/* Значение */}
                <input
                  type="text"
                  value={condition.value}
                  onChange={(e) => updateCondition(condition.id, { value: e.target.value })}
                  disabled={disabled}
                  placeholder="Значение"
                  className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-3 py-2 text-sm"
                />
              </div>

              {/* Удалить */}
              <button
                type="button"
                onClick={() => removeCondition(condition.id)}
                disabled={disabled}
                className="p-2 rounded hover:bg-white/5 text-red-400 disabled:opacity-50"
                aria-label="Удалить условие"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}

        {conditions.length === 0 && (
          <div className="rounded-lg border border-dashed border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-8 text-center">
            <p className="text-sm text-[color:var(--color-text-secondary)]">
              Нет условий. Добавьте условие или используйте настройки по умолчанию для типа алерта.
            </p>
          </div>
        )}
      </div>

      {/* Добавить условие */}
      <button
        type="button"
        onClick={addCondition}
        disabled={disabled}
        className="inline-flex items-center gap-2 rounded-lg border-2 border-dashed border-[color:var(--color-border)] px-4 py-2 text-sm hover:border-[color:var(--color-accent)] disabled:opacity-50"
      >
        <Plus className="w-4 h-4" />
        Добавить условие
      </button>

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
          <div className="mt-4 space-y-4">
            {/* Cooldown */}
            <div className="space-y-2">
              <label className="block text-sm font-medium">Cooldown (секунды)</label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min={0}
                  max={86400}
                  value={form.cooldown_sec}
                  onChange={(e) => onChange({ cooldown_sec: Number(e.target.value) })}
                  disabled={disabled}
                  className="w-32 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm"
                />
                <span className="text-sm text-[color:var(--color-text-secondary)]">
                  Минимальный интервал между алертами
                </span>
              </div>
            </div>

            {/* Rate Limit */}
            <div className="space-y-2">
              <label className="block text-sm font-medium">Rate Limiting</label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min={0}
                  value={form.rate_limit_count}
                  onChange={(e) => onChange({ rate_limit_count: Number(e.target.value) })}
                  disabled={disabled}
                  placeholder="0 = без лимита"
                  className="w-24 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm"
                />
                <span className="text-sm">раз в</span>
                <input
                  type="number"
                  min={1}
                  value={form.rate_limit_minutes || ''}
                  onChange={(e) => onChange({ rate_limit_minutes: Number(e.target.value) })}
                  disabled={disabled || form.rate_limit_count === 0}
                  className="w-20 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-3 py-2 text-sm disabled:opacity-50"
                />
                <span className="text-sm">минут</span>
              </div>
              <p className="text-xs text-[color:var(--color-text-secondary)]">
                Ограничение количества алертов за период времени
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Подсказка */}
      {conditions.length === 0 && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4">
          <p className="text-sm text-yellow-300">
            💡 Совет: Без условий алерт будет использовать настройки по умолчанию для выбранного типа.
            Рекомендуется указать хотя бы одно условие для точной настройки.
          </p>
        </div>
      )}
    </div>
  );
};

export default AlertStepConditions;
