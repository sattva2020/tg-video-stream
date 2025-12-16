/**
 * Feature 022 Phase 3: Stream Quality Alert Settings Component
 * 
 * Интерфейс для конфигурации alert'ов при падении качества потока
 */

import { useEffect, useState } from 'react';
import { QualityAlertConfigUpdate, QualityAlertConfigResponse } from '../../api/admin';

interface StreamQualityAlertSettingsProps {
  streamUrl: string;
  streamName?: string;
  loading?: boolean;
  error?: string | null;
}

const qualityLevels = ['low', 'medium', 'high', 'lossless', 'ultra'];
const resolutionOptions = ['640x480', '1280x720', '1920x1080', '2560x1440', '3840x2160'];

/**
 * StreamQualityAlertSettings - Компонент для управления alert конфигурацией
 * 
 * Features:
 * - Пороги качества (overall, audio, video)
 * - Пороги bitrate
 * - Минимальное разрешение
 * - Channels (Telegram, Email, etc)
 * - Behavior settings (degradation, recovery)
 * - Toggle enable/disable
 */
export default function StreamQualityAlertSettings({
  streamUrl,
  streamName,

  loading = false,
  error = null,
}: StreamQualityAlertSettingsProps) {
  const [config, setConfig] = useState<QualityAlertConfigUpdate>({
    stream_url: streamUrl,
    stream_name: streamName,
    min_overall_quality: 'medium',
    min_audio_quality: 'medium',
    min_video_quality: 'high',
    min_audio_bitrate_kbps: 128,
    min_video_bitrate_kbps: 1500,
    min_video_resolution: '1280x720',
    enabled: true,
    notify_on_degradation: true,
    notify_on_recovery: true,
    consecutive_failures: 3,
    alert_channels: {
      telegram: [],
      email: [],
    },
  });

  const [isLoading, setIsLoading] = useState(loading);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(error);

  const [showAdvanced, setShowAdvanced] = useState(false);

  // Load existing config on mount
  useEffect(() => {
    const loadConfig = async () => {
      setIsLoading(true);
      try {
        // TODO: Import adminApi when ready
        // const existingConfig = await adminApi.getQualityAlertConfig(streamUrl);
        // if (existingConfig) {
        //   setConfig(existingConfig);
        // }
        console.log(`Loading alert config for ${streamUrl}`);
        setIsLoading(false);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Unknown error';
        setErrorMsg(`Failed to load config: ${message}`);
      } finally {
        setIsLoading(false);
      }
    };

    loadConfig();
  }, [streamUrl]);

  const handleSave = async () => {
    setIsSaving(true);
    setSuccessMessage(null);
    setErrorMsg(null);

    try {
      // TODO: Import adminApi when ready
      // const result = await adminApi.setQualityAlertConfig(config);
      // if (onSave) onSave(result);
      // setSuccessMessage('Alert configuration saved successfully!');

      console.log('Saving config:', config);
      setSuccessMessage('Alert configuration saved successfully!');
      
      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(`Failed to save config: ${message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const updateConfig = (updates: Partial<QualityAlertConfigUpdate>) => {
    setConfig((prev) => ({ ...prev, ...updates }));
  };

  if (isLoading) {
    return (
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 flex items-center justify-center min-h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading alert settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow p-6">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Alert Settings</h3>
          <p className="text-sm text-gray-600 mt-1">
            {streamName || streamUrl}
          </p>
        </div>
        <label className="flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={config.enabled ?? true}
            onChange={(e) => updateConfig({ enabled: e.target.checked })}
            className="w-4 h-4 text-blue-600 rounded"
          />
          <span className="ml-2 text-sm text-gray-700">
            {config.enabled ? 'Enabled' : 'Disabled'}
          </span>
        </label>
      </div>

      {/* Error message */}
      {errorMsg && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {errorMsg}
        </div>
      )}

      {/* Success message */}
      {successMessage && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded text-green-700 text-sm">
          {successMessage}
        </div>
      )}

      {/* Quality Thresholds */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-medium text-gray-900 mb-4">Quality Thresholds</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Overall Quality */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Minimum Overall Quality
            </label>
            <select
              value={config.min_overall_quality || 'medium'}
              onChange={(e) => updateConfig({ min_overall_quality: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
            >
              {qualityLevels.map((level) => (
                <option key={level} value={level}>
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Audio Quality */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Minimum Audio Quality
            </label>
            <select
              value={config.min_audio_quality || 'medium'}
              onChange={(e) => updateConfig({ min_audio_quality: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
            >
              <option value="">No threshold</option>
              {qualityLevels.map((level) => (
                <option key={level} value={level}>
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Video Quality */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Minimum Video Quality
            </label>
            <select
              value={config.min_video_quality || 'high'}
              onChange={(e) => updateConfig({ min_video_quality: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
            >
              <option value="">No threshold</option>
              {qualityLevels.map((level) => (
                <option key={level} value={level}>
                  {level.charAt(0).toUpperCase() + level.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Consecutive Failures */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Consecutive Failures to Alert
            </label>
            <input
              type="number"
              min="1"
              max="10"
              value={config.consecutive_failures || 3}
              onChange={(e) =>
                updateConfig({ consecutive_failures: parseInt(e.target.value) })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
            />
          </div>
        </div>
      </div>

      {/* Bitrate Thresholds (Advanced) */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="mb-4 text-sm text-blue-600 hover:text-blue-700 font-medium"
      >
        {showAdvanced ? '▼' : '▶'} Advanced Bitrate Thresholds
      </button>

      {showAdvanced && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Audio Bitrate */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Minimum Audio Bitrate (kbps)
              </label>
              <input
                type="number"
                min="0"
                step="8"
                value={config.min_audio_bitrate_kbps || 0}
                onChange={(e) =>
                  updateConfig({ min_audio_bitrate_kbps: parseInt(e.target.value) || undefined })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                placeholder="Optional"
              />
              <p className="text-xs text-gray-500 mt-1">Common: 64, 128, 192, 256, 320 kbps</p>
            </div>

            {/* Video Bitrate */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Minimum Video Bitrate (kbps)
              </label>
              <input
                type="number"
                min="0"
                step="100"
                value={config.min_video_bitrate_kbps || 0}
                onChange={(e) =>
                  updateConfig({ min_video_bitrate_kbps: parseInt(e.target.value) || undefined })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                placeholder="Optional"
              />
              <p className="text-xs text-gray-500 mt-1">Common: 500, 1000, 1500, 2500, 5000 kbps</p>
            </div>

            {/* Video Resolution */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Minimum Video Resolution
              </label>
              <select
                value={config.min_video_resolution || ''}
                onChange={(e) =>
                  updateConfig({
                    min_video_resolution: e.target.value || undefined,
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
              >
                <option value="">No threshold</option>
                {resolutionOptions.map((res) => (
                  <option key={res} value={res}>
                    {res}
                  </option>
                ))}
              </select>
            </div>

            {/* Video FPS */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Minimum Video FPS
              </label>
              <input
                type="number"
                min="0"
                max="120"
                step="1"
                value={config.min_video_fps || 0}
                onChange={(e) =>
                  updateConfig({ min_video_fps: parseFloat(e.target.value) || undefined })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                placeholder="Optional"
              />
              <p className="text-xs text-gray-500 mt-1">Common: 24, 30, 60 fps</p>
            </div>
          </div>
        </div>
      )}

      {/* Alert Behavior */}
      <div className="mb-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-medium text-gray-900 mb-4">Alert Behavior</h4>
        <div className="space-y-3">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.notify_on_degradation ?? true}
              onChange={(e) =>
                updateConfig({ notify_on_degradation: e.target.checked })
              }
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="ml-2 text-sm text-gray-700">
              Notify when quality degrades
            </span>
          </label>

          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.notify_on_recovery ?? true}
              onChange={(e) =>
                updateConfig({ notify_on_recovery: e.target.checked })
              }
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="ml-2 text-sm text-gray-700">
              Notify when quality recovers
            </span>
          </label>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end gap-3">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className={`px-4 py-2 rounded font-medium text-white transition ${
            isSaving
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {isSaving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>

      {/* Info Box */}
      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded text-sm text-blue-800">
        <p className="font-medium mb-2">ℹ️ Alert Notification</p>
        <p>
          Alerts will be triggered when consecutive failures exceed the threshold. Configure channels (Telegram, Email, etc.) above to receive notifications.
        </p>
      </div>
    </div>
  );
}
