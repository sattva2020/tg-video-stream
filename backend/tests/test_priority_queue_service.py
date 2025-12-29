"""
Comprehensive tests for PriorityQueueService.

Covers:
- Service initialization and Redis connection
- Priority calculation (VIP, Admin, Normal roles)
- Add items with priority
- Get all items with pagination
- Get next item (peek)
- Pop next item (dequeue)
- Remove specific items
- Clear queue
- Queue size limits
- Edge cases and error handling
"""

import pytest
import time
from unittest.mock import Mock
from fakeredis import aioredis

from src.services.priority_queue_service import PriorityQueueService, PriorityLevel
from src.models.queue import QueueItem, QueueItemCreate, QueueInfo
from src.models.user import User, UserRole


# ========== FIXTURES ==========

@pytest.fixture
def fake_redis():
    """FakeRedis client for testing."""
    return aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def priority_queue_service(fake_redis):
    """Create PriorityQueueService with FakeRedis."""
    service = PriorityQueueService(max_queue_size=10)
    service._redis = fake_redis
    return service


@pytest.fixture
def vip_user():
    """VIP user fixture."""
    user = Mock(spec=User)
    user.id = 1
    user.role = "vip"
    return user


@pytest.fixture
def admin_user():
    """Admin user fixture."""
    user = Mock(spec=User)
    user.id = 2
    user.role = "admin"
    return user


@pytest.fixture
def normal_user():
    """Normal user fixture."""
    user = Mock(spec=User)
    user.id = 3
    user.role = "user"
    return user


@pytest.fixture
def sample_queue_item_create():
    """Sample QueueItemCreate."""
    return QueueItemCreate(
        title="Test Song",
        url="http://example.com/song.mp3",
        duration=180,
        source="youtube",
        metadata={"artist": "Test Artist"}
    )


# ========== INITIALIZATION TESTS ==========

class TestPriorityQueueServiceInit:
    """Test PriorityQueueService initialization."""
    
    def test_init_creates_service(self):
        """Test that service initializes correctly."""
        service = PriorityQueueService()
        assert service is not None
        assert service.max_queue_size == 100  # Default
    
    def test_init_with_custom_max_size(self):
        """Test initialization with custom max size."""
        service = PriorityQueueService(max_queue_size=50)
        assert service.max_queue_size == 50
    
    @pytest.mark.asyncio
    async def test_get_redis_lazy_initialization(self, priority_queue_service):
        """Test that Redis client is lazily initialized."""
        redis_client = await priority_queue_service._get_redis()
        assert redis_client is not None
    
    @pytest.mark.asyncio
    async def test_close_redis_connection(self, priority_queue_service):
        """Test closing Redis connection."""
        await priority_queue_service._get_redis()
        await priority_queue_service.close()
        assert priority_queue_service._redis is None


# ========== PRIORITY CALCULATION TESTS ==========

class TestPriorityCalculation:
    """Test priority score calculation."""
    
    def test_calculate_priority_vip(self):
        """Test VIP priority calculation."""
        score = PriorityQueueService._calculate_priority_score("vip")
        assert score == PriorityLevel.VIP  # 0
    
    def test_calculate_priority_superadmin(self):
        """Test superadmin priority calculation."""
        score = PriorityQueueService._calculate_priority_score("superadmin")
        assert score == PriorityLevel.VIP  # Same as VIP
    
    def test_calculate_priority_admin(self):
        """Test admin priority calculation."""
        score = PriorityQueueService._calculate_priority_score("admin")
        assert score == PriorityLevel.ADMIN  # 1000
    
    def test_calculate_priority_normal(self):
        """Test normal user priority calculation."""
        score = PriorityQueueService._calculate_priority_score("user")
        assert score == PriorityLevel.NORMAL  # 2000
    
    def test_generate_score_includes_timestamp(self):
        """Test that generated score includes timestamp component."""
        score1 = PriorityQueueService._generate_score("user")
        time.sleep(0.01)
        score2 = PriorityQueueService._generate_score("user")
        
        # Score2 should be slightly higher (later timestamp)
        assert score2 > score1
    
    def test_generate_score_vip_always_less_than_normal(self):
        """Test that VIP score is always less than normal user score."""
        vip_score = PriorityQueueService._generate_score("vip")
        normal_score = PriorityQueueService._generate_score("user")
        
        # VIP should have lower score (higher priority)
        assert vip_score < normal_score
    
    def test_queue_key_generation(self):
        """Test Redis key generation."""
        key = PriorityQueueService._get_queue_key(123)
        assert key == "priority_queue:123"


