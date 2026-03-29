"""
Unit tests for ImportService.

Tests import operations from various platforms:
- YouTube playlists
- Vimeo albums
- Local media libraries

Coverage includes:
- Import job creation and validation
- Item fetching from different platforms
- Deduplication integration
- Import processing
- Playlist creation from imports
- Job management (cancel, pause, resume)
- Error handling
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4, UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from src.services.import_service import ImportService
from src.models.import_job import ImportJob, ImportPlatform, ImportStatus
from src.models.playlist import Playlist, PlaylistItem
from src.schemas.import_schemas import ImportCreateRequest


# ==================== Fixtures ====================

@pytest.fixture
def import_service():
    """Get ImportService instance."""
    return ImportService()


@pytest.fixture
def db_session():
    """Mock database session."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid4()


@pytest.fixture
def sample_channel_id():
    """Sample channel ID for testing."""
    return uuid4()


@pytest.fixture
def youtube_import_request():
    """Sample YouTube import request."""
    return ImportCreateRequest(
        platform=ImportPlatform.YOUTUBE,
        source_url="https://www.youtube.com/playlist?list=PL1234567890",
        channel_id=uuid4(),
        options={"deduplicate": True}
    )


@pytest.fixture
def vimeo_import_request():
    """Sample Vimeo import request."""
    return ImportCreateRequest(
        platform=ImportPlatform.VIMEO,
        source_url="https://vimeo.com/album/1234567",
        options={"deduplicate": False}
    )


@pytest.fixture
def local_import_request():
    """Sample local import request."""
    return ImportCreateRequest(
        platform=ImportPlatform.LOCAL,
        source_path="/path/to/music",
        options={"recursive": True, "file_types": [".mp3", ".wav"]}
    )


@pytest.fixture
def sample_import_job(db_session, sample_user_id, sample_channel_id):
    """Sample ImportJob for testing."""
    job = ImportJob(
        id=uuid4(),
        user_id=sample_user_id,
        channel_id=sample_channel_id,
        platform=ImportPlatform.YOUTUBE,
        source_url="https://www.youtube.com/playlist?list=PL1234567890",
        status=ImportStatus.PENDING,
        options={"deduplicate": True}
    )
    return job


@pytest.fixture
def sample_items():
    """Sample items list for testing."""
    return [
        {
            "url": "https://youtube.com/watch?v=abc123",
            "title": "Test Video 1",
            "duration": 180,
            "thumbnail": "https://example.com/thumb1.jpg",
            "type": "youtube"
        },
        {
            "url": "https://youtube.com/watch?v=def456",
            "title": "Test Video 2",
            "duration": 240,
            "thumbnail": "https://example.com/thumb2.jpg",
            "type": "youtube"
        }
    ]


# ==================== Import Job Creation Tests ====================

def test_create_import_job_youtube(import_service, db_session, youtube_import_request, sample_user_id):
    """Test creating import job for YouTube platform."""
    # Act
    job = import_service.create_import_job(db_session, youtube_import_request, sample_user_id)

    # Assert
    assert job.user_id == sample_user_id
    assert job.platform == ImportPlatform.YOUTUBE
    assert job.source_url == youtube_import_request.source_url
    assert job.status == ImportStatus.PENDING
    assert job.options == youtube_import_request.options
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()
    db_session.refresh.assert_called_once()


def test_create_import_job_vimeo(import_service, db_session, vimeo_import_request, sample_user_id):
    """Test creating import job for Vimeo platform."""
    # Act
    job = import_service.create_import_job(db_session, vimeo_import_request, sample_user_id)

    # Assert
    assert job.platform == ImportPlatform.VIMEO
    assert job.source_url == vimeo_import_request.source_url
    assert job.status == ImportStatus.PENDING
    db_session.add.assert_called_once()


def test_create_import_job_local(import_service, db_session, local_import_request, sample_user_id):
    """Test creating import job for local files."""
    # Act
    job = import_service.create_import_job(db_session, local_import_request, sample_user_id)

    # Assert
    assert job.platform == ImportPlatform.LOCAL
    assert job.source_path == local_import_request.source_path
    assert job.options == local_import_request.options
    db_session.add.assert_called_once()


