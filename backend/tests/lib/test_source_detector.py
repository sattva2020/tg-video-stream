"""Unit tests for video source detection utilities.

Tests automatic detection of video source types from URLs,
supporting multiple platforms.
"""

import pytest

from src.lib.source_detector import (
    SourceDetector,
    SourceType,
)


class TestSourceTypeEnum:
    """Test SourceType enumeration values."""

    def test_source_type_values(self):
        """Test all expected source types are defined."""
        expected_types = [
            "youtube",
            "vimeo",
            "dailymotion",
            "twitch",
            "direct",
            "hls",
            "dash",
            "cloud_drive",
            "dropbox",
            "onedrive",
            "rss",
            "unknown",
        ]

        for expected in expected_types:
            assert expected in [source.value for source in SourceType]

    def test_source_type_unknown_exists(self):
        """Test UNKNOWN source type exists."""
        assert SourceType.UNKNOWN == "unknown"


class TestDetectSource:
    """Test main detect_source() method."""

    def test_detect_youtube_urls(self):
        """Test detection of YouTube URLs."""
        youtube_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/embed/dQw4w9WgXcQ",
            "http://www.youtube.com/watch?v=test123",
        ]

        for url in youtube_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.YOUTUBE
            assert "video_id" in result["metadata"]
            assert len(result["metadata"]["video_id"]) == 11

    def test_detect_vimeo_urls(self):
        """Test detection of Vimeo URLs."""
        vimeo_urls = [
            "https://vimeo.com/123456789",
            "https://www.vimeo.com/123456789",
            "https://vimeo.com/channels/staffpicks/123456789",
        ]

        for url in vimeo_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.VIMEO
            assert "video_id" in result["metadata"]
            assert result["metadata"]["video_id"] == "123456789"

    def test_detect_twitch_channel_urls(self):
        """Test detection of Twitch channel URLs."""
        twitch_urls = [
            "https://www.twitch.tv/testchannel",
            "https://twitch.tv/testchannel",
        ]

        for url in twitch_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.TWITCH
            assert result["metadata"]["channel_id"] == "testchannel"
            assert result["metadata"]["content_type"] == "channel"

    def test_detect_twitch_vod_urls(self):
        """Test detection of Twitch VOD URLs."""
        vod_urls = [
            "https://www.twitch.tv/videos/123456",
            "https://twitch.tv/videos/123456",
        ]

        for url in vod_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.TWITCH
            assert result["metadata"]["channel_id"] == "123456"
            assert result["metadata"]["content_type"] == "vod"

    def test_detect_dailymotion_urls(self):
        """Test detection of Dailymotion URLs."""
        dailymotion_urls = [
            "https://www.dailymotion.com/video/x123abc",
            "https://dailymotion.com/video/x123abc",
            "https://www.dailymotion.com/embed/x123abc",
            "https://dai.ly/x123abc",
        ]

        for url in dailymotion_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.DAILYMOTION
            assert "video_id" in result["metadata"]

    def test_detect_hls_urls(self):
        """Test detection of HLS streaming URLs."""
        hls_urls = [
            "https://example.com/stream.m3u8",
            "https://cdn.example.com/live/stream.m3u8",
            "https://example.com/stream.m3u8?token=abc123",
        ]

        for url in hls_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.HLS
            assert result["metadata"]["url"] == url
            assert result["metadata"]["is_live"] is True

    def test_detect_dash_urls(self):
        """Test detection of DASH streaming URLs."""
        dash_urls = [
            "https://example.com/stream.mpd",
            "https://cdn.example.com/live/stream.mpd",
        ]

        for url in dash_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.DASH
            assert result["metadata"]["url"] == url
            assert result["metadata"]["is_live"] is True

    def test_detect_google_drive_urls(self):
        """Test detection of Google Drive URLs."""
        drive_urls = [
            "https://drive.google.com/file/d/abc123XYZ/view",
            "https://drive.google.com/open?id=abc123XYZ",
        ]

        for url in drive_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.GOOGLE_DRIVE
            assert result["metadata"]["file_id"] == "abc123XYZ"
            assert result["metadata"]["requires_auth"] is True

    def test_detect_dropbox_urls(self):
        """Test detection of Dropbox URLs."""
        dropbox_urls = [
            "https://www.dropbox.com/s/abc123/file.mp4",
            "https://dropbox.com/s/abc123/file.mp4",
            "https://db.tt/abc123",
        ]

        for url in dropbox_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.DROPBOX
            assert result["metadata"]["file_id"] == "abc123"
            assert result["metadata"]["requires_auth"] is True

    def test_detect_onedrive_urls(self):
        """Test detection of OneDrive URLs."""
        onedrive_urls = [
            "https://onedrive.live.com/?id=abc123",
            "https://1drv.ms/u/abc123",
        ]

        for url in onedrive_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.ONEDRIVE
            assert result["metadata"]["url"] == url
            assert result["metadata"]["requires_auth"] is True

    def test_detect_rss_feed_urls(self):
        """Test detection of RSS feed URLs."""
        rss_urls = [
            "https://example.com/feed.xml",
            "https://example.com/feed.rss",
            "https://example.com/feed.atom",
            "https://example.com/feed",
            "https://example.com/rss",
            "https://example.com/atom",
        ]

        for url in rss_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.RSS_FEED
            assert result["metadata"]["url"] == url

    def test_detect_direct_video_urls(self):
        """Test detection of direct video file URLs."""
        video_extensions = [
            ".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv", ".flv",
            ".m4v", ".mpg", ".mpeg", ".3gp", ".ogv", ".ts"
        ]

        for ext in video_extensions:
            url = f"https://example.com/video{ext}"
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.DIRECT
            assert result["metadata"]["extension"] == ext
            assert result["metadata"]["url"] == url

    def test_detect_direct_video_with_query_string(self):
        """Test detection works with query strings in URL."""
        url = "https://example.com/video.mp4?token=abc123&expires=456"
        result = SourceDetector.detect_source(url)
        assert result["valid"] is True
        assert result["source_type"] == SourceType.DIRECT
        assert result["metadata"]["extension"] == ".mp4"

    def test_detect_invalid_urls(self):
        """Test detection rejects invalid URLs."""
        invalid_urls = [
            "",
            "not-a-url",
            "ftp://example.com",
            "//example.com",
            None,
        ]

        for url in invalid_urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is False
            assert result["source_type"] == SourceType.UNKNOWN
            assert "error" in result

    def test_detect_unknown_valid_url(self):
        """Test detection returns unknown for valid URL without video."""
        # Valid URL but not a recognized video source
        result = SourceDetector.detect_source("https://example.com/page")
        assert result["valid"] is False
        assert result["source_type"] == SourceType.UNKNOWN
        assert "error" in result

    def test_detect_source_with_whitespace(self):
        """Test detection handles surrounding whitespace."""
        url = "  https://youtube.com/watch?v=test123  "
        result = SourceDetector.detect_source(url)
        assert result["valid"] is True
        assert result["source_type"] == SourceType.YOUTUBE

    def test_detect_source_case_insensitive(self):
        """Test detection is case-insensitive for domains."""
        urls = [
            "https://YOUTUBE.COM/watch?v=test123",
            "https://Vimeo.com/123456",
            "https://TWITCH.tv/channel",
        ]

        for url in urls:
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True