# ========== ADD ITEMS TESTS ==========

class TestAddItems:
    """Test adding items to priority queue."""
    
    @pytest.mark.asyncio
    async def test_add_item_vip_user(self, priority_queue_service, vip_user, sample_queue_item_create):
        """Test adding item with VIP user."""
        item = await priority_queue_service.add(
            channel_id=1,
            item_create=sample_queue_item_create,
            user=vip_user
        )
        
        assert item is not None
        assert item.title == "Test Song"
        assert item.metadata["priority_role"] == "vip"
        assert item.metadata["is_vip"] is True
    
    @pytest.mark.asyncio
    async def test_add_item_admin_user(self, priority_queue_service, admin_user, sample_queue_item_create):
        """Test adding item with admin user."""
        item = await priority_queue_service.add(
            channel_id=1,
            item_create=sample_queue_item_create,
            user=admin_user
        )
        
        assert item.metadata["priority_role"] == "admin"
        assert item.metadata["is_admin"] is True
    
    @pytest.mark.asyncio
    async def test_add_item_normal_user(self, priority_queue_service, normal_user, sample_queue_item_create):
        """Test adding item with normal user."""
        item = await priority_queue_service.add(
            channel_id=1,
            item_create=sample_queue_item_create,
            user=normal_user
        )
        
        assert item.metadata["priority_role"] == "user"
        assert item.metadata["is_vip"] is False
    
    @pytest.mark.asyncio
    async def test_add_multiple_items(self, priority_queue_service, vip_user, normal_user):
        """Test adding multiple items with different priorities."""
        item1 = QueueItemCreate(title="VIP Song", url="http://vip.mp3", duration=180, source="youtube")
        item2 = QueueItemCreate(title="Normal Song", url="http://normal.mp3", duration=200, source="youtube")
        
        await priority_queue_service.add(1, item1, vip_user)
        await priority_queue_service.add(1, item2, normal_user)
        
        # Get all items
        queue_info = await priority_queue_service.get_all(channel_id=1)
        assert queue_info.total_items == 2
    
    @pytest.mark.asyncio
    async def test_add_item_exceeds_max_size(self, priority_queue_service, normal_user, sample_queue_item_create):
        """Test that adding items beyond max_queue_size raises exception."""
        # Fill queue to max (10 items)
        for i in range(10):
            item = QueueItemCreate(title=f"Song {i}", url=f"http://song{i}.mp3", duration=180, source="youtube")
            await priority_queue_service.add(1, item, normal_user)
        
        # Try to add 11th item
        with pytest.raises(Exception, match="достигла максимального размера"):
            await priority_queue_service.add(1, sample_queue_item_create, normal_user)


# ========== GET ITEMS TESTS ==========

class TestGetItems:
    """Test retrieving items from queue."""
    
    @pytest.mark.asyncio
    async def test_get_all_empty_queue(self, priority_queue_service):
        """Test getting all items from empty queue."""
        queue_info = await priority_queue_service.get_all(channel_id=1)
        
        assert queue_info.total_items == 0
        assert len(queue_info.items) == 0
        assert queue_info.total_duration == 0
    
    @pytest.mark.asyncio
    async def test_get_all_with_items(self, priority_queue_service, vip_user, normal_user):
        """Test getting all items respects priority order."""
        # Add normal user item first
        normal_item = QueueItemCreate(title="Normal", url="http://n.mp3", duration=180, source="youtube")
        await priority_queue_service.add(1, normal_item, normal_user)
        
        # Add VIP item second
        vip_item = QueueItemCreate(title="VIP", url="http://v.mp3", duration=200, source="youtube")
        await priority_queue_service.add(1, vip_item, vip_user)
        
        queue_info = await priority_queue_service.get_all(channel_id=1)
        
        # VIP should be first (lower score = higher priority)
        assert queue_info.items[0].title == "VIP"
        assert queue_info.items[1].title == "Normal"
        assert queue_info.total_duration == 380
    
    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, priority_queue_service, normal_user):
        """Test pagination in get_all."""
        # Add 5 items
        for i in range(5):
            item = QueueItemCreate(title=f"Song {i}", url=f"http://s{i}.mp3", duration=180, source="youtube")
            await priority_queue_service.add(1, item, normal_user)
        
        # Get first 2
        page1 = await priority_queue_service.get_all(channel_id=1, limit=2, offset=0)
        assert len(page1.items) == 2
        assert page1.total_items == 5
        
        # Get next 2
        page2 = await priority_queue_service.get_all(channel_id=1, limit=2, offset=2)
        assert len(page2.items) == 2
        
        # Different items
        assert page1.items[0].title != page2.items[0].title


