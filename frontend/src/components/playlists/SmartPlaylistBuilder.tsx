import React from 'react';
import { useForm } from 'react-hook-form';
import { SmartPlaylist, SmartPlaylistCreate, SmartPlaylistUpdate, SmartPlaylistCriteria } from '../../api/playlists';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/Dialog';

interface SmartPlaylistBuilderProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  smartPlaylist?: SmartPlaylist; // If provided, edit mode
  onSubmit: (data: SmartPlaylistCreate | SmartPlaylistUpdate) => Promise<void>;
}

export const SmartPlaylistBuilder: React.FC<SmartPlaylistBuilderProps> = ({
  open,
  onOpenChange,
  smartPlaylist,
  onSubmit,
}) => {
  const { register, handleSubmit, reset, setValue, watch, formState: { errors, isSubmitting } } = useForm<SmartPlaylistCreate>({
    defaultValues: {
      name: '',
      description: '',
      is_public: false,
      criteria: {
        filters: {
          duration_min: undefined,
          duration_max: undefined,
          type: undefined,
          tags: [],
          source: undefined,
        },
        order_by: 'date_added',
        order_direction: 'desc',
        limit: undefined,
        shuffle: false,
      },
      auto_update: false,
      auto_update_interval: 24,
    },
  });

  React.useEffect(() => {
    if (open) {
      if (smartPlaylist) {
        setValue('name', smartPlaylist.name);
        setValue('description', smartPlaylist.description || '');
        setValue('is_public', smartPlaylist.is_public);
        setValue('criteria', smartPlaylist.criteria);
        setValue('auto_update', smartPlaylist.auto_update);
        setValue('auto_update_interval', smartPlaylist.auto_update_interval);
      } else {
        reset({
          name: '',
          description: '',
          is_public: false,
          criteria: {
            filters: {
              duration_min: undefined,
              duration_max: undefined,
              type: undefined,
              tags: [],
              source: undefined,
            },
            order_by: 'date_added',
            order_direction: 'desc',
            limit: undefined,
            shuffle: false,
          },
          auto_update: false,
          auto_update_interval: 24,
        });
      }
    }
  }, [open, smartPlaylist, setValue, reset]);

  const criteria = watch('criteria');
  const autoUpdate = watch('auto_update');
  const filters = criteria?.filters || {};

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{smartPlaylist ? 'Edit Smart Playlist' : 'Create Smart Playlist'}</DialogTitle>
          <DialogDescription>
            {smartPlaylist
              ? 'Update smart playlist criteria and settings.'
              : 'Create a playlist that automatically updates based on criteria.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Basic Info */}
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              {...register('name', { required: 'Name is required' })}
              placeholder="My Smart Playlist"
            />
            {errors.name && <span className="text-sm text-red-500">{errors.name.message}</span>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Automatically curated content based on criteria"
            />
          </div>

          {/* Filters Section */}
          <div className="space-y-3 border-t pt-4">
            <Label className="text-base font-semibold">Filters</Label>

            {/* Duration Range */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="duration_min">Min Duration (minutes)</Label>
                <Input
                  id="duration_min"
                  type="number"
                  min="0"
                  {...register('criteria.filters.duration_min', {
                    valueAsNumber: true,
                    min: { value: 0, message: 'Must be positive' },
                  })}
                  placeholder="0"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration_max">Max Duration (minutes)</Label>
                <Input
                  id="duration_max"
                  type="number"
                  min="0"
                  {...register('criteria.filters.duration_max', {
                    valueAsNumber: true,
                    min: { value: 0, message: 'Must be positive' },
                  })}
                  placeholder="No limit"
                />
              </div>
            </div>

            {/* Type Filter */}
            <div className="space-y-2">
              <Label>Media Type</Label>
              <Select
                onValueChange={(value: string) => setValue('criteria.filters.type', value === 'all' ? undefined : value)}
                value={filters.type || 'all'}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="youtube">YouTube</SelectItem>
                  <SelectItem value="vimeo">Vimeo</SelectItem>
                  <SelectItem value="local">Local File</SelectItem>
                  <SelectItem value="stream">Stream</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Source Filter */}
            <div className="space-y-2">
              <Label htmlFor="source">Source URL Contains</Label>
              <Input
                id="source"
                {...register('criteria.filters.source')}
                placeholder="youtube.com, vimeo.com, etc."
              />
              <p className="text-xs text-muted-foreground">
                Only include items from sources containing this text
              </p>
            </div>
          </div>

          {/* Ordering Section */}
          <div className="space-y-3 border-t pt-4">
            <Label className="text-base font-semibold">Ordering</Label>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Sort By</Label>
                <Select
                  onValueChange={(value: 'date_added' | 'duration' | 'name' | 'source') =>
                    setValue('criteria.order_by', value)
                  }
                  value={criteria?.order_by || 'date_added'}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="date_added">Date Added</SelectItem>
                    <SelectItem value="duration">Duration</SelectItem>
                    <SelectItem value="name">Name</SelectItem>
                    <SelectItem value="source">Source</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Direction</Label>
                <Select
                  onValueChange={(value: 'asc' | 'desc') => setValue('criteria.order_direction', value)}
                  value={criteria?.order_direction || 'desc'}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="desc">Descending</SelectItem>
                    <SelectItem value="asc">Ascending</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="limit">Limit Items</Label>
              <Input
                id="limit"
                type="number"
                min="1"
                {...register('criteria.limit', {
                  valueAsNumber: true,
                  min: { value: 1, message: 'Must be at least 1' },
                })}
                placeholder="No limit"
              />
            </div>

            <div className="flex items-center justify-between space-x-2">
              <Label htmlFor="shuffle" className="flex flex-col space-y-1">
                <span>Shuffle Results</span>
                <span className="font-normal text-xs text-muted-foreground">
                  Randomize item order after filtering
                </span>
              </Label>
              <Switch
                id="shuffle"
                checked={criteria?.shuffle || false}
                onCheckedChange={(checked: boolean) => setValue('criteria.shuffle', checked)}
              />
            </div>
          </div>

          {/* Auto Update Section */}
          <div className="space-y-3 border-t pt-4">
            <div className="flex items-center justify-between space-x-2">
              <Label htmlFor="auto_update" className="flex flex-col space-y-1">
                <span>Auto Update</span>
                <span className="font-normal text-xs text-muted-foreground">
                  Automatically regenerate playlist periodically
                </span>
              </Label>
              <Switch
                id="auto_update"
                checked={autoUpdate || false}
                onCheckedChange={(checked: boolean) => setValue('auto_update', checked)}
              />
            </div>

            {autoUpdate && (
              <div className="space-y-2">
                <Label htmlFor="auto_update_interval">Update Interval (hours)</Label>
                <Input
                  id="auto_update_interval"
                  type="number"
                  min="1"
                  {...register('auto_update_interval', {
                    valueAsNumber: true,
                    required: autoUpdate ? 'Update interval is required' : false,
                    min: { value: 1, message: 'Must be at least 1 hour' },
                  })}
                  placeholder="24"
                />
                {errors.auto_update_interval && (
                  <span className="text-sm text-red-500">{errors.auto_update_interval.message}</span>
                )}
              </div>
            )}
          </div>

          {/* Public Toggle */}
          <div className="flex items-center justify-between space-x-2 border-t pt-4">
            <Label htmlFor="is_public" className="flex flex-col space-y-1">
              <span>Public Smart Playlist</span>
              <span className="font-normal text-xs text-muted-foreground">
                Anyone with the link can view this smart playlist.
              </span>
            </Label>
            <Switch
              id="is_public"
              checked={watch('is_public')}
              onCheckedChange={(checked: boolean) => setValue('is_public', checked)}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {smartPlaylist ? 'Save Changes' : 'Create Smart Playlist'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