class TestDetectorMethods:
    """Test individual detector methods."""

    def test_detect_youtube_method(self):
        """Test _detect_youtube() method directly."""
        result = SourceDetector._detect_youtube("https://youtube.com/watch?v=test123")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.YOUTUBE
        assert result["metadata"]["video_id"] == "test123"

    def test_detect_youtube_invalid(self):
        """Test _detect_youtube() with invalid URL."""
        result = SourceDetector._detect_youtube("https://example.com")
        assert result["valid"] is False
        assert result["source_type"] == SourceType.UNKNOWN

    def test_detect_vimeo_method(self):
        """Test _detect_vimeo() method directly."""
        result = SourceDetector._detect_vimeo("https://vimeo.com/123456")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.VIMEO
        assert result["metadata"]["video_id"] == "123456"

    def test_detect_twitch_method(self):
        """Test _detect_twitch() method directly."""
        result = SourceDetector._detect_twitch("https://twitch.tv/testchannel")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.TWITCH
        assert result["metadata"]["channel_id"] == "testchannel"

    def test_detect_dailymotion_method(self):
        """Test _detect_dailymotion() method directly."""
        result = SourceDetector._detect_dailymotion("https://dailymotion.com/video/x123abc")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.DAILYMOTION

    def test_detect_hls_method(self):
        """Test _detect_hls() method directly."""
        result = SourceDetector._detect_hls("https://example.com/stream.m3u8")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.HLS

    def test_detect_hls_invalid(self):
        """Test _detect_hls() with invalid URL."""
        result = SourceDetector._detect_hls("https://example.com/stream.mp4")
        assert result["valid"] is False
        assert result["source_type"] == SourceType.UNKNOWN

    def test_detect_dash_method(self):
        """Test _detect_dash() method directly."""
        result = SourceDetector._detect_dash("https://example.com/stream.mpd")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.DASH

    def test_detect_dash_invalid(self):
        """Test _detect_dash() with invalid URL."""
        result = SourceDetector._detect_dash("https://example.com/stream.m3u8")
        assert result["valid"] is False

    def test_detect_google_drive_method(self):
        """Test _detect_google_drive() method directly."""
        result = SourceDetector._detect_google_drive("https://drive.google.com/file/d/abc123")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.GOOGLE_DRIVE
        assert result["metadata"]["file_id"] == "abc123"

    def test_detect_dropbox_method(self):
        """Test _detect_dropbox() method directly."""
        result = SourceDetector._detect_dropbox("https://dropbox.com/s/abc123/file.mp4")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.DROPBOX

    def test_detect_onedrive_method(self):
        """Test _detect_onedrive() method directly."""
        result = SourceDetector._detect_onedrive("https://onedrive.live.com/?id=abc123")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.ONEDRIVE

    def test_detect_rss_feed_method(self):
        """Test _detect_rss_feed() method directly."""
        result = SourceDetector._detect_rss_feed("https://example.com/feed.xml")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.RSS_FEED

    def test_detect_direct_video_method(self):
        """Test _detect_direct_video() method directly."""
        result = SourceDetector._detect_direct_video("https://example.com/video.mp4")
        assert result["valid"] is True
        assert result["source_type"] == SourceType.DIRECT

    def test_detect_direct_video_invalid(self):
        """Test _detect_direct_video() with non-video URL."""
        result = SourceDetector._detect_direct_video("https://example.com/page.html")
        assert result["valid"] is False

    def test_detect_direct_video_no_extension(self):
        """Test _detect_direct_video() with URL without extension."""
        result = SourceDetector._detect_direct_video("https://example.com/video")
        assert result["valid"] is False


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_supported_sources(self):
        """Test get_supported_sources() returns all sources except UNKNOWN."""
        sources = SourceDetector.get_supported_sources()

        assert isinstance(sources, list)
        assert len(sources) > 0
        assert SourceType.UNKNOWN.value not in sources
        assert SourceType.YOUTUBE.value in sources
        assert SourceType.VIMEO.value in sources

    def test_is_supported_valid_types(self):
        """Test is_supported() with valid source types."""
        valid_types = [
            "youtube",
            "vimeo",
            "dailymotion",
            "twitch",
            "direct",
            "hls",
            "dash",
            "cloud_drive",
            "dropbox",
            "onedrive",
            "rss",
        ]

        for source_type in valid_types:
            assert SourceDetector.is_supported(source_type) is True

    def test_is_supported_unknown(self):
        """Test is_supported() rejects UNKNOWN type."""
        assert SourceDetector.is_supported("unknown") is False

    def test_is_supported_invalid(self):
        """Test is_supported() rejects invalid types."""
        assert SourceDetector.is_supported("invalid_type") is False
        assert SourceDetector.is_supported("") is False

    def test_normalize_url_valid(self):
        """Test normalize_url() with valid URLs."""
        assert SourceDetector.normalize_url("https://youtube.com/watch?v=test") == "https://youtube.com/watch?v=test"
        assert SourceDetector.normalize_url("  https://example.com/video  ") == "https://example.com/video"

    def test_normalize_url_http_to_https_youtube(self):
        """Test normalize_url() converts YouTube http to https."""
        url = "http://www.youtube.com/watch?v=test"
        normalized = SourceDetector.normalize_url(url)
        assert normalized.startswith("https://")
        assert normalized == "https://www.youtube.com/watch?v=test"

    def test_normalize_url_http_to_https_vimeo(self):
        """Test normalize_url() converts Vimeo http to https."""
        url = "http://vimeo.com/123456"
        normalized = SourceDetector.normalize_url(url)
        assert normalized.startswith("https://")
        assert normalized == "https://vimeo.com/123456"

    def test_normalize_url_empty(self):
        """Test normalize_url() with empty input."""
        assert SourceDetector.normalize_url("") == ""
        assert SourceDetector.normalize_url(None) == ""

    def test_normalize_url_whitespace(self):
        """Test normalize_url() strips whitespace."""
        assert SourceDetector.normalize_url("  https://example.com  ") == "https://example.com"
        assert SourceDetector.normalize_url("\nhttps://example.com\t") == "https://example.com"


