/**
 * ScheduleCalendar — Компонент календаря расписания трансляций.
 * 
 * Функции:
 * - Отображение месячного/недельного календаря
 * - Создание/редактирование слотов
 * - Drag-and-drop для слотов
 * - Привязка плейлистов к слотам
 */

import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Plus,
  Copy,
  Layers,
  Clock,
  Music,
  MoreVertical,
  Trash2,
  Edit,
  AlertCircle,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Skeleton,
  Tooltip,
} from '@heroui/react';
import { useScheduleCalendar, useDeleteSlot } from '../../hooks/useScheduleQuery';
import type { ScheduleSlot, CalendarDay } from '../../api/schedule';

// ==================== Types ====================

interface ScheduleCalendarProps {
  channelId: string;
  onCreateSlot: (date: Date, startTime?: string) => void;
  onEditSlot: (slot: ScheduleSlot) => void;
  onCopyDay: (sourceDate: Date) => void;
  onApplyTemplate: (date: Date) => void;
}

interface DayProps {
  day: CalendarDay;
  isToday: boolean;
  isSelected: boolean;
  onClick: () => void;
  onSlotClick: (slot: ScheduleSlot) => void;
  onAddClick: () => void;
}

// ==================== Helper Functions ====================

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const MONTHS_RU = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
];

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  // 0 = Sunday, we want 0 = Monday
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h > 0 ? `${h}ч ${m > 0 ? m + 'м' : ''}` : `${m}м`;
}

function parseTime(timeStr: string): { hours: number; minutes: number } {
  const [h, m] = timeStr.split(':').map(Number);
  return { hours: h, minutes: m };
}

function getSlotDuration(startTime: string, endTime: string): number {
  const start = parseTime(startTime);
  const end = parseTime(endTime);
  return (end.hours * 60 + end.minutes) - (start.hours * 60 + start.minutes);
}

// ==================== Sub-Components ====================

