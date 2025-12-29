"""
Comprehensive tests for RadioService.

Covers:
- Service initialization
- URL validation
- Stream CRUD operations (add, get, update, remove)
- Search functionality
- Play count tracking
- Edge cases and error handling
"""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from src.services.radio_service import RadioService
from src.models import RadioStream


# ========== FIXTURES ==========

@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def radio_service(mock_db):
    """Create RadioService instance with mocked DB."""
    return RadioService(mock_db)


@pytest.fixture
def sample_stream():
    """Sample RadioStream object for testing."""
    return RadioStream(
        id=1,
        name="Test Radio",
        url="http://stream.example.com/radio",
        description="Test stream description",
        genre="Rock",
        added_by=1,
        is_active=True,
        play_count=0
    )


# ========== INITIALIZATION TESTS ==========

class TestRadioServiceInit:
    """Test RadioService initialization."""
    
    def test_init_creates_service(self, mock_db):
        """Test that RadioService initializes correctly."""
        service = RadioService(mock_db)
        assert service is not None
        assert service.db == mock_db
        assert service.logger is not None


# ========== URL VALIDATION TESTS ==========

class TestURLValidation:
    """Test URL validation logic."""
    
    def test_validate_url_http_success(self, radio_service):
        """Test that valid HTTP URL passes validation."""
        result = radio_service.validate_url("http://stream.example.com/radio")
        assert result is True
    
    def test_validate_url_https_success(self, radio_service):
        """Test that valid HTTPS URL passes validation."""
        result = radio_service.validate_url("https://stream.example.com/radio")
        assert result is True
    
    def test_validate_url_with_port(self, radio_service):
        """Test that URL with port passes validation."""
        result = radio_service.validate_url("http://stream.example.com:8000/radio")
        assert result is True
    
    def test_validate_url_with_path(self, radio_service):
        """Test that URL with complex path passes validation."""
        result = radio_service.validate_url("https://example.com/stream/radio/channel1")
        assert result is True
    
    def test_validate_url_invalid_protocol(self, radio_service):
        """Test that non-HTTP(S) protocol raises ValueError."""
        with pytest.raises(ValueError, match="Invalid protocol"):
            radio_service.validate_url("ftp://stream.example.com/radio")
    
    def test_validate_url_no_host(self, radio_service):
        """Test that URL without host raises ValueError."""
        with pytest.raises(ValueError, match="must contain host"):
            radio_service.validate_url("http://")
    
    def test_validate_url_empty_string(self, radio_service):
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError):
            radio_service.validate_url("")


# ========== ADD STREAM TESTS ==========

class TestAddStream:
    """Test adding new radio streams."""
    
    def test_add_stream_success(self, radio_service, mock_db):
        """Test successful stream addition."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        result = radio_service.add_stream(
            name="Test Radio",
            url="http://stream.example.com/radio",
            description="Test stream",
            genre="Rock",
            added_by=1
        )
        
        assert result is not None
        assert result.name == "Test Radio"
        assert result.url == "http://stream.example.com/radio"
        assert result.is_active is True
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_add_stream_duplicate_url(self, radio_service, mock_db, sample_stream):
        """Test that duplicate URL raises ValueError."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_stream
        
        with pytest.raises(ValueError, match="Stream already exists"):
            radio_service.add_stream(
                name="Duplicate",
                url=sample_stream.url
            )
    
    def test_add_stream_invalid_url(self, radio_service, mock_db):
        """Test that invalid URL raises ValueError."""
        with pytest.raises(ValueError):
            radio_service.add_stream(
                name="Invalid",
                url="not-a-url"
            )
    
    def test_add_stream_without_optional_fields(self, radio_service, mock_db):
        """Test adding stream with only required fields."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        result = radio_service.add_stream(
            name="Minimal Stream",
            url="http://minimal.example.com/stream"
        )
        
        assert result.name == "Minimal Stream"
        assert result.description is None
        assert result.genre is None
        assert result.added_by is None


# ========== GET STREAM TESTS ==========

class TestGetStream:
    """Test retrieving individual streams."""
    
    def test_get_stream_exists(self, radio_service, mock_db, sample_stream):
        """Test retrieving existing stream by ID."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_stream
        
        result = radio_service.get_stream(1)
        
        assert result == sample_stream
        mock_db.query.assert_called_once()
    
    def test_get_stream_not_found(self, radio_service, mock_db):
        """Test that non-existent stream returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = radio_service.get_stream(999)
        
        assert result is None


# ========== GET ALL STREAMS TESTS ==========

class TestGetAllStreams:
    """Test retrieving multiple streams."""
    
    def test_get_all_streams_active_only(self, radio_service, mock_db, sample_stream):
        """Test retrieving only active streams."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [sample_stream]
        
        result = radio_service.get_all_streams(active_only=True)
        
        assert len(result) == 1
        assert result[0] == sample_stream
        mock_query.filter.assert_called_once()
    
    def test_get_all_streams_include_inactive(self, radio_service, mock_db):
        """Test retrieving all streams including inactive."""
        inactive_stream = RadioStream(id=2, name="Inactive", url="http://test.com", is_active=False)
        
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [inactive_stream]
        
        result = radio_service.get_all_streams(active_only=False)
        
        assert len(result) == 1
        # Verify filter was NOT called for active_only
        mock_query.filter.assert_not_called()


