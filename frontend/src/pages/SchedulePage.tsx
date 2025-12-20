/**
 * SchedulePage - Страница управления расписанием трансляций.
 * 
 * Включает:
 * - Календарь с расписанием слотов
 * - Управление плейлистами
 * - Шаблоны расписания
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { Button, Card, Tooltip, Badge, Dropdown, DropdownTrigger, DropdownMenu, DropdownItem, Select, SelectItem, Skeleton } from '@heroui/react';
import { CalendarDays, List, Copy, ChevronDown, Plus, RefreshCw } from 'lucide-react';

import { ResponsiveHeader } from '@/components/layout';
import { ScheduleCalendar, PlaylistManager, SlotEditorModal, CopyScheduleModal } from '@/components/schedule';
import { StatCard } from '@/components/dashboard/StatCard';
import { useScheduleTemplates, useApplyTemplate, usePlaylists } from '@/hooks/useScheduleQuery';
import { useChannels } from '@/hooks/useChannelsQuery';
import type { ScheduleSlot, ScheduleTemplate } from '@/api/schedule';
import { toast } from 'sonner';

type TabKey = 'calendar' | 'playlists' | 'templates';

export default function SchedulePage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabKey>('calendar');
  const [selectedChannelId, setSelectedChannelId] = useState<string>('');
  const [selectedSlot, setSelectedSlot] = useState<ScheduleSlot | null>(null);
  const [isSlotModalOpen, setIsSlotModalOpen] = useState(false);
  const [isCopyModalOpen, setIsCopyModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | undefined>(undefined);

  // React Query hooks
  const { data: channels = [], isLoading: channelsLoading } = useChannels();
  const { data: templates = [], isLoading: templatesLoading } = useScheduleTemplates();
  const { data: playlists = [] } = usePlaylists();
  const applyTemplateMutation = useApplyTemplate();

  const flatControlClassName =
    'text-foreground bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] hover:bg-[color:var(--color-surface-hover)] hover:border-[color:var(--color-border-strong)] transition-colors';
  
  // Auto-select first channel
  useEffect(() => {
    if (channels.length > 0 && !selectedChannelId) {
      setSelectedChannelId(channels[0].id);
    }
  }, [channels, selectedChannelId]);

  // Handlers
  const handleSlotClick = (slot: ScheduleSlot) => {
    setSelectedSlot(slot);
    setIsSlotModalOpen(true);
  };

  const handleDateClick = (date: Date) => {
    console.log('[Schedule] handleDateClick:', date);
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
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)] transition-colors duration-300">
      <ResponsiveHeader />
      <div className="mx-auto max-w-7xl px-4 py-6 sm:py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
                <CalendarDays className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-bold text-[color:var(--color-text)]">
                  {t('schedule.title', 'Расписание трансляций')}
                </h1>
                <p className="text-[color:var(--color-text-muted)] mt-1">
                  {t('schedule.subtitle', 'Управление расписанием и плейлистами')}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Channel Selector */}
              {channelsLoading ? (
                <Skeleton className="w-48 h-10 rounded-lg" />
              ) : channels.length > 0 ? (
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-[color:var(--color-text)] whitespace-nowrap">
                    {t('schedule.channel', 'Канал')}:
                  </span>
                  <Select
                    size="sm"
                    aria-label={t('schedule.selectChannel', 'Выберите канал')}
                    selectedKeys={selectedChannelId ? [selectedChannelId] : []}
                    onChange={(e) => setSelectedChannelId(e.target.value)}
                    className="w-40"
                    classNames={{
                      trigger: "text-foreground",
                      value: "text-foreground",
                      selectorIcon: "text-foreground",
                    }}
                    popoverProps={{
                      classNames: {
                        content: "bg-[color:var(--color-panel)] border border-[color:var(--color-border)]",
                      },
                    }}
                    disableSelectorIconRotation
                  >
                    {channels.map((channel) => (
                      <SelectItem 
                        key={channel.id}
                        hideSelectedIcon
                      >
                        {channel.name}
                      </SelectItem>
                    ))}
                  </Select>
                </div>
              ) : null}
              
              {/* Quick Template Apply */}
              {templates.length > 0 && activeTab === 'calendar' && (
                <Dropdown>
                  <DropdownTrigger>
                    <Button
                      variant="flat"
                      className={flatControlClassName}
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
                    className={flatControlClassName}
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
          <StatCard
            title={t('schedule.todaySlots', 'Слотов сегодня')}
            value={12}
            icon={CalendarDays}
            color="violet"
          />
          <StatCard
            title={t('schedule.playlists', 'Плейлистов')}
            value={playlists.length}
            icon={List}
            color="blue"
          />
          <StatCard
            title={t('schedule.templates', 'Шаблонов')}
            value={templates.length}
            icon={Copy}
            color="amber"
          />
          <StatCard
            title={t('schedule.weekSlots', 'Слотов на неделю')}
            value={84}
            icon={RefreshCw}
            color="emerald"
          />
        </motion.div>

        {/* Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] shadow-md shadow-black/5 p-4 sm:p-6">
            <div className="flex flex-wrap items-center gap-2 sm:gap-3 pb-3">
              <button
                type="button"
                onClick={() => setActiveTab('calendar')}
                className={`px-3 sm:px-4 py-2 text-sm font-medium rounded-full transition-all border flex items-center gap-2
                  ${activeTab === 'calendar'
                    ? 'bg-[color:var(--color-accent)]/15 border-[color:var(--color-accent)] text-[color:var(--color-accent)] shadow-sm shadow-[color:var(--color-accent)]/30'
                    : 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-border)] text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:border-[color:var(--color-border-strong)]'}
                `}
              >
                <div className="p-1.5 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 shadow-sm shadow-violet-500/25">
                  <CalendarDays className="w-4 h-4 text-white" />
                </div>
                <span>{t('schedule.tabs.calendar', 'Календарь')}</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('playlists')}
                className={`px-3 sm:px-4 py-2 text-sm font-medium rounded-full transition-all border flex items-center gap-2
                  ${activeTab === 'playlists'
                    ? 'bg-[color:var(--color-accent)]/15 border-[color:var(--color-accent)] text-[color:var(--color-accent)] shadow-sm shadow-[color:var(--color-accent)]/30'
                    : 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-border)] text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:border-[color:var(--color-border-strong)]'}
                `}
              >
                <div className="p-1.5 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 shadow-sm shadow-blue-500/25">
                  <List className="w-4 h-4 text-white" />
                </div>
                <span>{t('schedule.tabs.playlists', 'Плейлисты')}</span>
                <Badge size="sm" color="primary" variant="flat">
                  {playlists.length}
                </Badge>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('templates')}
                className={`px-3 sm:px-4 py-2 text-sm font-medium rounded-full transition-all border flex items-center gap-2
                  ${activeTab === 'templates'
                    ? 'bg-[color:var(--color-accent)]/15 border-[color:var(--color-accent)] text-[color:var(--color-accent)] shadow-sm shadow-[color:var(--color-accent)]/30'
                    : 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-border)] text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] hover:border-[color:var(--color-border-strong)]'}
                `}
              >
                <div className="p-1.5 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 shadow-sm shadow-amber-500/25">
                  <Copy className="w-4 h-4 text-white" />
                </div>
                <span>{t('schedule.tabs.templates', 'Шаблоны')}</span>
                <Badge size="sm" color="secondary" variant="flat">
                  {templates.length}
                </Badge>
              </button>
            </div>

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
                {activeTab === 'calendar' &&
                  (channelsLoading ? (
                    <div className="p-8 text-center">
                      <Skeleton className="w-full h-[500px] rounded-xl" />
                    </div>
                  ) : !selectedChannelId ? (
                    <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] shadow-md shadow-black/5">
                      <Card className="bg-transparent shadow-none border-none">
                        <div className="p-8 text-center">
                          <p className="text-[color:var(--color-text-muted)]">
                            {channels.length === 0
                              ? t(
                                  'schedule.noChannels',
                                  'Нет доступных каналов. Добавьте канал для управления расписанием.'
                                )
                              : t('schedule.selectChannelPrompt', 'Выберите канал для просмотра расписания')}
                          </p>
                        </div>
                      </Card>
                    </div>
                  ) : (
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
                  ))}

                {activeTab === 'playlists' && <PlaylistManager channelId={selectedChannelId} />}

                {activeTab === 'templates' && (
                  <TemplatesSection
                    templates={templates}
                    isLoading={templatesLoading}
                    onApply={handleApplyTemplate}
                  />
                )}
              </motion.div>
            </AnimatePresence>
          </div>
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
          <div
            key={i}
            className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5"
          >
            <Card className="bg-transparent shadow-none border-none">
              <div className="p-6 animate-pulse">
                <div className="h-6 bg-[color:var(--color-surface-muted)] rounded w-3/4 mb-3" />
                <div className="h-4 bg-[color:var(--color-surface-muted)] rounded w-full mb-2" />
                <div className="h-4 bg-[color:var(--color-surface-muted)] rounded w-2/3" />
              </div>
            </Card>
          </div>
        ))}
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
        <Card className="bg-transparent shadow-none border-none">
          <div className="p-12 text-center">
            <Copy className="w-16 h-16 mx-auto text-[color:var(--color-text-muted)] mb-4" />
            <h3 className="text-xl font-semibold text-[color:var(--color-text)] mb-2">
              {t('schedule.noTemplates', 'Нет шаблонов')}
            </h3>
            <p className="text-[color:var(--color-text-muted)] mb-4">
              {t('schedule.noTemplatesDesc', 'Создайте шаблон расписания для быстрого применения')}
            </p>
            <Button color="primary" startContent={<Plus className="w-4 h-4" />}>
              {t('schedule.createTemplate', 'Создать шаблон')}
            </Button>
          </div>
        </Card>
      </div>
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
          <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5">
            <Card className="bg-transparent shadow-none border-none">
              <div className="p-6">
                <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-2">
                  {template.name}
                </h3>
                {template.description && (
                  <p className="text-sm text-[color:var(--color-text-muted)] mb-4">
                    {template.description}
                  </p>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[color:var(--color-text-muted)]">
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
              </div>
            </Card>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
