"""
ChannelService for multi-channel management.

Manages:
- Multiple Telegram channels/groups
- Channel-specific playback settings
- Channel access control
- Channel status monitoring

Uses Channel model from src.models.telegram
Database fields: id (UUID), account_id, chat_id (bigint), name, status, ffmpeg_args, video_quality
"""

import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import and_

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from src.models import Channel, TelegramAccount
from src.database import get_db

logger = logging.getLogger(__name__)

# Redis keys for channel status caching
CHANNEL_STATUS_KEY = "channel:status:{channel_id}"
CHANNEL_STATUS_TTL = 3600  # 1 hour


class ChannelService:
    """
    Service for managing multiple Telegram channels.
    
    Uses Channel model with fields:
    - id: UUID primary key
    - chat_id: Telegram chat ID (bigint)
    - name: Channel name
    - status: stopped/running/error
    - account_id: linked TelegramAccount
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize channel service.
        
        Args:
            db_session: SQLAlchemy database session (optional, will use get_db if not provided)
        """
        self._db = db_session
        self._owns_db = db_session is None
        self._redis: Optional[Any] = None
        self.logger = logger
    
    @property
    def db(self) -> Session:
        """Get database session. Auto-creates if needed."""
        if self._db is None:
            from src.database import SessionLocal
            self._db = SessionLocal()
            self._owns_db = True
        return self._db
    
    def close(self):
        """Close database session if we own it."""
        if self._owns_db and self._db is not None:
            try:
                self._db.close()
            except Exception:
                pass
            self._db = None
            self._owns_db = False
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
        return False
    
    async def _get_redis(self):
        """Get or create Redis connection for status caching."""
        if aioredis is None:
            return None
        
        if self._redis is None:
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                self._redis = aioredis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception as e:
                self.logger.warning(f"Redis connection failed: {e}")
                self._redis = None
        
        return self._redis
    
    async def list_channels(
        self,
        user_id: Optional[int] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List all channels accessible to user.
        
        Args:
            user_id: Optional user ID for access filtering (not used yet)
            active_only: If True, filter by status != 'error'
            
        Returns:
            List of channel dictionaries with status info
        """
        try:
            query = self.db.query(Channel)
            
            if active_only:
                query = query.filter(Channel.status != 'error')
            
            channels = query.all()
            
            result = []
            for channel in channels:
                channel_dict = {
                    "id": channel.chat_id,  # Use chat_id as the main ID for API
                    "uuid": str(channel.id),
                    "name": channel.name or f"Channel {channel.chat_id}",
                    "type": "channel",
                    "is_active": channel.status != 'error',
                    "account_id": str(channel.account_id) if channel.account_id else None,
                    "created_at": channel.created_at.isoformat() if channel.created_at else None,
                    "db_status": channel.status or "stopped",
                }
                
                # Get real-time status from Redis cache
                status = await self.get_channel_status(channel.chat_id)
                channel_dict.update({
                    "is_playing": status.get("is_playing", False),
                    "status": status.get("status", channel.status or "stopped"),
                    "current_track": status.get("current_track"),
                })
                
                result.append(channel_dict)
            
            self.logger.debug(f"Listed {len(result)} channels for user {user_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error listing channels: {e}", exc_info=True)
            return []
    
    async def get_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """
        Get channel by chat_id.
        
        Args:
            channel_id: Telegram channel/chat ID
            
        Returns:
            Channel dictionary or None if not found
        """
        try:
            channel = self.db.query(Channel).filter(
                Channel.chat_id == channel_id
            ).first()
            
            if not channel:
                return None
            
            return {
                "id": channel.chat_id,
                "uuid": str(channel.id),
                "name": channel.name or f"Channel {channel.chat_id}",
                "type": "channel",
                "is_active": channel.status != 'error',
                "account_id": str(channel.account_id) if channel.account_id else None,
                "created_at": channel.created_at.isoformat() if channel.created_at else None,
                "status": channel.status or "stopped",
            }
            
        except Exception as e:
            self.logger.error(f"Error getting channel {channel_id}: {e}", exc_info=True)
            return None
    
    async def get_channel_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get channel by name (case-insensitive search).
        
        Args:
            name: Channel name to search
            
        Returns:
            Channel dictionary or None if not found
        """
        try:
            channel = self.db.query(Channel).filter(
                Channel.name.ilike(f"%{name}%")
            ).first()
            
            if not channel:
                return None
            
            return {
                "id": channel.chat_id,
                "uuid": str(channel.id),
                "name": channel.name,
                "type": "channel",
                "is_active": channel.status != 'error',
                "account_id": str(channel.account_id) if channel.account_id else None,
            }
            
        except Exception as e:
            self.logger.error(f"Error getting channel by name '{name}': {e}", exc_info=True)
            return None
    
    async def user_has_access(self, user_id: int, channel_id: int) -> bool:
        """
        Check if user has access to channel.
        
        Args:
            user_id: Telegram user ID
            channel_id: Telegram channel ID
            
        Returns:
            True if user has access, False otherwise
        """
        # TODO: Implement proper permission checking when RBAC is ready
        # For now, return True for all non-error channels
        
        try:
            channel = self.db.query(Channel).filter(
                Channel.chat_id == channel_id,
                Channel.status != 'error'
            ).first()
            
            return channel is not None
            
        except Exception as e:
            self.logger.error(f"Error checking access: {e}", exc_info=True)
            return False
    
    async def get_channel_status(self, channel_id: int) -> Dict[str, Any]:
        """
        Get real-time channel status from Redis.
        
        Args:
            channel_id: Telegram channel ID (chat_id)
            
        Returns:
            Status dictionary with playback info
        """
        # Default status
        status = {
            "channel_id": channel_id,
            "is_playing": False,
            "status": "stopped",
            "current_track": None,
            "position": 0,
            "position_formatted": "0:00",
            "duration": 0,
            "queue_length": 0,
        }
        
        try:
            redis = await self._get_redis()
            if redis:
                key = CHANNEL_STATUS_KEY.format(channel_id=channel_id)
                cached = await redis.hgetall(key)
                
                if cached:
                    status.update({
                        "is_playing": cached.get("is_playing", "false") == "true",
                        "status": cached.get("status", "unknown"),
                        "position": int(cached.get("position", 0)),
                        "duration": int(cached.get("duration", 0)),
                        "queue_length": int(cached.get("queue_length", 0)),
                    })
                    
                    # Parse current track if exists
                    if cached.get("current_track_title"):
                        status["current_track"] = {
                            "title": cached.get("current_track_title"),
                            "artist": cached.get("current_track_artist"),
                        }
                    
                    # Format position
                    pos = status["position"]
                    status["position_formatted"] = f"{pos // 60}:{pos % 60:02d}"
            
        except Exception as e:
            self.logger.warning(f"Error getting channel status from Redis: {e}")
        
        return status
    
    async def update_channel_status(
        self,
        channel_id: int,
        is_playing: bool = False,
        status: str = "stopped",
        current_track: Optional[Dict[str, str]] = None,
        position: int = 0,
        duration: int = 0,
        queue_length: int = 0
    ) -> bool:
        """
        Update channel status in Redis cache.
        
        Args:
            channel_id: Telegram channel ID
            is_playing: Whether channel is currently playing
            status: Status string (playing, paused, stopped, buffering)
            current_track: Current track info dict
            position: Current position in seconds
            duration: Track duration in seconds
            queue_length: Number of items in queue
            
        Returns:
            True if update successful
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return False
            
            key = CHANNEL_STATUS_KEY.format(channel_id=channel_id)
            
            data = {
                "is_playing": "true" if is_playing else "false",
                "status": status,
                "position": str(position),
                "duration": str(duration),
                "queue_length": str(queue_length),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            if current_track:
                data["current_track_title"] = current_track.get("title", "")
                data["current_track_artist"] = current_track.get("artist", "")
            
            await redis.hset(key, mapping=data)
            await redis.expire(key, CHANNEL_STATUS_TTL)
            
            self.logger.debug(f"Updated status for channel {channel_id}: {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating channel status: {e}", exc_info=True)
            return False
    
    async def create_channel(
        self,
        channel_id: int,
        name: str,
        account_id: Optional[str] = None,
        channel_type: str = "channel"
    ) -> Optional[Dict[str, Any]]:
        """
        Create or update channel configuration.
        
        Args:
            channel_id: Telegram channel/chat ID
            name: Channel display name
            account_id: Linked Telegram account UUID (string)
            channel_type: Type of chat (not stored in DB, just for API compat)
            
        Returns:
            Created channel dictionary or None on error
        """
        try:
            # Check if channel exists
            existing = self.db.query(Channel).filter(
                Channel.chat_id == channel_id
            ).first()
            
            if existing:
                # Update existing channel
                existing.name = name
                if account_id:
                    existing.account_id = uuid.UUID(account_id)
                existing.status = "stopped"
                self.db.commit()
                channel = existing
            else:
                # Create new channel
                channel = Channel(
                    chat_id=channel_id,
                    name=name,
                    account_id=uuid.UUID(account_id) if account_id else None,
                    status="stopped",
                )
                self.db.add(channel)
                self.db.commit()
            
            self.logger.info(f"Created/updated channel {channel_id}: {name}")
            
            return {
                "id": channel.chat_id,
                "uuid": str(channel.id),
                "name": channel.name,
                "type": channel_type,
                "is_active": True,
                "account_id": str(channel.account_id) if channel.account_id else None,
            }
            
        except Exception as e:
            self.logger.error(f"Error creating channel: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    async def delete_channel(self, channel_id: int) -> bool:
        """
        Deactivate channel (set status to error).
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            True if successful
        """
        try:
            channel = self.db.query(Channel).filter(
                Channel.chat_id == channel_id
            ).first()
            
            if not channel:
                return False
            
            channel.status = "error"
            self.db.commit()
            
            self.logger.info(f"Deactivated channel {channel_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting channel: {e}", exc_info=True)
            self.db.rollback()
            return False
    
    async def get_channel_settings(self, channel_id: int) -> Dict[str, Any]:
        """
        Get all settings for a channel.
        
        Args:
            channel_id: Telegram channel ID
            
        Returns:
            Combined settings dictionary
        """
        from src.services.playback_service import PlaybackService
        
        channel = await self.get_channel(channel_id)
        if not channel:
            return {}
        
        # Get playback settings
        playback_service = PlaybackService(self.db)
        settings = playback_service.get_settings(
            user_id=channel_id,
            channel_id=channel_id
        )
        
        return {
            **channel,
            "playback": settings,
        }

