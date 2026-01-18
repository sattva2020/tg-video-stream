import React, { useState, useEffect, useCallback } from 'react';
import { FolderInfo, getFolders, scanFolder, MediaFile } from '../../api/media';
import { Button } from '../ui/Button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/Dialog';
import { ScrollArea } from '../ui/ScrollArea';
import { Folder, Music, Loader2, Check } from 'lucide-react';
import { cn } from '../../lib/utils';

interface FileBrowserProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect?: (path: string) => void;
  onFilesSelect?: (files: MediaFile[]) => void;
  currentPath?: string;
  mode?: 'folder' | 'files';
}

export const FileBrowser: React.FC<FileBrowserProps> = ({
  open,
  onOpenChange,
  onSelect,
  onFilesSelect,
  currentPath,
  mode = 'folder'
}) => {
  const [folders, setFolders] = useState<FolderInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(currentPath || null);
  const [previewFiles, setPreviewFiles] = useState<MediaFile[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<MediaFile[]>([]);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    if (open) {
      loadFolders();
      setSelectedFiles([]);
    }
  }, [open]);

  const loadPreview = useCallback(async (path: string) => {
    setScanning(true);
    try {
      const result = await scanFolder(path, false);
      if (mode === 'files') {
        setPreviewFiles(result.files);
      } else {
        setPreviewFiles(result.files.slice(0, 5)); // Show first 5 files
      }
    } catch (error) {
      console.error('Failed to scan folder:', error);
    } finally {
      setScanning(false);
    }
  }, [mode]);

  useEffect(() => {
    if (selectedFolder) {
      loadPreview(selectedFolder);
    } else {
      setPreviewFiles([]);
    }
  }, [selectedFolder, loadPreview]);

  const loadFolders = async () => {
    setLoading(true);
    try {
      const data = await getFolders();
      setFolders(data);
    } catch (error) {
      console.error('Failed to load folders:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleFileSelection = (file: MediaFile) => {
    if (mode !== 'files') return;
    
    setSelectedFiles(prev => {
      const exists = prev.find(f => f.path === file.path);
      if (exists) {
        return prev.filter(f => f.path !== file.path);
      } else {
        return [...prev, file];
      }
    });
  };

  const handleSelect = () => {
    if (mode === 'files') {
      if (onFilesSelect && selectedFiles.length > 0) {
        onFilesSelect(selectedFiles);
        onOpenChange(false);
      }
    } else {
      if (selectedFolder && onSelect) {
        onSelect(selectedFolder);
        onOpenChange(false);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Select Music Folder</DialogTitle>
        </DialogHeader>

        <div className="flex-1 min-h-0 flex gap-4">
          {/* Folder List */}
          <div className="w-1/2 border-r pr-4">
            <h3 className="font-medium mb-2 text-sm text-muted-foreground">Available Folders</h3>
            <ScrollArea className="h-[300px]">
              {loading ? (
                <div className="flex justify-center p-4">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="space-y-1">
                  {folders.map((folder) => (
                    <button
                      key={folder.path}
                      onClick={() => setSelectedFolder(folder.path)}
                      className={cn(
                        "w-full flex items-center gap-2 px-2 py-1.5 text-sm rounded-md transition-colors",
                        selectedFolder === folder.path
                          ? "bg-primary/10 text-primary"
                          : "hover:bg-muted"
                      )}
                    >
                      <Folder className="h-4 w-4" />
                      <span className="truncate">{folder.name}</span>
                      {folder.audio_count !== undefined && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          {folder.audio_count}
                        </span>
                      )}
                    </button>
                  ))}
                  {folders.length === 0 && (
                    <div className="text-sm text-muted-foreground text-center py-4">
                      No folders found in music directory
                    </div>
                  )}
                </div>
              )}
            </ScrollArea>
          </div>

          {/* Preview */}
          <div className="w-1/2 pl-4">
            <h3 className="font-medium mb-2 text-sm text-muted-foreground">
              {mode === 'files' ? 'Select Files' : 'Preview'}
            </h3>
            <ScrollArea className="h-[300px]">
              {selectedFolder ? (
                scanning ? (
                  <div className="flex justify-center p-4">
                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : (
                  <div className="space-y-2">
                    {previewFiles.map((file, i) => (
                      <div 
                        key={i} 
                        className={cn(
                          "flex items-center gap-2 text-sm p-1.5 rounded transition-colors",
                          mode === 'files' 
                            ? "cursor-pointer hover:bg-muted"
                            : "text-muted-foreground",
                          mode === 'files' && selectedFiles.find(f => f.path === file.path) && "bg-primary/10 text-primary"
                        )}
                        onClick={() => toggleFileSelection(file)}
                      >
                        {mode === 'files' ? (
                          <div className={cn(
                            "h-4 w-4 border rounded flex items-center justify-center shrink-0",
                            selectedFiles.find(f => f.path === file.path)
                              ? "bg-primary border-primary text-primary-foreground"
                              : "border-muted-foreground"
                          )}>
                            {selectedFiles.find(f => f.path === file.path) && <Check className="h-3 w-3" />}
                          </div>
                        ) : (
                          <Music className="h-3 w-3 shrink-0" />
                        )}
                        <span className="truncate">{file.title || file.filename}</span>
                      </div>
                    ))}
                    {previewFiles.length === 0 && (
                      <div className="text-sm text-muted-foreground italic">
                        No audio files found
                      </div>
                    )}
                    {mode === 'folder' && previewFiles.length >= 5 && (
                      <div className="text-xs text-muted-foreground pt-2">
                        ...and more
                      </div>
                    )}
                  </div>
                )
              ) : (
                <div className="text-sm text-muted-foreground italic">
                  Select a folder to preview contents
                </div>
              )}
            </ScrollArea>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleSelect} 
            disabled={mode === 'files' ? selectedFiles.length === 0 : !selectedFolder}
          >
            {mode === 'files' 
              ? `Add ${selectedFiles.length} Tracks` 
              : 'Select Folder'
            }
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
