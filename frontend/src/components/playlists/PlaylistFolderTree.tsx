import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Folder,
  FolderOpen,
  ChevronRight,
  ChevronDown,
  Plus,
  MoreVertical,
  Edit,
  Trash2,
  GripVertical,
} from 'lucide-react';
import { PlaylistGroup } from '../../api/playlists';
import { Button } from '../ui/Button';
import { Skeleton } from '../ui/Skeleton';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/DropdownMenu';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  useDroppable,
} from '@dnd-kit/core';

interface PlaylistFolderTreeProps {
  groups: PlaylistGroup[];
  isLoading?: boolean;
  onCreateGroup?: (parentId?: string) => void;
  onEditGroup?: (group: PlaylistGroup) => void;
  onDeleteGroup?: (group: PlaylistGroup) => void;
  onMoveGroup?: (groupId: string, newParentId: string | null, position?: number) => void;
  onToggleExpand?: (groupId: string) => void;
}

interface TreeNode {
  group: PlaylistGroup;
  children: TreeNode[];
  level: number;
}

// Build tree structure from flat list
const buildTree = (groups: PlaylistGroup[]): TreeNode[] => {
  const groupMap = new Map<string, TreeNode>();
  const rootNodes: TreeNode[] = [];

  // Create tree nodes
  groups.forEach((group) => {
    groupMap.set(group.id, { group, children: [], level: 0 });
  });

  // Build hierarchy
  groups.forEach((group) => {
    const node = groupMap.get(group.id)!;
    if (group.parent_id && groupMap.has(group.parent_id)) {
      groupMap.get(group.parent_id)!.children.push(node);
    } else {
      rootNodes.push(node);
    }
  });

  // Calculate levels
  const calculateLevel = (node: TreeNode, level: number = 0) => {
    node.level = level;
    node.children.forEach((child) => calculateLevel(child, level + 1));
  };

  rootNodes.forEach((node) => calculateLevel(node));

  return rootNodes;
};

// Sort tree nodes by position
const sortTreeNodes = (nodes: TreeNode[]): TreeNode[] => {
  return nodes
    .sort((a, b) => a.group.position - b.group.position)
    .map((node) => ({
      ...node,
      children: sortTreeNodes(node.children),
    }));
};

// Draggable Folder Node
interface DraggableFolderNodeProps {
  node: TreeNode;
  isExpanded: boolean;
  onToggle: (groupId: string) => void;
  onEdit: (group: PlaylistGroup) => void;
  onDelete: (group: PlaylistGroup) => void;
}

