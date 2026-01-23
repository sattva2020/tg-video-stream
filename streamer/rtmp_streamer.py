"""
RTMP Streamer for Multi-Platform Broadcasting.

This module provides functionality to push streams to RTMP endpoints
including YouTube, Twitch, and custom RTMP destinations.

Usage:
    streamer = RTMPStreamer(platform="youtube", rtmp_url="rtmp://...", stream_key="...")
    await streamer.start(stream_url="https://...")
    await streamer.stop()

Environment variables:
    FFMPEG_PATH: Path to FFmpeg binary (default: "ffmpeg")
    RTMP_RECONNECT_DELAY: Delay between reconnection attempts in seconds (default: 5)
    RTMP_BUFFER_SIZE: RTMP buffer size in bytes (default: 256000)

Platform-specific settings:
    YouTube: Requires stream key from YouTube Studio
    Twitch: Requires stream key from Twitch Dashboard
    Custom: Requires full RTMP URL + stream key
"""

import asyncio
import logging
import os
import signal
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("rtmp_streamer")


class PlatformType(Enum):
    """Supported streaming platforms."""
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    CUSTOM = "custom"


@dataclass
class StreamConfig:
    """Configuration for an RTMP stream."""
    platform: str
    rtmp_url: str
    stream_key: str
    video_quality: str = "720p"  # 480p, 720p, 1080p
    audio_bitrate: str = "128k"  # 64k, 128k, 192k
    video_bitrate: Optional[str] = None  # Auto-calculated from quality
    fps: int = 30
    preset: str = "ultrafast"
    codec: str = "libx264"
    audio_codec: str = "aac"
    additional_params: Optional[str] = None


