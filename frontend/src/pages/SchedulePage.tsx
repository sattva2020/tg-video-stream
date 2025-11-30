/**
 * SchedulePage - Страница управления расписанием трансляций.
 * 
 * Включает:
 * - Календарь с расписанием слотов
 * - Управление плейлистами
 * - Шаблоны расписания
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Card, Tabs, Tab, Tooltip, Badge, Dropdown, DropdownTrigger, DropdownMenu, DropdownItem } from '@heroui/react';
import { CalendarDays, List, Copy, ChevronDown, Plus, RefreshCw } from 'lucide-react';

import { ResponsiveHeader } from '@/components/layout';
import { ScheduleCalendar, PlaylistManager, SlotEditorModal, CopyScheduleModal } from '@/components/schedule';
import { useScheduleTemplates, useApplyTemplate, usePlaylists } from '@/hooks/useScheduleQuery';
import type { ScheduleSlot, ScheduleTemplate } from '@/api/schedule';
import { toast } from 'sonner';

type TabKey = 'calendar' | 'playlists' | 'templates';

export default function SchedulePage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabKey>('calendar');
  // TODO: Добавить выбор канала из списка доступных каналов
  const [selectedChannelId, _setSelectedChannelId] = useState<string>('default-channel');
  const [selectedSlot, setSelectedSlot] = useState<ScheduleSlot | null>(null);
  const [isSlotModalOpen, setIsSlotModalOpen] = useState(false);
  const [isCopyModalOpen, setIsCopyModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);

  // React Query hooks
  const { data: templates = [], isLoading: templatesLoading } = useScheduleTemplates();
  const { data: playlists = [] } = usePlaylists();
  const applyTemplateMutation = useApplyTemplate();

  // Handlers
  const handleSlotClick = (slot: ScheduleSlot) => {
    setSelectedSlot(slot);
    setIsSlotModalOpen(true);
  };

  const handleDateClick = (date: Date) => {
    setSelectedDate(date);
    setSelectedSlot(null);
    setIsSlotModalOpen(true);
  };

  const handleCreateSlot = () => {
    setSelectedSlot(null);
    setSelectedDate(new Date());
    setIsSlotModalOpen(true);
  };

  const handleSlotModalClose = () => {
    setIsSlotModalOpen(false);
    setSelectedSlot(null);
    setSelectedDate(undefined);
  };

  const handleApplyTemplate = async (template: ScheduleTemplate) => {
    // Генерируем список дат на неделю вперед
    const targetDates: string[] = [];
    const startDate = new Date();
    for (let i = 0; i < 7; i++) {
      const date = new Date(startDate);
      date.setDate(date.getDate() + i);
      targetDates.push(date.toISOString().split('T')[0]);
    }

    try {
      await applyTemplateMutation.mutateAsync({
        template_id: template.id,
        channel_id: selectedChannelId,
        target_dates: targetDates,
      });
      toast.success(t('schedule.templateApplied', 'Шаблон применен'));
    } catch {
      toast.error(t('schedule.templateApplyError', 'Ошибка применения шаблона'));
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-gray-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <ResponsiveHeader />
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                {t('schedule.title', 'Расписание трансляций')}
              </h1>
              <p className="text-gray-500 dark:text-gray-400 mt-1">
                {t('schedule.subtitle', 'Управление расписанием и плейлистами')}
              </p>
            </div>

            <div className="flex items-center gap-3">
              {/* Quick Template Apply */}
              {templates.length > 0 && activeTab === 'calendar' && (
                <Dropdown>
                  <DropdownTrigger>
                    <Button
                      variant="flat"
                      startContent={<Copy className="w-4 h-4" />}
                      endContent={<ChevronDown className="w-4 h-4" />}
                    >
                      {t('schedule.applyTemplate', 'Применить шаблон')}
                    </Button>
                  </DropdownTrigger>
                  <DropdownMenu
                    aria-label="Templates"
                    onAction={(key) => {
                      const template = templates.find(t => t.id === key);
                      if (template) handleApplyTemplate(template);
                    }}
                  >
                    {templates.map((template) => (
                      <DropdownItem key={template.id} description={template.description}>
                        {template.name}
                      </DropdownItem>
                    ))}
                  </DropdownMenu>
                </Dropdown>
              )}

              {/* Copy Schedule */}
              {activeTab === 'calendar' && (
                <Tooltip content={t('schedule.copySchedule', 'Копировать расписание')}>
                  <Button
                    variant="flat"
                    isIconOnly
                    onPress={() => setIsCopyModalOpen(true)}
                  >
                    <RefreshCw className="w-5 h-5" />
                  </Button>
                </Tooltip>
              )}

              {/* Create Slot */}
              {activeTab === 'calendar' && (
                <Button
                  color="primary"
                  startContent={<Plus className="w-4 h-4" />}
                  onPress={handleCreateSlot}
                >
                  {t('schedule.createSlot', 'Создать слот')}
                </Button>
              )}
            </div>
          </div>
        </motion.div>

        {/* Stats Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6"
        >
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
                <CalendarDays className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {t('schedule.todaySlots', 'Слотов сегодня')}
                </p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">12</p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-success-100 dark:bg-success-900/30 rounded-lg">
                <List className="w-5 h-5 text-success-600 dark:text-success-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {t('schedule.playlists', 'Плейлистов')}
                </p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">{playlists.length}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
                <Copy className="w-5 h-5 text-warning-600 dark:text-warning-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {t('schedule.templates', 'Шаблонов')}
                </p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">{templates.length}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-secondary-100 dark:bg-secondary-900/30 rounded-lg">
                <RefreshCw className="w-5 h-5 text-secondary-600 dark:text-secondary-400" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {t('schedule.weekSlots', 'Слотов на неделю')}
                </p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">84</p>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <Tabs
            selectedKey={activeTab}
            onSelectionChange={(key) => setActiveTab(key as TabKey)}
            variant="underlined"
            classNames={{
              tabList: "gap-6 w-full relative rounded-none p-0 border-b border-divider",
              cursor: "w-full bg-primary",
              tab: "max-w-fit px-0 h-12",
              tabContent: "group-data-[selected=true]:text-primary"
            }}
          >
            <Tab
              key="calendar"
              title={
                <div className="flex items-center gap-2">
                  <CalendarDays className="w-4 h-4" />
                  <span>{t('schedule.tabs.calendar', 'Календарь')}</span>
                </div>
              }
            />
            <Tab
              key="playlists"
              title={
                <div className="flex items-center gap-2">
                  <List className="w-4 h-4" />
                  <span>{t('schedule.tabs.playlists', 'Плейлисты')}</span>
                  <Badge size="sm" color="primary" variant="flat">
                    {playlists.length}
                  </Badge>
                </div>
              }
            />
            <Tab
              key="templates"
              title={
                <div className="flex items-center gap-2">
                  <Copy className="w-4 h-4" />
                  <span>{t('schedule.tabs.templates', 'Шаблоны')}</span>
                  <Badge size="sm" color="secondary" variant="flat">
                    {templates.length}
                  </Badge>
                </div>
              }
            />
          </Tabs>

          {/* Tab Content */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="mt-6"
            >
              {activeTab === 'calendar' && (
                <ScheduleCalendar
                  channelId={selectedChannelId}
                  onCreateSlot={handleDateClick}
                  onEditSlot={handleSlotClick}
                  onCopyDay={(date) => {
                    setSelectedDate(date);
                    setIsCopyModalOpen(true);
                  }}
                  onApplyTemplate={() => {}}
                />
              )}

              {activeTab === 'playlists' && (
                <PlaylistManager />
              )}

              {activeTab === 'templates' && (
                <TemplatesSection
                  templates={templates}
                  isLoading={templatesLoading}
                  onApply={handleApplyTemplate}
                />
              )}
            </motion.div>
          </AnimatePresence>
        </motion.div>

        {/* Modals */}
        <SlotEditorModal
          isOpen={isSlotModalOpen}
          onClose={handleSlotModalClose}
          slot={selectedSlot}
          channelId={selectedChannelId}
          initialDate={selectedDate}
        />

        <CopyScheduleModal
          isOpen={isCopyModalOpen}
          onClose={() => setIsCopyModalOpen(false)}
          channelId={selectedChannelId}
          sourceDate={selectedDate || new Date()}
        />
      </div>
    </div>
  );
}

