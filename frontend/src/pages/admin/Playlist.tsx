import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Reorder, useDragControls, motion } from 'framer-motion';
import { Card, CardBody, CardHeader, Button, Input } from '@heroui/react';
import { Plus, Trash2, GripVertical, RefreshCw } from 'lucide-react';
import { adminApi } from '../../api/admin';
import { useToast } from '../../hooks/useToast';

interface PlaylistItemProps {
  item: string;
  index: number;
  onRemove: () => void;
  isDisabled: boolean;
}

const PlaylistItem: React.FC<PlaylistItemProps> = ({ item, index, onRemove, isDisabled }) => {
  const { t } = useTranslation();
  const dragControls = useDragControls();

  return (
    <Reorder.Item
      value={item}
      dragListener={false}
      dragControls={dragControls}
      className="flex items-center justify-between p-3 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-outline)] hover:border-[color:var(--color-accent)] transition-colors select-none"
      whileDrag={{
        scale: 1.02,
        boxShadow: '0 10px 30px rgba(0,0,0,0.2)',
        zIndex: 50,
      }}
      layout
      transition={{ duration: 0.2 }}
    >
      <div className="flex items-center gap-3 flex-1 overflow-hidden">
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
        <span 
          className="truncate text-[color:var(--color-text)]" 
          title={item}
        >
          {item}
        </span>
      </div>
      
      <div className="flex items-center gap-1 ml-2 shrink-0">
        <Button
          isIconOnly
          size="sm"
          variant="light"
          color="danger"
          onPress={onRemove}
          isDisabled={isDisabled}
          aria-label={t('playlist.delete', 'Удалить')}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>
    </Reorder.Item>
  );
};

const Playlist: React.FC = () => {
  const { t } = useTranslation();
  const toast = useToast();
  const [items, setItems] = useState<string[]>([]);
  const [newItem, setNewItem] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchPlaylist = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.getPlaylist();
      setItems(data.items || []);
    } catch (err) {
      toast.error(t('playlist.loadError', 'Не удалось загрузить плейлист'));
    } finally {
      setLoading(false);
    }
  }, [toast, t]);

  useEffect(() => {
    fetchPlaylist();
  }, [fetchPlaylist]);

  const savePlaylist = async (newItems: string[]) => {
    setLoading(true);
    try {
      await adminApi.updatePlaylist(newItems);
      setItems(newItems);
      toast.success(t('playlist.saved', 'Плейлист сохранён'));
    } catch (err) {
      toast.error(t('playlist.saveError', 'Не удалось сохранить плейлист'));
    } finally {
      setLoading(false);
    }
  };

  const handleReorder = (newItems: string[]) => {
    setItems(newItems);
    // Save immediately after reorder
    savePlaylist(newItems);
  };

  const handleAdd = () => {
    if (!newItem.trim()) return;
    const updated = [...items, newItem.trim()];
    savePlaylist(updated);
    setNewItem('');
  };

  const handleRemove = (index: number) => {
    const updated = items.filter((_, i) => i !== index);
    savePlaylist(updated);
  };

  return (
    <Card className="bg-[color:var(--color-panel)] border border-[color:var(--color-outline)]">
      <CardHeader className="flex justify-between items-center">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-[color:var(--color-text)]">
            {t('playlist.management', 'Управление плейлистом')}
          </h2>
          {items.length > 0 && (
            <span className="text-xs text-[color:var(--color-text-muted)] bg-[color:var(--color-surface-muted)] px-2 py-1 rounded-full">
              {t('playlist.dragHint', '⇅ Перетащите для сортировки')}
            </span>
          )}
        </div>
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
      </CardHeader>
      
      <CardBody className="space-y-4">
        <div className="flex gap-3">
          <Input
            type="text"
            value={newItem}
            onChange={(e) => setNewItem(e.target.value)}
            placeholder={t('playlist.urlPlaceholder', 'Введите YouTube URL')}
            classNames={{
              input: 'text-[color:var(--color-text)]',
              inputWrapper: 'bg-[color:var(--color-surface-muted)] border-[color:var(--color-outline)]',
            }}
            className="flex-1"
            isDisabled={loading}
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          />
          <Button
            onPress={handleAdd}
            isDisabled={loading || !newItem.trim()}
            color="primary"
            startContent={<Plus className="w-4 h-4" />}
          >
            {t('playlist.addItem', 'Добавить')}
          </Button>
        </div>

        {items.length === 0 ? (
          <div className="text-[color:var(--color-text-muted)] text-center py-6 italic">
            {t('playlist.empty', 'Плейлист пуст')}
          </div>
        ) : (
          <Reorder.Group
            axis="y"
            values={items}
            onReorder={handleReorder}
            className="space-y-2"
            layoutScroll
          >
            {items.map((item, index) => (
              <PlaylistItem
                key={item}
                item={item}
                index={index}
                onRemove={() => handleRemove(index)}
                isDisabled={loading}
              />
            ))}
          </Reorder.Group>
        )}
      </CardBody>
    </Card>
  );
};

export default Playlist;
