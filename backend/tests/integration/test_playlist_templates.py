"""
Integration Tests: Playlist Templates

Tests the playlist template functionality including:
- Creating templates with items
- Applying templates to create playlists
- Cloning templates
- Template metadata calculation
- Public/private template access
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.schedule import PlaylistTemplate, Playlist
from src.auth.jwt import create_access_token
import uuid


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user for authentication"""
    user = User(
        email="template-test@example.com",
        hashed_password="hashed_password",
        full_name="Template Test User",
        status="approved",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def another_user(db_session: Session):
    """Create another test user for testing public templates"""
    user = User(
        email="another-user@example.com",
        hashed_password="hashed_password",
        full_name="Another User",
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


def test_create_template_with_items(client: TestClient, db_session: Session, auth_headers: dict):
    """Test creating a playlist template with multiple items"""
    template_payload = {
        "name": "Evening News Format",
        "description": "Standard evening news template",
        "is_public": False,
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=abc123",
                "title": "Headlines",
                "duration": 300,
                "type": "youtube"
            },
            {
                "url": "https://www.youtube.com/watch?v=def456",
                "title": "Weather Report",
                "duration": 180,
                "type": "youtube"
            },
            {
                "url": "https://vimeo.com/789012",
                "title": "Sports Update",
                "duration": 240,
                "type": "vimeo"
            }
        ]
    }

    response = client.post("/api/playlists/templates", json=template_payload, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "id" in data
    assert data["name"] == "Evening News Format"
    assert data["description"] == "Standard evening news template"
    assert data["is_public"] is False
    assert data["items_count"] == 3
    assert data["total_duration"] == 720  # 300 + 180 + 240
    assert data["user_id"] is not None
    assert "created_at" in data

    # Verify items are preserved
    assert len(data["items"]) == 3
    assert data["items"][0]["title"] == "Headlines"
    assert data["items"][1]["title"] == "Weather Report"
    assert data["items"][2]["title"] == "Sports Update"

    # Verify database record
    template = db_session.query(PlaylistTemplate).filter(PlaylistTemplate.id == data["id"]).first()
    assert template is not None
    assert template.name == "Evening News Format"
    assert template.items_count == 3


def test_get_user_templates(client: TestClient, auth_headers: dict):
    """Test fetching all templates for a user"""
    # Create two templates
    template1_payload = {
        "name": "Template 1",
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=test1",
                "title": "Test 1",
                "duration": 100,
                "type": "youtube"
            }
        ]
    }

    template2_payload = {
        "name": "Template 2",
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=test2",
                "title": "Test 2",
                "duration": 200,
                "type": "youtube"
            }
        ]
    }

    client.post("/api/playlists/templates", json=template1_payload, headers=auth_headers)
    client.post("/api/playlists/templates", json=template2_payload, headers=auth_headers)

    # Fetch templates
    response = client.get("/api/playlists/templates", headers=auth_headers)

    assert response.status_code == 200
    templates = response.json()

    # Should have at least 2 templates
    assert len(templates) >= 2

    # Verify our templates are in the list
    template_names = [t["name"] for t in templates]
    assert "Template 1" in template_names
    assert "Template 2" in template_names


def test_get_template_by_id(client: TestClient, auth_headers: dict):
    """Test fetching a single template by ID"""
    # Create a template
    template_payload = {
        "name": "Morning Show",
        "description": "Daily morning format",
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=morning",
                "title": "Morning Intro",
                "duration": 120,
                "type": "youtube"
            }
        ]
    }

    create_response = client.post("/api/playlists/templates", json=template_payload, headers=auth_headers)
    template_id = create_response.json()["id"]

    # Fetch the template
    response = client.get(f"/api/playlists/templates/{template_id}", headers=auth_headers)

    assert response.status_code == 200
    template = response.json()

    assert template["id"] == template_id
    assert template["name"] == "Morning Show"
    assert template["description"] == "Daily morning format"
    assert template["items_count"] == 1


