"""
Redis-based Stream Controller for multi-channel management.

Instead of using systemd (which doesn't work in Docker containers),
this controller uses Redis pub/sub to communicate with streamer service.

Architecture:
- Backend publishes commands to Redis channel 'stream:control'
- Streamer subscribes and executes commands
- Status updates are stored in Redis keys
"""

import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from uuid import UUID

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy.orm import Session
from src.models.telegram import Channel
from src.services.encryption import EncryptionService
from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis channels and keys
STREAM_CONTROL_CHANNEL = "stream:control"
STREAM_STATUS_KEY = "stream:status:{channel_id}"
STREAM_STATUS_TTL = 3600  # 1 hour (must match streamer TTL)


class RedisStreamController:
    """
    Controls streaming via Redis pub/sub messaging.
    
    Commands published to 'stream:control':
    - start: Start streaming for a channel
    - stop: Stop streaming for a channel
    - restart: Restart streaming
    - update_playlist: Notify about playlist changes
    
    Status stored in 'stream:status:{channel_id}':
    - status: running/stopped/error
    - started_at: timestamp
    - current_item: current playlist item
    - error: error message if any
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.encryption_service = EncryptionService()
        self._redis: Optional[Any] = None
        self.redis_url = settings.REDIS_URL
        
    async def _get_redis(self) -> Optional[Any]:
        """Get or create async Redis connection."""
        if aioredis is None:
            logger.error("redis.asyncio not available")
            return None
            
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
                await self._redis.ping()
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self._redis = None
                
        return self._redis
    
    def _get_sync_redis(self):
        """Get sync Redis connection for non-async contexts."""
        import redis
        return redis.from_url(self.redis_url, decode_responses=True)
    
    async def _publish_command(self, command: Dict[str, Any]) -> bool:
        """Publish command to stream control channel."""
        redis_client = await self._get_redis()
        if not redis_client:
            return False
            
        try:
            message = json.dumps(command)
            await redis_client.publish(STREAM_CONTROL_CHANNEL, message)
            logger.info(f"Published command: {command.get('action')} for channel {command.get('channel_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish command: {e}")
            return False
    
    def _publish_command_sync(self, command: Dict[str, Any]) -> bool:
        """Synchronous version of publish command."""
        try:
            redis_client = self._get_sync_redis()
            message = json.dumps(command)
            redis_client.publish(STREAM_CONTROL_CHANNEL, message)
            logger.info(f"Published command: {command.get('action')} for channel {command.get('channel_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to publish command: {e}")
            return False
    
    def _prepare_channel_config(self, channel: Channel) -> Dict[str, Any]:
        """Prepare channel configuration for streamer."""
        try:
            session_string = self.encryption_service.decrypt(
                channel.account.encrypted_session
            )
        except Exception as e:
            logger.error(f"Failed to decrypt session: {e}")
            session_string = None
            
        return {
            "channel_id": str(channel.id),
            "chat_id": channel.chat_id,
            "chat_username": getattr(channel, 'chat_username', None),  # For peer resolution
            "name": channel.name,
            "session_string": session_string,
            "api_id": settings.API_ID,
            "api_hash": settings.API_HASH,
            "video_quality": channel.video_quality or "720p",
            "ffmpeg_args": channel.ffmpeg_args,
            "stream_type": getattr(channel, 'stream_type', 'video'),
        }
    
    def start_channel(self, channel_id: str) -> bool:
        """
        Start streaming for a channel.
        
        Publishes start command with full channel config.
        """
        channel = self.db.query(Channel).filter(
            Channel.id == channel_id
        ).first()
        
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")
            
        if not channel.account or not channel.account.encrypted_session:
            raise ValueError(f"Channel {channel_id} has no associated account with session")
        
        config = self._prepare_channel_config(channel)
        
        command = {
            "action": "start",
            "channel_id": channel_id,
            "config": config,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        success = self._publish_command_sync(command)
        
        if success:
            channel.status = "starting"
            self.db.commit()
            
        return success
    
    def stop_channel(self, channel_id: str) -> bool:
        """Stop streaming for a channel."""
        channel = self.db.query(Channel).filter(
            Channel.id == channel_id
        ).first()
        
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")
        
        command = {
            "action": "stop",
            "channel_id": channel_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        success = self._publish_command_sync(command)
        
        if success:
            channel.status = "stopping"
            self.db.commit()
            
        return success
    
    def restart_channel(self, channel_id: str) -> bool:
        """Restart streaming for a channel."""
        channel = self.db.query(Channel).filter(
            Channel.id == channel_id
        ).first()
        
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")
            
        if not channel.account or not channel.account.encrypted_session:
            raise ValueError(f"Channel {channel_id} has no associated account")
        
        config = self._prepare_channel_config(channel)
        
        command = {
            "action": "restart",
            "channel_id": channel_id,
            "config": config,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        success = self._publish_command_sync(command)
        
        if success:
            channel.status = "restarting"
            self.db.commit()
            
        return success
    
    def update_playlist(self, channel_id: str) -> bool:
        """Notify streamer to reload playlist."""
        command = {
            "action": "update_playlist",
            "channel_id": channel_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return self._publish_command_sync(command)
    
    async def get_channel_status(self, channel_id: str) -> Dict[str, Any]:
        """Get real-time status from Redis."""
        redis_client = await self._get_redis()
        if not redis_client:
            return {"status": "unknown", "error": "Redis not available"}
            
        try:
            key = STREAM_STATUS_KEY.format(channel_id=channel_id)
            data = await redis_client.get(key)
            if data:
                return json.loads(data)
            return {"status": "unknown"}
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"status": "unknown", "error": str(e)}
    
    def get_channel_status_sync(self, channel_id: str) -> Dict[str, Any]:
        """Synchronous version of get_channel_status."""
        try:
            redis_client = self._get_sync_redis()
            key = STREAM_STATUS_KEY.format(channel_id=channel_id)
            data = redis_client.get(key)
            if data:
                return json.loads(data)
            return {"status": "unknown"}
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"status": "unknown", "error": str(e)}


def get_channel_controller(db: Session) -> RedisStreamController:
    """Factory function to get channel controller instance."""
    return RedisStreamController(db)
