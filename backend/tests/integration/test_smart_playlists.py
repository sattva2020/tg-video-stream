"""
Integration Tests: Smart Playlists

Tests the smart playlist functionality including:
- Creating smart playlists with criteria
- Filtering by duration, type, title
- Sorting and limiting results
- Refreshing smart playlists
- Public/private access control
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.schedule import SmartPlaylist, Playlist
from src.auth.jwt import create_access_token
import uuid


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user for authentication"""
    user = User(
        email="smart-test@example.com",
        hashed_password="hashed_password",
        full_name="Smart Playlist Test User",
        status="approved",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def another_user(db_session: Session):
    """Create another test user for testing public smart playlists"""
    user = User(
        email="another-smart-user@example.com",
        hashed_password="hashed_password",
        full_name="Another Smart User",
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
def sample_playlists(db_session: Session, test_user: User):
    """Create sample playlists with various items for testing"""
    items_short = [
        {"url": "https://www.youtube.com/watch?v=short1", "title": "Short Video 1", "duration": 120, "type": "youtube"},
        {"url": "https://www.youtube.com/watch?v=short2", "title": "Short Video 2", "duration": 150, "type": "youtube"},
    ]

    items_medium = [
        {"url": "https://www.youtube.com/watch?v=med1", "title": "Medium Video 1", "duration": 300, "type": "youtube"},
        {"url": "https://www.youtube.com/watch?v=med2", "title": "Medium Video 2", "duration": 400, "type": "youtube"},
    ]

    items_long = [
        {"url": "https://www.youtube.com/watch?v=long1", "title": "Long Video 1", "duration": 600, "type": "youtube"},
        {"url": "https://www.youtube.com/watch?v=long2", "title": "Long Video 2", "duration": 900, "type": "youtube"},
    ]

    items_vimeo = [
        {"url": "https://vimeo.com/123456", "title": "Vimeo Video", "duration": 250, "type": "vimeo"},
    ]

    playlist1 = Playlist(
        user_id=test_user.id,
        name="Short Videos",
        items=items_short,
        items_count=len(items_short),
        total_duration=sum(item["duration"] for item in items_short)
    )

    playlist2 = Playlist(
        user_id=test_user.id,
        name="Medium Videos",
        items=items_medium,
        items_count=len(items_medium),
        total_duration=sum(item["duration"] for item in items_medium)
    )

    playlist3 = Playlist(
        user_id=test_user.id,
        name="Long Videos",
        items=items_long,
        items_count=len(items_long),
        total_duration=sum(item["duration"] for item in items_long)
    )

    playlist4 = Playlist(
        user_id=test_user.id,
        name="Vimeo Videos",
        items=items_vimeo,
        items_count=len(items_vimeo),
        total_duration=sum(item["duration"] for item in items_vimeo)
    )

    db_session.add_all([playlist1, playlist2, playlist3, playlist4])
    db_session.commit()
    db_session.refresh_all([playlist1, playlist2, playlist3, playlist4])

    return [playlist1, playlist2, playlist3, playlist4]


def test_create_smart_playlist_with_duration_criteria(client: TestClient, db_session: Session, auth_headers: dict, sample_playlists: list):
    """Test creating a smart playlist with duration filtering"""
    criteria = {
        "filters": {
            "duration_min": 200,
            "duration_max": 500
        },
        "order_by": "duration",
        "order_direction": "asc"
    }

    smart_playlist_payload = {
        "name": "Medium Length Videos",
        "description": "Videos between 200-500 seconds",
        "criteria": criteria,
        "is_public": False
    }

    response = client.post("/api/playlists/smart", json=smart_playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert data["name"] == "Medium Length Videos"
    assert data["description"] == "Videos between 200-500 seconds"
    assert data["criteria"] == criteria
    assert data["is_public"] is False
    assert "items_count" in data
    assert "total_duration" in data
    assert "created_at" in data

    # Verify smart playlist in database
    smart_playlist = db_session.query(SmartPlaylist).filter(SmartPlaylist.id == data["id"]).first()
    assert smart_playlist is not None
    assert smart_playlist.name == "Medium Length Videos"
    assert smart_playlist.playlist_id is not None  # Should have generated playlist

    # Verify generated playlist
    generated_playlist = db_session.query(Playlist).filter(Playlist.id == smart_playlist.playlist_id).first()
    assert generated_playlist is not None
    # Should include medium videos (300, 400) and vimeo (250) = 3 items
    assert generated_playlist.items_count == 3
    assert all(200 <= item["duration"] <= 500 for item in generated_playlist.items)


def test_create_smart_playlist_with_type_filter(client: TestClient, db_session: Session, auth_headers: dict, sample_playlists: list):
    """Test creating a smart playlist that filters by media type"""
    criteria = {
        "filters": {
            "type": "youtube"
        }
    }

    smart_playlist_payload = {
        "name": "YouTube Only",
        "description": "Only YouTube videos",
        "criteria": criteria
    }

    response = client.post("/api/playlists/smart", json=smart_playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    # Verify generated playlist
    smart_playlist = db_session.query(SmartPlaylist).filter(SmartPlaylist.id == data["id"]).first()
    generated_playlist = db_session.query(Playlist).filter(Playlist.id == smart_playlist.playlist_id).first()

    # Should have 6 YouTube videos (2 short + 2 medium + 2 long)
    assert generated_playlist.items_count == 6
    assert all(item["type"] == "youtube" for item in generated_playlist.items)


def test_create_smart_playlist_with_title_filter(client: TestClient, db_session: Session, auth_headers: dict, sample_playlists: list):
    """Test creating a smart playlist that filters by title"""
    criteria = {
        "filters": {
            "title_contains": "Video 1"
        }
    }

    smart_playlist_payload = {
        "name": "Numbered Videos",
        "criteria": criteria
    }

    response = client.post("/api/playlists/smart", json=smart_playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    # Verify generated playlist
    smart_playlist = db_session.query(SmartPlaylist).filter(SmartPlaylist.id == data["id"]).first()
    generated_playlist = db_session.query(Playlist).filter(Playlist.id == smart_playlist.playlist_id).first()

    # Should have 3 items with "Video 1" in title
    assert generated_playlist.items_count == 3
    assert all("Video 1" in item["title"] for item in generated_playlist.items)


def test_smart_playlist_sorting(client: TestClient, db_session: Session, auth_headers: dict, sample_playlists: list):
    """Test smart playlist sorting by duration"""
    criteria = {
        "filters": {},
        "order_by": "duration",
        "order_direction": "desc"
    }

    smart_playlist_payload = {
        "name": "Longest First",
        "criteria": criteria
    }

    response = client.post("/api/playlists/smart", json=smart_playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    # Verify sorting
    smart_playlist = db_session.query(SmartPlaylist).filter(SmartPlaylist.id == data["id"]).first()
    generated_playlist = db_session.query(Playlist).filter(Playlist.id == smart_playlist.playlist_id).first()

    # Check items are sorted by duration descending
    durations = [item["duration"] for item in generated_playlist.items]
    assert durations == sorted(durations, reverse=True)


def test_smart_playlist_limit(client: TestClient, db_session: Session, auth_headers: dict, sample_playlists: list):
    """Test smart playlist item limit"""
    criteria = {
        "filters": {},
        "limit": 3
    }

    smart_playlist_payload = {
        "name": "Top 3",
        "criteria": criteria
    }

    response = client.post("/api/playlists/smart", json=smart_playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    # Verify limit
    smart_playlist = db_session.query(SmartPlaylist).filter(SmartPlaylist.id == data["id"]).first()
    generated_playlist = db_session.query(Playlist).filter(Playlist.id == smart_playlist.playlist_id).first()

    # Should have exactly 3 items
    assert generated_playlist.items_count == 3
    assert len(generated_playlist.items) == 3


def test_smart_playlist_shuffle(client: TestClient, db_session: Session, auth_headers: dict, sample_playlists: list):
    """Test smart playlist with shuffle enabled"""
    criteria = {
        "filters": {},
        "shuffle": True
    }

    smart_playlist_payload = {
        "name": "Shuffled Playlist",
        "criteria": criteria
    }

    response = client.post("/api/playlists/smart", json=smart_playlist_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    # Verify shuffle (just check it's created, randomness is hard to test)
    smart_playlist = db_session.query(SmartPlaylist).filter(SmartPlaylist.id == data["id"]).first()
    generated_playlist = db_session.query(Playlist).filter(Playlist.id == smart_playlist.playlist_id).first()

    # Should have all items
    assert generated_playlist.items_count == 7  # All items from sample playlists


def test_refresh_smart_playlist(client: TestClient, db_session: Session, auth_headers: dict, sample_playlists: list):
    """Test refreshing an existing smart playlist"""
    # Create initial smart playlist
    criteria = {
        "filters": {
            "duration_min": 0
        },
        "limit": 5
    }

    create_payload = {
        "name": "First 5 Videos",
        "criteria": criteria
    }

    create_response = client.post("/api/playlists/smart", json=create_payload, headers=auth_headers)
    smart_playlist_id = create_response.json()["id"]
    playlist_id = create_response.json()["playlist_id"]

    # Add a new playlist to the database
    new_items = [
        {"url": "https://www.youtube.com/watch?v=new1", "title": "New Video 1", "duration": 100, "type": "youtube"},
        {"url": "https://www.youtube.com/watch?v=new2", "title": "New Video 2", "duration": 200, "type": "youtube"},
    ]
    new_playlist = Playlist(
        user_id=sample_playlists[0].user_id,
        name="New Playlist",
        items=new_items,
        items_count=len(new_items),
        total_duration=sum(item["duration"] for item in new_items)
    )
    db_session.add(new_playlist)
    db_session.commit()

    # Refresh smart playlist
    refresh_response = client.post(
        f"/api/playlists/smart/{smart_playlist_id}/refresh",
        headers=auth_headers
    )

    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()

    # Verify refreshed data
    assert refreshed["id"] == str(playlist_id)
    # Now should have more items since we added a new playlist
    assert refreshed["items_count"] >= 5


def test_update_smart_playlist_criteria(client: TestClient, db_session: Session, auth_headers: dict, sample_playlists: list):
    """Test updating smart playlist criteria"""
    # Create with initial criteria
    criteria = {
        "filters": {
            "duration_min": 0
        }
    }

    create_payload = {
        "name": "All Videos",
        "criteria": criteria
    }

    create_response = client.post("/api/playlists/smart", json=create_payload, headers=auth_headers)
    smart_playlist_id = create_response.json()["id"]

    # Update criteria
    new_criteria = {
        "filters": {
            "duration_min": 500
        },
        "order_by": "duration",
        "order_direction": "desc"
    }

    update_payload = {
        "name": "Long Videos Only",
        "criteria": new_criteria
    }

    update_response = client.put(
        f"/api/playlists/smart/{smart_playlist_id}",
        json=update_payload,
        headers=auth_headers
    )

    assert update_response.status_code == 200
    updated = update_response.json()

    assert updated["name"] == "Long Videos Only"
    assert updated["criteria"] == new_criteria

    # Refresh to apply new criteria
    refresh_response = client.post(
        f"/api/playlists/smart/{smart_playlist_id}/refresh",
        headers=auth_headers
    )

    # Verify only long videos included
    smart_playlist = db_session.query(SmartPlaylist).filter(SmartPlaylist.id == smart_playlist_id).first()
    generated_playlist = db_session.query(Playlist).filter(Playlist.id == smart_playlist.playlist_id).first()

    assert all(item["duration"] >= 500 for item in generated_playlist.items)


def test_delete_smart_playlist(client: TestClient, db_session: Session, auth_headers: dict):
    """Test deleting a smart playlist"""
    criteria = {
        "filters": {
            "duration_min": 0
        }
    }

    create_payload = {
        "name": "To Be Deleted",
        "criteria": criteria
    }

    create_response = client.post("/api/playlists/smart", json=create_payload, headers=auth_headers)
    smart_playlist_id = create_response.json()["id"]
    playlist_id = create_response.json()["playlist_id"]

    # Delete smart playlist
    delete_response = client.delete(
        f"/api/playlists/smart/{smart_playlist_id}",
        headers=auth_headers
    )

    assert delete_response.status_code == 200

    # Verify smart playlist is deleted
    smart_playlist = db_session.query(SmartPlaylist).filter(SmartPlaylist.id == smart_playlist_id).first()
    assert smart_playlist is None

    # Verify linked playlist is also deleted
    linked_playlist = db_session.query(Playlist).filter(Playlist.id == playlist_id).first()
    assert linked_playlist is None


def test_clone_smart_playlist(client: TestClient, auth_headers: dict):
    """Test cloning a smart playlist"""
    criteria = {
        "filters": {
            "type": "youtube"
        }
    }

    create_payload = {
        "name": "Original Smart Playlist",
        "description": "To be cloned",
        "criteria": criteria
    }

    create_response = client.post("/api/playlists/smart", json=create_payload, headers=auth_headers)
    original_id = create_response.json()["id"]

    # Clone the smart playlist
    clone_response = client.post(
        f"/api/playlists/smart/{original_id}/clone",
        headers=auth_headers
    )

    assert clone_response.status_code == 200
    cloned = clone_response.json()

    # Verify clone properties
    assert cloned["name"] == "Copy of Original Smart Playlist"
    assert cloned["description"] == "To be cloned"
    assert cloned["criteria"] == criteria
    assert cloned["is_public"] is False  # Clones are private by default
    assert cloned["id"] != original_id


def test_get_user_smart_playlists(client: TestClient, auth_headers: dict):
    """Test fetching all smart playlists for a user"""
    # Create two smart playlists
    criteria1 = {"filters": {"duration_min": 100}}
    criteria2 = {"filters": {"duration_min": 200}}

    payload1 = {"name": "Smart 1", "criteria": criteria1}
    payload2 = {"name": "Smart 2", "criteria": criteria2}

    client.post("/api/playlists/smart", json=payload1, headers=auth_headers)
    client.post("/api/playlists/smart", json=payload2, headers=auth_headers)

    # Fetch smart playlists
    response = client.get("/api/playlists/smart", headers=auth_headers)

    assert response.status_code == 200
    smart_playlists = response.json()

    # Should have at least 2 smart playlists
    assert len(smart_playlists) >= 2

    # Verify our playlists are in the list
    playlist_names = [p["name"] for p in smart_playlists]
    assert "Smart 1" in playlist_names
    assert "Smart 2" in playlist_names


def test_get_smart_playlist_by_id(client: TestClient, auth_headers: dict):
    """Test fetching a single smart playlist by ID"""
    criteria = {"filters": {"duration_min": 0}}

    payload = {"name": "Test Smart Playlist", "criteria": criteria}

    create_response = client.post("/api/playlists/smart", json=payload, headers=auth_headers)
    smart_playlist_id = create_response.json()["id"]

    # Fetch the smart playlist
    response = client.get(f"/api/playlists/smart/{smart_playlist_id}", headers=auth_headers)

    assert response.status_code == 200
    smart_playlist = response.json()

    assert smart_playlist["id"] == smart_playlist_id
    assert smart_playlist["name"] == "Test Smart Playlist"


def test_public_smart_playlists_accessible_by_other_users(client: TestClient, test_user: User, another_user: User):
    """Test that public smart playlists can be accessed by other users"""
    # Create auth tokens
    user_token = create_access_token(data={"sub": str(test_user.id)})
    user_headers = {"Authorization": f"Bearer {user_token}"}

    another_token = create_access_token(data={"sub": str(another_user.id)})
    another_headers = {"Authorization": f"Bearer {another_token}"}

    # Create a public smart playlist as first user
    criteria = {"filters": {"type": "youtube"}}

    payload = {
        "name": "Public Smart Playlist",
        "description": "Everyone can see this",
        "criteria": criteria,
        "is_public": True
    }

    create_response = client.post("/api/playlists/smart", json=payload, headers=user_headers)
    smart_playlist_id = create_response.json()["id"]

    # Fetch public smart playlists as another user
    response = client.get("/api/playlists/smart/public", headers=another_headers)

    assert response.status_code == 200
    public_smart_playlists = response.json()

    # Verify our smart playlist is in the public list
    smart_playlist_ids = [p["id"] for p in public_smart_playlists]
    assert str(smart_playlist_id) in smart_playlist_ids


def test_private_smart_playlists_not_accessible_by_other_users(client: TestClient, test_user: User, another_user: User):
    """Test that private smart playlists cannot be accessed by other users"""
    # Create auth tokens
    user_token = create_access_token(data={"sub": str(test_user.id)})
    user_headers = {"Authorization": f"Bearer {user_token}"}

    another_token = create_access_token(data={"sub": str(another_user.id)})
    another_headers = {"Authorization": f"Bearer {another_token}"}

    # Create a private smart playlist as first user
    criteria = {"filters": {"duration_min": 0}}

    payload = {
        "name": "Private Smart Playlist",
        "criteria": criteria,
        "is_public": False
    }

    create_response = client.post("/api/playlists/smart", json=payload, headers=user_headers)
    smart_playlist_id = create_response.json()["id"]

    # Try to access private smart playlist as another user
    response = client.get(f"/api/playlists/smart/{smart_playlist_id}", headers=another_headers)

    # Should be forbidden or not found
    assert response.status_code in [403, 404]


def test_smart_playlist_auto_update_flag(client: TestClient, auth_headers: dict):
    """Test creating smart playlist with auto-update enabled"""
    criteria = {
        "filters": {
            "duration_min": 100
        }
    }

    payload = {
        "name": "Auto Update Playlist",
        "criteria": criteria,
        "auto_update": True,
        "auto_update_interval": 12  # hours
    }

    response = client.post("/api/playlists/smart", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    assert data["auto_update"] is True
    assert data["auto_update_interval"] == 12


def test_combined_criteria_filters(client: TestClient, db_session: Session, auth_headers: dict, sample_playlists: list):
    """Test smart playlist with multiple filters combined"""
    criteria = {
        "filters": {
            "duration_min": 200,
            "duration_max": 500,
            "type": "youtube",
            "title_contains": "Video"
        },
        "order_by": "duration",
        "order_direction": "asc",
        "limit": 10
    }

    payload = {
        "name": "Specific YouTube Videos",
        "criteria": criteria
    }

    response = client.post("/api/playlists/smart", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    # Verify generated playlist matches all criteria
    smart_playlist = db_session.query(SmartPlaylist).filter(SmartPlaylist.id == data["id"]).first()
    generated_playlist = db_session.query(Playlist).filter(Playlist.id == smart_playlist.playlist_id).first()

    # All items should match all filters
    for item in generated_playlist.items:
        assert 200 <= item["duration"] <= 500
        assert item["type"] == "youtube"
        assert "Video" in item["title"]

    # Should be sorted by duration ascending
    durations = [item["duration"] for item in generated_playlist.items]
    assert durations == sorted(durations)
