"""
Comprehensive tests for ShazamService.

Covers:
- Service initialization and Redis connection
- Audio recognition (recognize_audio, recognize_track)
- Result parsing and formatting
- Rate limiting (consume_rate_limit, is_rate_limited)
- History management (add_to_history, get_history, delete_from_history)
- Batch recognition
- Edge cases and error handling
"""

import io
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import tempfile
import time

from fakeredis import aioredis
from src.services.shazam_service import ShazamService


# ========== FIXTURES ==========

@pytest.fixture
def fake_redis():
    """FakeRedis client for testing."""
    return aioredis.FakeRedis(decode_responses=True, encoding="utf-8")


@pytest.fixture
def shazam_service(fake_redis):
    """Create ShazamService instance with FakeRedis."""
    return ShazamService(redis_client=fake_redis)


@pytest.fixture
def sample_shazam_response():
    """Sample Shazam API response."""
    return {
        "track": {
            "key": "12345",
            "title": "Test Song",
            "subtitle": "Test Artist • Test Label",
            "images": {
                "coverart": "http://example.com/cover.jpg"
            },
            "sections": [
                {
                    "type": "SONG",
                    "metadata": [
                        {"title": "Album", "text": "Test Album"},
                        {"title": "Released", "text": "2023"}
                    ]
                }
            ],
            "share": {
                "href": "http://shazam.com/track/12345",
                "image": "http://example.com/share.jpg"
            },
            "duration": 180,
            "hub": {
                "actions": [{"id": "action-123"}]
            }
        },
        "matches": [
            {"score": 95.5}
        ],
        "confidence": 0.955
    }


@pytest.fixture
def sample_audio_bytes():
    """Sample audio data."""
    return b'\x00\x01\x02\x03' * 1000  # 4KB of fake audio data


# ========== RATE LIMITING TESTS (EXISTING) ==========

@pytest.mark.asyncio
async def test_recognition_rate_limit_blocks_after_ten_requests(fake_redis):
    """Ensure normal users hit the 10 req/min recognition limit."""
    service = ShazamService(redis_client=fake_redis)

    for _ in range(10):
        allowed, retry_after = await service.consume_rate_limit(user_id=123)
        assert allowed is True
        assert retry_after == 0

    allowed, retry_after = await service.consume_rate_limit(user_id=123)
    assert allowed is False
    assert retry_after > 0


@pytest.mark.asyncio
async def test_is_rate_limited_matches_consume_state(fake_redis):
    """Boolean helper should reflect counter state after limit is exceeded."""
    service = ShazamService(redis_client=fake_redis)

    for _ in range(11):
        await service.consume_rate_limit(user_id=456)

    assert await service.is_rate_limited(user_id=456) is True


@pytest.mark.asyncio
async def test_vip_users_receive_higher_recognition_limit(fake_redis):
    """VIP roles should have a larger allowance (100 req/min)."""
    service = ShazamService(redis_client=fake_redis)

    for _ in range(50):
        allowed, retry_after = await service.consume_rate_limit(user_id=789, user_role="vip")
        assert allowed is True
        assert retry_after == 0

    assert await service.is_rate_limited(user_id=789, user_role="vip") is False


# ========== INITIALIZATION TESTS ==========

class TestShazamServiceInit:
    """Test ShazamService initialization."""
    
    def test_init_creates_service(self):
        """Test that ShazamService initializes correctly."""
        service = ShazamService()
        assert service is not None
        assert service.shazam is not None
        assert service.logger is not None
    
    def test_init_with_redis_client(self, fake_redis):
        """Test initialization with existing Redis client."""
        service = ShazamService(redis_client=fake_redis)
        assert service._redis == fake_redis


# ========== AUDIO RECOGNITION TESTS ==========

