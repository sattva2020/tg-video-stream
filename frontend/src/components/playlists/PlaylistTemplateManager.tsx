import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  playlistsApi,
  PlaylistTemplate,
  PlaylistTemplateCreate,
  PlaylistTemplateUpdate,
  PlaylistEntry,
} from '../../api/playlists';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';
import { Skeleton } from '../ui/Skeleton';
import { Plus, Edit, Trash2, Copy, Play, FolderOpen } from 'lucide-react';
import { useToast } from '../ui/use-toast';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/Dialog';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { Textarea } from '../ui/Textarea';
import { Switch } from '../ui/Switch';
import { useForm } from 'react-hook-form';
import { Badge } from '../ui/Badge';

interface TemplateFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  template?: PlaylistTemplate;
  onSubmit: (data: PlaylistTemplateCreate | PlaylistTemplateUpdate) => Promise<void>;
}

const TemplateForm: React.FC<TemplateFormProps> = ({
  open,
  onOpenChange,
  template,
  onSubmit,
}) => {
  const { register, handleSubmit, reset, setValue, watch, formState: { errors, isSubmitting } } = useForm<PlaylistTemplateCreate>({
    defaultValues: {
      name: '',
      description: '',
      is_public: false,
      items: [],
    },
  });

  useEffect(() => {
    if (open) {
      if (template) {
        setValue('name', template.name);
        setValue('description', template.description || '');
        setValue('is_public', template.is_public);
      } else {
        reset({
          name: '',
          description: '',
          is_public: false,
          items: [],
        });
      }
    }
  }, [open, template, setValue, reset]);

  const isPublic = watch('is_public');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{template ? 'Edit Template' : 'Create Template'}</DialogTitle>
          <DialogDescription>
            {template
              ? 'Update template details. Changes will not affect existing playlists created from this template.'
              : 'Create a new playlist template for quick reuse.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            <Input
              id="name"
              {...register('name', { required: 'Name is required' })}
              placeholder="My Awesome Template"
            />
            {errors.name && <span className="text-sm text-destructive">{errors.name.message}</span>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="What's this template for?"
            />
          </div>

          <div className="flex items-center justify-between space-x-2">
            <Label htmlFor="is_public" className="flex flex-col space-y-1">
              <span>Public Template</span>
              <span className="font-normal text-xs text-muted-foreground">
                Anyone can see and use this template.
              </span>
            </Label>
            <Switch
              id="is_public"
              checked={isPublic}
              onCheckedChange={(checked: boolean) => setValue('is_public', checked)}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {template ? 'Save Changes' : 'Create Template'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export const PlaylistTemplateManager: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [templates, setTemplates] = useState<PlaylistTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<PlaylistTemplate | undefined>();
  const [applyDialogOpen, setApplyDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<PlaylistTemplate | undefined>();
  const [newPlaylistName, setNewPlaylistName] = useState('');

  const loadTemplates = useCallback(async () => {
    try {
      setLoading(true);
      const data = await playlistsApi.getMyTemplates();
      setTemplates(data);
    } catch (error) {
      console.error('Failed to load templates', error);
      toast({
        title: 'Error',
        description: 'Failed to load playlist templates',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const handleCreateTemplate = async (data: PlaylistTemplateCreate) => {
    try {
      await playlistsApi.createTemplate(data);
      toast({
        title: 'Success',
        description: 'Template created successfully',
      });
      setFormOpen(false);
      loadTemplates();
    } catch (error) {
      console.error('Failed to create template', error);
      toast({
        title: 'Error',
        description: 'Failed to create template',
        variant: 'destructive',
      });
    }
  };

  const handleUpdateTemplate = async (data: PlaylistTemplateUpdate) => {
    if (!editingTemplate) return;
    try {
      await playlistsApi.updateTemplate(editingTemplate.id, data);
      toast({
        title: 'Success',
        description: 'Template updated successfully',
      });
      setFormOpen(false);
      setEditingTemplate(undefined);
      loadTemplates();
    } catch (error) {
      console.error('Failed to update template', error);
      toast({
        title: 'Error',
        description: 'Failed to update template',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      await playlistsApi.deleteTemplate(templateId);
      toast({
        title: 'Success',
        description: 'Template deleted successfully',
      });
      loadTemplates();
    } catch (error) {
      console.error('Failed to delete template', error);
      toast({
        title: 'Error',
        description: 'Failed to delete template',
        variant: 'destructive',
      });
    }
  };

  const handleCloneTemplate = async (templateId: string) => {
    try {
      await playlistsApi.cloneTemplate(templateId);
      toast({
        title: 'Success',
        description: 'Template cloned successfully',
      });
      loadTemplates();
    } catch (error) {
      console.error('Failed to clone template', error);
      toast({
        title: 'Error',
        description: 'Failed to clone template',
        variant: 'destructive',
      });
    }
  };

  const openCreateForm = () => {
    setEditingTemplate(undefined);
    setFormOpen(true);
  };

  const openEditForm = (template: PlaylistTemplate) => {
    setEditingTemplate(template);
    setFormOpen(true);
  };

  const openApplyDialog = (template: PlaylistTemplate) => {
    setSelectedTemplate(template);
    setNewPlaylistName(`${template.name} (from template)`);
    setApplyDialogOpen(true);
  };

  const handleApplyTemplate = async () => {
    if (!selectedTemplate) return;

    try {
      const newPlaylist = await playlistsApi.applyTemplate(selectedTemplate.id, newPlaylistName);
      toast({
        title: 'Success',
        description: 'Playlist created from template',
      });
      setApplyDialogOpen(false);
      setSelectedTemplate(undefined);
      navigate(`/user-playlists/edit/${newPlaylist.id}`);
    } catch (error) {
      console.error('Failed to apply template', error);
      toast({
        title: 'Error',
        description: 'Failed to create playlist from template',
        variant: 'destructive',
      });
    }
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  if (loading) {
    return (
      <div className="space-y-4 p-8">
        <Skeleton className="h-12 w-1/3" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Playlist Templates</h1>
          <p className="text-muted-foreground">
            Save and reuse playlist configurations for quick setup
          </p>
        </div>
        <Button onClick={openCreateForm}>
          <Plus className="mr-2 h-4 w-4" /> Create Template
        </Button>
      </div>

      {templates.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No templates yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create templates from your playlists to quickly set up new ones
            </p>
            <Button onClick={openCreateForm}>
              <Plus className="mr-2 h-4 w-4" /> Create Your First Template
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <Card key={template.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2">
                      {template.name}
                      {template.is_public && <Badge variant="secondary">Public</Badge>}
                    </CardTitle>
                    {template.description && (
                      <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                        {template.description}
                      </p>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Tracks</span>
                    <span className="font-medium">{template.items_count}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Duration</span>
                    <span className="font-medium">{formatDuration(template.total_duration)}</span>
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => openApplyDialog(template)}
                    >
                      <Play className="mr-1 h-3 w-3" /> Apply
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEditForm(template)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleCloneTemplate(template.id)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive"
                      onClick={() => handleDeleteTemplate(template.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <TemplateForm
        open={formOpen}
        onOpenChange={setFormOpen}
        template={editingTemplate}
        onSubmit={editingTemplate ? handleUpdateTemplate : handleCreateTemplate}
      />

      <Dialog open={applyDialogOpen} onOpenChange={setApplyDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Apply Template</DialogTitle>
            <DialogDescription>
              Create a new playlist from &quot;{selectedTemplate?.name}&quot;
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="playlist-name">Playlist Name</Label>
              <Input
                id="playlist-name"
                value={newPlaylistName}
                onChange={(e) => setNewPlaylistName(e.target.value)}
                placeholder="Enter playlist name"
              />
            </div>
            {selectedTemplate && (
              <div className="text-sm text-muted-foreground">
                This will create a new playlist with {selectedTemplate.items_count} tracks
                ({formatDuration(selectedTemplate.total_duration)}).
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setApplyDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleApplyTemplate} disabled={!newPlaylistName.trim()}>
              Create Playlist
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
