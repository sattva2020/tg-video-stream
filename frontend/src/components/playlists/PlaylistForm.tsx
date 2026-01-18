import React from 'react';
import { useForm } from 'react-hook-form';
import { Playlist, PlaylistCreate, PlaylistUpdate } from '../../api/playlists';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Textarea } from '../ui/Textarea';
import { Switch } from '../ui/Switch';
import { Label } from '../ui/Label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/Select";
import { FileBrowser } from '../media/FileBrowser';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/Dialog';

interface PlaylistFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  playlist?: Playlist; // If provided, edit mode
  onSubmit: (data: PlaylistCreate | PlaylistUpdate) => Promise<void>;
}

export const PlaylistForm: React.FC<PlaylistFormProps> = ({
  open,
  onOpenChange,
  playlist,
  onSubmit,
}) => {
  const [fileBrowserOpen, setFileBrowserOpen] = React.useState(false);
  const { register, handleSubmit, reset, setValue, watch, formState: { errors, isSubmitting } } = useForm<PlaylistCreate>({
    defaultValues: {
      name: '',
      description: '',
      is_public: false,
      color: '#8B5CF6',
      icon: 'folder',
      source_type: 'manual',
      source_url: '',
    },
  });

  React.useEffect(() => {
    if (open) {
      if (playlist) {
        setValue('name', playlist.name);
        setValue('description', playlist.description || '');
        setValue('is_public', playlist.is_public);
        setValue('color', playlist.color);
        setValue('icon', playlist.icon);
        setValue('source_type', playlist.source_type || 'manual');
        setValue('source_url', playlist.source_url || '');
      } else {
        reset({
          name: '',
          description: '',
          is_public: false,
          color: '#8B5CF6',
          icon: 'folder',
          source_type: 'manual',
          source_url: '',
        });
      }
    }
  }, [open, playlist, setValue, reset]);

  const isPublic = watch('is_public');
  const sourceType = watch('source_type');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{playlist ? 'Edit Playlist' : 'Create Playlist'}</DialogTitle>
          <DialogDescription>
            {playlist ? 'Update playlist details.' : 'Create a new collection of tracks.'}
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              {...register('name', { required: 'Name is required' })}
              placeholder="My Awesome Playlist"
            />
            {errors.name && <span className="text-sm text-red-500">{errors.name.message}</span>}
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="What's in this playlist?"
            />
          </div>

          <div className="space-y-2">
            <Label>Source Type</Label>
            <Select
              onValueChange={(value) => setValue('source_type', value)}
              value={sourceType}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select source type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="manual">Manual (Drag & Drop)</SelectItem>
                <SelectItem value="folder">Local Folder</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {sourceType === 'folder' && (
            <div className="space-y-2">
              <Label>Folder Path</Label>
              <div className="flex gap-2">
                <Input
                  {...register('source_url', { required: sourceType === 'folder' })}
                  placeholder="/music/my-playlist"
                  readOnly
                />
                <Button type="button" variant="outline" onClick={() => setFileBrowserOpen(true)}>
                  Browse
                </Button>
              </div>
            </div>
          )}
          
          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="is_public" className="flex flex-col space-y-1">
              <span>Public Playlist</span>
              <span className="font-normal text-xs text-muted-foreground">
                Anyone with the link can view this playlist.
              </span>
            </Label>
            <Switch
              id="is_public"
              checked={isPublic}
              onCheckedChange={(checked) => setValue('is_public', checked)}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="color">Color</Label>
            <div className="flex gap-2">
              {['#8B5CF6', '#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#EC4899'].map((c) => (
                <div
                  key={c}
                  className={`w-6 h-6 rounded-full cursor-pointer border-2 ${watch('color') === c ? 'border-black dark:border-white' : 'border-transparent'}`}
                  style={{ backgroundColor: c }}
                  onClick={() => setValue('color', c)}
                />
              ))}
            </div>
            <Input type="hidden" {...register('color')} />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {playlist ? 'Save Changes' : 'Create Playlist'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>

      <FileBrowser
        open={fileBrowserOpen}
        onOpenChange={setFileBrowserOpen}
        onSelect={(path) => {
          setValue('source_url', path);
          // Auto-fill name if empty
          const currentName = watch('name');
          if (!currentName) {
            const folderName = path.split('/').pop() || path;
            setValue('name', folderName, { shouldValidate: true });
          }
        }}
        currentPath={watch('source_url')}
      />
    </Dialog>
  );
};