# ========== GET/POP NEXT TESTS ==========

class TestGetAndPopNext:
    """Test get_next and pop_next operations."""
    
    @pytest.mark.asyncio
    async def test_get_next_empty_queue(self, priority_queue_service):
        """Test get_next on empty queue returns None."""
        next_item = await priority_queue_service.get_next(channel_id=1)
        assert next_item is None
    
    @pytest.mark.asyncio
    async def test_get_next_returns_highest_priority(self, priority_queue_service, vip_user, normal_user):
        """Test that get_next returns highest priority item."""
        # Add normal first
        normal_item = QueueItemCreate(title="Normal", url="http://n.mp3", duration=180, source="youtube")
        await priority_queue_service.add(1, normal_item, normal_user)
        
        # Add VIP second
        vip_item = QueueItemCreate(title="VIP", url="http://v.mp3", duration=200, source="youtube")
        await priority_queue_service.add(1, vip_item, vip_user)
        
        next_item = await priority_queue_service.get_next(channel_id=1)
        
        # Should be VIP item
        assert next_item.title == "VIP"
    
    @pytest.mark.asyncio
    async def test_get_next_does_not_remove_item(self, priority_queue_service, vip_user):
        """Test that get_next doesn't remove item from queue."""
        vip_item = QueueItemCreate(title="VIP", url="http://v.mp3", duration=200, source="youtube")
        await priority_queue_service.add(1, vip_item, vip_user)
        
        # Get next twice
        first = await priority_queue_service.get_next(channel_id=1)
        second = await priority_queue_service.get_next(channel_id=1)
        
        # Should be the same item
        assert first.title == second.title
        
        # Queue should still have 1 item
        queue_info = await priority_queue_service.get_all(channel_id=1)
        assert queue_info.total_items == 1
    
    @pytest.mark.asyncio
    async def test_pop_next_removes_item(self, priority_queue_service, vip_user):
        """Test that pop_next removes item from queue."""
        vip_item = QueueItemCreate(title="VIP", url="http://v.mp3", duration=200, source="youtube")
        await priority_queue_service.add(1, vip_item, vip_user)
        
        popped = await priority_queue_service.pop_next(channel_id=1)
        assert popped.title == "VIP"
        
        # Queue should be empty
        queue_info = await priority_queue_service.get_all(channel_id=1)
        assert queue_info.total_items == 0
    
    @pytest.mark.asyncio
    async def test_pop_next_maintains_priority_order(self, priority_queue_service, vip_user, admin_user, normal_user):
        """Test that pop_next respects priority order."""
        # Add in random order
        normal = QueueItemCreate(title="Normal", url="http://n.mp3", duration=180, source="youtube")
        vip = QueueItemCreate(title="VIP", url="http://v.mp3", duration=200, source="youtube")
        admin = QueueItemCreate(title="Admin", url="http://a.mp3", duration=190, source="youtube")
        
        await priority_queue_service.add(1, normal, normal_user)
        await priority_queue_service.add(1, admin, admin_user)
        await priority_queue_service.add(1, vip, vip_user)
        
        # Pop should be in order: VIP, Admin, Normal
        first = await priority_queue_service.pop_next(channel_id=1)
        assert first.title == "VIP"
        
        second = await priority_queue_service.pop_next(channel_id=1)
        assert second.title == "Admin"
        
        third = await priority_queue_service.pop_next(channel_id=1)
        assert third.title == "Normal"


# ========== REMOVE ITEMS TESTS ==========

class TestRemoveItems:
    """Test removing specific items from queue."""
    
    @pytest.mark.asyncio
    async def test_remove_by_id(self, priority_queue_service, normal_user):
        """Test removing item by ID."""
        item_create = QueueItemCreate(title="Test", url="http://test.mp3", duration=180, source="youtube")
        added_item = await priority_queue_service.add(1, item_create, normal_user)
        
        # Remove by ID
        removed = await priority_queue_service.remove(channel_id=1, item_id=added_item.id)
        assert removed is True
        
        # Queue should be empty
        queue_info = await priority_queue_service.get_all(channel_id=1)
        assert queue_info.total_items == 0
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_item(self, priority_queue_service):
        """Test removing non-existent item returns False."""
        removed = await priority_queue_service.remove(channel_id=1, item_id="fake-id-123")
        assert removed is False