class TestAudioRecognition:
    """Test audio recognition functionality."""
    
    @pytest.mark.asyncio
    async def test_recognize_audio_success(self, shazam_service, sample_audio_bytes, sample_shazam_response):
        """Test successful audio recognition."""
        with patch.object(shazam_service.shazam, 'recognize_song', new=AsyncMock(return_value=sample_shazam_response)):
            result = await shazam_service.recognize_audio(sample_audio_bytes)
            
            assert result is not None
            assert result['title'] == "Test Song"
            assert result['artist'] == "Test Artist"
            assert result['album'] == "Test Album"
            assert result['track_id'] == "12345"
            assert result['source'] == "shazam"
    
    @pytest.mark.asyncio
    async def test_recognize_audio_no_match(self, shazam_service, sample_audio_bytes):
        """Test audio recognition with no matches."""
        with patch.object(shazam_service.shazam, 'recognize_song', new=AsyncMock(return_value=None)):
            result = await shazam_service.recognize_audio(sample_audio_bytes)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_recognize_audio_empty_data(self, shazam_service):
        """Test that empty audio data raises ValueError."""
        with pytest.raises(ValueError, match="Audio data is empty"):
            await shazam_service.recognize_audio(b'')
    
    @pytest.mark.asyncio
    async def test_recognize_track_success(self, shazam_service, sample_shazam_response):
        """Test recognize_track with BytesIO buffer."""
        audio_buffer = io.BytesIO(b'\x00\x01\x02\x03' * 1000)
        
        with patch.object(shazam_service.shazam, 'recognize_song', new=AsyncMock(return_value=sample_shazam_response)):
            result = await shazam_service.recognize_track(audio_buffer, user_id=123)
            
            assert result is not None
            assert result['title'] == "Test Song"
    
    @pytest.mark.asyncio
    async def test_recognize_track_empty_buffer(self, shazam_service):
        """Test that empty buffer raises ValueError."""
        audio_buffer = io.BytesIO(b'')
        
        with pytest.raises(ValueError, match="Audio buffer is empty"):
            await shazam_service.recognize_track(audio_buffer, user_id=123)


# ========== RESULT PARSING TESTS ==========

class TestResultParsing:
    """Test Shazam result parsing."""
    
    def test_parse_result_complete(self, shazam_service, sample_shazam_response):
        """Test parsing complete Shazam response."""
        result = shazam_service._parse_result(sample_shazam_response)
        
        assert result['track_id'] == "12345"
        assert result['title'] == "Test Song"
        assert result['artist'] == "Test Artist"
        assert result['album'] == "Test Album"
        assert result['release_year'] == "2023"
        assert 0 <= result['confidence'] <= 1
        assert result['source'] == "shazam"
    
    def test_parse_result_minimal(self, shazam_service):
        """Test parsing minimal Shazam response."""
        minimal_response = {
            "track": {
                "title": "Minimal Song"
            }
        }
        
        result = shazam_service._parse_result(minimal_response)
        
        assert result['title'] == "Minimal Song"
        assert result['artist'] == "Unknown"
        assert result['album'] == "Unknown"
    
    def test_parse_result_confidence_calculation(self, shazam_service):
        """Test confidence score normalization."""
        # Test percentage score (>1)
        response = {
            "track": {"title": "Test"},
            "matches": [{"score": 95.5}]
        }
        result = shazam_service._parse_result(response)
        assert 0 <= result['confidence'] <= 1
        
        # Test decimal score (<1)
        response_decimal = {
            "track": {"title": "Test"},
            "matches": [{"score": 0.95}]
        }
        result_decimal = shazam_service._parse_result(response_decimal)
        assert result_decimal['confidence'] == 0.95
    
    def test_extract_artist_with_label(self, shazam_service):
        """Test artist extraction from subtitle with label."""
        artist = shazam_service._extract_artist("Artist Name • Label Name")
        assert artist == "Artist Name"
    
    def test_extract_artist_no_label(self, shazam_service):
        """Test artist extraction from subtitle without label."""
        artist = shazam_service._extract_artist("Simple Artist")
        assert artist == "Simple Artist"
    
    def test_extract_artist_none(self, shazam_service):
        """Test artist extraction with None subtitle."""
        artist = shazam_service._extract_artist(None)
        assert artist == "Unknown"


# ========== HISTORY MANAGEMENT TESTS ==========

