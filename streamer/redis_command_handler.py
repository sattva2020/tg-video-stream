"""
Redis Command Handler for multi-channel stream control.

Listens for control commands from backend via Redis pub/sub:
- start: Start streaming for a specific channel
- stop: Stop streaming for a channel  
- restart: Restart a channel's stream
- update_playlist: Reload playlist for a channel

Status updates are published back to Redis.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, Callable, Awaitable
from datetime import datetime, timezone
from dataclasses import dataclass

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

logger = logging.getLogger(__name__)

# Redis channels
STREAM_CONTROL_CHANNEL = "stream:control"
STREAM_STATUS_KEY = "stream:status:{channel_id}"
STREAM_STATUS_TTL = 3600  # 1 hour (increased from 5 minutes)


@dataclass
class ChannelConfig:
    """Configuration for a streaming channel."""
    channel_id: str
    chat_id: int
    name: str
    session_string: str
    api_id: int
    api_hash: str
    video_quality: str = "720p"
    ffmpeg_args: Optional[str] = None
    chat_username: Optional[str] = None  # For peer resolution


class RedisCommandHandler:
    """
    Handles commands from backend via Redis pub/sub.
    
    Usage:
        handler = RedisCommandHandler(redis_url)
        handler.on_start = my_start_callback
        handler.on_stop = my_stop_callback
        await handler.start()
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or self._get_redis_url()
        self._redis: Optional[Any] = None
        self._pubsub: Optional[Any] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Callbacks for command handling
        self.on_start: Optional[Callable[[ChannelConfig], Awaitable[bool]]] = None
        self.on_stop: Optional[Callable[[str], Awaitable[bool]]] = None
        self.on_restart: Optional[Callable[[ChannelConfig], Awaitable[bool]]] = None
        self.on_update_playlist: Optional[Callable[[str], Awaitable[bool]]] = None
    
    @staticmethod
    def _get_redis_url() -> str:
        """Build Redis URL from environment variables."""
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = os.getenv("REDIS_PORT", "6379")
        redis_db = os.getenv("REDIS_DB", "0")
        redis_url = os.getenv("REDIS_URL")
        
        if redis_url:
            return redis_url
        return f"redis://{redis_host}:{redis_port}/{redis_db}"
    
    async def _get_redis(self) -> Optional[Any]:
        """Get or create Redis connection."""
        if aioredis is None:
            logger.error("redis.asyncio not available - install redis package")
            return None
            
        if self._redis is None:
            try:
                self._redis = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
                await self._redis.ping()
                logger.info(f"Connected to Redis: {self.redis_url}")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self._redis = None
                
        return self._redis
    
    async def update_status(
        self,
        channel_id: str,
        status: str,
        current_item: Optional[str] = None,
        error: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Update channel status in Redis."""
        redis_client = await self._get_redis()
        if not redis_client:
            return
            
        try:
            data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            if current_item:
                data["current_item"] = current_item
            if error:
                data["error"] = error
            if extra:
                data.update(extra)
                
            key = STREAM_STATUS_KEY.format(channel_id=channel_id)
            await redis_client.setex(key, STREAM_STATUS_TTL, json.dumps(data))
            logger.debug(f"Updated status for {channel_id}: {status}")
            
        except Exception as e:
            logger.error(f"Failed to update status: {e}")
    
    async def _handle_message(self, message: Dict[str, Any]):
        """Process a control command message."""
        try:
            channel = message.get("channel")
            if channel != STREAM_CONTROL_CHANNEL:
                return
                
            data_str = message.get("data")
            if not data_str or not isinstance(data_str, str):
                return
                
            command = json.loads(data_str)
            action = command.get("action")
            channel_id = command.get("channel_id")
            
            logger.info(f"Received command: {action} for channel {channel_id}")
            
            if action == "start":
                await self._handle_start(command)
            elif action == "stop":
                await self._handle_stop(command)
            elif action == "restart":
                await self._handle_restart(command)
            elif action == "update_playlist":
                await self._handle_update_playlist(command)
            else:
                logger.warning(f"Unknown command action: {action}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in command: {e}")
        except Exception as e:
            logger.exception(f"Error handling command: {e}")
    
    async def _handle_start(self, command: Dict[str, Any]):
        """Handle start command."""
        channel_id = command.get("channel_id")
        config_data = command.get("config", {})
        
        if not channel_id:
            logger.error("Start command missing channel_id")
            return
            
        if not self.on_start:
            logger.warning("No on_start callback registered")
            await self.update_status(channel_id, "error", error="No start handler")
            return
        
        try:
            config = ChannelConfig(
                channel_id=config_data.get("channel_id", channel_id),
                chat_id=config_data.get("chat_id"),
                name=config_data.get("name", "Unknown"),
                session_string=config_data.get("session_string", ""),
                api_id=config_data.get("api_id", 0),
                api_hash=config_data.get("api_hash", ""),
                video_quality=config_data.get("video_quality", "720p"),
                ffmpeg_args=config_data.get("ffmpeg_args"),
                chat_username=config_data.get("chat_username"),
            )
            
            await self.update_status(channel_id, "starting")
            success = await self.on_start(config)
            
            if success:
                await self.update_status(channel_id, "running")
            else:
                await self.update_status(channel_id, "error", error="Start failed")
                
        except Exception as e:
            logger.exception(f"Error starting channel {channel_id}: {e}")
            await self.update_status(channel_id, "error", error=str(e))
    
    async def _handle_stop(self, command: Dict[str, Any]):
        """Handle stop command."""
        channel_id = command.get("channel_id")
        
        if not channel_id:
            logger.error("Stop command missing channel_id")
            return
            
        if not self.on_stop:
            logger.warning("No on_stop callback registered")
            return
        
        try:
            await self.update_status(channel_id, "stopping")
            success = await self.on_stop(channel_id)
            
            if success:
                await self.update_status(channel_id, "stopped")
            else:
                await self.update_status(channel_id, "error", error="Stop failed")
                
        except Exception as e:
            logger.exception(f"Error stopping channel {channel_id}: {e}")
            await self.update_status(channel_id, "error", error=str(e))
    
    async def _handle_restart(self, command: Dict[str, Any]):
        """Handle restart command."""
        channel_id = command.get("channel_id")
        config_data = command.get("config", {})
        
        if not channel_id:
            logger.error("Restart command missing channel_id")
            return
            
        if not self.on_restart:
            # Fallback to stop + start
            if self.on_stop and self.on_start:
                await self._handle_stop(command)
                await asyncio.sleep(2)
                await self._handle_start(command)
            return
        
        try:
            config = ChannelConfig(
                channel_id=config_data.get("channel_id", channel_id),
                chat_id=config_data.get("chat_id"),
                name=config_data.get("name", "Unknown"),
                session_string=config_data.get("session_string", ""),
                api_id=config_data.get("api_id", 0),
                api_hash=config_data.get("api_hash", ""),
                video_quality=config_data.get("video_quality", "720p"),
                ffmpeg_args=config_data.get("ffmpeg_args"),
            )
            
            await self.update_status(channel_id, "restarting")
            success = await self.on_restart(config)
            
            if success:
                await self.update_status(channel_id, "running")
            else:
                await self.update_status(channel_id, "error", error="Restart failed")
                
        except Exception as e:
            logger.exception(f"Error restarting channel {channel_id}: {e}")
            await self.update_status(channel_id, "error", error=str(e))
    
    async def _handle_update_playlist(self, command: Dict[str, Any]):
        """Handle playlist update notification."""
        channel_id = command.get("channel_id")
        
        if not channel_id:
            logger.error("Update playlist command missing channel_id")
            return
            
        if not self.on_update_playlist:
            logger.debug("No on_update_playlist callback - ignoring")
            return
        
        try:
            await self.on_update_playlist(channel_id)
            logger.info(f"Playlist update triggered for channel {channel_id}")
        except Exception as e:
            logger.exception(f"Error updating playlist for {channel_id}: {e}")
    
    async def _listen_loop(self):
        """Main loop for listening to Redis commands."""
        while self._running:
            try:
                redis_client = await self._get_redis()
                if not redis_client:
                    await asyncio.sleep(5)
                    continue
                
                self._pubsub = redis_client.pubsub()
                await self._pubsub.subscribe(STREAM_CONTROL_CHANNEL)
                logger.info(f"Subscribed to {STREAM_CONTROL_CHANNEL}")
                
                async for message in self._pubsub.listen():
                    if not self._running:
                        break
                    if message["type"] == "message":
                        await self._handle_message(message)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Redis listener error: {e}")
                await asyncio.sleep(5)
                self._redis = None  # Force reconnect
    
    async def start(self):
        """Start the command handler."""
        if self._running:
            return
            
        self._running = True
        self._task = asyncio.create_task(self._listen_loop())
        logger.info("Redis command handler started")
    
    async def stop(self):
        """Stop the command handler."""
        self._running = False
        
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(STREAM_CONTROL_CHANNEL)
                await self._pubsub.close()
            except Exception:
                pass
                
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
                
        logger.info("Redis command handler stopped")
