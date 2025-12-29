import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DragDropContext, Droppable, Draggable, DropResult, DroppableProps } from '@hello-pangea/dnd';
import { Playlist, PlaylistEntry, playlistsApi } from '../../api/playlists';
import { FileBrowser } from '../media/FileBrowser';
import { MediaFile } from '../../api/media';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Skeleton } from '../ui/skeleton';
import { ArrowLeft, GripVertical, Trash2, Play, Plus, Download } from 'lucide-react';
import { useToast } from '../ui/use-toast';
import { Badge } from '../ui/badge';

export const PlaylistEditor: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [playlist, setPlaylist] = useState<Playlist | null>(null);
  const [loading, setLoading] = useState(true);
  const [items, setItems] = useState<PlaylistEntry[]>([]);
  const [fileBrowserOpen, setFileBrowserOpen] = useState(false);

  const loadPlaylist = useCallback(async (playlistId: string) => {
    try {
      setLoading(true);
      const data = await playlistsApi.getPlaylist(playlistId);
      setPlaylist(data);
      setItems(data.items || []);
    } catch (error) {
      console.error('Failed to load playlist', error);
      toast({
        title: 'Error',
        description: 'Failed to load playlist details',
        variant: 'destructive',
      });
      navigate('/user-playlists');
    } finally {
      setLoading(false);
    }
  }, [navigate, toast]);

  useEffect(() => {
    if (id) {
      loadPlaylist(id);
    }
  }, [id, loadPlaylist]);

  const handleFilesSelected = async (files: MediaFile[]) => {
    if (!playlist) return;
    
    const newEntries: PlaylistEntry[] = files.map(file => ({
      url: file.path,
      title: file.title || file.filename,
      duration: file.duration || 0,
      type: 'local'
    }));

    const newItems = [...items, ...newEntries];
    setItems(newItems);

    try {
      await playlistsApi.updatePlaylist(playlist.id, { items: newItems });
      toast({
        title: 'Added',
        description: `Added ${files.length} tracks to playlist`,
      });
    } catch (error) {
      console.error("Failed to add tracks", error);
      toast({
        title: 'Error',
        description: 'Failed to save changes',
        variant: 'destructive',
      });
      // Revert
      setItems(items);
    }
  };

  const handleDragEnd = async (result: DropResult) => {
    if (!result.destination || !playlist) return;

    const newItems = Array.from(items);
    const [reorderedItem] = newItems.splice(result.source.index, 1);
    newItems.splice(result.destination.index, 0, reorderedItem);

    setItems(newItems);
    
    // Update backend
    try {
        await playlistsApi.updatePlaylist(playlist.id, { items: newItems });
    } catch (error) {
        console.error("Failed to update playlist order", error);
        toast({
            title: 'Error',
            description: 'Failed to save new order',
            variant: 'destructive'
        });
    }
  };

  const handleRemoveEntry = async (index: number) => {
    if (!playlist) return;
    const newItems = [...items];
    newItems.splice(index, 1);
    setItems(newItems);
    
    try {
      await playlistsApi.updatePlaylist(playlist.id, { items: newItems });
      toast({
        title: 'Removed',
        description: 'Track removed from playlist',
      });
    } catch (error) {
      console.error("Failed to remove track", error);
      toast({
        title: 'Error',
        description: 'Failed to save changes',
        variant: 'destructive',
      });
      // Revert
      setItems(items);
    }
  };

  const handlePlay = async () => {
    if (!playlist) return;
    try {
      await playlistsApi.playPlaylist(playlist.id);
      toast({
        title: 'Success',
        description: `Started playing playlist: ${playlist.name}`,
      });
    } catch (error) {
      console.error('Failed to play playlist', error);
      toast({
        title: 'Error',
        description: 'Failed to start playback',
        variant: 'destructive',
      });
    }
  };

  const handleExport = async () => {
    if (!playlist) return;
    try {
      await playlistsApi.exportPlaylist(playlist.id, playlist.name);
      toast({
        title: 'Success',
        description: 'Playlist exported successfully',
      });
    } catch (error) {
      console.error('Failed to export playlist', error);
      toast({
        title: 'Error',
        description: 'Failed to export playlist',
        variant: 'destructive',
      });
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 p-8">
        <Skeleton className="h-12 w-1/3" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!playlist) return null;

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/user-playlists')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            {playlist.name}
            {playlist.is_public && <Badge variant="secondary">Public</Badge>}
          </h1>
          <p className="text-muted-foreground">{playlist.description}</p>
        </div>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" /> Export M3U
          </Button>
          <Button onClick={handlePlay}>
            <Play className="mr-2 h-4 w-4" /> Play All
          </Button>
          <Button variant="outline" onClick={() => setFileBrowserOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> Add Tracks
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Tracks ({items.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <DragDropContext onDragEnd={handleDragEnd}>
            {/**
             * TS 5.9 + React 18 могут ругаться на тип Droppable как JSX-элемента.
             * Приводим к совместимому типу, чтобы избежать ошибки компиляции.
             */}
            {(() => {
              const DroppableComponent = Droppable as unknown as React.ComponentType<DroppableProps>;
              return (
                <DroppableComponent droppableId="playlist-entries">
                  {(provided) => {
                    const placeholder = provided.placeholder as React.ReactElement | null;
                    return (
                      <div
                        {...provided.droppableProps}
                        ref={provided.innerRef}
                        className="space-y-2"
                      >
                        {items.map((item, index) => (
                          <Draggable key={`${index}-${item.url}`} draggableId={`${index}-${item.url}`} index={index}>
                            {(provided) => (
                              <div
                                ref={provided.innerRef}
                                {...provided.draggableProps}
                                className="flex items-center gap-4 p-3 bg-card border rounded-lg group hover:bg-accent/50 transition-colors"
                              >
                                <div {...provided.dragHandleProps} className="cursor-grab text-muted-foreground hover:text-foreground">
                                  <GripVertical className="h-5 w-5" />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <p className="font-medium truncate">{item.title || item.url.split('/').pop()}</p>
                                  <p className="text-xs text-muted-foreground truncate">{item.url}</p>
                                </div>
                                <div className="text-sm text-muted-foreground">
                                  {Math.floor(item.duration / 60)}:{String(Math.floor(item.duration % 60)).padStart(2, '0')}
                                </div>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive hover:bg-destructive/10"
                                  onClick={() => handleRemoveEntry(index)}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            )}
                          </Draggable>
                        ))}
                        {placeholder}
                        {items.length === 0 && (
                          <div className="text-center py-12 text-muted-foreground border-2 border-dashed rounded-lg">
                            No tracks in this playlist yet.
                          </div>
                        )}
                      </div>
                    );
                  }}
                </DroppableComponent>
              );
            })()}
          </DragDropContext>
        </CardContent>
      </Card>

      <FileBrowser
        open={fileBrowserOpen}
        onOpenChange={setFileBrowserOpen}
        mode="files"
        onFilesSelect={handleFilesSelected}
      />
    </div>
  );
};
