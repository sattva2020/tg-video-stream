"""Unit tests for LyricsService caching behaviour."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Provide fallback DATABASE_URL for the Declarative Base import used by models
os.environ.setdefault("DATABASE_URL", "sqlite:///./test-lyrics.db")

from src.database import Base
from src.models.lyrics_cache import LyricsCache
from src.services.lyrics_service import LyricsService


class DummySong:
    def __init__(self, lyrics: str = "Dummy lyrics", url: str = "https://example.com/song") -> None:
        self.lyrics = lyrics
        self.url = url
        self.html_lyrics = f"<pre>{lyrics}</pre>"


class DummyGenius:
    def __init__(self, song: DummySong | None = None) -> None:
        self.song = song
        self.requests: list[tuple[str, str]] = []

    def search_song(self, title: str, artist: str) -> DummySong | None:
        self.requests.append((artist, title))
        return self.song


@pytest.fixture()
def db_session():
    """Provide isolated in-memory SQLite session for each test."""

    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine, tables=[LyricsCache.__table__])
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_returns_cached_lyrics_when_not_expired(db_session):
    cache_entry = LyricsCache(
        artist_name="Artist",
        track_title="Song",
        lyrics_text="cached lyrics",
        source_api="genius",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    db_session.add(cache_entry)
    db_session.commit()

    service = LyricsService(db_session, genius_client=DummyGenius())

    result = service.get_lyrics("Artist", "Song")

    assert result is not None
    assert result["source"] == "cache"

    db_session.refresh(cache_entry)
    assert cache_entry.access_count == 1


def test_expired_cache_refetched_and_replaced(db_session):
    expired_entry = LyricsCache(
        artist_name="Artist",
        track_title="Song",
        lyrics_text="old lyrics",
        source_api="genius",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db_session.add(expired_entry)
    db_session.commit()

    dummy_song = DummySong(lyrics="fresh lyrics")
    service = LyricsService(db_session, genius_client=DummyGenius(dummy_song))

    result = service.get_lyrics("Artist", "Song")

    assert result is not None
    assert result["source"] == "genius"
    assert result["lyrics"] == "fresh lyrics"

    rows = db_session.query(LyricsCache).all()
    assert len(rows) == 1
    assert rows[0].lyrics_text == "fresh lyrics"


def test_fetch_from_api_sets_cache_with_seven_day_ttl(db_session):
    dummy_song = DummySong()
    service = LyricsService(db_session, genius_client=DummyGenius(dummy_song))

    result = service.get_lyrics("Artist", "Song")

    assert result is not None
    assert result["source"] == "genius"

    cache_entry = db_session.query(LyricsCache).first()
    assert cache_entry is not None

    ttl = cache_entry.expires_at - cache_entry.fetched_at
    assert abs(ttl - timedelta(days=LyricsService.CACHE_TTL_DAYS)) < timedelta(seconds=5)
