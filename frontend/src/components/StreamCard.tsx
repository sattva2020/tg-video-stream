/**
 * StreamCard Component
 * 
 * Карточка активного стрима для мониторинг дашборда.
 * Показывает статус, слушателей, текущий трек и предупреждения.
 * 
 * @example
 * ```tsx
 * <StreamCard
 *   channelId={123456}
 *   streamState={streamState}
 *   autoEndWarning={warning}
 * />
 * ```
 */

import React, { useMemo } from 'react';
import type { StreamState, AutoEndWarning } from '../hooks/useMonitoringWebSocket';

// === Types ===

export interface StreamCardProps {
  /** Telegram channel ID */
  channelId: number;
  /** Current stream state */
  streamState: StreamState;
  /** Auto-end warning (if any) */
  autoEndWarning?: AutoEndWarning;
  /** Channel name (optional) */
  channelName?: string;
  /** CSS class name */
  className?: string;
  /** Click handler */
  onClick?: () => void;
}

// === Status Configuration ===

const STATUS_CONFIG = {
  playing: {
    label: 'Playing',
    color: 'bg-green-500',
    textColor: 'text-green-700',
    icon: '▶️',
  },
  paused: {
    label: 'Paused',
    color: 'bg-yellow-500',
    textColor: 'text-yellow-700',
    icon: '⏸️',
  },
  stopped: {
    label: 'Stopped',
    color: 'bg-gray-500',
    textColor: 'text-gray-700',
    icon: '⏹️',
  },
  placeholder: {
    label: 'Placeholder',
    color: 'bg-blue-500',
    textColor: 'text-blue-700',
    icon: '🔄',
  },
} as const;

// === Helper Functions ===

function formatDuration(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatTimeAgo(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  
  if (diffSec < 5) return 'just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  return `${Math.floor(diffSec / 3600)}h ago`;
}

// === Component ===

export const StreamCard: React.FC<StreamCardProps> = ({
  channelId,
  streamState,
  autoEndWarning,
  channelName,
  className = '',
  onClick,
}) => {
  const statusConfig = STATUS_CONFIG[streamState.status];
  
  // Format channel ID for display
  const displayChannelId = useMemo(() => {
    // Telegram channel IDs are usually negative and start with -100
    const idStr = channelId.toString();
    if (idStr.startsWith('-100')) {
      return idStr.slice(4); // Remove -100 prefix
    }
    return idStr;
  }, [channelId]);

  return (
    <div
      className={`
        rounded-2xl bg-[color:var(--color-panel)]
        border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
        shadow-md shadow-black/5
        p-4 transition-colors
        ${onClick ? 'cursor-pointer hover:border-[color:var(--color-accent)]' : ''}
        ${className}
      `}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{statusConfig.icon}</span>
          <div>
            <h3 className="font-semibold text-[color:var(--color-text)]">
              {channelName || `Channel ${displayChannelId}`}
            </h3>
            <p className="text-xs text-[color:var(--color-text-muted)]">
              ID: {channelId}
            </p>
          </div>
        </div>
        
        {/* Status Badge */}
        <span className={`
          px-2 py-1 rounded-full text-xs font-medium text-white
          ${statusConfig.color}
        `}>
          {statusConfig.label}
        </span>
      </div>

      {/* Listeners */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">👥</span>
        <span className="text-2xl font-bold text-[color:var(--color-text)]">
          {streamState.listeners_count}
        </span>
        <span className="text-sm text-[color:var(--color-text-muted)]">
          listeners
        </span>
      </div>

      {/* Current Position (for playing streams) */}
      {streamState.status === 'playing' && streamState.current_position > 0 && (
        <div className="flex items-center gap-2 mb-3 text-sm text-[color:var(--color-text-muted)]">
          <span>⏱️</span>
          <span>{formatDuration(streamState.current_position)}</span>
        </div>
      )}

      {/* Placeholder Warning */}
      {streamState.is_placeholder && (
        <div className="bg-blue-500/10 border border-blue-500/20 rounded-md p-2 mb-3">
          <div className="flex items-center gap-2 text-blue-300 text-sm">
            <span>🔄</span>
            <span>Playing placeholder audio (queue empty)</span>
          </div>
        </div>
      )}

      {/* Auto-End Warning */}
      {autoEndWarning && (
        <div className="bg-amber-500/10 border border-amber-500/20 rounded-md p-2 mb-3">
          <div className="flex items-center gap-2 text-amber-300 text-sm">
            <span>⚠️</span>
            <span>
              Auto-stop in {autoEndWarning.remaining_seconds}s (no listeners)
            </span>
          </div>
        </div>
      )}

      {/* Current Track */}
      {streamState.current_item_id && (
        <div className="border-t border-[color:var(--color-border)] pt-3 mt-3">
          <p className="text-xs text-[color:var(--color-text-muted)] mb-1">
            Current Track
          </p>
          <p className="text-sm text-[color:var(--color-text)] truncate">
            {streamState.current_item_id}
          </p>
        </div>
      )}

      {/* Footer - Last Update */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-2 mt-3">
        <p className="text-xs text-[color:var(--color-text-muted)]">
          Updated {formatTimeAgo(streamState.timestamp)}
        </p>
      </div>
    </div>
  );
};

export default StreamCard;
