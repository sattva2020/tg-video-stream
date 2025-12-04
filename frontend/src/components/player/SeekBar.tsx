/**
 * SeekBar Component
 * Управление позицией воспроизведения трека
 * 
 * Features:
 * - Progress slider with time display
 * - Current time and total duration display
 * - Seek to specific position
 * - Real-time progress updates
 * - Keyboard shortcuts (arrow keys)
 * - Accessibility support (ARIA labels)
 * 
 * User Story: US2 - Seek & Rewind
 * Related Tasks: T020-T026
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Play, SkipBack, SkipForward } from 'lucide-react';

export interface SeekBarProps {
  /** Current playback position in seconds */
  currentTime?: number;
  /** Total track duration in seconds */
  duration?: number;
  /** Callback when user seeks */
  onSeek?: (position: number) => void;
  /** Callback when rewind button clicked (go back N seconds) */
  onRewind?: (seconds: number) => void;
  /** Callback when forward button clicked (go forward N seconds) */
  onForward?: (seconds: number) => void;
  /** API base URL */
  apiBaseUrl?: string;
  /** Whether component is disabled */
  disabled?: boolean;
  /** Auto-update position from backend (poll interval in ms, 0 to disable) */
  autoUpdateInterval?: number;
}

const REWIND_SECONDS = 10;
const FORWARD_SECONDS = 10;
const POLL_INTERVAL = 1000; // 1 second

/**
 * Format seconds to MM:SS display format
 */
