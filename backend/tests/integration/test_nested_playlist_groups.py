"""
Integration Tests: Nested Playlist Groups

Tests the nested folder functionality for playlist groups including:
- Creating parent and child groups
- Verifying parent-child relationships
- Preventing circular references
- Moving groups between parents
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.schedule import PlaylistGroup, Playlist
from src.auth.jwt import create_access_token


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user for authentication"""
    user = User(
        email="nested-test@example.com",
        hashed_password="hashed_password",
        full_name="Nested Test User",
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


def test_create_parent_group(client: TestClient, db_session: Session, auth_headers: dict):
    """Test creating a parent playlist group at root level"""
    payload = {
        "name": "Music Collection",
        "description": "My music folders",
        "position": 0,
        "color": "#FF5733"
    }

    response = client.post("/api/playlists/groups", json=payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert data["name"] == "Music Collection"
    assert data["description"] == "My music folders"
    assert data["parent_id"] is None  # Root level group
    assert data["position"] == 0
    assert data["color"] == "#FF5733"
    assert data["user_id"] is not None
    assert "created_at" in data

    # Verify database record
    group = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == data["id"]).first()
    assert group is not None
    assert group.name == "Music Collection"
    assert group.parent_id is None


def test_create_child_group(client: TestClient, db_session: Session, auth_headers: dict):
    """Test creating a child group inside a parent group"""
    # First create a parent group
    parent_payload = {
        "name": "Parent Folder",
        "position": 0
    }
    parent_response = client.post("/api/playlists/groups", json=parent_payload, headers=auth_headers)
    assert parent_response.status_code == 201
    parent_data = parent_response.json()

    # Create child group with parent_id
    child_payload = {
        "name": "Child Folder",
        "description": "Nested inside parent",
        "parent_id": parent_data["id"],
        "position": 0
    }

    child_response = client.post("/api/playlists/groups", json=child_payload, headers=auth_headers)

    assert child_response.status_code == 201
    child_data = child_response.json()

    # Verify child group properties
    assert child_data["name"] == "Child Folder"
    assert child_data["parent_id"] == parent_data["id"]
    assert child_data["position"] == 0

    # Verify database relationships
    parent = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == parent_data["id"]).first()
    child = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == child_data["id"]).first()

    assert child.parent_id == parent.id
    assert child in parent.children


def test_create_deeply_nested_groups(client: TestClient, db_session: Session, auth_headers: dict):
    """Test creating groups at multiple nesting levels"""
    # Level 1: Root
    level1_response = client.post(
        "/api/playlists/groups",
        json={"name": "Level 1", "position": 0},
        headers=auth_headers
    )
    level1_id = level1_response.json()["id"]

    # Level 2: Child of Level 1
    level2_response = client.post(
        "/api/playlists/groups",
        json={"name": "Level 2", "parent_id": level1_id, "position": 0},
        headers=auth_headers
    )
    level2_id = level2_response.json()["id"]

    # Level 3: Child of Level 2
    level3_response = client.post(
        "/api/playlists/groups",
        json={"name": "Level 3", "parent_id": level2_id, "position": 0},
        headers=auth_headers
    )
    level3_id = level3_response.json()["id"]

    # Verify all levels in database
    level1 = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == level1_id).first()
    level2 = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == level2_id).first()
    level3 = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == level3_id).first()

    assert level1.parent_id is None
    assert level2.parent_id == level1.id
    assert level3.parent_id == level2.id

    # Verify hierarchy
    assert level2 in level1.children
    assert level3 in level2.children
    assert level3 not in level1.children  # Not direct child


def test_get_groups_returns_nested_structure(client: TestClient, auth_headers: dict):
    """Test that fetching groups returns all groups with parent relationships"""
    # Create nested structure
    parent_response = client.post(
        "/api/playlists/groups",
        json={"name": "Music", "position": 0},
        headers=auth_headers
    )
    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/api/playlists/groups",
        json={"name": "Rock", "parent_id": parent_id, "position": 0},
        headers=auth_headers
    )

    # Fetch all groups
    response = client.get("/api/playlists/groups", headers=auth_headers)

    assert response.status_code == 200
    groups = response.json()

    # Should have at least 2 groups
    assert len(groups) >= 2

    # Find our groups
    parent = next((g for g in groups if g["id"] == parent_id), None)
    child = next((g for g in groups if g["name"] == "Rock"), None)

    assert parent is not None
    assert child is not None

    # Verify parent has no parent
    assert parent["parent_id"] is None

    # Verify child has parent_id set to parent
    assert child["parent_id"] == parent_id


