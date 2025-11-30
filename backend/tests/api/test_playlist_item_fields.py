import os
import uuid
from fastapi.testclient import TestClient
from src.models.user import User
from src.auth.jwt import create_access_token


os.environ.setdefault("STREAMER_STATUS_TOKEN", "tests-status-token")

def make_auth_headers(db_session):
    user = User(email="fieldtest@example.com", hashed_password="hashed", status="approved", role="admin")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_create_playlist_item_includes_status_and_duration(client: TestClient, db_session):
    headers = make_auth_headers(db_session)

    payload = {
        "url": "https://example.com/audio/test.mp3",
        "title": "Test MP3",
        "type": "stream"
    }

    r = client.post("/api/playlist/", json=payload, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] == "queued"
    assert "duration" in data
    assert data["duration"] is None


def test_create_with_duration_is_persisted(client: TestClient, db_session):
    headers = make_auth_headers(db_session)

    payload = {
        "url": "https://example.com/audio/test.flac",
        "title": "FLAC Track",
        "type": "stream",
        "duration": 360
    }

    r = client.post("/api/playlist/", json=payload, headers=headers)
    assert r.status_code == 200
    data = r.json()

    assert data["duration"] == 360

    # Ensure listed items include these fields
    r2 = client.get("/api/playlist/", headers=headers)
    assert r2.status_code == 200
    found = False
    for item in r2.json():
        if item.get("url") == "https://example.com/audio/test.flac":
            assert "status" in item
            assert "duration" in item
            found = True
            break
    assert found


def test_streamer_can_update_status(client: TestClient, db_session):
    headers = make_auth_headers(db_session)
    payload = {
        "url": "https://example.com/audio/status-update.opus",
        "type": "stream"
    }
    response = client.post("/api/playlist/", json=payload, headers=headers)
    assert response.status_code == 200
    item = response.json()

    patch_resp = client.patch(
        f"/api/playlist/{item['id']}/status",
        json={"status": "playing"},
        headers={"X-Streamer-Token": os.environ["STREAMER_STATUS_TOKEN"]}
    )
    assert patch_resp.status_code == 200, patch_resp.json()
    updated = patch_resp.json()
    assert updated["status"] == "playing"

    unauthorized = client.patch(
        f"/api/playlist/{item['id']}/status",
        json={"status": "queued"}
    )
    assert unauthorized.status_code == 403
