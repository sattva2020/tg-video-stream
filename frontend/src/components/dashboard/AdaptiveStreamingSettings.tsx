/**
 * Feature 009 Phase 7: Adaptive Streaming Settings Component
 *
 * Интерфейс для конфигурации адаптивного битрейта и управления качеством потока
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Card, CardBody, Input, Button, Switch, Select, SelectItem, Chip, Skeleton } from '@heroui/react';
import { Settings, Gauge, Smartphone, Monitor, Save, RefreshCw, Info, CheckCircle2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { adminApi } from '../../api/admin';
import { useToast } from '../../hooks/useToast';
import {
  QualityLevel,
  DeviceType,
  AdaptiveStreamConfigResponse,
  AdaptiveStreamConfigUpdate,
} from '../../types/adaptive-streaming';

interface AdaptiveStreamingSettingsProps {
  streamId: string;
  streamName?: string;
  onSuccess?: () => void;
}

const qualityLevels: QualityLevel[] = ['low', 'medium', 'high', 'ultra'];
const deviceTypes: DeviceType[] = ['mobile', 'tablet', 'desktop', 'tv'];

const qualityLabels: Record<QualityLevel, string> = {
  low: 'Low (360p)',
  medium: 'Medium (480p)',
  high: 'High (720p)',
  ultra: 'Ultra (1080p)',
};

const deviceLabels: Record<DeviceType, string> = {
  mobile: 'Mobile',
  tablet: 'Tablet',
  desktop: 'Desktop',
  tv: 'TV',
};

/**
 * AdaptiveStreamingSettings - Компонент для управления конфигурацией адаптивного стрима
 *
 * Features:
 * - Включение/выключение адаптивного стрима
 * - Настройка профилей качества (low, medium, high, ultra)
 * - Пороги пропускной способности для каждого качества
 * - Настройки адаптации (интервал, сглаживание, измерения)
 * - Правила для устройств
 * - Мониторинг и логирование
 */
