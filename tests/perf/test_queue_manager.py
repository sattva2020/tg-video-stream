import pytest
import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
# Add streamer directory to path to allow imports like 'import audio_utils' inside streamer modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../streamer")))

from streamer.queue_manager import StreamQueue

@pytest.mark.asyncio
async def test_queue_buffering():
    # Mock dependencies
    with patch('streamer.queue_manager.expand_playlist', new_callable=AsyncMock) as mock_expand, \
         patch('streamer.queue_manager.best_stream_url', new_callable=AsyncMock) as mock_best_url, \
         patch('streamer.audio_utils.is_audio_file', return_value=False), \
         patch('streamer.audio_utils.detect_content_type', new_callable=AsyncMock, return_value="video/mp4"), \
         patch('streamer.audio_utils.get_transcoding_profile', return_value=None):

        mock_expand.side_effect = lambda urls: [urls[0]] # Return same url
        mock_best_url.side_effect = lambda url: f"direct_{url}"

        queue = StreamQueue(max_buffer_size=2)
        items = [
            {"url": "http://example.com/1", "id": "1"},
            {"url": "http://example.com/2", "id": "2"},
            {"url": "http://example.com/3", "id": "3"},
        ]
        
        queue.add_items(items)
        
        # Wait a bit for buffering to happen
        await asyncio.sleep(0.1)
        
        assert not queue.queue.empty()
        
        # Get first item
        item1 = await queue.get_next()
        assert item1["link"] == "http://example.com/1"
        assert item1["direct_url"] == "direct_http://example.com/1"
        
        # Get second item
        item2 = await queue.get_next()
        assert item2["link"] == "http://example.com/2"
        
        # Get third item
        item3 = await queue.get_next()
        assert item3["link"] == "http://example.com/3"
        
        await queue.stop()

@pytest.mark.asyncio
async def test_queue_expansion():
    # Mock dependencies
    with patch('streamer.queue_manager.expand_playlist', new_callable=AsyncMock) as mock_expand, \
         patch('streamer.queue_manager.best_stream_url', new_callable=AsyncMock) as mock_best_url, \
         patch('streamer.audio_utils.is_audio_file', return_value=False), \
         patch('streamer.audio_utils.detect_content_type', new_callable=AsyncMock, return_value="video/mp4"), \
         patch('streamer.audio_utils.get_transcoding_profile', return_value=None):

        # Mock expansion returning 2 items
        mock_expand.return_value = ["http://expanded/1", "http://expanded/2"]
        mock_best_url.side_effect = lambda url: f"direct_{url}"

        queue = StreamQueue(max_buffer_size=5)
        items = [{"url": "http://playlist.com", "id": "p1"}]
        
        queue.add_items(items)
        
        await asyncio.sleep(0.1)
        
        item1 = await queue.get_next()
        assert item1["link"] == "http://expanded/1"
        assert item1["track_id"] == "p1"
        
        item2 = await queue.get_next()
        assert item2["link"] == "http://expanded/2"
        assert item2["track_id"] == "p1"
        
        await queue.stop()
