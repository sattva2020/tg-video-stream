import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

# Add streamer directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'streamer')))

import audio_utils
import utils


def async_test(coro):
    """Decorator to run async test methods."""
    def wrapper(*args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(coro(*args, **kwargs))
    return wrapper


class TestPhase5Audio(unittest.TestCase):

    def test_is_audio_file(self):
        self.assertTrue(audio_utils.is_audio_file("http://example.com/song.mp3"))
        self.assertTrue(audio_utils.is_audio_file("https://server.org/music.flac"))
        self.assertFalse(audio_utils.is_audio_file("http://example.com/video.mp4"))
        self.assertFalse(audio_utils.is_audio_file("http://example.com/page.html"))

    def test_parse_m3u_content(self):
        content = """
        #EXTM3U
        #EXTINF:123, Sample Artist - Sample Title
        http://example.com/song1.mp3
        
        # Comment
        http://example.com/song2.mp3
        """
        urls = audio_utils.parse_m3u_content(content)
        self.assertEqual(urls, ["http://example.com/song1.mp3", "http://example.com/song2.mp3"])

    @patch('audio_utils.requests.get')
    @async_test
    async def test_fetch_playlist(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'audio/x-mpegurl'}
        mock_response.text = "http://example.com/stream.mp3"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        urls = await audio_utils.fetch_playlist("http://example.com/playlist.m3u")
        self.assertEqual(urls, ["http://example.com/stream.mp3"])

    @patch('utils.audio_utils.fetch_playlist', new_callable=AsyncMock)
    @async_test
    async def test_expand_playlist_with_m3u(self, mock_fetch):
        mock_fetch.return_value = ["http://example.com/song1.mp3", "http://example.com/song2.mp3"]
        
        input_urls = ["http://example.com/list.m3u"]
        expanded = await utils.expand_playlist(input_urls)
        
        self.assertEqual(expanded, ["http://example.com/song1.mp3", "http://example.com/song2.mp3"])
        mock_fetch.assert_called_once_with("http://example.com/list.m3u")

    @patch('utils.audio_utils.is_audio_file')
    @async_test
    async def test_best_stream_url_direct_audio(self, mock_is_audio):
        mock_is_audio.return_value = True
        url = "http://example.com/song.mp3"
        result = await utils.best_stream_url(url)
        self.assertEqual(result, url)

if __name__ == '__main__':
    unittest.main()
