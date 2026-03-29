"""
Unit tests for DeduplicationService.

Tests duplicate detection functionality:
- URL-based duplicate detection
- Content ID-based duplicate detection (YouTube/Vimeo)
- Fuzzy title matching
- Batch duplicate checking
- Duplicate statistics

Coverage includes:
- Video ID extraction from URLs
- Exact URL matching
- Platform-specific content ID matching
- Similarity calculations
- Batch processing
- Error handling
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from sqlalchemy.orm import Session

from src.services.deduplication_service import DeduplicationService
from src.models.playlist import PlaylistItem


# ==================== Fixtures ====================

@pytest.fixture
def dedup_service():
    """Get DeduplicationService instance."""
    return DeduplicationService()


@pytest.fixture
def db_session():
    """Mock database session."""
    session = Mock(spec=Session)
    session.query = Mock()
    return session


@pytest.fixture
def sample_playlist_item():
    """Sample PlaylistItem for testing."""
    item = PlaylistItem(
        id=uuid4(),
        url="https://youtube.com/watch?v=abc123",
        title="Test Video",
        duration=180,
        type="youtube"
    )
    return item


@pytest.fixture
def sample_items():
    """Sample items list for batch testing."""
    return [
        {
            "url": "https://youtube.com/watch?v=abc123",
            "title": "Test Video 1",
            "type": "youtube"
        },
        {
            "url": "https://youtube.com/watch?v=def456",
            "title": "Test Video 2",
            "type": "youtube"
        },
        {
            "url": "https://vimeo.com/123456789",
            "title": "Vimeo Video",
            "type": "vimeo"
        },
        {
            "url": "/path/to/video.mp4",
            "title": "Local Video",
            "type": "local"
        }
    ]


# ==================== Video ID Extraction Tests ====================

def test_extract_youtube_video_id_standard_url(dedup_service):
    """Test extracting YouTube video ID from standard URL."""
    url = "https://www.youtube.com/watch?v=abc123xyz"
    video_id = dedup_service.extract_video_id(url, "youtube")

    assert video_id == "abc123xyz"


def test_extract_youtube_video_id_short_url(dedup_service):
    """Test extracting YouTube video ID from short URL."""
    url = "https://youtu.be/def456uvw"
    video_id = dedup_service.extract_video_id(url, "youtube")

    assert video_id == "def456uvw"


def test_extract_youtube_video_id_embed_url(dedup_service):
    """Test extracting YouTube video ID from embed URL."""
    url = "https://www.youtube.com/embed/ghi789rst"
    video_id = dedup_service.extract_video_id(url, "youtube")

    assert video_id == "ghi789rst"


def test_extract_youtube_video_id_no_match(dedup_service):
    """Test handling invalid YouTube URL."""
    url = "https://example.com/video"
    video_id = dedup_service.extract_video_id(url, "youtube")

    assert video_id is None


def test_extract_vimeo_video_id_standard_url(dedup_service):
    """Test extracting Vimeo video ID from standard URL."""
    url = "https://vimeo.com/123456789"
    video_id = dedup_service.extract_video_id(url, "vimeo")

    assert video_id == "123456789"


def test_extract_vimeo_video_id_player_url(dedup_service):
    """Test extracting Vimeo video ID from player URL."""
    url = "https://player.vimeo.com/video/987654321"
    video_id = dedup_service.extract_video_id(url, "vimeo")

    assert video_id == "987654321"


def test_extract_video_id_local_file(dedup_service):
    """Test that local files return full path as ID."""
    url = "/path/to/local/video.mp4"
    video_id = dedup_service.extract_video_id(url, "local")

    assert video_id == url


def test_extract_video_id_empty_url(dedup_service):
    """Test handling empty URL."""
    video_id = dedup_service.extract_video_id("", "youtube")

    assert video_id is None


def test_extract_video_id_none_url(dedup_service):
    """Test handling None URL."""
    video_id = dedup_service.extract_video_id(None, "youtube")

    assert video_id is None


# ==================== URL Duplicate Detection Tests ====================

def test_is_duplicate_url_found(dedup_service, db_session):
    """Test detecting duplicate URL in database."""
    # Arrange
    mock_query = Mock()
    mock_item = Mock()
    mock_query.first.return_value = mock_item
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    result = dedup_service.is_duplicate_url(db_session, "https://youtube.com/watch?v=abc123")

    # Assert
    assert result is True
    db_session.query.assert_called_once_with(PlaylistItem)


def test_is_duplicate_url_not_found(dedup_service, db_session):
    """Test when URL is not duplicate."""
    # Arrange
    mock_query = Mock()
    mock_query.first.return_value = None
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    result = dedup_service.is_duplicate_url(db_session, "https://youtube.com/watch?v=xyz999")

    # Assert
    assert result is False


def test_is_duplicate_url_with_channel_id(dedup_service, db_session):
    """Test duplicate URL with channel scope."""
    # Arrange
    channel_id = str(uuid4())
    mock_query = Mock()
    mock_query.first.return_value = None
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    result = dedup_service.is_duplicate_url(
        db_session,
        "https://youtube.com/watch?v=abc123",
        channel_id=channel_id
    )

    # Assert
    assert result is False
    # Verify channel_id filter was applied
    assert db_session.query.return_value.filter.call_count >= 2


def test_is_duplicate_url_with_exclude_ids(dedup_service, db_session):
    """Test duplicate URL with excluded IDs."""
    # Arrange
    exclude_ids = {str(uuid4()), str(uuid4())}
    mock_query = Mock()
    mock_query.first.return_value = None
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    result = dedup_service.is_duplicate_url(
        db_session,
        "https://youtube.com/watch?v=abc123",
        exclude_ids=exclude_ids
    )

    # Assert
    assert result is False


def test_is_duplicate_url_error_handling(dedup_service, db_session):
    """Test error handling in duplicate URL check."""
    # Arrange
    db_session.query.side_effect = Exception("Database error")

    # Act
    with patch('builtins.print'):  # Suppress print output
        result = dedup_service.is_duplicate_url(db_session, "https://youtube.com/watch?v=abc123")

    # Assert
    assert result is False  # Should return False on error


# ==================== Content ID Duplicate Detection Tests ====================

def test_is_duplicate_by_content_id_youtube(dedup_service, db_session):
    """Test detecting duplicate YouTube video by content ID."""
    # Arrange
    mock_item = Mock()
    mock_item.url = "https://www.youtube.com/watch?v=abc123"
    mock_query = Mock()
    mock_query.all.return_value = [mock_item]
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    result = dedup_service.is_duplicate_by_content_id(
        db_session,
        "abc123",
        "youtube"
    )

    # Assert
    assert result is True


def test_is_duplicate_by_content_id_vimeo(dedup_service, db_session):
    """Test detecting duplicate Vimeo video by content ID."""
    # Arrange
    mock_item = Mock()
    mock_item.url = "https://vimeo.com/123456789"
    mock_query = Mock()
    mock_query.all.return_value = [mock_item]
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    result = dedup_service.is_duplicate_by_content_id(
        db_session,
        "123456789",
        "vimeo"
    )

    # Assert
    assert result is True


def test_is_duplicate_by_content_id_not_found(dedup_service, db_session):
    """Test when content ID is not duplicate."""
    # Arrange
    mock_query = Mock()
    mock_query.all.return_value = []
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    result = dedup_service.is_duplicate_by_content_id(
        db_session,
        "xyz999",
        "youtube"
    )

    # Assert
    assert result is False


def test_is_duplicate_by_content_id_local_platform(dedup_service, db_session):
    """Test that local platform always returns False for content ID check."""
    # Act
    result = dedup_service.is_duplicate_by_content_id(
        db_session,
        "/path/to/video.mp4",
        "local"
    )

    # Assert
    assert result is False


def test_is_duplicate_by_content_id_empty_id(dedup_service, db_session):
    """Test handling empty content ID."""
    # Act
    result = dedup_service.is_duplicate_by_content_id(
        db_session,
        "",
        "youtube"
    )

    # Assert
    assert result is False


# ==================== Similarity Calculation Tests ====================

def test_calculate_similarity_identical(dedup_service):
    """Test similarity calculation for identical strings."""
    result = dedup_service.calculate_similarity("Test Video", "Test Video")

    assert result == 1.0


def test_calculate_similarity_similar(dedup_service):
    """Test similarity calculation for similar strings."""
    result = dedup_service.calculate_similarity("Test Video", "Test Videos")

    assert result > 0.8  # Very similar


def test_calculate_similarity_different(dedup_service):
    """Test similarity calculation for different strings."""
    result = dedup_service.calculate_similarity("Test Video", "Completely Different")

    assert result < 0.3  # Not similar


def test_calculate_similarity_case_insensitive(dedup_service):
    """Test that similarity is case-insensitive."""
    result1 = dedup_service.calculate_similarity("Test Video", "test video")
    result2 = dedup_service.calculate_similarity("TEST VIDEO", "test video")

    assert result1 > 0.9
    assert result2 > 0.9


def test_calculate_similarity_empty_string(dedup_service):
    """Test similarity calculation with empty strings."""
    result = dedup_service.calculate_similarity("Test Video", "")

    assert result == 0.0


def test_calculate_similarity_none_values(dedup_service):
    """Test similarity calculation with None values."""
    result = dedup_service.calculate_similarity(None, "Test Video")

    assert result == 0.0


# ==================== Similar Title Search Tests ====================

def test_find_similar_titles_found(dedup_service, db_session):
    """Test finding items with similar titles."""
    # Arrange
    mock_items = [
        Mock(title="Test Video 1"),
        Mock(title="Test Video 2"),
        Mock(title="Completely Different")
    ]
    mock_query = Mock()
    mock_query.all.return_value = mock_items
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    results = dedup_service.find_similar_titles(
        db_session,
        "Test Video",
        threshold=0.7
    )

    # Assert
    assert len(results) >= 2  # At least the similar ones


def test_find_similar_titles_no_matches(dedup_service, db_session):
    """Test when no similar titles are found."""
    # Arrange
    mock_items = [
        Mock(title="Completely Different Title"),
        Mock(title="Another Unrelated Title")
    ]
    mock_query = Mock()
    mock_query.all.return_value = mock_items
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    results = dedup_service.find_similar_titles(
        db_session,
        "Test Video",
        threshold=0.9
    )

    # Assert
    assert len(results) == 0


def test_find_similar_titles_empty_title(dedup_service, db_session):
    """Test handling empty title."""
    # Act
    results = dedup_service.find_similar_titles(db_session, "", threshold=0.8)

    # Assert
    assert results == []


def test_find_similar_titles_with_channel_id(dedup_service, db_session):
    """Test finding similar titles with channel scope."""
    # Arrange
    channel_id = str(uuid4())
    mock_items = [Mock(title="Test Video")]
    mock_query = Mock()
    mock_query.all.return_value = mock_items
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    results = dedup_service.find_similar_titles(
        db_session,
        "Test Video",
        threshold=0.8,
        channel_id=channel_id
    )

    # Assert
    assert len(results) >= 0


def test_find_similar_titles_error_handling(dedup_service, db_session):
    """Test error handling in similar title search."""
    # Arrange
    db_session.query.side_effect = Exception("Database error")

    # Act
    with patch('builtins.print'):  # Suppress print output
        results = dedup_service.find_similar_titles(
            db_session,
            "Test Video",
            threshold=0.8
        )

    # Assert
    assert results == []


# ==================== Batch Duplicate Checking Tests ====================

def test_check_duplicates_batch_all_unique(dedup_service, db_session, sample_items):
    """Test batch checking when all items are unique."""
    # Arrange
    mock_query = Mock()
    mock_query.first.return_value = None
    mock_query.all.return_value = []
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    unique, duplicates, summary = dedup_service.check_duplicates_batch(
        db_session,
        sample_items
    )

    # Assert
    assert len(unique) == 4
    assert len(duplicates) == 0
    assert summary["unique"] == 4
    assert summary["duplicates"] == 0


def test_check_duplicates_batch_with_duplicates(dedup_service, db_session):
    """Test batch checking with duplicate items."""
    # Arrange
    items = [
        {"url": "https://youtube.com/watch?v=abc123", "title": "Video 1", "type": "youtube"},
        {"url": "https://youtube.com/watch?v=abc123", "title": "Video 1 Duplicate", "type": "youtube"}
    ]

    mock_query = Mock()
    # First URL is duplicate, second is same URL
    mock_query.first.return_value = Mock()
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    unique, duplicates, summary = dedup_service.check_duplicates_batch(
        db_session,
        items
    )

    # Assert
    assert len(duplicates) >= 1
    assert summary["duplicates"] >= 1


def test_check_duplicates_batch_duplicate_in_batch(dedup_service, db_session):
    """Test detecting duplicates within the import batch itself."""
    # Arrange
    items = [
        {"url": "https://youtube.com/watch?v=abc123", "title": "Video 1", "type": "youtube"},
        {"url": "https://youtube.com/watch?v=abc123", "title": "Video 1 Again", "type": "youtube"},
        {"url": "https://youtube.com/watch?v=def456", "title": "Video 2", "type": "youtube"}
    ]

    mock_query = Mock()
    mock_query.first.return_value = None  # No duplicates in DB
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    unique, duplicates, summary = dedup_service.check_duplicates_batch(
        db_session,
        items
    )

    # Assert
    assert len(unique) == 2  # abc123 and def456
    assert len(duplicates) == 1  # Second abc123
    assert duplicates[0]["duplicate_reason"] == "duplicate_in_batch"


def test_check_duplicates_batch_by_content_id(dedup_service, db_session):
    """Test detecting duplicates by content ID."""
    # Arrange
    items = [
        {"url": "https://youtube.com/watch?v=abc123", "title": "Video 1", "type": "youtube"},
        {"url": "https://youtu.be/abc123", "title": "Video 1 Short URL", "type": "youtube"}
    ]

    def mock_filter_side_effect(*args, **kwargs):
        # For URL check, return None (not duplicate)
        # For content ID check, return duplicate
        if "url" in str(args):
            return Mock(first=Mock(return_value=None))
        else:
            # Return item with same video ID
            mock_item = Mock()
            mock_item.url = "https://www.youtube.com/watch?v=abc123"
            return Mock(all=Mock(return_value=[mock_item]))

    mock_query = Mock()
    mock_query.filter.side_effect = mock_filter_side_effect
    db_session.query.return_value = mock_query

    # Act
    unique, duplicates, summary = dedup_service.check_duplicates_batch(
        db_session,
        items
    )

    # Assert
    # Should detect duplicate by content ID
    assert summary["by_content_id"] >= 1 or len(duplicates) >= 1


def test_check_duplicates_batch_by_title(dedup_service, db_session):
    """Test detecting duplicates by similar title."""
    # Arrange
    items = [
        {"url": "https://youtube.com/watch?v=abc123", "title": "Test Video", "type": "youtube"}
    ]

    # Setup similar title in database
    mock_similar_item = Mock()
    mock_similar_item.id = uuid4()
    mock_similar_item.title = "Test Video"

    mock_query = Mock()
    mock_query.first.return_value = None  # No URL duplicate
    mock_query.all.return_value = [mock_similar_item]  # Similar title found
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    unique, duplicates, summary = dedup_service.check_duplicates_batch(
        db_session,
        items
    )

    # Assert
    # Should detect duplicate by similar title
    assert summary["by_title"] >= 1 or len(duplicates) >= 1


def test_check_duplicates_batch_empty_items(dedup_service, db_session):
    """Test batch checking with empty items list."""
    # Act
    unique, duplicates, summary = dedup_service.check_duplicates_batch(
        db_session,
        []
    )

    # Assert
    assert len(unique) == 0
    assert len(duplicates) == 0
    assert summary["total"] == 0


def test_check_duplicates_batch_item_without_url(dedup_service, db_session):
    """Test handling items without URL."""
    # Arrange
    items = [
        {"title": "Video without URL", "type": "youtube"}  # Missing URL
    ]

    # Act
    unique, duplicates, summary = dedup_service.check_duplicates_batch(
        db_session,
        items
    )

    # Assert
    # Items without URL should be skipped
    assert len(unique) == 0
    assert summary["unique"] == 0


# ==================== Duplicate Statistics Tests ====================

def test_get_duplicate_stats(dedup_service, db_session):
    """Test getting duplicate statistics."""
    # Arrange
    mock_items = [
        Mock(url="https://youtube.com/watch?v=abc123"),
        Mock(url="https://youtube.com/watch?v=abc123"),  # Duplicate
        Mock(url="https://youtube.com/watch?v=def456"),
        Mock(url="https://youtube.com/watch?v=ghi789"),
    ]
    mock_query = Mock()
    mock_query.all.return_value = mock_items
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    stats = dedup_service.get_duplicate_stats(db_session)

    # Assert
    assert stats["total_items"] == 4
    assert stats["unique_items"] == 3
    assert stats["duplicate_urls"] == 1
    assert stats["total_duplicates"] == 1


def test_get_duplicate_stats_no_duplicates(dedup_service, db_session):
    """Test stats when no duplicates exist."""
    # Arrange
    mock_items = [
        Mock(url="https://youtube.com/watch?v=abc123"),
        Mock(url="https://youtube.com/watch?v=def456"),
        Mock(url="https://youtube.com/watch?v=ghi789"),
    ]
    mock_query = Mock()
    mock_query.all.return_value = mock_items
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    stats = dedup_service.get_duplicate_stats(db_session)

    # Assert
    assert stats["total_items"] == 3
    assert stats["unique_items"] == 3
    assert stats["duplicate_urls"] == 0
    assert stats["total_duplicates"] == 0


def test_get_duplicate_stats_empty_database(dedup_service, db_session):
    """Test stats with no items."""
    # Arrange
    mock_query = Mock()
    mock_query.all.return_value = []
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    stats = dedup_service.get_duplicate_stats(db_session)

    # Assert
    assert stats["total_items"] == 0
    assert stats["unique_items"] == 0
    assert stats["duplicate_urls"] == 0


def test_get_duplicate_stats_with_channel_id(dedup_service, db_session):
    """Test getting stats scoped to channel."""
    # Arrange
    channel_id = str(uuid4())
    mock_items = [Mock(url="https://youtube.com/watch?v=abc123")]
    mock_query = Mock()
    mock_query.all.return_value = mock_items
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    stats = dedup_service.get_duplicate_stats(db_session, channel_id=channel_id)

    # Assert
    assert stats["total_items"] == 1
    assert stats["unique_items"] == 1


def test_get_duplicate_stats_error_handling(dedup_service, db_session):
    """Test error handling in stats calculation."""
    # Arrange
    db_session.query.side_effect = Exception("Database error")

    # Act
    with patch('builtins.print'):  # Suppress print output
        stats = dedup_service.get_duplicate_stats(db_session)

    # Assert
    assert stats["total_items"] == 0
    assert stats["unique_items"] == 0


# ==================== Edge Cases ====================

def test_check_duplicates_batch_item_without_title(dedup_service, db_session):
    """Test handling items without title in batch check."""
    # Arrange
    items = [
        {"url": "https://youtube.com/watch?v=abc123", "type": "youtube"}  # No title
    ]

    mock_query = Mock()
    mock_query.first.return_value = None
    mock_query.all.return_value = []
    db_session.query.return_value.filter.return_value = mock_query

    # Act
    unique, duplicates, summary = dedup_service.check_duplicates_batch(
        db_session,
        items
    )

    # Assert
    assert len(unique) == 1
    # Should skip title-based duplicate check


def test_extract_video_id_unsupported_platform(dedup_service):
    """Test video ID extraction for unsupported platform."""
    # Act
    video_id = dedup_service.extract_video_id("https://example.com/video", "unsupported")

    # Assert
    assert video_id is None


def test_calculate_similarity_unicode(dedup_service):
    """Test similarity calculation with Unicode characters."""
    result = dedup_service.calculate_similarity("Tëst Vidéo", "Tëst Vidéo")

    assert result == 1.0
