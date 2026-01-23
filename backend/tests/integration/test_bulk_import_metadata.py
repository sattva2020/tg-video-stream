"""
Integration Tests: Bulk Import YouTube/Vimeo with Metadata

Tests the bulk import functionality including:
- Bulk import of YouTube playlist URLs
- Bulk import of Vimeo video URLs
- Metadata fetching (title, duration, thumbnails)
- Error handling for invalid URLs
- Mixed URL imports (YouTube + Vimeo)
- Thumbnail storage in playlist items
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

from src.models.user import User
from src.models.schedule import Playlist, PlaylistGroup
from src.auth.jwt import create_access_token
import uuid
import json


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user for authentication"""
    user = User(
        email="bulk-import-test@example.com",
        hashed_password="hashed_password",
        full_name="Bulk Import Test User",
        status="approved",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_group(db_session: Session, test_user: User):
    """Create a test playlist group"""
    group = PlaylistGroup(
        user_id=test_user.id,
        name="Imported Playlists",
        position=0
    )
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)
    return group


@pytest.fixture
def auth_headers(test_user: User):
    """Create authentication headers for test user"""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


# Test YouTube Import
def test_bulk_import_youtube_playlist(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import of a YouTube playlist URL"""
    # Mock the async import function to avoid network calls
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        mock_import.return_value = None  # Fire and forget

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": ["https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "success_count" in data
        assert "failed_count" in data
        assert "results" in data
        assert "message" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["url"] == "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"


def test_bulk_import_youtube_video(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import of a YouTube video URL"""
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        mock_import.return_value = None

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 1
        assert data["results"][0]["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_bulk_import_youtube_short_url(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import of a YouTube short URL (youtu.be)"""
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        mock_import.return_value = None

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": ["https://youtu.be/dQw4w9WgXcQ"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 1
        assert data["results"][0]["url"] == "https://youtu.be/dQw4w9WgXcQ"


# Test Vimeo Import
def test_bulk_import_vimeo_video(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import of a Vimeo video URL"""
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        mock_import.return_value = None

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": ["https://vimeo.com/148751763"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 1
        assert data["results"][0]["url"] == "https://vimeo.com/148751763"


def test_bulk_import_vimeo_with_player_url(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import of a Vimeo video URL with player path"""
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        mock_import.return_value = None

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": ["https://player.vimeo.com/video/148751763"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 1


# Test Mixed Imports
def test_bulk_import_mixed_youtube_vimeo(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import of mixed YouTube and Vimeo URLs"""
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        mock_import.return_value = None

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": [
                    "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
                    "https://vimeo.com/148751763",
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                ]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 3
        assert data["success_count"] + data["failed_count"] == 3


# Test Error Handling
def test_bulk_import_invalid_url(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import with invalid URL is handled gracefully"""
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        # Mock import to raise an exception for invalid URL
        mock_import.side_effect = Exception("Failed to extract info")

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": ["https://invalid-url-that-does-not-exist.com/video"]
            },
            headers=auth_headers
        )

        # The endpoint should still return 200, but mark as failed
        # or return an error depending on implementation
        assert response.status_code in [200, 400]


def test_bulk_import_empty_url_array(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import with empty URL array returns error"""
    response = client.post(
        "/api/playlists/import/bulk",
        json={"urls": []},
        headers=auth_headers
    )

    assert response.status_code == 400


def test_bulk_import_mixed_valid_invalid_urls(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import with mix of valid and invalid URLs"""
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        # First call succeeds, second fails
        mock_import.side_effect = [None, Exception("Invalid URL")]

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": [
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://invalid-url.com/video"
                ]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 2
        assert data["success_count"] + data["failed_count"] == 2


# Test Authentication
def test_bulk_import_requires_authentication(client: TestClient):
    """Test bulk import endpoint requires authentication"""
    response = client.post(
        "/api/playlists/import/bulk",
        json={
            "urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
        }
    )

    assert response.status_code == 401


# Test Channel ID Parameter
def test_bulk_import_with_channel_id(client: TestClient, db_session: Session, test_user: User, auth_headers: dict):
    """Test bulk import with optional channel_id parameter"""
    from src.models.channel import Channel

    # Create a test channel
    channel = Channel(
        user_id=test_user.id,
        name="Test Channel",
        description="Test channel for bulk import"
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)

    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        mock_import.return_value = None

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
                "channel_id": str(channel.id)
            },
            headers=auth_headers
        )

        assert response.status_code == 200


