"""
Comprehensive tests for QueueService

Модуль тестирует:
- Инициализацию и Redis соединение
- CRUD операции (add, add_priority, remove, move)
- Query операции (get_all, get_next, get_by_id, get_size, is_empty)
- Playback операции (skip, clear, pop_next)
- Utility операции (get_position, get_all_channel_ids, create_operation)
- Обработку ошибок (QueueFullError, QueueEmptyError, ItemNotFoundError, InvalidPositionError)
- Граничные случаи и edge cases

Coverage target: 70%+
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime
import json
import uuid

from src.services.queue_service import (
    QueueService,
    QueueServiceError,
    QueueFullError,
    QueueEmptyError,
    ItemNotFoundError,
    InvalidPositionError,
    get_queue_service,
    shutdown_queue_service,
)
from src.models.queue import (
    QueueItem,
    QueueItemCreate,
    QueueInfo,
    QueueOperation,
    QueueSource,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_redis():
    """Mock Redis client с основными методами."""
    redis_mock = AsyncMock()
    
    # Методы Redis List
    redis_mock.rpush = AsyncMock(return_value=1)
    redis_mock.lpush = AsyncMock(return_value=1)
    redis_mock.llen = AsyncMock(return_value=0)
    redis_mock.lrange = AsyncMock(return_value=[])
    redis_mock.lrem = AsyncMock(return_value=1)
    redis_mock.lindex = AsyncMock(return_value=None)
    redis_mock.lpop = AsyncMock(return_value=None)
    redis_mock.delete = AsyncMock(return_value=1)
    
    # Pipeline
    pipeline_mock = AsyncMock()
    pipeline_mock.delete = AsyncMock()
    pipeline_mock.rpush = AsyncMock()
    pipeline_mock.execute = AsyncMock(return_value=[])
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)
    redis_mock.pipeline = Mock(return_value=pipeline_mock)
    
    # Scan для get_all_channel_ids
    async def mock_scan_iter(match):
        keys = ["stream_queue:123", "stream_queue:456"]
        for key in keys:
            yield key
    redis_mock.scan_iter = mock_scan_iter
    
    redis_mock.close = AsyncMock()
    
    return redis_mock


@pytest.fixture
def queue_service(mock_redis):
    """QueueService с мокнутым Redis."""
    service = QueueService(redis_url="redis://localhost:6379", max_queue_size=100)
    service._redis = mock_redis
    return service


@pytest.fixture
def sample_queue_item_create():
    """Пример QueueItemCreate для тестов."""
    return QueueItemCreate(
        title="Test Track",
        url="https://example.com/track.mp3",
        duration=180,
        source=QueueSource.YOUTUBE,
        metadata={"artist": "Test Artist"}
    )


@pytest.fixture
def sample_queue_item():
    """Пример QueueItem для тестов."""
    return QueueItem(
        channel_id=123,
        title="Sample Track",
        url="https://example.com/sample.mp3",
        duration=200,
        source=QueueSource.STREAM,
        requested_by=999,
        metadata={"genre": "Electronic"}
    )


# ==================== Test Classes ====================

class TestQueueServiceInit:
    """Тесты инициализации QueueService."""
    
    def test_init_default_params(self):
        """Тест инициализации с параметрами по умолчанию."""
        with patch("src.config.settings.REDIS_URL", "redis://default:6379"):
            service = QueueService()
            
            assert service.redis_url == "redis://default:6379"
            assert service.max_queue_size == 100
            assert service._redis is None
    
    def test_init_custom_params(self):
        """Тест инициализации с кастомными параметрами."""
        service = QueueService(
            redis_url="redis://custom:6380",
            max_queue_size=50
        )
        
        assert service.redis_url == "redis://custom:6380"
        assert service.max_queue_size == 50
        assert service._redis is None
    
    @pytest.mark.asyncio
    async def test_get_redis_lazy_init(self, mock_redis):
        """Тест ленивой инициализации Redis."""
        with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_from_url:
            mock_from_url.return_value = mock_redis
            
            service = QueueService(redis_url="redis://localhost:6379")
            assert service._redis is None
            
            # Первый вызов создает соединение
            redis_client = await service._get_redis()
            assert redis_client is mock_redis
            mock_from_url.assert_called_once_with(
                "redis://localhost:6379",
                decode_responses=True
            )
            
            # Повторный вызов возвращает тот же клиент
            redis_client2 = await service._get_redis()
            assert redis_client2 is mock_redis
            assert mock_from_url.call_count == 1
    
    @pytest.mark.asyncio
    async def test_close_redis_connection(self, queue_service, mock_redis):
        """Тест закрытия Redis соединения."""
        await queue_service.close()
        
        mock_redis.close.assert_called_once()
        assert queue_service._redis is None
    
    @pytest.mark.asyncio
    async def test_close_when_no_connection(self):
        """Тест закрытия когда соединение не было создано."""
        service = QueueService()
        # Не должно быть ошибки
        await service.close()
        assert service._redis is None
    
    def test_get_queue_key_static(self):
        """Тест генерации Redis ключа."""
        key = QueueService._get_queue_key(123)
        assert key == "stream_queue:123"
        
        key2 = QueueService._get_queue_key(456)
        assert key2 == "stream_queue:456"


class TestQueueServiceAdd:
    """Тесты добавления элементов в очередь."""
    
    @pytest.mark.asyncio
    async def test_add_to_empty_queue(
        self, queue_service, mock_redis, sample_queue_item_create
    ):
        """Тест добавления в пустую очередь."""
        mock_redis.llen.return_value = 0
        
        item = await queue_service.add(
            channel_id=123,
            item_create=sample_queue_item_create,
            requested_by=999
        )
        
        assert isinstance(item, QueueItem)
        assert item.channel_id == 123
        assert item.title == "Test Track"
        assert item.url == "https://example.com/track.mp3"
        assert item.duration == 180
        assert item.source == QueueSource.YOUTUBE
        assert item.requested_by == 999
        assert item.metadata["artist"] == "Test Artist"
        
        # Проверяем вызовы Redis
        mock_redis.llen.assert_called_once_with("stream_queue:123")
        mock_redis.rpush.assert_called_once()
        
        # Проверяем что добавлен JSON
        call_args = mock_redis.rpush.call_args[0]
        assert call_args[0] == "stream_queue:123"
        # Второй аргумент - JSON строка
        json_data = json.loads(call_args[1])
        assert json_data["title"] == "Test Track"
    
    @pytest.mark.asyncio
    async def test_add_to_non_empty_queue(
        self, queue_service, mock_redis, sample_queue_item_create
    ):
        """Тест добавления в непустую очередь."""
        mock_redis.llen.return_value = 5
        
        item = await queue_service.add(
            channel_id=123,
            item_create=sample_queue_item_create
        )
        
        assert isinstance(item, QueueItem)
        mock_redis.rpush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_raises_queue_full_error(
        self, queue_service, mock_redis, sample_queue_item_create
    ):
        """Тест ошибки при переполнении очереди."""
        mock_redis.llen.return_value = 100  # Максимальный размер
        
        with pytest.raises(QueueFullError) as exc_info:
            await queue_service.add(
                channel_id=123,
                item_create=sample_queue_item_create
            )
        
        assert "достигла максимального размера" in str(exc_info.value)
        mock_redis.rpush.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_add_without_metadata(self, queue_service, mock_redis):
        """Тест добавления без метаданных."""
        mock_redis.llen.return_value = 0
        
        item_create = QueueItemCreate(
            title="No Meta",
            url="https://example.com/nometa.mp3",
            duration=100,
            source=QueueSource.FILE
        )
        
        item = await queue_service.add(
            channel_id=123,
            item_create=item_create
        )
        
        assert item.metadata == {}


class TestQueueServiceAddPriority:
    """Тесты приоритетного добавления (в начало очереди)."""
    
    @pytest.mark.asyncio
    async def test_add_priority_to_queue(
        self, queue_service, mock_redis, sample_queue_item_create
    ):
        """Тест приоритетного добавления."""
        mock_redis.llen.return_value = 5
        
        item = await queue_service.add_priority(
            channel_id=123,
            item_create=sample_queue_item_create,
            requested_by=888
        )
        
        assert isinstance(item, QueueItem)
        assert item.requested_by == 888
        
        # Проверяем LPUSH (в начало)
        mock_redis.lpush.assert_called_once()
        call_args = mock_redis.lpush.call_args[0]
        assert call_args[0] == "stream_queue:123"
    
    @pytest.mark.asyncio
    async def test_add_priority_raises_queue_full(
        self, queue_service, mock_redis, sample_queue_item_create
    ):
        """Тест ошибки при переполнении (приоритетное)."""
        mock_redis.llen.return_value = 100
        
        with pytest.raises(QueueFullError):
            await queue_service.add_priority(
                channel_id=123,
                item_create=sample_queue_item_create
            )
        
        mock_redis.lpush.assert_not_called()


class TestQueueServiceRemove:
    """Тесты удаления элементов из очереди."""
    
    @pytest.mark.asyncio
    async def test_remove_existing_item(self, queue_service, mock_redis):
        """Тест удаления существующего элемента."""
        item_id = str(uuid.uuid4())
        item = QueueItem(
            channel_id=123,
            title="To Remove",
            url="https://example.com/remove.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        item.id = item_id
        
        # Mock Redis возвращает список с нашим элементом
        mock_redis.lrange.return_value = [item.to_redis_json()]
        mock_redis.lrem.return_value = 1
        
        result = await queue_service.remove(channel_id=123, item_id=item_id)
        
        assert result is True
        mock_redis.lrange.assert_called_once_with("stream_queue:123", 0, -1)
        mock_redis.lrem.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_item(self, queue_service, mock_redis):
        """Тест удаления несуществующего элемента."""
        other_item = QueueItem(
            channel_id=123,
            title="Other",
            url="https://example.com/other.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.lrange.return_value = [other_item.to_redis_json()]
        
        with pytest.raises(ItemNotFoundError) as exc_info:
            await queue_service.remove(channel_id=123, item_id="nonexistent-id")
        
        assert "не найден" in str(exc_info.value)
        mock_redis.lrem.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_remove_from_empty_queue(self, queue_service, mock_redis):
        """Тест удаления из пустой очереди."""
        mock_redis.lrange.return_value = []
        
        with pytest.raises(ItemNotFoundError):
            await queue_service.remove(channel_id=123, item_id="any-id")
    
    @pytest.mark.asyncio
    async def test_remove_with_invalid_json(self, queue_service, mock_redis):
        """Тест обработки некорректного JSON в очереди."""
        mock_redis.lrange.return_value = ["invalid json", '{"malformed"']
        
        with pytest.raises(ItemNotFoundError):
            await queue_service.remove(channel_id=123, item_id="any-id")


class TestQueueServiceMove:
    """Тесты перемещения элементов в очереди."""
    
    @pytest.mark.asyncio
    async def test_move_item_forward(self, queue_service, mock_redis):
        """Тест перемещения элемента вперед (к началу)."""
        items = []
        for i in range(5):
            item = QueueItem(
                channel_id=123,
                title=f"Track {i}",
                url=f"https://example.com/track{i}.mp3",
                duration=100 + i * 10,
                source=QueueSource.STREAM
            )
            items.append(item)
        
        items_json = [item.to_redis_json() for item in items]
        mock_redis.lrange.return_value = items_json
        
        # Перемещаем элемент с позиции 3 на позицию 1
        target_id = items[3].id
        result = await queue_service.move(
            channel_id=123,
            item_id=target_id,
            new_position=1
        )
        
        assert len(result) == 5
        assert result[1].id == target_id
        assert result[1].title == "Track 3"
        
        # Проверяем pipeline операции
        pipeline = mock_redis.pipeline.return_value
        pipeline.delete.assert_called_once()
        assert pipeline.rpush.call_count == 5
    
    @pytest.mark.asyncio
    async def test_move_item_backward(self, queue_service, mock_redis):
        """Тест перемещения элемента назад."""
        items = []
        for i in range(3):
            item = QueueItem(
                channel_id=123,
                title=f"Track {i}",
                url=f"https://example.com/track{i}.mp3",
                duration=100,
                source=QueueSource.STREAM
            )
            items.append(item)
        
        items_json = [item.to_redis_json() for item in items]
        mock_redis.lrange.return_value = items_json
        
        # Перемещаем с позиции 0 на позицию 2
        result = await queue_service.move(
            channel_id=123,
            item_id=items[0].id,
            new_position=2
        )
        
        assert len(result) == 3
        assert result[2].id == items[0].id
    
    @pytest.mark.asyncio
    async def test_move_to_same_position(self, queue_service, mock_redis):
        """Тест перемещения на ту же позицию (нет изменений)."""
        item = QueueItem(
            channel_id=123,
            title="Track",
            url="https://example.com/track.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.lrange.return_value = [item.to_redis_json()]
        
        result = await queue_service.move(
            channel_id=123,
            item_id=item.id,
            new_position=0
        )
        
        assert len(result) == 1
        # Pipeline не должен быть вызван
        pipeline = mock_redis.pipeline.return_value
        pipeline.delete.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_move_nonexistent_item(self, queue_service, mock_redis):
        """Тест перемещения несуществующего элемента."""
        item = QueueItem(
            channel_id=123,
            title="Track",
            url="https://example.com/track.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.lrange.return_value = [item.to_redis_json()]
        
        with pytest.raises(ItemNotFoundError):
            await queue_service.move(
                channel_id=123,
                item_id="nonexistent",
                new_position=0
            )
    
    @pytest.mark.asyncio
    async def test_move_invalid_position_negative(self, queue_service, mock_redis):
        """Тест некорректной позиции (отрицательная)."""
        item = QueueItem(
            channel_id=123,
            title="Track",
            url="https://example.com/track.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.lrange.return_value = [item.to_redis_json()]
        
        with pytest.raises(InvalidPositionError) as exc_info:
            await queue_service.move(
                channel_id=123,
                item_id=item.id,
                new_position=-1
            )
        
        assert "Некорректная позиция" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_move_invalid_position_too_large(self, queue_service, mock_redis):
        """Тест некорректной позиции (за пределами очереди)."""
        item = QueueItem(
            channel_id=123,
            title="Track",
            url="https://example.com/track.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.lrange.return_value = [item.to_redis_json()]
        
        with pytest.raises(InvalidPositionError):
            await queue_service.move(
                channel_id=123,
                item_id=item.id,
                new_position=10
            )


class TestQueueServiceQuery:
    """Тесты query операций (get_all, get_next, get_by_id, get_size, is_empty)."""
    
    @pytest.mark.asyncio
    async def test_get_all_with_items(self, queue_service, mock_redis):
        """Тест получения всей очереди."""
        items = []
        for i in range(3):
            item = QueueItem(
                channel_id=123,
                title=f"Track {i}",
                url=f"https://example.com/track{i}.mp3",
                duration=100 + i * 50,
                source=QueueSource.STREAM
            )
            items.append(item)
        
        items_json = [item.to_redis_json() for item in items]
        mock_redis.llen.return_value = 3
        mock_redis.lrange.return_value = items_json
        
        result = await queue_service.get_all(channel_id=123)
        
        assert isinstance(result, QueueInfo)
        assert result.channel_id == 123
        assert result.total_items == 3
        assert len(result.items) == 3
        assert result.total_duration == 100 + 150 + 200  # 450
        
        mock_redis.lrange.assert_called_once_with("stream_queue:123", 0, 49)
    
    @pytest.mark.asyncio
    async def test_get_all_empty_queue(self, queue_service, mock_redis):
        """Тест получения пустой очереди."""
        mock_redis.llen.return_value = 0
        mock_redis.lrange.return_value = []
        
        result = await queue_service.get_all(channel_id=123)
        
        assert result.total_items == 0
        assert len(result.items) == 0
        assert result.total_duration == 0
    
    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, queue_service, mock_redis):
        """Тест пагинации."""
        items = [
            QueueItem(
                channel_id=123,
                title="Track",
                url="https://example.com/track.mp3",
                duration=100,
                source=QueueSource.STREAM
            ).to_redis_json()
        ]
        
        mock_redis.llen.return_value = 100
        mock_redis.lrange.return_value = items
        
        result = await queue_service.get_all(
            channel_id=123,
            limit=10,
            offset=20
        )
        
        assert result.total_items == 100
        mock_redis.lrange.assert_called_once_with("stream_queue:123", 20, 29)
    
    @pytest.mark.asyncio
    async def test_get_all_handles_invalid_json(self, queue_service, mock_redis):
        """Тест обработки некорректного JSON."""
        mock_redis.llen.return_value = 2
        mock_redis.lrange.return_value = ["invalid json", "also bad"]
        
        result = await queue_service.get_all(channel_id=123)
        
        assert result.total_items == 2
        assert len(result.items) == 0  # Все элементы пропущены
    
    @pytest.mark.asyncio
    async def test_get_next_existing(self, queue_service, mock_redis):
        """Тест получения следующего элемента."""
        item = QueueItem(
            channel_id=123,
            title="Next Track",
            url="https://example.com/next.mp3",
            duration=150,
            source=QueueSource.YOUTUBE
        )
        
        mock_redis.lindex.return_value = item.to_redis_json()
        
        result = await queue_service.get_next(channel_id=123)
        
        assert isinstance(result, QueueItem)
        assert result.title == "Next Track"
        
        mock_redis.lindex.assert_called_once_with("stream_queue:123", 0)
    
    @pytest.mark.asyncio
    async def test_get_next_empty_queue(self, queue_service, mock_redis):
        """Тест get_next на пустой очереди."""
        mock_redis.lindex.return_value = None
        
        result = await queue_service.get_next(channel_id=123)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_next_invalid_json(self, queue_service, mock_redis):
        """Тест get_next с некорректным JSON."""
        mock_redis.lindex.return_value = "invalid json"
        
        result = await queue_service.get_next(channel_id=123)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, queue_service, mock_redis):
        """Тест получения элемента по ID."""
        item = QueueItem(
            channel_id=123,
            title="Found",
            url="https://example.com/found.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.lrange.return_value = [item.to_redis_json()]
        
        result = await queue_service.get_by_id(channel_id=123, item_id=item.id)
        
        assert isinstance(result, QueueItem)
        assert result.id == item.id
        assert result.title == "Found"
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, queue_service, mock_redis):
        """Тест get_by_id когда элемент не найден."""
        item = QueueItem(
            channel_id=123,
            title="Other",
            url="https://example.com/other.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.lrange.return_value = [item.to_redis_json()]
        
        result = await queue_service.get_by_id(channel_id=123, item_id="nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_size(self, queue_service, mock_redis):
        """Тест получения размера очереди."""
        mock_redis.llen.return_value = 42
        
        size = await queue_service.get_size(channel_id=123)
        
        assert size == 42
        mock_redis.llen.assert_called_once_with("stream_queue:123")
    
    @pytest.mark.asyncio
    async def test_is_empty_true(self, queue_service, mock_redis):
        """Тест проверки пустой очереди."""
        mock_redis.llen.return_value = 0
        
        result = await queue_service.is_empty(channel_id=123)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_empty_false(self, queue_service, mock_redis):
        """Тест проверки непустой очереди."""
        mock_redis.llen.return_value = 5
        
        result = await queue_service.is_empty(channel_id=123)
        
        assert result is False


class TestQueueServicePlayback:
    """Тесты playback операций (skip, clear, pop_next)."""
    
    @pytest.mark.asyncio
    async def test_skip_track(self, queue_service, mock_redis):
        """Тест пропуска текущего трека."""
        skipped_item = QueueItem(
            channel_id=123,
            title="Skipped",
            url="https://example.com/skipped.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        next_item = QueueItem(
            channel_id=123,
            title="Next",
            url="https://example.com/next.mp3",
            duration=120,
            source=QueueSource.YOUTUBE
        )
        
        mock_redis.llen.return_value = 2
        mock_redis.lpop.return_value = skipped_item.to_redis_json()
        mock_redis.lindex.return_value = next_item.to_redis_json()
        
        result = await queue_service.skip(channel_id=123)
        
        assert isinstance(result, QueueItem)
        assert result.title == "Next"
        
        mock_redis.lpop.assert_called_once_with("stream_queue:123")
        mock_redis.lindex.assert_called_once_with("stream_queue:123", 0)
    
    @pytest.mark.asyncio
    async def test_skip_empty_queue(self, queue_service, mock_redis):
        """Тест skip на пустой очереди."""
        mock_redis.llen.return_value = 0
        
        with pytest.raises(QueueEmptyError) as exc_info:
            await queue_service.skip(channel_id=123)
        
        assert "пуста" in str(exc_info.value)
        mock_redis.lpop.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_skip_last_item(self, queue_service, mock_redis):
        """Тест skip последнего элемента (очередь станет пустой)."""
        item = QueueItem(
            channel_id=123,
            title="Last",
            url="https://example.com/last.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.llen.return_value = 1
        mock_redis.lpop.return_value = item.to_redis_json()
        mock_redis.lindex.return_value = None
        
        result = await queue_service.skip(channel_id=123)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_skip_with_invalid_json(self, queue_service, mock_redis):
        """Тест skip с некорректным JSON (не падает)."""
        mock_redis.llen.return_value = 1
        mock_redis.lpop.return_value = "invalid json"
        mock_redis.lindex.return_value = None
        
        result = await queue_service.skip(channel_id=123)
        
        # Не должно упасть, просто вернет None
        assert result is None
    
    @pytest.mark.asyncio
    async def test_clear_queue(self, queue_service, mock_redis):
        """Тест очистки очереди."""
        mock_redis.llen.return_value = 10
        mock_redis.delete.return_value = 1
        
        count = await queue_service.clear(channel_id=123)
        
        assert count == 10
        mock_redis.llen.assert_called_once_with("stream_queue:123")
        mock_redis.delete.assert_called_once_with("stream_queue:123")
    
    @pytest.mark.asyncio
    async def test_clear_empty_queue(self, queue_service, mock_redis):
        """Тест очистки пустой очереди."""
        mock_redis.llen.return_value = 0
        
        count = await queue_service.clear(channel_id=123)
        
        assert count == 0
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pop_next_item(self, queue_service, mock_redis):
        """Тест извлечения следующего элемента."""
        item = QueueItem(
            channel_id=123,
            title="Pop Me",
            url="https://example.com/pop.mp3",
            duration=130,
            source=QueueSource.FILE
        )
        
        mock_redis.lpop.return_value = item.to_redis_json()
        
        result = await queue_service.pop_next(channel_id=123)
        
        assert isinstance(result, QueueItem)
        assert result.title == "Pop Me"
        
        mock_redis.lpop.assert_called_once_with("stream_queue:123")
    
    @pytest.mark.asyncio
    async def test_pop_next_empty_queue(self, queue_service, mock_redis):
        """Тест pop_next на пустой очереди."""
        mock_redis.lpop.return_value = None
        
        result = await queue_service.pop_next(channel_id=123)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_pop_next_invalid_json(self, queue_service, mock_redis):
        """Тест pop_next с некорректным JSON."""
        mock_redis.lpop.return_value = "invalid json"
        
        result = await queue_service.pop_next(channel_id=123)
        
        assert result is None


class TestQueueServiceUtility:
    """Тесты utility операций (get_position, get_all_channel_ids, create_operation)."""
    
    @pytest.mark.asyncio
    async def test_get_position_found(self, queue_service, mock_redis):
        """Тест получения позиции элемента."""
        items = []
        for i in range(5):
            item = QueueItem(
                channel_id=123,
                title=f"Track {i}",
                url=f"https://example.com/track{i}.mp3",
                duration=100,
                source=QueueSource.STREAM
            )
            items.append(item)
        
        items_json = [item.to_redis_json() for item in items]
        mock_redis.lrange.return_value = items_json
        
        position = await queue_service.get_position(
            channel_id=123,
            item_id=items[2].id
        )
        
        assert position == 2
    
    @pytest.mark.asyncio
    async def test_get_position_not_found(self, queue_service, mock_redis):
        """Тест get_position для несуществующего элемента."""
        item = QueueItem(
            channel_id=123,
            title="Track",
            url="https://example.com/track.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.lrange.return_value = [item.to_redis_json()]
        
        position = await queue_service.get_position(
            channel_id=123,
            item_id="nonexistent"
        )
        
        assert position is None
    
    @pytest.mark.asyncio
    async def test_get_all_channel_ids(self, queue_service, mock_redis):
        """Тест получения списка всех каналов."""
        # mock_redis.scan_iter уже настроен в fixture
        
        channel_ids = await queue_service.get_all_channel_ids()
        
        assert isinstance(channel_ids, list)
        assert 123 in channel_ids
        assert 456 in channel_ids
    
    @pytest.mark.asyncio
    async def test_get_all_channel_ids_empty(self, queue_service, mock_redis):
        """Тест когда нет активных очередей."""
        async def empty_scan(*args, **kwargs):
            return
            yield  # Сделать функцию генератором
        
        mock_redis.scan_iter = empty_scan
        
        channel_ids = await queue_service.get_all_channel_ids()
        
        assert channel_ids == []
    
    @pytest.mark.asyncio
    async def test_get_all_channel_ids_invalid_keys(self, queue_service, mock_redis):
        """Тест обработки некорректных ключей Redis."""
        async def invalid_scan(*args, **kwargs):
            yield "stream_queue:invalid"
            yield "stream_queue:"
            yield "other_key:123"
        
        mock_redis.scan_iter = invalid_scan
        
        channel_ids = await queue_service.get_all_channel_ids()
        
        # Должны быть пропущены некорректные ключи
        assert isinstance(channel_ids, list)
    
    @pytest.mark.asyncio
    async def test_create_operation_full(self, queue_service):
        """Тест создания QueueOperation со всеми параметрами."""
        op = await queue_service.create_operation(
            operation_type="move",
            channel_id=123,
            item_id="test-id",
            position=5
        )
        
        assert isinstance(op, QueueOperation)
        assert op.operation == "move"
        assert op.channel_id == 123
        assert op.item_id == "test-id"
        assert op.position == 5
    
    @pytest.mark.asyncio
    async def test_create_operation_minimal(self, queue_service):
        """Тест создания QueueOperation с минимальными параметрами."""
        op = await queue_service.create_operation(
            operation_type="clear",
            channel_id=456
        )
        
        assert op.operation == "clear"
        assert op.channel_id == 456
        assert op.item_id is None
        assert op.position is None


class TestQueueServiceSingleton:
    """Тесты singleton функций."""
    
    @pytest.mark.asyncio
    async def test_get_queue_service_singleton(self):
        """Тест получения singleton экземпляра."""
        service1 = get_queue_service()
        service2 = get_queue_service()
        
        assert service1 is service2
        assert isinstance(service1, QueueService)
    
    @pytest.mark.asyncio
    async def test_shutdown_queue_service(self):
        """Тест shutdown singleton."""
        # Сначала получаем экземпляр
        service = get_queue_service()
        assert service is not None
        
        with patch.object(service, 'close', new_callable=AsyncMock) as mock_close:
            await shutdown_queue_service()
            mock_close.assert_called_once()
        
        # После shutdown должен создаться новый экземпляр
        new_service = get_queue_service()
        assert new_service is not None
    
    @pytest.mark.asyncio
    async def test_shutdown_when_no_service(self):
        """Тест shutdown когда сервис не создан."""
        # Сначала обнуляем глобальный экземпляр
        import src.services.queue_service as qs_module
        qs_module._queue_service = None
        
        # Не должно быть ошибки
        await shutdown_queue_service()


class TestQueueServiceEdgeCases:
    """Тесты граничных случаев и edge cases."""
    
    @pytest.mark.asyncio
    async def test_add_with_max_queue_size_minus_one(self, mock_redis):
        """Тест добавления когда очередь почти полная."""
        service = QueueService(max_queue_size=10)
        service._redis = mock_redis
        
        mock_redis.llen.return_value = 9  # 9/10
        
        item_create = QueueItemCreate(
            title="Last One",
            url="https://example.com/last.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        # Должно пройти
        item = await service.add(channel_id=123, item_create=item_create)
        assert isinstance(item, QueueItem)
    
    @pytest.mark.asyncio
    async def test_move_single_item_queue(self, queue_service, mock_redis):
        """Тест перемещения в очереди из 1 элемента."""
        item = QueueItem(
            channel_id=123,
            title="Only",
            url="https://example.com/only.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        mock_redis.lrange.return_value = [item.to_redis_json()]
        
        result = await queue_service.move(
            channel_id=123,
            item_id=item.id,
            new_position=0
        )
        
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_get_all_with_items_without_duration(self, queue_service, mock_redis):
        """Тест get_all с элементами без duration."""
        item1 = QueueItem(
            channel_id=123,
            title="No Duration",
            url="https://example.com/nodur.mp3",
            duration=None,
            source=QueueSource.STREAM
        )
        item2 = QueueItem(
            channel_id=123,
            title="With Duration",
            url="https://example.com/withdur.mp3",
            duration=150,
            source=QueueSource.YOUTUBE
        )
        
        mock_redis.llen.return_value = 2
        mock_redis.lrange.return_value = [
            item1.to_redis_json(),
            item2.to_redis_json()
        ]
        
        result = await queue_service.get_all(channel_id=123)
        
        assert result.total_items == 2
        assert result.total_duration == 150  # Только item2
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_simulation(self, queue_service, mock_redis):
        """Тест симуляции конкурентных операций (через pipeline)."""
        items = []
        for i in range(3):
            item = QueueItem(
                channel_id=123,
                title=f"Track {i}",
                url=f"https://example.com/track{i}.mp3",
                duration=100,
                source=QueueSource.STREAM
            )
            items.append(item)
        
        items_json = [item.to_redis_json() for item in items]
        mock_redis.lrange.return_value = items_json
        
        # move использует pipeline для атомарности
        result = await queue_service.move(
            channel_id=123,
            item_id=items[0].id,
            new_position=2
        )
        
        # Проверяем что pipeline был создан с transaction=True
        mock_redis.pipeline.assert_called_once_with(transaction=True)


class TestQueueServiceAdditionalCoverage:
    """Тесты для покрытия оставшихся веток кода."""
    
    @pytest.mark.asyncio
    async def test_remove_with_json_error_raises_not_found(self, queue_service, mock_redis):
        """Тест remove выбрасывает ItemNotFoundError при невалидном JSON."""
        # Невалидный JSON в очереди
        mock_redis.lrange.return_value = [
            b'invalid_json_data_here',
            b'{"malformed": json'
        ]
        
        with pytest.raises(ItemNotFoundError):
            await queue_service.remove(channel_id=123, item_id="some_id")
    
    @pytest.mark.asyncio
    async def test_get_by_id_with_json_error_continues(self, queue_service, mock_redis):
        """Тест get_by_id продолжает поиск при ошибках парсинга."""
        valid_item = QueueItem(
            channel_id=123,
            title="Valid Track",
            url="https://example.com/track.mp3",
            duration=100,
            source=QueueSource.STREAM
        )
        
        # Невалидные элементы и валидный в конце
        mock_redis.lrange.return_value = [
            b'{"broken": json',
            b'not_json_at_all',
            valid_item.to_redis_json()
        ]
        
        result = await queue_service.get_by_id(channel_id=123, item_id=valid_item.id)
        
        assert result is not None
        assert result.id == valid_item.id
        assert result.title == "Valid Track"
    
    @pytest.mark.asyncio
    async def test_get_position_with_json_errors_continues(self, queue_service, mock_redis):
        """Тест get_position продолжает поиск при ошибках парсинга."""
        target_item = QueueItem(
            channel_id=123,
            title="Target Track",
            url="https://example.com/target.mp3",
            duration=200,
            source=QueueSource.STREAM
        )
        
        # Невалидные элементы и целевой в позиции 2
        mock_redis.lrange.return_value = [
            b'{"invalid": json}',
            b'not_a_json_string',
            target_item.to_redis_json()
        ]
        
        result = await queue_service.get_position(channel_id=123, item_id=target_item.id)
        
        # Должен вернуть корректную позицию (2) несмотря на невалидные элементы
        assert result == 2
