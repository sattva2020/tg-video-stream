"""
Tests for src/services/scheduler_service.py.

Coverage target: 70%+

Test categories:
1. Initialization
2. Start/Stop
3. CRUD operations (create/get/update/delete schedules)
4. Internal scheduling (_schedule_job, _reschedule_job, _unschedule_job)
5. Trigger logic (_trigger_playlist)
6. Restore schedules on startup
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from sqlalchemy.orm import Session

from src.services.scheduler_service import SchedulerService
from src.models import ScheduledPlaylist


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy database session."""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def mock_scheduler():
    """Mock APScheduler BackgroundScheduler."""
    scheduler = MagicMock()
    scheduler.running = False
    return scheduler


@pytest.fixture
def scheduler_service(mock_db_session, mock_scheduler):
    """SchedulerService instance with mocked dependencies."""
    with patch('src.services.scheduler_service.BackgroundScheduler', return_value=mock_scheduler):
        service = SchedulerService(mock_db_session)
        yield service


@pytest.fixture
def sample_schedule():
    """Sample ScheduledPlaylist object."""
    return ScheduledPlaylist(
        id=1,
        playlist_id=100,
        schedule_time="09:30",
        name="Morning Playlist",
        days_of_week=[0, 1, 2, 3, 4],  # Mon-Fri
        timezone="UTC",
        description="Weekday morning music",
        created_by=1,
        is_active=True,
        last_triggered=None,
        trigger_count=0
    )


# ============================================================================
# Test Initialization
# ============================================================================

class TestSchedulerServiceInit:
    """Test SchedulerService initialization."""
    
    def test_init_creates_scheduler(self, mock_db_session):
        """Test __init__() creates BackgroundScheduler."""
        with patch('src.services.scheduler_service.BackgroundScheduler') as MockScheduler:
            mock_sched = MagicMock()
            MockScheduler.return_value = mock_sched
            
            service = SchedulerService(mock_db_session)
            
            assert service.db == mock_db_session
            assert service.scheduler == mock_sched
            assert service._jobs == {}
            MockScheduler.assert_called_once()
    
    def test_init_sets_logger(self, scheduler_service):
        """Test __init__() sets logger."""
        assert scheduler_service.logger is not None
        assert scheduler_service.logger.name == "src.services.scheduler_service"


# ============================================================================
# Test Start/Stop
# ============================================================================

class TestSchedulerServiceStartStop:
    """Test scheduler start/stop lifecycle."""
    
    def test_start_when_not_running(self, scheduler_service, mock_scheduler):
        """Test start() when scheduler is not running."""
        mock_scheduler.running = False
        
        with patch.object(scheduler_service, '_restore_schedules') as mock_restore:
            scheduler_service.start()
            
            mock_scheduler.start.assert_called_once()
            mock_restore.assert_called_once()
    
    def test_start_when_already_running(self, scheduler_service, mock_scheduler):
        """Test start() when scheduler already running (should be idempotent)."""
        mock_scheduler.running = True
        
        with patch.object(scheduler_service, '_restore_schedules') as mock_restore:
            scheduler_service.start()
            
            mock_scheduler.start.assert_not_called()
            mock_restore.assert_not_called()
    
    def test_stop_when_running(self, scheduler_service, mock_scheduler):
        """Test stop() when scheduler is running."""
        mock_scheduler.running = True
        
        scheduler_service.stop()
        
        mock_scheduler.shutdown.assert_called_once()
    
    def test_stop_when_not_running(self, scheduler_service, mock_scheduler):
        """Test stop() when scheduler not running (should be safe)."""
        mock_scheduler.running = False
        
        scheduler_service.stop()
        
        mock_scheduler.shutdown.assert_not_called()


# ============================================================================
# Test Create Schedule
# ============================================================================

