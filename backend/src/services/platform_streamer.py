"""
Platform Streamer Service for multi-platform broadcast management.

Communicates with streamer service via Redis pub/sub to control
multi-platform streaming to YouTube, Twitch, and custom RTMP destinations.

Architecture:
- Backend publishes commands to Redis channel 'stream:control'
- Streamer subscribes and executes platform-specific commands
- Status updates are stored in Redis keys
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from sqlalchemy.orm import Session
from src.models.streaming_platform import StreamingPlatform
from src.models.broadcast_destination import BroadcastDestination
from src.models.telegram import Channel
from src.services.encryption import EncryptionService
from src.core.config import settings

logger = logging.getLogger(__name__)

# Redis channels and keys
STREAM_CONTROL_CHANNEL = "stream:control"
PLATFORM_STATUS_KEY = "platform:status:{platform_id}"
PLATFORM_STATUS_TTL = 3600  # 1 hour


class PlatformStreamerService:
    """
    Manages multi-platform broadcast configuration and control.

    Commands published to 'stream:control':
    - add_platform: Add a platform destination to a channel
    - remove_platform: Remove a platform destination
    - start_platform: Start streaming to a specific platform
    - stop_platform: Stop streaming to a specific platform
    - start_all_platforms: Start all platforms for a channel
    - stop_all_platforms: Stop all platforms for a channel
    - get_platform_status: Get status of specific platform
    - get_all_platform_statuses: Get all platform statuses

    Status stored in 'platform:status:{platform_id}':
    - status: idle/streaming/error
    - started_at: timestamp
    - rtmp_url: destination URL
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

    def _prepare_platform_config(
        self,
        platform: StreamingPlatform,
        destination: BroadcastDestination
    ) -> Dict[str, Any]:
        """
        Prepare platform configuration for streamer.

        Decrypts credentials and builds platform-specific config.
        """
        try:
            # Decrypt stream key if encrypted
            stream_key = None
            if platform.stream_key:
                try:
                    stream_key = self.encryption_service.decrypt(platform.stream_key)
                except Exception:
                    # If not encrypted, use as-is
                    stream_key = platform.stream_key

            # Decrypt additional credentials if present
            credentials = None
            if platform.encrypted_credentials:
                try:
                    credentials_json = self.encryption_service.decrypt(
                        platform.encrypted_credentials
                    )
                    credentials = json.loads(credentials_json)
                except Exception as e:
                    logger.error(f"Failed to decrypt platform credentials: {e}")

            # Parse platform settings if present
            platform_settings = None
            if destination.platform_settings:
                try:
                    platform_settings = json.loads(destination.platform_settings)
                except Exception as e:
                    logger.warning(f"Failed to parse platform settings: {e}")

            config = {
                "platform_id": str(platform.id),
                "platform_type": platform.platform_type,
                "platform_name": platform.platform_name,
                "rtmp_url": platform.stream_url,
                "stream_key": stream_key,
                "enabled": destination.enabled,
                "video_quality": platform_settings.get("video_quality", "720p") if platform_settings else "720p",
            }

            # Add platform-specific settings
            if platform_settings:
                config.update(platform_settings)

            # Add custom title/description for this destination
            if destination.custom_title:
                config["custom_title"] = destination.custom_title
            if destination.custom_description:
                config["custom_description"] = destination.custom_description

            # Add additional credentials for API-based platforms
            if credentials:
                config["credentials"] = credentials

            return config

        except Exception as e:
            logger.error(f"Failed to prepare platform config: {e}")
            raise

    def add_platform_destination(
        self,
        channel_id: str,
        platform_id: str
    ) -> bool:
        """
        Add a platform destination to a channel.

        Publishes add_platform command to streamer.
        """
        channel = self.db.query(Channel).filter(
            Channel.id == channel_id
        ).first()

        if not channel:
            raise ValueError(f"Channel {channel_id} not found")

        platform = self.db.query(StreamingPlatform).filter(
            StreamingPlatform.id == platform_id
        ).first()

        if not platform:
            raise ValueError(f"Platform {platform_id} not found")

        # Check if destination already exists
        existing = self.db.query(BroadcastDestination).filter(
            BroadcastDestination.channel_id == channel_id,
            BroadcastDestination.platform_id == platform_id
        ).first()

        if existing:
            logger.warning(f"Platform destination already exists for channel {channel_id}, platform {platform_id}")
            return True

        # Create broadcast destination
        destination = BroadcastDestination(
            channel_id=channel_id,
            platform_id=platform_id,
            enabled=True,
            status="idle"
        )
        self.db.add(destination)
        self.db.commit()

        # Prepare platform config
        config = self._prepare_platform_config(platform, destination)

        command = {
            "action": "add_platform",
            "channel_id": channel_id,
            "platform_config": config,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        success = self._publish_command_sync(command)

        if success:
            platform.status = "active"
            self.db.commit()

        return success

    def remove_platform_destination(
        self,
        channel_id: str,
        platform_id: str
    ) -> bool:
        """
        Remove a platform destination from a channel.

        Publishes remove_platform command to streamer.
        """
        destination = self.db.query(BroadcastDestination).filter(
            BroadcastDestination.channel_id == channel_id,
            BroadcastDestination.platform_id == platform_id
        ).first()

        if not destination:
            raise ValueError(f"Broadcast destination not found for channel {channel_id}, platform {platform_id}")

        # Don't remove if currently streaming
        if destination.status == "streaming":
            raise ValueError(f"Cannot remove platform while streaming. Stop the platform first.")

        command = {
            "action": "remove_platform",
            "channel_id": channel_id,
            "platform_id": platform_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        success = self._publish_command_sync(command)

        if success:
            self.db.delete(destination)
            self.db.commit()

        return success

    def start_platform_stream(
        self,
        channel_id: str,
        platform_id: str,
        source_url: Optional[str] = None
    ) -> bool:
        """
        Start streaming to a specific platform.

        Publishes start_platform command to streamer.
        """
        destination = self.db.query(BroadcastDestination).filter(
            BroadcastDestination.channel_id == channel_id,
            BroadcastDestination.platform_id == platform_id
        ).first()

        if not destination:
            raise ValueError(f"Broadcast destination not found for channel {channel_id}, platform {platform_id}")

        if not destination.enabled:
            raise ValueError(f"Platform destination is disabled")

        platform = destination.platform

        command = {
            "action": "start_platform",
            "channel_id": channel_id,
            "platform_id": platform_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if source_url:
            command["source_url"] = source_url

        success = self._publish_command_sync(command)

        if success:
            destination.status = "streaming"
            platform.status = "active"
            platform.last_error = None
            destination.last_error = None
            self.db.commit()

        return success

    def stop_platform_stream(
        self,
        channel_id: str,
        platform_id: str
    ) -> bool:
        """
        Stop streaming to a specific platform.

        Publishes stop_platform command to streamer.
        """
        destination = self.db.query(BroadcastDestination).filter(
            BroadcastDestination.channel_id == channel_id,
            BroadcastDestination.platform_id == platform_id
        ).first()

        if not destination:
            raise ValueError(f"Broadcast destination not found for channel {channel_id}, platform {platform_id}")

        command = {
            "action": "stop_platform",
            "channel_id": channel_id,
            "platform_id": platform_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        success = self._publish_command_sync(command)

        if success:
            destination.status = "idle"
            self.db.commit()

        return success

    def start_all_platforms(
        self,
        channel_id: str,
        source_url: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Start streaming to all enabled platforms for a channel.

        Returns dict mapping platform_id to success status.
        """
        destinations = self.db.query(BroadcastDestination).filter(
            BroadcastDestination.channel_id == channel_id,
            BroadcastDestination.enabled == True
        ).all()

        if not destinations:
            logger.warning(f"No enabled platforms found for channel {channel_id}")
            return {}

        # Publish start_all_platforms command to streamer
        command = {
            "action": "start_all_platforms",
            "channel_id": channel_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if source_url:
            command["source_url"] = source_url

        success = self._publish_command_sync(command)

        results = {}
        if success:
            for destination in destinations:
                try:
                    destination.status = "streaming"
                    destination.platform.status = "active"
                    destination.platform.last_error = None
                    destination.last_error = None
                    results[str(destination.platform_id)] = True
                except Exception as e:
                    logger.error(f"Failed to update destination {destination.platform_id}: {e}")
                    results[str(destination.platform_id)] = False

            self.db.commit()
        else:
            # Command failed, mark all as failed
            for destination in destinations:
                results[str(destination.platform_id)] = False

        return results

    def stop_all_platforms(self, channel_id: str) -> Dict[str, bool]:
        """
        Stop streaming to all platforms for a channel.

        Returns dict mapping platform_id to success status.
        """
        destinations = self.db.query(BroadcastDestination).filter(
            BroadcastDestination.channel_id == channel_id,
            BroadcastDestination.status == "streaming"
        ).all()

        if not destinations:
            logger.warning(f"No streaming platforms found for channel {channel_id}")
            return {}

        # Publish stop_all_platforms command to streamer
        command = {
            "action": "stop_all_platforms",
            "channel_id": channel_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        success = self._publish_command_sync(command)

        results = {}
        if success:
            for destination in destinations:
                try:
                    destination.status = "idle"
                    results[str(destination.platform_id)] = True
                except Exception as e:
                    logger.error(f"Failed to update destination {destination.platform_id}: {e}")
                    results[str(destination.platform_id)] = False

            self.db.commit()
        else:
            # Command failed, mark all as failed
            for destination in destinations:
                results[str(destination.platform_id)] = False

        return results

    async def get_platform_status(self, platform_id: str) -> Dict[str, Any]:
        """
        Get real-time status of a platform from Redis.

        Returns status dict with keys:
        - status: idle/streaming/error
        - started_at: timestamp if streaming
        - rtmp_url: destination URL
        - error: error message if any
        """
        redis_client = await self._get_redis()
        if not redis_client:
            return {"status": "unknown", "error": "Redis not available"}

        try:
            key = PLATFORM_STATUS_KEY.format(platform_id=platform_id)
            data = await redis_client.get(key)
            if data:
                return json.loads(data)
            return {"status": "unknown"}
        except Exception as e:
            logger.error(f"Failed to get platform status: {e}")
            return {"status": "unknown", "error": str(e)}

    def get_platform_status_sync(self, platform_id: str) -> Dict[str, Any]:
        """Synchronous version of get_platform_status."""
        try:
            redis_client = self._get_sync_redis()
            key = PLATFORM_STATUS_KEY.format(platform_id=platform_id)
            data = redis_client.get(key)
            if data:
                return json.loads(data)
            return {"status": "unknown"}
        except Exception as e:
            logger.error(f"Failed to get platform status: {e}")
            return {"status": "unknown", "error": str(e)}

    def get_all_platform_statuses(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Get status of all platforms for a channel.

        Returns list of status dicts for each platform destination.
        """
        destinations = self.db.query(BroadcastDestination).filter(
            BroadcastDestination.channel_id == channel_id
        ).all()

        statuses = []
        for destination in destinations:
            status = self.get_platform_status_sync(str(destination.platform_id))
            statuses.append({
                "platform_id": str(destination.platform_id),
                "platform_name": destination.platform.platform_name,
                "platform_type": destination.platform.platform_type,
                "enabled": destination.enabled,
                "status": status.get("status", "unknown"),
                "streaming_since": status.get("started_at"),
                "error": status.get("error") or destination.last_error,
            })

        return statuses


def get_platform_streamer(db: Session) -> PlatformStreamerService:
    """Factory function to get platform streamer service instance."""
    return PlatformStreamerService(db)