# ========== CLEAR QUEUE TESTS ==========

class TestClearQueue:
    """Test clearing entire queue."""
    
    @pytest.mark.asyncio
    async def test_clear_empty_queue(self, priority_queue_service):
        """Test clearing empty queue."""
        result = await priority_queue_service.clear(channel_id=1)
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_clear_queue_with_items(self, priority_queue_service, normal_user):
        """Test clearing queue with multiple items."""
        # Add 3 items
        for i in range(3):
            item = QueueItemCreate(title=f"Song {i}", url=f"http://s{i}.mp3", duration=180, source="youtube")
            await priority_queue_service.add(1, item, normal_user)
        
        # Clear
        cleared = await priority_queue_service.clear(channel_id=1)
        assert cleared == 3
        
        # Queue should be empty
        queue_info = await priority_queue_service.get_all(channel_id=1)
        assert queue_info.total_items == 0


# ========== EDGE CASES ==========

class TestPriorityQueueEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_fifo_within_same_priority(self, priority_queue_service, normal_user):
        """Test FIFO order for items with same priority."""
        item1 = QueueItemCreate(title="First", url="http://1.mp3", duration=180, source="youtube")
        item2 = QueueItemCreate(title="Second", url="http://2.mp3", duration=180, source="youtube")
        item3 = QueueItemCreate(title="Third", url="http://3.mp3", duration=180, source="youtube")
        
        await priority_queue_service.add(1, item1, normal_user)
        time.sleep(0.01)  # Ensure different timestamps
        await priority_queue_service.add(1, item2, normal_user)
        time.sleep(0.01)
        await priority_queue_service.add(1, item3, normal_user)
        
        # Pop should be in FIFO order
        first = await priority_queue_service.pop_next(channel_id=1)
        assert first.title == "First"
        
        second = await priority_queue_service.pop_next(channel_id=1)
        assert second.title == "Second"
        
        third = await priority_queue_service.pop_next(channel_id=1)
        assert third.title == "Third"
    
    @pytest.mark.asyncio
    async def test_multiple_channels_isolated(self, priority_queue_service, normal_user):
        """Test that different channels have isolated queues."""
        item1 = QueueItemCreate(title="Channel 1", url="http://1.mp3", duration=180, source="youtube")
        item2 = QueueItemCreate(title="Channel 2", url="http://2.mp3", duration=180, source="youtube")
        
        await priority_queue_service.add(1, item1, normal_user)
        await priority_queue_service.add(2, item2, normal_user)
        
        # Channel 1 should have 1 item
        queue1 = await priority_queue_service.get_all(channel_id=1)
        assert queue1.total_items == 1
        assert queue1.items[0].title == "Channel 1"
        
        # Channel 2 should have 1 item
        queue2 = await priority_queue_service.get_all(channel_id=2)
        assert queue2.total_items == 1
        assert queue2.items[0].title == "Channel 2"
    
    @pytest.mark.asyncio
    async def test_case_insensitive_role_matching(self, priority_queue_service):
        """Test that role matching is case-insensitive."""
        user_upper = Mock(spec=User)
        user_upper.id = 1
        user_upper.role = "VIP"  # Uppercase
        
        item = QueueItemCreate(title="Test", url="http://test.mp3", duration=180, source="youtube")
        added = await priority_queue_service.add(1, item, user_upper)
        
        # Should still be recognized as VIP
        assert added.metadata["is_vip"] is True


# ========== ADDITIONAL COVERAGE TESTS ==========

