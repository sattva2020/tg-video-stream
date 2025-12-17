import React, { useState } from 'react';
import { Plus, Trash2, Server } from 'lucide-react';

export interface HostCondition {
  id: string;
  type: 'include' | 'exclude';
  pattern: string;
  matchType: 'exact' | 'wildcard' | 'regex';
}

interface HostFilterBuilderProps {
  /** Массив условий фильтра */
  conditions: HostCondition[];
  /** Callback при изменении условий */
  onChange: (conditions: HostCondition[]) => void;
  /** Отключить редактирование */
  disabled?: boolean;
}

const typeLabels: Record<HostCondition['type'], string> = {
  include: 'Включить',
  exclude: 'Исключить',
};

const matchTypeLabels: Record<HostCondition['matchType'], string> = {
  exact: 'точное совпадение',
  wildcard: 'паттерн (*)',
  regex: 'regex',
};

const generateId = () => Math.random().toString(36).substring(2, 9);

/**
 * Визуальный builder для фильтрации по хостам.
 * Заменяет JSON-поле на интуитивный интерфейс.
 */
export const HostFilterBuilder: React.FC<HostFilterBuilderProps> = ({
  conditions,
  onChange,
  disabled = false,
}) => {
  const [newType, setNewType] = useState<HostCondition['type']>('include');
  const [newMatchType, setNewMatchType] = useState<HostCondition['matchType']>('wildcard');
  const [newPattern, setNewPattern] = useState('');

  const addCondition = () => {
    if (!newPattern.trim()) return;
    
    const condition: HostCondition = {
      id: generateId(),
      type: newType,
      pattern: newPattern.trim(),
      matchType: newMatchType,
    };
    
    onChange([...conditions, condition]);
    setNewPattern('');
  };

  const removeCondition = (id: string) => {
    onChange(conditions.filter((c) => c.id !== id));
  };

  const updateCondition = (id: string, updates: Partial<HostCondition>) => {
    onChange(
      conditions.map((c) => (c.id === id ? { ...c, ...updates } : c))
    );
  };

  const includeConditions = conditions.filter((c) => c.type === 'include');
  const excludeConditions = conditions.filter((c) => c.type === 'exclude');

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-[color:var(--color-accent)]" />
          <span className="text-sm font-medium">Фильтр по хостам</span>
        </div>
        <span className="text-xs text-[color:var(--color-text-secondary)]">
          {includeConditions.length} включено, {excludeConditions.length} исключено
        </span>
      </div>

      {/* Существующие условия */}
      {conditions.length > 0 && (
        <div className="space-y-2">
          {conditions.map((condition) => (
            <div
              key={condition.id}
              className={`flex items-center gap-2 rounded-lg border p-2 ${
                condition.type === 'include'
                  ? 'border-green-500/30 bg-green-500/10'
                  : 'border-red-500/30 bg-red-500/10'
              }`}
            >
              <select
                value={condition.type}
                onChange={(e) => updateCondition(condition.id, { type: e.target.value as HostCondition['type'] })}
                disabled={disabled}
                className={`rounded-md border px-2 py-1 text-sm font-medium ${
                  condition.type === 'include'
                    ? 'border-green-500/50 bg-green-500/20 text-green-400'
                    : 'border-red-500/50 bg-red-500/20 text-red-400'
                }`}
              >
                {Object.entries(typeLabels).map(([type, label]) => (
                  <option key={type} value={type}>{label}</option>
                ))}
              </select>
              <select
                value={condition.matchType}
                onChange={(e) => updateCondition(condition.id, { matchType: e.target.value as HostCondition['matchType'] })}
                disabled={disabled}
                className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm"
              >
                {Object.entries(matchTypeLabels).map(([type, label]) => (
                  <option key={type} value={type}>{label}</option>
                ))}
              </select>
              <input
                type="text"
                value={condition.pattern}
                onChange={(e) => updateCondition(condition.id, { pattern: e.target.value })}
                disabled={disabled}
                placeholder="web-*"
                className="flex-1 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm font-mono"
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
        <select
          value={newType}
          onChange={(e) => setNewType(e.target.value as HostCondition['type'])}
          disabled={disabled}
          className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm"
        >
          {Object.entries(typeLabels).map(([type, label]) => (
            <option key={type} value={type}>{label}</option>
          ))}
        </select>
        <select
          value={newMatchType}
          onChange={(e) => setNewMatchType(e.target.value as HostCondition['matchType'])}
          disabled={disabled}
          className="rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm"
        >
          {Object.entries(matchTypeLabels).map(([type, label]) => (
            <option key={type} value={type}>{label}</option>
          ))}
        </select>
        <input
          type="text"
          value={newPattern}
          onChange={(e) => setNewPattern(e.target.value)}
          disabled={disabled}
          placeholder="Паттерн хоста (напр. web-*, prod-db-01)"
          className="flex-1 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)] px-2 py-1 text-sm font-mono"
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
          disabled={disabled || !newPattern.trim()}
          className="inline-flex items-center gap-1 rounded-lg bg-[color:var(--color-accent)] px-2 py-1 text-sm text-white hover:opacity-90 disabled:opacity-50"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {conditions.length === 0 && (
        <p className="text-xs text-[color:var(--color-text-secondary)]">
          Нет условий — правило будет применяться ко всем хостам
        </p>
      )}

      {/* Подсказка */}
      <div className="text-xs text-[color:var(--color-text-secondary)] space-y-1">
        <p>💡 Примеры паттернов:</p>
        <ul className="list-disc list-inside pl-2 space-y-0.5">
          <li><code className="bg-[color:var(--color-surface-muted)] px-1 rounded">web-*</code> — все хосты, начинающиеся с web-</li>
          <li><code className="bg-[color:var(--color-surface-muted)] px-1 rounded">*-prod-*</code> — все хосты с -prod- в имени</li>
          <li><code className="bg-[color:var(--color-surface-muted)] px-1 rounded">db-0[1-3]</code> — db-01, db-02, db-03 (regex)</li>
        </ul>
      </div>
    </div>
  );
};

/**
 * Конвертирует JSON-фильтр хостов в массив условий.
 */
export const parseHostFilter = (filter: Record<string, unknown> | null | undefined): HostCondition[] => {
  if (!filter || typeof filter !== 'object') return [];
  
  const conditions: HostCondition[] = [];
  
  // Формат: { "include": ["web-*"], "exclude": ["dev-*"] }
  const include = filter.include;
  const exclude = filter.exclude;
  
  if (Array.isArray(include)) {
    include.forEach((pattern) => {
      if (typeof pattern === 'string') {
        conditions.push({
          id: generateId(),
          type: 'include',
          pattern,
          matchType: pattern.includes('*') ? 'wildcard' : 'exact',
        });
      }
    });
  }
  
  if (Array.isArray(exclude)) {
    exclude.forEach((pattern) => {
      if (typeof pattern === 'string') {
        conditions.push({
          id: generateId(),
          type: 'exclude',
          pattern,
          matchType: pattern.includes('*') ? 'wildcard' : 'exact',
        });
      }
    });
  }
  
  return conditions;
};

/**
 * Конвертирует массив условий в JSON-фильтр хостов.
 */
export const toHostFilter = (conditions: HostCondition[]): Record<string, unknown> | undefined => {
  if (conditions.length === 0) return undefined;
  
  const include = conditions.filter((c) => c.type === 'include').map((c) => c.pattern);
  const exclude = conditions.filter((c) => c.type === 'exclude').map((c) => c.pattern);
  
  const filter: Record<string, string[]> = {};
  if (include.length > 0) filter.include = include;
  if (exclude.length > 0) filter.exclude = exclude;
  
  return Object.keys(filter).length > 0 ? filter : undefined;
};

export default HostFilterBuilder;
