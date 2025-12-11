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
  FolderPlus,
  Folder,
  FolderOpen,
  ChevronDown,
  ChevronRight,
  MoveRight,
  ArrowUpDown,
  HardDrive,
  Globe,
  GripVertical,
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
  useDeletePlaylist,
  usePlaylistGroups,
  useCreatePlaylistGroup,
  useDeletePlaylistGroup,
  useMovePlaylistToGroup,
} from '../../hooks/useScheduleQuery';
import { useMediaFolders, useScanFolder } from '../../hooks/useMediaQuery';
import type { Playlist, PlaylistItem, PlaylistGroup } from '../../api/schedule';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
} from '@dnd-kit/core';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

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
  { value: 'folder', label: 'Локальная папка', icon: HardDrive },
];

const PRESET_COLORS = [
  '#8B5CF6', '#EC4899', '#EF4444', '#F97316', '#EAB308',
  '#22C55E', '#14B8A6', '#06B6D4', '#3B82F6', '#6366F1',
];

// Get icon component by source type
function getSourceIcon(sourceType: string) {
  switch (sourceType) {
    case 'youtube':
      return Youtube;
    case 'm3u':
      return FileText;
    case 'folder':
    case 'local':
      return HardDrive;
    case 'url':
      return Globe;
    case 'manual':
    default:
      return ListMusic;
  }
}

// ==================== Draggable Playlist Card ====================

interface DraggablePlaylistCardProps {
  playlist: Playlist;
  groups: PlaylistGroup[];
  isSelected: boolean;
  onSelect?: (playlist: Playlist) => void;
  onEdit: (playlist: Playlist) => void;
  onDelete: (playlist: Playlist) => void;
  onMoveToGroup: (playlistId: string, groupId: string | undefined) => void;
  t: any;
}

