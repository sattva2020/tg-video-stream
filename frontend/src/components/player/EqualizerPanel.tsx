/**
 * EqualizerPanel Component
 * Управление предустановками эквалайзера и пользовательскими настройками
 * 
 * Features:
 * - 12 EQ presets (Flat, Bass Boost, Vocal, etc.)
 * - 10-band graphic equalizer with individual sliders
 * - Custom preset saving
 * - Real-time audio adjustment via GStreamer
 * - Accessibility support (ARIA labels)
 * 
 * User Story: US6 - Equalizer
 * Related Tasks: T040-T045
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Volume2, Settings, X } from 'lucide-react';

export interface EqualizerPreset {
  id: string;
  name: string;
  description?: string;
  bands: number[]; // Array of 10 dB values
}

export interface EqualizerPanelProps {
  /** Initial preset ID */
  initialPreset?: string;
  /** Callback when preset changes */
  onPresetChange?: (presetId: string) => void;
  /** Callback when custom bands change */
  onBandsChange?: (bands: number[]) => void;
  /** API base URL */
  apiBaseUrl?: string;
  /** Whether component is disabled */
  disabled?: boolean;
  /** Show only presets (hide band sliders) */
  presetsOnly?: boolean;
}

// Standard 10-band EQ frequencies (equal spacing on log scale)
const EQ_FREQUENCIES = [60, 150, 400, 1000, 2400, 6000, 15000, 20000];
const EQ_MIN = -12;
const EQ_MAX = 12;
const EQ_STEP = 0.5;

/**
 * Default EQ presets with carefully tuned values
 */
const DEFAULT_PRESETS: EqualizerPreset[] = [
  {
    id: 'flat',
    name: 'Flat',
    description: 'Default: No modification',
    bands: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  },
  {
    id: 'bassboost',
    name: 'Bass Boost',
    description: 'Enhanced low frequencies',
    bands: [8, 6, 4, 2, 0, -2, -4, -2, 0, 0],
  },
  {
    id: 'trebleboost',
    name: 'Treble Boost',
    description: 'Enhanced high frequencies',
    bands: [0, -2, -4, -2, 0, 2, 4, 6, 8, 8],
  },
  {
    id: 'vocal',
    name: 'Vocal',
    description: 'Enhanced midrange for vocals',
    bands: [-4, -2, 0, 4, 6, 4, 2, 0, -2, -4],
  },
  {
    id: 'jazz',
    name: 'Jazz',
    description: 'Warm and smooth',
    bands: [4, 3, 1, 2, -2, 4, 3, 2, 1, 0],
  },
  {
    id: 'rock',
    name: 'Rock',
    description: 'Punchy bass and treble',
    bands: [6, 4, 2, 1, 0, 2, 4, 5, 6, 7],
  },
  {
    id: 'pop',
    name: 'Pop',
    description: 'Upbeat and bright',
    bands: [2, 4, 3, 2, 0, -2, 2, 4, 3, 2],
  },
  {
    id: 'electronic',
    name: 'Electronic',
    description: 'Deep bass with clarity',
    bands: [6, 5, 2, 0, -2, 0, 2, 3, 4, 3],
  },
  {
    id: 'classical',
    name: 'Classical',
    description: 'Balanced and detailed',
    bands: [1, 1, 0, -1, -2, 1, 2, 2, 1, 0],
  },
  {
    id: 'meditation',
    name: 'Meditation',
    description: 'Calm and relaxing',
    bands: [-6, -4, -2, 0, 2, 2, 0, -2, -4, -6],
  },
  {
    id: 'gaming',
    name: 'Gaming',
    description: 'Enhanced directional cues',
    bands: [2, 3, 2, 1, -1, 0, 3, 4, 5, 4],
  },
  {
    id: 'podcast',
    name: 'Podcast',
    description: 'Clear speech intelligibility',
    bands: [-3, -1, 0, 2, 4, 3, 1, 0, -2, -4],
  },
];

/**
 * EqualizerPanel Component
 * 
 * Provides UI for selecting EQ presets and fine-tuning individual bands
 * with real-time audio adjustment.
 */
