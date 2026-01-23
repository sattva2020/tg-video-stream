"""
Integration tests for RSS Feed Service.

Tests cover:
- Video enclosure detection and parsing
- RSS and Atom format support
- Media RSS support
- Video MIME type and URL detection
- Duration parsing
- Feed title extraction
- Error handling
"""
import pytest
from unittest.mock import MagicMock, Mock, patch, AsyncMock
import httpx
from datetime import datetime

from src.services.rss_feed_service import (
    VideoEnclosure,
    FeedFormat,
    parse_feed,
    parse_feed_sync,
    _is_video_mime_type,
    _is_video_url,
    _parse_duration,
    _detect_feed_format,
    _extract_feed_title,
    _extract_enclosures,
    _extract_rss_enclosures,
    _extract_atom_enclosures,
    _get_item_text,
    _extract_media_thumbnail,
)


# ======================== FIXTURES ========================

@pytest.fixture
def sample_rss_feed_xml():
    """Sample RSS feed with video enclosures."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Test Video Feed</title>
    <item>
      <title>Episode 1</title>
      <enclosure url="https://example.com/video1.mp4" type="video/mp4" length="1024000"/>
      <pubDate>Mon, 01 Jan 2025 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Episode 2</title>
      <enclosure url="https://example.com/video2.webm" type="video/webm" length="2048000"/>
      <pubDate>Mon, 02 Jan 2025 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def sample_atom_feed_xml():
    """Sample Atom feed with video enclosures."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">
  <title>Test Video Podcast</title>
  <entry>
    <title>Episode 1</title>
    <link rel="enclosure" href="https://example.com/video1.mp4" type="video/mp4" length="1024000"/>
    <published>2025-01-01T12:00:00Z</published>
  </entry>
  <entry>
    <title>Episode 2</title>
    <link rel="enclosure" href="https://example.com/video2.webm" type="video/webm" length="2048000"/>
    <published>2025-01-02T12:00:00Z</published>
  </entry>
</feed>"""


@pytest.fixture
def sample_media_rss_xml():
    """Sample Media RSS feed."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Media RSS Feed</title>
    <item>
      <title>Video Episode</title>
      <media:content url="https://example.com/video.mp4" type="video/mp4" duration="3600"/>
      <media:thumbnail url="https://example.com/thumb.jpg"/>
      <pubDate>Mon, 01 Jan 2025 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()
    client.aclose = AsyncMock()
    return client


# ======================== TEST CLASSES ========================

class TestVideoEnclosure:
    """Test VideoEnclosure class."""

    def test_init_with_all_fields(self):
        """Test initialization with all fields."""
        enc = VideoEnclosure(
            url="https://example.com/video.mp4",
            title="Test Video",
            duration=3600,
            thumbnail="https://example.com/thumb.jpg",
            mime_type="video/mp4",
            size=1024000,
            published="2025-01-01T12:00:00Z"
        )
        assert enc.url == "https://example.com/video.mp4"
        assert enc.title == "Test Video"
        assert enc.duration == 3600
        assert enc.thumbnail == "https://example.com/thumb.jpg"
        assert enc.mime_type == "video/mp4"
        assert enc.size == 1024000
        assert enc.published == "2025-01-01T12:00:00Z"

    def test_init_with_minimal_fields(self):
        """Test initialization with minimal fields."""
        enc = VideoEnclosure(url="https://example.com/video.mp4")
        assert enc.url == "https://example.com/video.mp4"
        assert enc.title is None
        assert enc.duration is None

    def test_to_dict(self):
        """Test converting to dictionary."""
        enc = VideoEnclosure(
            url="https://example.com/video.mp4",
            title="Test Video",
            duration=3600
        )
        data = enc.to_dict()
        assert data["url"] == "https://example.com/video.mp4"
        assert data["title"] == "Test Video"
        assert data["duration"] == 3600


