import React from 'react';
import { Clock, Gauge } from 'lucide-react';

interface RateLimitConfigProps {
  /** Максимум сообщений */
  maxMessages: number;
  /** Окно времени в секундах */
  windowSec: number;
  /** Окно дедупликации в секундах */
  dedupWindowSec: number;
  /** Callback при изменении */
  onChange: (config: { maxMessages: number; windowSec: number; dedupWindowSec: number }) => void;
  /** Отключить редактирование */
  disabled?: boolean;
}

/**
 * Простой конфигуратор rate limiting и дедупликации.
 * Заменяет JSON-поле на понятные числовые инпуты.
 */
export const RateLimitConfig: React.FC<RateLimitConfigProps> = ({
  maxMessages,
  windowSec,
  dedupWindowSec,
  onChange,
  disabled = false,
}) => {
  return (
    <div className="space-y-4">
      {/* Rate Limiting */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Gauge className="w-4 h-4 text-[color:var(--color-accent)]" />
          <span className="text-sm font-medium">Rate Limiting</span>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-[color:var(--color-text-secondary)]">Максимум</span>
          <input
            type="number"
            min={0}
            max={1000}
            value={maxMessages}
            onChange={(e) => onChange({ maxMessages: Number(e.target.value), windowSec, dedupWindowSec })}
            disabled={disabled}
            className="w-20 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-2 py-1 text-sm text-center"
          />
          <span className="text-sm text-[color:var(--color-text-secondary)]">сообщений за</span>
          <input
            type="number"
            min={1}
            max={86400}
            value={windowSec}
            onChange={(e) => onChange({ maxMessages, windowSec: Number(e.target.value), dedupWindowSec })}
            disabled={disabled}
            className="w-20 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-2 py-1 text-sm text-center"
          />
          <span className="text-sm text-[color:var(--color-text-secondary)]">сек</span>
        </div>
        
        {maxMessages === 0 && (
          <p className="text-xs text-[color:var(--color-text-secondary)]">
            Rate limiting отключен (0 = без ограничений)
          </p>
        )}
      </div>

      {/* Дедупликация */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-[color:var(--color-accent)]" />
          <span className="text-sm font-medium">Дедупликация</span>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-[color:var(--color-text-secondary)]">Игнорировать дубликаты в течение</span>
          <input
            type="number"
            min={0}
            max={86400}
            value={dedupWindowSec}
            onChange={(e) => onChange({ maxMessages, windowSec, dedupWindowSec: Number(e.target.value) })}
            disabled={disabled}
            className="w-20 rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-2 py-1 text-sm text-center"
          />
          <span className="text-sm text-[color:var(--color-text-secondary)]">сек</span>
        </div>
        
        {dedupWindowSec === 0 && (
          <p className="text-xs text-[color:var(--color-text-secondary)]">
            Дедупликация отключена (0 = все сообщения доставляются)
          </p>
        )}
        {dedupWindowSec > 0 && (
          <p className="text-xs text-[color:var(--color-text-secondary)]">
            Повторные события с тем же содержимым будут пропущены в течение {dedupWindowSec} сек
          </p>
        )}
      </div>

      {/* Пресеты */}
      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-[color:var(--color-text-secondary)]">Быстрые настройки:</span>
        <button
          type="button"
          onClick={() => onChange({ maxMessages: 0, windowSec: 60, dedupWindowSec: 0 })}
          disabled={disabled}
          className="text-xs px-2 py-1 rounded bg-[color:var(--color-surface-muted)] hover:bg-[color:var(--color-border)] transition-colors disabled:opacity-50"
        >
          Без ограничений
        </button>
        <button
          type="button"
          onClick={() => onChange({ maxMessages: 5, windowSec: 60, dedupWindowSec: 300 })}
          disabled={disabled}
          className="text-xs px-2 py-1 rounded bg-[color:var(--color-surface-muted)] hover:bg-[color:var(--color-border)] transition-colors disabled:opacity-50"
        >
          Умеренный (5/мин, dedup 5мин)
        </button>
        <button
          type="button"
          onClick={() => onChange({ maxMessages: 1, windowSec: 300, dedupWindowSec: 600 })}
          disabled={disabled}
          className="text-xs px-2 py-1 rounded bg-[color:var(--color-surface-muted)] hover:bg-[color:var(--color-border)] transition-colors disabled:opacity-50"
        >
          Строгий (1/5мин, dedup 10мин)
        </button>
      </div>
    </div>
  );
};

/**
 * Конвертирует JSON rate_limit в понятные значения.
 */
export const parseRateLimitConfig = (
  rateLimit: Record<string, unknown> | null | undefined,
  dedupWindowSec: number
): { maxMessages: number; windowSec: number; dedupWindowSec: number } => {
  const maxMessages = typeof rateLimit?.per_recipient_min === 'number' 
    ? rateLimit.per_recipient_min 
    : 0;
  const windowSec = typeof rateLimit?.window_sec === 'number' 
    ? rateLimit.window_sec 
    : 60;
  
  return { maxMessages, windowSec, dedupWindowSec };
};

/**
 * Конвертирует значения в JSON rate_limit.
 */
export const toRateLimitConfig = (
  maxMessages: number,
  windowSec: number
): Record<string, unknown> | undefined => {
  if (maxMessages <= 0) return undefined;
  
  return {
    per_recipient_min: maxMessages,
    window_sec: windowSec,
  };
};

export default RateLimitConfig;
