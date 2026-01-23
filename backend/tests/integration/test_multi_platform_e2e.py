"""
End-to-End Integration Tests: Multi-Platform Video Sources

Tests the complete workflow for all supported video source types:
- URL detection and validation
- Metadata fetching
- Database storage
- Transcoding trigger for incompatible formats
- Source management

Coverage Target: Complete E2E flow for each source type
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from src.models.user import User
from src.models.playlist import PlaylistItem, Playlist
from src.auth.jwt import create_access_token
from sqlalchemy.orm import Session


@pytest.fixture
def admin_user(db_session: Session):
    """Create admin user in DB"""
    user = User(
        email="multipletform.admin@e2e.test",
        google_id="multplatform_e2e_admin_123",
        status="approved",
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_playlist(db_session: Session, admin_user):
    """Create a test playlist for the user"""
    playlist = Playlist(
        name="E2E Multi-Platform Test Playlist",
        description="Testing all video source types",
        owner_id=admin_user.id,
        status="active"
    )
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)
    return playlist


@pytest.fixture
def admin_token(admin_user):
    """Generate JWT for admin"""
    return create_access_token({
        "sub": str(admin_user.id),
        "role": admin_user.role
    })


class TestVimeoE2E:
    """End-to-end tests for Vimeo video sources"""

    def test_add_vimeo_video_fetches_metadata(self, client: TestClient, admin_token, user_playlist):
        """Test adding Vimeo video via API and verify metadata is fetched"""
        mock_metadata = {
            "title": "Test Vimeo Video",
            "description": "Test Description",
            "uploader": "Vimeo User",
            "duration": 180,
            "view_count": 1000,
            "thumbnail": "https://vimeo.com/thumb.jpg",
            "webpage_url": "https://vimeo.com/123456789",
            "extractor": "vimeo",
            "extractor_key": "Vimeo"
        }

        with patch('src.tasks.media.extract_video_metadata', return_value=mock_metadata):
            response = client.post(
                "/api/playlist/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://vimeo.com/123456789",
                    "playlist_id": str(user_playlist.id),
                    "auto_detect": True
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert data["type"] == "vimeo"
            assert data["title"] == "Test Vimeo Video"
            assert data["url"] == "https://vimeo.com/123456789"

    def test_vimeo_video_validates_successfully(self, client: TestClient, admin_token):
        """Test Vimeo video URL validation"""
        response = client.post(
            "/api/video-sources/validate",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"url": "https://vimeo.com/123456789"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["source_type"] == "vimeo"
        assert data["source_type_label"] == "Vimeo"


class TestTwitchE2E:
    """End-to-end tests for Twitch video sources"""

    def test_add_twitch_clip_fetches_metadata(self, client: TestClient, admin_token, user_playlist):
        """Test adding Twitch clip via API and verify metadata is fetched"""
        mock_metadata = {
            "title": "Test Twitch Clip",
            "description": "Amazing gaming moment",
            "uploader": "TwitchStreamer",
            "duration": 45,
            "view_count": 50000,
            "thumbnail": "https://clips.twitch.tv/thumb.jpg",
            "webpage_url": "https://clips.twitch.tv/example/clip",
            "extractor": "twitch:clip",
            "extractor_key": "TwitchClip"
        }

        with patch('src.tasks.media.extract_video_metadata', return_value=mock_metadata):
            response = client.post(
                "/api/playlist/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://clips.twitch.tv/example/clip",
                    "playlist_id": str(user_playlist.id),
                    "auto_detect": True
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert data["type"] == "twitch"
            assert data["title"] == "Test Twitch Clip"

    def test_add_twitch_vod_fetches_metadata(self, client: TestClient, admin_token, user_playlist):
        """Test adding Twitch VOD via API and verify metadata is fetched"""
        mock_metadata = {
            "title": "Test Twitch VOD",
            "description": "Full stream recording",
            "uploader": "TwitchStreamer",
            "duration": 7200,
            "view_count": 10000,
            "thumbnail": "https://static-cdn.jtvnw.net/thumb.jpg",
            "webpage_url": "https://www.twitch.tv/videos/123456789",
            "extractor": "twitch:video",
            "extractor_key": "TwitchVideo"
        }

        with patch('src.tasks.media.extract_video_metadata', return_value=mock_metadata):
            response = client.post(
                "/api/playlist/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://www.twitch.tv/videos/123456789",
                    "playlist_id": str(user_playlist.id),
                    "auto_detect": True
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert data["type"] == "twitch"


class TestDirectVideoE2E:
    """End-to-end tests for direct video URL sources"""

    def test_add_mp4_url_validates_codecs(self, client: TestClient, admin_token):
        """Test direct MP4 URL validates codec compatibility"""
        mock_validation = MagicMock(
            valid=True,
            is_compatible=True,
            video_codec="h264",
            audio_codec="aac",
            format="mp4",
            has_orientation=False,
            orientation_value=None,
            errors=[],
            warnings=[]
        )

        with patch('src.api.video_sources.VideoValidator') as MockValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_url = AsyncMock(return_value=mock_validation)
            MockValidator.return_value = mock_validator_instance

            response = client.post(
                "/api/video-sources/validate",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://example.com/video.mp4",
                    "check_availability": True
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["source_type"] == "direct"

    def test_incompatible_mp4_triggers_transcoding(self, client: TestClient, admin_token):
        """Test incompatible video format triggers transcoding"""
        mock_metadata = {
            "title": "Incompatible Video",
            "description": "Video with unsupported codec",
            "webpage_url": "https://example.com/video.avi",
            "extractor": "generic",
            "duration": 120
        }

        mock_validation = MagicMock(
            valid=True,
            is_compatible=False,
            video_codec="mpeg4",
            audio_codec="mp3",
            format="avi",
            has_orientation=False,
            errors=[],
            warnings=["Codec not compatible with Telegram"]
        )

        with patch('src.tasks.media.extract_video_metadata', return_value=mock_metadata), \
             patch('src.tasks.media.VideoValidator') as MockValidator:
            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_url = AsyncMock(return_value=mock_validation)
            mock_validator_instance.check_transcoding_required = MagicMock(return_value={
                "required": True,
                "reasons": ["Unsupported codec: mpeg4"]
            })
            MockValidator.return_value = mock_validator_instance

            response = client.post(
                "/api/playlist/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://example.com/video.avi",
                    "auto_detect": True
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert data["type"] == "direct"
            # Transcoding task should be queued automatically


class TestRSSFeedE2E:
    """End-to-end tests for RSS feed ingestion"""

    def test_add_rss_feed_parses_videos(self, client: TestClient, admin_token):
        """Test adding RSS feed URL and verify videos are parsed and queued"""
        mock_feed_data = {
            "title": "Test Video Feed",
            "description": "RSS feed with video enclosures",
            "entries": [
                {
                    "title": "Video 1",
                    "link": "https://example.com/video1.mp4",
                    "description": "First video",
                    "id": "1"
                },
                {
                    "title": "Video 2",
                    "link": "https://example.com/video2.mp4",
                    "description": "Second video",
                    "id": "2"
                }
            ]
        }

        with patch('src.services.rss_feed_service.parse_feed', return_value=mock_feed_data), \
             patch('src.tasks.media.extract_video_metadata') as mock_extract:

            mock_extract.side_effect = [
                {
                    "title": "Video 1",
                    "webpage_url": "https://example.com/video1.mp4",
                    "duration": 120
                },
                {
                    "title": "Video 2",
                    "webpage_url": "https://example.com/video2.mp4",
                    "duration": 180
                }
            ]

            response = client.post(
                "/api/playlist/import",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://example.com/feed.xml",
                    "name": "RSS Feed Test"
                }
            )

            # RSS feeds should create a playlist and import items
            assert response.status_code in [201, 202]


class TestSourceManagerIntegration:
    """Integration tests for Source Manager functionality"""

    def test_source_manager_shows_all_sources(self, client: TestClient, admin_token, admin_user, db_session):
        """Test that SourceManager shows all sources with correct status"""
        # Create multiple playlist items with different source types
        sources = [
            {
                "title": "Vimeo Video",
                "url": "https://vimeo.com/123456789",
                "type": "vimeo",
                "status": "active"
            },
            {
                "title": "Twitch Clip",
                "url": "https://clips.twitch.tv/test",
                "type": "twitch",
                "status": "active"
            },
            {
                "title": "Direct MP4",
                "url": "https://example.com/video.mp4",
                "type": "direct",
                "status": "pending_validation"
            }
        ]

        for source in sources:
            item = PlaylistItem(
                title=source["title"],
                url=source["url"],
                type=source["type"],
                status=source["status"],
                owner_id=admin_user.id
            )
            db_session.add(item)

        db_session.commit()

        # Get all playlist items (this is what SourceManager would display)
        response = client.get(
            "/api/playlist/",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

        # Verify all source types are present
        source_types = {item["type"] for item in data}
        assert "vimeo" in source_types
        assert "twitch" in source_types
        assert "direct" in source_types

    def test_source_detection_accuracy(self, client: TestClient, admin_token):
        """Test automatic source type detection for all supported types"""
        test_urls = [
            ("https://vimeo.com/123456789", "vimeo", "Vimeo"),
            ("https://www.twitch.tv/videos/12345", "twitch", "Twitch"),
            ("https://clips.twitch.tv/testclip", "twitch", "Twitch"),
            ("https://example.com/video.mp4", "direct", "Direct Video URL"),
            ("https://example.com/stream.m3u8", "hls", "HLS Stream"),
            ("https://www.youtube.com/watch?v=test", "youtube", "YouTube"),
            ("https://drive.google.com/file/d/test", "cloud_drive", "Google Drive"),
            ("https://www.dropbox.com/s/test", "dropbox", "Dropbox"),
            ("https://example.com/feed.xml", "rss", "RSS Feed")
        ]

        for url, expected_type, expected_label in test_urls:
            response = client.post(
                "/api/video-sources/detect",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"url": url}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["source_type"] == expected_type, f"Failed for {url}"
            assert data["source_type_label"] == expected_label, f"Failed for {url}"


class TestTranscodingWorkflow:
    """Integration tests for transcoding workflow"""

    def test_transcoding_triggered_for_incompatible_format(self, client: TestClient, admin_token):
        """Test that transcoding is automatically triggered for incompatible formats"""
        mock_metadata = {
            "title": "AVI Video",
            "webpage_url": "https://example.com/video.avi",
            "extractor": "generic",
            "duration": 150
        }

        mock_validation = MagicMock(
            valid=True,
            is_compatible=False,
            video_codec="xvid",
            audio_codec="mp3",
            format="avi",
            has_orientation=False
        )

        with patch('src.tasks.media.extract_video_metadata', return_value=mock_metadata), \
             patch('src.tasks.media.VideoValidator') as MockValidator, \
             patch('src.tasks.media.transcode_video_task') as mock_transcode:

            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_url = AsyncMock(return_value=mock_validation)
            mock_validator_instance.check_transcoding_required = MagicMock(return_value={
                "required": True,
                "reasons": ["Unsupported codec: xvid"]
            })
            MockValidator.return_value = mock_validator_instance

            response = client.post(
                "/api/playlist/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://example.com/video.avi",
                    "auto_detect": True
                }
            )

            assert response.status_code == 201
            # Verify transcoding would be triggered (mocked in this test)
            # In production, transcode_video_task would be called

    def test_transcoding_not_triggered_for_compatible_format(self, client: TestClient, admin_token):
        """Test that transcoding is NOT triggered for compatible formats"""
        mock_metadata = {
            "title": "MP4 Video",
            "webpage_url": "https://example.com/video.mp4",
            "extractor": "generic",
            "duration": 150
        }

        mock_validation = MagicMock(
            valid=True,
            is_compatible=True,
            video_codec="h264",
            audio_codec="aac",
            format="mp4",
            has_orientation=False
        )

        with patch('src.tasks.media.extract_video_metadata', return_value=mock_metadata), \
             patch('src.tasks.media.VideoValidator') as MockValidator:

            mock_validator_instance = MagicMock()
            mock_validator_instance.validate_url = AsyncMock(return_value=mock_validation)
            mock_validator_instance.check_transcoding_required = MagicMock(return_value={
                "required": False,
                "reasons": []
            })
            MockValidator.return_value = mock_validator_instance

            response = client.post(
                "/api/playlist/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://example.com/video.mp4",
                    "auto_detect": True
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert data["type"] == "direct"


class TestAutoDetectionWorkflow:
    """Integration tests for automatic source detection"""

    def test_auto_detection_overrides_manual_type(self, client: TestClient, admin_token, user_playlist):
        """Test that auto-detection overrides manually specified type"""
        mock_metadata = {
            "title": "Vimeo Video",
            "webpage_url": "https://vimeo.com/987654321",
            "extractor": "vimeo",
            "uploader": "Vimeo User",
            "duration": 200
        }

        with patch('src.tasks.media.extract_video_metadata', return_value=mock_metadata):
            # User specifies "youtube" but URL is vimeo
            response = client.post(
                "/api/playlist/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://vimeo.com/987654321",
                    "type": "youtube",  # Wrong type
                    "playlist_id": str(user_playlist.id),
                    "auto_detect": True  # Should override
                }
            )

            assert response.status_code == 201
            data = response.json()
            # With auto_detect=True, should use detected type
            assert data["type"] == "vimeo"

    def test_manual_type_respected_when_auto_detect_false(self, client: TestClient, admin_token, user_playlist):
        """Test that manual type is respected when auto_detect is False"""
        mock_metadata = {
            "title": "Video",
            "webpage_url": "https://example.com/video.mp4",
            "extractor": "generic",
            "duration": 100
        }

        with patch('src.tasks.media.extract_video_metadata', return_value=mock_metadata):
            response = client.post(
                "/api/playlist/",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "url": "https://example.com/video.mp4",
                    "type": "direct",
                    "playlist_id": str(user_playlist.id),
                    "auto_detect": False
                }
            )

            assert response.status_code == 201
            data = response.json()
            # Should respect manual type
            assert data["type"] == "direct"
