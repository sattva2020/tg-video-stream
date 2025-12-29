"""
Unit Tests for QueueService

Тесты для сервиса управления очередью воспроизведения.
Используется fakeredis для изоляции от реального Redis.

Покрытие:
- Добавление элементов (add_item, priority_add)
- Удаление элементов (remove_item)
- Перемещение элементов (move_item)
- Получение очереди (get_queue, get_item)
- Пропуск трека (skip_current)
- Ограничения (max_queue_size)
- Edge cases (пустая очередь, дубликаты)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

# Тестируемый модуль
from src.services.queue_service import (
    QueueService,
    QueueServiceError,
    QueueFullError,
    QueueEmptyError,
    ItemNotFoundError,
    InvalidPositionError,
)
from src.models.queue import QueueItem, QueueItemCreate, QueueSource


# === Fixtures ===

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.llen = AsyncMock(return_value=0)
    redis_mock.rpush = AsyncMock(return_value=1)
    redis_mock.lpush = AsyncMock(return_value=1)
    redis_mock.lrange = AsyncMock(return_value=[])
    redis_mock.lrem = AsyncMock(return_value=1)
    redis_mock.lindex = AsyncMock(return_value=None)
    redis_mock.lset = AsyncMock()
    redis_mock.linsert = AsyncMock(return_value=1)
    redis_mock.lpop = AsyncMock(return_value=None)
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def queue_service(mock_redis):
    """QueueService with mocked Redis."""
    service = QueueService(redis_url="redis://localhost:6379", max_queue_size=100)
    service._redis = mock_redis
    return service


@pytest.fixture
def sample_queue_item():
    """Sample QueueItem for tests."""
    return QueueItem(
        id=str(uuid4()),
        channel_id=123456,
        title="Test Track",
        url="https://youtube.com/watch?v=test123",
        source=QueueSource.YOUTUBE,
        duration=180,
        requested_by=789,
        added_at=datetime.now(timezone.utc),
        position=0,
    )


@pytest.fixture
def sample_queue_item_create():
    """Sample QueueItemCreate for adding items."""
    return QueueItemCreate(
        channel_id=123456,
        title="Test Track",
        url="https://youtube.com/watch?v=test123",
        source=QueueSource.YOUTUBE,
        duration=180,
        requested_by=789,
    )


# === Test: Initialization ===

class TestQueueServiceInit:
    """Tests for QueueService initialization."""
    
    def test_default_max_queue_size(self):
        """Test default max queue size is 100."""
        service = QueueService(redis_url="redis://localhost:6379")
        assert service.max_queue_size == 100
    
    def test_custom_max_queue_size(self):
        """Test custom max queue size."""
        service = QueueService(redis_url="redis://localhost:6379", max_queue_size=50)
        assert service.max_queue_size == 50
    
    def test_redis_key_prefix(self):
        """Test Redis key prefix is correct."""
        assert QueueService.REDIS_KEY_PREFIX == "stream_queue"


# === Test: Add Item ===

class TestAddItem:
    """Tests for adding items to queue."""
    
    @pytest.mark.asyncio
    async def test_add_item_to_empty_queue(self, queue_service, mock_redis, sample_queue_item_create):
        """Test adding item to empty queue."""
        mock_redis.llen.return_value = 0
        mock_redis.rpush.return_value = 1
        
        result = await queue_service.add_item(123456, sample_queue_item_create)
        
        assert result is not None
        assert result.title == "Test Track"
        assert result.channel_id == 123456
        mock_redis.rpush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_item_queue_full(self, queue_service, mock_redis, sample_queue_item_create):
        """Test adding item when queue is full raises QueueFullError."""
        mock_redis.llen.return_value = 100  # Queue is full
        
        with pytest.raises(QueueFullError):
            await queue_service.add_item(123456, sample_queue_item_create)
    
    @pytest.mark.asyncio
    async def test_priority_add_to_front(self, queue_service, mock_redis, sample_queue_item_create):
        """Test priority add puts item at front of queue."""
        mock_redis.llen.return_value = 5
        mock_redis.lpush.return_value = 6
        
        result = await queue_service.priority_add(123456, sample_queue_item_create)
        
        assert result is not None
        mock_redis.lpush.assert_called_once()


# === Test: Remove Item ===

class TestRemoveItem:
    """Tests for removing items from queue."""
    
    @pytest.mark.asyncio
    async def test_remove_existing_item(self, queue_service, mock_redis, sample_queue_item):
        """Test removing existing item from queue."""
        item_json = sample_queue_item.model_dump_json()
        mock_redis.lrange.return_value = [item_json]
        mock_redis.lrem.return_value = 1
        
        result = await queue_service.remove_item(123456, sample_queue_item.id)
        
        assert result is True
        mock_redis.lrem.assert_called()
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_item(self, queue_service, mock_redis):
        """Test removing non-existent item raises ItemNotFoundError."""
        mock_redis.lrange.return_value = []
        mock_redis.lrem.return_value = 0
        
        with pytest.raises(ItemNotFoundError):
            await queue_service.remove_item(123456, "nonexistent-id")


# === Test: Get Queue ===

class TestGetQueue:
    """Tests for getting queue contents."""
    
    @pytest.mark.asyncio
    async def test_get_empty_queue(self, queue_service, mock_redis):
        """Test getting empty queue returns empty list."""
        mock_redis.lrange.return_value = []
        mock_redis.llen.return_value = 0
        
        result = await queue_service.get_queue(123456)
        
        assert result.items == []
        assert result.total_items == 0
    
    @pytest.mark.asyncio
    async def test_get_queue_with_items(self, queue_service, mock_redis, sample_queue_item):
        """Test getting queue with items."""
        item_json = sample_queue_item.model_dump_json()
        mock_redis.lrange.return_value = [item_json]
        mock_redis.llen.return_value = 1
        
        result = await queue_service.get_queue(123456)
        
        assert len(result.items) == 1
        assert result.total_items == 1


# === Test: Move Item ===

class TestMoveItem:
    """Tests for moving items in queue."""
    
    @pytest.mark.asyncio
    async def test_move_item_forward(self, queue_service, mock_redis, sample_queue_item):
        """Test moving item to later position."""
        item_json = sample_queue_item.model_dump_json()
        mock_redis.lrange.return_value = [item_json, '{"id": "other"}']
        mock_redis.llen.return_value = 2
        
        # Mock the full move operation
        mock_redis.lrem.return_value = 1
        mock_redis.linsert.return_value = 2
        
        result = await queue_service.move_item(123456, sample_queue_item.id, 1)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_move_to_same_position(self, queue_service, mock_redis, sample_queue_item):
        """Test moving item to same position is no-op."""
        item_json = sample_queue_item.model_dump_json()
        mock_redis.lrange.return_value = [item_json]
        mock_redis.llen.return_value = 1
        
        # Should succeed without actually moving
        result = await queue_service.move_item(123456, sample_queue_item.id, 0)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_move_to_invalid_position(self, queue_service, mock_redis, sample_queue_item):
        """Test moving to invalid position raises error."""
        item_json = sample_queue_item.model_dump_json()
        mock_redis.lrange.return_value = [item_json]
        mock_redis.llen.return_value = 1
        
        with pytest.raises(InvalidPositionError):
            await queue_service.move_item(123456, sample_queue_item.id, 100)


# === Test: Skip Current ===

class TestSkipCurrent:
    """Tests for skipping current track."""
    
    @pytest.mark.asyncio
    async def test_skip_with_items(self, queue_service, mock_redis, sample_queue_item):
        """Test skipping current track returns next item."""
        item_json = sample_queue_item.model_dump_json()
        mock_redis.lpop.return_value = item_json
        
        result = await queue_service.skip_current(123456)
        
        assert result is not None
        mock_redis.lpop.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_skip_empty_queue(self, queue_service, mock_redis):
        """Test skipping on empty queue returns None."""
        mock_redis.lpop.return_value = None
        
        result = await queue_service.skip_current(123456)
        
        assert result is None


# === Test: Edge Cases ===

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_queue_key_generation(self, queue_service):
        """Test Redis key is generated correctly."""
        key = queue_service._get_queue_key(123456)
        assert key == "stream_queue:123456"
    
    @pytest.mark.asyncio
    async def test_duplicate_items_allowed(self, queue_service, mock_redis, sample_queue_item_create):
        """Test that duplicate items (same URL) are allowed."""
        mock_redis.llen.return_value = 1
        mock_redis.rpush.return_value = 2
        
        # Add same item twice should work (each gets unique ID)
        result1 = await queue_service.add_item(123456, sample_queue_item_create)
        result2 = await queue_service.add_item(123456, sample_queue_item_create)
        
        # Both should have different IDs
        assert result1.id != result2.id
    
    @pytest.mark.asyncio
    async def test_get_item_by_id(self, queue_service, mock_redis, sample_queue_item):
        """Test getting specific item by ID."""
        item_json = sample_queue_item.model_dump_json()
        mock_redis.lrange.return_value = [item_json]
        
        result = await queue_service.get_item(123456, sample_queue_item.id)
        
        assert result is not None
        assert result.id == sample_queue_item.id
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_item(self, queue_service, mock_redis):
        """Test getting non-existent item raises error."""
        mock_redis.lrange.return_value = []
        
        with pytest.raises(ItemNotFoundError):
            await queue_service.get_item(123456, "nonexistent-id")


# === Test: Redis Connection ===

class TestRedisConnection:
    """Tests for Redis connection handling."""
    
    @pytest.mark.asyncio
    async def test_lazy_redis_initialization(self):
        """Test Redis client is lazily initialized."""
        service = QueueService(redis_url="redis://localhost:6379")
        assert service._redis is None
    
    @pytest.mark.asyncio
    async def test_close_connection(self, queue_service, mock_redis):
        """Test closing Redis connection."""
        await queue_service.close()
        mock_redis.close.assert_called_once()
