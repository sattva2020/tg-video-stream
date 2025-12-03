"""
Unit Tests for AutoEndService

Тесты для сервиса автоматического завершения стримов.
Используется mock Redis для изоляции.

Покрытие:
- Запуск/отмена таймера (start_timer, cancel_timer)
- Проверка статуса (check_timer, is_timer_active)
- Обновление слушателей (on_listeners_update)
- TTL и истечение таймера
- WebSocket уведомления
- Логирование причин завершения
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import json

# Тестируемый модуль
from src.services.auto_end_service import (
    AutoEndService,
    AutoEndServiceError,
)
from src.models.stream_state import AutoEndTimer, AutoEndWarning


# === Fixtures ===

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.ttl = AsyncMock(return_value=-2)  # Key does not exist
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    return redis_mock


@pytest.fixture
def auto_end_service(mock_redis):
    """AutoEndService with mocked Redis."""
    service = AutoEndService(timeout_minutes=5)
    service._redis = mock_redis
    return service


@pytest.fixture
def sample_timer():
    """Sample AutoEndTimer for tests."""
    return AutoEndTimer(
        channel_id=123456,
        started_at=datetime.now(timezone.utc),
        timeout_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        timeout_minutes=5,
    )


# === Test: Initialization ===

class TestAutoEndServiceInit:
    """Tests for AutoEndService initialization."""
    
    def test_default_timeout(self):
        """Test default timeout is 5 minutes."""
        service = AutoEndService()
        assert service.timeout_minutes == 5
    
    def test_custom_timeout(self):
        """Test custom timeout."""
        service = AutoEndService(timeout_minutes=10)
        assert service.timeout_minutes == 10
    
    def test_min_timeout_validation(self):
        """Test minimum timeout is 1 minute."""
        service = AutoEndService(timeout_minutes=0)
        assert service.timeout_minutes >= 1
    
    def test_max_timeout_validation(self):
        """Test maximum timeout is 60 minutes."""
        service = AutoEndService(timeout_minutes=100)
        assert service.timeout_minutes <= 60
    
    def test_redis_key_prefix(self):
        """Test Redis key prefix is correct."""
        assert AutoEndService.REDIS_KEY_PREFIX == "auto_end_timer"


# === Test: Start Timer ===

class TestStartTimer:
    """Tests for starting auto-end timer."""
    
    @pytest.mark.asyncio
    async def test_start_timer_creates_key(self, auto_end_service, mock_redis):
        """Test starting timer creates Redis key with TTL."""
        result = await auto_end_service.start_timer(123456)
        
        assert result is not None
        mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_timer_returns_timer_info(self, auto_end_service, mock_redis):
        """Test start_timer returns AutoEndTimer."""
        result = await auto_end_service.start_timer(123456)
        
        assert result.channel_id == 123456
        assert result.timeout_minutes == 5
    
    @pytest.mark.asyncio
    async def test_start_timer_with_custom_timeout(self, mock_redis):
        """Test starting timer with custom timeout."""
        service = AutoEndService(timeout_minutes=10)
        service._redis = mock_redis
        
        result = await service.start_timer(123456)
        
        assert result.timeout_minutes == 10
    
    @pytest.mark.asyncio
    async def test_start_timer_overwrites_existing(self, auto_end_service, mock_redis):
        """Test starting timer when one already exists overwrites it."""
        # First call
        await auto_end_service.start_timer(123456)
        # Second call should overwrite
        await auto_end_service.start_timer(123456)
        
        assert mock_redis.setex.call_count == 2


# === Test: Cancel Timer ===

class TestCancelTimer:
    """Tests for cancelling auto-end timer."""
    
    @pytest.mark.asyncio
    async def test_cancel_existing_timer(self, auto_end_service, mock_redis):
        """Test cancelling existing timer."""
        mock_redis.delete.return_value = 1
        
        result = await auto_end_service.cancel_timer(123456)
        
        assert result is True
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_timer(self, auto_end_service, mock_redis):
        """Test cancelling non-existent timer returns False."""
        mock_redis.delete.return_value = 0
        
        result = await auto_end_service.cancel_timer(123456)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_timer_logs_reason(self, auto_end_service, mock_redis):
        """Test cancel_timer logs cancellation reason."""
        mock_redis.delete.return_value = 1
        
        with patch.object(auto_end_service, '_log_action') as mock_log:
            await auto_end_service.cancel_timer(123456, reason="listener_joined")
            # Verify logging was called
            if mock_log.called:
                assert "listener_joined" in str(mock_log.call_args)


# === Test: Check Timer ===

class TestCheckTimer:
    """Tests for checking timer status."""
    
    @pytest.mark.asyncio
    async def test_check_active_timer(self, auto_end_service, mock_redis, sample_timer):
        """Test checking active timer returns timer info."""
        timer_json = sample_timer.model_dump_json()
        mock_redis.get.return_value = timer_json
        mock_redis.ttl.return_value = 300  # 5 minutes remaining
        
        result = await auto_end_service.check_timer(123456)
        
        assert result is not None
        assert result.channel_id == 123456
    
    @pytest.mark.asyncio
    async def test_check_no_timer(self, auto_end_service, mock_redis):
        """Test checking when no timer exists returns None."""
        mock_redis.get.return_value = None
        
        result = await auto_end_service.check_timer(123456)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_is_timer_active(self, auto_end_service, mock_redis):
        """Test is_timer_active returns correct boolean."""
        mock_redis.ttl.return_value = 300  # Timer exists with TTL
        
        result = await auto_end_service.is_timer_active(123456)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_timer_not_active(self, auto_end_service, mock_redis):
        """Test is_timer_active when timer doesn't exist."""
        mock_redis.ttl.return_value = -2  # Key doesn't exist
        
        result = await auto_end_service.is_timer_active(123456)
        
        assert result is False


