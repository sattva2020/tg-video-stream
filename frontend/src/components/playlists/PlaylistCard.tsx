import React from 'react';
import { Playlist } from '../../api/playlists';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Clock, List, MoreVertical, Play, Copy, Trash, Edit, Share2, Sparkles } from 'lucide-react';
import { formatDuration } from '../../utils/format';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/DropdownMenu';

interface PlaylistCardProps {
  playlist: Playlist;
  isOwner: boolean;
  onEdit?: (playlist: Playlist) => void;
  onDelete?: (playlist: Playlist) => void;
  onClone?: (playlist: Playlist) => void;
  onPlay?: (playlist: Playlist) => void;
  onView?: (playlist: Playlist) => void;
}

export const PlaylistCard: React.FC<PlaylistCardProps> = ({
  playlist,
  isOwner,
  onEdit,
  onDelete,
  onClone,
  onPlay,
  onView,
}) => {
  return (
    <Card className="group relative overflow-hidden rounded-2xl border bg-card/90 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg">
      <div className="absolute inset-x-0 top-0 h-20 bg-gradient-to-r from-primary/10 via-transparent to-emerald-100/40 dark:from-primary/20 dark:to-emerald-900/30" aria-hidden />

      <CardHeader className="pb-3">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => onView?.(playlist)}>
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center text-white shadow-sm ring-2 ring-white/60 transition-transform group-hover:scale-105"
              style={{ backgroundColor: playlist.color || '#22c55e' }}
            >
              <Sparkles size={20} />
            </div>
            <div className="space-y-1">
              <CardTitle className="text-lg font-semibold group-hover:text-primary transition-colors">{playlist.name}</CardTitle>
              <div className="flex items-center gap-2">
                {playlist.is_public && (
                  <Badge variant="secondary" className="h-6 text-xs">
                    Public
                  </Badge>
                )}
                <Badge variant="outline" className="h-6 text-xs capitalize">{playlist.source_type || 'manual'}</Badge>
              </div>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical size={16} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {isOwner ? (
                <>
                  <DropdownMenuItem onClick={() => onEdit?.(playlist)}>
                    <Edit className="mr-2 h-4 w-4" /> Edit
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => onDelete?.(playlist)} className="text-red-600">
                    <Trash className="mr-2 h-4 w-4" /> Delete
                  </DropdownMenuItem>
                </>
              ) : (
                <DropdownMenuItem onClick={() => onClone?.(playlist)}>
                  <Copy className="mr-2 h-4 w-4" /> Clone to Library
                </DropdownMenuItem>
              )}
              {playlist.is_public && (
                <DropdownMenuItem
                  onClick={() => {
                    navigator.clipboard.writeText(`${window.location.origin}/playlists/${playlist.share_code}`);
                  }}
                >
                  <Share2 className="mr-2 h-4 w-4" /> Copy Link
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="pb-3 space-y-4">
        <p className="text-sm text-muted-foreground line-clamp-2 min-h-[2.5rem]">
          {playlist.description || 'No description'}
        </p>

        <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
          <div className="inline-flex items-center gap-2 rounded-full bg-muted px-3 py-1">
            <List size={14} />
            <span>{playlist.items_count} items</span>
          </div>
          <div className="inline-flex items-center gap-2 rounded-full bg-muted px-3 py-1">
            <Clock size={14} />
            <span>{formatDuration(playlist.total_duration)}</span>
          </div>
          {playlist.source_url && (
            <div className="inline-flex items-center gap-2 rounded-full bg-muted px-3 py-1">
              <Share2 size={14} />
              <span className="truncate max-w-[160px]" title={playlist.source_url}>
                {playlist.source_url}
              </span>
            </div>
          )}
        </div>
      </CardContent>

      <CardFooter className="pt-0 flex gap-2">
        <Button className="flex-1" onClick={() => onPlay?.(playlist)}>
          <Play className="mr-2 h-4 w-4" /> Play Now
        </Button>
        <Button variant="secondary" onClick={() => onView?.(playlist)}>
          Details
        </Button>
      </CardFooter>
    </Card>
  );
};
