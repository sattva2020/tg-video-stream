/**
 * ScheduleOptimizationModal — Модальное окно для оптимизации расписания.
 *
 * Функции:
 * - Предпросмотр оптимизации расписания
 * - Настройка параметров оптимизации
 * - Отображение метрик (покрытие, вовлеченность, разнообразие)
 * - Применение предложенных изменений
 */

import React, { useState, useMemo, useCallback, useId } from 'react';
import {
  Sparkles,
  TrendingUp,
  Clock,
  AlertCircle,
  CheckCircle2,
  Loader2,
  BarChart3,
  Settings,
  Calendar,
  Music,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Slider,
  Switch,
  Divider,
  Chip,
  Card,
  CardBody,
  Tooltip,
} from '@heroui/react';
import { usePreviewOptimization } from '../../hooks/useScheduleAI';
import type {
  ScheduleOptimizationRequest,
  OptimizationParameters,
  ScheduleOptimizationResponse,
  ScheduleSuggestion,
} from '../../api/scheduleAI';

// ==================== Types ====================

interface ScheduleOptimizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  channelId: string;
  startDate: string;
  endDate: string;
  onOptimizationApplied?: () => void;
}

interface OptimizationSettings {
  prioritizeCoverage: boolean;
  prioritizeVariety: boolean;
  prioritizePeakHours: boolean;
  maximizeEngagement: boolean;
  avoidConflicts: boolean;
  weights: {
    coverage: number;
    engagement: number;
    variety: number;
    conflicts: number;
    peakHours: number;
  };
}

// ==================== Constants ====================

const DEFAULT_WEIGHTS = {
  coverage: 25,
  engagement: 30,
  variety: 20,
  conflicts: 15,
  peakHours: 10,
};

// ==================== Helper Functions ====================

function formatMetricValue(value: number): string {
  return Math.round(value * 100) / 100;
}

function formatTime(time: string): string {
  const [hours, minutes] = time.split(':');
  return `${hours}:${minutes}`;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

// ==================== Sub-Components ====================

const MetricsCard: React.FC<{
  label: string;
  value: number | string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'violet' | 'orange' | 'cyan';
}> = ({ label, value, icon, color }) => {
  const colorClasses = {
    blue: 'text-blue-500 bg-blue-500/10 border-blue-500/20',
    green: 'text-green-500 bg-green-500/10 border-green-500/20',
    violet: 'text-violet-500 bg-violet-500/10 border-violet-500/20',
    orange: 'text-orange-500 bg-orange-500/10 border-orange-500/20',
    cyan: 'text-cyan-500 bg-cyan-500/10 border-cyan-500/20',
  };

  return (
    <div className={`p-3 rounded-lg border ${colorClasses[color]}`}>
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <p className="text-xs text-[color:var(--color-text-muted)]">{label}</p>
      </div>
      <p className="text-xl font-bold text-[color:var(--color-text)]">{value}</p>
    </div>
  );
};

const SuggestionItem: React.FC<{
  suggestion: ScheduleSuggestion;
}> = ({ suggestion }) => {
  const { t } = useTranslation();

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="p-3 rounded-lg bg-[color:var(--color-surface)] border border-[color:var(--color-border)] hover:border-[color:var(--color-accent)] transition-colors"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <Calendar className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
            <span className="text-sm font-medium text-[color:var(--color-text)]">
              {formatDate(suggestion.date)}
            </span>
            <Clock className="w-4 h-4 text-[color:var(--color-text-muted)] flex-shrink-0" />
            <span className="text-sm text-[color:var(--color-text)]">
              {formatTime(suggestion.start_time)} - {formatTime(suggestion.end_time)}
            </span>
          </div>

          {suggestion.playlist_name && (
            <div className="flex items-center gap-2 mb-2">
              <Music className="w-4 h-4 text-[color:var(--color-accent)] flex-shrink-0" />
              <span className="text-sm text-[color:var(--color-text)]">{suggestion.playlist_name}</span>
            </div>
          )}

          <p className="text-xs text-[color:var(--color-text-muted)]">{suggestion.reason}</p>
        </div>

        <Chip size="sm" variant="flat" color="primary">
          <span className="text-xs">{t('schedule.optimization.priority', 'Приоритет')}: {suggestion.priority}</span>
        </Chip>
      </div>
    </motion.div>
  );
};