def test_create_playlist_in_nested_group(client: TestClient, db_session: Session, auth_headers: dict):
    """Test creating a playlist inside a nested group"""
    # Create parent group
    parent_response = client.post(
        "/api/playlists/groups",
        json={"name": "Music Library", "position": 0},
        headers=auth_headers
    )
    parent_id = parent_response.json()["id"]

    # Create child group
    child_response = client.post(
        "/api/playlists/groups",
        json={"name": "Favorites", "parent_id": parent_id, "position": 0},
        headers=auth_headers
    )
    child_id = child_response.json()["id"]

    # Create playlist in child group
    playlist_payload = {
        "name": "My Favorite Songs",
        "description": "Best tracks ever",
        "group_id": child_id,
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=test",
                "title": "Test Song",
                "duration": 180,
                "type": "youtube"
            }
        ]
    }

    playlist_response = client.post("/api/playlists/", json=playlist_payload, headers=auth_headers)

    assert playlist_response.status_code == 201
    playlist_data = playlist_response.json()

    # Verify playlist is in child group
    assert playlist_data["group_id"] == child_id

    # Verify in database
    playlist = db_session.query(Playlist).filter(Playlist.id == playlist_data["id"]).first()
    assert playlist is not None
    assert playlist.group_id == child_id

    # Verify group hierarchy
    child_group = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == child_id).first()
    parent_group = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == parent_id).first()

    assert child_group.parent_id == parent_id
    assert playlist in child_group.playlists


def test_move_group_to_parent(client: TestClient, db_session: Session, auth_headers: dict):
    """Test moving a group to a new parent"""
    # Create two root groups
    group1_response = client.post(
        "/api/playlists/groups",
        json={"name": "Group 1", "position": 0},
        headers=auth_headers
    )
    group1_id = group1_response.json()["id"]

    group2_response = client.post(
        "/api/playlists/groups",
        json={"name": "Group 2", "position": 1},
        headers=auth_headers
    )
    group2_id = group2_response.json()["id"]

    # Initially both are root level
    group1 = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == group1_id).first()
    group2 = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == group2_id).first()

    assert group1.parent_id is None
    assert group2.parent_id is None

    # Move Group 2 to be a child of Group 1
    move_response = client.post(
        f"/api/playlists/groups/{group2_id}/move",
        params={"parent_id": group1_id},
        headers=auth_headers
    )

    assert move_response.status_code == 200
    moved_data = move_response.json()

    # Verify move
    assert moved_data["parent_id"] == group1_id

    # Verify in database
    db_session.refresh(group2)
    assert group2.parent_id == group1_id
    assert group2 in group1.children


def test_prevent_circular_reference(client: TestClient, db_session: Session, auth_headers: dict):
    """Test that circular references are prevented"""
    # Create parent -> child structure
    parent_response = client.post(
        "/api/playlists/groups",
        json={"name": "Parent", "position": 0},
        headers=auth_headers
    )
    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/api/playlists/groups",
        json={"name": "Child", "parent_id": parent_id, "position": 0},
        headers=auth_headers
    )
    child_id = child_response.json()["id"]

    # Try to move parent to be a child of its own child (circular reference)
    move_response = client.post(
        f"/api/playlists/groups/{parent_id}/move",
        params={"parent_id": child_id},
        headers=auth_headers
    )

    # Should fail with 400 or 422
    assert move_response.status_code in [400, 422]

    # Verify database wasn't changed
    parent = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == parent_id).first()
    child = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == child_id).first()

    assert parent.parent_id is None  # Parent still has no parent
    assert child.parent_id == parent_id  # Child still belongs to parent


def test_delete_parent_group_moves_children_to_root(client: TestClient, db_session: Session, auth_headers: dict):
    """Test that deleting a parent group moves children to root level"""
    # Create parent with child
    parent_response = client.post(
        "/api/playlists/groups",
        json={"name": "Parent", "position": 0},
        headers=auth_headers
    )
    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/api/playlists/groups",
        json={"name": "Child", "parent_id": parent_id, "position": 0},
        headers=auth_headers
    )
    child_id = child_response.json()["id"]

    # Delete parent
    delete_response = client.delete(f"/api/playlists/groups/{parent_id}", headers=auth_headers)
    assert delete_response.status_code == 200

    # Verify child was moved to root
    child = db_session.query(PlaylistGroup).filter(PlaylistGroup.id == child_id).first()
    assert child is not None
    assert child.parent_id is None  # Now at root level


def test_get_group_with_parent_details(client: TestClient, auth_headers: dict):
    """Test fetching a group and verifying its parent relationship"""
    # Create parent and child
    parent_response = client.post(
        "/api/playlists/groups",
        json={"name": "Parent Folder", "position": 0},
        headers=auth_headers
    )
    parent_id = parent_response.json()["id"]

    child_response = client.post(
        "/api/playlists/groups",
        json={"name": "Child Folder", "parent_id": parent_id, "position": 0},
        headers=auth_headers
    )
    child_id = child_response.json()["id"]

    # Fetch child group
    response = client.get(f"/api/playlists/groups/{child_id}", headers=auth_headers)

    assert response.status_code == 200
    child_data = response.json()

    # Verify child has parent_id
    assert child_data["parent_id"] == parent_id
    assert child_data["name"] == "Child Folder"