def test_create_import_job_youtube_missing_url(import_service, db_session, sample_user_id):
    """Test that YouTube import fails without source_url."""
    request = ImportCreateRequest(
        platform=ImportPlatform.YOUTUBE,
        source_url=None
    )

    # Act & Assert
    with pytest.raises(ValueError, match="source_url is required for YouTube imports"):
        import_service.create_import_job(db_session, request, sample_user_id)


def test_create_import_job_local_missing_path(import_service, db_session, sample_user_id):
    """Test that local import fails without source_path."""
    request = ImportCreateRequest(
        platform=ImportPlatform.LOCAL,
        source_path=None
    )

    # Act & Assert
    with pytest.raises(ValueError, match="source_path is required for local imports"):
        import_service.create_import_job(db_session, request, sample_user_id)


# ==================== Fetch Items Tests ====================

@patch('src.services.import_service.extract_video_metadata')
def test_fetch_youtube_items_single_video(mock_extract, import_service):
    """Test fetching single YouTube video."""
    # Arrange
    mock_extract.return_value = {
        "url": "https://youtube.com/watch?v=abc123",
        "title": "Test Video",
        "duration": 180,
        "thumbnail": "https://example.com/thumb.jpg",
        "extractor": "youtube"
    }

    # Act
    items, metadata = import_service._fetch_youtube_items(
        "https://youtube.com/watch?v=abc123",
        {}
    )

    # Assert
    assert len(items) == 1
    assert items[0]["title"] == "Test Video"
    assert items[0]["url"] == "https://youtube.com/watch?v=abc123"
    assert metadata["extractor"] == "youtube"


@patch('src.services.import_service.extract_video_metadata')
def test_fetch_youtube_items_playlist(mock_extract, import_service):
    """Test fetching YouTube playlist."""
    # Arrange
    mock_extract.return_value = {
        "is_playlist": True,
        "playlist_title": "Test Playlist",
        "playlist_id": "PL123456",
        "extractor": "youtube",
        "entries": [
            {
                "url": "https://youtube.com/watch?v=abc123",
                "title": "Video 1",
                "duration": 180
            },
            {
                "url": "https://youtube.com/watch?v=def456",
                "title": "Video 2",
                "duration": 240
            }
        ]
    }

    # Act
    items, metadata = import_service._fetch_youtube_items(
        "https://www.youtube.com/playlist?list=PL123456",
        {}
    )

    # Assert
    assert len(items) == 2
    assert items[0]["title"] == "Video 1"
    assert items[1]["title"] == "Video 2"
    assert metadata["playlist_title"] == "Test Playlist"
    assert metadata["playlist_id"] == "PL123456"


@patch('src.services.import_service.extract_video_metadata')
def test_fetch_youtube_items_error(mock_extract, import_service):
    """Test error handling when fetching YouTube items fails."""
    # Arrange
    mock_extract.return_value = {"error": "Video not found"}

    # Act & Assert
    with pytest.raises(ValueError, match="Failed to fetch YouTube metadata"):
        import_service._fetch_youtube_items("https://youtube.com/watch?v=invalid", {})


@patch('src.services.import_service.extract_video_metadata')
def test_fetch_vimeo_items_single_video(mock_extract, import_service):
    """Test fetching single Vimeo video."""
    # Arrange
    mock_extract.return_value = {
        "url": "https://vimeo.com/123456789",
        "title": "Vimeo Video",
        "duration": 300,
        "extractor": "vimeo"
    }

    # Act
    items, metadata = import_service._fetch_vimeo_items(
        "https://vimeo.com/123456789",
        {}
    )

    # Assert
    assert len(items) == 1
    assert items[0]["title"] == "Vimeo Video"
    assert items[0]["type"] == "vimeo"