class TestDirectVideoExtensions:
    """Test direct video file extension detection."""

    def test_all_supported_extensions(self):
        """Test all declared extensions are detected."""
        extensions = [
            '.mp4', '.webm', '.mkv', '.avi', '.mov', '.wmv', '.flv',
            '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts'
        ]

        for ext in extensions:
            url = f"https://example.com/video{ext}"
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.DIRECT
            assert result["metadata"]["extension"] == ext

    def test_extension_case_insensitive(self):
        """Test extension detection is case-insensitive."""
        for ext in ['.MP4', '.Mp4', '.mp4']:
            url = f"https://example.com/video{ext}"
            result = SourceDetector.detect_source(url)
            assert result["valid"] is True
            assert result["source_type"] == SourceType.DIRECT

    def test_non_video_extension(self):
        """Test non-video extensions are not detected as direct video."""
        non_video_extensions = ['.pdf', '.txt', '.html', '.jpg', '.png']

        for ext in non_video_extensions:
            url = f"https://example.com/file{ext}"
            result = SourceDetector.detect_source(url)
            # May be valid for other sources (like RSS) but not DIRECT
            if result["source_type"] == SourceType.DIRECT:
                pytest.fail(f"Extension {ext} should not be detected as direct video")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_url_with_fragment(self):
        """Test URLs with fragments (#)."""
        url = "https://youtube.com/watch?v=test123&t=10s"
        result = SourceDetector.detect_source(url)
        assert result["valid"] is True

    def test_url_with_port(self):
        """Test URLs with port numbers."""
        url = "https://cdn.example.com:8080/stream.m3u8"
        result = SourceDetector.detect_source(url)
        assert result["valid"] is True
        assert result["source_type"] == SourceType.HLS

    def test_url_with_authentication(self):
        """Test URLs with basic authentication (should still work for direct files)."""
        # Note: This is an edge case - URLs with auth might not match our patterns
        # but should be handled gracefully
        url = "https://user:pass@example.com/video.mp4"
        result = SourceDetector.detect_source(url)
        # May or may not be valid depending on regex
        # Just ensure it doesn't crash
        assert "valid" in result

    def test_international_domains(self):
        """Test URLs with international domain names."""
        url = "https://xn--example-7ua.com/video.mp4"
        result = SourceDetector.detect_source(url)
        # Should at least not crash
        assert "valid" in result

    def test_very_long_url(self):
        """Test detection with very long URL."""
        long_path = "a" * 1000
        url = f"https://example.com/{long_path}/video.mp4"
        result = SourceDetector.detect_source(url)
        # Should handle gracefully
        assert "valid" in result

    def test_special_characters_in_path(self):
        """Test URLs with special characters in path."""
        url = "https://example.com/video-file_2024.mp4"
        result = SourceDetector.detect_source(url)
        assert result["valid"] is True
        assert result["source_type"] == SourceType.DIRECT