// Templates Section Component
interface TemplatesSectionProps {
  templates: ScheduleTemplate[];
  isLoading: boolean;
  onApply: (template: ScheduleTemplate) => void;
}

function TemplatesSection({ templates, isLoading, onApply }: TemplatesSectionProps) {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="p-6 animate-pulse">
            <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-3" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
          </Card>
        ))}
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <Card className="p-12 text-center">
        <Copy className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
        <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
          {t('schedule.noTemplates', 'Нет шаблонов')}
        </h3>
        <p className="text-gray-500 dark:text-gray-400 mb-4">
          {t('schedule.noTemplatesDesc', 'Создайте шаблон расписания для быстрого применения')}
        </p>
        <Button color="primary" startContent={<Plus className="w-4 h-4" />}>
          {t('schedule.createTemplate', 'Создать шаблон')}
        </Button>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {templates.map((template) => (
        <motion.div
          key={template.id}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          whileHover={{ scale: 1.02 }}
        >
          <Card className="p-6 hover:shadow-lg transition-shadow">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              {template.name}
            </h3>
            {template.description && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                {template.description}
              </p>
            )}
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-400">
                {t('schedule.slotsCount', { count: template.slots?.length || 0 })}
              </span>
              <Button
                size="sm"
                color="primary"
                variant="flat"
                onPress={() => onApply(template)}
              >
                {t('schedule.apply', 'Применить')}
              </Button>
            </div>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
