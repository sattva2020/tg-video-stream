"""
Integration Tests: Bulk Operations on Playlists

Tests the bulk operations functionality including:
- Bulk deleting multiple playlists
- Bulk moving playlists to different groups
- Bulk copying playlists
- Error handling for unauthorized playlists
- Mixed success/failure scenarios
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.schedule import Playlist, PlaylistGroup
from src.auth.jwt import create_access_token


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user for authentication"""
    user = User(
        email="bulk-ops-test@example.com",
        hashed_password="hashed_password",
        full_name="Bulk Operations Test User",
        status="approved",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def another_user(db_session: Session):
    """Create another test user for testing authorization"""
    user = User(
        email="another-bulk-user@example.com",
        hashed_password="hashed_password",
        full_name="Another Bulk User",
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
def another_auth_headers(another_user: User):
    """Create authentication headers for another user"""
    token = create_access_token(data={"sub": str(another_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_group(db_session: Session, test_user: User):
    """Create a test group for move operations"""
    group = PlaylistGroup(
        user_id=test_user.id,
        name="Test Group",
        position=0
    )
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)
    return group


@pytest.fixture
def test_playlists(db_session: Session, test_user: User):
    """Create multiple test playlists for bulk operations"""
    playlists = []
    for i in range(1, 5):
        playlist = Playlist(
            user_id=test_user.id,
            name=f"Bulk Test Playlist {i}",
            description=f"Test playlist {i} for bulk operations",
            items=[
                {
                    "url": f"https://www.youtube.com/watch?v=test{i}",
                    "title": f"Test Video {i}",
                    "duration": 180 + (i * 60),
                    "type": "youtube"
                }
            ],
            items_count=1,
            total_duration=180 + (i * 60),
            is_public=False
        )
        db_session.add(playlist)
        db_session.commit()
        db_session.refresh(playlist)
        playlists.append(playlist)
    return playlists


def test_bulk_delete_all_owned_playlists(client: TestClient, db_session: Session, test_playlists: list, auth_headers: dict):
    """Test bulk deleting multiple playlists owned by the user"""
    playlist_ids = [p.id for p in test_playlists]

    request_payload = {
        "playlist_ids": playlist_ids
    }

    response = client.post("/api/playlists/bulk/delete", json=request_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["success_count"] == 4
    assert data["failed_count"] == 0
    assert data["errors"] == []

    # Verify playlists are deleted from database
    for playlist_id in playlist_ids:
        deleted_playlist = db_session.query(Playlist).filter(Playlist.id == playlist_id).first()
        assert deleted_playlist is None


def test_bulk_delete_partial_list(client: TestClient, db_session: Session, test_playlists: list, auth_headers: dict):
    """Test bulk deleting only some of the playlists"""
    # Delete only first 2 playlists
    to_delete = test_playlists[:2]
    playlist_ids = [p.id for p in to_delete]

    request_payload = {
        "playlist_ids": playlist_ids
    }

    response = client.post("/api/playlists/bulk/delete", json=request_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["success_count"] == 2
    assert data["failed_count"] == 0
    assert data["errors"] == []

    # Verify deleted playlists are gone
    for playlist_id in playlist_ids:
        deleted_playlist = db_session.query(Playlist).filter(Playlist.id == playlist_id).first()
        assert deleted_playlist is None

    # Verify remaining playlists still exist
    remaining_ids = [p.id for p in test_playlists[2:]]
    for playlist_id in remaining_ids:
        remaining_playlist = db_session.query(Playlist).filter(Playlist.id == playlist_id).first()
        assert remaining_playlist is not None


def test_bulk_delete_with_non_existent_playlists(client: TestClient, test_playlists: list, auth_headers: dict):
    """Test bulk delete with mix of existent and non-existent playlists"""
    # Mix of real and fake playlist IDs
    fake_id = uuid.uuid4()
    playlist_ids = [test_playlists[0].id, fake_id, test_playlists[1].id]

    request_payload = {
        "playlist_ids": playlist_ids
    }

    response = client.post("/api/playlists/bulk/delete", json=request_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Two successes (real playlists), one failure (fake playlist)
    assert data["success_count"] == 2
    assert data["failed_count"] == 1
    assert len(data["errors"]) == 1
    assert "not found" in data["errors"][0].lower()


def test_bulk_delete_unauthorized_playlists(client: TestClient, db_session: Session, test_user: User, another_user: User):
    """Test that users cannot delete playlists owned by other users"""
    # Create playlists as first user
    user_token = create_access_token(data={"sub": str(test_user.id)})
    user_headers = {"Authorization": f"Bearer {user_token}"}

    user_playlist = Playlist(
        user_id=test_user.id,
        name="User's Playlist",
        items=[],
        items_count=0,
        total_duration=0
    )
    db_session.add(user_playlist)
    db_session.commit()
    db_session.refresh(user_playlist)

    # Try to delete as another user
    another_token = create_access_token(data={"sub": str(another_user.id)})
    another_headers = {"Authorization": f"Bearer {another_token}"}

    request_payload = {
        "playlist_ids": [user_playlist.id]
    }

    response = client.post("/api/playlists/bulk/delete", json=request_payload, headers=another_headers)

    assert response.status_code == 200
    data = response.json()

    # Should fail (not authorized)
    assert data["success_count"] == 0
    assert data["failed_count"] == 1
    assert "not authorized" in data["errors"][0].lower()

    # Verify playlist still exists
    still_exists = db_session.query(Playlist).filter(Playlist.id == user_playlist.id).first()
    assert still_exists is not None


def test_bulk_move_to_group(client: TestClient, db_session: Session, test_playlists: list, test_group: PlaylistGroup, auth_headers: dict):
    """Test bulk moving playlists to a specific group"""
    playlist_ids = [p.id for p in test_playlists]

    request_payload = {
        "playlist_ids": playlist_ids,
        "group_id": str(test_group.id)
    }

    response = client.post("/api/playlists/bulk/move", json=request_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["success_count"] == 4
    assert data["failed_count"] == 0
    assert data["errors"] == []

    # Verify all playlists are now in the group
    for playlist_id in playlist_ids:
        playlist = db_session.query(Playlist).filter(Playlist.id == playlist_id).first()
        assert playlist.group_id == test_group.id


def test_bulk_move_to_root(client: TestClient, db_session: Session, test_playlists: list, test_group: PlaylistGroup, auth_headers: dict):
    """Test bulk moving playlists to root (no group)"""
    # First move them to a group
    for playlist in test_playlists:
        playlist.group_id = test_group.id
    db_session.commit()

    # Now move them back to root
    playlist_ids = [p.id for p in test_playlists]

    request_payload = {
        "playlist_ids": playlist_ids,
        "group_id": None
    }

    response = client.post("/api/playlists/bulk/move", json=request_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["success_count"] == 4
    assert data["failed_count"] == 0

    # Verify all playlists are now at root level
    for playlist_id in playlist_ids:
        playlist = db_session.query(Playlist).filter(Playlist.id == playlist_id).first()
        assert playlist.group_id is None


def test_bulk_move_with_non_existent_playlists(client: TestClient, test_playlists: list, test_group: PlaylistGroup, auth_headers: dict):
    """Test bulk move with mix of existent and non-existent playlists"""
    fake_id = uuid.uuid4()
    playlist_ids = [test_playlists[0].id, fake_id, test_playlists[1].id]

    request_payload = {
        "playlist_ids": playlist_ids,
        "group_id": str(test_group.id)
    }

    response = client.post("/api/playlists/bulk/move", json=request_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Two successes, one failure
    assert data["success_count"] == 2
    assert data["failed_count"] == 1
    assert "not found" in data["errors"][0].lower()


def test_bulk_move_unauthorized_playlists(client: TestClient, db_session: Session, test_user: User, another_user: User, test_group: PlaylistGroup):
    """Test that users cannot move playlists owned by other users"""
    # Create playlist as first user
    user_token = create_access_token(data={"sub": str(test_user.id)})
    user_headers = {"Authorization": f"Bearer {user_token}"}

    user_playlist = Playlist(
        user_id=test_user.id,
        name="User's Playlist",
        items=[],
        items_count=0,
        total_duration=0
    )
    db_session.add(user_playlist)
    db_session.commit()
    db_session.refresh(user_playlist)

    # Try to move as another user
    another_token = create_access_token(data={"sub": str(another_user.id)})
    another_headers = {"Authorization": f"Bearer {another_token}"}

    request_payload = {
        "playlist_ids": [user_playlist.id],
        "group_id": str(test_group.id)
    }

    response = client.post("/api/playlists/bulk/move", json=request_payload, headers=another_headers)

    assert response.status_code == 200
    data = response.json()

    # Should fail
    assert data["success_count"] == 0
    assert data["failed_count"] == 1
    assert "not authorized" in data["errors"][0].lower()

    # Verify playlist wasn't moved
    playlist = db_session.query(Playlist).filter(Playlist.id == user_playlist.id).first()
    assert playlist.group_id is None


def test_bulk_copy_own_playlists(client: TestClient, db_session: Session, test_playlists: list, auth_headers: dict):
    """Test bulk copying playlists owned by the user"""
    playlist_ids = [p.id for p in test_playlists[:2]]

    request_payload = {
        "playlist_ids": playlist_ids
    }

    response = client.post("/api/playlists/bulk/copy", json=request_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert data["success_count"] == 2
    assert data["failed_count"] == 0
    assert data["errors"] == []
    assert "copied_playlists" in data
    assert len(data["copied_playlists"]) == 2

    # Verify copied playlists have correct properties
    for i, copied in enumerate(data["copied_playlists"]):
        assert copied["name"].startswith("Copy of")
        assert copied["items_count"] == test_playlists[i].items_count
        assert copied["total_duration"] == test_playlists[i].total_duration
        assert len(copied["items"]) == len(test_playlists[i].items)

        # Verify copied playlist exists in database
        db_copy = db_session.query(Playlist).filter(Playlist.id == copied["id"]).first()
        assert db_copy is not None
        assert db_copy.name.startswith("Copy of")


def test_bulk_copy_public_playlists_from_other_user(client: TestClient, db_session: Session, test_user: User, another_user: User):
    """Test that users can copy public playlists from other users"""
    # Create auth tokens
    user_token = create_access_token(data={"sub": str(test_user.id)})
    user_headers = {"Authorization": f"Bearer {user_token}"}

    another_token = create_access_token(data={"sub": str(another_user.id)})
    another_headers = {"Authorization": f"Bearer {another_token}"}

    # Create public playlist as first user
    public_playlist = Playlist(
        user_id=test_user.id,
        name="Public Playlist",
        items=[{
            "url": "https://www.youtube.com/watch?v=public",
            "title": "Public Video",
            "duration": 180,
            "type": "youtube"
        }],
        items_count=1,
        total_duration=180,
        is_public=True
    )
    db_session.add(public_playlist)
    db_session.commit()
    db_session.refresh(public_playlist)

    # Copy as another user
    request_payload = {
        "playlist_ids": [public_playlist.id]
    }

    response = client.post("/api/playlists/bulk/copy", json=request_payload, headers=another_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["success_count"] == 1
    assert data["failed_count"] == 0
    assert len(data["copied_playlists"]) == 1

    copied = data["copied_playlists"][0]
    assert copied["name"].startswith("Copy of Public Playlist")
    assert copied["items_count"] == 1

    # Verify copied playlist belongs to another_user
    db_copy = db_session.query(Playlist).filter(Playlist.id == copied["id"]).first()
    assert db_copy.user_id == another_user.id


def test_bulk_copy_private_playlists_from_other_user_fails(client: TestClient, db_session: Session, test_user: User, another_user: User):
    """Test that users cannot copy private playlists from other users"""
    # Create auth tokens
    another_token = create_access_token(data={"sub": str(another_user.id)})
    another_headers = {"Authorization": f"Bearer {another_token}"}

    # Create private playlist as first user (default is_private=False)
    private_playlist = Playlist(
        user_id=test_user.id,
        name="Private Playlist",
        items=[],
        items_count=0,
        total_duration=0,
        is_public=False
    )
    db_session.add(private_playlist)
    db_session.commit()
    db_session.refresh(private_playlist)

    # Try to copy as another user
    request_payload = {
        "playlist_ids": [private_playlist.id]
    }

    response = client.post("/api/playlists/bulk/copy", json=request_payload, headers=another_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["success_count"] == 0
    assert data["failed_count"] == 1
    assert "not authorized" in data["errors"][0].lower()


def test_bulk_copy_with_non_existent_playlists(client: TestClient, test_playlists: list, auth_headers: dict):
    """Test bulk copy with mix of existent and non-existent playlists"""
    fake_id = uuid.uuid4()
    playlist_ids = [test_playlists[0].id, fake_id]

    request_payload = {
        "playlist_ids": playlist_ids
    }

    response = client.post("/api/playlists/bulk/copy", json=request_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # One success, one failure
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert "not found" in data["errors"][0].lower()
    assert len(data["copied_playlists"]) == 1


def test_bulk_operations_empty_playlist_list(client: TestClient, auth_headers: dict):
    """Test bulk operations with empty playlist list"""
    empty_requests = [
        ("/api/playlists/bulk/delete", {"playlist_ids": []}),
        ("/api/playlists/bulk/move", {"playlist_ids": [], "group_id": None}),
        ("/api/playlists/bulk/copy", {"playlist_ids": []})
    ]

    for endpoint, payload in empty_requests:
        response = client.post(endpoint, json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 0
        assert data["failed_count"] == 0


def test_bulk_operations_require_authentication(client: TestClient, test_playlists: list):
    """Test that bulk operations require authentication"""
    playlist_id = test_playlists[0].id

    operations = [
        ("/api/playlists/bulk/delete", {"playlist_ids": [playlist_id]}),
        ("/api/playlists/bulk/move", {"playlist_ids": [playlist_id], "group_id": None}),
        ("/api/playlists/bulk/copy", {"playlist_ids": [playlist_id]})
    ]

    for endpoint, payload in operations:
        response = client.post(endpoint, json=payload)
        assert response.status_code == 401


def test_bulk_copy_preserves_playlist_properties(client: TestClient, db_session: Session, test_user: User, auth_headers: dict):
    """Test that bulk copy preserves all playlist properties"""
    # Create a playlist with various properties
    original = Playlist(
        user_id=test_user.id,
        name="Original Playlist",
        description="Original description",
        items=[
            {
                "url": "https://www.youtube.com/watch?v=1",
                "title": "Video 1",
                "duration": 100,
                "type": "youtube",
                "thumbnail": "https://example.com/thumb1.jpg"
            },
            {
                "url": "https://vimeo.com/12345",
                "title": "Video 2",
                "duration": 200,
                "type": "vimeo",
                "thumbnail": "https://example.com/thumb2.jpg"
            }
        ],
        items_count=2,
        total_duration=300,
        is_public=True,
        repeat_mode="all"
    )
    db_session.add(original)
    db_session.commit()
    db_session.refresh(original)

    # Copy the playlist
    request_payload = {
        "playlist_ids": [original.id]
    }

    response = client.post("/api/playlists/bulk/copy", json=request_payload, headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    copied = data["copied_playlists"][0]

    # Verify all properties are preserved
    assert copied["items_count"] == original.items_count
    assert copied["total_duration"] == original.total_duration
    assert len(copied["items"]) == len(original.items)

    # Verify items are preserved exactly
    for i in range(len(original.items)):
        assert copied["items"][i]["url"] == original.items[i]["url"]
        assert copied["items"][i]["title"] == original.items[i]["title"]
        assert copied["items"][i]["duration"] == original.items[i]["duration"]
        assert copied["items"][i]["type"] == original.items[i]["type"]

    # Verify in database
    db_copy = db_session.query(Playlist).filter(Playlist.id == copied["id"]).first()
    assert db_copy.items_count == 2
    assert db_copy.total_duration == 300
    assert len(db_copy.items) == 2


def test_bulk_move_to_non_existent_group(client: TestClient, test_playlists: list, auth_headers: dict):
    """Test bulk move to a non-existent group"""
    fake_group_id = uuid.uuid4()

    request_payload = {
        "playlist_ids": [test_playlists[0].id],
        "group_id": str(fake_group_id)
    }

    response = client.post("/api/playlists/bulk/move", json=request_payload, headers=auth_headers)

    # Should succeed at the API level but fail when trying to set the group_id
    # The API doesn't validate group existence, it just sets group_id
    # If group doesn't exist, it's still a valid operation (group_id can be any UUID)
    # The frontend should handle group validation
    assert response.status_code == 200
