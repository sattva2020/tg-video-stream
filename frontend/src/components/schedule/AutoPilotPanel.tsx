/**
 * AutoPilotPanel — Панель автоматического генератора расписаний.
 *
 * Функции:
 * - Генерация расписания одним кликом
 * - Использование AI-рекомендаций
 * - Применение шаблонов
 * - Разрешение конфликтов
 * - Предпросмотр перед применением
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Wand2,
  Calendar,
  Sparkles,
  Settings,
  Eye,
  Play,
  Clock,
  CheckCircle2,
  AlertCircle,
  Info,
  Loader2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Card,
  CardHeader,
  CardBody,
  Input,
  Switch,
  Slider,
  Select,
  SelectItem,
  Divider,
  Chip,
  Tooltip,
} from '@heroui/react';
import {
  useGenerateAutoPilotSchedule,
  usePreviewAutoPilotSchedule,
} from '../../hooks/useScheduleAI';
import type { AutoPilotRequest } from '../../api/scheduleAI';

// ==================== Types ====================

interface AutoPilotPanelProps {
  channelId: string;
  onScheduleGenerated?: () => void;
}

interface GenerationSettings {
  useAi: boolean;
  maxDailyHours: number;
  resolveConflicts: boolean;
}

// ==================== Constants ====================

const PRESET_RANGES = [
  {
    key: 'week',
    label: 'Неделя',
    days: 7,
  },
  {
    key: 'twoWeeks',
    label: '2 недели',
    days: 14,
  },
  {
    key: 'month',
    label: 'Месяц',
    days: 30,
  },
];

// ==================== Helper Functions ====================

function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

function getRangeDates(presetDays: number | null, customStart: string, customEnd: string): { start: string; end: string } {
  if (presetDays) {
    const start = new Date();
    const end = addDays(start, presetDays);
    return { start: formatDate(start), end: formatDate(end) };
  }
  return { start: customStart, end: customEnd };
}

// ==================== Sub-Components ====================

const StatusDisplay: React.FC<{
  status: 'idle' | 'previewing' | 'generating' | 'success' | 'error';
  result?: any;
  error?: string;
}> = ({ status, result, error }) => {
  const { t } = useTranslation();

  if (status === 'idle') {
    return null;
  }

  if (status === 'previewing') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3 p-4 rounded-lg bg-blue-500/10 border border-blue-500/30"
      >
        <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
        <div className="flex-1">
          <p className="font-medium text-blue-500">
            {t('schedule.autoPilot.previewing', 'Создание предпросмотра...')}
          </p>
        </div>
      </motion.div>
    );
  }

  if (status === 'generating') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3 p-4 rounded-lg bg-violet-500/10 border border-violet-500/30"
      >
        <Loader2 className="w-5 h-5 text-violet-500 animate-spin" />
        <div className="flex-1">
          <p className="font-medium text-violet-500">
            {t('schedule.autoPilot.generating', 'Генерация расписания...')}
          </p>
          <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
            {t('schedule.autoPilot.generatingDesc', 'Это может занять несколько минут')}
          </p>
        </div>
      </motion.div>
    );
  }

  if (status === 'success' && result) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-4 rounded-lg bg-green-500/10 border border-green-500/30"
      >
        <div className="flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-500 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium text-green-500">
              {t('schedule.autoPilot.success', 'Расписание успешно создано!')}
            </p>
            <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="text-center">
                <p className="text-2xl font-bold text-[color:var(--color-text)]">
                  {result.slots_created}
                </p>
                <p className="text-xs text-[color:var(--color-text-muted)]">
                  {t('schedule.autoPilot.slotsCreated', 'Слотов создано')}
                </p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-[color:var(--color-text)]">
                  {result.gaps_filled}
                </p>
                <p className="text-xs text-[color:var(--color-text-muted)]">
                  {t('schedule.autoPilot.gapsFilled', 'Пробелов заполнено')}
                </p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-[color:var(--color-text)]">
                  {result.conflicts_resolved}
                </p>
                <p className="text-xs text-[color:var(--color-text-muted)]">
                  {t('schedule.autoPilot.conflictsResolved', 'Конфликтов решено')}
                </p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-[color:var(--color-text)]">
                  {result.status}
                </p>
                <p className="text-xs text-[color:var(--color-text-muted)]">
                  {t('schedule.autoPilot.status', 'Статус')}
                </p>
              </div>
            </div>
            {result.warnings && result.warnings.length > 0 && (
              <div className="mt-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <p className="text-sm font-medium text-amber-500 mb-2">
                  {t('schedule.autoPilot.warnings', 'Предупреждения:')}
                </p>
                <ul className="text-sm text-[color:var(--color-text-muted)] space-y-1">
                  {result.warnings.map((warning: string, i: number) => (
                    <li key={i}>• {warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    );
  }

  if (status === 'error') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/30"
      >
        <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
        <div className="flex-1">
          <p className="font-medium text-red-500">
            {t('schedule.autoPilot.error', 'Ошибка генерации')}
          </p>
          <p className="text-sm text-[color:var(--color-text-muted)] mt-1">{error}</p>
        </div>
      </motion.div>
    );
  }

  return null;
};

// ==================== Main Component ====================

export const AutoPilotPanel: React.FC<AutoPilotPanelProps> = ({
  channelId,
  onScheduleGenerated,
}) => {
  const { t } = useTranslation();

  // State
  const [selectedPreset, setSelectedPreset] = useState<string | null>('week');
  const [customStartDate, setCustomStartDate] = useState(formatDate(new Date()));
  const [customEndDate, setCustomEndDate] = useState(formatDate(addDays(new Date(), 7)));
  const [settings, setSettings] = useState<GenerationSettings>({
    useAi: true,
    maxDailyHours: 18,
    resolveConflicts: true,
  });
  const [status, setStatus] = useState<'idle' | 'previewing' | 'generating' | 'success' | 'error'>('idle');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Mutations
  const generateMutation = useGenerateAutoPilotSchedule();
  const previewMutation = usePreviewAutoPilotSchedule();

  // Computed values
  const rangeDates = useMemo(() => {
    const days = selectedPreset
      ? PRESET_RANGES.find(r => r.key === selectedPreset)?.days || null
      : null;
    return getRangeDates(days, customStartDate, customEndDate);
  }, [selectedPreset, customStartDate, customEndDate]);

  const flatControlClassName =
    'text-[color:var(--color-text)] bg-[color:var(--color-surface-muted)] border border-[color:var(--color-outline)] hover:bg-[color:var(--color-panel)] hover:border-[color:var(--color-accent)] transition-colors';

  // Handlers
  const handlePreview = async () => {
    setStatus('previewing');
    setError(null);
    setResult(null);

    try {
      const request: AutoPilotRequest = {
        channel_id: channelId,
        date_range: rangeDates,
        use_ai_recommendations: settings.useAi,
        max_daily_hours: settings.maxDailyHours,
        resolve_conflicts: settings.resolveConflicts,
      };

      await previewMutation.mutateAsync(request);
      setStatus('idle');
    } catch (err: any) {
      setStatus('error');
      setError(err.message || t('schedule.autoPilot.previewError', 'Ошибка создания предпросмотра'));
    }
  };

  const handleGenerate = async () => {
    setStatus('generating');
    setError(null);
    setResult(null);

    try {
      const request: AutoPilotRequest = {
        channel_id: channelId,
        date_range: rangeDates,
        use_ai_recommendations: settings.useAi,
        max_daily_hours: settings.maxDailyHours,
        resolve_conflicts: settings.resolveConflicts,
      };

      const response = await generateMutation.mutateAsync(request);
      setResult(response);
      setStatus('success');
      onScheduleGenerated?.();
    } catch (err: any) {
      setStatus('error');
      setError(err.message || t('schedule.autoPilot.generateError', 'Ошибка генерации расписания'));
    }
  };

  const isProcessing = status === 'previewing' || status === 'generating';

  return (
    <Card className="w-full bg-[color:var(--color-panel)] border border-[color:var(--color-border)] shadow-md shadow-black/5">
      <CardHeader className="flex gap-3">
        <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
          <Wand2 className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-bold text-[color:var(--color-text)]">
            {t('schedule.autoPilot.title', 'Автопилот')}
          </h2>
          <p className="text-sm text-[color:var(--color-text-muted)]">
            {t('schedule.autoPilot.description', 'Автоматическая генерация расписания')}
          </p>
        </div>
      </CardHeader>

      <Divider className="bg-[color:var(--color-border)]" />

      <CardBody className="space-y-6">
        {/* Date Range Selection */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Calendar className="w-4 h-4 text-[color:var(--color-text-muted)]" />
            <p className="text-sm font-semibold text-[color:var(--color-text)]">
              {t('schedule.autoPilot.dateRange', 'Период расписания')}
            </p>
          </div>

          {/* Preset Buttons */}
          <div className="flex flex-wrap gap-2 mb-3">
            {PRESET_RANGES.map((preset) => (
              <Chip
                key={preset.key}
                variant={selectedPreset === preset.key ? 'solid' : 'bordered'}
                color={selectedPreset === preset.key ? 'primary' : 'default'}
                className="cursor-pointer"
                onClick={() => setSelectedPreset(preset.key)}
              >
                {preset.label}
              </Chip>
            ))}
            <Chip
              variant={selectedPreset === null ? 'solid' : 'bordered'}
              color={selectedPreset === null ? 'primary' : 'default'}
              className="cursor-pointer"
              onClick={() => setSelectedPreset(null)}
            >
              {t('schedule.autoPilot.custom', 'Настраиваемый')}
            </Chip>
          </div>

          {/* Custom Date Inputs */}
          <AnimatePresence>
            {selectedPreset === null && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="grid grid-cols-2 gap-3"
              >
                <div>
                  <label className="text-xs text-[color:var(--color-text-muted)] mb-1 block">
                    {t('schedule.autoPilot.startDate', 'Начальная дата')}
                  </label>
                  <Input
                    type="date"
                    value={customStartDate}
                    onValueChange={setCustomStartDate}
                    classNames={{
                      input: 'text-[color:var(--color-text)]',
                    }}
                  />
                </div>
                <div>
                  <label className="text-xs text-[color:var(--color-text-muted)] mb-1 block">
                    {t('schedule.autoPilot.endDate', 'Конечная дата')}
                  </label>
                  <Input
                    type="date"
                    value={customEndDate}
                    onValueChange={setCustomEndDate}
                    classNames={{
                      input: 'text-[color:var(--color-text)]',
                    }}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Selected Range Display */}
          <div className="mt-3 p-3 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('schedule.autoPilot.selectedRange', 'Выбранный период')}:{' '}
              <span className="font-semibold text-[color:var(--color-text)]">
                {rangeDates.start} - {rangeDates.end}
              </span>
            </p>
          </div>
        </div>

        {/* AI Settings */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-4 h-4 text-[color:var(--color-text-muted)]" />
            <p className="text-sm font-semibold text-[color:var(--color-text)]">
              {t('schedule.autoPilot.aiSettings', 'Настройки AI')}
            </p>
          </div>

          <div className="space-y-3">
            {/* Use AI Recommendations */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
              <div className="flex-1">
                <p className="text-sm font-medium text-[color:var(--color-text)]">
                  {t('schedule.autoPilot.useAi', 'Использовать AI-рекомендации')}
                </p>
                <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                  {t('schedule.autoPilot.useAiDesc', 'Определять лучшее время для контента на основе данных')}
                </p>
              </div>
              <Switch
                isSelected={settings.useAi}
                onValueChange={(value) => setSettings(prev => ({ ...prev, useAi: value }))}
                color="primary"
                classNames={{
                  wrapper: 'group-data-[selected=true]:bg-primary',
                }}
              />
            </div>

            {/* Max Daily Hours */}
            <div className="p-3 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium text-[color:var(--color-text)]">
                  {t('schedule.autoPilot.maxDailyHours', 'Максимум часов в день')}
                </p>
                <Chip size="sm" variant="flat">
                  {settings.maxDailyHours}h
                </Chip>
              </div>
              <Slider
                size="sm"
                step={1}
                minValue={1}
                maxValue={24}
                value={settings.maxDailyHours}
                onChangeValue={(value) => setSettings(prev => ({ ...prev, maxDailyHours: value as number }))}
                className="max-w-full"
                color="primary"
                classNames={{
                  track: 'border-[color:var(--color-border)]',
                  filler: 'bg-primary',
                }}
              />
              <p className="text-xs text-[color:var(--color-text-muted)] mt-2">
                {t('schedule.autoPilot.maxDailyHoursDesc', 'Ограничение на количество часов трансляций в день')}
              </p>
            </div>

            {/* Resolve Conflicts */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
              <div className="flex-1">
                <p className="text-sm font-medium text-[color:var(--color-text)]">
                  {t('schedule.autoPilot.resolveConflicts', 'Разрешать конфликты')}
                </p>
                <p className="text-xs text-[color:var(--color-text-muted)] mt-1">
                  {t('schedule.autoPilot.resolveConflictsDesc', 'Автоматически разрешать пересечения слотов')}
                </p>
              </div>
              <Switch
                isSelected={settings.resolveConflicts}
                onValueChange={(value) => setSettings(prev => ({ ...prev, resolveConflicts: value }))}
                color="primary"
                classNames={{
                  wrapper: 'group-data-[selected=true]:bg-primary',
                }}
              />
            </div>
          </div>
        </div>

        {/* Status Display */}
        <StatusDisplay status={status} result={result} error={error || undefined} />

        {/* Actions */}
        <div className="flex gap-3">
          <Button
            className={flatControlClassName}
            onPress={handlePreview}
            isDisabled={isProcessing}
            startContent={<Eye className="w-4 h-4" />}
            variant="flat"
          >
            {t('schedule.autoPilot.preview', 'Предпросмотр')}
          </Button>
          <Button
            color="primary"
            onPress={handleGenerate}
            isDisabled={isProcessing}
            isLoading={status === 'generating'}
            startContent={!isProcessing && <Play className="w-4 h-4" />}
            className="flex-1"
          >
            {t('schedule.autoPilot.generate', 'Сгенерировать расписание')}
          </Button>
        </div>

        {/* Info */}
        <div className="flex items-start gap-2 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
          <Info className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-[color:var(--color-text-muted)]">
            {t(
              'schedule.autoPilot.info',
              'Автопилот автоматически заполнит пробелы в расписании, используя лучшие плейлисты для каждого временного слота.'
            )}
          </p>
        </div>
      </CardBody>
    </Card>
  );
};

export default AutoPilotPanel;
