import React, { useState } from 'react';
import { Plus, Trash2, Tag } from 'lucide-react';

export interface TagCondition {
  id: string;
  key: string;
  operator: 'equals' | 'contains' | 'regex' | 'not_equals';
  value: string;
}

interface TagFilterBuilderProps {
  /** Массив условий фильтра */
  conditions: TagCondition[];
  /** Callback при изменении условий */
  onChange: (conditions: TagCondition[]) => void;
  /** Отключить редактирование */
  disabled?: boolean;
}

const operatorLabels: Record<TagCondition['operator'], string> = {
  equals: 'равно',
  contains: 'содержит',
  regex: 'regex',
  not_equals: 'не равно',
};

const generateId = () => Math.random().toString(36).substring(2, 9);

/**
 * Визуальный builder для фильтрации по тегам.
 * Заменяет JSON-поле на интуитивный интерфейс.
 */
export const TagFilterBuilder: React.FC<TagFilterBuilderProps> = ({
  conditions,
  onChange,
  disabled = false,
}) => {
  const [newKey, setNewKey] = useState('');
  const [newOperator, setNewOperator] = useState<TagCondition['operator']>('equals');
  const [newValue, setNewValue] = useState('');

  const addCondition = () => {
    if (!newKey.trim() || !newValue.trim()) return;
    
    const condition: TagCondition = {
      id: generateId(),
      key: newKey.trim(),
      operator: newOperator,
      value: newValue.trim(),
    };
    
    onChange([...conditions, condition]);
    setNewKey('');
    setNewValue('');
    setNewOperator('equals');
  };

  const removeCondition = (id: string) => {
    onChange(conditions.filter((c) => c.id !== id));
  };

  const updateCondition = (id: string, updates: Partial<TagCondition>) => {
    onChange(
      conditions.map((c) => (c.id === id ? { ...c, ...updates } : c))
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Tag className="w-4 h-4 text-[color:var(--color-accent)]" />
          <span className="text-sm font-medium">Фильтр по тегам</span>
        </div>
        <span className="text-xs text-[color:var(--color-text-secondary)]">
          {conditions.length} условий
        </span>
      </div>

      {/* Существующие условия */}
      {conditions.length > 0 && (
        <div className="space-y-2">
          {conditions.map((condition) => (
            <div
              key={condition.id}
              className="flex items-center gap-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] p-2"
            >
              <input
                type="text"
                value={condition.key}
                onChange={(e) => updateCondition(condition.id, { key: e.target.value })}
                disabled={disabled}
                placeholder="Тег"
                className="flex-1 min-w-[80px] rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm"
              />
              <select
                value={condition.operator}
                onChange={(e) => updateCondition(condition.id, { operator: e.target.value as TagCondition['operator'] })}
                disabled={disabled}
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm"
              >
                {Object.entries(operatorLabels).map(([op, label]) => (
                  <option key={op} value={op}>{label}</option>
                ))}
              </select>
              <input
                type="text"
                value={condition.value}
                onChange={(e) => updateCondition(condition.id, { value: e.target.value })}
                disabled={disabled}
                placeholder="Значение"
                className="flex-1 min-w-[100px] rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm"
              />
              <button
                type="button"
                onClick={() => removeCondition(condition.id)}
                disabled={disabled}
                className="p-1 rounded hover:bg-white/5 text-red-400 disabled:opacity-50"
                aria-label="Удалить условие"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Добавление нового условия */}
      <div className="flex items-center gap-2 rounded-lg border border-dashed border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)]/50 p-2">
        <input
          type="text"
          value={newKey}
          onChange={(e) => setNewKey(e.target.value)}
          disabled={disabled}
          placeholder="Тег (напр. service)"
          className="flex-1 min-w-[80px] rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm"
        />
        <select
          value={newOperator}
          onChange={(e) => setNewOperator(e.target.value as TagCondition['operator'])}
          disabled={disabled}
          className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm"
        >
          {Object.entries(operatorLabels).map(([op, label]) => (
            <option key={op} value={op}>{label}</option>
          ))}
        </select>
        <input
          type="text"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          disabled={disabled}
          placeholder="Значение (напр. billing)"
          className="flex-1 min-w-[100px] rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm"
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              addCondition();
            }
          }}
        />
        <button
          type="button"
          onClick={addCondition}
          disabled={disabled || !newKey.trim() || !newValue.trim()}
          className="inline-flex items-center gap-1 rounded-lg bg-[color:var(--color-accent)] px-2 py-1 text-sm text-white hover:opacity-90 disabled:opacity-50"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {conditions.length === 0 && (
        <p className="text-xs text-[color:var(--color-text-secondary)]">
          Нет условий — правило будет применяться ко всем тегам
        </p>
      )}
    </div>
  );
};

/**
 * Конвертирует JSON-фильтр тегов в массив условий.
 */
export const parseTagFilter = (filter: Record<string, unknown> | null | undefined): TagCondition[] => {
  if (!filter || typeof filter !== 'object') return [];
  
  const conditions: TagCondition[] = [];
  
  // Формат: { "service": ["billing", "api"], "env": ["prod"] }
  for (const [key, value] of Object.entries(filter)) {
    if (Array.isArray(value)) {
      value.forEach((v) => {
        if (typeof v === 'string') {
          conditions.push({
            id: generateId(),
            key,
            operator: 'equals',
            value: v,
          });
        }
      });
    } else if (typeof value === 'string') {
      conditions.push({
        id: generateId(),
        key,
        operator: 'equals',
        value,
      });
    }
  }
  
  return conditions;
};

/**
 * Конвертирует массив условий в JSON-фильтр тегов.
 */
export const toTagFilter = (conditions: TagCondition[]): Record<string, unknown> | undefined => {
  if (conditions.length === 0) return undefined;
  
  const filter: Record<string, string[]> = {};
  
  conditions.forEach((c) => {
    if (!filter[c.key]) {
      filter[c.key] = [];
    }
    // Для простоты пока поддерживаем только equals
    if (c.operator === 'equals') {
      filter[c.key].push(c.value);
    }
  });
  
  return Object.keys(filter).length > 0 ? filter : undefined;
};

export default TagFilterBuilder;