const DraggableFolderNode: React.FC<DraggableFolderNodeProps> = ({
  node,
  isExpanded,
  onToggle,
  onEdit,
  onDelete,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    isDragging,
  } = useDraggable({
    id: node.group.id,
    data: {
      type: 'group',
      group: node.group,
    },
  });

  const { setNodeRef: setDroppableRef, isOver } = useDroppable({
    id: `drop-${node.group.id}`,
    data: {
      type: 'group',
      group: node.group,
    },
  });

  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        opacity: isDragging ? 0.5 : 1,
      }
    : undefined;

  const setRefs = (element: HTMLDivElement | null) => {
    setNodeRef(element);
    setDroppableRef(element);
  };

  const paddingLeft = `${node.level * 16 + 12}px`;

  return (
    <div ref={setRefs} style={style} className="relative">
      <div
        className={`
          flex items-center gap-2 py-2 pr-2 rounded-lg transition-colors
          ${isOver ? 'bg-accent/50' : 'hover:bg-accent/30'}
          ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}
        `}
        style={{ paddingLeft }}
      >
        {/* Drag handle */}
        <div
          {...attributes}
          {...listeners}
          className="p-1 -ml-1 text-muted-foreground hover:text-foreground"
        >
          <GripVertical className="w-4 h-4" />
        </div>

        {/* Expand/Collapse button */}
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => onToggle(node.group.id)}
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </Button>

        {/* Folder icon */}
        {isExpanded ? (
          <FolderOpen className="w-5 h-5 text-primary" />
        ) : (
          <Folder className="w-5 h-5 text-primary" />
        )}

        {/* Group name */}
        <span className="flex-1 text-sm font-medium truncate">{node.group.name}</span>

        {/* Playlist count badge */}
        <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
          {node.group.playlists_count}
        </span>

        {/* Actions menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-6 w-6">
              <MoreVertical className="w-4 h-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(node.group)}>
              <Edit className="mr-2 h-4 w-4" /> Edit
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onDelete(node.group)} className="text-red-600">
              <Trash2 className="mr-2 h-4 w-4" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Children */}
      <AnimatePresence>
        {isExpanded && node.children.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            {node.children.map((child) => (
              <DraggableFolderNode
                key={child.group.id}
                node={child}
                isExpanded={false}
                onToggle={onToggle}
                onEdit={onEdit}
                onDelete={onDelete}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

// Droppable Root Zone
interface DroppableRootZoneProps {
  children: React.ReactNode;
}

const DroppableRootZone: React.FC<DroppableRootZoneProps> = ({ children }) => {
  const { setNodeRef, isOver } = useDroppable({
    id: 'root',
    data: {
      type: 'root',
    },
  });

  return (
    <div
      ref={setNodeRef}
      className={`
        min-h-[100px] rounded-lg border-2 border-dashed transition-colors p-4
        ${isOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
      `}
    >
      {children}
    </div>
  );
};

// Main Component
export const PlaylistFolderTree: React.FC<PlaylistFolderTreeProps> = ({
  groups,
  isLoading = false,
  onCreateGroup,
  onEditGroup,
  onDeleteGroup,
  onMoveGroup,
  onToggleExpand,
}) => {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [activeGroup, setActiveGroup] = useState<PlaylistGroup | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const treeNodes = useMemo(() => {
    return sortTreeNodes(buildTree(groups));
  }, [groups]);

  const handleToggle = (groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      onToggleExpand?.(groupId);
      return next;
    });
  };

  const handleDragStart = (event: DragStartEvent) => {
    const { active } = event;
    const group = groups.find((g) => g.id === active.id);
    setActiveGroup(group || null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveGroup(null);

    if (!over) return;

    const activeId = active.id as string;
    const overId = over.id as string;

    // Don't drop on self
    if (activeId === overId || overId === `drop-${activeId}`) return;

    // If dropped on root, move to root level
    if (overId === 'root') {
      onMoveGroup?.(activeId, null, 0);
      return;
    }

    // If dropped on another group
    if (overId.toString().startsWith('drop-')) {
      const targetGroupId = overId.toString().replace('drop-', '');
      const targetGroup = groups.find((g) => g.id === targetGroupId);

      if (targetGroup) {
        // Check if dropping into own descendant
        const isDescendant = (groupId: string, parentId: string): boolean => {
          const parentChildren = groups.filter((g) => g.parent_id === parentId);
          return parentChildren.some((child) => {
            if (child.id === groupId) return true;
            return isDescendant(groupId, child.id);
          });
        };

        if (!isDescendant(activeId, targetGroupId)) {
          onMoveGroup?.(activeId, targetGroupId, 0);
        }
      }
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-2 p-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-2">
            <Skeleton className="h-8 w-8 rounded" />
            <Skeleton className="h-8 flex-1 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (treeNodes.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Folder className="w-12 h-12 mx-auto mb-4 opacity-50" />
        <p className="text-sm">No playlist groups yet.</p>
        <p className="text-xs mt-1">Create a group to organize your playlists.</p>
        {onCreateGroup && (
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => onCreateGroup()}
          >
            <Plus className="mr-2 h-4 w-4" /> Create First Group
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="h-full">
      <div className="flex items-center justify-between mb-4 px-2">
        <h3 className="text-sm font-semibold">Playlist Groups</h3>
        {onCreateGroup && (
          <Button variant="ghost" size="sm" onClick={() => onCreateGroup()}>
            <Plus className="mr-2 h-4 w-4" /> New Group
          </Button>
        )}
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <DroppableRootZone>
          <div className="space-y-1">
            {treeNodes.map((node) => (
              <DraggableFolderNode
                key={node.group.id}
                node={node}
                isExpanded={expandedGroups.has(node.group.id)}
                onToggle={handleToggle}
                onEdit={(group) => onEditGroup?.(group)}
                onDelete={(group) => onDeleteGroup?.(group)}
              />
            ))}
          </div>
        </DroppableRootZone>

        <DragOverlay>
          {activeGroup ? (
            <div className="flex items-center gap-2 py-2 px-3 bg-card border rounded-lg shadow-lg opacity-80 rotate-2">
              <Folder className="w-5 h-5 text-primary" />
              <span className="text-sm font-medium">{activeGroup.name}</span>
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
};
