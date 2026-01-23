from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from src.models.schedule import SmartPlaylist, Playlist
from datetime import datetime, timezone
import uuid
import random
from typing import List, Dict, Any


class SmartPlaylistService:
    @staticmethod
    def get_user_smart_playlists(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
        """Get all smart playlists for a specific user."""
        return db.query(SmartPlaylist).filter(SmartPlaylist.user_id == user_id)\
            .order_by(desc(SmartPlaylist.updated_at))\
            .offset(skip).limit(limit).all()

    @staticmethod
    def get_public_smart_playlists(db: Session, skip: int = 0, limit: int = 100):
        """Get all public smart playlists."""
        return db.query(SmartPlaylist).filter(SmartPlaylist.is_public == True)\
            .order_by(desc(SmartPlaylist.updated_at))\
            .offset(skip).limit(limit).all()

    @staticmethod
    def get_smart_playlist(db: Session, smart_playlist_id: uuid.UUID):
        """Get a single smart playlist by ID."""
        return db.query(SmartPlaylist).filter(SmartPlaylist.id == smart_playlist_id).first()

    @staticmethod
    def create_smart_playlist(db: Session, name: str, user_id: uuid.UUID, criteria: dict,
                             description: str = None, is_public: bool = False,
                             channel_id: uuid.UUID = None, group_id: uuid.UUID = None,
                             auto_update: bool = False, auto_update_interval: int = 24):
        """
        Create a new smart playlist.

        Args:
            db: Database session
            name: Smart playlist name
            user_id: Owner user ID
            criteria: Criteria dict with filters, order_by, limit, shuffle
            description: Optional description
            is_public: Whether smart playlist is public
            channel_id: Optional channel ID
            group_id: Optional group ID
            auto_update: Whether to auto-update the playlist
            auto_update_interval: Update interval in hours

        Returns:
            Created SmartPlaylist instance
        """
        db_smart_playlist = SmartPlaylist(
            user_id=user_id,
            name=name,
            description=description,
            criteria=criteria,
            is_public=is_public,
            channel_id=channel_id,
            group_id=group_id,
            auto_update=auto_update,
            auto_update_interval=auto_update_interval,
            items_count=0,
            total_duration=0
        )

        db.add(db_smart_playlist)
        db.commit()
        db.refresh(db_smart_playlist)

        # Generate initial playlist
        SmartPlaylistService.refresh_smart_playlist(db, db_smart_playlist)

        return db_smart_playlist

    @staticmethod
    def update_smart_playlist(db: Session, db_smart_playlist: SmartPlaylist, name: str = None,
                             description: str = None, is_public: bool = None,
                             criteria: dict = None, auto_update: bool = None,
                             auto_update_interval: int = None, group_id: uuid.UUID = None):
        """
        Update an existing smart playlist.

        Args:
            db: Database session
            db_smart_playlist: Existing SmartPlaylist instance
            name: New name (optional)
            description: New description (optional)
            is_public: New public flag (optional)
            criteria: New criteria (optional)
            auto_update: New auto-update flag (optional)
            auto_update_interval: New update interval (optional)
            group_id: New group ID (optional)

        Returns:
            Updated SmartPlaylist instance
        """
        if name is not None:
            db_smart_playlist.name = name
        if description is not None:
            db_smart_playlist.description = description
        if is_public is not None:
            db_smart_playlist.is_public = is_public
        if criteria is not None:
            db_smart_playlist.criteria = criteria
        if auto_update is not None:
            db_smart_playlist.auto_update = auto_update
        if auto_update_interval is not None:
            db_smart_playlist.auto_update_interval = auto_update_interval
        if group_id is not None:
            db_smart_playlist.group_id = group_id

        db.commit()
        db.refresh(db_smart_playlist)
        return db_smart_playlist

    @staticmethod
    def delete_smart_playlist(db: Session, db_smart_playlist: SmartPlaylist):
        """
        Delete a smart playlist.

        Args:
            db: Database session
            db_smart_playlist: SmartPlaylist instance to delete
        """
        # If there's a linked playlist, delete it too
        if db_smart_playlist.playlist_id:
            linked_playlist = db.query(Playlist).filter(Playlist.id == db_smart_playlist.playlist_id).first()
            if linked_playlist:
                db.delete(linked_playlist)

        db.delete(db_smart_playlist)
        db.commit()

    @staticmethod
    def _filter_playlist_items(items: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Filter playlist items based on criteria.

        Args:
            items: List of playlist items (dicts)
            criteria: Criteria dict with filters

        Returns:
            Filtered list of items
        """
        filters = criteria.get('filters', {})
        filtered_items = items

        # Filter by duration
        duration_min = filters.get('duration_min')
        if duration_min is not None:
            filtered_items = [item for item in filtered_items if item.get('duration', 0) >= duration_min]

        duration_max = filters.get('duration_max')
        if duration_max is not None:
            filtered_items = [item for item in filtered_items if item.get('duration', 0) <= duration_max]

        # Filter by type
        type_filter = filters.get('type')
        if type_filter is not None:
            if isinstance(type_filter, list):
                filtered_items = [item for item in filtered_items if item.get('type') in type_filter]
            else:
                filtered_items = [item for item in filtered_items if item.get('type') == type_filter]

        # Filter by title (case-insensitive substring match)
        title_contains = filters.get('title_contains')
        if title_contains:
            filtered_items = [
                item for item in filtered_items
                if title_contains.lower() in (item.get('title') or '').lower()
            ]

        return filtered_items

    @staticmethod
    def _sort_playlist_items(items: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Sort playlist items based on criteria.

        Args:
            items: List of playlist items (dicts)
            criteria: Criteria dict with order_by and order_direction

        Returns:
            Sorted list of items
        """
        order_by = criteria.get('order_by', 'date_added')
        order_direction = criteria.get('order_direction', 'desc')

        reverse = (order_direction == 'desc')

        if order_by == 'duration':
            return sorted(items, key=lambda x: x.get('duration', 0), reverse=reverse)
        elif order_by == 'name':
            return sorted(items, key=lambda x: (x.get('title') or '').lower(), reverse=reverse)
        elif order_by == 'date_added':
            # For now, keep original order (date_added not tracked at item level)
            return items[::-1] if reverse else items
        else:
            return items

    @staticmethod
    def _limit_playlist_items(items: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Limit playlist items based on criteria.

        Args:
            items: List of playlist items (dicts)
            criteria: Criteria dict with limit

        Returns:
            Limited list of items
        """
        limit = criteria.get('limit')
        if limit is not None and limit > 0:
            return items[:limit]
        return items

    @staticmethod
    def _shuffle_playlist_items(items: List[Dict[str, Any]], criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Shuffle playlist items if criteria specifies.

        Args:
            items: List of playlist items (dicts)
            criteria: Criteria dict with shuffle flag

        Returns:
            Shuffled or original list of items
        """
        shuffle = criteria.get('shuffle', False)
        if shuffle:
            shuffled = items.copy()
            random.shuffle(shuffled)
            return shuffled
        return items

    @staticmethod
    def refresh_smart_playlist(db: Session, db_smart_playlist: SmartPlaylist):
        """
        Refresh a smart playlist by regenerating its content based on criteria.

        Args:
            db: Database session
            db_smart_playlist: SmartPlaylist instance to refresh

        Returns:
            Updated Playlist instance with generated content
        """
        criteria = db_smart_playlist.criteria

        # Get all user's playlists to extract items from
        user_playlists = db.query(Playlist).filter(Playlist.user_id == db_smart_playlist.user_id).all()

        # Collect all items from all playlists
        all_items = []
        for playlist in user_playlists:
            all_items.extend(playlist.items or [])

        # Apply filters
        filtered_items = SmartPlaylistService._filter_playlist_items(all_items, criteria)

        # Sort items
        sorted_items = SmartPlaylistService._sort_playlist_items(filtered_items, criteria)

        # Limit items
        limited_items = SmartPlaylistService._limit_playlist_items(sorted_items, criteria)

        # Shuffle if needed
        final_items = SmartPlaylistService._shuffle_playlist_items(limited_items, criteria)

        # Calculate stats
        total_duration = sum(item.get('duration', 0) for item in final_items)

        # Create or update the linked playlist
        if db_smart_playlist.playlist_id:
            # Update existing playlist
            linked_playlist = db.query(Playlist).filter(Playlist.id == db_smart_playlist.playlist_id).first()
            if linked_playlist:
                linked_playlist.items = final_items
                linked_playlist.items_count = len(final_items)
                linked_playlist.total_duration = total_duration
                db.commit()
                db.refresh(linked_playlist)
            else:
                # Playlist was deleted, create new one
                linked_playlist = None
        else:
            linked_playlist = None

        if not linked_playlist:
            # Create new playlist
            linked_playlist = Playlist(
                user_id=db_smart_playlist.user_id,
                name=db_smart_playlist.name,
                description=db_smart_playlist.description or f"Generated from smart playlist '{db_smart_playlist.name}'",
                is_public=db_smart_playlist.is_public,
                color=db_smart_playlist.color,
                icon="wand-magic-sparkles",  # Magic wand icon for smart playlists
                items=final_items,
                items_count=len(final_items),
                total_duration=total_duration,
                group_id=db_smart_playlist.group_id,
                channel_id=db_smart_playlist.channel_id
            )
            db.add(linked_playlist)
            db.commit()
            db.refresh(linked_playlist)

            # Link smart playlist to generated playlist
            db_smart_playlist.playlist_id = linked_playlist.id
            db.commit()

        # Update smart playlist stats
        db_smart_playlist.items_count = len(final_items)
        db_smart_playlist.total_duration = total_duration
        db_smart_playlist.last_refreshed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_smart_playlist)

        return linked_playlist

    @staticmethod
    def clone_smart_playlist(db: Session, source_smart_playlist: SmartPlaylist,
                            user_id: uuid.UUID, new_name: str = None):
        """
        Clone a smart playlist for a user.

        Args:
            db: Database session
            source_smart_playlist: SmartPlaylist to clone
            user_id: Owner user ID for the new smart playlist
            new_name: Optional new name (defaults to "Copy of {name}")

        Returns:
            Created SmartPlaylist instance
        """
        clone_name = new_name or f"Copy of {source_smart_playlist.name}"

        new_smart_playlist = SmartPlaylist(
            user_id=user_id,
            name=clone_name,
            description=source_smart_playlist.description,
            is_public=False,  # Clones are private by default
            channel_id=None,  # Clones are not tied to a specific channel
            group_id=None,    # Clones are not tied to a specific group
            criteria=source_smart_playlist.criteria,  # Copy criteria
            auto_update=source_smart_playlist.auto_update,
            auto_update_interval=source_smart_playlist.auto_update_interval,
            items_count=0,
            total_duration=0
        )

        db.add(new_smart_playlist)
        db.commit()
        db.refresh(new_smart_playlist)

        # Generate initial playlist
        SmartPlaylistService.refresh_smart_playlist(db, new_smart_playlist)

        return new_smart_playlist
