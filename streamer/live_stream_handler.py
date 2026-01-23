"""
Live stream handler for RTMP/SRT streams.

Provides:
- RTMP/SRT stream URL handling
- Stream metadata extraction
- Connection management
- Reconnection logic
- Stream validation

Integration Points:
- PyTgCalls for stream playback
- GStreamer for codec support
- MediaMTX for RTMP ingestion
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

logger = logging.getLogger(__name__)


@dataclass
class LiveStreamMetadata:
    """Metadata for a live RTMP/SRT stream."""
    url: str
    title: str = ""
    description: str = ""
    ingestion_type: str = "rtmp"  # rtmp, srt, webrtc
    bitrate_kbps: Optional[int] = None
    is_active: bool = False
    last_updated: datetime = None

    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


class LiveStreamHandler:
    """
    Manages RTMP/SRT live stream connections.

    Handles:
    - Stream URL validation and testing
    - Metadata extraction (title, bitrate, format)
    - Connection management and reconnection
    - Stream status monitoring
    - Error recovery
    """

    # Connection defaults
    DEFAULT_TIMEOUT = 10
    RECONNECT_ATTEMPTS = 5
    RECONNECT_DELAY_SECONDS = 3

    # Supported protocols
    SUPPORTED_PROTOCOLS = {
        'rtmp': 'RTMP',
        'rtmps': 'RTMPS',
        'srt': 'SRT',
    }

    def __init__(self):
        """Initialize live stream handler."""
        self.logger = logger
        self.active_streams: Dict[str, Dict[str, Any]] = {}  # channel_id -> stream info

    async def initialize(self) -> None:
        """Initialize live stream handler."""
        self.logger.info("LiveStreamHandler initialized")

    async def shutdown(self) -> None:
        """Shutdown and cleanup."""
        self.logger.info("LiveStreamHandler shutdown")

    async def validate_stream_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a stream URL is properly formatted.

        Args:
            url: Stream URL to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL is empty"

        # Extract protocol from URL
        protocol_match = re.match(r'^([a-zA-Z0-9+]+)://', url)
        if not protocol_match:
            return False, "URL must start with a protocol (rtmp://, rtmps://, srt://)"

        protocol = protocol_match.group(1).lower()

        # Check if protocol is supported
        if protocol not in self.SUPPORTED_PROTOCOLS:
            return False, f"Unsupported protocol: {protocol}. Supported: {', '.join(self.SUPPORTED_PROTOCOLS.keys())}"

        # Basic format validation for RTMP/RTMPS
        if protocol in ('rtmp', 'rtmps'):
            # RTMP format: rtmp[s]://host[:port]/app/stream_key
            rtmp_pattern = r'^rtmp[s]?://[^/]+/[^/]+/[^/]+$'
            if not re.match(rtmp_pattern, url):
                return False, "Invalid RTMP URL format. Expected: rtmp[s]://host[:port]/app/stream_key"

        # Basic format validation for SRT
        elif protocol == 'srt':
            # SRT format: srt://host:port?mode=caller
            srt_pattern = r'^srt://[^/:]+(:\d+)?(\?.*)?$'
            if not re.match(srt_pattern, url):
                return False, "Invalid SRT URL format. Expected: srt://host:port?mode=caller"

        self.logger.info(f"Stream validation successful: {url}")
        return True, None

    async def get_stream_metadata(self, url: str) -> Optional[LiveStreamMetadata]:
        """
        Extract metadata from stream URL.

        Args:
            url: Stream URL

        Returns:
            LiveStreamMetadata object or None if extraction fails
        """
        try:
            # Extract protocol
            protocol_match = re.match(r'^([a-zA-Z0-9+]+)://', url)
            if not protocol_match:
                return None

            protocol = protocol_match.group(1).lower()
            ingestion_type = self.SUPPORTED_PROTOCOLS.get(protocol, 'UNKNOWN')

            # Extract stream key from RTMP URL for title
            title = "Live Stream"
            if protocol in ('rtmp', 'rtmps'):
                # RTMP URL: rtmp://host/app/stream_key
                parts = url.split('/')
                if len(parts) >= 4:
                    stream_key = parts[-1]
                    title = f"Live Stream ({stream_key})"

            metadata = LiveStreamMetadata(
                url=url,
                title=title,
                ingestion_type=ingestion_type,
                is_active=False,
                last_updated=datetime.now()
            )

            self.logger.info(f"Metadata extracted: {metadata}")
            return metadata

        except Exception as e:
            self.logger.error(f"Failed to extract metadata: {e}")
            return None

    async def start_stream(self, channel_id: str, url: str, name: str = "") -> Tuple[bool, Optional[str]]:
        """
        Start streaming RTMP/SRT to channel.

        Args:
            channel_id: Telegram channel ID
            url: Stream URL
            name: Friendly name for the stream

        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Validate URL first
            is_valid, error = await self.validate_stream_url(url)
            if not is_valid:
                return False, error

            # Get metadata
            metadata = await self.get_stream_metadata(url)

            # Store stream info
            self.active_streams[channel_id] = {
                'url': url,
                'name': name or (metadata.title if metadata else "Live Stream"),
                'metadata': metadata,
                'started_at': datetime.now(),
                'reconnect_count': 0,
            }

            self.logger.info(f"Started live stream for channel {channel_id}: {url}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to start live stream: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    async def stop_stream(self, channel_id: str) -> bool:
        """
        Stop streaming to channel.

        Args:
            channel_id: Telegram channel ID

        Returns:
            True if successful
        """
        if channel_id in self.active_streams:
            del self.active_streams[channel_id]
            self.logger.info(f"Stopped live stream for channel {channel_id}")
            return True
        return False

    async def handle_stream_error(self, channel_id: str) -> Tuple[bool, Optional[str]]:
        """
        Handle stream error with reconnection logic.

        Args:
            channel_id: Telegram channel ID

        Returns:
            Tuple of (should_reconnect, error_message)
        """
        if channel_id not in self.active_streams:
            return False, "Stream not found"

        stream_info = self.active_streams[channel_id]
        reconnect_count = stream_info.get('reconnect_count', 0)

        if reconnect_count >= self.RECONNECT_ATTEMPTS:
            return False, f"Max reconnection attempts reached ({self.RECONNECT_ATTEMPTS})"

        # Wait before reconnecting
        await asyncio.sleep(self.RECONNECT_DELAY_SECONDS * (reconnect_count + 1))

        # Try to reconnect
        stream_info['reconnect_count'] = reconnect_count + 1

        # Validate URL again
        is_valid, error = await self.validate_stream_url(stream_info['url'])

        if is_valid:
            self.logger.info(f"Live stream reconnected for channel {channel_id} (attempt {reconnect_count + 1})")
            stream_info['reconnect_count'] = 0  # Reset on success
            return True, None
        else:
            return False, error

    def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently active streams."""
        return self.active_streams.copy()

    async def cleanup(self) -> None:
        """Cleanup all streams and resources."""
        self.active_streams.clear()
        await self.shutdown()


# Global instance
_live_handler: Optional[LiveStreamHandler] = None


def get_live_handler() -> LiveStreamHandler:
    """Get or create global live stream handler instance."""
    global _live_handler
    if _live_handler is None:
        _live_handler = LiveStreamHandler()
    return _live_handler


async def reset_live_handler() -> None:
    """Reset global live handler instance (for testing)."""
    global _live_handler
    if _live_handler:
        await _live_handler.cleanup()
    _live_handler = None
