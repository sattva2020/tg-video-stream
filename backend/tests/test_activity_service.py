"""
Comprehensive tests for ActivityService
Target: 70%+ coverage of activity_service.py (105 executable lines)

Test coverage:
- __init__ and service initialization
- log_event (event creation, commit, refresh, auto-cleanup trigger)
- get_events (pagination, filtering by event_type, search, validation)
- _cleanup_old_events (гистерезис, subquery logic, exception handling)
- cleanup_old_events (public cleanup with max_events parameter)
- delete_all_events (admin functionality)
- Helper functions (log_user_login, log_stream_start, etc.)
- Error handling (DB rollback, logging)
- Edge cases (empty results, boundary values)
"""
import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch, call

import pytest
from sqlalchemy.orm import Session

from api.schemas.system import ActivityEventResponse
from services.activity_service import (
    ActivityService,
    get_activity_service,
    log_user_login,
    log_user_logout,
    log_stream_start,
    log_stream_stop,
    log_stream_error,
    log_track_added,
    log_track_removed,
    log_playlist_updated,
    log_system_warning,
    log_system_error,
    MAX_EVENTS,
    CLEANUP_THRESHOLD,
)


# ======================== FIXTURES ========================
@pytest.fixture
def mock_activity_event():
    """Mock ActivityEvent model to avoid SQLAlchemy table conflicts."""
    with patch("services.activity_service.ActivityEvent") as mock_model, \
         patch("services.activity_service.desc") as mock_desc:
        # Setup created_at attribute for ordering
        mock_model.created_at = MagicMock()
        # desc() just returns a mock that order_by can use
        mock_desc.return_value = MagicMock()
        yield mock_model


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy session."""
    session = MagicMock(spec=Session)
    
    # Create mock query object for chaining
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []
    mock_query.count.return_value = 0
    mock_query.scalar.return_value = 0
    mock_query.delete.return_value = 0
    mock_query.subquery.return_value = MagicMock()
    
    # session.query() returns mock_query
    session.query.return_value = mock_query
    
    return session


@pytest.fixture
def activity_service(mock_db_session, mock_activity_event):
    """ActivityService instance with mocked DB and ActivityEvent."""
    return ActivityService(db=mock_db_session)


@pytest.fixture
def sample_events():
    """Sample activity events - plain Mock objects to avoid SQLAlchemy conflicts."""
    events = []
    for i in range(5):
        event = Mock()  # Plain Mock, not spec=ActivityEvent
        event.id = i + 1
        event.type = "user_login" if i % 2 == 0 else "stream_start"
        event.message = f"Test event {i+1}"
        event.user_email = f"user{i+1}@example.com"
        event.details = {"test": f"data{i+1}"}
        event.created_at = datetime(2025, 12, 28, 10, i, 0, tzinfo=timezone.utc)
        events.append(event)
    return events


# ======================== TEST CLASSES ========================

class TestActivityServiceInit:
    """Test ActivityService initialization."""

    def test_init_with_db_session(self, mock_db_session):
        """Test service initialization with DB session."""
        service = ActivityService(db=mock_db_session)
        assert service.db is mock_db_session


class TestActivityServiceLogEvent:
    """Test log_event method."""

    def test_log_event_basic(self, activity_service, mock_db_session, mock_activity_event):
        """Test logging event with basic parameters."""
        with patch("services.activity_service.logger") as mock_logger:
            # Setup mock event instance
            mock_event_instance = Mock()
            mock_event_instance.id = 1
            mock_event_instance.type = "user_login"
            mock_event_instance.message = "User logged in"
            mock_activity_event.return_value = mock_event_instance
            
            # Mock cleanup to not trigger
            with patch.object(activity_service, "_cleanup_old_events"):
                result = activity_service.log_event("user_login", "User logged in")
            
            # Verify ActivityEvent creation
            mock_activity_event.assert_called_once_with(
                type="user_login",
                message="User logged in",
                user_email=None,
                details=None
            )
            
            # Verify commit and refresh
            mock_db_session.add.assert_called_once_with(mock_event_instance)
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once_with(mock_event_instance)
            
            # Verify logging
            mock_logger.info.assert_called_once()
            assert "user_login" in mock_logger.info.call_args[0][0]

    def test_log_event_with_all_parameters(self, activity_service, mock_db_session, mock_activity_event):
        """Test logging event with all optional parameters."""
        mock_event_instance = Mock()
        mock_activity_event.return_value = mock_event_instance
        
        with patch.object(activity_service, "_cleanup_old_events"):
            result = activity_service.log_event(
                event_type="stream_start",
                message="Stream started",
                user_id=123,  # Для совместимости, но не сохраняется
                user_email="admin@example.com",
                details={"ip": "192.168.1.1", "browser": "Chrome"}
            )
            
            mock_activity_event.assert_called_once_with(
                type="stream_start",
                message="Stream started",
                user_email="admin@example.com",
                details={"ip": "192.168.1.1", "browser": "Chrome"}
            )

    def test_log_event_triggers_cleanup(self, activity_service, mock_db_session, mock_activity_event):
        """Test that log_event triggers automatic cleanup."""
        mock_event_instance = Mock()
        mock_activity_event.return_value = mock_event_instance
        
        with patch.object(activity_service, "_cleanup_old_events") as mock_cleanup:
            activity_service.log_event("test_event", "Test message")
            mock_cleanup.assert_called_once()


class TestActivityServiceGetEvents:
    """Test get_events method."""

    def test_get_events_default_parameters(self, activity_service, mock_db_session, sample_events):
        """Test get_events with default parameters (limit=20, offset=0)."""
        # Setup mock query chain returns
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = sample_events[:3]
        mock_query.count.return_value = 3
        
        result = activity_service.get_events()
        
        # Verify query was called for ActivityEvent
        mock_db_session.query.assert_called()
        # Verify pagination
        mock_query.limit.assert_called_with(20)
        mock_query.offset.assert_called_with(0)
        # Verify result
        assert result.total == 3
        assert len(result.events) == 3

    def test_get_events_with_pagination(self, activity_service, mock_db_session, sample_events):
        """Test get_events with custom limit and offset."""
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = sample_events[2:4]
        mock_query.count.return_value = 10
        
        result = activity_service.get_events(limit=2, offset=2)
        
        assert result.total == 10
        assert len(result.events) == 2
        mock_query.limit.assert_called_with(2)
        mock_query.offset.assert_called_with(2)

    def test_get_events_limit_validation(self, activity_service, mock_db_session):
        """Test get_events validates limit (min=1, max=100)."""
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        # Test min limit
        activity_service.get_events(limit=0)
        mock_query.limit.assert_called_with(1)
        
        # Test max limit
        activity_service.get_events(limit=200)
        mock_query.limit.assert_called_with(100)
        
        # Test negative limit
        activity_service.get_events(limit=-5)
        mock_query.limit.assert_called_with(1)

    def test_get_events_offset_validation(self, activity_service, mock_db_session):
        """Test get_events validates offset (min=0)."""
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        # Test negative offset
        activity_service.get_events(offset=-10)
        mock_query.offset.assert_called_with(0)

    def test_get_events_filter_by_event_type(self, activity_service, mock_db_session, sample_events):
        """Test get_events filters by event_type."""
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = [sample_events[0], sample_events[2]]
        mock_query.count.return_value = 2
        
        result = activity_service.get_events(event_type="user_login")
        
        # Verify filter was applied
        mock_query.filter.assert_called()
        assert result.total == 2

    def test_get_events_search_by_message(self, activity_service, mock_db_session, sample_events):
        """Test get_events searches in message field."""
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = [sample_events[0]]
        mock_query.count.return_value = 1
        
        result = activity_service.get_events(search="event 1")
        
        # Verify ilike filter was applied
        mock_query.filter.assert_called()
        assert result.total == 1

    def test_get_events_combined_filters(self, activity_service, mock_db_session, sample_events):
        """Test get_events with both event_type and search filters."""
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        result = activity_service.get_events(event_type="stream_start", search="test")
        
        # Verify both filters were applied
        assert mock_query.filter.call_count >= 2
        assert result.total == 0

    def test_get_events_empty_results(self, activity_service, mock_db_session):
        """Test get_events with no matching events."""
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = []
        mock_query.count.return_value = 0
        
        result = activity_service.get_events()
        
        assert result.total == 0
        assert len(result.events) == 0


class TestActivityServiceCleanupOldEvents:
    """Test _cleanup_old_events (private) and cleanup_old_events (public) methods."""

    def test_cleanup_old_events_below_threshold(self, activity_service, mock_db_session):
        """Test _cleanup_old_events does nothing when count <= MAX_EVENTS + CLEANUP_THRESHOLD."""
        mock_query = mock_db_session.query.return_value
        mock_query.scalar.return_value = MAX_EVENTS + CLEANUP_THRESHOLD  # Exactly at threshold
        
        result = activity_service._cleanup_old_events()
        
        # Should not execute deletion
        assert mock_query.delete.call_count == 0
        assert result is None

    def test_cleanup_old_events_above_threshold(self, activity_service, mock_db_session):
        """Test _cleanup_old_events deletes when count > MAX_EVENTS + CLEANUP_THRESHOLD."""
        mock_query = mock_db_session.query.return_value
        
        # First query().scalar() call for count check
        mock_query.scalar.return_value = MAX_EVENTS + CLEANUP_THRESHOLD + 50
        
        # Second query() for subquery creation
        subquery_mock = Mock()
        subquery_mock.select.return_value = "keep_ids_select"
        mock_query.subquery.return_value = subquery_mock
        
        # Third query() for delete operation
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = 50
        
        with patch("services.activity_service.logger") as mock_logger:
            result = activity_service._cleanup_old_events()
        
        assert result == 50
        mock_db_session.commit.assert_called()
        mock_logger.info.assert_called_once()
        assert "50" in mock_logger.info.call_args[0][0]

    def test_cleanup_old_events_exception_handling(self, activity_service, mock_db_session):
        """Test _cleanup_old_events handles exceptions and rolls back."""
        mock_db_session.scalar.return_value = MAX_EVENTS + CLEANUP_THRESHOLD + 100
        mock_db_session.query.side_effect = Exception("DB error")
        
        with patch("services.activity_service.logger") as mock_logger:
            result = activity_service._cleanup_old_events()
        
        assert result == 0
        mock_db_session.rollback.assert_called_once()
        mock_logger.error.assert_called_once()
        assert "Failed to cleanup" in mock_logger.error.call_args[0][0]

    def test_cleanup_old_events_public_method(self, activity_service, mock_db_session):
        """Test cleanup_old_events public method with custom max_events."""
        mock_query = mock_db_session.query.return_value
        
        # query().scalar() for count check
        mock_query.scalar.return_value = 500
        
        # Mock subquery and delete
        subquery_mock = Mock()
        subquery_mock.select.return_value = "keep_ids_select"
        mock_query.subquery.return_value = subquery_mock
        
        # Mock delete chain
        mock_query.filter.return_value = mock_query
        mock_query.delete.return_value = 100
        
        with patch("services.activity_service.logger") as mock_logger:
            result = activity_service.cleanup_old_events(max_events=400)
        
        assert result == 100
        mock_query.limit.assert_called_with(400)
        mock_logger.info.assert_called_once()

    def test_cleanup_old_events_public_no_cleanup_needed(self, activity_service, mock_db_session):
        """Test cleanup_old_events returns 0 when count <= max_events."""
        mock_query = mock_db_session.query.return_value
        mock_query.scalar.return_value = 50
        
        result = activity_service.cleanup_old_events(max_events=100)
        
        assert result == 0
        assert mock_db_session.commit.call_count == 0

    def test_cleanup_old_events_public_exception(self, activity_service, mock_db_session):
        """Test cleanup_old_events public method handles exceptions."""
        mock_query = mock_db_session.query.return_value
        mock_query.scalar.return_value = 200
        mock_db_session.query.side_effect = Exception("DB error")
        
        with patch("services.activity_service.logger") as mock_logger:
            result = activity_service.cleanup_old_events()
        
        assert result == 0
        mock_db_session.rollback.assert_called_once()
        mock_logger.error.assert_called_once()


class TestActivityServiceDeleteAllEvents:
    """Test delete_all_events method."""

    def test_delete_all_events_success(self, activity_service, mock_db_session):
        """Test successful deletion of all events."""
        mock_db_session.query.return_value.delete.return_value = 150
        
        with patch("services.activity_service.logger") as mock_logger:
            result = activity_service.delete_all_events()
        
        assert result == 150
        mock_db_session.commit.assert_called_once()
        mock_logger.info.assert_called_once()
        assert "150" in mock_logger.info.call_args[0][0]

    def test_delete_all_events_no_records(self, activity_service, mock_db_session):
        """Test delete_all_events when no records exist."""
        mock_db_session.query.return_value.delete.return_value = 0
        
        result = activity_service.delete_all_events()
        
        assert result == 0
        mock_db_session.commit.assert_called_once()

    def test_delete_all_events_exception(self, activity_service, mock_db_session):
        """Test delete_all_events handles exceptions."""
        mock_db_session.query.side_effect = Exception("DB error")
        
        with patch("services.activity_service.logger") as mock_logger:
            result = activity_service.delete_all_events()
        
        assert result == 0
        mock_db_session.rollback.assert_called_once()
        mock_logger.error.assert_called_once()


class TestActivityServiceFactory:
    """Test get_activity_service factory function."""

    def test_get_activity_service(self, mock_db_session):
        """Test factory function creates ActivityService instance."""
        service = get_activity_service(mock_db_session)
        assert isinstance(service, ActivityService)
        assert service.db is mock_db_session


class TestActivityServiceHelpers:
    """Test helper functions for logging events."""

    def test_log_user_login(self, mock_db_session):
        """Test log_user_login helper."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_user_login(mock_db_session, "user@example.com", ip="192.168.1.1")
            
            mock_factory.assert_called_once_with(mock_db_session)
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "user_login"
            assert "вошёл" in call_args[0][1]
            assert call_args[0][2] == "user@example.com"
            assert call_args[0][3] == {"ip": "192.168.1.1"}

    def test_log_user_login_without_ip(self, mock_db_session):
        """Test log_user_login without IP parameter."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_user_login(mock_db_session, "user@example.com")
            
            call_args = mock_service.log_event.call_args
            assert call_args[0][3] is None  # details

    def test_log_user_logout(self, mock_db_session):
        """Test log_user_logout helper."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_user_logout(mock_db_session, "user@example.com")
            
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "user_logout"
            assert "вышел" in call_args[0][1]

    def test_log_stream_start(self, mock_db_session):
        """Test log_stream_start helper."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_stream_start(mock_db_session, user_email="admin@example.com")
            
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "stream_start"
            assert "запущен" in call_args[0][1]
            assert call_args[0][2] == "admin@example.com"

    def test_log_stream_stop(self, mock_db_session):
        """Test log_stream_stop helper with reason."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_stream_stop(mock_db_session, user_email="admin@example.com", reason="Manual stop")
            
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "stream_stop"
            assert call_args[0][3] == {"reason": "Manual stop"}

    def test_log_stream_error(self, mock_db_session):
        """Test log_stream_error helper."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_stream_error(mock_db_session, "Connection timeout", user_email="admin@example.com")
            
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "stream_error"
            assert "Connection timeout" in call_args[0][1]
            assert call_args[0][3] == {"error": "Connection timeout"}

    def test_log_track_added(self, mock_db_session):
        """Test log_track_added helper."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_track_added(mock_db_session, "https://example.com/track.mp3", user_email="dj@example.com")
            
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "track_added"
            assert call_args[0][3] == {"url": "https://example.com/track.mp3"}

    def test_log_track_removed(self, mock_db_session):
        """Test log_track_removed helper."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_track_removed(mock_db_session, "https://example.com/track.mp3")
            
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "track_removed"

    def test_log_playlist_updated(self, mock_db_session):
        """Test log_playlist_updated helper."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_playlist_updated(mock_db_session, user_email="curator@example.com")
            
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "playlist_updated"

    def test_log_system_warning(self, mock_db_session):
        """Test log_system_warning helper."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_system_warning(mock_db_session, "High memory usage", details={"memory": "85%"})
            
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "system_warning"
            assert call_args[0][1] == "High memory usage"
            assert call_args[0][2] is None  # user_email
            assert call_args[0][3] == {"memory": "85%"}

    def test_log_system_error(self, mock_db_session):
        """Test log_system_error helper."""
        with patch("services.activity_service.get_activity_service") as mock_factory:
            mock_service = Mock(spec=ActivityService)
            mock_factory.return_value = mock_service
            
            log_system_error(mock_db_session, "Database connection lost", details={"error_code": 500})
            
            mock_service.log_event.assert_called_once()
            call_args = mock_service.log_event.call_args
            assert call_args[0][0] == "system_error"
            assert call_args[0][3] == {"error_code": 500}


class TestActivityServiceEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_get_events_response_mapping(self, activity_service, mock_db_session, sample_events):
        """Test get_events correctly maps ActivityEvent to ActivityEventResponse."""
        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = [sample_events[0]]
        mock_query.count.return_value = 1
        
        result = activity_service.get_events()
        
        assert len(result.events) == 1
        event = result.events[0]
        # Verify all expected fields are present and match
        assert hasattr(event, 'id')
        assert hasattr(event, 'type')
        assert hasattr(event, 'message')
        assert hasattr(event, 'user_email')
        assert hasattr(event, 'details')
        assert hasattr(event, 'created_at')
        assert event.id == sample_events[0].id
        assert event.type == sample_events[0].type
        assert event.message == sample_events[0].message
        assert event.user_email == sample_events[0].user_email
        assert event.details == sample_events[0].details
        assert event.created_at == sample_events[0].created_at

    def test_cleanup_with_zero_count(self, activity_service, mock_db_session):
        """Test cleanup when count is 0 or None."""
        mock_query = mock_db_session.query.return_value
        mock_query.scalar.return_value = None  # Can happen in empty DB
        
        result = activity_service._cleanup_old_events()
        
        assert result is None  # No cleanup needed
        
        assert result is None  # No cleanup needed