@patch('src.services.import_service.extract_video_metadata')
def test_fetch_vimeo_items_album(mock_extract, import_service):
    """Test fetching Vimeo album."""
    # Arrange
    mock_extract.return_value = {
        "is_playlist": True,
        "playlist_title": "Vimeo Album",
        "extractor": "vimeo",
        "entries": [
            {"url": "https://vimeo.com/123", "title": "Video 1", "duration": 180},
            {"url": "https://vimeo.com/456", "title": "Video 2", "duration": 240}
        ]
    }

    # Act
    items, metadata = import_service._fetch_vimeo_items(
        "https://vimeo.com/album/1234567",
        {}
    )

    # Assert
    assert len(items) == 2
    assert metadata["album_title"] == "Vimeo Album"


@patch('os.path.exists')
@patch('os.path.isfile')
@patch('os.stat')
def test_fetch_local_items_single_file(mock_stat, mock_isfile, mock_exists, import_service):
    """Test fetching single local file."""
    # Arrange
    mock_exists.return_value = True
    mock_isfile.return_value = True
    mock_stat.return_value = Mock(st_size=1024000)

    # Act
    items, metadata = import_service._fetch_local_items(
        "/path/to/video.mp4",
        {}
    )

    # Assert
    assert len(items) == 1
    assert items[0]["url"] == "/path/to/video.mp4"
    assert items[0]["title"] == "video.mp4"
    assert items[0]["type"] == "local"
    assert items[0]["file_size"] == 1024000


@patch('os.path.exists')
def test_fetch_local_items_path_not_exists(mock_exists, import_service):
    """Test error handling when path doesn't exist."""
    # Arrange
    mock_exists.return_value = False

    # Act & Assert
    with pytest.raises(ValueError, match="Path does not exist"):
        import_service._fetch_local_items("/invalid/path", {})


@patch('os.path.exists')
@patch('os.path.isfile')
@patch('os.listdir')
@patch('os.path.join')
def test_fetch_local_items_directory_non_recursive(mock_join, mock_listdir, mock_isfile, mock_exists, import_service):
    """Test fetching files from directory non-recursively."""
    # Arrange
    mock_exists.return_value = True
    mock_isfile.return_value = True
    mock_listdir.return_value = ["song1.mp3", "song2.wav", "video.mp4"]
    mock_join.side_effect = lambda *args: "/".join(args)

    with patch('os.stat') as mock_stat:
        mock_stat.return_value = Mock(st_size=1024000)

        # Act
        items, metadata = import_service._fetch_local_items(
            "/path/to/music",
            {"recursive": False}
        )

    # Assert
    assert len(items) == 3
    assert metadata["file_count"] == 3
    assert metadata["recursive"] is False


# ==================== Process Import Tests ====================

@patch.object(ImportService, 'fetch_import_items')
def test_process_import_success(mock_fetch, import_service, db_session, sample_import_job, sample_items):
    """Test successful import processing."""
    # Arrange
    mock_fetch.return_value = (sample_items, {"playlist_title": "Test"})

    with patch.object(import_service.deduplication_service, 'check_duplicates_batch') as mock_dup:
        mock_dup.return_value = (sample_items, [], {"unique": 2, "duplicates": 0})

        # Act
        result = import_service.process_import(db_session, sample_import_job)

    # Assert
    assert result.status == ImportStatus.COMPLETED
    assert result.total_items == 2
    assert result.successful_items == 2
    db_session.commit.assert_called()


@patch.object(ImportService, 'fetch_import_items')
def test_process_import_with_duplicates(mock_fetch, import_service, db_session, sample_import_job):
    """Test import processing with duplicate detection."""
    # Arrange
    items = [
        {"url": "https://youtube.com/watch?v=abc123", "title": "Video 1", "type": "youtube"},
        {"url": "https://youtube.com/watch?v=def456", "title": "Video 2", "type": "youtube"}
    ]
    mock_fetch.return_value = (items, {"playlist_title": "Test"})

    with patch.object(import_service.deduplication_service, 'check_duplicates_batch') as mock_dup:
        # First item is unique, second is duplicate
        mock_dup.return_value = (
            [items[0]],
            [items[1]],
            {"unique": 1, "duplicates": 1}
        )

        # Act
        result = import_service.process_import(db_session, sample_import_job)

    # Assert
    assert result.status == ImportStatus.COMPLETED
    assert result.results["summary"]["imported"] == 1
    assert result.results["summary"]["duplicates"] == 1


