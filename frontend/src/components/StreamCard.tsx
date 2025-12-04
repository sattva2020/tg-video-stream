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
        bg-white dark:bg-gray-800 rounded-lg shadow-md 
        border border-gray-200 dark:border-gray-700
        p-4 transition-all hover:shadow-lg
        ${onClick ? 'cursor-pointer hover:border-blue-400' : ''}
        ${className}
      `}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{statusConfig.icon}</span>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {channelName || `Channel ${displayChannelId}`}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
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
        <span className="text-2xl font-bold text-gray-900 dark:text-white">
          {streamState.listeners_count}
        </span>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          listeners
        </span>
      </div>

      {/* Current Position (for playing streams) */}
      {streamState.status === 'playing' && streamState.current_position > 0 && (
        <div className="flex items-center gap-2 mb-3 text-sm text-gray-600 dark:text-gray-300">
          <span>⏱️</span>
          <span>{formatDuration(streamState.current_position)}</span>
        </div>
      )}

      {/* Placeholder Warning */}
      {streamState.is_placeholder && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-2 mb-3">
          <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300 text-sm">
            <span>🔄</span>
            <span>Playing placeholder audio (queue empty)</span>
          </div>
        </div>
      )}

      {/* Auto-End Warning */}
      {autoEndWarning && (
        <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-md p-2 mb-3">
          <div className="flex items-center gap-2 text-orange-700 dark:text-orange-300 text-sm">
            <span>⚠️</span>
            <span>
              Auto-stop in {autoEndWarning.remaining_seconds}s (no listeners)
            </span>
          </div>
        </div>
      )}

      {/* Current Track */}
      {streamState.current_item_id && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-3 mt-3">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
            Current Track
          </p>
          <p className="text-sm text-gray-700 dark:text-gray-300 truncate">
            {streamState.current_item_id}
          </p>
        </div>
      )}

      {/* Footer - Last Update */}
      <div className="border-t border-gray-200 dark:border-gray-700 pt-2 mt-3">
        <p className="text-xs text-gray-400 dark:text-gray-500">
          Updated {formatTimeAgo(streamState.timestamp)}
        </p>
      </div>
    </div>
  );
};

export default StreamCard;