class TestAdditionalCoverage:
    """Tests for 99%+ coverage."""
    
    @pytest.mark.asyncio
    async def test_get_all_with_json_decode_error(self, priority_queue_service):
        """Test get_all handles JSON decode errors gracefully."""
        # Add invalid JSON directly to Redis
        await priority_queue_service._redis.zadd("priority_queue:1", {"invalid-json": 1000.0})
        
        # Should not crash, just skip invalid items
        queue_info = await priority_queue_service.get_all(channel_id=1)
        assert queue_info.total_items == 1  # Redis has 1 item
        assert len(queue_info.items) == 0  # But 0 valid items parsed
    
    @pytest.mark.asyncio
    async def test_get_next_with_json_decode_error(self, priority_queue_service):
        """Test get_next handles JSON decode errors."""
        await priority_queue_service._redis.zadd("priority_queue:1", {"bad-json": 500.0})
        
        result = await priority_queue_service.get_next(channel_id=1)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_pop_next_with_json_decode_error(self, priority_queue_service):
        """Test pop_next handles JSON decode errors."""
        await priority_queue_service._redis.zadd("priority_queue:1", {"corrupt-data": 700.0})
        
        result = await priority_queue_service.pop_next(channel_id=1)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_remove_with_json_decode_error(self, priority_queue_service, normal_user):
        """Test remove handles JSON decode errors in queue."""
        # Add valid item
        item = QueueItemCreate(title="Valid", url="http://v.mp3", duration=180, source="youtube")
        added = await priority_queue_service.add(1, item, normal_user)
        
        # Add invalid JSON
        await priority_queue_service._redis.zadd("priority_queue:1", {"garbage": 800.0})
        
        # Should still find and remove valid item
        removed = await priority_queue_service.remove(channel_id=1, item_id=added.id)
        assert removed is True
    
    @pytest.mark.asyncio
    async def test_get_size(self, priority_queue_service, normal_user):
        """Test get_size returns correct queue size."""
        assert await priority_queue_service.get_size(channel_id=1) == 0
        
        item = QueueItemCreate(title="Test", url="http://t.mp3", duration=180, source="youtube")
        await priority_queue_service.add(1, item, normal_user)
        
        assert await priority_queue_service.get_size(channel_id=1) == 1
    
    @pytest.mark.asyncio
    async def test_is_empty(self, priority_queue_service, normal_user):
        """Test is_empty returns correct status."""
        assert await priority_queue_service.is_empty(channel_id=1) is True
        
        item = QueueItemCreate(title="Test", url="http://t.mp3", duration=180, source="youtube")
        await priority_queue_service.add(1, item, normal_user)
        
        assert await priority_queue_service.is_empty(channel_id=1) is False
    
    @pytest.mark.asyncio
    async def test_get_vip_count(self, priority_queue_service, vip_user, normal_user):
        """Test get_vip_count returns correct VIP items count."""
        # Add 2 VIP items
        item1 = QueueItemCreate(title="VIP1", url="http://v1.mp3", duration=180, source="youtube")
        item2 = QueueItemCreate(title="VIP2", url="http://v2.mp3", duration=180, source="youtube")
        await priority_queue_service.add(1, item1, vip_user)
        await priority_queue_service.add(1, item2, vip_user)
        
        # Add 1 normal item
        item3 = QueueItemCreate(title="Normal", url="http://n.mp3", duration=180, source="youtube")
        await priority_queue_service.add(1, item3, normal_user)
        
        vip_count = await priority_queue_service.get_vip_count(channel_id=1)
        assert vip_count == 2
    
    @pytest.mark.asyncio
    async def test_get_queue_stats(self, priority_queue_service, vip_user, admin_user, normal_user):
        """Test get_queue_stats returns correct statistics."""
        # Add 1 VIP
        item1 = QueueItemCreate(title="VIP", url="http://v.mp3", duration=180, source="youtube")
        await priority_queue_service.add(1, item1, vip_user)
        
        # Add 2 Admin
        item2 = QueueItemCreate(title="Admin1", url="http://a1.mp3", duration=180, source="youtube")
        item3 = QueueItemCreate(title="Admin2", url="http://a2.mp3", duration=180, source="youtube")
        await priority_queue_service.add(1, item2, admin_user)
        await priority_queue_service.add(1, item3, admin_user)
        
        # Add 3 Normal
        for i in range(3):
            item = QueueItemCreate(title=f"Normal{i}", url=f"http://n{i}.mp3", duration=180, source="youtube")
            await priority_queue_service.add(1, item, normal_user)
        
        stats = await priority_queue_service.get_queue_stats(channel_id=1)
        
        assert stats["total"] == 6
        assert stats["vip"] == 1
        assert stats["admin"] == 2
        assert stats["normal"] == 3
    
    @pytest.mark.asyncio
    async def test_superadmin_role_priority(self, priority_queue_service):
        """Test superadmin role gets VIP priority."""
        superadmin = Mock(spec=User)
        superadmin.id = 1
        superadmin.role = "superadmin"
        
        item = QueueItemCreate(title="SuperAdmin", url="http://sa.mp3", duration=180, source="youtube")
        added = await priority_queue_service.add(1, item, superadmin)
        
        # Superadmin should be treated as VIP
        assert added.metadata["is_vip"] is True
    
    @pytest.mark.asyncio
    async def test_close_with_deprecation_warning(self, priority_queue_service):
        """Test close() triggers deprecation warning."""
        # close() is deprecated, should use aclose()
        # This test just ensures it doesn't crash and triggers warning
        with pytest.warns(DeprecationWarning, match="Use aclose\\(\\) instead"):
            await priority_queue_service.close()