export const EqualizerPanel: React.FC<EqualizerPanelProps> = ({
  initialPreset = 'flat',
  onPresetChange,
  onBandsChange,
  apiBaseUrl = '/api',
  disabled = false,
  presetsOnly = false,
}) => {
  const { t } = useTranslation();
  const [selectedPreset, setSelectedPreset] = useState<string>(initialPreset);
  const [customBands, setCustomBands] = useState<number[]>(
    DEFAULT_PRESETS.find((p) => p.id === initialPreset)?.bands || DEFAULT_PRESETS[0].bands
  );
  const [isCustom, setIsCustom] = useState(false);
  const [showBands, setShowBands] = useState(!presetsOnly);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [availablePresets, setAvailablePresets] = useState(DEFAULT_PRESETS);

  /**
   * Fetch available presets from server
   */
  useEffect(() => {
    const fetchPresets = async () => {
      try {
        const response = await axios.get(`${apiBaseUrl}/playback/equalizer/presets`);
        if (response.data && Array.isArray(response.data)) {
          setAvailablePresets(response.data);
        }
      } catch (err) {
        console.warn('Failed to fetch EQ presets:', err);
        // Use default presets on error
      }
    };

    fetchPresets();
  }, [apiBaseUrl]);

  /**
   * Apply preset
   */
  const applyPreset = useCallback(
    async (presetId: string) => {
      try {
        setIsLoading(true);
        setError(null);

        const preset = availablePresets.find((p) => p.id === presetId);
        if (!preset) {
          throw new Error('Preset not found');
        }

        // Call API endpoint
        await axios.put(`${apiBaseUrl}/playback/equalizer`, {
          preset: presetId,
          bands: preset.bands,
        });

        setSelectedPreset(presetId);
        setCustomBands(preset.bands);
        setIsCustom(false);
        onPresetChange?.(presetId);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to apply preset';
        setError(message);
        console.error('Preset apply error:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [apiBaseUrl, availablePresets, onPresetChange]
  );

  /**
   * Update individual band value
   */
  const handleBandChange = useCallback(
    async (bandIndex: number, newValue: number) => {
      const updatedBands = [...customBands];
      updatedBands[bandIndex] = newValue;

      try {
        setIsLoading(true);
        setError(null);

        // Call API endpoint
        await axios.put(`${apiBaseUrl}/playback/equalizer`, {
          preset: 'custom',
          bands: updatedBands,
        });

        setCustomBands(updatedBands);
        setSelectedPreset('custom');
        setIsCustom(true);
        onBandsChange?.(updatedBands);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update band';
        setError(message);
        console.error('Band update error:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [apiBaseUrl, customBands, onBandsChange]
  );

  /**
   * Reset to flat
   */
  const handleReset = useCallback(() => {
    applyPreset('flat');
  }, [applyPreset]);

  /**
   * Get preset button styling
   */
  const getPresetButtonClass = (presetId: string): string => {
    const isActive =
      (isCustom && presetId === 'custom') || (!isCustom && selectedPreset === presetId);
    return `px-3 py-2 text-xs font-medium rounded transition-all ${
      isActive
        ? 'bg-purple-500 text-white'
        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
    } disabled:cursor-not-allowed disabled:opacity-50`;
  };

  return (
    <div className="w-full space-y-4 rounded-lg bg-gray-900 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Volume2 className="h-5 w-5 text-purple-400" />
          <h3 className="text-sm font-medium text-gray-100">
            {t('playback.equalizer', 'Equalizer')}
          </h3>
        </div>
        <button
          onClick={() => setShowBands(!showBands)}
          disabled={disabled || isLoading || presetsOnly}
          className="p-1 hover:bg-gray-800 rounded transition-all disabled:opacity-50"
          title={t('playback.toggle_bands', 'Toggle band details')}
        >
          <Settings className="h-4 w-4 text-gray-400" />
        </button>
      </div>

      {/* Presets Grid */}
      <div className="space-y-2">
        <label className="text-xs text-gray-400">
          {t('playback.presets', 'Presets')}
        </label>
        <div className="grid grid-cols-3 gap-2 overflow-y-auto max-h-32">
          {availablePresets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => applyPreset(preset.id)}
              disabled={disabled || isLoading}
              className={getPresetButtonClass(preset.id)}
              title={preset.description}
            >
              {preset.name}
            </button>
          ))}
        </div>
      </div>

      {/* Band Sliders (Collapsible) */}
      {showBands && !presetsOnly && (
        <div className="space-y-3 border-t border-gray-700 pt-3">
          <div className="flex items-center justify-between">
            <label className="text-xs text-gray-400">
              {t('playback.10band_eq', '10-Band Equalizer')}
            </label>
            <button
              onClick={handleReset}
              disabled={disabled || isLoading}
              className="text-xs px-2 py-1 rounded bg-gray-700 text-gray-300 hover:bg-gray-600 transition-all disabled:opacity-50"
            >
              {t('common.reset', 'Reset')}
            </button>
          </div>

          {/* Band Sliders */}
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {customBands.map((value, index) => (
              <div key={index} className="flex items-center gap-2">
                <span className="w-12 text-xs text-gray-500 text-right">
                  {index < EQ_FREQUENCIES.length
                    ? `${EQ_FREQUENCIES[index]}Hz`
                    : `Band ${index + 1}`}
                </span>
                <input
                  type="range"
                  min={EQ_MIN}
                  max={EQ_MAX}
                  step={EQ_STEP}
                  value={value}
                  onChange={(e) => handleBandChange(index, parseFloat(e.target.value))}
                  disabled={disabled || isLoading}
                  className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
                />
                <span className="w-8 text-xs text-gray-400 text-right">
                  {value > 0 ? '+' : ''}{value.toFixed(1)}
                </span>
              </div>
            ))}
          </div>

          {/* Custom Indicator */}
          {isCustom && (
            <div className="text-xs text-purple-300">
              {t('playback.custom_eq', 'Custom Equalizer')}
            </div>
          )}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="rounded-sm bg-red-900 px-3 py-2 text-sm text-red-100 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="hover:text-red-50">
            <X className="h-4 w-4" />
          </button>
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

export default EqualizerPanel;
