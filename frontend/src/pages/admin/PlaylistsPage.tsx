import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlaylistList } from '../../components/playlists/PlaylistList';
import { PlaylistForm } from '../../components/playlists/PlaylistForm';
import { Button } from '../../components/ui/Button';
import { Plus, Upload, Library, Sparkles } from 'lucide-react';
import { Playlist, PlaylistCreate, PlaylistUpdate, playlistsApi } from '../../api/playlists';
import { useToast } from '../../components/ui/use-toast';
import { useAuth } from '../../context/AuthContext';
import { formatDuration } from '../../utils/format';
import { AppLayout } from '../../components/layout';

export const PlaylistsPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toast } = useToast();

  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingPlaylist, setEditingPlaylist] = useState<Playlist | undefined>(undefined);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fetchPlaylists = async () => {
      setIsLoading(true);
      try {
        const response = await playlistsApi.getMyPlaylists();
        setPlaylists(Array.isArray(response) ? response : []);
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Не удалось загрузить плейлисты',
          variant: 'destructive',
        });
        setPlaylists([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPlaylists();
  }, [refreshTrigger, toast]);

  const handleCreate = async (data: PlaylistCreate | PlaylistUpdate) => {
    try {
      await playlistsApi.createPlaylist(data as PlaylistCreate);
      toast({ title: 'Success', description: 'Playlist created successfully' });
      setIsCreateOpen(false);
      setRefreshTrigger((prev) => prev + 1);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to create playlist', variant: 'destructive' });
    }
  };

  const handleUpdate = async (data: PlaylistUpdate) => {
    if (!editingPlaylist) return;
    try {
      await playlistsApi.updatePlaylist(editingPlaylist.id, data);
      toast({ title: 'Success', description: 'Playlist updated successfully' });
      setEditingPlaylist(undefined);
      setRefreshTrigger((prev) => prev + 1);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to update playlist', variant: 'destructive' });
    }
  };

  const handleEdit = (playlist: Playlist) => {
    setEditingPlaylist(playlist);
    setIsCreateOpen(false);
  };

  const handleDelete = async (playlist: Playlist) => {
    if (!confirm('Are you sure you want to delete this playlist?')) return;
    try {
      await playlistsApi.deletePlaylist(playlist.id);
      toast({ title: 'Success', description: 'Playlist deleted' });
      setRefreshTrigger((prev) => prev + 1);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to delete playlist', variant: 'destructive' });
    }
  };

  const handleClone = async (playlist: Playlist) => {
    try {
      await playlistsApi.clonePlaylist(playlist.id);
      toast({ title: 'Success', description: 'Playlist cloned to your library' });
      setRefreshTrigger((prev) => prev + 1);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to clone playlist', variant: 'destructive' });
    }
  };

  const handlePlay = async (playlist: Playlist) => {
    try {
      await playlistsApi.playPlaylist(playlist.id);
      toast({ title: 'Success', description: `Started playing playlist: ${playlist.name}` });
    } catch (error) {
      console.error('Failed to play playlist', error);
      toast({ title: 'Error', description: 'Failed to start playback', variant: 'destructive' });
    }
  };

  const handleView = (playlist: Playlist) => {
    navigate(`/user-playlists/${playlist.id}`);
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      await playlistsApi.importPlaylist(file);
      toast({ title: 'Success', description: 'Playlist imported successfully' });
      setRefreshTrigger((prev) => prev + 1);
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to import playlist', variant: 'destructive' });
    } finally {
      event.target.value = '';
    }
  };

  const safePlaylists = Array.isArray(playlists) ? playlists : [];
  const totalItems = safePlaylists.reduce((acc, p) => acc + (p.items_count || 0), 0);
  const totalDuration = safePlaylists.reduce((acc, p) => acc + (p.total_duration || 0), 0);

  return (
    <AppLayout>
    <div className="mx-auto max-w-6xl px-4 py-8 space-y-8">
      <div className="relative overflow-hidden rounded-3xl border bg-gradient-to-r from-indigo-50 via-white to-emerald-50 p-6 shadow-sm dark:from-slate-950 dark:via-slate-900 dark:to-emerald-950/30">
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_20%_20%,rgba(99,102,241,0.12),transparent_35%),radial-gradient(circle_at_80%_0%,rgba(16,185,129,0.12),transparent_25%)]" />
        <div className="relative flex flex-col gap-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 rounded-full bg-white/70 px-3 py-1 text-xs font-semibold text-indigo-700 ring-1 ring-indigo-100 dark:bg-slate-900/70 dark:text-indigo-200 dark:ring-indigo-900/40">
                <Library className="h-4 w-4" />
                Плейлисты
              </div>
              <h1 className="text-3xl font-semibold text-foreground">My Playlists</h1>
              <p className="text-sm text-muted-foreground max-w-2xl">
                Управляйте личной коллекцией и делитесь подборками. Импортируйте M3U или создайте новую подборку за пару кликов.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept=".m3u,.m3u8"
                onChange={handleFileChange}
              />
              <Button variant="outline" onClick={handleImportClick}>
                <Upload className="mr-2 h-4 w-4" /> Import M3U
              </Button>
              <Button onClick={() => setIsCreateOpen(true)}>
                <Plus className="mr-2 h-4 w-4" /> Create Playlist
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-2xl border bg-white/80 px-4 py-3 shadow-sm backdrop-blur dark:bg-slate-900/80">
              <p className="text-xs text-muted-foreground">Всего плейлистов</p>
              <p className="text-2xl font-semibold text-foreground">{safePlaylists.length}</p>
            </div>
            <div className="rounded-2xl border bg-white/80 px-4 py-3 shadow-sm backdrop-blur dark:bg-slate-900/80">
              <p className="text-xs text-muted-foreground">Треков в коллекции</p>
              <p className="text-2xl font-semibold text-foreground">{totalItems}</p>
            </div>
            <div className="rounded-2xl border bg-white/80 px-4 py-3 shadow-sm backdrop-blur dark:bg-slate-900/80">
              <p className="text-xs text-muted-foreground">Суммарная длительность</p>
              <p className="text-2xl font-semibold text-foreground">{formatDuration(totalDuration)}</p>
            </div>
          </div>
        </div>
      </div>

      {safePlaylists.length === 0 && !isLoading ? (
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed bg-muted/40 px-6 py-10 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Sparkles className="h-6 w-6" />
          </div>
          <div className="space-y-2 max-w-xl">
            <h2 className="text-lg font-semibold text-foreground">No playlists yet</h2>
            <p className="text-sm text-muted-foreground">
              Создайте первый плейлист или импортируйте M3U, чтобы начать управлять коллекцией.
            </p>
          </div>
          <div className="flex flex-wrap justify-center gap-3">
            <Button onClick={() => setIsCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" /> Create playlist
            </Button>
            <Button variant="outline" onClick={handleImportClick}>
              <Upload className="mr-2 h-4 w-4" /> Import M3U
            </Button>
          </div>
        </div>
      ) : (
        <PlaylistList
          playlists={safePlaylists}
          isLoading={isLoading}
          currentUserId={user?.id}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onClone={handleClone}
          onPlay={handlePlay}
          onView={handleView}
        />
      )}

      <PlaylistForm
        open={isCreateOpen || Boolean(editingPlaylist)}
        onOpenChange={(open) => {
          setIsCreateOpen(open);
          if (!open) setEditingPlaylist(undefined);
        }}
        playlist={editingPlaylist}
        onSubmit={editingPlaylist ? handleUpdate : handleCreate}
      />
    </div>
    </AppLayout>
  );
};