// ==================== Main Component ====================

export const ScheduleOptimizationModal: React.FC<ScheduleOptimizationModalProps> = ({
  isOpen,
  onClose,
  channelId,
  startDate,
  endDate,
  onOptimizationApplied,
}) => {
  const { t } = useTranslation();
  const flatControlClassName =
    'text-[color:var(--color-text)] bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-hover)] hover:border-[color:var(--color-border-strong)] transition-colors';
  const baseId = useId();

  // State
  const [settings, setSettings] = useState<OptimizationSettings>({
    prioritizeCoverage: true,
    prioritizeVariety: true,
    prioritizePeakHours: true,
    maximizeEngagement: true,
    avoidConflicts: true,
    weights: DEFAULT_WEIGHTS,
  });

  const [previewStatus, setPreviewStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [optimizationResult, setOptimizationResult] = useState<ScheduleOptimizationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Mutation
  const previewMutation = usePreviewOptimization();

  // Computed values
  const totalWeight = useMemo(() => {
    return Object.values(settings.weights).reduce((sum, val) => sum + val, 0);
  }, [settings.weights]);

  const weightsAreValid = useMemo(() => {
    return totalWeight === 100;
  }, [totalWeight]);

  // Build optimization parameters
  const buildOptimizationParameters = useCallback((): OptimizationParameters => {
    return {
      prioritize_coverage: settings.prioritizeCoverage,
      prioritize_variety: settings.prioritizeVariety,
      prioritize_peak_hours: settings.prioritizePeakHours,
      maximize_engagement: settings.maximizeEngagement,
      avoid_conflicts: settings.avoidConflicts,
      weights: {
        coverage: settings.weights.coverage / 100,
        engagement: settings.weights.engagement / 100,
        variety: settings.weights.variety / 100,
        conflicts: settings.weights.conflicts / 100,
        peak_hours: settings.weights.peakHours / 100,
      },
    };
  }, [settings]);

  // Handlers
  const handlePreview = async () => {
    setPreviewStatus('loading');
    setError(null);
    setOptimizationResult(null);

    try {
      const request: ScheduleOptimizationRequest = {
        channel_id: channelId,
        start_date: startDate,
        end_date: endDate,
        parameters: buildOptimizationParameters(),
      };

      const result = await previewMutation.mutateAsync(request);
      setOptimizationResult(result);
      setPreviewStatus('success');
    } catch (err: any) {
      setPreviewStatus('error');
      setError(err.message || t('schedule.optimization.previewError', 'Ошибка оптимизации'));
    }
  };

  const handleApply = () => {
    // Apply optimization (this would typically call another API endpoint)
    if (onOptimizationApplied) {
      onOptimizationApplied();
    }
    onClose();
  };

  const handleWeightChange = (key: keyof OptimizationSettings['weights'], value: number) => {
    setSettings(prev => ({
      ...prev,
      weights: {
        ...prev.weights,
        [key]: value,
      },
    }));
  };

  const handleToggleChange = (key: keyof Omit<OptimizationSettings, 'weights'>) => {
    setSettings(prev => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  // Reset state when modal opens/closes
  React.useEffect(() => {
    if (!isOpen) {
      setPreviewStatus('idle');
      setOptimizationResult(null);
      setError(null);
    }
  }, [isOpen]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="3xl"
      scrollBehavior="inside"
      backdrop="blur"
      classNames={{
        backdrop: "bg-black/50 backdrop-blur-sm",
        base: "bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-xl shadow-black/10",
        header: "border-b border-[color:var(--color-border)]",
        body: "py-6",
        footer: "border-t border-[color:var(--color-border)]",
      }}
    >
      <ModalContent>
        <ModalHeader className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 shadow-sm shadow-black/10">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[color:var(--color-text)]">
              {t('schedule.optimization.title', 'Оптимизация расписания')}
            </h2>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('schedule.optimization.description', 'AI-анализ и предложения по улучшению расписания')}
            </p>
          </div>
        </ModalHeader>

        <ModalBody className="gap-6">
          {/* Date Range Info */}
          <div className="p-3 rounded-lg bg-[color:var(--color-surface)] border border-[color:var(--color-border)]">
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="w-4 h-4 text-[color:var(--color-text-muted)]" />
              <span className="text-[color:var(--color-text-muted)]">
                {t('schedule.optimization.dateRange', 'Период')}:
              </span>
              <span className="font-medium text-[color:var(--color-text)]">
                {formatDate(startDate)} - {formatDate(endDate)}
              </span>
            </div>
          </div>

          {/* Optimization Settings */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-[color:var(--color-text-muted)]" />
              <h3 className="text-base font-semibold text-[color:var(--color-text)]">
                {t('schedule.optimization.settings', 'Настройки оптимизации')}
              </h3>
            </div>

            {/* Toggles */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Switch
                isSelected={settings.prioritizeCoverage}
                onValueChange={() => handleToggleChange('prioritizeCoverage')}
                classNames={{
                  wrapper: 'group-data-[selected=true]:bg-[color:var(--color-accent)]',
                }}
              >
                <span className="text-sm text-[color:var(--color-text)]">
                  {t('schedule.optimization.prioritizeCoverage', 'Максимизировать покрытие')}
                </span>
              </Switch>

              <Switch
                isSelected={settings.maximizeEngagement}
                onValueChange={() => handleToggleChange('maximizeEngagement')}
                classNames={{
                  wrapper: 'group-data-[selected=true]:bg-[color:var(--color-accent)]',
                }}
              >
                <span className="text-sm text-[color:var(--color-text)]">
                  {t('schedule.optimization.maximizeEngagement', 'Максимизировать вовлеченность')}
                </span>
              </Switch>

              <Switch
                isSelected={settings.prioritizeVariety}
                onValueChange={() => handleToggleChange('prioritizeVariety')}
                classNames={{
                  wrapper: 'group-data-[selected=true]:bg-[color:var(--color-accent)]',
                }}
              >
                <span className="text-sm text-[color:var(--color-text)]">
                  {t('schedule.optimization.prioritizeVariety', 'Обеспечить разнообразие')}
                </span>
              </Switch>

              <Switch
                isSelected={settings.avoidConflicts}
                onValueChange={() => handleToggleChange('avoidConflicts')}
                classNames={{
                  wrapper: 'group-data-[selected=true]:bg-[color:var(--color-accent)]',
                }}
              >
                <span className="text-sm text-[color:var(--color-text)]">
                  {t('schedule.optimization.avoidConflicts', 'Избегать конфликтов')}
                </span>
              </Switch>

              <Switch
                isSelected={settings.prioritizePeakHours}
                onValueChange={() => handleToggleChange('prioritizePeakHours')}
                classNames={{
                  wrapper: 'group-data-[selected=true]:bg-[color:var(--color-accent)]',
                }}
              >
                <span className="text-sm text-[color:var(--color-text)]">
                  {t('schedule.optimization.prioritizePeakHours', 'Приоритет пиковых часов')}
                </span>
              </Switch>
            </div>

            <Divider className="bg-[color:var(--color-border)]" />

            {/* Weights */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-[color:var(--color-text)]">
                  {t('schedule.optimization.weights', 'Веса оптимизации')}
                </span>
                {!weightsAreValid && (
                  <Chip size="sm" color="warning" variant="flat">
                    {t('schedule.optimization.totalWeight', 'Сумма: {total}%', { total: totalWeight })}
                  </Chip>
                )}
              </div>

              <div className="space-y-3">
                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-xs text-[color:var(--color-text-muted)]">
                      {t('schedule.optimization.coverage', 'Покрытие')}
                    </label>
                    <span className="text-xs text-[color:var(--color-text)]">{settings.weights.coverage}%</span>
                  </div>
                  <Slider
                    size="sm"
                    value={settings.weights.coverage}
                    onChange={(value) => handleWeightChange('coverage', value as number)}
                    minValue={0}
                    maxValue={100}
                    step={5}
                    classNames={{
                      track: 'border-[color:var(--color-border)]',
                      filler: 'bg-blue-500',
                      thumb: 'bg-blue-500',
                    }}
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-xs text-[color:var(--color-text-muted)]">
                      {t('schedule.optimization.engagement', 'Вовлеченность')}
                    </label>
                    <span className="text-xs text-[color:var(--color-text)]">{settings.weights.engagement}%</span>
                  </div>
                  <Slider
                    size="sm"
                    value={settings.weights.engagement}
                    onChange={(value) => handleWeightChange('engagement', value as number)}
                    minValue={0}
                    maxValue={100}
                    step={5}
                    classNames={{
                      track: 'border-[color:var(--color-border)]',
                      filler: 'bg-green-500',
                      thumb: 'bg-green-500',
                    }}
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-xs text-[color:var(--color-text-muted)]">
                      {t('schedule.optimization.variety', 'Разнообразие')}
                    </label>
                    <span className="text-xs text-[color:var(--color-text)]">{settings.weights.variety}%</span>
                  </div>
                  <Slider
                    size="sm"
                    value={settings.weights.variety}
                    onChange={(value) => handleWeightChange('variety', value as number)}
                    minValue={0}
                    maxValue={100}
                    step={5}
                    classNames={{
                      track: 'border-[color:var(--color-border)]',
                      filler: 'bg-violet-500',
                      thumb: 'bg-violet-500',
                    }}
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-xs text-[color:var(--color-text-muted)]">
                      {t('schedule.optimization.conflicts', 'Конфликты')}
                    </label>
                    <span className="text-xs text-[color:var(--color-text)]">{settings.weights.conflicts}%</span>
                  </div>
                  <Slider
                    size="sm"
                    value={settings.weights.conflicts}
                    onChange={(value) => handleWeightChange('conflicts', value as number)}
                    minValue={0}
                    maxValue={100}
                    step={5}
                    classNames={{
                      track: 'border-[color:var(--color-border)]',
                      filler: 'bg-orange-500',
                      thumb: 'bg-orange-500',
                    }}
                  />
                </div>

                <div>
                  <div className="flex justify-between mb-1">
                    <label className="text-xs text-[color:var(--color-text-muted)]">
                      {t('schedule.optimization.peakHours', 'Пиковые часы')}
                    </label>
                    <span className="text-xs text-[color:var(--color-text)]">{settings.weights.peakHours}%</span>
                  </div>
                  <Slider
                    size="sm"
                    value={settings.weights.peakHours}
                    onChange={(value) => handleWeightChange('peakHours', value as number)}
                    minValue={0}
                    maxValue={100}
                    step={5}
                    classNames={{
                      track: 'border-[color:var(--color-border)]',
                      filler: 'bg-cyan-500',
                      thumb: 'bg-cyan-500',
                    }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Preview Status */}
          <AnimatePresence>
            {previewStatus === 'loading' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex items-center gap-3 p-4 rounded-lg bg-violet-500/10 border border-violet-500/30"
              >
                <Loader2 className="w-5 h-5 text-violet-500 animate-spin" />
                <div className="flex-1">
                  <p className="font-medium text-violet-500">
                    {t('schedule.optimization.analyzing', 'Анализ расписания...')}
                  </p>
                  <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
                    {t('schedule.optimization.analyzingDesc', 'Это может занять несколько секунд')}
                  </p>
                </div>
              </motion.div>
            )}

            {previewStatus === 'error' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex items-start gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/30"
              >
                <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="font-medium text-red-500">
                    {t('schedule.optimization.error', 'Ошибка оптимизации')}
                  </p>
                  <p className="text-sm text-[color:var(--color-text-muted)] mt-1">{error}</p>
                </div>
              </motion.div>
            )}

            {previewStatus === 'success' && optimizationResult && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-4"
              >
                {/* Metrics */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-[color:var(--color-text-muted)]" />
                    <h3 className="text-base font-semibold text-[color:var(--color-text)]">
                      {t('schedule.optimization.metrics', 'Метрики')}
                    </h3>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                    <MetricsCard
                      label={t('schedule.optimization.coverage', 'Покрытие')}
                      value={`${formatMetricValue(optimizationResult.metrics.coverage * 100)}%`}
                      icon={<TrendingUp className="w-4 h-4" />}
                      color="blue"
                    />
                    <MetricsCard
                      label={t('schedule.optimization.engagement', 'Вовлеченность')}
                      value={formatMetricValue(optimizationResult.metrics.engagement_score)}
                      icon={<Sparkles className="w-4 h-4" />}
                      color="green"
                    />
                    <MetricsCard
                      label={t('schedule.optimization.variety', 'Разнообразие')}
                      value={formatMetricValue(optimizationResult.metrics.variety_score)}
                      icon={<Music className="w-4 h-4" />}
                      color="violet"
                    />
                    <MetricsCard
                      label={t('schedule.optimization.conflicts', 'Конфликты')}
                      value={optimizationResult.metrics.conflicts_count}
                      icon={<AlertCircle className="w-4 h-4" />}
                      color="orange"
                    />
                    <MetricsCard
                      label={t('schedule.optimization.peakHours', 'Пиковые часы')}
                      value={`${formatMetricValue(optimizationResult.metrics.peak_hours_coverage * 100)}%`}
                      icon={<Clock className="w-4 h-4" />}
                      color="cyan"
                    />
                  </div>
                </div>

                {/* Warnings */}
                {optimizationResult.warnings && optimizationResult.warnings.length > 0 && (
                  <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertCircle className="w-4 h-4 text-amber-500" />
                      <p className="text-sm font-medium text-amber-500">
                        {t('schedule.optimization.warnings', 'Предупреждения:')}
                      </p>
                    </div>
                    <ul className="text-sm text-[color:var(--color-text-muted)] space-y-1">
                      {optimizationResult.warnings.map((warning, i) => (
                        <li key={i}>• {warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Suggestions */}
                {optimizationResult.suggestions && optimizationResult.suggestions.length > 0 && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5 text-[color:var(--color-text-muted)]" />
                        <h3 className="text-base font-semibold text-[color:var(--color-text)]">
                          {t('schedule.optimization.suggestions', 'Предложения ({count})', {
                            count: optimizationResult.suggestions.length,
                          })}
                        </h3>
                      </div>
                    </div>

                    <div className="space-y-2 max-h-64 overflow-y-auto pr-2">
                      {optimizationResult.suggestions.map((suggestion, index) => (
                        <SuggestionItem key={index} suggestion={suggestion} />
                      ))}
                    </div>
                  </div>
                )}

                {optimizationResult.suggestions.length === 0 && (
                  <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 text-center">
                    <CheckCircle2 className="w-8 h-8 text-green-500 mx-auto mb-2" />
                    <p className="text-sm text-green-500">
                      {t('schedule.optimization.noSuggestions', 'Расписание уже оптимизировано!')}
                    </p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </ModalBody>

        <ModalFooter>
          <Button variant="flat" className={flatControlClassName} onPress={onClose}>
            {t('common.close', 'Закрыть')}
          </Button>
          <Button
            color="primary"
            onPress={handlePreview}
            isLoading={previewMutation.isPending || previewStatus === 'loading'}
            isDisabled={!weightsAreValid}
            startContent={!previewMutation.isPending && previewStatus !== 'loading' && <Sparkles className="w-4 h-4" />}
          >
            {previewStatus === 'success'
              ? t('schedule.optimization.refresh', 'Обновить')
              : t('schedule.optimization.preview', 'Предпросмотр')}
          </Button>
          {previewStatus === 'success' && optimizationResult && optimizationResult.suggestions.length > 0 && (
            <Button
              color="success"
              onPress={handleApply}
              startContent={<CheckCircle2 className="w-4 h-4" />}
            >
              {t('schedule.optimization.apply', 'Применить')}
            </Button>
          )}
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default ScheduleOptimizationModal;