@patch.object(ImportService, 'fetch_import_items')
def test_process_import_without_deduplication(mock_fetch, import_service, db_session, sample_import_job, sample_items):
    """Test import processing with deduplication disabled."""
    # Arrange
    sample_import_job.options = {"deduplicate": False}
    mock_fetch.return_value = (sample_items, {"playlist_title": "Test"})

    # Act
    result = import_service.process_import(db_session, sample_import_job)

    # Assert
    assert result.status == ImportStatus.COMPLETED
    assert result.results["summary"]["imported"] == 2


@patch.object(ImportService, 'fetch_import_items')
def test_process_import_error_handling(mock_fetch, import_service, db_session, sample_import_job):
    """Test error handling during import processing."""
    # Arrange
    mock_fetch.side_effect = Exception("Network error")

    # Act
    result = import_service.process_import(db_session, sample_import_job)

    # Assert
    assert result.status == ImportStatus.FAILED
    assert "Network error" in result.error_message


# ==================== Create Playlist Tests ====================

def test_create_playlist_from_import_success(import_service, db_session, sample_import_job, sample_user_id):
    """Test creating playlist from completed import."""
    # Arrange
    sample_import_job.status = ImportStatus.COMPLETED
    sample_import_job.results = {
        "imported": [
            {"url": "https://youtube.com/watch?v=abc", "title": "Video 1", "duration": 180},
            {"url": "https://youtube.com/watch?v=def", "title": "Video 2", "duration": 240}
        ],
        "summary": {"imported": 2}
    }

    # Act
    playlist = import_service.create_playlist_from_import(
        db_session,
        sample_import_job,
        "My Imported Playlist",
        "Test description",
        sample_user_id
    )

    # Assert
    assert playlist.name == "My Imported Playlist"
    assert playlist.description == "Test description"
    assert playlist.items_count == 2
    assert playlist.total_duration == 420
    assert playlist.color == "#8B5CF6"
    assert playlist.icon == "download"


def test_create_playlist_from_import_not_completed(import_service, db_session, sample_import_job, sample_user_id):
    """Test that playlist creation fails for non-completed imports."""
    # Arrange
    sample_import_job.status = ImportStatus.PENDING

    # Act & Assert
    with pytest.raises(ValueError, match="Can only create playlist from completed import job"):
        import_service.create_playlist_from_import(
            db_session,
            sample_import_job,
            "Test Playlist",
            user_id=sample_user_id
        )


def test_create_playlist_from_import_no_items(import_service, db_session, sample_import_job, sample_user_id):
    """Test that playlist creation fails when no items were imported."""
    # Arrange
    sample_import_job.status = ImportStatus.COMPLETED
    sample_import_job.results = {"imported": [], "summary": {"imported": 0}}

    # Act & Assert
    with pytest.raises(ValueError, match="No items were imported successfully"):
        import_service.create_playlist_from_import(
            db_session,
            sample_import_job,
            "Test Playlist",
            user_id=sample_user_id
        )


# ==================== Job Management Tests ====================

def test_cancel_import(import_service, db_session, sample_import_job):
    """Test cancelling an import job."""
    # Arrange
    sample_import_job.status = ImportStatus.PENDING

    # Act
    result = import_service.cancel_import(db_session, sample_import_job)

    # Assert
    assert result.status == ImportStatus.CANCELLED
    db_session.commit.assert_called_once()


def test_cancel_import_already_completed(import_service, db_session, sample_import_job):
    """Test that completed jobs cannot be cancelled."""
    # Arrange
    sample_import_job.status = ImportStatus.COMPLETED

    # Act & Assert
    with pytest.raises(ValueError, match="Cannot cancel job with status COMPLETED"):
        import_service.cancel_import(db_session, sample_import_job)


