"""
Tests for Scheduler Service

Coverage target: 100% (currently 0%)
"""
import pytest
from datetime import datetime, time, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session

from src.services.scheduler_service import SchedulerService, ScheduledSlot


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def scheduler_service(mock_db):
    """Scheduler service instance for testing"""
    return SchedulerService(mock_db)


class TestSchedulerServiceInit:
    """Tests for SchedulerService initialization"""
    
    def test_init_creates_service(self, mock_db):
        """Test that SchedulerService initializes correctly"""
        service = SchedulerService(mock_db)
        assert service is not None
        assert service.db == mock_db
    
    def test_init_with_none_db_raises_error(self):
        """Test that init with None db raises error"""
        with pytest.raises((TypeError, AttributeError)):
            SchedulerService(None)


class TestScheduledSlotCreation:
    """Tests for creating scheduled slots"""
    
    def test_create_slot_success(self, scheduler_service, mock_db):
        """Test successful slot creation"""
        channel_id = "channel-123"
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        playlist_id = "playlist-456"
        
        # Mock database add and commit
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        slot = scheduler_service.create_slot(
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            playlist_id=playlist_id
        )
        
        assert slot is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_create_slot_with_invalid_times(self, scheduler_service):
        """Test that creating slot with end_time before start_time raises error"""
        channel_id = "channel-123"
        start_time = datetime.now()
        end_time = start_time - timedelta(hours=1)  # End before start!
        
        with pytest.raises(ValueError, match="end_time must be after start_time"):
            scheduler_service.create_slot(
                channel_id=channel_id,
                start_time=start_time,
                end_time=end_time,
                playlist_id="playlist-123"
            )
    
    def test_create_slot_without_playlist_id(self, scheduler_service, mock_db):
        """Test creating slot without playlist_id"""
        channel_id = "channel-123"
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        slot = scheduler_service.create_slot(
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time,
            playlist_id=None
        )
        
        assert slot is not None
    
    def test_create_overlapping_slots_raises_conflict(self, scheduler_service, mock_db):
        """Test that creating overlapping slots raises conflict error"""
        channel_id = "channel-123"
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=1)
        
        # Mock existing overlapping slot
        existing_slot = Mock(
            channel_id=channel_id,
            start_time=start_time,
            end_time=end_time
        )
        mock_db.query().filter().first.return_value = existing_slot
        
        with pytest.raises(ValueError, match="overlapping|conflict"):
            scheduler_service.create_slot(
                channel_id=channel_id,
                start_time=start_time,
                end_time=end_time,
                playlist_id="playlist-123"
            )


class TestScheduledSlotRetrieval:
    """Tests for retrieving scheduled slots"""
    
    def test_get_slot_by_id(self, scheduler_service, mock_db):
        """Test retrieving slot by ID"""
        slot_id = "slot-123"
        expected_slot = Mock(id=slot_id, channel_id="channel-123")
        
        mock_db.query().filter().first.return_value = expected_slot
        
        slot = scheduler_service.get_slot(slot_id)
        
        assert slot == expected_slot
    
    def test_get_nonexistent_slot_returns_none(self, scheduler_service, mock_db):
        """Test that getting non-existent slot returns None"""
        mock_db.query().filter().first.return_value = None
        
        slot = scheduler_service.get_slot("nonexistent-id")
        
        assert slot is None
    
    def test_get_slots_by_channel(self, scheduler_service, mock_db):
        """Test retrieving all slots for a channel"""
        channel_id = "channel-123"
        expected_slots = [
            Mock(id="slot-1", channel_id=channel_id),
            Mock(id="slot-2", channel_id=channel_id),
        ]
        
        mock_db.query().filter().all.return_value = expected_slots
        
        slots = scheduler_service.get_slots_by_channel(channel_id)
        
        assert len(slots) == 2
        assert slots == expected_slots
    
    def test_get_slots_by_date_range(self, scheduler_service, mock_db):
        """Test retrieving slots within date range"""
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        
        expected_slots = [Mock(start_time=start_date + timedelta(days=i)) for i in range(3)]
        mock_db.query().filter().all.return_value = expected_slots
        
        slots = scheduler_service.get_slots_by_date_range(start_date, end_date)
        
        assert len(slots) == 3


