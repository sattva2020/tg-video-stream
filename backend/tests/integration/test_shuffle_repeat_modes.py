"""
Integration Tests: Shuffle and Repeat Modes

Tests the playlist shuffle and repeat functionality including:
- Creating playlists with shuffle mode enabled
- Creating playlists with repeat modes (none, one, all)
- Updating playlist shuffle mode
- Updating playlist repeat mode
- Verifying shuffle and repeat modes are persisted correctly
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.schedule import Playlist, PlaylistRepeatMode
from src.auth.jwt import create_access_token
import uuid


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user for authentication"""
    user = User(
        email="shuffle-test@example.com",
        hashed_password="hashed_password",
        full_name="Shuffle Test User",
        status="approved",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User):
    """Create authentication headers for test user"""
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_playlist_items():
    """Create sample playlist items for testing"""
    return [
        {"url": "https://www.youtube.com/watch?v=video1", "title": "Video 1", "duration": 180, "type": "youtube"},
        {"url": "https://www.youtube.com/watch?v=video2", "title": "Video 2", "duration": 240, "type": "youtube"},
        {"url": "https://www.youtube.com/watch?v=video3", "title": "Video 3", "duration": 300, "type": "youtube"},
        {"url": "https://vimeo.com/12345", "title": "Vimeo Video", "duration": 200, "type": "vimeo"},
    ]