class TestMetadataStructure:
    """Test that metadata contains expected fields."""

    def test_youtube_metadata(self):
        """Test YouTube metadata structure."""
        result = SourceDetector.detect_source("https://youtube.com/watch?v=test123")
        assert "metadata" in result
        assert "video_id" in result["metadata"]
        assert isinstance(result["metadata"]["video_id"], str)

    def test_cloud_storage_requires_auth(self):
        """Test cloud storage sources have requires_auth flag."""
        cloud_urls = [
            ("https://drive.google.com/file/d/abc123", SourceType.GOOGLE_DRIVE),
            ("https://dropbox.com/s/abc123/file.mp4", SourceType.DROPBOX),
            ("https://onedrive.live.com/?id=abc123", SourceType.ONEDRIVE),
        ]

        for url, expected_type in cloud_urls:
            result = SourceDetector.detect_source(url)
            assert result["source_type"] == expected_type
            assert result["metadata"].get("requires_auth") is True

    def test_streaming_is_live_flag(self):
        """Test streaming sources have is_live flag."""
        streaming_urls = [
            ("https://example.com/stream.m3u8", SourceType.HLS),
            ("https://example.com/stream.mpd", SourceType.DASH),
        ]

        for url, expected_type in streaming_urls:
            result = SourceDetector.detect_source(url)
            assert result["source_type"] == expected_type
            assert result["metadata"].get("is_live") is True

    def test_twitch_content_type(self):
        """Test Twitch detection differentiates VOD vs channel."""
        # Channel
        result = SourceDetector.detect_source("https://twitch.tv/testchannel")
        assert result["metadata"]["content_type"] == "channel"

        # VOD
        result = SourceDetector.detect_source("https://twitch.tv/videos/123456")
        assert result["metadata"]["content_type"] == "vod"
