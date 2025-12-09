import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Reorder, useDragControls, motion } from 'framer-motion';
import { Card, CardBody, CardHeader, Button, Input, Select, SelectItem, Chip } from '@heroui/react';
import { Plus, Trash2, Youtube, FileAudio, GripVertical, RefreshCw } from 'lucide-react';
import { client } from '../api/client';
import { useToast } from '../hooks/useToast';

interface PlaylistItem {
    id: string;
    url: string;
    title: string;
    type: 'youtube' | 'local';
    position: number;
    created_at: string;
}

interface LocalFile {
    name: string;
    path: string;
    size: number;
}

interface PlaylistManagerProps {
    token: string;
}

interface DraggableItemProps {
    item: PlaylistItem;
    index: number;
    onDelete: () => void;
    isDisabled: boolean;
}

const DraggablePlaylistItem: React.FC<DraggableItemProps> = ({ item, index, onDelete, isDisabled }) => {
    const { t } = useTranslation();
    const dragControls = useDragControls();

    return (
        <Reorder.Item
            value={item}
            dragListener={false}
            dragControls={dragControls}
            className="flex items-center justify-between p-3 bg-[color:var(--color-surface-muted)] rounded-lg border border-[color:var(--color-outline)] hover:border-[color:var(--color-accent)] transition-colors select-none"
            whileDrag={{
                scale: 1.02,
                boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
                zIndex: 50,
            }}
            layout
            transition={{ duration: 0.2 }}
        >
            <div className="flex items-center gap-3 overflow-hidden flex-1">
                {/* Drag handle */}
                <motion.div
                    className="cursor-grab active:cursor-grabbing touch-none p-1 -ml-1 rounded hover:bg-[color:var(--color-outline)]"
                    onPointerDown={(e) => {
                        if (!isDisabled) {
                            dragControls.start(e);
                        }
                    }}
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                >
                    <GripVertical className="w-4 h-4 text-[color:var(--color-text-muted)]" />
                </motion.div>
                
                <span className="text-[color:var(--color-text-muted)] font-mono w-6 text-center shrink-0">
                    {index + 1}
                </span>
                <div className="truncate flex-1">
                    <div className="flex items-center gap-2">
                        <Chip
                            size="sm"
                            variant="flat"
                            color={item.type === 'local' ? 'success' : 'danger'}
                            startContent={item.type === 'local' ? <FileAudio className="w-3 h-3" /> : <Youtube className="w-3 h-3" />}
                        >
                            {item.type === 'local' ? 'FILE' : 'YT'}
                        </Chip>
                        <span className="font-medium text-[color:var(--color-text)] truncate">
                            {item.title || item.url}
                        </span>
                    </div>
                    <div className="text-xs text-[color:var(--color-text-muted)] truncate ml-14">
                        {item.url}
                    </div>
                </div>
            </div>
            <Button
                isIconOnly
                size="sm"
                variant="light"
                color="danger"
                onPress={onDelete}
                isDisabled={isDisabled}
                aria-label={t('playlist.delete', 'Удалить')}
            >
                <Trash2 className="w-4 h-4" />
            </Button>
        </Reorder.Item>
    );
};

