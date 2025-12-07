/**
 * SlotEditorModal — Модальное окно для создания/редактирования слота расписания.
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Clock,
  Music,
  Palette,
  Save,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Input,
  Textarea,
  Select,
  SelectItem,
} from '@heroui/react';
import { useCreateSlot, useUpdateSlot, usePlaylists } from '../../hooks/useScheduleQuery';
import type { ScheduleSlot, ScheduleSlotCreate, ScheduleSlotUpdate, RepeatType } from '../../api/schedule';

// ==================== Types ====================

interface SlotEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  channelId: string;
  slot?: ScheduleSlot | null;  // null = create mode
  initialDate?: Date;
  initialTime?: string;
}

interface FormData {
  title: string;
  description: string;
  playlist_id: string;
  start_date: string;
  start_time: string;
  end_time: string;
  color: string;
  repeat_type: RepeatType;
  repeat_days: number[];
  repeat_until: string;
}

// ==================== Constants ====================

const PRESET_COLORS = [
  '#3B82F6', // Blue
  '#8B5CF6', // Violet
  '#EC4899', // Pink
  '#EF4444', // Red
  '#F97316', // Orange
  '#EAB308', // Yellow
  '#22C55E', // Green
  '#14B8A6', // Teal
  '#06B6D4', // Cyan
  '#6366F1', // Indigo
];

const REPEAT_OPTIONS: { value: RepeatType; label: string }[] = [
  { value: 'none', label: 'Без повторения' },
  { value: 'daily', label: 'Ежедневно' },
  { value: 'weekly', label: 'Еженедельно' },
  { value: 'weekdays', label: 'По будням (Пн-Пт)' },
  { value: 'weekends', label: 'По выходным (Сб-Вс)' },
  { value: 'custom', label: 'Выбрать дни...' },
];

const WEEKDAYS = [
  { value: 0, label: 'Пн' },
  { value: 1, label: 'Вт' },
  { value: 2, label: 'Ср' },
  { value: 3, label: 'Чт' },
  { value: 4, label: 'Пт' },
  { value: 5, label: 'Сб' },
  { value: 6, label: 'Вс' },
];

// ==================== Helper Functions ====================

function formatDateForInput(date: Date): string {
  return date.toISOString().split('T')[0];
}

function getDefaultEndTime(startTime: string): string {
  const [h, m] = startTime.split(':').map(Number);
  const endHour = Math.min(23, h + 2);
  return `${String(endHour).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

// ==================== Component ====================

export const SlotEditorModal: React.FC<SlotEditorModalProps> = ({
  isOpen,
  onClose,
  channelId,
  slot,
  initialDate,
  initialTime,
}) => {
  const { t } = useTranslation();
  const isEditMode = !!slot;

  // Mutations
  const createMutation = useCreateSlot();
  const updateMutation = useUpdateSlot();
  const isLoading = createMutation.isPending || updateMutation.isPending;

  // Playlists data
  const { data: playlists = [] } = usePlaylists(channelId);

  // Initialize form data based on slot (for edit mode) or defaults (for create mode)
  const getInitialFormData = useCallback((): FormData => {
    if (slot) {
      return {
        title: slot.title || '',
        description: slot.description || '',
        playlist_id: slot.playlist_id || '',
        start_date: slot.start_date,
        start_time: slot.start_time,
        end_time: slot.end_time,
        color: slot.color,
        repeat_type: slot.repeat_type,
        repeat_days: slot.repeat_days || [],
        repeat_until: slot.repeat_until || '',
      };
    }
    const startTime = initialTime || '09:00';
    return {
      title: '',
      description: '',
      playlist_id: '',
      start_date: initialDate ? formatDateForInput(initialDate) : formatDateForInput(new Date()),
      start_time: startTime,
      end_time: getDefaultEndTime(startTime),
      color: PRESET_COLORS[Math.floor(Math.random() * PRESET_COLORS.length)],
      repeat_type: 'none',
      repeat_days: [],
      repeat_until: '',
    };
  }, [slot, initialDate, initialTime]);

  // Form state - initialized with proper values
  const [formData, setFormData] = useState<FormData>(getInitialFormData);

  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});

  // Reset form data when slot, dates change or modal opens
  useEffect(() => {
    setFormData(getInitialFormData());
    setErrors({});
  }, [slot, initialDate, initialTime, isOpen, getInitialFormData]);

  // Form handlers
  const handleChange = (field: keyof FormData, value: string | number[] | RepeatType) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when field changes
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const toggleRepeatDay = (day: number) => {
    setFormData(prev => ({
      ...prev,
      repeat_days: prev.repeat_days.includes(day)
        ? prev.repeat_days.filter(d => d !== day)
        : [...prev.repeat_days, day].sort()
    }));
  };

  // Validation
  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof FormData, string>> = {};

    if (!formData.start_date) {
      newErrors.start_date = 'Выберите дату';
    }
    if (!formData.start_time) {
      newErrors.start_time = 'Укажите время начала';
    }
    if (!formData.end_time) {
      newErrors.end_time = 'Укажите время окончания';
    }
    if (formData.start_time >= formData.end_time) {
      newErrors.end_time = 'Время окончания должно быть после начала';
    }
    if (formData.repeat_type === 'custom' && formData.repeat_days.length === 0) {
      newErrors.repeat_days = 'Выберите хотя бы один день';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Submit
  const handleSubmit = async () => {
    if (!validate()) return;

    try {
      if (isEditMode && slot) {
        // Update existing slot
        const updateData: ScheduleSlotUpdate = {
          title: formData.title || undefined,
          description: formData.description || undefined,
          playlist_id: formData.playlist_id || undefined,
          start_date: formData.start_date,
          start_time: formData.start_time,
          end_time: formData.end_time,
          color: formData.color,
          repeat_type: formData.repeat_type,
          repeat_days: formData.repeat_type === 'custom' ? formData.repeat_days : undefined,
          repeat_until: formData.repeat_until || undefined,
        };
        await updateMutation.mutateAsync({ slotId: slot.id, data: updateData });
      } else {
        // Create new slot
        const createData: ScheduleSlotCreate = {
          channel_id: channelId,
          title: formData.title || undefined,
          description: formData.description || undefined,
          playlist_id: formData.playlist_id || undefined,
          start_date: formData.start_date,
          start_time: formData.start_time,
          end_time: formData.end_time,
          color: formData.color,
          repeat_type: formData.repeat_type,
          repeat_days: formData.repeat_type === 'custom' ? formData.repeat_days : undefined,
          repeat_until: formData.repeat_until || undefined,
        };
        await createMutation.mutateAsync(createData);
      }
      onClose();
    } catch (error) {
      // Error is handled by mutation hooks
    }
  };

  // Selected playlist info
  const selectedPlaylist = useMemo(() => {
    return playlists.find(p => p.id === formData.playlist_id);
  }, [playlists, formData.playlist_id]);

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose}
      size="2xl"
      scrollBehavior="inside"
      backdrop="blur"
      classNames={{
        backdrop: "bg-black/50 backdrop-blur-sm",
        base: "bg-white dark:bg-gray-900 shadow-xl",
        header: "border-b border-gray-200 dark:border-gray-700",
        body: "py-6",
        footer: "border-t border-gray-200 dark:border-gray-700",
      }}
    >
      <ModalContent>
        <ModalHeader className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600">
            <Clock className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">
              {isEditMode 
                ? t('schedule.editSlot', 'Редактирование слота')
                : t('schedule.createSlot', 'Новый слот расписания')}
            </h2>
            <p className="text-sm text-default-500">
              {isEditMode 
                ? t('schedule.editSlotDesc', 'Измените параметры слота')
                : t('schedule.createSlotDesc', 'Добавьте слот в расписание')}
            </p>
          </div>
        </ModalHeader>

        <ModalBody className="gap-6">
          {/* Date & Time Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-default-700">{t('schedule.date', 'Дата')}</label>
              <Input
                type="date"
                value={formData.start_date}
                onChange={(e) => handleChange('start_date', e.target.value)}
                isInvalid={!!errors.start_date}
                errorMessage={errors.start_date}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-default-700">{t('schedule.startTime', 'Начало')}</label>
              <Input
                type="time"
                value={formData.start_time}
                onChange={(e) => handleChange('start_time', e.target.value)}
                isInvalid={!!errors.start_time}
                errorMessage={errors.start_time}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-default-700">{t('schedule.endTime', 'Конец')}</label>
              <Input
                type="time"
                value={formData.end_time}
                onChange={(e) => handleChange('end_time', e.target.value)}
                isInvalid={!!errors.end_time}
                errorMessage={errors.end_time}
              />
            </div>
          </div>

          {/* Playlist Selection */}
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-default-700">{t('schedule.playlist', 'Плейлист')}</label>
            {playlists.length === 0 ? (
              <div className="p-4 rounded-lg bg-warning-50 border border-warning-200">
                <p className="text-sm text-warning-700 font-medium">
                  {t('schedule.noPlaylists', 'Нет доступных плейлистов')}
                </p>
                <p className="text-xs text-warning-600 mt-1">
                  {t('schedule.createPlaylistHint', 'Сначала создайте плейлист для расписания в настройках канала')}
                </p>
              </div>
            ) : (
              <Select
                placeholder={t('schedule.selectPlaylist', 'Выберите плейлист')}
                selectedKeys={formData.playlist_id ? new Set([formData.playlist_id]) : new Set()}
                onSelectionChange={(keys) => {
                  const selected = Array.from(keys)[0] as string;
                  handleChange('playlist_id', selected || '');
                }}
              >
                {playlists.map((playlist) => (
                  <SelectItem key={playlist.id} textValue={playlist.name}>
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: playlist.color }}
                      />
                      <span>{playlist.name}</span>
                      <span className="text-xs text-default-400">
                        ({playlist.items_count} треков)
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </Select>
            )}
            
            {selectedPlaylist && (
              <div className="mt-2 p-3 rounded-lg bg-default-100">
                <div className="flex items-center gap-2 text-sm">
                  <Music className="w-4 h-4" style={{ color: selectedPlaylist.color }} />
                  <span className="font-medium">{selectedPlaylist.name}</span>
                </div>
                <p className="text-xs text-default-500 mt-1">
                  {selectedPlaylist.items_count} треков • 
                  {Math.floor(selectedPlaylist.total_duration / 3600)}ч {Math.floor((selectedPlaylist.total_duration % 3600) / 60)}м
                </p>
              </div>
            )}
          </div>

          {/* Title & Description */}
          <div className="grid grid-cols-1 gap-4">
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-default-700">{t('schedule.title', 'Название (опционально)')}</label>
              <Input
                placeholder={t('schedule.titlePlaceholder', 'Например: Утренний эфир')}
                value={formData.title}
                onChange={(e) => handleChange('title', e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-sm font-medium text-default-700">{t('schedule.description', 'Описание')}</label>
              <Textarea
                placeholder={t('schedule.descriptionPlaceholder', 'Дополнительная информация...')}
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                minRows={2}
              />
            </div>
          </div>

          {/* Color Picker */}
          <div>
            <label className="text-sm font-medium text-default-700 mb-2 flex items-center gap-2">
              <Palette className="w-4 h-4" />
              {t('schedule.color', 'Цвет')}
            </label>
            <div className="flex flex-wrap gap-2">
              {PRESET_COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => handleChange('color', color)}
                  className={`
                    w-8 h-8 rounded-lg transition-all
                    ${formData.color === color 
                      ? 'ring-2 ring-offset-2 ring-violet-500 scale-110' 
                      : 'hover:scale-105'}
                  `}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </div>

          {/* Repeat Options */}
          <div className="flex flex-col gap-1">
            <label className="text-sm font-medium text-default-700">{t('schedule.repeat', 'Повторение')}</label>
            <Select
              placeholder={t('schedule.selectRepeat', 'Выберите режим повторения')}
              selectedKeys={new Set([formData.repeat_type])}
              onSelectionChange={(keys) => {
                const selected = Array.from(keys)[0] as RepeatType;
                handleChange('repeat_type', selected);
              }}
            >
              {REPEAT_OPTIONS.map((option) => (
                <SelectItem key={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </Select>

            {/* Custom days selector */}
            {formData.repeat_type === 'custom' && (
              <div className="mt-3">
                <p className="text-sm text-default-500 mb-2">
                  {t('schedule.selectDays', 'Выберите дни недели:')}
                </p>
                <div className="flex flex-wrap gap-2">
                  {WEEKDAYS.map((day) => (
                    <button
                      key={day.value}
                      onClick={() => toggleRepeatDay(day.value)}
                      className={`
                        px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                        ${formData.repeat_days.includes(day.value)
                          ? 'bg-violet-500 text-white'
                          : 'bg-default-100 text-default-700 hover:bg-default-200'}
                      `}
                    >
                      {day.label}
                    </button>
                  ))}
                </div>
                {errors.repeat_days && (
                  <p className="text-xs text-danger mt-1">{errors.repeat_days}</p>
                )}
              </div>
            )}

            {/* Repeat until date */}
            {formData.repeat_type !== 'none' && (
              <div className="mt-3 flex flex-col gap-1">
                <label className="text-sm font-medium text-default-700">{t('schedule.repeatUntil', 'Повторять до (опционально)')}</label>
                <Input
                  type="date"
                  value={formData.repeat_until}
                  onChange={(e) => handleChange('repeat_until', e.target.value)}
                />
              </div>
            )}
          </div>
        </ModalBody>

        <ModalFooter>
          <Button variant="flat" onPress={onClose}>
            {t('common.cancel', 'Отмена')}
          </Button>
          <Button
            color="primary"
            onPress={handleSubmit}
            isLoading={isLoading}
            startContent={!isLoading && <Save className="w-4 h-4" />}
          >
            {isEditMode 
              ? t('common.save', 'Сохранить')
              : t('common.create', 'Создать')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default SlotEditorModal;