def test_apply_template_to_playlist(client: TestClient, db_session: Session, auth_headers: dict):
    """Test applying a template to create a new playlist"""
    # Create a template
    template_payload = {
        "name": "Music Hour",
        "description": "One hour of music",
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=song1",
                "title": "Song One",
                "duration": 180,
                "type": "youtube"
            },
            {
                "url": "https://www.youtube.com/watch?v=song2",
                "title": "Song Two",
                "duration": 200,
                "type": "youtube"
            },
            {
                "url": "https://www.youtube.com/watch?v=song3",
                "title": "Song Three",
                "duration": 220,
                "type": "youtube"
            }
        ]
    }

    template_response = client.post("/api/playlists/templates", json=template_payload, headers=auth_headers)
    template_id = template_response.json()["id"]

    # Apply template to create playlist
    apply_payload = {
        "playlist_name": "Friday Music Hour",
        "playlist_description": "End the week with great music"
    }

    response = client.post(
        f"/api/playlists/templates/{template_id}/apply",
        json=apply_payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    playlist = response.json()

    # Verify playlist created from template
    assert playlist["name"] == "Friday Music Hour"
    assert playlist["description"] == "End the week with great music"
    assert playlist["items_count"] == 3
    assert playlist["total_duration"] == 600  # 180 + 200 + 220

    # Verify items copied correctly
    assert len(playlist["items"]) == 3
    assert playlist["items"][0]["title"] == "Song One"
    assert playlist["items"][1]["title"] == "Song Two"
    assert playlist["items"][2]["title"] == "Song Three"

    # Verify in database
    db_playlist = db_session.query(Playlist).filter(Playlist.id == playlist["id"]).first()
    assert db_playlist is not None
    assert db_playlist.items_count == 3
    assert db_playlist.total_duration == 600


def test_apply_nonexistent_template_returns_error(client: TestClient, auth_headers: dict):
    """Test that applying a non-existent template returns an error"""
    fake_id = uuid.uuid4()

    apply_payload = {
        "playlist_name": "Test Playlist"
    }

    response = client.post(
        f"/api/playlists/templates/{fake_id}/apply",
        json=apply_payload,
        headers=auth_headers
    )

    assert response.status_code == 404


def test_clone_template(client: TestClient, auth_headers: dict):
    """Test cloning a template"""
    # Create original template
    template_payload = {
        "name": "Original Template",
        "description": "This is the original",
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=original",
                "title": "Original Song",
                "duration": 150,
                "type": "youtube"
            }
        ]
    }

    create_response = client.post("/api/playlists/templates", json=template_payload, headers=auth_headers)
    template_id = create_response.json()["id"]

    # Clone the template
    response = client.post(
        f"/api/playlists/templates/{template_id}/clone",
        headers=auth_headers
    )

    assert response.status_code == 200
    cloned = response.json()

    # Verify clone has correct properties
    assert cloned["name"] == "Copy of Original Template"
    assert cloned["description"] == "This is the original"
    assert cloned["items_count"] == 1
    assert cloned["total_duration"] == 150

    # Verify items are identical
    assert cloned["items"][0]["url"] == "https://www.youtube.com/watch?v=original"
    assert cloned["items"][0]["title"] == "Original Song"


def test_update_template(client: TestClient, db_session: Session, auth_headers: dict):
    """Test updating an existing template"""
    # Create template
    template_payload = {
        "name": "Old Name",
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=old",
                "title": "Old Item",
                "duration": 100,
                "type": "youtube"
            }
        ]
    }

    create_response = client.post("/api/playlists/templates", json=template_payload, headers=auth_headers)
    template_id = create_response.json()["id"]

    # Update template
    update_payload = {
        "name": "New Name",
        "description": "Updated description",
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=new1",
                "title": "New Item 1",
                "duration": 200,
                "type": "youtube"
            },
            {
                "url": "https://www.youtube.com/watch?v=new2",
                "title": "New Item 2",
                "duration": 300,
                "type": "youtube"
            }
        ]
    }

    response = client.put(
        f"/api/playlists/templates/{template_id}",
        json=update_payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    updated = response.json()

    # Verify updates
    assert updated["name"] == "New Name"
    assert updated["description"] == "Updated description"
    assert updated["items_count"] == 2
    assert updated["total_duration"] == 500  # 200 + 300

    # Verify in database
    template = db_session.query(PlaylistTemplate).filter(PlaylistTemplate.id == template_id).first()
    assert template.name == "New Name"
    assert template.items_count == 2


def test_delete_template(client: TestClient, db_session: Session, auth_headers: dict):
    """Test deleting a template"""
    # Create template
    template_payload = {
        "name": "To Be Deleted",
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=delete",
                "title": "Delete Me",
                "duration": 100,
                "type": "youtube"
            }
        ]
    }

    create_response = client.post("/api/playlists/templates", json=template_payload, headers=auth_headers)
    template_id = create_response.json()["id"]

    # Delete template
    response = client.delete(f"/api/playlists/templates/{template_id}", headers=auth_headers)

    assert response.status_code == 200

    # Verify template is deleted
    template = db_session.query(PlaylistTemplate).filter(PlaylistTemplate.id == template_id).first()
    assert template is None


