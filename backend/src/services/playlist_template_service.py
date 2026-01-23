from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.models.schedule import PlaylistTemplate, Playlist
import uuid


class PlaylistTemplateService:
    @staticmethod
    def get_user_templates(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
        """Get all templates for a specific user."""
        return db.query(PlaylistTemplate).filter(PlaylistTemplate.user_id == user_id)\
            .order_by(desc(PlaylistTemplate.updated_at))\
            .offset(skip).limit(limit).all()

    @staticmethod
    def get_public_templates(db: Session, skip: int = 0, limit: int = 100):
        """Get all public templates."""
        return db.query(PlaylistTemplate).filter(PlaylistTemplate.is_public == True)\
            .order_by(desc(PlaylistTemplate.updated_at))\
            .offset(skip).limit(limit).all()

    @staticmethod
    def get_template(db: Session, template_id: uuid.UUID):
        """Get a single template by ID."""
        return db.query(PlaylistTemplate).filter(PlaylistTemplate.id == template_id).first()

    @staticmethod
    def create_template(db: Session, name: str, user_id: uuid.UUID, items: list = None,
                       description: str = None, is_public: bool = False,
                       channel_id: uuid.UUID = None):
        """
        Create a new playlist template.

        Args:
            db: Database session
            name: Template name
            user_id: Owner user ID
            items: List of playlist items (dictionaries with url, title, duration, type)
            description: Optional description
            is_public: Whether template is public
            channel_id: Optional channel ID

        Returns:
            Created PlaylistTemplate instance
        """
        items_data = items or []
        total_duration = sum(item.get('duration', 0) for item in items_data)

        db_template = PlaylistTemplate(
            user_id=user_id,
            name=name,
            description=description,
            is_public=is_public,
            channel_id=channel_id,
            items=items_data,
            items_count=len(items_data),
            total_duration=total_duration
        )

        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        return db_template

    @staticmethod
    def update_template(db: Session, db_template: PlaylistTemplate, name: str = None,
                       description: str = None, is_public: bool = None,
                       items: list = None):
        """
        Update an existing playlist template.

        Args:
            db: Database session
            db_template: Existing PlaylistTemplate instance
            name: New name (optional)
            description: New description (optional)
            is_public: New public flag (optional)
            items: New items list (optional)

        Returns:
            Updated PlaylistTemplate instance
        """
        if name is not None:
            db_template.name = name
        if description is not None:
            db_template.description = description
        if is_public is not None:
            db_template.is_public = is_public
        if items is not None:
            items_data = items
            db_template.items = items_data
            db_template.items_count = len(items_data)
            db_template.total_duration = sum(item.get('duration', 0) for item in items_data)

        db.commit()
        db.refresh(db_template)
        return db_template

    @staticmethod
    def delete_template(db: Session, db_template: PlaylistTemplate):
        """Delete a playlist template."""
        db.delete(db_template)
        db.commit()

    @staticmethod
    def apply_template(db: Session, template_id: uuid.UUID, user_id: uuid.UUID,
                       playlist_name: str, playlist_description: str = None,
                       group_id: uuid.UUID = None, channel_id: uuid.UUID = None):
        """
        Apply a template to create a new playlist.

        Args:
            db: Database session
            template_id: Template ID to apply
            user_id: Owner user ID for the new playlist
            playlist_name: Name for the new playlist
            playlist_description: Optional description for the new playlist
            group_id: Optional group ID for the new playlist
            channel_id: Optional channel ID for the new playlist

        Returns:
            Created Playlist instance

        Raises:
            ValueError: If template not found
        """
        # Get template
        template = db.query(PlaylistTemplate).filter(PlaylistTemplate.id == template_id).first()
        if not template:
            raise ValueError("Template not found")

        # Create playlist from template
        new_playlist = Playlist(
            user_id=user_id,
            name=playlist_name,
            description=playlist_description or template.description,
            is_public=False,  # Playlists created from templates are private by default
            color="#8B5CF6",  # Default purple color
            icon="folder",
            items=template.items,  # Copy items from template
            items_count=template.items_count,
            total_duration=template.total_duration,
            group_id=group_id,
            channel_id=channel_id
        )

        db.add(new_playlist)
        db.commit()
        db.refresh(new_playlist)
        return new_playlist

    @staticmethod
    def clone_template(db: Session, source_template: PlaylistTemplate, user_id: uuid.UUID,
                       new_name: str = None):
        """
        Clone a template for a user.

        Args:
            db: Database session
            source_template: Template to clone
            user_id: Owner user ID for the new template
            new_name: Optional new name (defaults to "Copy of {name}")

        Returns:
            Created PlaylistTemplate instance
        """
        clone_name = new_name or f"Copy of {source_template.name}"

        new_template = PlaylistTemplate(
            user_id=user_id,
            name=clone_name,
            description=source_template.description,
            is_public=False,  # Clones are private by default
            channel_id=None,  # Clones are not tied to a specific channel
            items=source_template.items,  # Copy items
            items_count=source_template.items_count,
            total_duration=source_template.total_duration
        )

        db.add(new_template)
        db.commit()
        db.refresh(new_template)
        return new_template
