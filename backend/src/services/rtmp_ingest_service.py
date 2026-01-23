"""
RTMPIngestService for managing RTMP/SRT live stream ingestion.

Features:
- Create and manage live stream ingest endpoints
- Generate stream keys and ingestion URLs
- Validate RTMP/SRT URLs
- Stream lifecycle management
"""

import logging
import secrets
from typing import List, Optional
from urllib.parse import urlparse
from sqlalchemy.orm import Session

from src.models import LiveStream, LiveStreamStatus, IngestionType


logger = logging.getLogger(__name__)


class RTMPIngestService:
    """Manages RTMP/SRT live stream ingestion."""

    def __init__(self, db_session: Session):
        """Initialize RTMP ingest service."""
        self.db = db_session
        self.logger = logger

    def generate_stream_key(self) -> str:
        """
        Generate a secure unique stream key for RTMP ingestion.

        Returns:
            Cryptographically secure random stream key (32 bytes, hex-encoded)
        """
        return secrets.token_hex(32)

    def validate_ingestion_url(self, url: str, ingestion_type: IngestionType) -> bool:
        """
        Validate ingestion URL format based on protocol.

        Args:
            url: Stream ingestion URL to validate
            ingestion_type: Type of ingestion (RTMP or SRT)

        Returns:
            True if URL is valid for the given ingestion type

        Raises:
            ValueError: If URL format is invalid
        """
        try:
            parsed = urlparse(url)

            # Check protocol matches ingestion type
            if ingestion_type == IngestionType.RTMP:
                if parsed.scheme not in ["rtmp", "rtmps"]:
                    raise ValueError(f"Invalid protocol for RTMP: {parsed.scheme} (must be rtmp or rtmps)")
            elif ingestion_type == IngestionType.SRT:
                if parsed.scheme not in ["srt", "srts"]:
                    raise ValueError(f"Invalid protocol for SRT: {parsed.scheme} (must be srt or srts)")

            # Check for netloc (host)
            if not parsed.netloc:
                raise ValueError("URL must contain host")

            return True

        except Exception as e:
            raise ValueError(f"Ingestion URL validation failed: {e}")

    def create_ingest_endpoint(
        self,
        owner_id: str,
        chat_id: int,
        title: str,
        ingestion_type: IngestionType,
        ingestion_url: Optional[str] = None,
        max_guests: int = 5,
        recording_enabled: bool = True,
        quality_preset: Optional[str] = None
    ) -> LiveStream:
        """
        Create a new live stream ingest endpoint.

        Args:
            owner_id: User ID who owns the stream
            chat_id: Telegram chat ID for broadcasting
            title: Display title for the stream
            ingestion_type: Type of ingestion (RTMP, SRT, WEBRTC_CAMERA, WEBRTC_SCREEN)
            ingestion_url: Optional custom ingestion URL (auto-generated if None)
            max_guests: Maximum number of co-hosts (default: 5)
            recording_enabled: Enable automatic recording (default: True)
            quality_preset: Quality preset (low, medium, high, ultra)

        Returns:
            Created LiveStream object

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate max_guests
        if max_guests < 0 or max_guests > 50:
            raise ValueError("max_guests must be between 0 and 50")

        # Validate quality_preset
        valid_presets = ["low", "medium", "high", "ultra", None]
        if quality_preset not in valid_presets:
            raise ValueError(f"Invalid quality_preset: {quality_preset} (must be one of {valid_presets})")

        # Validate custom ingestion URL if provided
        if ingestion_url:
            if ingestion_type in [IngestionType.RTMP, IngestionType.SRT]:
                self.validate_ingestion_url(ingestion_url, ingestion_type)

        # Generate stream key for RTMP/SRT
        stream_key = None
        if ingestion_type in [IngestionType.RTMP, IngestionType.SRT]:
            stream_key = self.generate_stream_key()
            # Auto-generate ingestion URL if not provided
            if not ingestion_url:
                # Default RTMP URL format (can be overridden by env config)
                if ingestion_type == IngestionType.RTMP:
                    ingestion_url = f"rtmp://localhost:1935/live/{stream_key}"
                elif ingestion_type == IngestionType.SRT:
                    ingestion_url = f"srt://localhost:4000?streamid={stream_key}"

        # Create live stream
        stream = LiveStream(
            owner_id=owner_id,
            chat_id=chat_id,
            title=title,
            status=LiveStreamStatus.IDLE,
            ingestion_type=ingestion_type,
            ingestion_url=ingestion_url,
            stream_key=stream_key,
            max_guests=max_guests,
            recording_enabled=recording_enabled,
            quality_preset=quality_preset,
            current_guest_count=0,
            viewer_count=0
        )

        self.db.add(stream)
        self.db.commit()

        self.logger.info(
            f"Live stream ingest endpoint created: {title} "
            f"(type={ingestion_type}, owner={owner_id}, chat={chat_id})"
        )

        return stream

    def get_stream(self, stream_id: str) -> Optional[LiveStream]:
        """
        Get live stream by ID.

        Args:
            stream_id: Stream identifier

        Returns:
            LiveStream object or None if not found
        """
        return self.db.query(LiveStream).filter(LiveStream.id == stream_id).first()

    def get_stream_by_key(self, stream_key: str) -> Optional[LiveStream]:
        """
        Get live stream by stream key (used for RTMP authentication).

        Args:
            stream_key: Stream key for authentication

        Returns:
            LiveStream object or None if not found
        """
        return self.db.query(LiveStream).filter(LiveStream.stream_key == stream_key).first()

    def get_streams_by_owner(self, owner_id: str, active_only: bool = False) -> List[LiveStream]:
        """
        Get all live streams for a specific owner.

        Args:
            owner_id: User ID who owns the streams
            active_only: If True, return only active streams

        Returns:
            List of LiveStream objects
        """
        query = self.db.query(LiveStream).filter(LiveStream.owner_id == owner_id)

        if active_only:
            query = query.filter(LiveStream.status == LiveStreamStatus.ACTIVE)

        return query.order_by(LiveStream.created_at.desc()).all()

    def get_streams_by_chat(self, chat_id: int, active_only: bool = False) -> List[LiveStream]:
        """
        Get all live streams for a specific Telegram chat.

        Args:
            chat_id: Telegram chat ID
            active_only: If True, return only active streams

        Returns:
            List of LiveStream objects
        """
        query = self.db.query(LiveStream).filter(LiveStream.chat_id == chat_id)

        if active_only:
            query = query.filter(LiveStream.status == LiveStreamStatus.ACTIVE)

        return query.order_by(LiveStream.created_at.desc()).all()

    def get_all_streams(self, status: Optional[LiveStreamStatus] = None) -> List[LiveStream]:
        """
        Get all live streams, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of LiveStream objects
        """
        query = self.db.query(LiveStream)

        if status:
            query = query.filter(LiveStream.status == status)

        return query.order_by(LiveStream.created_at.desc()).all()

    def update_stream_status(
        self,
        stream_id: str,
        status: LiveStreamStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update the status of a live stream.

        Args:
            stream_id: Stream identifier
            status: New status
            error_message: Optional error message if status is ERROR

        Returns:
            True if stream was found and updated

        Raises:
            ValueError: If stream not found
        """
        stream = self.get_stream(stream_id)

        if not stream:
            raise ValueError(f"Stream not found: {stream_id}")

        old_status = stream.status
        stream.status = status

        # Update timestamps based on status transitions
        if status == LiveStreamStatus.ACTIVE and old_status != LiveStreamStatus.ACTIVE:
            from datetime import datetime
            stream.started_at = datetime.utcnow()
            self.logger.info(f"Stream started: {stream.title}")

        elif status == LiveStreamStatus.STOPPED and old_status == LiveStreamStatus.ACTIVE:
            from datetime import datetime
            stream.stopped_at = datetime.utcnow()
            self.logger.info(f"Stream stopped: {stream.title}")

        elif status == LiveStreamStatus.ERROR:
            stream.last_error = error_message
            stream.error_count += 1
            self.logger.warning(
                f"Stream error: {stream.title} - {error_message} "
                f"(error count: {stream.error_count})"
            )

        self.db.commit()

        return True

    def regenerate_stream_key(self, stream_id: str) -> str:
        """
        Regenerate a new stream key for an existing stream.

        Args:
            stream_id: Stream identifier

        Returns:
            New stream key

        Raises:
            ValueError: If stream not found or is not RTMP/SRT
        """
        stream = self.get_stream(stream_id)

        if not stream:
            raise ValueError(f"Stream not found: {stream_id}")

        if stream.ingestion_type not in [IngestionType.RTMP, IngestionType.SRT]:
            raise ValueError(f"Cannot regenerate stream key for ingestion type: {stream.ingestion_type}")

        # Only allow regeneration when stream is IDLE
        if stream.status != LiveStreamStatus.IDLE:
            raise ValueError(f"Cannot regenerate stream key while stream is {stream.status}")

        # Generate new key and update URL
        new_key = self.generate_stream_key()
        stream.stream_key = new_key

        # Update ingestion URL with new key
        if stream.ingestion_type == IngestionType.RTMP:
            stream.ingestion_url = f"rtmp://localhost:1935/live/{new_key}"
        elif stream.ingestion_type == IngestionType.SRT:
            stream.ingestion_url = f"srt://localhost:4000?streamid={new_key}"

        self.db.commit()

        self.logger.info(f"Stream key regenerated: {stream.title}")

        return new_key

    def delete_stream(self, stream_id: str) -> bool:
        """
        Delete a live stream (hard delete).

        Args:
            stream_id: Stream identifier

        Returns:
            True if stream was found and deleted
        """
        stream = self.get_stream(stream_id)

        if not stream:
            return False

        # Prevent deletion of active streams
        if stream.status == LiveStreamStatus.ACTIVE:
            raise ValueError(f"Cannot delete active stream. Stop it first.")

        self.db.delete(stream)
        self.db.commit()

        self.logger.info(f"Live stream deleted: {stream.title}")

        return True

    def update_viewer_count(self, stream_id: str, count: int) -> bool:
        """
        Update viewer count for a stream.

        Args:
            stream_id: Stream identifier
            count: New viewer count

        Returns:
            True if stream was found and updated
        """
        stream = self.get_stream(stream_id)

        if not stream:
            return False

        stream.viewer_count = count

        from datetime import datetime
        stream.last_viewer_update = datetime.utcnow()

        self.db.commit()

        self.logger.debug(f"Viewer count updated: {stream.title} → {count}")

        return True

    def update_latency(self, stream_id: str, latency_ms: int) -> bool:
        """
        Update latency measurement for a stream.

        Args:
            stream_id: Stream identifier
            latency_ms: Latency in milliseconds

        Returns:
            True if stream was found and updated
        """
        stream = self.get_stream(stream_id)

        if not stream:
            return False

        stream.latency_ms = latency_ms
        self.db.commit()

        self.logger.debug(f"Latency updated: {stream.title} → {latency_ms}ms")

        return True

    def increment_guest_count(self, stream_id: str) -> bool:
        """
        Increment the guest count for a stream.

        Args:
            stream_id: Stream identifier

        Returns:
            True if stream was found and updated

        Raises:
            ValueError: If guest limit reached
        """
        stream = self.get_stream(stream_id)

        if not stream:
            return False

        if stream.current_guest_count >= stream.max_guests:
            raise ValueError(f"Guest limit reached: {stream.max_guests}")

        stream.current_guest_count += 1
        self.db.commit()

        self.logger.debug(
            f"Guest count incremented: {stream.title} → {stream.current_guest_count}/{stream.max_guests}"
        )

        return True

    def decrement_guest_count(self, stream_id: str) -> bool:
        """
        Decrement the guest count for a stream.

        Args:
            stream_id: Stream identifier

        Returns:
            True if stream was found and updated
        """
        stream = self.get_stream(stream_id)

        if not stream:
            return False

        if stream.current_guest_count > 0:
            stream.current_guest_count -= 1
            self.db.commit()

            self.logger.debug(
                f"Guest count decremented: {stream.title} → {stream.current_guest_count}/{stream.max_guests}"
            )

        return True