def test_public_templates_accessible_by_other_users(client: TestClient, test_user: User, another_user: User):
    """Test that public templates can be accessed by other users"""
    # Create auth tokens
    user_token = create_access_token(data={"sub": str(test_user.id)})
    user_headers = {"Authorization": f"Bearer {user_token}"}

    another_token = create_access_token(data={"sub": str(another_user.id)})
    another_headers = {"Authorization": f"Bearer {another_token}"}

    # Create a public template as first user
    template_payload = {
        "name": "Public Template",
        "description": "Everyone can use this",
        "is_public": True,
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=public",
                "title": "Public Content",
                "duration": 180,
                "type": "youtube"
            }
        ]
    }

    create_response = client.post("/api/playlists/templates", json=template_payload, headers=user_headers)
    template_id = create_response.json()["id"]

    # Fetch public templates as another user
    response = client.get("/api/playlists/templates/public", headers=another_headers)

    assert response.status_code == 200
    public_templates = response.json()

    # Verify our public template is in the list
    template_ids = [t["id"] for t in public_templates]
    assert str(template_id) in template_ids

    # Verify the other user can apply the public template
    apply_payload = {
        "playlist_name": "Using Public Template"
    }

    apply_response = client.post(
        f"/api/playlists/templates/{template_id}/apply",
        json=apply_payload,
        headers=another_headers
    )

    assert apply_response.status_code == 200
    playlist = apply_response.json()
    assert playlist["name"] == "Using Public Template"
    assert playlist["items_count"] == 1


def test_private_templates_not_accessible_by_other_users(client: TestClient, test_user: User, another_user: User):
    """Test that private templates cannot be accessed by other users"""
    # Create auth tokens
    user_token = create_access_token(data={"sub": str(test_user.id)})
    user_headers = {"Authorization": f"Bearer {user_token}"}

    another_token = create_access_token(data={"sub": str(another_user.id)})
    another_headers = {"Authorization": f"Bearer {another_token}"}

    # Create a private template as first user
    template_payload = {
        "name": "Private Template",
        "is_public": False,
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=private",
                "title": "Private Content",
                "duration": 180,
                "type": "youtube"
            }
        ]
    }

    create_response = client.post("/api/playlists/templates", json=template_payload, headers=user_headers)
    template_id = create_response.json()["id"]

    # Try to access private template as another user
    response = client.get(f"/api/playlists/templates/{template_id}", headers=another_headers)

    # Should be forbidden or not found
    assert response.status_code in [403, 404]

    # Try to apply private template as another user
    apply_payload = {
        "playlist_name": "Should Not Work"
    }

    apply_response = client.post(
        f"/api/playlists/templates/{template_id}/apply",
        json=apply_payload,
        headers=another_headers
    )

    # Should be forbidden or not found
    assert apply_response.status_code in [403, 404]


def test_template_metadata_calculation(db_session: Session, test_user: User):
    """Test that template metadata (items_count, total_duration) is calculated correctly"""
    items = [
        {"url": "https://www.youtube.com/watch?v=1", "title": "Item 1", "duration": 100, "type": "youtube"},
        {"url": "https://www.youtube.com/watch?v=2", "title": "Item 2", "duration": 200, "type": "youtube"},
        {"url": "https://www.youtube.com/watch?v=3", "title": "Item 3", "duration": 300, "type": "youtube"},
        {"url": "https://www.youtube.com/watch?v=4", "title": "Item 4", "duration": 400, "type": "youtube"},
    ]

    template = PlaylistTemplate(
        user_id=test_user.id,
        name="Metadata Test",
        items=items
    )

    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)

    # Verify metadata calculated automatically
    assert template.items_count == 4
    assert template.total_duration == 1000  # 100 + 200 + 300 + 400


def test_template_items_order_preserved(client: TestClient, auth_headers: dict):
    """Test that item order is preserved when applying a template"""
    # Create template with items in specific order
    template_payload = {
        "name": "Ordered Template",
        "items": [
            {
                "url": "https://www.youtube.com/watch?v=first",
                "title": "First Item",
                "duration": 100,
                "type": "youtube"
            },
            {
                "url": "https://www.youtube.com/watch?v=second",
                "title": "Second Item",
                "duration": 200,
                "type": "youtube"
            },
            {
                "url": "https://www.youtube.com/watch?v=third",
                "title": "Third Item",
                "duration": 300,
                "type": "youtube"
            }
        ]
    }

    template_response = client.post("/api/playlists/templates", json=template_payload, headers=auth_headers)
    template_id = template_response.json()["id"]

    # Apply template
    apply_response = client.post(
        f"/api/playlists/templates/{template_id}/apply",
        json={"playlist_name": "Ordered Playlist"},
        headers=auth_headers
    )

    assert apply_response.status_code == 200
    playlist = apply_response.json()

    # Verify order is preserved
    assert playlist["items"][0]["title"] == "First Item"
    assert playlist["items"][1]["title"] == "Second Item"
    assert playlist["items"][2]["title"] == "Third Item"
