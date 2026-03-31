import React, { useState, useMemo } from 'react';
import { Playlist } from '../../api/playlists';
import { PlaylistCard } from './PlaylistCard';
import { Skeleton } from '../ui/Skeleton';
import { Button } from '../ui/Button';
import { Checkbox } from '../ui/Checkbox';
import { Trash2, Copy, FolderOpen, X, CheckSquare, Square } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/DropdownMenu';

interface PlaylistListProps {
  playlists: Playlist[];
  isLoading: boolean;
  currentUserId?: string;
  onEdit: (playlist: Playlist) => void;
  onDelete: (playlist: Playlist) => void;
  onClone: (playlist: Playlist) => void;
  onPlay: (playlist: Playlist) => void;
  onView: (playlist: Playlist) => void;
  onBulkDelete?: (playlists: Playlist[]) => void;
  onBulkMove?: (playlists: Playlist[], targetFolderId?: string) => void;
  onBulkCopy?: (playlists: Playlist[]) => void;
}

export const PlaylistList: React.FC<PlaylistListProps> = ({
  playlists,
  isLoading,
  currentUserId,
  onEdit,
  onDelete,
  onClone,
  onPlay,
  onView,
  onBulkDelete,
  onBulkMove,
  onBulkCopy,
}) => {
  const safePlaylists = Array.isArray(playlists) ? playlists : [];
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isSelectionEnabled, setIsSelectionEnabled] = useState(false);

  const selectedPlaylists = useMemo(() => {
    return safePlaylists.filter((p) => selectedIds.has(p.id));
  }, [safePlaylists, selectedIds]);

  const allSelected = safePlaylists.length > 0 && selectedIds.size === safePlaylists.length;
  const someSelected = selectedIds.size > 0 && !allSelected;

  const handleToggleSelection = (playlist: Playlist, selected: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (selected) {
        next.add(playlist.id);
      } else {
        next.delete(playlist.id);
      }
      return next;
    });
  };

  const handleSelectAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(safePlaylists.map((p) => p.id)));
    }
  };

  const handleExitSelectionMode = () => {
    setIsSelectionEnabled(false);
    setSelectedIds(new Set());
  };

  const handleBulkAction = (action: 'delete' | 'move' | 'copy') => {
    if (selectedPlaylists.length === 0) return;

    try {
      switch (action) {
        case 'delete':
          onBulkDelete?.(selectedPlaylists);
          break;
        case 'move':
          onBulkMove?.(selectedPlaylists);
          break;
        case 'copy':
          onBulkCopy?.(selectedPlaylists);
          break;
      }
      setSelectedIds(new Set());
      setIsSelectionEnabled(false);
    } catch (error) {
      // Error handling is done by the parent component
    }
  };

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-[200px] rounded-xl border bg-card text-card-foreground shadow p-6">
            <div className="flex items-center gap-4 mb-4">
              <Skeleton className="h-12 w-12 rounded-lg" />
              <div className="space-y-2">
                <Skeleton className="h-4 w-[150px]" />
                <Skeleton className="h-4 w-[100px]" />
              </div>
            </div>
            <Skeleton className="h-20 w-full" />
          </div>
        ))}
      </div>
    );
  }

  if (safePlaylists.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        No playlists found. Create one to get started!
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Selection Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {isSelectionEnabled ? (
              <Checkbox
                checked={allSelected}
                onCheckedChange={handleSelectAll}
                className="mr-2"
              />
            ) : (
              <CheckSquare size={20} className="mr-2" />
            )}
            <Button
              variant={isSelectionEnabled ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                if (isSelectionEnabled) {
                  handleExitSelectionMode();
                } else {
                  setIsSelectionEnabled(true);
                }
              }}
            >
              {isSelectionEnabled ? (
                <>
                  <X className="mr-2 h-4 w-4" /> Exit Selection
                </>
              ) : (
                <>
                  <CheckSquare className="mr-2 h-4 w-4" /> Select Multiple
                </>
              )}
            </Button>
          </div>
          {selectedIds.size > 0 && (
            <span className="text-sm text-muted-foreground">
              {selectedIds.size} {selectedIds.size === 1 ? 'playlist' : 'playlists'} selected
            </span>
          )}
        </div>

        {/* Bulk Actions */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="default" size="sm">
                  Bulk Actions ({selectedIds.size})
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {onBulkDelete && (
                  <DropdownMenuItem
                    onClick={() => handleBulkAction('delete')}
                    className="text-red-600"
                  >
                    <Trash2 className="mr-2 h-4 w-4" /> Delete Selected
                  </DropdownMenuItem>
                )}
                {onBulkMove && (
                  <DropdownMenuItem onClick={() => handleBulkAction('move')}>
                    <FolderOpen className="mr-2 h-4 w-4" /> Move to Folder
                  </DropdownMenuItem>
                )}
                {onBulkCopy && (
                  <DropdownMenuItem onClick={() => handleBulkAction('copy')}>
                    <Copy className="mr-2 h-4 w-4" /> Duplicate Selected
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleExitSelectionMode}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>

      {/* Playlist Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {safePlaylists.map((playlist) => (
          <PlaylistCard
            key={playlist.id}
            playlist={playlist}
            isOwner={playlist.user_id === currentUserId}
            onEdit={onEdit}
            onDelete={onDelete}
            onClone={onClone}
            onPlay={onPlay}
            onView={onView}
            isSelected={selectedIds.has(playlist.id)}
            isSelectionEnabled={isSelectionEnabled}
            onSelectionChange={handleToggleSelection}
          />
        ))}
      </div>
    </div>
  );
};
