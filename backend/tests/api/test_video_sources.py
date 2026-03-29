"""
API tests for video sources endpoints.

Tests for:
- POST /api/video-sources/detect - Detect video source type from URL
- POST /api/video-sources/validate - Validate video source URL
- GET /api/video-sources/supported - Get supported source types
"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.lib.source_detector import SourceType


class TestDetectVideoSource:
    """Tests for POST /api/video-sources/detect endpoint."""

    def test_detect_youtube_video_success(self, client: TestClient, admin_user):
        """Test successful detection of YouTube video URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.YOUTUBE
            assert data["source_type_label"] == "YouTube"
            assert "metadata" in data
            assert "normalized_url" in data
            assert data["normalized_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_detect_youtube_short_url(self, client: TestClient, admin_user):
        """Test detection of YouTube short URL (youtu.be)."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://youtu.be/dQw4w9WgXcQ"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.YOUTUBE
            assert data["source_type_label"] == "YouTube"

    def test_detect_vimeo_video_success(self, client: TestClient, admin_user):
        """Test successful detection of Vimeo video URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://vimeo.com/123456789"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.VIMEO
            assert data["source_type_label"] == "Vimeo"

    def test_detect_twitch_channel_success(self, client: TestClient, admin_user):
        """Test successful detection of Twitch channel URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://www.twitch.tv/username"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.TWITCH
            assert data["source_type_label"] == "Twitch"

    def test_detect_direct_video_url(self, client: TestClient, admin_user):
        """Test detection of direct video URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://example.com/videos/video.mp4"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.DIRECT
            assert data["source_type_label"] == "Direct Video URL"

    def test_detect_hls_stream_url(self, client: TestClient, admin_user):
        """Test detection of HLS stream URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://example.com/stream/playlist.m3u8"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.HLS
            assert data["source_type_label"] == "HLS Stream"

    def test_detect_dash_stream_url(self, client: TestClient, admin_user):
        """Test detection of DASH stream URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://example.com/stream/manifest.mpd"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.DASH
            assert data["source_type_label"] == "DASH Stream"

    def test_detect_google_drive_url(self, client: TestClient, admin_user):
        """Test detection of Google Drive URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://drive.google.com/file/d/1Ab2Cd3Ef4Gh5Ij6Kl7Mn8Op9Qr0St1U/view"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.GOOGLE_DRIVE
            assert data["source_type_label"] == "Google Drive"

    def test_detect_dropbox_url(self, client: TestClient, admin_user):
        """Test detection of Dropbox URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://www.dropbox.com/s/abc123def456/video.mp4?dl=0"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.DROPBOX
            assert data["source_type_label"] == "Dropbox"

    def test_detect_rss_feed_url(self, client: TestClient, admin_user):
        """Test detection of RSS feed URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "https://example.com/feed.xml"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.RSS_FEED
            assert data["source_type_label"] == "RSS/Atom Feed"

    def test_detect_invalid_url(self, client: TestClient, admin_user):
        """Test detection of invalid URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "not-a-valid-url"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert data["source_type"] == SourceType.UNKNOWN
            assert data["source_type_label"] == "Unknown"
            assert "error" in data

    def test_detect_empty_url_validation_error(self, client: TestClient, admin_user):
        """Test validation error for empty URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/detect",
                json={"url": ""}
            )

            # Should return 422 for validation error
            assert response.status_code == 422

    def test_detect_url_normalization(self, client: TestClient, admin_user):
        """Test that URLs are normalized before detection."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            # URL with extra spaces
            response = client.post(
                "/api/video-sources/detect",
                json={"url": "  https://www.youtube.com/watch?v=dQw4w9WgXcQ  "}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["normalized_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
            assert data["normalized_url"].strip() == data["normalized_url"]

    def test_detect_unauthorized_request(self, client: TestClient):
        """Test that unauthorized requests are rejected."""
        # Don't mock get_current_user, should fail auth
        response = client.post(
            "/api/video-sources/detect",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        )

        # Should return 401 or 403 for unauthorized
        assert response.status_code in [401, 403]


class TestValidateVideoSource:
    """Tests for POST /api/video-sources/validate endpoint."""

    def test_validate_youtube_video_success(self, client: TestClient, admin_user):
        """Test successful validation of YouTube video URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/validate",
                json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.YOUTUBE
            assert data["source_type_label"] == "YouTube"
            assert "error" not in data or data["error"] is None

    def test_validate_with_availability_check_disabled(self, client: TestClient, admin_user):
        """Test validation with availability check disabled (default)."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/validate",
                json={
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "check_availability": False
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["is_available"] is None

    def test_validate_with_availability_check_enabled(self, client: TestClient, admin_user):
        """Test validation with availability check enabled."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/validate",
                json={
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "check_availability": True
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            # is_available should be present (None since not implemented yet)
            assert "is_available" in data

    def test_validate_invalid_url(self, client: TestClient, admin_user):
        """Test validation of invalid URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/validate",
                json={"url": "not-a-valid-url"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert data["source_type"] == SourceType.UNKNOWN
            assert "error" in data

    def test_validate_direct_video_compatibility_check(self, client: TestClient, admin_user):
        """Test validation checks compatibility for direct video URLs."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            # AVI format may require transcoding
            response = client.post(
                "/api/video-sources/validate",
                json={"url": "https://example.com/video.avi"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == SourceType.DIRECT
            assert len(data["compatibility_issues"]) > 0
            assert any("avi" in issue.lower() for issue in data["compatibility_issues"])

    def test_validate_direct_video_wmv_compatibility(self, client: TestClient, admin_user):
        """Test validation detects WMV compatibility issues."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/validate",
                json={"url": "https://example.com/video.wmv"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert len(data["compatibility_issues"]) > 0
            assert any("wmv" in issue.lower() for issue in data["compatibility_issues"])

    def test_validate_direct_video_mp4_no_issues(self, client: TestClient, admin_user):
        """Test validation has no compatibility issues for MP4."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/validate",
                json={"url": "https://example.com/video.mp4"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert len(data["compatibility_issues"]) == 0

    def test_validate_empty_url_validation_error(self, client: TestClient, admin_user):
        """Test validation error for empty URL."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.post(
                "/api/video-sources/validate",
                json={"url": ""}
            )

            assert response.status_code == 422

    def test_validate_unauthorized_request(self, client: TestClient):
        """Test that unauthorized validation requests are rejected."""
        response = client.post(
            "/api/video-sources/validate",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
        )

        assert response.status_code in [401, 403]


class TestGetSupportedSources:
    """Tests for GET /api/video-sources/supported endpoint."""

    def test_get_supported_sources_success(self, client: TestClient, admin_user):
        """Test successful retrieval of supported sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()
            assert "sources" in data
            assert "total_count" in data
            assert isinstance(data["sources"], list)
            assert data["total_count"] > 0

    def test_supported_sources_includes_youtube(self, client: TestClient, admin_user):
        """Test that YouTube is in supported sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            youtube_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.YOUTUBE),
                None
            )
            assert youtube_source is not None
            assert youtube_source["label"] == "YouTube"
            assert "description" in youtube_source
            assert "examples" in youtube_source
            assert len(youtube_source["examples"]) > 0

    def test_supported_sources_includes_vimeo(self, client: TestClient, admin_user):
        """Test that Vimeo is in supported sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            vimeo_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.VIMEO),
                None
            )
            assert vimeo_source is not None
            assert vimeo_source["label"] == "Vimeo"

    def test_supported_sources_includes_twitch(self, client: TestClient, admin_user):
        """Test that Twitch is in supported sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            twitch_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.TWITCH),
                None
            )
            assert twitch_source is not None
            assert twitch_source["label"] == "Twitch"

    def test_supported_sources_includes_direct(self, client: TestClient, admin_user):
        """Test that Direct Video URL is in supported sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            direct_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.DIRECT),
                None
            )
            assert direct_source is not None
            assert direct_source["label"] == "Direct Video URL"

    def test_supported_sources_includes_hls(self, client: TestClient, admin_user):
        """Test that HLS Stream is in supported sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            hls_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.HLS),
                None
            )
            assert hls_source is not None
            assert hls_source["label"] == "HLS Stream"

    def test_supported_sources_includes_dash(self, client: TestClient, admin_user):
        """Test that DASH Stream is in supported sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            dash_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.DASH),
                None
            )
            assert dash_source is not None
            assert dash_source["label"] == "DASH Stream"

    def test_supported_sources_includes_cloud_storage(self, client: TestClient, admin_user):
        """Test that cloud storage providers are in supported sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            # Check Google Drive
            gdrive_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.GOOGLE_DRIVE),
                None
            )
            assert gdrive_source is not None
            assert gdrive_source["label"] == "Google Drive"

            # Check Dropbox
            dropbox_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.DROPBOX),
                None
            )
            assert dropbox_source is not None
            assert dropbox_source["label"] == "Dropbox"

            # Check OneDrive
            onedrive_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.ONEDRIVE),
                None
            )
            assert onedrive_source is not None
            assert onedrive_source["label"] == "OneDrive"

    def test_supported_sources_includes_rss(self, client: TestClient, admin_user):
        """Test that RSS/Atom Feed is in supported sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            rss_source = next(
                (s for s in data["sources"] if s["type"] == SourceType.RSS_FEED),
                None
            )
            assert rss_source is not None
            assert rss_source["label"] == "RSS/Atom Feed"

    def test_supported_sources_structure(self, client: TestClient, admin_user):
        """Test that all sources have required fields."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            for source in data["sources"]:
                assert "type" in source
                assert "label" in source
                assert "description" in source
                assert "examples" in source
                assert isinstance(source["examples"], list)

    def test_supported_sources_count_matches_list(self, client: TestClient, admin_user):
        """Test that total_count matches actual number of sources."""
        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            response = client.get("/api/video-sources/supported")

            assert response.status_code == 200
            data = response.json()

            assert data["total_count"] == len(data["sources"])

    def test_supported_sources_unauthorized_request(self, client: TestClient):
        """Test that unauthorized requests are rejected."""
        response = client.get("/api/video-sources/supported")

        assert response.status_code in [401, 403]


