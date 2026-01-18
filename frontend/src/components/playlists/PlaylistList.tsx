import React from 'react';
import { Playlist } from '../../api/playlists';
import { PlaylistCard } from './PlaylistCard';
import { Skeleton } from '../ui/Skeleton';

interface PlaylistListProps {
  playlists: Playlist[];
  isLoading: boolean;
  currentUserId?: string;
  onEdit: (playlist: Playlist) => void;
  onDelete: (playlist: Playlist) => void;
  onClone: (playlist: Playlist) => void;
  onPlay: (playlist: Playlist) => void;
  onView: (playlist: Playlist) => void;
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
}) => {
  const safePlaylists = Array.isArray(playlists) ? playlists : [];

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
        />
      ))}
    </div>
  );
};