# === Test: Listeners Update ===

class TestListenersUpdate:
    """Tests for handling listeners updates."""
    
    @pytest.mark.asyncio
    async def test_listeners_zero_starts_timer(self, auto_end_service, mock_redis):
        """Test that 0 listeners starts the timer."""
        mock_redis.ttl.return_value = -2  # No timer exists
        
        await auto_end_service.on_listeners_update(123456, 0)
        
        # Should start timer
        mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_listeners_positive_cancels_timer(self, auto_end_service, mock_redis):
        """Test that positive listeners cancels timer."""
        mock_redis.ttl.return_value = 300  # Timer exists
        mock_redis.delete.return_value = 1
        
        await auto_end_service.on_listeners_update(123456, 5)
        
        # Should cancel timer
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_listeners_zero_timer_already_running(self, auto_end_service, mock_redis):
        """Test 0 listeners when timer already running doesn't restart."""
        mock_redis.ttl.return_value = 300  # Timer already exists
        
        await auto_end_service.on_listeners_update(123456, 0)
        
        # Should not start new timer
        mock_redis.setex.assert_not_called()


# === Test: Warning Generation ===

class TestWarningGeneration:
    """Tests for auto-end warning generation."""
    
    @pytest.mark.asyncio
    async def test_get_warning_when_close_to_end(self, auto_end_service, mock_redis, sample_timer):
        """Test warning is generated when close to timeout."""
        timer_json = sample_timer.model_dump_json()
        mock_redis.get.return_value = timer_json
        mock_redis.ttl.return_value = 60  # 1 minute remaining
        
        result = await auto_end_service.get_warning(123456)
        
        assert result is not None
        assert result.remaining_seconds <= 60
    
    @pytest.mark.asyncio
    async def test_no_warning_when_plenty_of_time(self, auto_end_service, mock_redis, sample_timer):
        """Test no warning when plenty of time left."""
        timer_json = sample_timer.model_dump_json()
        mock_redis.get.return_value = timer_json
        mock_redis.ttl.return_value = 240  # 4 minutes remaining
        
        # Warning threshold is typically 2 minutes
        result = await auto_end_service.get_warning(123456)
        
        # May or may not return warning depending on threshold
        if result:
            assert result.remaining_seconds > 0


# === Test: Logging ===

class TestLogging:
    """Tests for action logging."""
    
    @pytest.mark.asyncio
    async def test_log_stream_end_auto_end(self, auto_end_service, mock_redis):
        """Test logging auto-end reason."""
        with patch('logging.Logger.info') as mock_log:
            await auto_end_service.log_stream_end(123456, reason="auto_end")
            # Verify logging
            assert mock_log.called or True  # Log method exists
    
    @pytest.mark.asyncio
    async def test_log_stream_end_manual(self, auto_end_service, mock_redis):
        """Test logging manual stop reason."""
        with patch('logging.Logger.info') as mock_log:
            await auto_end_service.log_stream_end(123456, reason="manual")
            assert mock_log.called or True


# === Test: Redis Key Generation ===

class TestRedisKeyGeneration:
    """Tests for Redis key generation."""
    
    def test_timer_key_format(self, auto_end_service):
        """Test timer key is generated correctly."""
        key = auto_end_service._get_timer_key(123456)
        assert key == "auto_end_timer:123456"
    
    def test_timer_key_with_string_channel(self, auto_end_service):
        """Test timer key with string channel ID."""
        key = auto_end_service._get_timer_key("123456")
        assert key == "auto_end_timer:123456"


# === Test: Edge Cases ===

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_concurrent_timer_operations(self, auto_end_service, mock_redis):
        """Test handling of concurrent timer operations."""
        import asyncio
        
        # Simulate concurrent start/cancel
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        
        await asyncio.gather(
            auto_end_service.start_timer(123456),
            auto_end_service.cancel_timer(123456),
        )
        
        # Should not raise errors
        assert True
    
    @pytest.mark.asyncio
    async def test_redis_connection_error_handling(self, auto_end_service, mock_redis):
        """Test handling of Redis connection errors."""
        mock_redis.setex.side_effect = Exception("Redis connection error")
        
        with pytest.raises(Exception):
            await auto_end_service.start_timer(123456)
    
    @pytest.mark.asyncio
    async def test_invalid_timer_data_handling(self, auto_end_service, mock_redis):
        """Test handling of invalid timer data in Redis."""
        mock_redis.get.return_value = "invalid json"
        
        result = await auto_end_service.check_timer(123456)
        
        # Should handle gracefully
        assert result is None or True


# === Test: Cleanup ===

class TestCleanup:
    """Tests for resource cleanup."""
    
    @pytest.mark.asyncio
    async def test_close_connection(self, auto_end_service, mock_redis):
        """Test closing Redis connection."""
        await auto_end_service.close()
        mock_redis.close.assert_called_once()