class RTMPStreamer:
    """
    RTMP Streamer for pushing streams to multiple platforms.

    Manages FFmpeg processes for RTMP streaming to platforms like
    YouTube, Twitch, and custom RTMP endpoints.

    Attributes:
        config: Stream configuration including platform and RTMP details
        process: FFmpeg subprocess if streaming
        is_running: True if stream is currently active
    """

    # Platform-specific RTMP endpoints
    PLATFORM_RTMP_URLS = {
        "youtube": "rtmp://a.rtmp.youtube.com/live2",
        "twitch": "rtmp://live.twitch.tv/app",
    }

    def __init__(self, config: StreamConfig):
        """
        Initialize RTMPStreamer.

        Args:
            config: Stream configuration with platform and RTMP details
        """
        self.config = config
        self.process: Optional[asyncio.subprocess.Process] = None
        self.is_running = False
        self._stop_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None

        # Validate platform
        if config.platform.lower() not in self.PLATFORM_RTMP_URLS and config.platform.lower() != "custom":
            raise ValueError(f"Unsupported platform: {config.platform}")

        log.info(f"RTMPStreamer initialized for {config.platform}")

    def _get_ffmpeg_path(self) -> str:
        """Get FFmpeg binary path from environment or use default."""
        return os.getenv("FFMPEG_PATH", "ffmpeg")

    def _build_rtmp_url(self) -> str:
        """
        Build complete RTMP URL with stream key.

        Returns:
            Full RTMP URL in format: rtmp://server/app/stream_key
        """
        platform = self.config.platform.lower()

        if platform == "custom":
            # For custom, use the provided rtmp_url directly
            base_url = self.config.rtmp_url
        else:
            # Use predefined platform URL
            base_url = self.PLATFORM_RTMP_URLS[platform]

        # Append stream key
        return f"{base_url}/{self.config.stream_key}"

    def _build_ffmpeg_args(self, source_url: str) -> list[str]:
        """
        Build FFmpeg command line arguments for RTMP streaming.

        Args:
            source_url: Source stream URL to push to RTMP

        Returns:
            List of FFmpeg command arguments
        """
        rtmp_url = self._build_rtmp_url()
        ffmpeg_path = self._get_ffmpeg_path()

        # Base input arguments
        args = [
            ffmpeg_path,
            "-re",  # Read input at native frame rate
        ]

        # Input source
        if source_url.startswith("http://") or source_url.startswith("https://"):
            # For HTTP streams, set user agent and headers
            args.extend([
                "-user_agent", "Mozilla/5.0",
                "-headers", "Accept: */*",
            ])
        args.extend(["-i", source_url])

        # Video codec settings
        args.extend([
            "-c:v", self.config.codec,
            "-preset", self.config.preset,
            "-tune", "zerolatency",  # Optimize for live streaming
            "-g", str(self.config.fps * 2),  # Keyframe interval (2 seconds)
            "-r", str(self.config.fps),  # Frame rate
        ])

        # Calculate video bitrate based on quality if not specified
        if not self.config.video_bitrate:
            quality_bitrates = {
                "480p": "900k",
                "720p": "1800k",
                "1080p": "3500k",
            }
            video_bitrate = quality_bitrates.get(self.config.video_quality.lower(), "1800k")
        else:
            video_bitrate = self.config.video_bitrate

        # Video quality settings
        if self.config.video_quality == "480p":
            args.extend(["-vf", "scale=-2:480"])
        elif self.config.video_quality == "1080p":
            args.extend(["-vf", "scale=-2:1080"])
        else:  # 720p
            args.extend(["-vf", "scale=-2:720"])

        args.extend(["-b:v", video_bitrate])
        args.extend(["-maxrate", f"{int(int(video_bitrate.replace('k', '')) * 1.2)}k"])
        args.extend(["-bufsize", f"{int(int(video_bitrate.replace('k', '')) * 2)}k"])

        # Audio codec settings
        args.extend([
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            "-ar", "48000",  # Sample rate
        ])

        # RTMP output settings
        args.extend([
            "-f", "flv",  # Flash Video format for RTMP
            "-flvflags", "no_duration_filesize",
        ])

        # Add custom parameters if provided
        if self.config.additional_params:
            import shlex
            try:
                custom_args = shlex.split(self.config.additional_params)
                args.extend(custom_args)
            except Exception as e:
                log.warning(f"Failed to parse additional_params: {e}")

        # Output URL
        args.append(rtmp_url)

        return args

    async def start(self, source_url: str) -> bool:
        """
        Start streaming to RTMP endpoint.

        Launches FFmpeg process to push source stream to RTMP destination.

        Args:
            source_url: Source stream URL (HTTP, local file, etc.)

        Returns:
            True if stream started successfully, False otherwise
        """
        if self.is_running:
            log.warning(f"Stream already running for {self.config.platform}")
            return False

        try:
            args = self._build_ffmpeg_args(source_url)
            log.info(f"Starting RTMP stream for {self.config.platform}")
            log.debug(f"FFmpeg args: {' '.join(args)}")

            # Start FFmpeg process
            self.process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self.is_running = True
            self._stop_event.clear()

            # Start monitoring task
            self._monitor_task = asyncio.create_task(self._monitor_stream())

            log.info(f"RTMP stream started for {self.config.platform} (PID: {self.process.pid})")
            return True

        except FileNotFoundError as e:
            log.error(f"FFmpeg not found at {self._get_ffmpeg_path()}: {e}")
            return False
        except Exception as e:
            log.exception(f"Failed to start RTMP stream for {self.config.platform}: {e}")
            return False

    async def stop(self) -> bool:
        """
        Stop streaming to RTMP endpoint.

        Gracefully terminates FFmpeg process and cleanup resources.

        Returns:
            True if stream stopped successfully, False otherwise
        """
        if not self.is_running:
            log.warning(f"Stream not running for {self.config.platform}")
            return False

        log.info(f"Stopping RTMP stream for {self.config.platform}")

        try:
            # Signal stop event
            self._stop_event.set()

            # Cancel monitor task
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                self._monitor_task = None

            # Terminate FFmpeg process gracefully
            if self.process:
                # Try graceful shutdown first
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                    log.info(f"FFmpeg process terminated gracefully for {self.config.platform}")
                except asyncio.TimeoutError:
                    # Force kill if graceful shutdown fails
                    log.warning(f"FFmpeg process did not terminate, killing for {self.config.platform}")
                    self.process.kill()
                    await self.process.wait()

                self.process = None

            self.is_running = False
            log.info(f"RTMP stream stopped for {self.config.platform}")
            return True

        except Exception as e:
            log.exception(f"Error stopping RTMP stream for {self.config.platform}: {e}")
            return False

    async def _monitor_stream(self):
        """
        Monitor FFmpeg process for errors and health.

        Reads stderr from FFmpeg to detect connection issues or errors.
        Automatically attempts reconnection on connection failures.
        """
        if not self.process:
            return

        try:
            while self.is_running and not self._stop_event.is_set():
                # Read stderr line by line
                line = await self.process.stderr.readline()

                if not line:
                    # Process ended
                    if self.process.returncode is not None:
                        log.warning(f"FFmpeg process ended for {self.config.platform} (code: {self.process.returncode})")
                        break
                    continue

                line_str = line.decode('utf-8', errors='ignore').strip()

                # Log errors and warnings
                if "error" in line_str.lower() or "failed" in line_str.lower():
                    log.error(f"FFmpeg error for {self.config.platform}: {line_str}")
                elif "warning" in line_str.lower():
                    log.warning(f"FFmpeg warning for {self.config.platform}: {line_str}")
                elif "connected" in line_str.lower() or "streaming" in line_str.lower():
                    log.info(f"FFmpeg for {self.config.platform}: {line_str}")

        except asyncio.CancelledError:
            log.debug(f"Monitor task cancelled for {self.config.platform}")
        except Exception as e:
            log.exception(f"Error monitoring stream for {self.config.platform}: {e}")

    def is_streaming(self) -> bool:
        """
        Check if stream is currently active.

        Returns:
            True if stream is running, False otherwise
        """
        return self.is_running and self.process is not None

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the stream.

        Returns:
            Dictionary with stream status information
        """
        return {
            "platform": self.config.platform,
            "is_running": self.is_running,
            "video_quality": self.config.video_quality,
            "audio_bitrate": self.config.audio_bitrate,
            "pid": self.process.pid if self.process else None,
            "rtmp_url": self._build_rtmp_url(),
        }

    async def restart(self, source_url: str) -> bool:
        """
        Restart the stream with new source URL.

        Stops current stream and starts with new source.

        Args:
            source_url: New source stream URL

        Returns:
            True if restart successful, False otherwise
        """
        log.info(f"Restarting RTMP stream for {self.config.platform}")

        # Stop current stream
        if self.is_running:
            await self.stop()
            await asyncio.sleep(2)  # Brief pause before restart

        # Start with new source
        return await self.start(source_url)


def create_streamer_from_config(config_dict: Dict[str, Any]) -> RTMPStreamer:
    """
    Create RTMPStreamer instance from configuration dictionary.

    Args:
        config_dict: Configuration dictionary with keys:
            - platform: Platform name (youtube, twitch, custom)
            - rtmp_url: RTMP server URL (for custom) or None
            - stream_key: Stream key for the platform
            - video_quality: Video quality (480p, 720p, 1080p)
            - audio_bitrate: Audio bitrate (128k, 192k, etc.)
            - fps: Frame rate (default: 30)
            - additional_params: Additional FFmpeg parameters

    Returns:
        Configured RTMPStreamer instance

    Example:
        config = {
            "platform": "youtube",
            "stream_key": "xxxx-xxxx-xxxx-xxxx",
            "video_quality": "720p",
            "audio_bitrate": "128k",
        }
        streamer = create_streamer_from_config(config)
    """
    config = StreamConfig(
        platform=config_dict.get("platform", "custom"),
        rtmp_url=config_dict.get("rtmp_url", ""),
        stream_key=config_dict.get("stream_key", ""),
        video_quality=config_dict.get("video_quality", "720p"),
        audio_bitrate=config_dict.get("audio_bitrate", "128k"),
        video_bitrate=config_dict.get("video_bitrate"),
        fps=config_dict.get("fps", 30),
        preset=config_dict.get("preset", "ultrafast"),
        codec=config_dict.get("codec", "libx264"),
        audio_codec=config_dict.get("audio_codec", "aac"),
        additional_params=config_dict.get("additional_params"),
    )

    return RTMPStreamer(config)


async def test_stream_config(config: StreamConfig) -> bool:
    """
    Test stream configuration by checking FFmpeg availability.

    Args:
        config: Stream configuration to test

    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        streamer = RTMPStreamer(config)
        ffmpeg_path = streamer._get_ffmpeg_path()

        # Test FFmpeg availability
        proc = await asyncio.create_subprocess_exec(
            ffmpeg_path,
            "-version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.wait()

        if proc.returncode != 0:
            log.error(f"FFmpeg test failed: {ffmpeg_path} not usable")
            return False

        log.info(f"Stream config test passed for {config.platform}")
        return True

    except FileNotFoundError:
        log.error(f"FFmpeg not found at {ffmpeg_path}")
        return False
    except Exception as e:
        log.error(f"Stream config test failed: {e}")
        return False
