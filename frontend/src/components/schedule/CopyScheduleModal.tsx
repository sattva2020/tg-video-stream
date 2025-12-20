/**
 * CopyScheduleModal — Модальное окно для копирования расписания на другие даты.
 */

import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  Copy,
  ChevronLeft,
  ChevronRight,
  Check,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
} from '@heroui/react';
import { useCopySchedule } from '../../hooks/useScheduleQuery';

// ==================== Types ====================

interface CopyScheduleModalProps {
  isOpen: boolean;
  onClose: () => void;
  channelId: string;
  sourceDate: Date;
}

// ==================== Constants ====================

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const MONTHS_RU = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
];

// ==================== Helper Functions ====================

function formatDate(date: Date): string {
  return date.toISOString().split('T')[0];
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number): number {
  const day = new Date(year, month, 1).getDay();
  return day === 0 ? 6 : day - 1;
}

// ==================== Component ====================

export const CopyScheduleModal: React.FC<CopyScheduleModalProps> = ({
  isOpen,
  onClose,
  channelId,
  sourceDate,
}) => {
  const { t } = useTranslation();
  const today = new Date();

  // State
  const [currentYear, setCurrentYear] = useState(sourceDate.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(sourceDate.getMonth());
  const [selectedDates, setSelectedDates] = useState<Set<string>>(new Set());

  // Mutation
  const copyMutation = useCopySchedule();

  // Source date string
  const sourceDateStr = formatDate(sourceDate);

  const flatControlClassName =
    'text-foreground bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-hover)] hover:border-[color:var(--color-border-strong)] transition-colors';
  // Navigation
  const goToPrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentYear((y) => y - 1);
      setCurrentMonth(11);
    } else {
      setCurrentMonth((m) => m - 1);
    }
  };

  const goToNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentYear((y) => y + 1);
      setCurrentMonth(0);
    } else {
      setCurrentMonth((m) => m + 1);
    }
  };

  // Toggle date selection
  const toggleDate = (dateStr: string) => {
    if (dateStr === sourceDateStr) return; // Can't select source date
    
    const newSelected = new Set(selectedDates);
    if (newSelected.has(dateStr)) {
      newSelected.delete(dateStr);
    } else {
      newSelected.add(dateStr);
    }
    setSelectedDates(newSelected);
  };

  // Quick select options
  const selectWeek = () => {
    const startOfWeek = new Date(sourceDate);
    const dayOfWeek = startOfWeek.getDay();
    const diff = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
    startOfWeek.setDate(startOfWeek.getDate() + diff);

    const newSelected = new Set<string>();
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek);
      date.setDate(date.getDate() + i);
      const dateStr = formatDate(date);
      if (dateStr !== sourceDateStr) {
        newSelected.add(dateStr);
      }
    }
    setSelectedDates(newSelected);
  };

  const selectMonth = () => {
    const daysInMonth = getDaysInMonth(currentYear, currentMonth);
    const newSelected = new Set<string>();
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      if (dateStr !== sourceDateStr) {
        newSelected.add(dateStr);
      }
    }
    setSelectedDates(newSelected);
  };

  const clearSelection = () => {
    setSelectedDates(new Set());
  };

  // Calendar grid
  const calendarGrid = useMemo(() => {
    const daysInMonth = getDaysInMonth(currentYear, currentMonth);
    const firstDay = getFirstDayOfMonth(currentYear, currentMonth);
    const grid: (string | null)[] = [];

    // Empty cells
    for (let i = 0; i < firstDay; i++) {
      grid.push(null);
    }

    // Days
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      grid.push(dateStr);
    }

    return grid;
  }, [currentYear, currentMonth]);

  const todayStr = formatDate(today);

  // Submit
  const handleSubmit = async () => {
    if (selectedDates.size === 0) return;

    await copyMutation.mutateAsync({
      channel_id: channelId,
      source_date: sourceDateStr,
      target_dates: Array.from(selectedDates),
    });

    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      size="lg"
      scrollBehavior="inside"
      backdrop="blur"
      classNames={{
        backdrop: 'bg-black/50 backdrop-blur-sm',
        base: 'bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-xl shadow-black/10',
        header: 'border-b border-[color:var(--color-border)]',
        footer: 'border-t border-[color:var(--color-border)]',
      }}
    >
      <ModalContent>
        <ModalHeader className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-[color:var(--color-accent)] shadow-sm shadow-black/10">
            <Copy className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">
              {t('schedule.copySchedule', 'Копировать расписание')}
            </h2>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {t('schedule.copyFrom', 'Источник')}: {sourceDate.toLocaleDateString('ru-RU', {
                weekday: 'short',
                day: 'numeric',
                month: 'long'
              })}
            </p>
          </div>
        </ModalHeader>

        <ModalBody>
          {/* Quick actions */}
          <div className="flex flex-wrap gap-2 mb-4">
            <Button size="sm" variant="flat" className={flatControlClassName} onPress={selectWeek}>
              {t('schedule.selectWeek', 'Вся неделя')}
            </Button>
            <Button size="sm" variant="flat" className={flatControlClassName} onPress={selectMonth}>
              {t('schedule.selectMonth', 'Весь месяц')}
            </Button>
            <Button 
              size="sm" 
              variant="flat" 
              className={flatControlClassName}
              onPress={clearSelection}
              isDisabled={selectedDates.size === 0}
            >
              {t('schedule.clearSelection', 'Очистить')}
            </Button>
            
            <div className="flex-1" />
            
            <span className="text-sm text-[color:var(--color-text-muted)] self-center">
              {t('schedule.selected', 'Выбрано')}: {selectedDates.size}
            </span>
          </div>

          {/* Month Navigation */}
          <div className="flex items-center justify-between mb-4">
            <Button isIconOnly size="sm" variant="flat" className={flatControlClassName} onPress={goToPrevMonth}>
              <ChevronLeft className="w-5 h-5" />
            </Button>
            <span className="font-semibold">
              {MONTHS_RU[currentMonth]} {currentYear}
            </span>
            <Button isIconOnly size="sm" variant="flat" className={flatControlClassName} onPress={goToNextMonth}>
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>

          {/* Calendar */}
          <div className="rounded-xl border border-[color:var(--color-border)] overflow-hidden">
            {/* Weekday headers */}
            <div className="grid grid-cols-7 bg-[color:var(--color-surface-muted)]">
              {WEEKDAYS.map((day, i) => (
                <div
                  key={day}
                  className={`
                    py-2 text-center text-xs font-medium
                    ${i >= 5 ? 'text-danger' : 'text-[color:var(--color-text-muted)]'}
                  `}
                >
                  {day}
                </div>
              ))}
            </div>

            {/* Days grid */}
            <div className="grid grid-cols-7 gap-1 p-2">
              {calendarGrid.map((dateStr, i) => {
                if (!dateStr) {
                  return <div key={`empty-${i}`} className="h-10" />;
                }

                const dayNum = parseInt(dateStr.split('-')[2]);
                const isSource = dateStr === sourceDateStr;
                const isSelected = selectedDates.has(dateStr);
                const isToday = dateStr === todayStr;
                const isPast = dateStr < todayStr;

                return (
                  <motion.button
                    key={dateStr}
                    whileHover={{ scale: isSource ? 1 : 1.1 }}
                    whileTap={{ scale: isSource ? 1 : 0.95 }}
                    onClick={() => toggleDate(dateStr)}
                    disabled={isSource || isPast}
                    className={`
                      relative h-10 rounded-lg font-medium text-sm
                      transition-colors
                      ${isSource
                        ? 'bg-[color:var(--color-panel)] ring-1 ring-inset ring-[color:var(--color-accent)] text-[color:var(--color-text)] cursor-not-allowed'
                        : isSelected
                          ? 'bg-[color:var(--color-accent)] text-white'
                          : isToday
                            ? 'bg-[color:var(--color-surface-muted)] text-[color:var(--color-text)]'
                            : isPast
                              ? 'text-[color:var(--color-text-muted)] opacity-50 cursor-not-allowed'
                              : 'hover:bg-[color:var(--color-surface-muted)] text-[color:var(--color-text)]'}
                    `}
                  >
                    {dayNum}
                    {isSource && (
                      <span className="absolute -top-1 -right-1 w-3 h-3 bg-[color:var(--color-accent)] rounded-full" />
                    )}
                    {isSelected && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="absolute -top-1 -right-1"
                      >
                        <Check className="w-3 h-3 text-white bg-[color:var(--color-accent)] rounded-full" />
                      </motion.div>
                    )}
                  </motion.button>
                );
              })}
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 mt-4 text-xs text-[color:var(--color-text-muted)]">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded border border-[color:var(--color-accent)]" />
              <span>{t('schedule.source', 'Источник')}</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-[color:var(--color-accent)]" />
              <span>{t('schedule.target', 'Цель')}</span>
            </div>
          </div>
        </ModalBody>

        <ModalFooter>
          <Button variant="flat" className={flatControlClassName} onPress={onClose}>
            {t('common.cancel', 'Отмена')}
          </Button>
          <Button
            color="primary"
            onPress={handleSubmit}
            isLoading={copyMutation.isPending}
            isDisabled={selectedDates.size === 0}
            startContent={!copyMutation.isPending && <Copy className="w-4 h-4" />}
          >
            {t('schedule.copyTo', 'Копировать на')} {selectedDates.size} {selectedDates.size === 1 ? 'дату' : 'дат'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export default CopyScheduleModal;