class TestSchedulerServiceCreateSchedule:
    """Test schedule creation."""
    
    def test_create_schedule_with_all_fields(self, scheduler_service, mock_db_session):
        """Test create_schedule() with all parameters."""
        with patch.object(scheduler_service, '_schedule_job', return_value="job_1") as mock_schedule_job:
            result = scheduler_service.create_schedule(
                playlist_id=100,
                schedule_time="09:30",
                name="Morning Playlist",
                days_of_week=[0, 1, 2, 3, 4],
                timezone="Europe/Moscow",
                description="Weekday morning",
                created_by=1
            )
            
            assert isinstance(result, ScheduledPlaylist)
            assert result.playlist_id == 100
            assert result.schedule_time == "09:30"
            assert result.name == "Morning Playlist"
            assert result.days_of_week == [0, 1, 2, 3, 4]
            assert result.timezone == "Europe/Moscow"
            assert result.description == "Weekday morning"
            assert result.created_by == 1
            assert result.is_active is True
            
            mock_db_session.add.assert_called_once_with(result)
            mock_db_session.commit.assert_called_once()
            mock_schedule_job.assert_called_once_with(result)
    
    def test_create_schedule_defaults_all_days(self, scheduler_service, mock_db_session):
        """Test create_schedule() defaults to all 7 days when days_of_week=None."""
        with patch.object(scheduler_service, '_schedule_job'):
            result = scheduler_service.create_schedule(
                playlist_id=200,
                schedule_time="12:00",
                name="Daily Playlist",
                days_of_week=None  # Should default to [0,1,2,3,4,5,6]
            )
            
            assert result.days_of_week == [0, 1, 2, 3, 4, 5, 6]
    
    def test_create_schedule_minimal_fields(self, scheduler_service, mock_db_session):
        """Test create_schedule() with only required fields."""
        with patch.object(scheduler_service, '_schedule_job'):
            result = scheduler_service.create_schedule(
                playlist_id=300,
                schedule_time="18:00",
                name="Evening Playlist"
            )
            
            assert result.playlist_id == 300
            assert result.schedule_time == "18:00"
            assert result.name == "Evening Playlist"
            assert result.days_of_week == [0, 1, 2, 3, 4, 5, 6]
            assert result.timezone == "UTC"
            assert result.description is None
            assert result.created_by is None


# ============================================================================
# Test Get Schedules
# ============================================================================

class TestSchedulerServiceGetSchedules:
    """Test schedule retrieval."""
    
    def test_get_schedule_existing(self, scheduler_service, mock_db_session, sample_schedule):
        """Test get_schedule() returns existing schedule."""
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = sample_schedule
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        result = scheduler_service.get_schedule(schedule_id=1)
        
        assert result == sample_schedule
        mock_db_session.query.assert_called_once_with(ScheduledPlaylist)
    
    def test_get_schedule_not_found(self, scheduler_service, mock_db_session):
        """Test get_schedule() returns None when not found."""
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        result = scheduler_service.get_schedule(schedule_id=999)
        
        assert result is None
    
    def test_get_all_schedules_active_only(self, scheduler_service, mock_db_session, sample_schedule):
        """Test get_all_schedules() with active_only=True (default)."""
        schedule2 = ScheduledPlaylist(
            id=2,
            playlist_id=200,
            schedule_time="14:00",
            name="Afternoon",
            days_of_week=[0, 6],
            timezone="UTC",
            is_active=True
        )
        
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_order.all.return_value = [sample_schedule, schedule2]
        mock_filter.order_by.return_value = mock_order
        mock_query.filter.return_value = mock_filter
        mock_db_session.query.return_value = mock_query
        
        result = scheduler_service.get_all_schedules(active_only=True)
        
        assert len(result) == 2
        assert result[0] == sample_schedule
        assert result[1] == schedule2
        mock_query.filter.assert_called_once()
    
    def test_get_all_schedules_include_inactive(self, scheduler_service, mock_db_session):
        """Test get_all_schedules() with active_only=False."""
        mock_query = MagicMock()
        mock_order = MagicMock()
        mock_order.all.return_value = []
        mock_query.order_by.return_value = mock_order
        mock_db_session.query.return_value = mock_query
        
        result = scheduler_service.get_all_schedules(active_only=False)
        
        # Should not call filter() when active_only=False
        mock_query.filter.assert_not_called()
        mock_query.order_by.assert_called_once()


# ============================================================================
# Test Update Schedule
# ============================================================================

