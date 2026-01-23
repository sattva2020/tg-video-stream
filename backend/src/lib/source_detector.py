"""
Source detection utilities for the Telegram broadcast platform.

This module provides automatic detection of video source types from URLs,
supporting multiple platforms including YouTube, Vimeo, Twitch, Dailymotion,
direct video URLs, HLS/DASH streams, cloud storage, and RSS feeds.
"""

from typing import Optional, Dict, Any
from enum import Enum

from src.lib.validators import URLValidator


class SourceType(str, Enum):
    """Enumeration of supported video source types."""

    YOUTUBE = "youtube"
    VIMEO = "vimeo"
    DAILYMOTION = "dailymotion"
    TWITCH = "twitch"
    DIRECT = "direct"
    HLS = "hls"
    DASH = "dash"
    GOOGLE_DRIVE = "cloud_drive"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"
    RSS_FEED = "rss"
    UNKNOWN = "unknown"


class SourceDetector:
    """
    Automatic video source type detection from URLs.

    This class provides methods to detect the type of video source
    from a given URL and extract relevant metadata such as video IDs,
    file IDs, and other platform-specific information.
    """

    # Direct video file extensions
    DIRECT_VIDEO_EXTENSIONS = {
        '.mp4', '.webm', '.mkv', '.avi', '.mov', '.wmv', '.flv',
        '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts'
    }

    # DASH streaming extension
    DASH_EXTENSION = '.mpd'

    @staticmethod
    def detect_source(url: str) -> Dict[str, Any]:
        """
        Automatically detect the source type from a URL.

        Args:
            url: URL string to detect source type from

        Returns:
            dict: Detection result with keys:
                - valid (bool): Whether URL format is valid
                - source_type (SourceType): Detected source type
                - metadata (dict): Extracted metadata (IDs, etc.)
                - error (str, optional): Error message if detection failed
        """
        if not url or not isinstance(url, str):
            return {
                "valid": False,
                "source_type": SourceType.UNKNOWN,
                "metadata": {},
                "error": "URL cannot be empty"
            }

        url = url.strip()

        # Try each source type in order of specificity
        # (most specific patterns first to avoid false positives)

        # 1. YouTube
        result = SourceDetector._detect_youtube(url)
        if result["valid"]:
            return result

        # 2. Vimeo
        result = SourceDetector._detect_vimeo(url)
        if result["valid"]:
            return result

        # 3. Twitch
        result = SourceDetector._detect_twitch(url)
        if result["valid"]:
            return result

        # 4. Dailymotion
        result = SourceDetector._detect_dailymotion(url)
        if result["valid"]:
            return result

        # 5. Google Drive
        result = SourceDetector._detect_google_drive(url)
        if result["valid"]:
            return result

        # 6. Dropbox
        result = SourceDetector._detect_dropbox(url)
        if result["valid"]:
            return result

        # 7. OneDrive
        result = SourceDetector._detect_onedrive(url)
        if result["valid"]:
            return result

        # 8. RSS Feed
        result = SourceDetector._detect_rss_feed(url)
        if result["valid"]:
            return result

        # 9. HLS Stream
        result = SourceDetector._detect_hls(url)
        if result["valid"]:
            return result

        # 10. DASH Stream
        result = SourceDetector._detect_dash(url)
        if result["valid"]:
            return result

        # 11. Direct video URL
        result = SourceDetector._detect_direct_video(url)
        if result["valid"]:
            return result

        # If no pattern matched, return unknown
        return {
            "valid": False,
            "source_type": SourceType.UNKNOWN,
            "metadata": {},
            "error": "Unable to detect source type from URL"
        }

    @staticmethod
    def _detect_youtube(url: str) -> Dict[str, Any]:
        """
        Detect YouTube URL and extract video ID.

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        result = URLValidator.validate_youtube_url(url)
        if result["valid"]:
            return {
                "valid": True,
                "source_type": SourceType.YOUTUBE,
                "metadata": {
                    "video_id": result["video_id"]
                }
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_vimeo(url: str) -> Dict[str, Any]:
        """
        Detect Vimeo URL and extract video ID.

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        result = URLValidator.validate_vimeo_url(url)
        if result["valid"]:
            return {
                "valid": True,
                "source_type": SourceType.VIMEO,
                "metadata": {
                    "video_id": result["video_id"]
                }
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_twitch(url: str) -> Dict[str, Any]:
        """
        Detect Twitch URL and extract channel/video ID.

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        result = URLValidator.validate_twitch_url(url)
        if result["valid"]:
            metadata = {
                "channel_id": result["channel_id"]
            }
            # Try to determine if it's a VOD or channel
            if "/videos/" in url.lower():
                metadata["content_type"] = "vod"
            else:
                metadata["content_type"] = "channel"

            return {
                "valid": True,
                "source_type": SourceType.TWITCH,
                "metadata": metadata
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_dailymotion(url: str) -> Dict[str, Any]:
        """
        Detect Dailymotion URL and extract video ID.

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        result = URLValidator.validate_dailymotion_url(url)
        if result["valid"]:
            return {
                "valid": True,
                "source_type": SourceType.DAILYMOTION,
                "metadata": {
                    "video_id": result["video_id"]
                }
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_hls(url: str) -> Dict[str, Any]:
        """
        Detect HLS streaming URL (.m3u8 format).

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        result = URLValidator.validate_hls_url(url)
        if result["valid"]:
            return {
                "valid": True,
                "source_type": SourceType.HLS,
                "metadata": {
                    "url": result["url"],
                    "is_live": True
                }
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_dash(url: str) -> Dict[str, Any]:
        """
        Detect DASH streaming URL (.mpd format).

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        if not url or not isinstance(url, str):
            return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

        url_lower = url.lower()
        if url_lower.endswith(SourceDetector.DASH_EXTENSION):
            return {
                "valid": True,
                "source_type": SourceType.DASH,
                "metadata": {
                    "url": url,
                    "is_live": True
                }
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_google_drive(url: str) -> Dict[str, Any]:
        """
        Detect Google Drive URL and extract file ID.

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        result = URLValidator.validate_google_drive_url(url)
        if result["valid"]:
            return {
                "valid": True,
                "source_type": SourceType.GOOGLE_DRIVE,
                "metadata": {
                    "file_id": result["file_id"],
                    "requires_auth": True
                }
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_dropbox(url: str) -> Dict[str, Any]:
        """
        Detect Dropbox URL and extract file ID.

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        result = URLValidator.validate_dropbox_url(url)
        if result["valid"]:
            return {
                "valid": True,
                "source_type": SourceType.DROPBOX,
                "metadata": {
                    "file_id": result["file_id"],
                    "requires_auth": True
                }
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_onedrive(url: str) -> Dict[str, Any]:
        """
        Detect OneDrive URL.

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        result = URLValidator.validate_onedrive_url(url)
        if result["valid"]:
            return {
                "valid": True,
                "source_type": SourceType.ONEDRIVE,
                "metadata": {
                    "url": result["url"],
                    "requires_auth": True
                }
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_rss_feed(url: str) -> Dict[str, Any]:
        """
        Detect RSS/Atom feed URL.

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        result = URLValidator.validate_rss_feed_url(url)
        if result["valid"]:
            return {
                "valid": True,
                "source_type": SourceType.RSS_FEED,
                "metadata": {
                    "url": result["url"]
                }
            }
        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def _detect_direct_video(url: str) -> Dict[str, Any]:
        """
        Detect direct video file URL.

        Args:
            url: URL to check

        Returns:
            dict: Detection result with source_type and metadata
        """
        if not url or not isinstance(url, str):
            return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

        # First validate it's a proper URL
        url_validation = URLValidator.validate_url(url)
        if not url_validation["valid"]:
            return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

        # Check if URL ends with a video file extension
        url_lower = url.lower().split('?')[0]  # Remove query string for extension check
        _, ext = url_lower.rsplit('.', 1) if '.' in url_lower.rsplit('/', 1)[-1] else (None, None)

        if ext and f".{ext}" in SourceDetector.DIRECT_VIDEO_EXTENSIONS:
            return {
                "valid": True,
                "source_type": SourceType.DIRECT,
                "metadata": {
                    "url": url,
                    "extension": f".{ext}"
                }
            }

        return {"valid": False, "source_type": SourceType.UNKNOWN, "metadata": {}}

    @staticmethod
    def get_supported_sources() -> list[str]:
        """
        Get list of supported source types.

        Returns:
            list[str]: List of supported source type strings
        """
        return [source.value for source in SourceType if source != SourceType.UNKNOWN]

    @staticmethod
    def is_supported(source_type: str) -> bool:
        """
        Check if a source type is supported.

        Args:
            source_type: Source type string to check

        Returns:
            bool: True if source type is supported
        """
        try:
            return SourceType(source_type) != SourceType.UNKNOWN
        except ValueError:
            return False

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL by stripping whitespace and ensuring consistent format.

        Args:
            url: URL to normalize

        Returns:
            str: Normalized URL
        """
        if not url or not isinstance(url, str):
            return ""

        url = url.strip()

        # Ensure https for YouTube URLs (they prefer https)
        if url.startswith('http://www.youtube.com') or url.startswith('http://youtube.com'):
            url = url.replace('http://', 'https://', 1)

        # Ensure https for Vimeo
        if url.startswith('http://vimeo.com') or url.startswith('http://www.vimeo.com'):
            url = url.replace('http://', 'https://', 1)

        return url