# ========== SINGLETON TESTS ==========

class TestSingletonPattern:
    """Test singleton pattern for PriorityQueueService."""
    
    def test_get_priority_queue_service_returns_singleton(self):
        """Test that get_priority_queue_service returns singleton."""
        from src.services.priority_queue_service import get_priority_queue_service, _priority_queue_service
        
        # Reset singleton
        import src.services.priority_queue_service as pqs_module
        pqs_module._priority_queue_service = None
        
        service1 = get_priority_queue_service()
        service2 = get_priority_queue_service()
        
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_shutdown_priority_queue_service(self):
        """Test shutdown_priority_queue_service closes and resets singleton."""
        from src.services.priority_queue_service import (
            get_priority_queue_service,
            shutdown_priority_queue_service,
        )
        import src.services.priority_queue_service as pqs_module
        
        # Create singleton
        pqs_module._priority_queue_service = None
        service = get_priority_queue_service()
        assert service is not None
        
        # Shutdown
        await shutdown_priority_queue_service()
        
        # Singleton should be reset
        assert pqs_module._priority_queue_service is None


# ========== FINAL COVERAGE TESTS ==========

class TestFinalCoverage:
    """Tests for covering remaining lines and branches."""
    
    @pytest.mark.asyncio
    async def test_pop_next_json_decode_error(self, fake_redis):
        """Test pop_next handles JSON decode errors and returns None."""
        service = PriorityQueueService()
        service._redis = fake_redis
        
        channel_id = 123
        key = service._get_queue_key(channel_id)
        
        # Add invalid JSON to sorted set
        await fake_redis.zadd(key, {"invalid_json_data": 1000.0})
        
        # pop_next should handle JSON error gracefully and return None
        result = await service.pop_next(channel_id)
        
        assert result is None  # Returns None on JSON error
    
    @pytest.mark.asyncio
    async def test_get_all_branch_coverage(self, priority_queue_service, vip_user):
        """Test get_all with pagination branches."""
        channel_id = 123
        
        # Add items to queue
        for i in range(5):
            item = QueueItemCreate(
                channel_id=channel_id,
                title=f"Track {i}",
                url=f"https://example.com/track{i}.mp3",
                duration=100 + i
            )
            await priority_queue_service.add(channel_id, item, vip_user)
        
        # Test offset beyond queue size
        result = await priority_queue_service.get_all(
            channel_id=channel_id,
            limit=10,
            offset=100
        )
        
        assert result.total_items == 5
        assert len(result.items) == 0  # No items returned due to offset
        # total_duration = 0 when no items returned (correct behavior)
    
    @pytest.mark.asyncio
    async def test_get_all_json_error_in_items(self, fake_redis):
        """Test get_all continues despite JSON errors in some items."""
        from src.models.queue import QueueItemCreate
        from unittest.mock import Mock
        
        service = PriorityQueueService()
        service._redis = fake_redis
        
        channel_id = 123
        key = service._get_queue_key(channel_id)
        
        # Add mix of valid and invalid JSON
        vip_user = Mock()
        vip_user.id = 1
        vip_user.role = "vip"  # String, not enum
        
        # Valid item
        valid_item = QueueItemCreate(
            channel_id=channel_id,
            title="Valid Track",
            url="https://example.com/valid.mp3",
            duration=100
        )
        await service.add(channel_id, valid_item, vip_user)
        
        # Add invalid JSON manually
        await fake_redis.zadd(key, {"invalid_json": 5000.0})
        
        # get_all should handle JSON error and return valid items only
        result = await service.get_all(channel_id)
        
        # Should have 1 valid item (invalid skipped)
        assert result.total_items >= 1
        assert any(item.title == "Valid Track" for item in result.items)