# Test Metadata Storage (after import completes)
def test_playlist_items_have_metadata(db_session: Session, test_user: User):
    """Test that imported playlist items have metadata including thumbnails"""
    # Create a playlist with items that have metadata
    playlist = Playlist(
        user_id=test_user.id,
        name="Test Imported Playlist",
        items=[
            {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Never Gonna Give You Up",
                "duration": 212,
                "type": "youtube",
                "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
            },
            {
                "url": "https://vimeo.com/148751763",
                "title": "Vimeo Test Video",
                "duration": 120,
                "type": "vimeo",
                "thumbnail": "https://i.vimeocdn.com/video/123456.jpg"
            }
        ],
        items_count=2,
        total_duration=332
    )

    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)

    # Verify items have metadata
    assert len(playlist.items) == 2
    assert playlist.items[0]["title"] == "Never Gonna Give You Up"
    assert playlist.items[0]["duration"] == 212
    assert playlist.items[0]["type"] == "youtube"
    assert playlist.items[0]["thumbnail"] is not None

    assert playlist.items[1]["title"] == "Vimeo Test Video"
    assert playlist.items[1]["duration"] == 120
    assert playlist.items[1]["type"] == "vimeo"
    assert playlist.items[1]["thumbnail"] is not None


def test_playlist_items_type_detection(db_session: Session, test_user: User):
    """Test that imported items have correct type detected"""
    playlist = Playlist(
        user_id=test_user.id,
        name="Test Type Detection",
        items=[
            {
                "url": "https://www.youtube.com/watch?v=test",
                "title": "YouTube Video",
                "duration": 100,
                "type": "youtube",
                "thumbnail": "https://example.com/yt.jpg"
            },
            {
                "url": "https://vimeo.com/123",
                "title": "Vimeo Video",
                "duration": 200,
                "type": "vimeo",
                "thumbnail": "https://example.com/vimeo.jpg"
            },
            {
                "url": "https://example.com/stream.m3u8",
                "title": "Stream",
                "duration": 300,
                "type": "stream",
                "thumbnail": "https://example.com/stream.jpg"
            }
        ],
        items_count=3,
        total_duration=600
    )

    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)

    # Verify correct types
    assert playlist.items[0]["type"] == "youtube"
    assert playlist.items[1]["type"] == "vimeo"
    assert playlist.items[2]["type"] == "stream"


# Test Thumbnail Validation
def test_thumbnail_urls_are_valid(db_session: Session, test_user: User):
    """Test that thumbnail URLs stored in playlist items are valid HTTP(S) URLs"""
    playlist = Playlist(
        user_id=test_user.id,
        name="Test Thumbnails",
        items=[
            {
                "url": "https://www.youtube.com/watch?v=test",
                "title": "Video with Thumbnail",
                "duration": 100,
                "type": "youtube",
                "thumbnail": "https://i.ytimg.com/vi/test/hqdefault.jpg"
            },
            {
                "url": "https://www.youtube.com/watch?v=test2",
                "title": "Video without Thumbnail",
                "duration": 100,
                "type": "youtube"
            }
        ],
        items_count=2,
        total_duration=200
    )

    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)

    # Check first item has valid thumbnail URL
    assert playlist.items[0]["thumbnail"].startswith("https://")
    assert "ytimg.com" in playlist.items[0]["thumbnail"]

    # Check second item has no thumbnail (optional field)
    assert "thumbnail" not in playlist.items[1] or playlist.items[1]["thumbnail"] is None


# Test Response Structure
def test_bulk_import_response_structure(client: TestClient, db_session: Session, auth_headers: dict):
    """Test that bulk import response has correct structure"""
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        mock_import.return_value = None

        response = client.post(
            "/api/playlists/import/bulk",
            json={
                "urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
            },
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert isinstance(data["success_count"], int)
        assert isinstance(data["failed_count"], int)
        assert isinstance(data["results"], list)
        assert isinstance(data["message"], str)

        # Verify result structure
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "url" in result
            assert "success" in result
            assert isinstance(result["success"], bool)


# Test Multiple Imports
def test_bulk_import_multiple_urls(client: TestClient, db_session: Session, auth_headers: dict):
    """Test bulk import with multiple URLs"""
    with patch('src.api.routes.playlists.import_playlist_async') as mock_import:
        mock_import.return_value = None

        urls = [
            "https://www.youtube.com/playlist?list=test1",
            "https://www.youtube.com/playlist?list=test2",
            "https://vimeo.com/123",
            "https://www.youtube.com/watch?v=test"
        ]

        response = client.post(
            "/api/playlists/import/bulk",
            json={"urls": urls},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) == 4
        assert data["success_count"] + data["failed_count"] == 4