export const AdaptiveStreamingSettings: React.FC<AdaptiveStreamingSettingsProps> = ({
  streamId,
  streamName,
  onSuccess,
}) => {
  const { t } = useTranslation();
  const toast = useToast();

  const [config, setConfig] = useState<AdaptiveStreamConfigUpdate | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load existing config
  const loadConfig = useCallback(async () => {
    setLoading(true);
    try {
      const existingConfig = await adminApi.getAdaptiveConfig(streamId);
      if (existingConfig) {
        setConfig(existingConfig);
      } else {
        // Set default config if none exists
        setConfig({
          enabled: false,
          default_quality: 'medium',
          min_quality: 'low',
          max_quality: 'ultra',
          bandwidth_threshold_low_kbps: 1500,
          bandwidth_threshold_medium_kbps: 3000,
          bandwidth_threshold_high_kbps: 6000,
          bandwidth_threshold_ultra_kbps: 8000,
          adaptation_interval_seconds: 30,
          bandwidth_smoothing_factor: 0.3,
          consecutive_measurements_required: 2,
          enable_bandwidth_monitoring: true,
          enable_quality_logging: true,
        });
      }
    } catch (error) {
      console.error('Failed to load adaptive streaming config:', error);
      toast.error(t('adaptive.loadFailed', 'Не удалось загрузить конфигурацию'));
    } finally {
      setLoading(false);
    }
  }, [streamId, toast, t]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const handleSave = async () => {
    if (!config) return;

    setSaving(true);
    setSuccessMessage(null);

    try {
      await adminApi.updateAdaptiveConfig(streamId, config);
      setHasChanges(false);
      setSuccessMessage(t('adaptive.saved', 'Конфигурация сохранена успешно!'));
      toast.success(t('adaptive.saved', 'Конфигурация сохранена успешно!'));

      if (onSuccess) {
        onSuccess();
      }

      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (error) {
      console.error('Failed to save adaptive streaming config:', error);
      toast.error(t('adaptive.saveFailed', 'Не удалось сохранить конфигурацию'));
    } finally {
      setSaving(false);
    }
  };

  const updateConfig = (updates: Partial<AdaptiveStreamConfigUpdate>) => {
    if (!config) return;
    setConfig({ ...config, ...updates });
    setHasChanges(true);
    setSuccessMessage(null);
  };

  const getQualityColor = (quality: string) => {
    switch (quality?.toLowerCase()) {
      case 'ultra':
        return 'success';
      case 'high':
        return 'primary';
      case 'medium':
        return 'warning';
      case 'low':
        return 'default';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
        <Card className="bg-transparent shadow-none border-none">
          <CardBody className="p-6">
            <div className="space-y-6">
              <Skeleton className="rounded-lg w-1/3 h-8" />
              <Skeleton className="rounded-lg w-full h-24" />
              <Skeleton className="rounded-lg w-full h-24" />
              <Skeleton className="rounded-lg w-full h-48" />
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
        <Card className="bg-transparent shadow-none border-none">
          <CardBody className="p-6 flex items-center justify-center min-h-64">
            <div className="text-center">
              <Settings size={48} className="mx-auto mb-4 text-[color:var(--color-text-muted)] opacity-50" />
              <p className="text-[color:var(--color-text-secondary)]">
                {t('adaptive.noConfig', 'Конфигурация не найдена')}
              </p>
            </div>
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
      <Card className="bg-transparent shadow-none border-none">
        <CardBody className="p-6">
          {/* Header */}
          <div className="flex justify-between items-start mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10 text-primary">
                <Settings size={20} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
                  {t('adaptive.title', 'Настройки адаптивного стрима')}
                </h3>
                <p className="text-sm text-[color:var(--color-text-secondary)]">
                  {streamName || streamId}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {hasChanges && (
                <Chip size="sm" color="warning" variant="flat">
                  {t('adaptive.unsaved', 'Есть несохраненные изменения')}
                </Chip>
              )}
              <Button
                isIconOnly
                variant="light"
                onPress={loadConfig}
                className="text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text)]"
              >
                <RefreshCw size={20} />
              </Button>
            </div>
          </div>

          {/* Success Message */}
          {successMessage && (
            <div className="mb-4 p-4 rounded-xl bg-success/10 border border-success/20 flex items-center gap-2">
              <CheckCircle2 size={20} className="text-success" />
              <span className="text-sm text-success">{successMessage}</span>
            </div>
          )}

          {/* Enable/Disable */}
          <div className="mb-6 p-4 rounded-xl bg-[color:var(--color-bg)] border border-[color:var(--color-border)]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Gauge size={20} className="text-[color:var(--color-text-secondary)]" />
                <div>
                  <p className="font-medium text-[color:var(--color-text)]">
                    {t('adaptive.enableAdaptive', 'Адаптивный битрейт')}
                  </p>
                  <p className="text-xs text-[color:var(--color-text-secondary)]">
                    {t('adaptive.enableDescription', 'Автоматическая настройка качества на основе пропускной способности')}
                  </p>
                </div>
              </div>
              <Switch
                isSelected={config.enabled ?? false}
                onValueChange={(checked) => updateConfig({ enabled: checked })}
                color="primary"
              />
            </div>
          </div>

          {/* Quality Profiles */}
          <div className="mb-6 space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]">
              <Monitor size={16} />
              <span>{t('adaptive.qualityProfiles', 'Профили качества')}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Default Quality */}
              <div>
                <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                  {t('adaptive.defaultQuality', 'Качество по умолчанию')}
                </label>
                <Select
                  selectedKeys={config.default_quality ? [config.default_quality] : []}
                  onSelectionChange={(keys) => {
                    const quality = Array.from(keys)[0] as QualityLevel;
                    updateConfig({ default_quality: quality });
                  }}
                  classNames={{
                    trigger: 'bg-[color:var(--color-bg)] border-[color:var(--color-border)]',
                  }}
                >
                  {qualityLevels.map((level) => (
                    <SelectItem key={level} textValue={qualityLabels[level]}>
                      <div className="flex items-center gap-2">
                        <Chip size="sm" color={getQualityColor(level)} variant="flat">
                          {level.toUpperCase()}
                        </Chip>
                        <span>{qualityLabels[level]}</span>
                      </div>
                    </SelectItem>
                  ))}
                </Select>
              </div>

              {/* Min/Max Quality */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                    {t('adaptive.minQuality', 'Мин. качество')}
                  </label>
                  <Select
                    selectedKeys={config.min_quality ? [config.min_quality] : []}
                    onSelectionChange={(keys) => {
                      const quality = Array.from(keys)[0] as QualityLevel;
                      updateConfig({ min_quality: quality });
                    }}
                    classNames={{
                      trigger: 'bg-[color:var(--color-bg)] border-[color:var(--color-border)]',
                    }}
                  >
                    {qualityLevels.map((level) => (
                      <SelectItem key={level}>
                        {level.charAt(0).toUpperCase() + level.slice(1)}
                      </SelectItem>
                    ))}
                  </Select>
                </div>

                <div>
                  <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                    {t('adaptive.maxQuality', 'Макс. качество')}
                  </label>
                  <Select
                    selectedKeys={config.max_quality ? [config.max_quality] : []}
                    onSelectionChange={(keys) => {
                      const quality = Array.from(keys)[0] as QualityLevel;
                      updateConfig({ max_quality: quality });
                    }}
                    classNames={{
                      trigger: 'bg-[color:var(--color-bg)] border-[color:var(--color-border)]',
                    }}
                  >
                    {qualityLevels.map((level) => (
                      <SelectItem key={level}>
                        {level.charAt(0).toUpperCase() + level.slice(1)}
                      </SelectItem>
                    ))}
                  </Select>
                </div>
              </div>
            </div>
          </div>

          {/* Bandwidth Thresholds */}
          <div className="mb-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]">
                <Gauge size={16} />
                <span>{t('adaptive.bandwidthThresholds', 'Пороги пропускной способности (Kbps)')}</span>
              </div>
              <div className="flex items-center gap-1 text-xs text-[color:var(--color-text-muted)]">
                <Info size={14} />
                <span>{t('adaptive.thresholdHint', 'Мин. полоса для переключения качества')}</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl bg-[color:var(--color-bg)] border border-[color:var(--color-border)]">
              {/* Low Quality Threshold */}
              <div>
                <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                  {t('adaptive.lowThreshold', 'Low Quality')} ≤
                </label>
                <Input
                  type="number"
                  min="0"
                  step="100"
                  value={String(config.bandwidth_threshold_low_kbps ?? 1500)}
                  onValueChange={(value) =>
                    updateConfig({ bandwidth_threshold_low_kbps: parseInt(value) || 1500 })
                  }
                  classNames={{
                    input: 'bg-[color:var(--color-bg)]',
                  }}
                  endContent="Kbps"
                />
              </div>

              {/* Medium Quality Threshold */}
              <div>
                <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                  {t('adaptive.mediumThreshold', 'Medium Quality')} ≤
                </label>
                <Input
                  type="number"
                  min="0"
                  step="100"
                  value={String(config.bandwidth_threshold_medium_kbps ?? 3000)}
                  onValueChange={(value) =>
                    updateConfig({ bandwidth_threshold_medium_kbps: parseInt(value) || 3000 })
                  }
                  classNames={{
                    input: 'bg-[color:var(--color-bg)]',
                  }}
                  endContent="Kbps"
                />
              </div>

              {/* High Quality Threshold */}
              <div>
                <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                  {t('adaptive.highThreshold', 'High Quality')} ≤
                </label>
                <Input
                  type="number"
                  min="0"
                  step="100"
                  value={String(config.bandwidth_threshold_high_kbps ?? 6000)}
                  onValueChange={(value) =>
                    updateConfig({ bandwidth_threshold_high_kbps: parseInt(value) || 6000 })
                  }
                  classNames={{
                    input: 'bg-[color:var(--color-bg)]',
                  }}
                  endContent="Kbps"
                />
              </div>

              {/* Ultra Quality Threshold */}
              <div>
                <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                  {t('adaptive.ultraThreshold', 'Ultra Quality')} ≤
                </label>
                <Input
                  type="number"
                  min="0"
                  step="100"
                  value={String(config.bandwidth_threshold_ultra_kbps ?? 8000)}
                  onValueChange={(value) =>
                    updateConfig({ bandwidth_threshold_ultra_kbps: parseInt(value) || 8000 })
                  }
                  classNames={{
                    input: 'bg-[color:var(--color-bg)]',
                  }}
                  endContent="Kbps"
                />
              </div>
            </div>
          </div>

          {/* Adaptation Settings */}
          <div className="mb-6 space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]">
              <Settings size={16} />
              <span>{t('adaptive.adaptationSettings', 'Настройки адаптации')}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-xl bg-[color:var(--color-bg)] border border-[color:var(--color-border)]">
              {/* Adaptation Interval */}
              <div>
                <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                  {t('adaptive.interval', 'Интервал проверки')}
                </label>
                <Input
                  type="number"
                  min="5"
                  max="300"
                  step="5"
                  value={String(config.adaptation_interval_seconds ?? 30)}
                  onValueChange={(value) =>
                    updateConfig({ adaptation_interval_seconds: parseInt(value) || 30 })
                  }
                  classNames={{
                    input: 'bg-[color:var(--color-bg)]',
                  }}
                  endContent="сек"
                  description="5-300 сек"
                />
              </div>

              {/* Smoothing Factor */}
              <div>
                <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                  {t('adaptive.smoothing', 'Коэфф. сглаживания')}
                </label>
                <Input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={String(config.bandwidth_smoothing_factor ?? 0.3)}
                  onValueChange={(value) =>
                    updateConfig({ bandwidth_smoothing_factor: parseFloat(value) || 0.3 })
                  }
                  classNames={{
                    input: 'bg-[color:var(--color-bg)]',
                  }}
                  description="0-1"
                />
              </div>

              {/* Consecutive Measurements */}
              <div>
                <label className="block text-xs text-[color:var(--color-text-secondary)] mb-2">
                  {t('adaptive.measurements', 'Измерений для смены')}
                </label>
                <Input
                  type="number"
                  min="1"
                  max="10"
                  step="1"
                  value={String(config.consecutive_measurements_required ?? 2)}
                  onValueChange={(value) =>
                    updateConfig({ consecutive_measurements_required: parseInt(value) || 2 })
                  }
                  classNames={{
                    input: 'bg-[color:var(--color-bg)]',
                  }}
                  description="1-10"
                />
              </div>
            </div>
          </div>

          {/* Device Rules */}
          <div className="mb-6 space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]">
              <Smartphone size={16} />
              <span>{t('adaptive.deviceRules', 'Правила для устройств')}</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl bg-[color:var(--color-bg)] border border-[color:var(--color-border)]">
              {deviceTypes.map((deviceType) => {
                const deviceRule = config.device_rules?.[deviceType];
                return (
                  <div key={deviceType} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-[color:var(--color-text)]">
                        {deviceLabels[deviceType]}
                      </span>
                      {deviceRule && (
                        <Chip size="sm" color={getQualityColor(deviceRule.max_quality)} variant="flat">
                          ≤ {deviceRule.max_quality.toUpperCase()}
                        </Chip>
                      )}
                    </div>
                    <p className="text-xs text-[color:var(--color-text-muted)]">
                      {t('adaptive.multiplier', 'Множитель')}: {deviceRule?.bandwidth_multiplier ?? 1.0}x
                    </p>
                  </div>
                );
              })}
            </div>
            <p className="text-xs text-[color:var(--color-text-muted)]">
              {t('adaptive.deviceRulesNote', 'Правила устройств настраиваются через API')}
            </p>
          </div>

          {/* Monitoring Settings */}
          <div className="mb-6 space-y-4">
            <div className="flex items-center gap-2 text-sm font-medium text-[color:var(--color-text-secondary)]">
              <Monitor size={16} />
              <span>{t('adaptive.monitoring', 'Мониторинг')}</span>
            </div>

            <div className="space-y-3 p-4 rounded-xl bg-[color:var(--color-bg)] border border-[color:var(--color-border)]">
              <Switch
                isSelected={config.enable_bandwidth_monitoring ?? true}
                onValueChange={(checked) => updateConfig({ enable_bandwidth_monitoring: checked })}
                color="primary"
              >
                <span className="text-sm text-[color:var(--color-text)]">
                  {t('adaptive.bandwidthMonitoring', 'Мониторинг пропускной способности')}
                </span>
              </Switch>

              <Switch
                isSelected={config.enable_quality_logging ?? true}
                onValueChange={(checked) => updateConfig({ enable_quality_logging: checked })}
                color="primary"
              >
                <span className="text-sm text-[color:var(--color-text)]">
                  {t('adaptive.qualityLogging', 'Логирование изменений качества')}
                </span>
              </Switch>
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end gap-3">
            <Button
              color="primary"
              onPress={handleSave}
              isDisabled={!hasChanges || saving}
              startContent={<Save size={18} />}
              className="font-medium"
            >
              {saving ? t('adaptive.saving', 'Сохранение...') : t('adaptive.save', 'Сохранить настройки')}
            </Button>
          </div>

          {/* Info Box */}
          <div className="mt-6 p-4 rounded-xl bg-primary/5 border border-primary/10 flex gap-3">
            <Info size={20} className="text-primary flex-shrink-0 mt-0.5" />
            <div className="text-sm text-[color:var(--color-text-secondary)]">
              <p className="font-medium text-[color:var(--color-text)] mb-1">
                {t('adaptive.infoTitle', 'Как это работает')}
              </p>
              <p>
                {t('adaptive.infoText',
                  'Система автоматически переключает качество на основе текущей пропускной способности. ' +
                  'Пороги определяют минимальную скорость для каждого качества. ' +
                  'Гистерезис предотвращает частые переключения.'
                )}
              </p>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
};