def test_pause_import(import_service, db_session, sample_import_job):
    """Test pausing an import job."""
    # Arrange
    sample_import_job.status = ImportStatus.IN_PROGRESS

    # Act
    result = import_service.pause_import(db_session, sample_import_job)

    # Assert
    assert result.status == ImportStatus.PAUSED
    db_session.commit.assert_called_once()


def test_pause_import_not_in_progress(import_service, db_session, sample_import_job):
    """Test that only in-progress jobs can be paused."""
    # Arrange
    sample_import_job.status = ImportStatus.PENDING

    # Act & Assert
    with pytest.raises(ValueError, match="Can only pause in-progress jobs"):
        import_service.pause_import(db_session, sample_import_job)


def test_resume_import(import_service, db_session, sample_import_job):
    """Test resuming a paused import job."""
    # Arrange
    sample_import_job.status = ImportStatus.PAUSED

    # Act
    result = import_service.resume_import(db_session, sample_import_job)

    # Assert
    assert result.status == ImportStatus.IN_PROGRESS
    db_session.commit.assert_called_once()


def test_resume_import_not_paused(import_service, db_session, sample_import_job):
    """Test that only paused jobs can be resumed."""
    # Arrange
    sample_import_job.status = ImportStatus.PENDING

    # Act & Assert
    with pytest.raises(ValueError, match="Can only resume paused jobs"):
        import_service.resume_import(db_session, sample_import_job)


# ==================== Summary Tests ====================

def test_get_import_summary(import_service, sample_import_job):
    """Test getting import summary."""
    # Arrange
    sample_import_job.status = ImportStatus.COMPLETED
    sample_import_job.started_at = datetime.now(timezone.utc)
    sample_import_job.completed_at = datetime.now(timezone.utc)
    sample_import_job.total_items = 10
    sample_import_job.results = {
        "summary": {
            "total": 10,
            "imported": 8,
            "duplicates": 1,
            "failed": 1
        },
        "failed": [{"error": "Network error"}]
    }

    # Act
    summary = import_service.get_import_summary(sample_import_job)

    # Assert
    assert summary["total_items"] == 10
    assert summary["imported_count"] == 8
    assert summary["duplicate_count"] == 1
    assert summary["failed_count"] == 1
    assert summary["duration_seconds"] is not None
    assert len(summary["errors"]) == 1


def test_get_import_summary_in_progress(import_service, sample_import_job):
    """Test getting summary for in-progress import."""
    # Arrange
    sample_import_job.status = ImportStatus.IN_PROGRESS
    sample_import_job.started_at = datetime.now(timezone.utc)
    sample_import_job.total_items = 100
    sample_import_job.processed_items = 50
    sample_import_job.successful_items = 45
    sample_import_job.failed_items = 5

    # Act
    summary = import_service.get_import_summary(sample_import_job)

    # Assert
    assert summary["status"] == "in_progress"
    assert summary["total_items"] == 100
    assert summary["imported_count"] == 45
    assert summary["failed_count"] == 5
    assert summary["duration_seconds"] is None  # Not completed yet


# ==================== Edge Cases ====================

def test_fetch_import_items_unsupported_platform(import_service):
    """Test error handling for unsupported platform."""
    from src.models.import_job import ImportPlatform

    # Act & Assert
    with pytest.raises(ValueError, match="Unsupported platform"):
        import_service.fetch_import_items(
            platform=ImportPlatform.YOUTUBE,  # Valid but testing error path
            source_url=None,
            source_path=None
        )


def test_process_import_empty_items_list(import_service, db_session, sample_import_job):
    """Test processing import with empty items list."""
    with patch.object(ImportService, 'fetch_import_items') as mock_fetch:
        # Arrange
        mock_fetch.return_value = ([], {"empty": True})

        with patch.object(import_service.deduplication_service, 'check_duplicates_batch') as mock_dup:
            mock_dup.return_value = ([], [], {"unique": 0, "duplicates": 0})

            # Act
            result = import_service.process_import(db_session, sample_import_job)

    # Assert
    assert result.status == ImportStatus.COMPLETED
    assert result.results["summary"]["total"] == 0