class TestScheduledSlotUpdate:
    """Tests for updating scheduled slots"""
    
    def test_update_slot_success(self, scheduler_service, mock_db):
        """Test successful slot update"""
        slot_id = "slot-123"
        existing_slot = Mock(
            id=slot_id,
            channel_id="channel-123",
            start_time=datetime.now(),
            playlist_id="old-playlist"
        )
        
        mock_db.query().filter().first.return_value = existing_slot
        mock_db.commit = Mock()
        
        new_playlist_id = "new-playlist"
        updated_slot = scheduler_service.update_slot(
            slot_id=slot_id,
            playlist_id=new_playlist_id
        )
        
        assert updated_slot.playlist_id == new_playlist_id
        mock_db.commit.assert_called_once()
    
    def test_update_nonexistent_slot_raises_error(self, scheduler_service, mock_db):
        """Test that updating non-existent slot raises error"""
        mock_db.query().filter().first.return_value = None
        
        with pytest.raises(ValueError, match="not found|does not exist"):
            scheduler_service.update_slot(
                slot_id="nonexistent-id",
                playlist_id="new-playlist"
            )


class TestScheduledSlotDeletion:
    """Tests for deleting scheduled slots"""
    
    def test_delete_slot_success(self, scheduler_service, mock_db):
        """Test successful slot deletion"""
        slot_id = "slot-123"
        existing_slot = Mock(id=slot_id)
        
        mock_db.query().filter().first.return_value = existing_slot
        mock_db.delete = Mock()
        mock_db.commit = Mock()
        
        scheduler_service.delete_slot(slot_id)
        
        mock_db.delete.assert_called_once_with(existing_slot)
        mock_db.commit.assert_called_once()
    
    def test_delete_nonexistent_slot_raises_error(self, scheduler_service, mock_db):
        """Test that deleting non-existent slot raises error"""
        mock_db.query().filter().first.return_value = None
        
        with pytest.raises(ValueError, match="not found|does not exist"):
            scheduler_service.delete_slot("nonexistent-id")


class TestSchedulerServiceExecution:
    """Tests for scheduler execution logic"""
    
    @pytest.mark.asyncio
    async def test_execute_scheduled_slot(self, scheduler_service, mock_db):
        """Test executing a scheduled slot starts stream"""
        slot = Mock(
            id="slot-123",
            channel_id="channel-123",
            playlist_id="playlist-456",
            start_time=datetime.now() - timedelta(seconds=10),
            end_time=datetime.now() + timedelta(hours=1)
        )
        
        with patch.object(scheduler_service, 'start_stream') as mock_start:
            await scheduler_service.execute_slot(slot)
            mock_start.assert_called_once_with(slot.channel_id, slot.playlist_id)
    
    @pytest.mark.asyncio
    async def test_check_upcoming_slots(self, scheduler_service, mock_db):
        """Test checking for upcoming slots to execute"""
        now = datetime.now()
        upcoming_slot = Mock(
            id="slot-123",
            start_time=now + timedelta(minutes=5),
            end_time=now + timedelta(hours=1),
            is_active=False
        )
        
        mock_db.query().filter().all.return_value = [upcoming_slot]
        
        with patch.object(scheduler_service, 'execute_slot') as mock_execute:
            await scheduler_service.check_upcoming_slots()
            # Should not execute yet (5 minutes away)
            mock_execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_stop_expired_slots(self, scheduler_service, mock_db):
        """Test stopping slots that have passed end_time"""
        now = datetime.now()
        expired_slot = Mock(
            id="slot-123",
            end_time=now - timedelta(minutes=1),
            is_active=True
        )
        
        mock_db.query().filter().all.return_value = [expired_slot]
        
        with patch.object(scheduler_service, 'stop_stream') as mock_stop:
            await scheduler_service.check_expired_slots()
            mock_stop.assert_called_once()


class TestSchedulerServiceEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_create_slot_db_error_rolls_back(self, scheduler_service, mock_db):
        """Test that database errors trigger rollback"""
        mock_db.add = Mock(side_effect=Exception("DB Error"))
        mock_db.rollback = Mock()
        
        with pytest.raises(Exception):
            scheduler_service.create_slot(
                channel_id="channel-123",
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(hours=1),
                playlist_id="playlist-123"
            )
        
        mock_db.rollback.assert_called_once()
    
    def test_get_slots_empty_result(self, scheduler_service, mock_db):
        """Test retrieving slots when none exist"""
        mock_db.query().filter().all.return_value = []
        
        slots = scheduler_service.get_slots_by_channel("empty-channel")
        
        assert slots == []
        assert len(slots) == 0


# Markers for pytest
pytestmark = [
    pytest.mark.unit,
    pytest.mark.asyncio,
]
