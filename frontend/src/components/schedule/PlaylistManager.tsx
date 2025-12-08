/**
 * PlaylistManager — Компонент для управления плейлистами.
 * 
 * Функции:
 * - Список плейлистов
 * - Создание/редактирование плейлистов
 * - Добавление треков
 * - Импорт из YouTube/m3u
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Music,
  Plus,
  Edit,
  Trash2,
  MoreVertical,
  Search,
  ExternalLink,
  Shuffle,
  ListMusic,
  Youtube,
  FileText,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Input,
  Card,
  CardBody,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Skeleton,
  Chip,
  Modal,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Textarea,
} from '@heroui/react';
import { 
  usePlaylists, 
  useCreatePlaylist, 
  useUpdatePlaylist, 
  useDeletePlaylist 
} from '../../hooks/useScheduleQuery';
import type { Playlist, PlaylistItem } from '../../api/schedule';

// ==================== Types ====================

interface PlaylistManagerProps {
  channelId?: string;
  onSelectPlaylist?: (playlist: Playlist) => void;
  selectedPlaylistId?: string;
}

interface PlaylistEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  playlist?: Playlist | null;
  channelId?: string;
}

// ==================== Constants ====================

const SOURCE_TYPES = [
  { value: 'manual', label: 'Вручную', icon: ListMusic },
  { value: 'youtube', label: 'YouTube Playlist', icon: Youtube },
  { value: 'm3u', label: 'M3U файл', icon: FileText },
];

const PRESET_COLORS = [
  '#8B5CF6', '#EC4899', '#EF4444', '#F97316', '#EAB308',
  '#22C55E', '#14B8A6', '#06B6D4', '#3B82F6', '#6366F1',
];

// ==================== Helper Functions ====================

function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) {
    return `${h}ч ${m}м`;
  }
  return `${m} мин`;
}

// ==================== Playlist Editor Modal ====================

const PlaylistEditorModal: React.FC<PlaylistEditorModalProps> = ({
  isOpen,
  onClose,
  playlist,
  channelId,
}) => {
  const { t } = useTranslation();
  const isEditMode = !!playlist;

  const createMutation = useCreatePlaylist();
  const updateMutation = useUpdatePlaylist();
  const isLoading = createMutation.isPending || updateMutation.isPending;

  const [formData, setFormData] = useState({
    name: playlist?.name || '',
    description: playlist?.description || '',
    color: playlist?.color || PRESET_COLORS[0],
    source_type: playlist?.source_type || 'manual',
    source_url: playlist?.source_url || '',
    is_shuffled: playlist?.is_shuffled || false,
    items_text: '', // For manual entry
  });

  React.useEffect(() => {
    if (playlist) {
      setFormData({
        name: playlist.name,
        description: playlist.description || '',
        color: playlist.color,
        source_type: playlist.source_type,
        source_url: playlist.source_url || '',
        is_shuffled: playlist.is_shuffled,
        items_text: playlist.items.map(i => `${i.url} | ${i.title || ''}`).join('\n'),
      });
    } else {
      setFormData({
        name: '',
        description: '',
        color: PRESET_COLORS[Math.floor(Math.random() * PRESET_COLORS.length)],
        source_type: 'manual',
        source_url: '',
        is_shuffled: false,
        items_text: '',
      });
    }
  }, [playlist, isOpen]);

  const handleSubmit = async () => {
    // Parse items from text
    const items: PlaylistItem[] = formData.items_text
      .split('\n')
      .filter(line => line.trim())
      .map(line => {
        const parts = line.split('|').map(p => p.trim());
        return {
          url: parts[0] || '',
          title: parts[1] || parts[0] || 'Untitled',
          type: parts[0]?.includes('youtube') ? 'youtube' : 'unknown',
        };
      });

    if (isEditMode && playlist) {
      await updateMutation.mutateAsync({
        playlistId: playlist.id,
        data: {
          name: formData.name,
          description: formData.description || undefined,
          color: formData.color,
          items,
          is_shuffled: formData.is_shuffled,
        },
      });
    } else {
      await createMutation.mutateAsync({
        name: formData.name,
        description: formData.description || undefined,
        channel_id: channelId,
        color: formData.color,
        source_type: formData.source_type,
        source_url: formData.source_url || undefined,
        items,
        is_shuffled: formData.is_shuffled,
      });
    }

    onClose();
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={onClose} 
      size="2xl"
      backdrop="blur"
      classNames={{
        backdrop: "bg-black/50",
      }}
    >
      <ModalContent className="bg-white dark:bg-gray-900 shadow-xl">
        <ModalHeader className="flex items-center gap-3">
          <div 
            className="p-2 rounded-lg"
            style={{ backgroundColor: formData.color }}
          >
            <Music className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {isEditMode ? t('playlist.edit', 'Редактирование') : t('playlist.create', 'Новый плейлист')}
            </h2>
          </div>
        </ModalHeader>

        <ModalBody className="gap-4">
          <div>
            <label className="text-sm font-medium text-default-700 mb-2 block">
              {t('playlist.name', 'Название')} <span className="text-danger">*</span>
            </label>
            <Input
              placeholder={t('playlist.namePlaceholder', 'Мой плейлист')}
              value={formData.name}
              onChange={(e) => setFormData(f => ({ ...f, name: e.target.value }))}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-default-700 mb-2 block">
              {t('playlist.description', 'Описание')}
            </label>
            <Textarea
              placeholder={t('playlist.descriptionPlaceholder', 'Описание плейлиста...')}
              value={formData.description}
              onChange={(e) => setFormData(f => ({ ...f, description: e.target.value }))}
              minRows={2}
            />
          </div>

          {/* Color picker */}
          <div>
            <label className="text-sm font-medium text-default-700 mb-2 block">
              {t('playlist.color', 'Цвет')}
            </label>
            <div className="flex flex-wrap gap-2">
              {PRESET_COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => setFormData(f => ({ ...f, color }))}
                  className={`
                    w-8 h-8 rounded-lg transition-all
                    ${formData.color === color ? 'ring-2 ring-offset-2 ring-violet-500 scale-110' : 'hover:scale-105'}
                  `}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </div>

          {/* Source type */}
          <div>
            <label className="text-sm font-medium text-default-700 mb-2 block">
              {t('playlist.sourceType', 'Источник')}
            </label>
            <div className="flex gap-2">
              {SOURCE_TYPES.map((type) => {
                const Icon = type.icon;
                return (
                  <button
                    key={type.value}
                    onClick={() => setFormData(f => ({ ...f, source_type: type.value }))}
                    className={`
                      flex items-center gap-2 px-4 py-2 rounded-lg transition-all
                      ${formData.source_type === type.value
                        ? 'bg-violet-500 text-white'
                        : 'bg-default-100 hover:bg-default-200'}
                    `}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-sm">{type.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Source URL (for youtube/m3u) */}
          {formData.source_type !== 'manual' && (
            <div>
              <label className="text-sm font-medium text-default-700 mb-2 block">
                {formData.source_type === 'youtube' 
                  ? t('playlist.youtubeUrl', 'URL плейлиста YouTube')
                  : t('playlist.m3uUrl', 'URL m3u файла')}
              </label>
              <Input
                placeholder={formData.source_type === 'youtube'
                  ? 'https://youtube.com/playlist?list=...'
                  : 'https://example.com/playlist.m3u'}
                value={formData.source_url}
                onChange={(e) => setFormData(f => ({ ...f, source_url: e.target.value }))}
                startContent={<ExternalLink className="w-4 h-4 text-default-400" />}
              />
            </div>
          )}

          {/* Manual items entry */}
          {formData.source_type === 'manual' && (
            <div>
              <label className="text-sm font-medium text-default-700 mb-2 block">
                {t('playlist.items', 'Треки (по одному на строку)')}
              </label>
              <Textarea
                placeholder={`https://youtube.com/watch?v=... | Название трека
https://youtube.com/watch?v=... | Другой трек`}
                value={formData.items_text}
                onChange={(e) => setFormData(f => ({ ...f, items_text: e.target.value }))}
                minRows={5}
              />
            </div>
          )}

          {/* Shuffle option */}
          <div className="flex items-center gap-3 p-3 rounded-lg bg-default-100">
            <button
              onClick={() => setFormData(f => ({ ...f, is_shuffled: !f.is_shuffled }))}
              className={`
                p-2 rounded-lg transition-colors
                ${formData.is_shuffled ? 'bg-violet-500 text-white' : 'bg-default-200'}
              `}
            >
              <Shuffle className="w-4 h-4" />
            </button>
            <div>
              <p className="font-medium text-sm">{t('playlist.shuffle', 'Перемешивать')}</p>
              <p className="text-xs text-default-500">
                {t('playlist.shuffleDesc', 'Треки будут воспроизводиться в случайном порядке')}
              </p>
            </div>
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
            isDisabled={!formData.name.trim()}
          >
            {isEditMode ? t('common.save', 'Сохранить') : t('common.create', 'Создать')}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

// ==================== Main Component ====================

export const PlaylistManager: React.FC<PlaylistManagerProps> = ({
  channelId,
  onSelectPlaylist,
  selectedPlaylistId,
}) => {
  const { t } = useTranslation();
  const [search, setSearch] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingPlaylist, setEditingPlaylist] = useState<Playlist | null>(null);

  const { data: playlists = [], isLoading } = usePlaylists(channelId);
  const deleteMutation = useDeletePlaylist();

  // Filtered playlists
  const filteredPlaylists = useMemo(() => {
    if (!search.trim()) return playlists;
    const query = search.toLowerCase();
    return playlists.filter(p => 
      p.name.toLowerCase().includes(query) ||
      p.description?.toLowerCase().includes(query)
    );
  }, [playlists, search]);

  const handleEdit = (playlist: Playlist) => {
    setEditingPlaylist(playlist);
    setEditorOpen(true);
  };

  const handleCreate = () => {
    setEditingPlaylist(null);
    setEditorOpen(true);
  };

  const handleDelete = async (playlist: Playlist) => {
    if (confirm(t('playlist.confirmDelete', `Удалить плейлист "${playlist.name}"?`))) {
      await deleteMutation.mutateAsync(playlist.id);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 shadow-lg shadow-violet-500/25">
            <ListMusic className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[color:var(--color-text)]">
              {t('playlist.title', 'Плейлисты')}
            </h2>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              {playlists.length} {t('playlist.count', 'плейлистов')}
            </p>
          </div>
        </div>

        <Button
          color="primary"
          onPress={handleCreate}
          startContent={<Plus className="w-4 h-4" />}
        >
          {t('playlist.create', 'Создать')}
        </Button>
      </div>

      {/* Search */}
      <Input
        placeholder={t('playlist.search', 'Поиск плейлистов...')}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        startContent={<Search className="w-4 h-4 text-default-400" />}
        isClearable
        onClear={() => setSearch('')}
      />

      {/* Playlist Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          // Skeleton
          Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))
        ) : filteredPlaylists.length === 0 ? (
          // Empty state
          <div className="col-span-full py-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-default-100 flex items-center justify-center">
              <Music className="w-8 h-8 text-default-400" />
            </div>
            <h3 className="text-lg font-semibold">
              {search ? t('playlist.notFound', 'Ничего не найдено') : t('playlist.empty', 'Нет плейлистов')}
            </h3>
            <p className="text-sm text-default-500 mt-1">
              {search 
                ? t('playlist.tryDifferentSearch', 'Попробуйте другой запрос')
                : t('playlist.createFirst', 'Создайте первый плейлист')}
            </p>
          </div>
        ) : (
          // Playlist cards
          <AnimatePresence mode="popLayout">
            {filteredPlaylists.map((playlist) => (
              <motion.div
                key={playlist.id}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                layout
              >
                <Card
                  isPressable={!!onSelectPlaylist}
                  isHoverable
                  className={`
                    overflow-hidden
                    ${selectedPlaylistId === playlist.id ? 'ring-2 ring-violet-500' : ''}
                  `}
                  onPress={() => onSelectPlaylist?.(playlist)}
                >
                  <CardBody className="p-4">
                    {/* Color bar */}
                    <div 
                      className="absolute top-0 left-0 right-0 h-1"
                      style={{ backgroundColor: playlist.color }}
                    />

                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div 
                          className="p-2 rounded-lg"
                          style={{ backgroundColor: `${playlist.color}20` }}
                        >
                          <Music className="w-5 h-5" style={{ color: playlist.color }} />
                        </div>
                        <div>
                          <h3 className="font-semibold text-[color:var(--color-text)]">
                            {playlist.name}
                          </h3>
                          <div className="flex items-center gap-2 mt-1 text-xs text-default-500">
                            <span>{playlist.items_count} треков</span>
                            <span>•</span>
                            <span>{formatDuration(playlist.total_duration)}</span>
                          </div>
                        </div>
                      </div>

                      <Dropdown>
                        <DropdownTrigger>
                          <Button isIconOnly size="sm" variant="light">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownTrigger>
                        <DropdownMenu aria-label="Playlist actions">
                          <DropdownItem
                            key="edit"
                            startContent={<Edit className="w-4 h-4" />}
                            onPress={() => handleEdit(playlist)}
                          >
                            {t('common.edit', 'Редактировать')}
                          </DropdownItem>
                          <DropdownItem
                            key="delete"
                            color="danger"
                            startContent={<Trash2 className="w-4 h-4" />}
                            onPress={() => handleDelete(playlist)}
                          >
                            {t('common.delete', 'Удалить')}
                          </DropdownItem>
                        </DropdownMenu>
                      </Dropdown>
                    </div>

                    {playlist.description && (
                      <p className="mt-2 text-sm text-default-500 line-clamp-2">
                        {playlist.description}
                      </p>
                    )}

                    {/* Tags */}
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {playlist.is_shuffled && (
                        <Chip size="sm" variant="flat" startContent={<Shuffle className="w-3 h-3" />}>
                          Shuffle
                        </Chip>
                      )}
                      {playlist.source_type !== 'manual' && (
                        <Chip size="sm" variant="flat" color="secondary">
                          {playlist.source_type}
                        </Chip>
                      )}
                    </div>
                  </CardBody>
                </Card>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Editor Modal */}
      <PlaylistEditorModal
        isOpen={editorOpen}
        onClose={() => {
          setEditorOpen(false);
          setEditingPlaylist(null);
        }}
        playlist={editingPlaylist}
        channelId={channelId}
      />
    </div>
  );
};

export default PlaylistManager;
