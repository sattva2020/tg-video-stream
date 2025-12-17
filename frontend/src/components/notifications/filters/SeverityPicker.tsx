import React from 'react';
import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react';

export type SeverityLevel = 'critical' | 'warning' | 'info' | 'ok';

interface SeverityPickerProps {
  /** Массив выбранных уровней severity */
  selected: SeverityLevel[];
  /** Callback при изменении выбора */
  onChange: (selected: SeverityLevel[]) => void;
  /** Отключить редактирование */
  disabled?: boolean;
}

interface SeverityOption {
  level: SeverityLevel;
  label: string;
  icon: React.ReactNode;
  colorClass: string;
  bgClass: string;
  borderClass: string;
}

const severityOptions: SeverityOption[] = [
  {
    level: 'critical',
    label: 'Critical',
    icon: <AlertTriangle className="w-4 h-4" />,
    colorClass: 'text-red-400',
    bgClass: 'bg-red-500/20',
    borderClass: 'border-red-500/50',
  },
  {
    level: 'warning',
    label: 'Warning',
    icon: <AlertCircle className="w-4 h-4" />,
    colorClass: 'text-yellow-400',
    bgClass: 'bg-yellow-500/20',
    borderClass: 'border-yellow-500/50',
  },
  {
    level: 'info',
    label: 'Info',
    icon: <Info className="w-4 h-4" />,
    colorClass: 'text-blue-400',
    bgClass: 'bg-blue-500/20',
    borderClass: 'border-blue-500/50',
  },
  {
    level: 'ok',
    label: 'Ok',
    icon: <CheckCircle className="w-4 h-4" />,
    colorClass: 'text-green-400',
    bgClass: 'bg-green-500/20',
    borderClass: 'border-green-500/50',
  },
];

/**
 * Визуальный компонент для выбора уровней severity.
 * Заменяет JSON-поле на интуитивные цветные бейджи.
 */
export const SeverityPicker: React.FC<SeverityPickerProps> = ({
  selected,
  onChange,
  disabled = false,
}) => {
  const toggleSeverity = (level: SeverityLevel) => {
    if (disabled) return;
    
    if (selected.includes(level)) {
      onChange(selected.filter((s) => s !== level));
    } else {
      onChange([...selected, level]);
    }
  };

  const selectAll = () => {
    if (disabled) return;
    onChange(severityOptions.map((o) => o.level));
  };

  const clearAll = () => {
    if (disabled) return;
    onChange([]);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Уровни важности</span>
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            onClick={selectAll}
            disabled={disabled}
            className="text-[color:var(--color-accent)] hover:underline disabled:opacity-50"
          >
            Все
          </button>
          <span className="text-[color:var(--color-text-secondary)]">|</span>
          <button
            type="button"
            onClick={clearAll}
            disabled={disabled}
            className="text-[color:var(--color-text-secondary)] hover:underline disabled:opacity-50"
          >
            Очистить
          </button>
        </div>
      </div>
      
      <div className="flex flex-wrap gap-2">
        {severityOptions.map((option) => {
          const isSelected = selected.includes(option.level);
          
          return (
            <button
              key={option.level}
              type="button"
              onClick={() => toggleSeverity(option.level)}
              disabled={disabled}
              className={`
                inline-flex items-center gap-2 px-3 py-2 rounded-lg border-2 
                transition-all duration-150 cursor-pointer
                ${isSelected 
                  ? `${option.bgClass} ${option.borderClass} ${option.colorClass}` 
                  : 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-border)] text-[color:var(--color-text-secondary)]'
                }
                ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:opacity-80'}
              `}
              aria-pressed={isSelected}
            >
              <span className={isSelected ? option.colorClass : 'opacity-50'}>
                {option.icon}
              </span>
              <span className="text-sm font-medium">{option.label}</span>
              {isSelected && (
                <span className={`w-2 h-2 rounded-full ${option.colorClass.replace('text-', 'bg-')}`} />
              )}
            </button>
          );
        })}
      </div>
      
      {selected.length === 0 && (
        <p className="text-xs text-[color:var(--color-text-secondary)]">
          Не выбрано ни одного уровня — правило будет применяться ко всем событиям
        </p>
      )}
    </div>
  );
};

/**
 * Конвертирует JSON-фильтр severity в массив уровней.
 */
export const parseSeverityFilter = (filter: Record<string, unknown> | null | undefined): SeverityLevel[] => {
  if (!filter) return [];
  
  const include = filter.include;
  if (Array.isArray(include)) {
    return include.filter((level): level is SeverityLevel => 
      typeof level === 'string' && ['critical', 'warning', 'info', 'ok'].includes(level)
    );
  }
  
  return [];
};

/**
 * Конвертирует массив уровней severity в JSON-фильтр.
 */
export const toSeverityFilter = (levels: SeverityLevel[]): Record<string, unknown> | undefined => {
  if (levels.length === 0) return undefined;
  return { include: levels };
};

export default SeverityPicker;
