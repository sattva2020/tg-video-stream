"""
Integration tests for playlist with local files and YouTube.
Uses shared conftest.py fixtures for database.
"""
import pytest
from src.models import User
from src.auth.jwt import create_access_token


@pytest.fixture
def auth_headers(db_session):
    """Create a test admin user and return auth headers."""
    user = User(
        email="playlist_test@example.com", 
        hashed_password="hashedpassword", 
        status="approved", 
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {access_token}"}


def test_add_local_file_playlist_item(client, auth_headers):
    """Test adding a local file to playlist."""
    payload = {
        "url": "/app/data/media/test_video.mp4",
        "title": "Test Video",
        "type": "local"
    }
    response = client.post("/api/playlist/", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "/app/data/media/test_video.mp4"
    assert data["title"] == "Test Video"
    assert data["type"] == "local"
    assert "id" in data

    # Verify it's in the list
    response = client.get("/api/playlist/", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    found = any(
        item["url"] == "/app/data/media/test_video.mp4" and item["type"] == "local"
        for item in items
    )
    assert found


def test_add_youtube_playlist_item(client, auth_headers):
    """Test adding a YouTube video to playlist."""
    payload = {
        "url": "https://youtube.com/watch?v=12345",
        "title": "YouTube Video",
        "type": "youtube"
    }
    response = client.post("/api/playlist/", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "youtube"