class TestVideoSourcesIntegration:
    """Integration tests for video sources endpoints."""

    def test_detect_and_validate_flow(self, client: TestClient, admin_user):
        """Test complete detect then validate flow."""
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            # First detect the source
            detect_response = client.post(
                "/api/video-sources/detect",
                json={"url": test_url}
            )

            assert detect_response.status_code == 200
            detect_data = detect_response.json()
            assert detect_data["valid"] is True

            # Then validate the source
            validate_response = client.post(
                "/api/video-sources/validate",
                json={"url": test_url}
            )

            assert validate_response.status_code == 200
            validate_data = validate_response.json()
            assert validate_data["valid"] is True

            # Both should return the same source type
            assert detect_data["source_type"] == validate_data["source_type"]

    def test_multiple_source_types_detection(self, client: TestClient, admin_user):
        """Test detection of multiple different source types."""
        test_urls = [
            ("https://www.youtube.com/watch?v=123", SourceType.YOUTUBE),
            ("https://vimeo.com/456", SourceType.VIMEO),
            ("https://www.twitch.tv/testuser", SourceType.TWITCH),
            ("https://example.com/video.mp4", SourceType.DIRECT),
            ("https://example.com/stream.m3u8", SourceType.HLS),
            ("https://example.com/stream.mpd", SourceType.DASH),
        ]

        with patch('src.api.video_sources.get_current_user', return_value=admin_user):
            for url, expected_type in test_urls:
                response = client.post(
                    "/api/video-sources/detect",
                    json={"url": url}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["source_type"] == expected_type


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