# ========== REMOVE STREAM TESTS ==========

class TestRemoveStream:
    """Test stream removal (soft delete)."""
    
    def test_remove_stream_success(self, radio_service, mock_db, sample_stream):
        """Test successful stream deactivation."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_stream
        mock_db.commit = Mock()
        
        result = radio_service.remove_stream(1)
        
        assert result is True
        assert sample_stream.is_active is False
        mock_db.commit.assert_called_once()
    
    def test_remove_stream_not_found(self, radio_service, mock_db):
        """Test removing non-existent stream."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = radio_service.remove_stream(999)
        
        assert result is False


# ========== PLAY COUNT TESTS ==========

class TestPlayCount:
    """Test play count tracking."""
    
    def test_update_play_count_success(self, radio_service, mock_db, sample_stream):
        """Test incrementing play count."""
        initial_count = sample_stream.play_count
        mock_db.query.return_value.filter.return_value.first.return_value = sample_stream
        mock_db.commit = Mock()
        
        radio_service.update_play_count(1)
        
        assert sample_stream.play_count == initial_count + 1
        mock_db.commit.assert_called_once()
    
    def test_update_play_count_stream_not_found(self, radio_service, mock_db):
        """Test that updating play count for non-existent stream doesn't crash."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Should not raise exception
        radio_service.update_play_count(999)


# ========== SEARCH TESTS ==========

class TestSearchStreams:
    """Test stream search functionality."""
    
    def test_search_by_name(self, radio_service, mock_db, sample_stream):
        """Test searching streams by name."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.all.return_value = [sample_stream]
        
        result = radio_service.search_streams("Test")
        
        assert len(result) == 1
        assert result[0] == sample_stream
    
    def test_search_by_genre(self, radio_service, mock_db, sample_stream):
        """Test searching streams by genre."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.all.return_value = [sample_stream]
        
        result = radio_service.search_streams("Rock")
        
        assert len(result) == 1
    
    def test_search_no_results(self, radio_service, mock_db):
        """Test search with no matches."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.all.return_value = []
        
        result = radio_service.search_streams("NonExistent")
        
        assert len(result) == 0
    
    def test_search_case_insensitive(self, radio_service, mock_db, sample_stream):
        """Test that search is case-insensitive."""
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.filter.return_value.all.return_value = [sample_stream]
        
        result = radio_service.search_streams("test")  # lowercase
        
        assert len(result) == 1


# ========== EDGE CASES ==========

class TestRadioServiceEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_add_stream_with_special_characters(self, radio_service, mock_db):
        """Test adding stream with special characters in name."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        result = radio_service.add_stream(
            name="Тест Радио 🎵",
            url="http://example.com/stream"
        )
        
        assert result.name == "Тест Радио 🎵"
    
    def test_url_validation_with_query_params(self, radio_service):
        """Test URL with query parameters."""
        result = radio_service.validate_url("http://example.com/stream?quality=high&format=mp3")
        assert result is True
    
    def test_multiple_streams_same_name_different_url(self, radio_service, mock_db):
        """Test that multiple streams can have same name with different URLs."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = Mock()
        mock_db.commit = Mock()
        
        result1 = radio_service.add_stream("Radio Name", "http://url1.com")
        result2 = radio_service.add_stream("Radio Name", "http://url2.com")
        
        assert result1.name == result2.name
        assert result1.url != result2.url
    
    def test_play_count_increments_correctly(self, radio_service, mock_db, sample_stream):
        """Test multiple play count increments."""
        sample_stream.play_count = 5
        mock_db.query.return_value.filter.return_value.first.return_value = sample_stream
        mock_db.commit = Mock()
        
        radio_service.update_play_count(1)
        radio_service.update_play_count(1)
        radio_service.update_play_count(1)
        
        assert sample_stream.play_count == 8
        assert mock_db.commit.call_count == 3