const PlaylistManager: React.FC<PlaylistManagerProps> = ({ token }) => {
    const { t } = useTranslation();
    const toast = useToast();
    const [items, setItems] = useState<PlaylistItem[]>([]);
    const [newUrl, setNewUrl] = useState('');
    const [sourceType, setSourceType] = useState<'youtube' | 'local'>('youtube');
    const [localFiles, setLocalFiles] = useState<LocalFile[]>([]);
    const [selectedFile, setSelectedFile] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    const fetchPlaylist = useCallback(async () => {
        setLoading(true);
        try {
            const response = await client.get('/api/playlist/');
            setItems(response.data);
        } catch (err) {
            console.error('Failed to fetch playlist', err);
            toast.error(t('playlist.loadError', 'Не удалось загрузить плейлист'));
        } finally {
            setLoading(false);
        }
    }, [toast, t]);

    const fetchLocalFiles = useCallback(async () => {
        try {
            const response = await client.get('/api/files/');
            setLocalFiles(response.data);
            if (response.data.length > 0) {
                setSelectedFile(response.data[0].path);
            }
        } catch (err) {
            console.error('Failed to fetch local files', err);
            toast.error(t('playlist.filesLoadError', 'Не удалось загрузить локальные файлы'));
        }
    }, [toast, t]);

    useEffect(() => {
        fetchPlaylist();
    }, [token, fetchPlaylist]);

    useEffect(() => {
        if (sourceType === 'local') {
            fetchLocalFiles();
        }
    }, [sourceType, fetchLocalFiles]);

    const handleReorder = (newItems: PlaylistItem[]) => {
        setItems(newItems);
    };

    const saveOrder = async () => {
        setSaving(true);
        try {
            // Update positions based on new order
            const updates = items.map((item, index) => ({
                id: item.id,
                position: index,
            }));
            await client.patch('/api/playlist/reorder', { items: updates });
            toast.success(t('playlist.orderSaved', 'Порядок сохранён'));
        } catch (err) {
            console.error('Failed to save order', err);
            toast.error(t('playlist.orderError', 'Не удалось сохранить порядок'));
            // Refresh to get actual order
            fetchPlaylist();
        } finally {
            setSaving(false);
        }
    };

    const handleAdd = async (e: React.FormEvent) => {
        e.preventDefault();
        
        const urlToAdd = sourceType === 'youtube' ? newUrl : selectedFile;
        if (!urlToAdd) return;

        setLoading(true);
        try {
            await client.post(
                '/api/playlist/',
                { 
                    url: urlToAdd,
                    type: sourceType,
                    title: sourceType === 'local' ? urlToAdd.split('/').pop() : undefined
                }
            );
            setNewUrl('');
            toast.success(t('playlist.trackAdded', 'Трек добавлен'));
            fetchPlaylist();
        } catch (err) {
            console.error('Failed to add item', err);
            toast.error(t('playlist.addError', 'Не удалось добавить трек'));
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: string) => {
        if (!confirm(t('playlist.confirmDelete', 'Удалить этот трек?'))) return;

        try {
            await client.delete(`/api/playlist/${id}`);
            toast.success(t('playlist.trackDeleted', 'Трек удалён'));
            fetchPlaylist();
        } catch (err) {
            console.error('Failed to delete item', err);
            toast.error(t('playlist.deleteError', 'Не удалось удалить трек'));
        }
    };

    return (
        <Card className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)]">
            <CardHeader className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold text-[color:var(--color-text)]">
                        {t('playlist.management', 'Управление плейлистом')}
                    </h2>
                    {items.length > 1 && (
                        <span className="text-xs text-[color:var(--color-text-muted)] bg-[color:var(--color-surface-muted)] px-2 py-1 rounded-full">
                            {t('playlist.dragHint', '⇅ Перетащите для сортировки')}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <Button
                        isIconOnly
                        size="sm"
                        variant="light"
                        onPress={fetchPlaylist}
                        isLoading={loading}
                        aria-label={t('common.refresh', 'Обновить')}
                    >
                        <RefreshCw className="w-4 h-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardBody className="space-y-6">
                <form onSubmit={handleAdd} className="space-y-4">
                    <div className="flex gap-4">
                        <Button
                            variant={sourceType === 'youtube' ? 'solid' : 'flat'}
                            color={sourceType === 'youtube' ? 'primary' : 'default'}
                            onPress={() => setSourceType('youtube')}
                            startContent={<Youtube className="w-4 h-4" />}
                            size="sm"
                        >
                            YouTube
                        </Button>
                        <Button
                            variant={sourceType === 'local' ? 'solid' : 'flat'}
                            color={sourceType === 'local' ? 'primary' : 'default'}
                            onPress={() => setSourceType('local')}
                            startContent={<FileAudio className="w-4 h-4" />}
                            size="sm"
                        >
                            {t('playlist.localFile', 'Локальный файл')}
                        </Button>
                    </div>

                    <div className="flex gap-3">
                        {sourceType === 'youtube' ? (
                            <Input
                                type="url"
                                value={newUrl}
                                onChange={(e) => setNewUrl(e.target.value)}
                                placeholder={t('playlist.youtubeUrlPlaceholder', 'Введите YouTube URL...')}
                                classNames={{
                                    input: 'text-[color:var(--color-text)]',
                                    inputWrapper: 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-outline)]',
                                }}
                                className="flex-1"
                                required={sourceType === 'youtube'}
                            />
                        ) : (
                            <Select
                                selectedKeys={selectedFile ? [selectedFile] : []}
                                onSelectionChange={(keys) => {
                                    const selected = Array.from(keys)[0] as string;
                                    if (selected) setSelectedFile(selected);
                                }}
                                placeholder={localFiles.length === 0 
                                    ? t('playlist.noFilesFound', 'Файлы не найдены') 
                                    : t('playlist.selectFile', 'Выберите файл')
                                }
                                classNames={{
                                    trigger: 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-outline)]',
                                    value: 'text-[color:var(--color-text)]',
                                }}
                                popoverProps={{
                                    classNames: {
                                        content: "bg-white dark:bg-gray-900 border border-default-200 dark:border-gray-700",
                                    },
                                }}
                                className="flex-1"
                                aria-label={t('playlist.selectFile', 'Выберите файл')}
                            >
                                {localFiles.map((file) => (
                                    <SelectItem key={file.path}>
                                        {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                                    </SelectItem>
                                ))}
                            </Select>
                        )}
                        <Button
                            type="submit"
                            isLoading={loading}
                            isDisabled={sourceType === 'local' && localFiles.length === 0}
                            color="primary"
                            startContent={!loading && <Plus className="w-4 h-4" />}
                        >
                            {t('playlist.addVideo', 'Добавить')}
                        </Button>
                    </div>
                </form>

                {items.length === 0 ? (
                    <p className="text-[color:var(--color-text-muted)] text-center py-6">
                        {t('playlist.emptyPlaylist', 'Плейлист пуст. Добавьте видео!')}
                    </p>
                ) : (
                    <Reorder.Group
                        axis="y"
                        values={items}
                        onReorder={handleReorder}
                        className="space-y-2"
                        layoutScroll
                    >
                        {items.map((item, index) => (
                            <DraggablePlaylistItem
                                key={item.id}
                                item={item}
                                index={index}
                                onDelete={() => handleDelete(item.id)}
                                isDisabled={loading || saving}
                            />
                        ))}
                    </Reorder.Group>
                )}
                
                {items.length > 1 && (
                    <div className="flex justify-end">
                        <Button
                            onPress={saveOrder}
                            isLoading={saving}
                            color="success"
                            variant="flat"
                            size="sm"
                        >
                            {t('playlist.saveOrder', 'Сохранить порядок')}
                        </Button>
                    </div>
                )}
            </CardBody>
        </Card>
    );
};

export default PlaylistManager;