class TestHistoryManagement:
    """Test recognition history management."""
    
    @pytest.mark.asyncio
    async def test_add_to_history_success(self, shazam_service):
        """Test adding recognition to history."""
        await shazam_service.add_to_history(
            user_id=123,
            track_id="track-123",
            artist="Test Artist",
            title="Test Song",
            confidence=0.95
        )
        
        # Verify entry was added
        history = await shazam_service.get_history(user_id=123)
        assert history['total'] > 0
    
    @pytest.mark.asyncio
    async def test_get_history_empty(self, shazam_service):
        """Test retrieving empty history."""
        result = await shazam_service.get_history(user_id=999)
        
        assert result['total'] == 0
        assert len(result['entries']) == 0
    
    @pytest.mark.asyncio
    async def test_get_history_with_entries(self, shazam_service):
        """Test retrieving history with entries."""
        # Add some entries
        await shazam_service.add_to_history(123, "track-1", "Artist 1", "Song 1", 0.9)
        await shazam_service.add_to_history(123, "track-2", "Artist 2", "Song 2", 0.95)
        
        result = await shazam_service.get_history(user_id=123, page=1, page_size=10)
        
        assert result['total'] == 2
        assert len(result['entries']) == 2
    
    @pytest.mark.asyncio
    async def test_get_history_pagination(self, shazam_service):
        """Test history pagination."""
        # Add 5 entries
        for i in range(5):
            await shazam_service.add_to_history(123, f"track-{i}", f"Artist {i}", f"Song {i}", 0.9)
        
        # Get page 1 (2 items)
        page1 = await shazam_service.get_history(user_id=123, page=1, page_size=2)
        assert len(page1['entries']) == 2
        
        # Get page 2 (2 items)
        page2 = await shazam_service.get_history(user_id=123, page=2, page_size=2)
        assert len(page2['entries']) == 2
        
        # Verify different entries
        assert page1['entries'][0]['title'] != page2['entries'][0]['title']
    
    @pytest.mark.asyncio
    async def test_delete_from_history_success(self, shazam_service):
        """Test deleting history entry."""
        await shazam_service.add_to_history(123, "track-123", "Artist", "Song", 0.9)
        history = await shazam_service.get_history(user_id=123)
        entry_id = history['entries'][0]['id']
        
        result = await shazam_service.delete_from_history(entry_id=entry_id)
        
        assert result is True
        
        # Verify entry was deleted
        deleted_entry = await shazam_service.get_history_entry(entry_id)
        assert deleted_entry is None
    
    @pytest.mark.asyncio
    async def test_history_limit_enforcement(self, shazam_service):
        """Test that history enforces HISTORY_LIMIT."""
        # Add more than HISTORY_LIMIT entries
        for i in range(60):
            await shazam_service.add_to_history(123, f"track-{i}", f"Artist {i}", f"Song {i}", 0.9)
        
        history = await shazam_service.get_history(user_id=123, page=1, page_size=100)
        
        # Should not exceed HISTORY_LIMIT (50)
        assert history['total'] <= shazam_service.HISTORY_LIMIT


# ========== BATCH RECOGNITION TESTS ==========

class TestBatchRecognition:
    """Test batch audio recognition."""
    
    @pytest.mark.asyncio
    async def test_batch_recognize_success(self, shazam_service, sample_shazam_response):
        """Test batch recognition with successful results."""
        audio_files = [b'\x00\x01' * 100, b'\x00\x02' * 100, b'\x00\x03' * 100]
        
        with patch.object(shazam_service.shazam, 'recognize_song', new=AsyncMock(return_value=sample_shazam_response)):
            results = await shazam_service.batch_recognize(audio_files)
            
            assert len(results) == 3
            assert all(r is not None for r in results)
    
    @pytest.mark.asyncio
    async def test_batch_recognize_with_failures(self, shazam_service):
        """Test batch recognition with some failures."""
        audio_files = [b'\x00\x01' * 100, b'\x00\x02' * 100]
        
        # First succeeds, second fails
        with patch.object(shazam_service.shazam, 'recognize_song', new=AsyncMock(side_effect=[
            {"track": {"title": "Success"}},
            Exception("Recognition failed")
        ])):
            results = await shazam_service.batch_recognize(audio_files)
            
            assert len(results) == 2
            assert results[0] is not None
            assert results[1] is None


# ========== EDGE CASES ==========

class TestShazamServiceEdgeCases:
    """Test edge cases and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_identify_track_with_rate_limit(self, fake_redis):
        """Test identify_track when rate limited."""
        service = ShazamService(redis_client=fake_redis)
        
        # Exceed rate limit
        for _ in range(15):
            await service.consume_rate_limit(user_id=123)
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp.write(b'\x00\x01' * 1000)
            temp_path = tmp.name
        
        try:
            result = await service.identify_track(
                audio_file=temp_path,
                user_id=123,
                channel_id=1
            )
            
            assert result['success'] is False
            assert result['rate_limited'] is True
            assert result['retry_after'] > 0
        finally:
            import os
            os.remove(temp_path)
    
    def test_sanitize_key_component(self, shazam_service):
        """Test Redis key sanitization."""
        result = shazam_service._sanitize_key_component("user@123!#$")
        assert result == "user123"
        assert '#' not in result
        assert '@' not in result
    
    def test_format_timestamp(self, shazam_service):
        """Test timestamp formatting."""
        timestamp = str(int(time.time()))
        result = shazam_service._format_timestamp(timestamp)
        
        assert result is not None
        assert "T" in result  # ISO format
    
    def test_format_timestamp_invalid(self, shazam_service):
        """Test timestamp formatting with invalid input."""
        result = shazam_service._format_timestamp("invalid")
        assert result == "invalid"