class TestSchedulerServiceUpdateSchedule:
    """Test schedule update."""
    
    def test_update_schedule_success(self, scheduler_service, mock_db_session, sample_schedule):
        """Test update_schedule() updates fields."""
        with patch.object(scheduler_service, 'get_schedule', return_value=sample_schedule):
            with patch.object(scheduler_service, '_reschedule_job') as mock_reschedule:
                result = scheduler_service.update_schedule(
                    schedule_id=1,
                    name="Updated Name",
                    description="New description"
                )
                
                assert result == sample_schedule
                assert sample_schedule.name == "Updated Name"
                assert sample_schedule.description == "New description"
                mock_db_session.commit.assert_called_once()
                mock_reschedule.assert_not_called()  # No timing fields updated
    
    def test_update_schedule_reschedules_on_time_change(self, scheduler_service, sample_schedule):
        """Test update_schedule() calls _reschedule_job when schedule_time changes."""
        with patch.object(scheduler_service, 'get_schedule', return_value=sample_schedule):
            with patch.object(scheduler_service, '_reschedule_job') as mock_reschedule:
                result = scheduler_service.update_schedule(
                    schedule_id=1,
                    schedule_time="15:00"
                )
                
                assert sample_schedule.schedule_time == "15:00"
                mock_reschedule.assert_called_once_with(sample_schedule)
    
    def test_update_schedule_reschedules_on_days_change(self, scheduler_service, sample_schedule):
        """Test update_schedule() calls _reschedule_job when days_of_week changes."""
        with patch.object(scheduler_service, 'get_schedule', return_value=sample_schedule):
            with patch.object(scheduler_service, '_reschedule_job') as mock_reschedule:
                result = scheduler_service.update_schedule(
                    schedule_id=1,
                    days_of_week=[5, 6]  # Weekends only
                )
                
                assert sample_schedule.days_of_week == [5, 6]
                mock_reschedule.assert_called_once_with(sample_schedule)
    
    def test_update_schedule_not_found(self, scheduler_service):
        """Test update_schedule() returns None when schedule not found."""
        with patch.object(scheduler_service, 'get_schedule', return_value=None):
            result = scheduler_service.update_schedule(
                schedule_id=999,
                name="Nonexistent"
            )
            
            assert result is None
    
    def test_update_schedule_ignores_invalid_fields(self, scheduler_service, sample_schedule):
        """Test update_schedule() ignores fields that don't exist on model."""
        with patch.object(scheduler_service, 'get_schedule', return_value=sample_schedule):
            original_name = sample_schedule.name
            
            result = scheduler_service.update_schedule(
                schedule_id=1,
                nonexistent_field="value"
            )
            
            assert result == sample_schedule
            assert sample_schedule.name == original_name  # Unchanged
            assert not hasattr(sample_schedule, 'nonexistent_field')


# ============================================================================
# Test Delete Schedule
# ============================================================================

class TestSchedulerServiceDeleteSchedule:
    """Test schedule deletion (soft delete)."""
    
    def test_delete_schedule_success(self, scheduler_service, mock_db_session, sample_schedule):
        """Test delete_schedule() marks schedule inactive."""
        with patch.object(scheduler_service, 'get_schedule', return_value=sample_schedule):
            with patch.object(scheduler_service, '_unschedule_job') as mock_unschedule:
                result = scheduler_service.delete_schedule(schedule_id=1)
                
                assert result is True
                assert sample_schedule.is_active is False
                mock_db_session.commit.assert_called_once()
                mock_unschedule.assert_called_once_with(sample_schedule)
    
    def test_delete_schedule_not_found(self, scheduler_service):
        """Test delete_schedule() returns False when schedule not found."""
        with patch.object(scheduler_service, 'get_schedule', return_value=None):
            result = scheduler_service.delete_schedule(schedule_id=999)
            
            assert result is False


# ============================================================================
# Test Internal Job Management
# ============================================================================

class TestSchedulerServiceJobManagement:
    """Test internal job scheduling methods."""
    
    def test_schedule_job_creates_cron_trigger(self, scheduler_service, mock_scheduler, sample_schedule):
        """Test _schedule_job() creates APScheduler job with CronTrigger."""
        mock_job = MagicMock()
        mock_job.id = "schedule_1"
        mock_scheduler.add_job.return_value = mock_job
        
        with patch('src.services.scheduler_service.CronTrigger') as MockCronTrigger:
            mock_trigger = MagicMock()
            MockCronTrigger.return_value = mock_trigger
            
            job_id = scheduler_service._schedule_job(sample_schedule)
            
            # Verify CronTrigger created with correct parameters
            MockCronTrigger.assert_called_once_with(
                hour=9,
                minute=30,
                day_of_week="0,1,2,3,4",  # Mon-Fri
                timezone="UTC"
            )
            
            # Verify add_job called
            mock_scheduler.add_job.assert_called_once_with(
                scheduler_service._trigger_playlist,
                trigger=mock_trigger,
                args=[1],
                id="schedule_1"
            )
            
            assert job_id == "schedule_1"
            assert scheduler_service._jobs[1] == "schedule_1"
    
    def test_schedule_job_parses_time_correctly(self, scheduler_service, mock_scheduler):
        """Test _schedule_job() parses HH:MM format correctly."""
        schedule = ScheduledPlaylist(
            id=2,
            playlist_id=100,
            schedule_time="23:45",
            name="Late Night",
            days_of_week=[0],
            timezone="UTC",
            is_active=True
        )
        
        mock_job = MagicMock()
        mock_job.id = "schedule_2"
        mock_scheduler.add_job.return_value = mock_job
        
        with patch('src.services.scheduler_service.CronTrigger') as MockCronTrigger:
            scheduler_service._schedule_job(schedule)
            
            MockCronTrigger.assert_called_once_with(
                hour=23,
                minute=45,
                day_of_week="0",
                timezone="UTC"
            )
    
    def test_reschedule_job_removes_and_recreates(self, scheduler_service, sample_schedule):
        """Test _reschedule_job() calls _unschedule_job then _schedule_job."""
        with patch.object(scheduler_service, '_unschedule_job') as mock_unschedule:
            with patch.object(scheduler_service, '_schedule_job') as mock_schedule:
                scheduler_service._reschedule_job(sample_schedule)
                
                mock_unschedule.assert_called_once_with(sample_schedule)
                mock_schedule.assert_called_once_with(sample_schedule)
    
    def test_unschedule_job_removes_from_scheduler(self, scheduler_service, mock_scheduler, sample_schedule):
        """Test _unschedule_job() removes job from scheduler."""
        scheduler_service._jobs[1] = "job_1"
        
        scheduler_service._unschedule_job(sample_schedule)
        
        mock_scheduler.remove_job.assert_called_once_with("job_1")
        assert 1 not in scheduler_service._jobs
    
    def test_unschedule_job_when_not_scheduled(self, scheduler_service, mock_scheduler, sample_schedule):
        """Test _unschedule_job() is safe when job not in _jobs dict."""
        # Don't add job to _jobs
        
        scheduler_service._unschedule_job(sample_schedule)
        
        mock_scheduler.remove_job.assert_not_called()


