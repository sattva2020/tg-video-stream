"""
StreamSwitchingService for seamless stream transitions.

Manages:
- Switching between pre-recorded and live content
- Stream transition preparation and validation
- Switch history tracking
- Seamless transitions with minimal interruption

Integrates with:
- LiveStream ORM model for live stream state
- Stream domain entity for business logic
- RTMPIngestService for RTMP/SRT streams
- WebRTCSignalingService for WebRTC guest streams
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.live_stream import LiveStream, LiveStreamStatus, IngestionType
from src.models.stream import Stream as StreamORM
from src.domain.entities.stream import Stream as StreamEntity, StreamType, StreamStatus


logger = logging.getLogger(__name__)


class SwitchTransition(str):
    """Тип перехода при переключении потока."""
    SCHEDULED_TO_LIVE = "scheduled_to_live"
    LIVE_TO_SCHEDULED = "live_to_scheduled"
    LIVE_TO_LIVE = "live_to_live"  # Смена источника live потока
    SCHEDULED_TO_SCHEDULED = "scheduled_to_scheduled"  # Смена трека/плейлиста


class StreamSwitchingService:
    """Manages seamless stream switching operations."""

    def __init__(self, db_session: Session):
        """Initialize stream switching service."""
        self.db = db_session
        self.logger = logger

    def get_active_stream(
        self,
        chat_id: int,
        channel_id: Optional[int] = None
    ) -> Optional[LiveStream]:
        """
        Get currently active stream for chat.

        Args:
            chat_id: Telegram chat ID
            channel_id: Optional channel identifier for multi-channel support

        Returns:
            LiveStream object if active, None otherwise
        """
        active_stream = self.db.query(LiveStream).filter(
            LiveStream.chat_id == chat_id,
            LiveStream.status == LiveStreamStatus.ACTIVE
        ).first()

        return active_stream

    def can_switch_to_live(
        self,
        chat_id: int,
        target_ingestion_type: IngestionType,
        channel_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate if switching to live stream is possible.

        Args:
            chat_id: Telegram chat ID
            target_ingestion_type: Target ingestion type (RTMP, SRT, WEBRTC_CAMERA, WEBRTC_SCREEN)
            channel_id: Optional channel identifier

        Returns:
            Dict with validation result:
            - can_switch: bool indicating if switch is possible
            - reason: str with explanation if cannot switch
            - current_stream: Optional[LiveStream] of currently active stream
        """
        active_stream = self.get_active_stream(chat_id, channel_id)

        if active_stream:
            # Stream is already live
            if active_stream.ingestion_type == target_ingestion_type:
                return {
                    "can_switch": False,
                    "reason": f"Stream is already {target_ingestion_type.value}",
                    "current_stream": active_stream
                }
            else:
                # Can switch between different live sources
                return {
                    "can_switch": True,
                    "reason": f"Can switch from {active_stream.ingestion_type.value} to {target_ingestion_type.value}",
                    "transition": SwitchTransition.LIVE_TO_LIVE,
                    "current_stream": active_stream
                }

        # No active stream, can start new live stream
        return {
            "can_switch": True,
            "reason": "No active stream, can start live stream",
            "transition": SwitchTransition.SCHEDULED_TO_LIVE,
            "current_stream": None
        }

    def can_switch_to_scheduled(
        self,
        chat_id: int,
        channel_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate if switching to pre-recorded content is possible.

        Args:
            chat_id: Telegram chat ID
            channel_id: Optional channel identifier

        Returns:
            Dict with validation result:
            - can_switch: bool indicating if switch is possible
            - reason: str with explanation if cannot switch
            - current_stream: Optional[LiveStream] of currently active stream
        """
        active_stream = self.get_active_stream(chat_id, channel_id)

        if not active_stream:
            return {
                "can_switch": False,
                "reason": "No active stream to switch from",
                "current_stream": None
            }

        # Can switch from live to pre-recorded
        return {
            "can_switch": True,
            "reason": "Can switch from live to pre-recorded content",
            "transition": SwitchTransition.LIVE_TO_SCHEDULED,
            "current_stream": active_stream
        }

    def prepare_live_stream(
        self,
        live_stream_id: UUID,
        channel_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Prepare live stream for broadcasting (validation and setup).

        Args:
            live_stream_id: LiveStream UUID
            channel_id: Optional channel identifier

        Returns:
            Dict with preparation result:
            - is_ready: bool indicating if stream is ready
            - ingestion_url: str with RTMP/SRT URL for streaming
            - stream_key: str with stream key for authentication
            - preview_url: str with preview URL
            - issues: List[str] with any issues found

        Raises:
            ValueError: If live stream not found
        """
        live_stream = self.db.query(LiveStream).filter(
            LiveStream.id == live_stream_id
        ).first()

        if not live_stream:
            raise ValueError(f"LiveStream {live_stream_id} not found")

        issues = []

        # Check status
        if live_stream.status not in [LiveStreamStatus.IDLE, LiveStreamStatus.STOPPED]:
            issues.append(f"Stream status is {live_stream.status}, must be IDLE or STOPPED")

        # Check ingestion URL for RTMP/SRT
        if live_stream.ingestion_type in [IngestionType.RTMP, IngestionType.SRT]:
            if not live_stream.ingestion_url or not live_stream.stream_key:
                issues.append(f"{live_stream.ingestion_type.value} stream requires ingestion_url and stream_key")

        # Check guest limits if WebRTC
        if live_stream.ingestion_type in [IngestionType.WEBRTC_CAMERA, IngestionType.WEBRTC_SCREEN]:
            if live_stream.current_guest_count >= live_stream.max_guests:
                issues.append(f"Guest limit reached ({live_stream.max_guests})")

        # Check error count
        if live_stream.error_count > 5:
            issues.append(f"Stream has {live_stream.error_count} errors, may be unstable")

        is_ready = len(issues) == 0

        result = {
            "is_ready": is_ready,
            "live_stream_id": str(live_stream_id),
            "ingestion_type": live_stream.ingestion_type.value,
            "ingestion_url": live_stream.ingestion_url,
            "stream_key": live_stream.stream_key,
            "preview_url": live_stream.preview_url,
            "issues": issues
        }

        if is_ready:
            self.logger.info(
                "LiveStream %s is ready for broadcasting (type=%s, chat_id=%s)",
                live_stream_id,
                live_stream.ingestion_type.value,
                live_stream.chat_id
            )
        else:
            self.logger.warning(
                "LiveStream %s has issues: %s",
                live_stream_id,
                ", ".join(issues)
            )

        return result

    def execute_switch_to_live(
        self,
        live_stream_id: UUID,
        stop_current: bool = True,
        channel_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute switch from pre-recorded to live content.

        Args:
            live_stream_id: Target LiveStream UUID
            stop_current: Whether to stop currently active stream (default: True)
            channel_id: Optional channel identifier

        Returns:
            Dict with switch result:
            - success: bool indicating if switch was successful
            - live_stream_id: str with UUID of switched stream
            - previous_stream_id: Optional[str] with previous stream if stopped
            - transition: str with transition type
            - message: str with status message

        Raises:
            ValueError: If validation fails
        """
        # Get target live stream
        live_stream = self.db.query(LiveStream).filter(
            LiveStream.id == live_stream_id
        ).first()

        if not live_stream:
            raise ValueError(f"LiveStream {live_stream_id} not found")

        # Validate stream is ready
        prep_result = self.prepare_live_stream(live_stream_id, channel_id)
        if not prep_result["is_ready"]:
            raise ValueError(f"Stream not ready: {', '.join(prep_result['issues'])}")

        # Get current active stream in chat
        current_active = self.get_active_stream(live_stream.chat_id, channel_id)
        previous_stream_id = None

        if current_active and stop_current:
            # Stop current stream
            previous_stream_id = str(current_active.id)
            current_active.status = LiveStreamStatus.STOPPED
            current_active.stopped_at = datetime.utcnow()
            self.logger.info(
                "Stopped previous stream %s before switching to %s",
                previous_stream_id,
                live_stream_id
            )

        # Start live stream
        live_stream.status = LiveStreamStatus.ACTIVE
        live_stream.started_at = datetime.utcnow()
        if live_stream.stream_type == StreamType.SCHEDULED:
            live_stream.went_live_at = datetime.utcnow()

        self.db.commit()

        self.logger.info(
            "Switched to live stream %s (type=%s, chat_id=%s)",
            live_stream_id,
            live_stream.ingestion_type.value,
            live_stream.chat_id
        )

        return {
            "success": True,
            "live_stream_id": str(live_stream_id),
            "previous_stream_id": previous_stream_id,
            "transition": SwitchTransition.SCHEDULED_TO_LIVE if current_active else SwitchTransition.LIVE_TO_LIVE,
            "ingestion_type": live_stream.ingestion_type.value,
            "message": f"Switched to {live_stream.ingestion_type.value} stream"
        }

    def execute_switch_to_scheduled(
        self,
        chat_id: int,
        stop_live: bool = True,
        channel_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute switch from live to pre-recorded content.

        Args:
            chat_id: Telegram chat ID
            stop_live: Whether to stop live stream (default: True)
            channel_id: Optional channel identifier

        Returns:
            Dict with switch result:
            - success: bool indicating if switch was successful
            - stopped_stream_id: Optional[str] with UUID of stopped live stream
            - transition: str with transition type
            - message: str with status message

        Raises:
            ValueError: If no active live stream found
        """
        # Get active live stream
        active_live = self.get_active_stream(chat_id, channel_id)

        if not active_live:
            raise ValueError(f"No active live stream found in chat {chat_id}")

        stopped_stream_id = str(active_live.id)

        if stop_live:
            # Stop live stream
            active_live.status = LiveStreamStatus.STOPPED
            active_live.stopped_at = datetime.utcnow()

            # Stop recording if active
            if active_live.active_recording_id:
                active_live.active_recording_id = None
                self.logger.info(
                    "Stopped recording %s for live stream %s",
                    active_live.active_recording_id,
                    stopped_stream_id
                )

        self.db.commit()

        self.logger.info(
            "Switched from live stream %s to pre-recorded content (chat_id=%s)",
            stopped_stream_id,
            chat_id
        )

        return {
            "success": True,
            "stopped_stream_id": stopped_stream_id,
            "transition": SwitchTransition.LIVE_TO_SCHEDULED,
            "message": "Switched to pre-recorded content"
        }

    def get_switch_history(
        self,
        chat_id: int,
        limit: int = 50,
        channel_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get history of stream switches for chat (based on status changes).

        Args:
            chat_id: Telegram chat ID
            limit: Maximum number of records to return
            channel_id: Optional channel identifier

        Returns:
            List of dicts with switch history:
            - live_stream_id: str
            - status: str
            - ingestion_type: str
            - started_at: datetime
            - stopped_at: Optional[datetime]
            - went_live_at: Optional[datetime]
        """
        streams = self.db.query(LiveStream).filter(
            LiveStream.chat_id == chat_id
        ).order_by(
            LiveStream.started_at.desc()
        ).limit(limit).all()

        history = []
        for stream in streams:
            history.append({
                "live_stream_id": str(stream.id),
                "title": stream.title,
                "status": stream.status.value,
                "ingestion_type": stream.ingestion_type.value,
                "started_at": stream.started_at.isoformat() if stream.started_at else None,
                "stopped_at": stream.stopped_at.isoformat() if stream.stopped_at else None,
                "went_live_at": stream.went_live_at.isoformat() if stream.went_live_at else None,
                "created_at": stream.created_at.isoformat() if stream.created_at else None,
                "viewer_count": stream.viewer_count,
                "latency_ms": stream.latency_ms
            })

        return history

    def get_switch_status(
        self,
        chat_id: int,
        channel_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get current switch status for chat.

        Args:
            chat_id: Telegram chat ID
            channel_id: Optional channel identifier

        Returns:
            Dict with current status:
            - is_live: bool indicating if currently live
            - active_stream_id: Optional[str] with active stream ID
            - ingestion_type: Optional[str] with current ingestion type
            - can_switch_to_live: bool
            - can_switch_to_scheduled: bool
            - viewer_count: int
            - latency_ms: Optional[int]
        """
        active_stream = self.get_active_stream(chat_id, channel_id)

        result = {
            "chat_id": chat_id,
            "is_live": active_stream is not None,
            "active_stream_id": str(active_stream.id) if active_stream else None,
            "ingestion_type": active_stream.ingestion_type.value if active_stream else None,
            "status": active_stream.status.value if active_stream else None,
            "viewer_count": active_stream.viewer_count if active_stream else 0,
            "latency_ms": active_stream.latency_ms if active_stream else None,
            "can_switch_to_live": False,
            "can_switch_to_scheduled": active_stream is not None
        }

        # Check if can switch to different live sources
        if not active_stream:
            result["can_switch_to_live"] = True
        else:
            # Can switch between live sources
            result["can_switch_to_live"] = True

        return result

    def validate_transition(
        self,
        from_type: Optional[StreamType],
        to_type: StreamType,
        from_ingestion: Optional[IngestionType] = None,
        to_ingestion: Optional[IngestionType] = None
    ) -> Dict[str, Any]:
        """
        Validate stream transition is supported.

        Args:
            from_type: Source stream type (SCHEDULED or LIVE)
            to_type: Target stream type
            from_ingestion: Source ingestion type (if LIVE)
            to_ingestion: Target ingestion type (if LIVE)

        Returns:
            Dict with validation result:
            - is_valid: bool indicating if transition is valid
            - transition: str with transition type
            - reason: str with explanation
        """
        # SCHEDULED → LIVE: Always valid
        if from_type == StreamType.SCHEDULED and to_type == StreamType.LIVE:
            return {
                "is_valid": True,
                "transition": SwitchTransition.SCHEDULED_TO_LIVE,
                "reason": "Can switch from pre-recorded to live content"
            }

        # LIVE → SCHEDULED: Always valid
        if from_type == StreamType.LIVE and to_type == StreamType.SCHEDULED:
            return {
                "is_valid": True,
                "transition": SwitchTransition.LIVE_TO_SCHEDULED,
                "reason": "Can switch from live to pre-recorded content"
            }

        # LIVE → LIVE: Valid if different ingestion types
        if from_type == StreamType.LIVE and to_type == StreamType.LIVE:
            if from_ingestion and to_ingestion and from_ingestion != to_ingestion:
                return {
                    "is_valid": True,
                    "transition": SwitchTransition.LIVE_TO_LIVE,
                    "reason": f"Can switch from {from_ingestion.value} to {to_ingestion.value}"
                }
            else:
                return {
                    "is_valid": False,
                    "transition": None,
                    "reason": "Cannot switch to same live source"
                }

        # SCHEDULED → SCHEDULED: Valid (track change)
        if from_type == StreamType.SCHEDULED and to_type == StreamType.SCHEDULED:
            return {
                "is_valid": True,
                "transition": SwitchTransition.SCHEDULED_TO_SCHEDULED,
                "reason": "Can switch between pre-recorded tracks"
            }

        # Unknown transition
        return {
            "is_valid": False,
            "transition": None,
            "reason": f"Unknown transition from {from_type} to {to_type}"
        }