class TestIsVideoMimeType:
    """Test video MIME type detection."""

    def test_recognizes_video_mp4(self):
        """Test video/mp4 recognition."""
        assert _is_video_mime_type("video/mp4") is True

    def test_recognizes_video_webm(self):
        """Test video/webm recognition."""
        assert _is_video_mime_type("video/webm") is True

    def test_recognizes_video_prefix(self):
        """Test any video/* prefix."""
        assert _is_video_mime_type("video/quicktime") is True
        assert _is_video_mime_type("video/x-matroska") is True

    def test_rejects_audio_types(self):
        """Test audio types are rejected."""
        assert _is_video_mime_type("audio/mpeg") is False
        assert _is_video_mime_type("audio/wav") is False

    def test_rejects_other_types(self):
        """Test non-media types are rejected."""
        assert _is_video_mime_type("application/pdf") is False
        assert _is_video_mime_type("text/plain") is False

    def test_handles_none(self):
        """Test None input."""
        assert _is_video_mime_type(None) is False

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert _is_video_mime_type("VIDEO/MP4") is True
        assert _is_video_mime_type("Video/WebM") is True


class TestIsVideoUrl:
    """Test video URL detection by extension."""

    def test_recognizes_mp4(self):
        """Test .mp4 recognition."""
        assert _is_video_url("https://example.com/video.mp4") is True

    def test_recognizes_webm(self):
        """Test .webm recognition."""
        assert _is_video_url("https://example.com/video.webm") is True

    def test_recognizes_all_video_extensions(self):
        """Test all supported video extensions."""
        extensions = [".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".m4v", ".mpg", ".mpeg", ".3gp", ".ogv"]
        for ext in extensions:
            assert _is_video_url(f"https://example.com/video{ext}") is True

    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert _is_video_url("https://example.com/video.MP4") is True
        assert _is_video_url("https://example.com/video.WebM") is True

    def test_rejects_non_video(self):
        """Test non-video extensions are rejected."""
        assert _is_video_url("https://example.com/audio.mp3") is False
        assert _is_video_url("https://example.com/doc.pdf") is False

    def test_handles_none(self):
        """Test None input."""
        assert _is_video_url(None) is False

    def test_handles_empty_string(self):
        """Test empty string."""
        assert _is_video_url("") is False


class TestParseDuration:
    """Test duration parsing."""

    def test_parse_seconds_as_int(self):
        """Test parsing seconds as integer."""
        assert _parse_duration("3600") == 3600
        assert _parse_duration("90") == 90

    def test_parse_hms_format(self):
        """Test HH:MM:SS format."""
        assert _parse_duration("01:00:00") == 3600
        assert _parse_duration("01:30:45") == 5445
        assert _parse_duration("00:05:30") == 330

    def test_parse_ms_format(self):
        """Test MM:SS format."""
        assert _parse_duration("05:30") == 330
        assert _parse_duration("10:00") == 600

    def test_parse_iso8601_duration(self):
        """Test ISO 8601 PT format."""
        assert _parse_duration("PT1H") == 3600
        assert _parse_duration("PT30M") == 1800
        assert _parse_duration("PT90S") == 90
        assert _parse_duration("PT1H30M45S") == 5445

    def test_parse_invalid_returns_none(self):
        """Test invalid format returns None."""
        assert _parse_duration("invalid") is None
        assert _parse_duration("") is None

    def test_parse_none_returns_none(self):
        """Test None input returns None."""
        assert _parse_duration(None) is None


class TestDetectFeedFormat:
    """Test feed format detection."""

    def test_detects_rss_format(self):
        """Test RSS format detection."""
        xml = '<rss version="2.0"><channel><title>Test</title></channel></rss>'
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        assert _detect_feed_format(root) == FeedFormat.RSS

    def test_detects_atom_format(self):
        """Test Atom format detection."""
        xml = '<feed xmlns="http://www.w3.org/2005/Atom"><title>Test</title></feed>'
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        assert _detect_feed_format(root) == FeedFormat.ATOM

    def test_detects_media_rss(self):
        """Test Media RSS detection."""
        xml = '<rss version="2.0"><channel><media:content url="test.mp4"/></channel></rss>'
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        assert _detect_feed_format(root) == FeedFormat.MEDIA_RSS

    def test_returns_unknown_for_unrecognized(self):
        """Test unknown format detection."""
        xml = '<root><item>Test</item></root>'
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        assert _detect_feed_format(root) == FeedFormat.UNKNOWN


class TestExtractFeedTitle:
    """Test feed title extraction."""

    def test_extract_rss_title(self):
        """Test RSS title extraction."""
        xml = '<rss version="2.0"><channel><title>Test Feed</title></channel></rss>'
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        title = _extract_feed_title(root, FeedFormat.RSS)
        assert title == "Test Feed"

    def test_extract_atom_title(self):
        """Test Atom title extraction."""
        xml = '<feed xmlns="http://www.w3.org/2005/Atom"><title>Test Feed</title></feed>'
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        title = _extract_feed_title(root, FeedFormat.ATOM)
        assert title == "Test Feed"

    def test_returns_none_when_missing(self):
        """Test None when title not found."""
        xml = '<rss version="2.0"><channel></channel></rss>'
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        title = _extract_feed_title(root, FeedFormat.RSS)
        assert title is None


class TestGetItemText:
    """Test text extraction from XML elements."""

    def test_extract_existing_text(self):
        """Test extracting text from existing element."""
        xml = '<item><title>Test Title</title></item>'
        import xml.etree.ElementTree as ET
        item = ET.fromstring(xml)
        text = _get_item_text(item, "title")
        assert text == "Test Title"

    def test_returns_none_for_missing_element(self):
        """Test None for missing element."""
        xml = '<item><description>Test</description></item>'
        import xml.etree.ElementTree as ET
        item = ET.fromstring(xml)
        text = _get_item_text(item, "title")
        assert text is None

    def test_returns_none_for_empty_text(self):
        """Test None for element with no text."""
        xml = '<item><title></title></item>'
        import xml.etree.ElementTree as ET
        item = ET.fromstring(xml)
        text = _get_item_text(item, "title")
        assert text is None


class TestExtractMediaThumbnail:
    """Test Media RSS thumbnail extraction."""

    def test_extract_media_thumbnail(self):
        """Test extracting media:thumbnail URL."""
        xml = '''<item xmlns:media="http://search.yahoo.com/mrss/">
            <media:thumbnail url="https://example.com/thumb.jpg"/>
        </item>'''
        import xml.etree.ElementTree as ET
        item = ET.fromstring(xml)
        namespaces = {"media": "http://search.yahoo.com/mrss/"}
        thumb = _extract_media_thumbnail(item, namespaces)
        assert thumb == "https://example.com/thumb.jpg"

    def test_extract_from_media_group(self):
        """Test extracting thumbnail from media:group."""
        xml = '''<item xmlns:media="http://search.yahoo.com/mrss/">
            <media:group>
                <media:thumbnail url="https://example.com/thumb.jpg"/>
            </media:group>
        </item>'''
        import xml.etree.ElementTree as ET
        item = ET.fromstring(xml)
        namespaces = {"media": "http://search.yahoo.com/mrss/"}
        thumb = _extract_media_thumbnail(item, namespaces)
        assert thumb == "https://example.com/thumb.jpg"

    def test_returns_none_when_missing(self):
        """Test None when thumbnail not found."""
        xml = '<item><title>Test</title></item>'
        import xml.etree.ElementTree as ET
        item = ET.fromstring(xml)
        namespaces = {"media": "http://search.yahoo.com/mrss/"}
        thumb = _extract_media_thumbnail(item, namespaces)
        assert thumb is None


class TestParseFeed:
    """Test main parse_feed function."""

    @pytest.mark.asyncio
    async def test_parse_rss_feed_success(self, mock_httpx_client, sample_rss_feed_xml):
        """Test successful RSS feed parsing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_rss_feed_xml
        mock_httpx_client.get.return_value = mock_response

        result = await parse_feed(
            "https://example.com/feed.rss",
            client=mock_httpx_client
        )

        assert result["success"] is True
        assert result["feed_title"] == "Test Video Feed"
        assert result["format"] == "rss"
        assert result["total_enclosures"] == 2
        assert len(result["enclosures"]) == 2
        assert result["enclosures"][0]["url"] == "https://example.com/video1.mp4"

    @pytest.mark.asyncio
    async def test_parse_atom_feed_success(self, mock_httpx_client, sample_atom_feed_xml):
        """Test successful Atom feed parsing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_atom_feed_xml
        mock_httpx_client.get.return_value = mock_response

        result = await parse_feed(
            "https://example.com/feed.atom",
            client=mock_httpx_client
        )

        assert result["success"] is True
        assert result["feed_title"] == "Test Video Podcast"
        assert result["format"] == "atom"
        assert result["total_enclosures"] == 2

    @pytest.mark.asyncio
    async def test_parse_media_rss_feed(self, mock_httpx_client, sample_media_rss_xml):
        """Test Media RSS feed parsing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_media_rss_xml
        mock_httpx_client.get.return_value = mock_response

        result = await parse_feed(
            "https://example.com/feed.xml",
            client=mock_httpx_client
        )

        assert result["success"] is True
        assert result["total_enclosures"] == 1
        assert result["enclosures"][0]["thumbnail"] == "https://example.com/thumb.jpg"

    @pytest.mark.asyncio
    async def test_parse_feed_max_items_limit(self, mock_httpx_client, sample_rss_feed_xml):
        """Test max_items parameter limits results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sample_rss_feed_xml
        mock_httpx_client.get.return_value = mock_response

        result = await parse_feed(
            "https://example.com/feed.rss",
            client=mock_httpx_client,
            max_items=1
        )

        assert result["success"] is True
        assert result["total_enclosures"] == 1

    @pytest.mark.asyncio
    async def test_parse_feed_http_error(self, mock_httpx_client):
        """Test HTTP error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_httpx_client.get.return_value = mock_response

        result = await parse_feed(
            "https://example.com/feed.rss",
            client=mock_httpx_client
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_parse_feed_invalid_xml(self, mock_httpx_client):
        """Test invalid XML handling."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "invalid xml content"
        mock_httpx_client.get.return_value = mock_response

        result = await parse_feed(
            "https://example.com/feed.rss",
            client=mock_httpx_client
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_parse_feed_empty_url(self):
        """Test empty URL error."""
        result = await parse_feed("")
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_parse_feed_creates_own_client(self, sample_rss_feed_xml):
        """Test that client is created if not provided."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = sample_rss_feed_xml
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            result = await parse_feed("https://example.com/feed.rss")

            assert result["success"] is True
            mock_client_class.assert_called_once()
            mock_client.aclose.assert_called_once()


class TestParseFeedSync:
    """Test synchronous parse_feed_sync wrapper."""

    def test_parse_feed_sync_success(self, sample_rss_feed_xml):
        """Test successful synchronous parsing."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = sample_rss_feed_xml
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client_class.return_value = mock_client

            result = parse_feed_sync("https://example.com/feed.rss")

            assert result["success"] is True


class TestExtractRSSEnclosures:
    """Test RSS enclosure extraction."""

    def test_extract_standard_enclosures(self):
        """Test extracting standard <enclosure> tags."""
        xml = '''<rss version="2.0">
            <channel>
                <item>
                    <title>Video</title>
                    <enclosure url="https://example.com/video.mp4" type="video/mp4" length="1024"/>
                </item>
            </channel>
        </rss>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_rss_enclosures(root)
        assert len(enclosures) == 1
        assert enclosures[0].url == "https://example.com/video.mp4"

    def test_extract_media_content(self):
        """Test extracting media:content."""
        xml = '''<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
            <channel>
                <item>
                    <title>Video</title>
                    <media:content url="https://example.com/video.mp4" type="video/mp4"/>
                </item>
            </channel>
        </rss>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_rss_enclosures(root)
        assert len(enclosures) == 1
        assert enclosures[0].url == "https://example.com/video.mp4"

    def test_extract_media_group(self):
        """Test extracting from media:group."""
        xml = '''<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
            <channel>
                <item>
                    <title>Video</title>
                    <media:group>
                        <media:content url="https://example.com/video.mp4" type="video/mp4"/>
                    </media:group>
                </item>
            </channel>
        </rss>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_rss_enclosures(root)
        assert len(enclosures) == 1
        assert enclosures[0].url == "https://example.com/video.mp4"

    def test_filters_non_video_enclosures(self):
        """Test that non-video enclosures are filtered out."""
        xml = '''<rss version="2.0">
            <channel>
                <item>
                    <title>Audio</title>
                    <enclosure url="https://example.com/audio.mp3" type="audio/mpeg"/>
                </item>
                <item>
                    <title>Video</title>
                    <enclosure url="https://example.com/video.mp4" type="video/mp4"/>
                </item>
            </channel>
        </rss>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_rss_enclosures(root)
        assert len(enclosures) == 1
        assert enclosures[0].url == "https://example.com/video.mp4"


class TestExtractAtomEnclosures:
    """Test Atom enclosure extraction."""

    def test_extract_link_enclosure(self):
        """Test extracting link rel='enclosure'."""
        xml = '''<feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Video</title>
                <link rel="enclosure" href="https://example.com/video.mp4" type="video/mp4"/>
            </entry>
        </feed>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_atom_enclosures(root)
        assert len(enclosures) == 1
        assert enclosures[0].url == "https://example.com/video.mp4"

    def test_extract_media_content_from_atom(self):
        """Test extracting media:content from Atom feed."""
        xml = '''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">
            <entry>
                <title>Video</title>
                <media:content url="https://example.com/video.mp4" type="video/mp4"/>
            </entry>
        </feed>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_atom_enclosures(root)
        assert len(enclosures) == 1
        assert enclosures[0].url == "https://example.com/video.mp4"

    def test_filters_non_video_in_atom(self):
        """Test filtering non-video in Atom feeds."""
        xml = '''<feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Audio</title>
                <link rel="enclosure" href="https://example.com/audio.mp3" type="audio/mpeg"/>
            </entry>
            <entry>
                <title>Video</title>
                <link rel="enclosure" href="https://example.com/video.mp4" type="video/mp4"/>
            </entry>
        </feed>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_atom_enclosures(root)
        assert len(enclosures) == 1
        assert enclosures[0].url == "https://example.com/video.mp4"


class TestExtractEnclosures:
    """Test main enclosure extraction dispatcher."""

    def test_dispatches_to_rss_extractor(self):
        """Test dispatching to RSS extractor for RSS format."""
        xml = '''<rss version="2.0">
            <channel>
                <item>
                    <enclosure url="https://example.com/video.mp4" type="video/mp4"/>
                </item>
            </channel>
        </rss>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_enclosures(root, FeedFormat.RSS)
        assert len(enclosures) == 1

    def test_dispatches_to_atom_extractor(self):
        """Test dispatching to Atom extractor for Atom format."""
        xml = '''<feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <link rel="enclosure" href="https://example.com/video.mp4" type="video/mp4"/>
            </entry>
        </feed>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_enclosures(root, FeedFormat.ATOM)
        assert len(enclosures) == 1

    def test_tries_both_for_unknown_format(self):
        """Test trying both extractors for unknown format."""
        xml = '''<rss version="2.0">
            <channel>
                <item>
                    <enclosure url="https://example.com/video.mp4" type="video/mp4"/>
                </item>
            </channel>
        </rss>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_enclosures(root, FeedFormat.UNKNOWN)
        assert len(enclosures) == 1


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_feed_returns_no_enclosures(self):
        """Test empty feed returns empty list."""
        xml = '<rss version="2.0"><channel></channel></rss>'
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_enclosures(root, FeedFormat.RSS)
        assert len(enclosures) == 0

    def test_feed_with_no_video_files(self):
        """Test feed with only non-video files."""
        xml = '''<rss version="2.0">
            <channel>
                <item>
                    <enclosure url="https://example.com/audio.mp3" type="audio/mpeg"/>
                </item>
                <item>
                    <enclosure url="https://example.com/doc.pdf" type="application/pdf"/>
                </item>
            </channel>
        </rss>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_enclosures(root, FeedFormat.RSS)
        assert len(enclosures) == 0

    def test_malformed_enclosure_tags(self):
        """Test handling malformed enclosure tags."""
        xml = '''<rss version="2.0">
            <channel>
                <item>
                    <title>Video</title>
                    <enclosure type="video/mp4"/>
                </item>
            </channel>
        </rss>'''
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml)
        enclosures = _extract_enclosures(root, FeedFormat.RSS)
        # Should not crash, just skip malformed entries
        assert isinstance(enclosures, list)
