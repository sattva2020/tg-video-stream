"""
Radio stream handler for HTTP/HTTPS audio streams.

Provides:
- HTTP/HTTPS stream URL handling
- Stream metadata extraction
- Connection management
- Reconnection logic
- Stream validation

Integration Points:
- PyTgCalls for stream playback
- GStreamer for codec support
- HTTP client for stream fetching
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class StreamMetadata:
    """Metadata for an HTTP stream."""
    url: str
    title: str = ""
    description: str = ""
    duration_seconds: Optional[int] = None
    bitrate_kbps: Optional[int] = None
    format: str = "unknown"
    is_live: bool = False
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


class RadioStreamHandler:
    """
    Manages HTTP/HTTPS radio stream connections.
    
    Handles:
    - Stream URL validation and testing
    - Metadata extraction (title, bitrate, format)
    - Connection management and reconnection
    - Stream status monitoring
    - Error recovery
    """
    
    # Connection defaults
    DEFAULT_TIMEOUT = 10
    DEFAULT_CHUNK_SIZE = 8192
    RECONNECT_ATTEMPTS = 3
    RECONNECT_DELAY_SECONDS = 5
    
    # Supported audio formats
    SUPPORTED_FORMATS = {
        'audio/mpeg': 'MP3',
        'audio/mp4': 'M4A',
        'audio/aac': 'AAC',
        'audio/ogg': 'OGG',
        'audio/opus': 'OPUS',
        'audio/flac': 'FLAC',
        'audio/wav': 'WAV',
        'audio/webm': 'WEBM',
        'application/vnd.apple.mpegurl': 'HLS',
        'application/x-mpegURL': 'HLS',
    }
    
    def __init__(self):
        """Initialize radio stream handler."""
        self.logger = logger
        self.active_streams: Dict[str, Dict[str, Any]] = {}  # channel_id -> stream info
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize aiohttp session."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self.logger.info("RadioStreamHandler initialized")
    
    async def shutdown(self) -> None:
        """Close aiohttp session and cleanup."""
        if self.session:
            await self.session.close()
            self.session = None
        self.logger.info("RadioStreamHandler shutdown")
    
    async def validate_stream_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a stream URL is accessible and is audio.
        
        Args:
            url: Stream URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL is empty"
        
        # Basic URL format validation
        if not (url.startswith('http://') or url.startswith('https://')):
            return False, "URL must start with http:// or https://"
        
        # Try to connect and check headers
        try:
            await self.initialize()
            
            async with self.session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)) as resp:
                if resp.status != 200:
                    return False, f"Server returned status {resp.status}"
                
                content_type = resp.headers.get('Content-Type', '').lower()
                
                # Check if it's audio
                if not (content_type.startswith('audio/') or 'mpegurl' in content_type or 'playlist' in content_type):
                    self.logger.warning(f"Stream content-type: {content_type}")
                    # Don't fail - some streams have incorrect content-type headers
                
                # Check content length if available
                content_length = resp.headers.get('Content-Length')
                if content_length:
                    try:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > 10000:  # Sanity check: files > 10GB
                            return False, f"Stream file too large ({size_mb:.1f}MB)"
                    except (ValueError, TypeError):
                        pass
                
                self.logger.info(f"Stream validation successful: {url} ({content_type})")
                return True, None
        
        except asyncio.TimeoutError:
            return False, "Connection timeout"
        except aiohttp.ClientError as e:
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            return False, f"Validation failed: {str(e)}"
    
    async def get_stream_metadata(self, url: str) -> Optional[StreamMetadata]:
        """
        Extract metadata from stream URL.
        
        Args:
            url: Stream URL
            
        Returns:
            StreamMetadata object or None if extraction fails
        """
        try:
            await self.initialize()
            
            async with self.session.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=self.DEFAULT_TIMEOUT)) as resp:
                if resp.status != 200:
                    return None
                
                # Extract metadata from headers
                content_type = resp.headers.get('Content-Type', 'unknown').lower()
                format_name = self._get_format_name(content_type)
                
                # Get bitrate if available
                bitrate_kbps = None
                try:
                    if 'icecast' in resp.headers or 'bitrate' in content_type:
                        # Try to extract from ICEcast headers
                        bitrate_str = resp.headers.get('ice-bitrate') or resp.headers.get('bitrate')
                        if bitrate_str:
                            bitrate_kbps = int(bitrate_str) // 1000
                except (ValueError, TypeError):
                    pass
                
                # Check if it's a live stream
                is_live = 'icecast' in str(resp.headers).lower() or 'live' in url.lower()
                
                # Extract title if available (from ICEcast or other headers)
                title = ""
                for header in ['Ice-Name', 'icy-name', 'Title', 'title']:
                    if header in resp.headers:
                        title = resp.headers[header]
                        break
                
                metadata = StreamMetadata(
                    url=url,
                    title=title or "Radio Stream",
                    format=format_name,
                    bitrate_kbps=bitrate_kbps,
                    is_live=is_live,
                    last_updated=datetime.now()
                )
                
                self.logger.info(f"Metadata extracted: {metadata}")
                return metadata
        
        except Exception as e:
            self.logger.error(f"Failed to extract metadata: {e}")
            return None
    
    def _get_format_name(self, content_type: str) -> str:
        """Get friendly format name from content-type."""
        content_type = content_type.split(';')[0].strip()
        return self.SUPPORTED_FORMATS.get(content_type, 'Unknown')
    
    async def start_stream(self, channel_id: str, url: str, name: str = "") -> Tuple[bool, Optional[str]]:
        """
        Start streaming HTTP radio to channel.
        
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
                'name': name or (metadata.title if metadata else "Radio Stream"),
                'metadata': metadata,
                'started_at': datetime.now(),
                'reconnect_count': 0,
            }
            
            self.logger.info(f"Started stream for channel {channel_id}: {url}")
            return True, None
        
        except Exception as e:
            error_msg = f"Failed to start stream: {str(e)}"
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
            self.logger.info(f"Stopped stream for channel {channel_id}")
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
            self.logger.info(f"Stream reconnected for channel {channel_id} (attempt {reconnect_count + 1})")
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
_radio_handler: Optional[RadioStreamHandler] = None


def get_radio_handler() -> RadioStreamHandler:
    """Get or create global radio stream handler instance."""
    global _radio_handler
    if _radio_handler is None:
        _radio_handler = RadioStreamHandler()
    return _radio_handler


async def reset_radio_handler() -> None:
    """Reset global radio handler instance (for testing)."""
    global _radio_handler
    if _radio_handler:
        await _radio_handler.cleanup()
    _radio_handler = None