const SlotBadge: React.FC<{ 
  slot: ScheduleSlot; 
  onClick: () => void;
  compact?: boolean;
}> = ({ slot, onClick, compact = false }) => {
  const duration = getSlotDuration(slot.start_time, slot.end_time);
  
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      className="w-full text-left group transition-transform duration-150 hover:scale-[1.02] active:scale-[0.98]"
    >
      <div 
        className={`
          relative overflow-hidden rounded-lg border transition-all duration-200
          hover:shadow-md hover:border-opacity-50
          ${compact ? 'p-1.5' : 'p-2'}
        `}
        style={{ 
          backgroundColor: `${slot.color}15`,
          borderColor: `${slot.color}40`
        }}
      >
        {/* Color indicator */}
        <div 
          className="absolute left-0 top-0 bottom-0 w-1 rounded-l"
          style={{ backgroundColor: slot.color }}
        />
        
        <div className={`${compact ? 'pl-2' : 'pl-3'}`}>
          {/* Time */}
          <div className="flex items-center gap-1 text-xs font-medium text-[color:var(--color-text)]">
            <Clock className="w-3 h-3" style={{ color: slot.color }} />
            <span>{slot.start_time} - {slot.end_time}</span>
            {!compact && (
              <span className="text-[color:var(--color-text-muted)] ml-1">
                ({formatDuration(duration)})
              </span>
            )}
          </div>
          
          {/* Title or Playlist */}
          {!compact && (
            <div className="mt-1 flex items-center gap-1.5">
              {slot.playlist_name ? (
                <>
                  <Music className="w-3 h-3 text-[color:var(--color-text-muted)]" />
                  <span className="text-xs text-[color:var(--color-text)] truncate">
                    {slot.playlist_name}
                  </span>
                </>
              ) : slot.title ? (
                <span className="text-xs text-[color:var(--color-text)] truncate">
                  {slot.title}
                </span>
              ) : (
                <span className="text-xs text-[color:var(--color-text-muted)] italic">
                  Без плейлиста
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </button>
  );
};

const CalendarDayCell: React.FC<DayProps> = ({
  day,
  isToday,
  isSelected,
  onClick,
  onSlotClick,
  onAddClick,
}) => {
  const dayNum = new Date(day.date).getDate();
  const slots = day.slots || [];
  const hasSlots = slots.length > 0;
  const maxVisibleSlots = 2;
  const hiddenCount = Math.max(0, slots.length - maxVisibleSlots);

  return (
    <div
      onClick={onClick}
      className={`
        relative min-h-[120px] p-2 border rounded-xl cursor-pointer
        transition-all duration-150 group hover:scale-[1.01]
        ${isToday 
          ? 'border-violet-500 bg-violet-500/5' 
          : 'border-[color:var(--color-border)] hover:border-[color:var(--color-border-hover)]'}
        ${isSelected 
          ? 'ring-2 ring-violet-500 ring-opacity-50' 
          : ''}
        ${day.has_conflicts 
          ? 'border-amber-500/50' 
          : ''}
      `}
    >
      {/* Day number */}
      <div className="flex items-center justify-between mb-2">
        <span className={`
          text-sm font-semibold
          ${isToday 
            ? 'text-violet-600 dark:text-violet-400' 
            : 'text-[color:var(--color-text)]'}
        `}>
          {dayNum}
        </span>
        
        {/* Conflict indicator */}
        {day.has_conflicts && (
          <Tooltip content="Есть пересечения слотов">
            <AlertCircle className="w-4 h-4 text-amber-500" />
          </Tooltip>
        )}
        
        {/* Add button (visible on hover) */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onAddClick();
          }}
          className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-[color:var(--color-surface-hover)] transition-all"
        >
          <Plus className="w-4 h-4 text-[color:var(--color-text-muted)]" />
        </button>
      </div>

      {/* Slots */}
      <div className="space-y-1">
        {slots.slice(0, maxVisibleSlots).map((slot) => (
          <SlotBadge 
            key={slot.id} 
            slot={slot} 
            onClick={() => onSlotClick(slot)}
            compact={slots.length > 1}
          />
        ))}
        
        {hiddenCount > 0 && (
          <div className="text-xs text-center text-[color:var(--color-text-muted)] py-1">
            + ещё {hiddenCount}
          </div>
        )}
      </div>

      {/* Empty state */}
      {!hasSlots && (
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <span className="text-xs text-[color:var(--color-text-muted)]">
            Нажмите для добавления
          </span>
        </div>
      )}
    </div>
  );
};

// ==================== Main Component ====================

export const ScheduleCalendar: React.FC<ScheduleCalendarProps> = ({
  channelId,
  onCreateSlot,
  onEditSlot,
  onCopyDay,
  onApplyTemplate,
}) => {
  const { t } = useTranslation();
  
  // State
  const [currentYear, setCurrentYear] = useState(() => new Date().getFullYear());
  const [currentMonth, setCurrentMonth] = useState(() => new Date().getMonth());
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  // Data
  const { data: calendarData, isLoading, isFetching } = useScheduleCalendar(
    channelId,
    currentYear,
    currentMonth + 1 // API expects 1-12
  );

  const deleteSlotMutation = useDeleteSlot();

  // Navigation handlers
  const goToPrevMonth = useCallback(() => {
    if (currentMonth === 0) {
      setCurrentYear(y => y - 1);
      setCurrentMonth(11);
    } else {
      setCurrentMonth(m => m - 1);
    }
  }, [currentMonth]);

  const goToNextMonth = useCallback(() => {
    if (currentMonth === 11) {
      setCurrentYear(y => y + 1);
      setCurrentMonth(0);
    } else {
      setCurrentMonth(m => m + 1);
    }
  }, [currentMonth]);

  const goToToday = useCallback(() => {
    const now = new Date();
    setCurrentYear(now.getFullYear());
    setCurrentMonth(now.getMonth());
    setSelectedDate(now.toISOString().split('T')[0]);
  }, []);

  // Build calendar grid
  const calendarGrid = useMemo(() => {
    const daysInMonth = getDaysInMonth(currentYear, currentMonth);
    const firstDay = getFirstDayOfMonth(currentYear, currentMonth);
    
    // Create map of dates to calendar data
    const dataMap = new Map<string, CalendarDay>();
    calendarData?.forEach(day => {
      dataMap.set(day.date, day);
    });

    const grid: (CalendarDay | null)[] = [];
    
    // Empty cells before first day
    for (let i = 0; i < firstDay; i++) {
      grid.push(null);
    }
    
    // Days of month
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const dayData = dataMap.get(dateStr) || {
        date: dateStr,
        slots: [],
        has_conflicts: false
      };
      grid.push(dayData);
    }
    
    return grid;
  }, [currentYear, currentMonth, calendarData]);

  const todayStr = new Date().toISOString().split('T')[0];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25">
            <Calendar className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[color:var(--color-text)]">
              {t('schedule.calendar', 'Расписание')}
            </h2>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('schedule.calendarDesc', 'Планирование трансляций')}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="flat"
            onPress={() => onApplyTemplate(new Date(currentYear, currentMonth, 1))}
            startContent={<Layers className="w-4 h-4" />}
          >
            {t('schedule.applyTemplate', 'Шаблон')}
          </Button>
          <Button
            size="sm"
            color="primary"
            onPress={() => onCreateSlot(new Date())}
            startContent={<Plus className="w-4 h-4" />}
          >
            {t('schedule.addSlot', 'Добавить')}
          </Button>
        </div>
      </div>

      {/* Month Navigation */}
      <div className="flex items-center justify-between p-4 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
        <Button
          isIconOnly
          size="sm"
          variant="flat"
          onPress={goToPrevMonth}
        >
          <ChevronLeft className="w-5 h-5" />
        </Button>

        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {MONTHS_RU[currentMonth]} {currentYear}
          </h3>
          <Button
            size="sm"
            variant="flat"
            onPress={goToToday}
          >
            {t('schedule.today', 'Сегодня')}
          </Button>
        </div>

        <Button
          isIconOnly
          size="sm"
          variant="flat"
          onPress={goToNextMonth}
        >
          <ChevronRight className="w-5 h-5" />
        </Button>
      </div>

      {/* Calendar Grid */}
      <div className="rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] overflow-hidden">
        {/* Weekday headers */}
        <div className="grid grid-cols-7 border-b border-[color:var(--color-border)]">
          {WEEKDAYS.map((day, i) => (
            <div 
              key={day} 
              className={`
                py-3 text-center text-sm font-medium
                ${i >= 5 
                  ? 'text-rose-500 dark:text-rose-400' 
                  : 'text-[color:var(--color-text-muted)]'}
              `}
            >
              {day}
            </div>
          ))}
        </div>

        {/* Days grid */}
        <div className="grid grid-cols-7 gap-1 p-2">
          {isLoading ? (
            // Skeleton loading
            Array.from({ length: 35 }).map((_, i) => (
              <Skeleton key={i} className="min-h-[120px] rounded-xl" />
            ))
          ) : (
            calendarGrid.map((day, i) => (
              day ? (
                <CalendarDayCell
                  key={day.date}
                  day={day}
                  isToday={day.date === todayStr}
                  isSelected={day.date === selectedDate}
                  onClick={() => setSelectedDate(day.date)}
                  onSlotClick={onEditSlot}
                  onAddClick={() => onCreateSlot(new Date(day.date))}
                />
              ) : (
                <div key={`empty-${i}`} className="min-h-[120px]" />
              )
            ))
          )}
        </div>
      </div>

      {/* Selected Day Details */}
      <AnimatePresence>
        {selectedDate && calendarData && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="p-4 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]"
          >
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold text-[color:var(--color-text)]">
                {new Date(selectedDate).toLocaleDateString('ru-RU', { 
                  weekday: 'long', 
                  day: 'numeric', 
                  month: 'long' 
                })}
              </h4>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="flat"
                  onPress={() => onCopyDay(new Date(selectedDate))}
                  startContent={<Copy className="w-4 h-4" />}
                >
                  {t('schedule.copyDay', 'Копировать')}
                </Button>
                <Button
                  size="sm"
                  color="primary"
                  onPress={() => onCreateSlot(new Date(selectedDate))}
                  startContent={<Plus className="w-4 h-4" />}
                >
                  {t('schedule.addSlot', 'Добавить')}
                </Button>
              </div>
            </div>

            {/* Day slots list */}
            {(() => {
              const dayData = calendarData.find(d => d.date === selectedDate);
              const daySlots = dayData?.slots || [];
              if (!dayData || daySlots.length === 0) {
                return (
                  <div className="py-8 text-center text-[color:var(--color-text-muted)]">
                    <Calendar className="w-12 h-12 mx-auto mb-3 opacity-50" />
                    <p>{t('schedule.noSlots', 'Нет запланированных слотов')}</p>
                    <p className="text-sm mt-1">
                      {t('schedule.clickToAdd', 'Нажмите "Добавить" чтобы создать')}
                    </p>
                  </div>
                );
              }

              return (
                <div className="space-y-2">
                  {daySlots.map((slot) => (
                    <div
                      key={slot.id}
                      className="flex items-center justify-between p-3 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]"
                    >
                      <div className="flex items-center gap-3">
                        <div 
                          className="w-3 h-10 rounded-full"
                          style={{ backgroundColor: slot.color }}
                        />
                        <div>
                          <div className="font-medium text-[color:var(--color-text)]">
                            {slot.start_time} - {slot.end_time}
                          </div>
                          <div className="text-sm text-[color:var(--color-text-muted)]">
                            {slot.playlist_name || slot.title || 'Без названия'}
                          </div>
                        </div>
                      </div>

                      <Dropdown>
                        <DropdownTrigger>
                          <Button isIconOnly size="sm" variant="light">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownTrigger>
                        <DropdownMenu aria-label="Slot actions">
                          <DropdownItem
                            key="edit"
                            startContent={<Edit className="w-4 h-4" />}
                            onPress={() => onEditSlot(slot)}
                          >
                            {t('common.edit', 'Редактировать')}
                          </DropdownItem>
                          <DropdownItem
                            key="delete"
                            color="danger"
                            startContent={<Trash2 className="w-4 h-4" />}
                            onPress={() => {
                              if (confirm(t('schedule.confirmDelete', 'Удалить этот слот?'))) {
                                deleteSlotMutation.mutate(slot.id);
                              }
                            }}
                          >
                            {t('common.delete', 'Удалить')}
                          </DropdownItem>
                        </DropdownMenu>
                      </Dropdown>
                    </div>
                  ))}
                </div>
              );
            })()}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading overlay */}
      {isFetching && !isLoading && (
        <div className="fixed top-4 right-4 px-3 py-2 rounded-lg bg-violet-500 text-white text-sm shadow-lg">
          {t('common.loading', 'Загрузка...')}
        </div>
      )}
    </div>
  );
};

export default ScheduleCalendar;
