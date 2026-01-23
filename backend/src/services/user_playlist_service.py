from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.models.schedule import Playlist, ScheduleSlot
from src.models.telegram import Channel, TelegramAccount
from src.schemas.playlist import PlaylistCreate, PlaylistUpdate
from src.services.redis_stream_controller import RedisStreamController
from src.services.encryption import EncryptionService
from datetime import datetime, timezone
import uuid
import secrets

class UserPlaylistService:
    @staticmethod
    def get_user_playlists(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
        return db.query(Playlist).filter(Playlist.user_id == user_id)\
            .order_by(desc(Playlist.updated_at))\
            .offset(skip).limit(limit).all()

    @staticmethod
    def get_public_playlists(db: Session, skip: int = 0, limit: int = 100):
        return db.query(Playlist).filter(Playlist.is_public == True)\
            .order_by(desc(Playlist.updated_at))\
            .offset(skip).limit(limit).all()

    @staticmethod
    def get_playlist(db: Session, playlist_id: uuid.UUID):
        return db.query(Playlist).filter(Playlist.id == playlist_id).first()

    @staticmethod
    def create_playlist(db: Session, playlist: PlaylistCreate, user_id: uuid.UUID):
        # Calculate stats
        items_data = [item.model_dump() for item in playlist.items]
        total_duration = sum(item.get('duration', 0) for item in items_data)
        
        db_playlist = Playlist(
            user_id=user_id,
            name=playlist.name,
            description=playlist.description,
            is_public=playlist.is_public,
            color=playlist.color,
            icon=playlist.icon,
            items=items_data,
            items_count=len(items_data),
            total_duration=total_duration
        )
        
        if playlist.is_public:
            db_playlist.share_code = secrets.token_urlsafe(8)
            
        db.add(db_playlist)
        db.commit()
        db.refresh(db_playlist)
        return db_playlist

    @staticmethod
    def update_playlist(db: Session, db_playlist: Playlist, update_data: PlaylistUpdate):
        if update_data.name is not None:
            db_playlist.name = update_data.name
        if update_data.description is not None:
            db_playlist.description = update_data.description
        if update_data.color is not None:
            db_playlist.color = update_data.color
        if update_data.icon is not None:
            db_playlist.icon = update_data.icon
            
        if update_data.is_public is not None:
            db_playlist.is_public = update_data.is_public
            if db_playlist.is_public and not db_playlist.share_code:
                db_playlist.share_code = secrets.token_urlsafe(8)
        
        if update_data.items is not None:
            items_data = [item.model_dump() for item in update_data.items]
            db_playlist.items = items_data
            db_playlist.items_count = len(items_data)
            db_playlist.total_duration = sum(item.get('duration', 0) for item in items_data)
            
        db.commit()
        db.refresh(db_playlist)
        return db_playlist

    @staticmethod
    def delete_playlist(db: Session, db_playlist: Playlist):
        db.delete(db_playlist)
        db.commit()

    @staticmethod
    def clone_playlist(db: Session, source_playlist: Playlist, user_id: uuid.UUID):
        new_playlist = Playlist(
            user_id=user_id,
            name=f"Copy of {source_playlist.name}",
            description=source_playlist.description,
            is_public=False, # Clones are private by default
            color=source_playlist.color,
            icon=source_playlist.icon,
            items=source_playlist.items, # Copy JSON
            items_count=source_playlist.items_count,
            total_duration=source_playlist.total_duration
        )
        db.add(new_playlist)
        db.commit()
        db.refresh(new_playlist)
        return new_playlist

    @staticmethod
    def generate_m3u(db_playlist: Playlist) -> str:
        """Generate M3U content from playlist items."""
        lines = ["#EXTM3U"]
        
        for item in db_playlist.items:
            # item is a dict from JSON
            title = item.get('title', 'Unknown Title')
            duration = item.get('duration', -1)
            url = item.get('url', '')
            
            lines.append(f"#EXTINF:{duration},{title}")
            lines.append(url)
            
        return "\n".join(lines)

    @staticmethod
    def import_m3u_playlist(db: Session, content: str, filename: str, user_id: uuid.UUID):
        items = []
        lines = content.splitlines()
        current_title = None
        current_duration = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("#EXTINF:"):
                # Parse #EXTINF:duration,title
                try:
                    info = line[8:]
                    parts = info.split(',', 1)
                    if len(parts) == 2:
                        current_duration = int(parts[0])
                        current_title = parts[1].strip()
                    else:
                        current_duration = 0
                        current_title = info.strip()
                except:
                    current_duration = 0
                    current_title = None
            elif line.startswith("#"):
                continue
            else:
                # It's a URL or path
                url = line
                title = current_title or os.path.basename(url)
                
                items.append({
                    "url": url,
                    "title": title,
                    "duration": max(0, current_duration),
                    "type": "local" if not url.startswith(('http://', 'https://')) else "stream"
                })
                
                # Reset for next item
                current_title = None
                current_duration = 0
        
        # Create playlist
        new_playlist = Playlist(
            user_id=user_id,
            name=filename.replace('.m3u', '').replace('.m3u8', '') or "Imported Playlist",
            description="Imported from M3U file",
            is_public=False,
            color="#10B981", # Green for import
            icon="file-audio",
            items=items,
            items_count=len(items),
            total_duration=sum(item['duration'] for item in items)
        )
        
        db.add(new_playlist)
        db.commit()
        db.refresh(new_playlist)
        return new_playlist

    @staticmethod
    def play_playlist(db: Session, playlist_id: uuid.UUID, user_id: uuid.UUID, channel_id: uuid.UUID = None):
        """
        Immediately play a playlist on a channel.
        Creates a schedule slot starting now and triggers the streamer.
        """
        # 1. Find channel
        if channel_id:
            channel = db.query(Channel).filter(Channel.id == channel_id).first()
            if not channel:
                raise ValueError("Channel not found")
            # Verify ownership
            if channel.account.user_id != user_id:
                raise ValueError("Not authorized for this channel")
        else:
            # Find first available channel for user
            channel = db.query(Channel).join(TelegramAccount).filter(TelegramAccount.user_id == user_id).first()
            if not channel:
                raise ValueError("No channels found for user. Please connect a Telegram account and create a channel first.")
        
        # 2. Create ScheduleSlot for NOW
        now = datetime.now(timezone.utc)
        
        slot = ScheduleSlot(
            channel_id=channel.id,
            playlist_id=playlist_id,
            start_date=now.date(),
            start_time=now.time()
        )
        db.add(slot)
        db.commit()
        
        # 3. Trigger Streamer
        try:
            encryption_service = EncryptionService()
            controller = RedisStreamController(db, encryption_service)
            # We use restart_channel to force reload configuration and schedule
            controller.restart_channel(channel.id)
        except Exception as e:
            # Log error but don't fail the request if possible, or raise?
            # If streamer is not running, this might fail.
            # But we successfully scheduled it.
            print(f"Failed to trigger streamer: {e}")
            # We might want to return a warning
            
        return {"status": "playing", "channel_id": channel.id, "slot_id": slot.id}

    @staticmethod
    def bulk_delete_playlists(db: Session, playlist_ids: list[uuid.UUID], user_id: uuid.UUID):
        """
        Bulk delete multiple playlists. Only playlists owned by the user will be deleted.
        Returns a dict with success_count, failed_count, and errors.
        """
        success_count = 0
        failed_count = 0
        errors = []

        for playlist_id in playlist_ids:
            playlist = UserPlaylistService.get_playlist(db, playlist_id)
            if not playlist:
                failed_count += 1
                errors.append(f"Playlist {playlist_id} not found")
                continue

            if playlist.user_id != user_id:
                failed_count += 1
                errors.append(f"Not authorized to delete playlist {playlist_id}")
                continue

            try:
                UserPlaylistService.delete_playlist(db, playlist)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"Failed to delete playlist {playlist_id}: {str(e)}")

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }

    @staticmethod
    def bulk_move_playlists(db: Session, playlist_ids: list[uuid.UUID], group_id: uuid.UUID, user_id: uuid.UUID):
        """
        Bulk move multiple playlists to a group. Only playlists owned by the user will be moved.
        Returns a dict with success_count, failed_count, and errors.
        """
        success_count = 0
        failed_count = 0
        errors = []

        for playlist_id in playlist_ids:
            playlist = UserPlaylistService.get_playlist(db, playlist_id)
            if not playlist:
                failed_count += 1
                errors.append(f"Playlist {playlist_id} not found")
                continue

            if playlist.user_id != user_id:
                failed_count += 1
                errors.append(f"Not authorized to move playlist {playlist_id}")
                continue

            try:
                playlist.group_id = group_id
                db.commit()
                db.refresh(playlist)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"Failed to move playlist {playlist_id}: {str(e)}")

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }

    @staticmethod
    def bulk_copy_playlists(db: Session, playlist_ids: list[uuid.UUID], user_id: uuid.UUID):
        """
        Bulk copy multiple playlists. Only playlists owned by or public to the user will be copied.
        Returns a dict with success_count, failed_count, errors, and copied_playlists.
        """
        success_count = 0
        failed_count = 0
        errors = []
        copied_playlists = []

        for playlist_id in playlist_ids:
            playlist = UserPlaylistService.get_playlist(db, playlist_id)
            if not playlist:
                failed_count += 1
                errors.append(f"Playlist {playlist_id} not found")
                continue

            # Check access rights (owner or public)
            if playlist.user_id != user_id and not playlist.is_public:
                failed_count += 1
                errors.append(f"Not authorized to copy playlist {playlist_id}")
                continue

            try:
                new_playlist = UserPlaylistService.clone_playlist(db, playlist, user_id)
                copied_playlists.append(new_playlist)
                success_count += 1
            except Exception as e:
                failed_count += 1
                errors.append(f"Failed to copy playlist {playlist_id}: {str(e)}")

        return {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors,
            "copied_playlists": copied_playlists
        }