def test_create_playlist_with_shuffle_enabled(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test creating a playlist with shuffle mode enabled"""
    playlist_payload = {
        "name": "Shuffled Playlist",
        "description": "This playlist should be shuffled during playback",
        "is_shuffled": True,
        "items": sample_playlist_items
    }

    response = client.post("/api/schedule/playlists", json=playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["is_shuffled"] is True
    assert data["name"] == "Shuffled Playlist"
    assert data["items_count"] == 4

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(data["id"])).first()
    assert playlist is not None
    assert playlist.is_shuffled is True


def test_create_playlist_with_shuffle_disabled(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test creating a playlist with shuffle mode disabled (default)"""
    playlist_payload = {
        "name": "Ordered Playlist",
        "description": "This playlist should play in order",
        "is_shuffled": False,
        "items": sample_playlist_items
    }

    response = client.post("/api/schedule/playlists", json=playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["is_shuffled"] is False
    assert data["name"] == "Ordered Playlist"

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(data["id"])).first()
    assert playlist is not None
    assert playlist.is_shuffled is False


def test_create_playlist_with_repeat_none(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test creating a playlist with repeat mode NONE (default)"""
    playlist_payload = {
        "name": "No Repeat Playlist",
        "repeat_mode": "none",
        "items": sample_playlist_items
    }

    response = client.post("/api/schedule/playlists", json=playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["repeat_mode"] == "none"

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(data["id"])).first()
    assert playlist is not None
    assert playlist.repeat_mode == PlaylistRepeatMode.NONE


def test_create_playlist_with_repeat_one(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test creating a playlist with repeat mode ONE"""
    playlist_payload = {
        "name": "Repeat One Playlist",
        "description": "This playlist should repeat the current item",
        "repeat_mode": "one",
        "items": sample_playlist_items
    }

    response = client.post("/api/schedule/playlists", json=playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["repeat_mode"] == "one"

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(data["id"])).first()
    assert playlist is not None
    assert playlist.repeat_mode == PlaylistRepeatMode.ONE


def test_create_playlist_with_repeat_all(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test creating a playlist with repeat mode ALL"""
    playlist_payload = {
        "name": "Repeat All Playlist",
        "description": "This playlist should loop continuously",
        "repeat_mode": "all",
        "items": sample_playlist_items
    }

    response = client.post("/api/schedule/playlists", json=playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["repeat_mode"] == "all"

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(data["id"])).first()
    assert playlist is not None
    assert playlist.repeat_mode == PlaylistRepeatMode.ALL


def test_update_playlist_shuffle_mode(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test updating playlist shuffle mode"""
    # Create playlist without shuffle
    create_payload = {
        "name": "Test Playlist",
        "is_shuffled": False,
        "items": sample_playlist_items
    }
    create_response = client.post("/api/schedule/playlists", json=create_payload, headers=auth_headers)
    playlist_id = create_response.json()["id"]

    # Update to enable shuffle
    update_payload = {
        "is_shuffled": True
    }
    response = client.put(f"/api/schedule/playlists/{playlist_id}", json=update_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["is_shuffled"] is True

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(playlist_id)).first()
    assert playlist is not None
    assert playlist.is_shuffled is True


def test_update_playlist_repeat_mode_to_one(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test updating playlist repeat mode to ONE"""
    # Create playlist with repeat none
    create_payload = {
        "name": "Test Playlist",
        "repeat_mode": "none",
        "items": sample_playlist_items
    }
    create_response = client.post("/api/schedule/playlists", json=create_payload, headers=auth_headers)
    playlist_id = create_response.json()["id"]

    # Update to repeat one
    update_payload = {
        "repeat_mode": "one"
    }
    response = client.put(f"/api/schedule/playlists/{playlist_id}", json=update_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["repeat_mode"] == "one"

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(playlist_id)).first()
    assert playlist is not None
    assert playlist.repeat_mode == PlaylistRepeatMode.ONE


def test_update_playlist_repeat_mode_to_all(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test updating playlist repeat mode to ALL"""
    # Create playlist with repeat none
    create_payload = {
        "name": "Test Playlist",
        "repeat_mode": "none",
        "items": sample_playlist_items
    }
    create_response = client.post("/api/schedule/playlists", json=create_payload, headers=auth_headers)
    playlist_id = create_response.json()["id"]

    # Update to repeat all
    update_payload = {
        "repeat_mode": "all"
    }
    response = client.put(f"/api/schedule/playlists/{playlist_id}", json=update_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["repeat_mode"] == "all"

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(playlist_id)).first()
    assert playlist is not None
    assert playlist.repeat_mode == PlaylistRepeatMode.ALL


def test_update_playlist_both_shuffle_and_repeat(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test updating both shuffle and repeat mode together"""
    # Create playlist with defaults
    create_payload = {
        "name": "Test Playlist",
        "is_shuffled": False,
        "repeat_mode": "none",
        "items": sample_playlist_items
    }
    create_response = client.post("/api/schedule/playlists", json=create_payload, headers=auth_headers)
    playlist_id = create_response.json()["id"]

    # Update both shuffle and repeat
    update_payload = {
        "is_shuffled": True,
        "repeat_mode": "all"
    }
    response = client.put(f"/api/schedule/playlists/{playlist_id}", json=update_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["is_shuffled"] is True
    assert data["repeat_mode"] == "all"

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(playlist_id)).first()
    assert playlist is not None
    assert playlist.is_shuffled is True
    assert playlist.repeat_mode == PlaylistRepeatMode.ALL


def test_get_playlist_returns_shuffle_and_repeat(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test that GET endpoint returns shuffle and repeat mode"""
    # Create playlist with both shuffle and repeat
    create_payload = {
        "name": "Full Feature Playlist",
        "is_shuffled": True,
        "repeat_mode": "all",
        "items": sample_playlist_items
    }
    create_response = client.post("/api/schedule/playlists", json=create_payload, headers=auth_headers)
    playlist_id = create_response.json()["id"]

    # Get playlist
    response = client.get(f"/api/schedule/playlists/{playlist_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["is_shuffled"] is True
    assert data["repeat_mode"] == "all"
    assert data["items_count"] == 4


def test_list_playlists_includes_shuffle_and_repeat(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test that playlist list endpoint includes shuffle and repeat modes"""
    # Create multiple playlists with different settings
    playlists = [
        {"name": "Shuffled None", "is_shuffled": True, "repeat_mode": "none", "items": sample_playlist_items},
        {"name": "Ordered One", "is_shuffled": False, "repeat_mode": "one", "items": sample_playlist_items},
        {"name": "Shuffled All", "is_shuffled": True, "repeat_mode": "all", "items": sample_playlist_items},
    ]

    for playlist in playlists:
        client.post("/api/schedule/playlists", json=playlist, headers=auth_headers)

    # List playlists
    response = client.get("/api/schedule/playlists", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3

    # Verify shuffle and repeat are in response
    for playlist in data[:3]:
        assert "is_shuffled" in playlist
        assert "repeat_mode" in playlist


def test_invalid_repeat_mode_is_rejected(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test that invalid repeat mode is rejected"""
    playlist_payload = {
        "name": "Invalid Playlist",
        "repeat_mode": "invalid_mode",
        "items": sample_playlist_items
    }

    response = client.post("/api/schedule/playlists", json=playlist_payload, headers=auth_headers)

    # Should return 422 validation error
    assert response.status_code == 422


def test_default_shuffle_and_repeat_values(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test that default values for shuffle and repeat are correct"""
    playlist_payload = {
        "name": "Default Values Playlist",
        "items": sample_playlist_items
    }

    response = client.post("/api/schedule/playlists", json=playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()
    assert data["is_shuffled"] is False  # Default should be False
    assert data["repeat_mode"] == "none"  # Default should be none


def test_update_shuffle_to_false(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test updating shuffle from True to False"""
    # Create with shuffle enabled
    create_payload = {
        "name": "Test Playlist",
        "is_shuffled": True,
        "items": sample_playlist_items
    }
    create_response = client.post("/api/schedule/playlists", json=create_payload, headers=auth_headers)
    playlist_id = create_response.json()["id"]

    # Update to disable shuffle
    update_payload = {
        "is_shuffled": False
    }
    response = client.put(f"/api/schedule/playlists/{playlist_id}", json=update_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["is_shuffled"] is False

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(playlist_id)).first()
    assert playlist is not None
    assert playlist.is_shuffled is False


def test_update_repeat_mode_from_all_to_none(client: TestClient, db_session: Session, auth_headers: dict, sample_playlist_items: list):
    """Test updating repeat mode from ALL to NONE"""
    # Create with repeat all
    create_payload = {
        "name": "Test Playlist",
        "repeat_mode": "all",
        "items": sample_playlist_items
    }
    create_response = client.post("/api/schedule/playlists", json=create_payload, headers=auth_headers)
    playlist_id = create_response.json()["id"]

    # Update to repeat none
    update_payload = {
        "repeat_mode": "none"
    }
    response = client.put(f"/api/schedule/playlists/{playlist_id}", json=update_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["repeat_mode"] == "none"

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == uuid.UUID(playlist_id)).first()
    assert playlist is not None
    assert playlist.repeat_mode == PlaylistRepeatMode.NONE
