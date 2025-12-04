/**
 * SpeedControl Component
 * Управление скоростью воспроизведения (0.5x - 2.0x)
 * 
 * Features:
 * - Speed range: 0.5x to 2.0x with 0.25x increments
 * - Real-time slider and preset buttons
 * - Pitch correction toggle
 * - API integration for persistence
 * - Accessibility support (ARIA labels)
 * 
 * User Story: US1 - Speed/Pitch Control
 * Related Tasks: T015-T018, T019
 */

import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Play } from 'lucide-react';

interface SpeedControlProps {
  /** Initial speed value (0.5 - 2.0) */
  initialSpeed?: number;
  /** Callback when speed changes */
  onSpeedChange?: (speed: number) => void;
  /** Callback when pitch correction toggles */
  onPitchCorrectionChange?: (enabled: boolean) => void;
  /** API base URL */
  apiBaseUrl?: string;
  /** Whether component is disabled */
  disabled?: boolean;
}

const SPEED_PRESETS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0];
const SPEED_MIN = 0.5;
const SPEED_MAX = 2.0;
const SPEED_STEP = 0.05;

/**
 * SpeedControl Component
 * 
 * Provides UI controls for adjusting playback speed with preset buttons
 * and manual slider adjustment. Includes pitch correction toggle.
 */
export const SpeedControl: React.FC<SpeedControlProps> = ({
  initialSpeed = 1.0,
  onSpeedChange,
  onPitchCorrectionChange,
  apiBaseUrl = '/api',
  disabled = false,
}) => {
  const { t } = useTranslation();
  const [speed, setSpeed] = useState<number>(initialSpeed);
  const [pitchCorrection, setPitchCorrection] = useState<boolean>(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Update speed on the backend
   */
  const updateSpeed = useCallback(
    async (newSpeed: number) => {
      try {
        setIsLoading(true);
        setError(null);

        // Clamp speed to valid range
        const clampedSpeed = Math.max(SPEED_MIN, Math.min(SPEED_MAX, newSpeed));
        
        // Call API endpoint
        await axios.put(`${apiBaseUrl}/playback/speed`, {
          speed: clampedSpeed,
          pitch_correction: pitchCorrection,
        });

        setSpeed(clampedSpeed);
        onSpeedChange?.(clampedSpeed);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update speed';
        setError(message);
        console.error('Speed update error:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [apiBaseUrl, pitchCorrection, onSpeedChange]
  );

  /**
   * Update pitch correction on the backend
   */
  const updatePitchCorrection = useCallback(
    async (enabled: boolean) => {
      try {
        setIsLoading(true);
        setError(null);

        await axios.put(`${apiBaseUrl}/playback/speed`, {
          speed,
          pitch_correction: enabled,
        });

        setPitchCorrection(enabled);
        onPitchCorrectionChange?.(enabled);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update pitch correction';
        setError(message);
        console.error('Pitch correction update error:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [apiBaseUrl, speed, onPitchCorrectionChange]
  );

  /**
   * Handle slider change
   */
  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newSpeed = parseFloat(e.target.value);
      updateSpeed(newSpeed);
    },
    [updateSpeed]
  );

  /**
   * Handle preset button click
   */
  const handlePresetClick = useCallback(
    (preset: number) => {
      updateSpeed(preset);
    },
    [updateSpeed]
  );

  /**
   * Format speed for display
   */
  const formatSpeed = (value: number): string => {
    return `${value.toFixed(2)}x`;
  };

  return (
    <div className="w-full space-y-4 rounded-lg bg-gray-900 p-4">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Play className="h-5 w-5 text-blue-400" />
        <h3 className="text-sm font-medium text-gray-100">
          {t('playback.speed', 'Speed Control')}
        </h3>
      </div>

      {/* Current Speed Display */}
      <div className="flex items-center justify-between rounded bg-gray-800 px-3 py-2">
        <span className="text-sm text-gray-300">{t('playback.current_speed', 'Current Speed')}</span>
        <span className="text-lg font-bold text-blue-400">{formatSpeed(speed)}</span>
      </div>

      {/* Speed Slider */}
      <div className="space-y-2">
        <label htmlFor="speed-slider" className="text-xs text-gray-400">
          {t('playback.adjust_speed', 'Adjust Speed')}
        </label>
        <input
          id="speed-slider"
          type="range"
          min={SPEED_MIN}
          max={SPEED_MAX}
          step={SPEED_STEP}
          value={speed}
          onChange={handleSliderChange}
          disabled={disabled || isLoading}
          aria-label={t('playback.speed_slider', 'Speed slider')}
          className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
          style={{
            background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${((speed - SPEED_MIN) / (SPEED_MAX - SPEED_MIN)) * 100}%, #374151 ${((speed - SPEED_MIN) / (SPEED_MAX - SPEED_MIN)) * 100}%, #374151 100%)`,
          }}
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>{formatSpeed(SPEED_MIN)}</span>
          <span>{formatSpeed(SPEED_MAX)}</span>
        </div>
      </div>

      {/* Speed Presets */}
      <div className="space-y-2">
        <label className="text-xs text-gray-400">
          {t('playback.presets', 'Presets')}
        </label>
        <div className="grid grid-cols-4 gap-2">
          {SPEED_PRESETS.map((preset) => (
            <button
              key={preset}
              onClick={() => handlePresetClick(preset)}
              disabled={disabled || isLoading}
              className={`py-1 px-2 text-xs font-medium rounded transition-all ${
                Math.abs(speed - preset) < 0.01
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-700 text-gray-200 hover:bg-gray-600'
              } disabled:cursor-not-allowed disabled:opacity-50`}
              aria-pressed={Math.abs(speed - preset) < 0.01}
            >
              {formatSpeed(preset)}
            </button>
          ))}
        </div>
      </div>

      {/* Pitch Correction Toggle */}
      <div className="flex items-center gap-3 rounded bg-gray-800 px-3 py-2">
        <input
          id="pitch-correction"
          type="checkbox"
          checked={pitchCorrection}
          onChange={(e) => updatePitchCorrection(e.target.checked)}
          disabled={disabled || isLoading}
          aria-label={t('playback.pitch_correction', 'Pitch correction')}
          className="h-4 w-4 cursor-pointer rounded border-gray-600 bg-gray-700 text-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <label htmlFor="pitch-correction" className="cursor-pointer flex-1 text-sm text-gray-300">
          {t('playback.auto_pitch_correction', 'Auto-correct pitch with speed')}
        </label>
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
    </div>
  );
};

export default SpeedControl;