const DraggablePlaylistCard: React.FC<DraggablePlaylistCardProps> = ({
  playlist,
  groups,
  isSelected,
  onSelect,
  onEdit,
  onDelete,
  onMoveToGroup,
  t,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: playlist.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const SourceIcon = getSourceIcon(playlist.source_type);

  return (
    <div ref={setNodeRef} style={style}>
      <Card
        isPressable={!!onSelect}
        isHoverable
        className={`
          overflow-hidden
          ${isSelected ? 'ring-2 ring-violet-500' : ''}
          ${isDragging ? 'shadow-lg ring-2 ring-primary' : ''}
        `}
        onPress={() => onSelect?.(playlist)}
      >
        <CardBody className="p-4">
          {/* Color bar */}
          <div
            className="absolute top-0 left-0 right-0 h-1"
            style={{ backgroundColor: playlist.color }}
          />

          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              {/* Drag handle */}
              <div
                {...attributes}
                {...listeners}
                className="cursor-grab active:cursor-grabbing p-1 -ml-1 text-default-400 hover:text-default-600 touch-none"
              >
                <GripVertical className="w-4 h-4" />
              </div>
              <div
                className="p-2 rounded-lg"
                style={{ backgroundColor: `${playlist.color}20` }}
              >
                <SourceIcon className="w-5 h-5" style={{ color: playlist.color }} />
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
              <DropdownMenu aria-label="Действия">
                <DropdownItem key="edit" startContent={<Edit className="w-4 h-4" />} onPress={() => onEdit(playlist)}>
                  {t('common.edit', 'Редактировать')}
                </DropdownItem>
                <DropdownItem key="move" startContent={<MoveRight className="w-4 h-4" />}>
                  <Dropdown>
                    <DropdownTrigger>
                      <span>{t('playlist.moveToGroup', 'Переместить в группу')}</span>
                    </DropdownTrigger>
                    <DropdownMenu 
                      aria-label="Выбрать группу"
                      items={[
                        { id: 'ungrouped', name: 'Без группы' },
                        ...groups
                      ]}
                    >
                      {(item: any) => (
                        <DropdownItem 
                          key={item.id} 
                          onPress={() => onMoveToGroup(playlist.id, item.id === 'ungrouped' ? undefined : item.id)}
                        >
                          {item.name}
                        </DropdownItem>
                      )}
                    </DropdownMenu>
                  </Dropdown>
                </DropdownItem>
                <DropdownItem key="delete" className="text-danger" color="danger" startContent={<Trash2 className="w-4 h-4" />} onPress={() => onDelete(playlist)}>
                  {t('common.delete', 'Удалить')}
                </DropdownItem>
              </DropdownMenu>
            </Dropdown>
          </div>

          {playlist.description && (
            <p className="mt-2 text-xs text-default-500 line-clamp-2">
              {playlist.description}
            </p>
          )}

          <div className="flex items-center gap-2 mt-3">
            {playlist.is_shuffled && (
              <Chip size="sm" variant="flat" startContent={<Shuffle className="w-3 h-3" />}>
                Shuffle
              </Chip>
            )}
            {playlist.group_name && (
              <Chip size="sm" variant="flat" color="secondary" startContent={<Folder className="w-3 h-3" />}>
                {playlist.group_name}
              </Chip>
            )}
          </div>
        </CardBody>
      </Card>
    </div>
  );
};

// ==================== Droppable Group ====================

interface DroppableGroupProps {
  id: string;
  children: React.ReactNode;
  className?: string;
}

const DroppableGroup: React.FC<DroppableGroupProps> = ({ id, children, className }) => {
  const { isOver, setNodeRef } = useDroppable({
    id: `group-${id}`,
  });

  return (
    <div
      ref={setNodeRef}
      className={`
        ${className || ''}
        ${isOver ? 'ring-2 ring-primary ring-offset-2 bg-primary/5' : ''}
        transition-all duration-200
      `}
    >
      {children}
    </div>
  );
};

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

  // Для работы с папками
  const [selectedFolder, setSelectedFolder] = useState<string>('');
  const [autoScan, setAutoScan] = useState(false);
  const { data: folders = [], isLoading: foldersLoading } = useMediaFolders();
  const { data: scanResult, isLoading: scanLoading } = useScanFolder(
    selectedFolder,
    true, // recursive
    autoScan && formData.source_type === 'folder'
  );

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
      setSelectedFolder('');
      setAutoScan(false);
    }
  }, [playlist, isOpen]);

  const handleSubmit = async () => {
    let items: PlaylistItem[] = [];

    // Для folder - берём из результата сканирования
    if (formData.source_type === 'folder' && scanResult) {
      items = scanResult.files.map(file => ({
        url: `file://${file.file_path}`,
        title: file.title || file.file_path.split('/').pop() || 'Untitled',
        duration: file.duration,
        type: 'local' as const,
      }));
    } else if (formData.source_type === 'manual') {
      // Для manual - парсим из текста
      items = formData.items_text
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
    }

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
          {formData.source_type !== 'manual' && formData.source_type !== 'folder' && (
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

          {/* Folder path (for local files) */}
          {formData.source_type === 'folder' && (
            <div className="space-y-3">
              <label className="text-sm font-medium text-default-700 mb-2 block">
                {t('playlist.folderPath', 'Выберите папку с музыкой')}
              </label>
              
              {/* Список папок */}
              {foldersLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => (
                    <Skeleton key={i} className="h-12 rounded-lg" />
                  ))}
                </div>
              ) : folders && folders.length > 0 ? (
                <div className="max-h-64 overflow-y-auto space-y-2 border border-default-200 rounded-lg p-3">
                  {folders.map((folder) => (
                    <button
                      key={folder.path}
                      onClick={() => {
                        setSelectedFolder(folder.path);
                        setFormData(f => ({ ...f, source_url: folder.path }));
                        setAutoScan(true);
                      }}
                      className={`
                        w-full flex items-center gap-3 p-3 rounded-lg transition-all
                        ${formData.source_url === folder.path
                          ? 'bg-violet-500 text-white'
                          : 'bg-default-100 hover:bg-default-200'
                        }
                      `}
                    >
                      <Folder className="w-5 h-5 shrink-0" />
                      <div className="flex-1 text-left">
                        <p className="font-medium text-sm">{folder.path}</p>
                        <p className={`text-xs ${formData.source_url === folder.path ? 'text-white/70' : 'text-default-500'}`}>
                          {folder.audio_count} файлов
                          {folder.has_subdirs && ' • Содержит подпапки'}
                        </p>
                      </div>
                      {formData.source_url === folder.path && (
                        <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center">
                          <div className="w-2 h-2 rounded-full bg-white" />
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="p-8 text-center border border-dashed border-default-300 rounded-lg">
                  <FolderOpen className="w-12 h-12 mx-auto mb-3 text-default-400" />
                  <p className="text-sm text-default-500">
                    {t('playlist.noFolders', 'Папки с музыкой не найдены')}
                  </p>
                  <p className="text-xs text-default-400 mt-1">
                    {t('playlist.checkMusicRoot', 'Проверьте настройку MUSIC_ROOT')}
                  </p>
                </div>
              )}

              {/* Статус сканирования */}
              {scanLoading && (
                <div className="flex items-center gap-2 p-3 bg-violet-50 dark:bg-violet-900/20 rounded-lg">
                  <div className="animate-spin">
                    <Music className="w-4 h-4 text-violet-600" />
                  </div>
                  <p className="text-sm text-violet-600">
                    {t('playlist.scanning', 'Сканирование папки...')}
                  </p>
                </div>
              )}

              {/* Результат сканирования */}
              {scanResult && !scanLoading && (
                <div className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                  <p className="text-sm text-green-600 font-medium">
                    ✓ Найдено треков: {scanResult.total}
                  </p>
                  <p className="text-xs text-green-600/70 mt-1">
                    {t('playlist.autoAdded', 'Треки будут добавлены автоматически при создании')}
                  </p>
                </div>
              )}
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
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [sortBy, setSortBy] = useState<'name' | 'date' | 'duration'>('name');

  const { data: playlists = [], isLoading } = usePlaylists(channelId);
  const { data: groups = [] } = usePlaylistGroups(channelId);
  const deleteMutation = useDeletePlaylist();
  const createGroupMutation = useCreatePlaylistGroup();
  const deleteGroupMutation = useDeletePlaylistGroup();
  const moveToGroupMutation = useMovePlaylistToGroup();

  // Toggle group expand/collapse
  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  // Sort function
  const sortPlaylists = (items: Playlist[]) => {
    return [...items].sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'date') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      if (sortBy === 'duration') return b.total_duration - a.total_duration;
      return 0;
    });
  };

  // Group playlists by group_id
  const groupedPlaylists = useMemo(() => {
    const grouped: Record<string, Playlist[]> = { ungrouped: [] };
    groups.forEach(g => { grouped[g.id] = []; });

    playlists.forEach(p => {
      if (p.group_id && grouped[p.group_id]) {
        grouped[p.group_id].push(p);
      } else {
        grouped.ungrouped.push(p);
      }
    });

    // Sort each group
    Object.keys(grouped).forEach(key => {
      grouped[key] = sortPlaylists(grouped[key]);
    });

    return grouped;
  }, [playlists, groups, sortBy]);

  // Filtered playlists (for search)
  const filteredPlaylists = useMemo(() => {
    if (!search.trim()) return null; // Use grouped view
    const query = search.toLowerCase();
    return sortPlaylists(playlists.filter(p =>
      p.name.toLowerCase().includes(query) ||
      p.description?.toLowerCase().includes(query)
    ));
  }, [playlists, search, sortBy]);

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

  const handleCreateGroup = async () => {
    const name = prompt(t('playlist.groupName', 'Название группы:'));
    if (name) {
      await createGroupMutation.mutateAsync({ name, channel_id: channelId });
    }
  };

  const handleDeleteGroup = async (group: PlaylistGroup) => {
    if (confirm(t('playlist.confirmDeleteGroup', `Удалить группу "${group.name}"? Плейлисты будут перемещены в "Без группы".`))) {
      await deleteGroupMutation.mutateAsync(group.id);
    }
  };

  const handleMoveToGroup = async (playlistId: string, groupId: string | undefined) => {
    await moveToGroupMutation.mutateAsync({ playlistId, groupId });
  };

  // DnD sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  // DnD state
  const [activePlaylist, setActivePlaylist] = useState<Playlist | null>(null);

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const playlist = playlists.find(p => p.id === active.id);
    setActivePlaylist(playlist || null);
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    setActivePlaylist(null);

    if (!over) return;

    const playlistId = active.id as string;
    const overId = over.id as string;

    // Check if dropped over a group
    if (overId.startsWith('group-')) {
      const groupId = overId.replace('group-', '');
      await handleMoveToGroup(playlistId, groupId === 'ungrouped' ? undefined : groupId);
    }
  };

  // Render playlist card using DraggablePlaylistCard
  const renderPlaylistCard = (playlist: Playlist) => (
    <DraggablePlaylistCard
      key={playlist.id}
      playlist={playlist}
      groups={groups}
      isSelected={selectedPlaylistId === playlist.id}
      onSelect={onSelectPlaylist}
      onEdit={handleEdit}
      onDelete={handleDelete}
      onMoveToGroup={handleMoveToGroup}
      t={t}
    />
  );

  return (
    <div className="h-full">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
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
                  {playlists.length} {t('playlist.count', 'плейлистов')} • {groups.length} {t('playlist.groupsCount', 'групп')}
                </p>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                variant="flat"
                onPress={handleCreateGroup}
                startContent={<FolderPlus className="w-4 h-4" />}
              >
                {t('playlist.createGroup', 'Группа')}
              </Button>
              <Button
                color="primary"
                onPress={handleCreate}
                startContent={<Plus className="w-4 h-4" />}
              >
                {t('playlist.create', 'Создать')}
              </Button>
            </div>
          </div>

          {/* Search and Sort */}
          <div className="flex gap-2">
            <Input
              className="flex-1"
              placeholder={t('playlist.search', 'Поиск плейлистов...')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              startContent={<Search className="w-4 h-4 text-default-400" />}
              isClearable
              onClear={() => setSearch('')}
            />
            <Dropdown>
              <DropdownTrigger>
                <Button variant="flat" startContent={<ArrowUpDown className="w-4 h-4" />}>
                  {t('playlist.sort', 'Сортировка')}
                </Button>
              </DropdownTrigger>
              <DropdownMenu aria-label="Сортировка" selectedKeys={[sortBy]} onAction={(key) => setSortBy(key as typeof sortBy)}>
                <DropdownItem key="name">{t('playlist.sortByName', 'По имени')}</DropdownItem>
                <DropdownItem key="date">{t('playlist.sortByDate', 'По дате')}</DropdownItem>
                <DropdownItem key="duration">{t('playlist.sortByDuration', 'По длительности')}</DropdownItem>
              </DropdownMenu>
            </Dropdown>
          </div>

          {/* Content */}
          {isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-32 rounded-xl" />
              ))}
            </div>
          ) : filteredPlaylists ? (
            // Search results (flat list)
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <AnimatePresence mode="popLayout">
                {filteredPlaylists.length === 0 ? (
                  <div className="col-span-full py-12 text-center">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-default-100 flex items-center justify-center">
                      <Music className="w-8 h-8 text-default-400" />
                    </div>
                    <h3 className="text-lg font-semibold">{t('playlist.notFound', 'Ничего не найдено')}</h3>
                    <p className="text-sm text-default-500 mt-1">{t('playlist.tryDifferentSearch', 'Попробуйте другой запрос')}</p>
                  </div>
                ) : (
                  filteredPlaylists.map(renderPlaylistCard)
                )}
              </AnimatePresence>
            </div>
          ) : (
            // Grouped view
            <div className="space-y-4">
              {/* Groups */}
              {groups.map(group => (
                <DroppableGroup key={group.id} id={group.id} className="border rounded-xl overflow-hidden dark:border-gray-700">
                  <button
                    onClick={() => toggleGroup(group.id)}
                    className="w-full flex items-center justify-between p-3 hover:bg-default-100 transition-colors"
                    title={t('playlist.toggleGroup', 'Свернуть/развернуть группу')}
                  >
                    <div className="flex items-center gap-3">
                      {expandedGroups.has(group.id) ? (
                        <FolderOpen className="w-5 h-5" style={{ color: group.color }} />
                      ) : (
                        <Folder className="w-5 h-5" style={{ color: group.color }} />
                      )}
                      <span className="font-medium">{group.name}</span>
                      <Chip size="sm" variant="flat">{groupedPlaylists[group.id]?.length || 0}</Chip>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onClick={(e) => { e.stopPropagation(); handleDeleteGroup(group); }}
                        title={t('common.delete', 'Удалить')}
                      >
                        <Trash2 className="w-4 h-4 text-danger" />
                      </Button>
                      {expandedGroups.has(group.id) ? (
                        <ChevronDown className="w-5 h-5 text-default-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-default-400" />
                      )}
                    </div>
                  </button>

                  <AnimatePresence>
                    {expandedGroups.has(group.id) && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="border-t dark:border-gray-700"
                      >
                        <div className="p-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                          {groupedPlaylists[group.id]?.length === 0 ? (
                            <p className="col-span-full text-sm text-default-500 py-4 text-center">
                              {t('playlist.emptyGroup', 'Перетащите плейлист сюда')}
                            </p>
                          ) : (
                            groupedPlaylists[group.id]?.map(renderPlaylistCard)
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </DroppableGroup>
              ))}

              {/* Ungrouped playlists */}
              <DroppableGroup id="ungrouped" className="border rounded-xl overflow-hidden dark:border-gray-700">
                <button
                  onClick={() => toggleGroup('ungrouped')}
                  className="w-full flex items-center justify-between p-3 hover:bg-default-100 transition-colors"
                  title={t('playlist.toggleGroup', 'Свернуть/развернуть группу')}
                >
                  <div className="flex items-center gap-3">
                    {expandedGroups.has('ungrouped') ? (
                      <FolderOpen className="w-5 h-5 text-default-400" />
                    ) : (
                      <Folder className="w-5 h-5 text-default-400" />
                    )}
                    <span className="font-medium">{t('playlist.ungrouped', 'Без группы')}</span>
                    <Chip size="sm" variant="flat">{groupedPlaylists.ungrouped.length}</Chip>
                  </div>
                  {expandedGroups.has('ungrouped') ? (
                    <ChevronDown className="w-5 h-5 text-default-400" />
                  ) : (
                    <ChevronRight className="w-5 h-5 text-default-400" />
                  )}
                </button>

                <AnimatePresence>
                  {expandedGroups.has('ungrouped') && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="border-t dark:border-gray-700"
                    >
                      <div className="p-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {groupedPlaylists.ungrouped.length === 0 ? (
                          <p className="col-span-full text-sm text-default-500 py-4 text-center">
                            {t('playlist.emptyGroup', 'Перетащите плейлист сюда')}
                          </p>
                        ) : (
                          groupedPlaylists.ungrouped.map(renderPlaylistCard)
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </DroppableGroup>


              {/* Empty state */}
              {playlists.length === 0 && (
                <div className="py-12 text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-default-100 flex items-center justify-center">
                    <Music className="w-8 h-8 text-default-400" />
                  </div>
                  <h3 className="text-lg font-semibold">{t('playlist.empty', 'Плейлист пуст')}</h3>
                  <p className="text-sm text-default-500 mt-1">{t('playlist.createFirst', 'Создайте первый плейлист')}</p>
                </div>
              )}
            </div>
          )}

        </div>
        <DragOverlay>
          {activePlaylist ? (
            <div className="opacity-80 rotate-3 scale-105 cursor-grabbing">
              <Card className="w-64 shadow-xl ring-2 ring-primary">
                <CardBody className="p-3 flex items-center gap-3">
                  <div
                    className="p-2 rounded-lg"
                    style={{ backgroundColor: `${activePlaylist.color}20` }}
                  >
                    {(() => {
                      const SourceIcon = getSourceIcon(activePlaylist.source_type);
                      return <SourceIcon className="w-5 h-5" style={{ color: activePlaylist.color }} />;
                    })()}
                  </div>
                  <div>
                    <h3 className="font-semibold text-sm line-clamp-1">{activePlaylist.name}</h3>
                    <p className="text-xs text-default-500">{activePlaylist.items_count} треков</p>
                  </div>
                </CardBody>
              </Card>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>

      {/* Editor Modal */}
      <PlaylistEditorModal
        isOpen={editorOpen}
        onClose={() => setEditorOpen(false)}
        playlist={editingPlaylist}
        channelId={channelId}
      />
    </div>
  );
};

export default PlaylistManager;
