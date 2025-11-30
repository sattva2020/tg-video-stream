import asyncio
import logging
from typing import List, Optional, Dict, Any
from collections import deque
try:
    from streamer.utils import expand_playlist, best_stream_url
    from streamer import audio_utils
except ImportError:
    from utils import expand_playlist, best_stream_url
    import audio_utils

log = logging.getLogger("tg_video_streamer")

class StreamQueue:
    def __init__(self, max_buffer_size: int = 3):
        self.queue = asyncio.Queue(maxsize=max_buffer_size)
        self.playlist_items = deque()
        self.current_item: Optional[Dict[str, Any]] = None
        self.is_running = False
        self.buffer_task: Optional[asyncio.Task] = None

    def add_items(self, items: List[Dict[str, Any]]):
        """Adds items to the internal playlist to be processed."""
        for item in items:
            self.playlist_items.append(item)
        
        if not self.is_running:
            self.start_buffering()

    def start_buffering(self):
        """Starts the background buffering task."""
        if self.is_running:
            return
        self.is_running = True
        self.buffer_task = asyncio.create_task(self._buffer_loop())
        log.info("StreamQueue buffering started")

    async def stop(self):
        """Stops the buffering task."""
        self.is_running = False
        if self.buffer_task:
            self.buffer_task.cancel()
            try:
                await self.buffer_task
            except asyncio.CancelledError:
                pass
        log.info("StreamQueue buffering stopped")

    async def _buffer_loop(self):
        """Background loop that prepares items and puts them into the async queue."""
        while self.is_running:
            if not self.playlist_items:
                # No more items to process, wait a bit
                await asyncio.sleep(1)
                continue

            if self.queue.full():
                await asyncio.sleep(1)
                continue

            item = self.playlist_items.popleft()
            track_url = item.get("url")
            track_id = item.get("id")

            if not track_url:
                log.warning("Skipping playlist entry without URL: %s", item)
                continue

            try:
                log.debug(f"Buffering item: {track_url}")
                expanded = await expand_playlist([track_url])
                
                if not expanded:
                    log.warning("Playlist item produced no playable URLs: %s", track_url)
                    continue

                for link in expanded:
                    # Resolve the direct link
                    direct = await best_stream_url(link)
                    
                    # Detect content type if audio
                    content_type = None
                    profile = None
                    
                    if audio_utils.is_audio_file(direct):
                        try:
                            content_type = await audio_utils.detect_content_type(direct)
                        except Exception:
                            pass
                        profile = audio_utils.get_transcoding_profile(direct, content_type=content_type)

                    prepared_item = {
                        "original_item": item,
                        "direct_url": direct,
                        "link": link,
                        "is_audio": audio_utils.is_audio_file(direct),
                        "profile": profile,
                        "track_id": track_id
                    }
                    
                    await self.queue.put(prepared_item)
                    log.info(f"Buffered item: {link}")

            except Exception as e:
                log.error(f"Error buffering item {track_url}: {e}")
                await asyncio.sleep(1)

    async def get_next(self):
        """Retrieves the next prepared item from the queue."""
        return await self.queue.get()

    def empty(self):
        return self.queue.empty() and not self.playlist_items