# ============================================================================
# Test Trigger Playlist
# ============================================================================

class TestSchedulerServiceTriggerPlaylist:
    """Test playlist trigger logic."""
    
    def test_trigger_playlist_updates_statistics(self, scheduler_service, mock_db_session, sample_schedule):
        """Test _trigger_playlist() updates last_triggered and trigger_count."""
        original_count = sample_schedule.trigger_count
        
        with patch.object(scheduler_service, 'get_schedule', return_value=sample_schedule):
            with patch('src.services.scheduler_service.datetime') as mock_datetime:
                mock_now = datetime(2024, 1, 15, 9, 30, 0)
                mock_datetime.utcnow.return_value = mock_now
                
                scheduler_service._trigger_playlist(schedule_id=1)
                
                assert sample_schedule.last_triggered == mock_now
                assert sample_schedule.trigger_count == original_count + 1
                mock_db_session.commit.assert_called_once()
    
    def test_trigger_playlist_handles_nonexistent_schedule(self, scheduler_service, mock_db_session):
        """Test _trigger_playlist() exits gracefully when schedule not found."""
        with patch.object(scheduler_service, 'get_schedule', return_value=None):
            scheduler_service._trigger_playlist(schedule_id=999)
            
            # Should not commit if schedule doesn't exist
            mock_db_session.commit.assert_not_called()
    
    def test_trigger_playlist_logs_trigger(self, scheduler_service, sample_schedule):
        """Test _trigger_playlist() logs the trigger event."""
        with patch.object(scheduler_service, 'get_schedule', return_value=sample_schedule):
            with patch.object(scheduler_service.logger, 'info') as mock_log:
                scheduler_service._trigger_playlist(schedule_id=1)
                
                mock_log.assert_called()
                log_message = mock_log.call_args[0][0]
                assert "Morning Playlist" in log_message
                assert "100" in log_message  # playlist_id


# ============================================================================
# Test Restore Schedules
# ============================================================================