const formatTime = (seconds: number): string => {
  if (!Number.isFinite(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * SeekBar Component
 * 
 * Provides UI for seeking within a track with time display,
 * rewind/forward shortcuts, and progress visualization.
 */
export const SeekBar: React.FC<SeekBarProps> = ({
  currentTime = 0,
  duration = 0,
  onSeek,
  onRewind,
  onForward,
  apiBaseUrl = '/api',
  disabled = false,
  autoUpdateInterval = POLL_INTERVAL,
}) => {
  const { t } = useTranslation();
  const [position, setPosition] = useState<number>(currentTime);
  const [displayDuration, setDisplayDuration] = useState<number>(duration);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Update position when currentTime prop changes
  useEffect(() => {
    if (!isDragging) {
      setPosition(currentTime);
    }
  }, [currentTime, isDragging]);

  // Update duration when prop changes
  useEffect(() => {
    setDisplayDuration(duration);
  }, [duration]);

  /**
   * Poll backend for current position
   */
  const pollPosition = useCallback(async () => {
    if (!autoUpdateInterval || disabled || isDragging) return;
    
    try {
      const response = await axios.get(`${apiBaseUrl}/playback/position`);
      if (response.data && typeof response.data.position === 'number') {
        setPosition(response.data.position);
        if (response.data.duration) {
          setDisplayDuration(response.data.duration);
        }
      }
    } catch (err) {
      console.warn('Failed to poll position:', err);
      // Don't show error for polling failures
    }
  }, [apiBaseUrl, autoUpdateInterval, disabled, isDragging]);

  /**
   * Setup polling interval
   */
  useEffect(() => {
    if (!autoUpdateInterval || disabled) {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
      return;
    }

    pollIntervalRef.current = setInterval(pollPosition, autoUpdateInterval);
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [autoUpdateInterval, disabled, pollPosition]);

  /**
   * Seek to specific position
   */
  const handleSeek = useCallback(
    async (newPosition: number) => {
      try {
        setIsLoading(true);
        setError(null);

        // Clamp position to valid range
        const clampedPosition = Math.max(0, Math.min(displayDuration, newPosition));

        // Call API endpoint
        await axios.post(`${apiBaseUrl}/playback/seek`, {
          position: clampedPosition,
        });

        setPosition(clampedPosition);
        onSeek?.(clampedPosition);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to seek';
        setError(message);
        console.error('Seek error:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [apiBaseUrl, displayDuration, onSeek]
  );

  /**
   * Handle slider change
   */
  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newPosition = parseFloat(e.target.value);
      setPosition(newPosition);
    },
    []
  );

  /**
   * Handle slider mouse down (start dragging)
   */
  const handleMouseDown = useCallback(() => {
    setIsDragging(true);
  }, []);

  /**
   * Handle slider mouse up (stop dragging and seek)
   */
  const handleMouseUp = useCallback(
    (e: React.MouseEvent<HTMLInputElement>) => {
      const newPosition = parseFloat((e.target as HTMLInputElement).value);
      setIsDragging(false);
      handleSeek(newPosition);
    },
    [handleSeek]
  );

  /**
   * Handle keyboard shortcuts
   */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (disabled) return;

      // Right arrow: forward 10 seconds
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        const newPosition = Math.min(displayDuration, position + FORWARD_SECONDS);
        handleSeek(newPosition);
        onForward?.(FORWARD_SECONDS);
      }
      // Left arrow: rewind 10 seconds
      else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        const newPosition = Math.max(0, position - REWIND_SECONDS);
        handleSeek(newPosition);
        onRewind?.(REWIND_SECONDS);
      }
    },
    [disabled, displayDuration, position, handleSeek, onForward, onRewind]
  );

  /**
   * Handle rewind button
   */
  const handleRewindClick = useCallback(() => {
    const newPosition = Math.max(0, position - REWIND_SECONDS);
    handleSeek(newPosition);
    onRewind?.(REWIND_SECONDS);
  }, [position, handleSeek, onRewind]);

  /**
   * Handle forward button
   */
  const handleForwardClick = useCallback(() => {
    const newPosition = Math.min(displayDuration, position + FORWARD_SECONDS);
    handleSeek(newPosition);
    onForward?.(FORWARD_SECONDS);
  }, [position, displayDuration, handleSeek, onForward]);

  const progressPercentage =
    displayDuration > 0 ? (position / displayDuration) * 100 : 0;

  return (
    <div
      className="w-full space-y-3 rounded-lg bg-gray-900 p-4"
      onKeyDown={handleKeyDown}
      role="region"
      aria-label={t('playback.seek_bar', 'Seek bar')}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <Play className="h-5 w-5 text-green-400" />
        <h3 className="text-sm font-medium text-gray-100">
          {t('playback.seek_control', 'Seek Control')}
        </h3>
      </div>

      {/* Seek Slider */}
      <div className="space-y-2">
        <input
          type="range"
          min="0"
          max={displayDuration || 100}
          step="0.1"
          value={position}
          onChange={handleSliderChange}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          disabled={disabled || isLoading}
          aria-label={t('playback.position_slider', 'Track position slider')}
          className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            background: `linear-gradient(to right, #10b981 0%, #10b981 ${progressPercentage}%, #374151 ${progressPercentage}%, #374151 100%)`,
          }}
        />
      </div>

      {/* Time Display */}
      <div className="flex items-center justify-between text-sm">
        <span className="font-mono text-gray-300">
          {formatTime(position)}
        </span>
        <span className="text-gray-500">/</span>
        <span className="font-mono text-gray-400">
          {formatTime(displayDuration)}
        </span>
      </div>

      {/* Rewind/Forward Controls */}
      <div className="flex items-center justify-center gap-2">
        <button
          onClick={handleRewindClick}
          disabled={disabled || isLoading || position <= 0}
          title={t('playback.rewind_10s', 'Rewind 10 seconds (← key)')}
          className="flex items-center gap-1 rounded-lg bg-gray-700 px-3 py-2 text-sm text-gray-300 transition-all hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <SkipBack className="h-4 w-4" />
          <span>-{REWIND_SECONDS}s</span>
        </button>

        <div className="flex-1" />

        <button
          onClick={handleForwardClick}
          disabled={
            disabled || isLoading || position >= displayDuration
          }
          title={t('playback.forward_10s', 'Forward 10 seconds (→ key)')}
          className="flex items-center gap-1 rounded-lg bg-gray-700 px-3 py-2 text-sm text-gray-300 transition-all hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span>+{FORWARD_SECONDS}s</span>
          <SkipForward className="h-4 w-4" />
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-sm bg-red-900 px-3 py-2 text-sm text-red-100">
          {error}
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="text-center text-xs text-gray-400">
          {t('common.updating', 'Updating...')}
        </div>
      )}

      {/* Keyboard Hint */}
      <div className="text-xs text-gray-500">
        {t('playback.keyboard_hint', 'Use arrow keys to rewind/forward')}
      </div>
    </div>
  );
};

export default SeekBar;
