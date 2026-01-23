from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.models.schedule import PlaylistGroup
import uuid


class PlaylistGroupService:
    @staticmethod
    def get_user_groups(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
        """Get all groups for a specific user, ordered by position."""
        return db.query(PlaylistGroup).filter(PlaylistGroup.user_id == user_id)\
            .order_by(PlaylistGroup.position)\
            .offset(skip).limit(limit).all()

    @staticmethod
    def get_group(db: Session, group_id: uuid.UUID):
        """Get a single group by ID."""
        return db.query(PlaylistGroup).filter(PlaylistGroup.id == group_id).first()

    @staticmethod
    def create_group(db: Session, name: str, user_id: uuid.UUID, parent_id: uuid.UUID = None,
                     description: str = None, color: str = "#6366F1", icon: str = "folder",
                     channel_id: uuid.UUID = None, position: int = 0):
        """
        Create a new playlist group.

        Args:
            db: Database session
            name: Group name
            user_id: Owner user ID
            parent_id: Optional parent group ID for nesting
            description: Optional description
            color: Hex color code
            icon: Icon name
            channel_id: Optional channel ID
            position: Sort position

        Returns:
            Created PlaylistGroup instance
        """
        db_group = PlaylistGroup(
            user_id=user_id,
            name=name,
            parent_id=parent_id,
            description=description,
            color=color,
            icon=icon,
            channel_id=channel_id,
            position=position
        )
        db.add(db_group)
        db.commit()
        db.refresh(db_group)
        return db_group

    @staticmethod
    def update_group(db: Session, db_group: PlaylistGroup, name: str = None,
                     parent_id: uuid.UUID = None, description: str = None,
                     color: str = None, icon: str = None, position: int = None):
        """
        Update a playlist group.

        Args:
            db: Database session
            db_group: PlaylistGroup instance to update
            name: New name
            parent_id: New parent group ID for moving/restructuring
            description: New description
            color: New color
            icon: New icon
            position: New position

        Returns:
            Updated PlaylistGroup instance
        """
        if name is not None:
            db_group.name = name
        if parent_id is not None:
            # Prevent setting self as parent to avoid circular reference
            if parent_id == db_group.id:
                raise ValueError("Cannot set group as its own parent")
            db_group.parent_id = parent_id
        if description is not None:
            db_group.description = description
        if color is not None:
            db_group.color = color
        if icon is not None:
            db_group.icon = icon
        if position is not None:
            db_group.position = position

        db.commit()
        db.refresh(db_group)
        return db_group

    @staticmethod
    def move_group(db: Session, group_id: uuid.UUID, new_parent_id: uuid.UUID = None,
                   new_position: int = None):
        """
        Move a group to a new parent and/or position.

        Args:
            db: Database session
            group_id: Group to move
            new_parent_id: New parent group ID (None for root level)
            new_position: New position in the parent

        Returns:
            Updated PlaylistGroup instance
        """
        db_group = PlaylistGroupService.get_group(db, group_id)
        if not db_group:
            raise ValueError("Group not found")

        # Prevent setting self as parent
        if new_parent_id == group_id:
            raise ValueError("Cannot set group as its own parent")

        if new_parent_id is not None:
            # Verify new parent exists
            new_parent = PlaylistGroupService.get_group(db, new_parent_id)
            if not new_parent:
                raise ValueError("Parent group not found")
            db_group.parent_id = new_parent_id

        if new_position is not None:
            db_group.position = new_position

        db.commit()
        db.refresh(db_group)
        return db_group

    @staticmethod
    def delete_group(db: Session, db_group: PlaylistGroup):
        """
        Delete a playlist group.
        Child groups will be moved to root level (parent_id set to NULL).
        Playlists in this group will have their group_id set to NULL.

        Args:
            db: Database session
            db_group: PlaylistGroup instance to delete
        """
        group_id = db_group.id

        # Move child groups to root level
        db.query(PlaylistGroup).filter(PlaylistGroup.parent_id == group_id)\
            .update({"parent_id": None})

        # Delete the group
        db.delete(db_group)
        db.commit()