class TestSchedulerServiceRestoreSchedules:
    """Test schedule restoration on startup."""
    
    def test_restore_schedules_on_startup(self, scheduler_service, sample_schedule):
        """Test _restore_schedules() restores all active schedules."""
        schedule2 = ScheduledPlaylist(
            id=2,
            playlist_id=200,
            schedule_time="18:00",
            name="Evening",
            days_of_week=[0, 1, 2, 3, 4, 5, 6],
            timezone="UTC",
            is_active=True
        )
        
        with patch.object(scheduler_service, 'get_all_schedules', return_value=[sample_schedule, schedule2]):
            with patch.object(scheduler_service, '_schedule_job') as mock_schedule_job:
                scheduler_service._restore_schedules()
                
                assert mock_schedule_job.call_count == 2
                mock_schedule_job.assert_any_call(sample_schedule)
                mock_schedule_job.assert_any_call(schedule2)
    
    def test_restore_schedules_with_empty_database(self, scheduler_service):
        """Test _restore_schedules() handles empty database gracefully."""
        with patch.object(scheduler_service, 'get_all_schedules', return_value=[]):
            with patch.object(scheduler_service, '_schedule_job') as mock_schedule_job:
                scheduler_service._restore_schedules()
                
                mock_schedule_job.assert_not_called()
    
    def test_restore_schedules_logs_count(self, scheduler_service, sample_schedule):
        """Test _restore_schedules() logs the number of restored schedules."""
        with patch.object(scheduler_service, 'get_all_schedules', return_value=[sample_schedule]):
            with patch.object(scheduler_service, '_schedule_job'):
                with patch.object(scheduler_service.logger, 'info') as mock_log:
                    scheduler_service._restore_schedules()
                    
                    mock_log.assert_called()
                    log_message = mock_log.call_args[0][0]
                    assert "1" in log_message
                    assert "Restored" in log_message


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestSchedulerServiceEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_schedule_with_single_day(self, scheduler_service, mock_scheduler):
        """Test scheduling for a single day of week."""
        schedule = ScheduledPlaylist(
            id=3,
            playlist_id=100,
            schedule_time="12:00",
            name="Sunday Only",
            days_of_week=[6],  # Only Sunday
            timezone="UTC",
            is_active=True
        )
        
        mock_job = MagicMock()
        mock_job.id = "schedule_3"
        mock_scheduler.add_job.return_value = mock_job
        
        with patch('src.services.scheduler_service.CronTrigger') as MockCronTrigger:
            scheduler_service._schedule_job(schedule)
            
            MockCronTrigger.assert_called_once_with(
                hour=12,
                minute=0,
                day_of_week="6",
                timezone="UTC"
            )
    
    def test_schedule_with_all_days(self, scheduler_service, mock_scheduler):
        """Test scheduling for all 7 days."""
        schedule = ScheduledPlaylist(
            id=4,
            playlist_id=100,
            schedule_time="08:00",
            name="Daily",
            days_of_week=[0, 1, 2, 3, 4, 5, 6],
            timezone="UTC",
            is_active=True
        )
        
        mock_job = MagicMock()
        mock_job.id = "schedule_4"
        mock_scheduler.add_job.return_value = mock_job
        
        with patch('src.services.scheduler_service.CronTrigger') as MockCronTrigger:
            scheduler_service._schedule_job(schedule)
            
            called_args = MockCronTrigger.call_args[1]
            assert called_args['day_of_week'] == "0,1,2,3,4,5,6"
    
    def test_schedule_with_non_utc_timezone(self, scheduler_service, mock_scheduler):
        """Test scheduling with non-UTC timezone."""
        schedule = ScheduledPlaylist(
            id=5,
            playlist_id=100,
            schedule_time="19:00",
            name="Europe Evening",
            days_of_week=[0, 1, 2],
            timezone="Europe/Berlin",
            is_active=True
        )
        
        mock_job = MagicMock()
        mock_job.id = "schedule_5"
        mock_scheduler.add_job.return_value = mock_job
        
        with patch('src.services.scheduler_service.CronTrigger') as MockCronTrigger:
            scheduler_service._schedule_job(schedule)
            
            called_args = MockCronTrigger.call_args[1]
            assert called_args['timezone'] == "Europe/Berlin"
    
    def test_update_multiple_fields_simultaneously(self, scheduler_service, sample_schedule):
        """Test updating multiple fields including timing in one call."""
        with patch.object(scheduler_service, 'get_schedule', return_value=sample_schedule):
            with patch.object(scheduler_service, '_reschedule_job') as mock_reschedule:
                result = scheduler_service.update_schedule(
                    schedule_id=1,
                    name="Updated Name",
                    schedule_time="16:30",
                    days_of_week=[5, 6],
                    description="New description"
                )
                
                assert sample_schedule.name == "Updated Name"
                assert sample_schedule.schedule_time == "16:30"
                assert sample_schedule.days_of_week == [5, 6]
                assert sample_schedule.description == "New description"
                mock_reschedule.assert_called_once_with(sample_schedule)
    
    def test_trigger_playlist_increments_from_zero(self, scheduler_service, mock_db_session):
        """Test _trigger_playlist() increments trigger_count from 0."""
        schedule = ScheduledPlaylist(
            id=6,
            playlist_id=100,
            schedule_time="10:00",
            name="First Trigger",
            days_of_week=[0],
            timezone="UTC",
            is_active=True,
            trigger_count=0  # Starting from 0
        )
        
        with patch.object(scheduler_service, 'get_schedule', return_value=schedule):
            scheduler_service._trigger_playlist(schedule_id=6)
            
            assert schedule.trigger_count == 1
