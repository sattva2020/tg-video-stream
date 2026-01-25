import os
import asyncio
import logging
import threading
from typing import List, Union
import requests

from pyrogram import Client
from pyrogram.errors import SessionExpired, SessionPasswordNeeded, AuthKeyInvalid, RPCError
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.exceptions import AlreadyJoinedError
    from pytgcalls.types import AudioVideoPiped, AudioPiped, HighQualityAudio, HighQualityVideo
    PYG_AVAILABLE = True
except Exception as e:
    # pytgcalls / tgcalls not available — run in degraded mode
    # Persist the full import error to a temporary file for debugging (visible to sysadmin).
    try:
        import traceback
        import pathlib
        p = pathlib.Path('/tmp/pytgcalls_import_error.log')
        with p.open('a', encoding='utf-8') as fh:
            fh.write('--- Import error at startup ---\n')
            fh.write(repr(e) + '\n')
            traceback.print_exc(file=fh)
    except Exception:
        # best-effort only
        pass
    PYG_AVAILABLE = False

from dotenv import load_dotenv
from utils import expand_playlist, build_ffmpeg_av_args, best_stream_url
import audio_utils
from metrics import MetricsCollector
from queue_manager import StreamQueue, QueueManager
from radio_handler import get_radio_handler, RadioStreamHandler
from redis_command_handler import RedisCommandHandler, ChannelConfig

# Rust transcoder client (optional - for health checks and future streaming)
try:
    from transcode_client import TranscodeClient
    RUST_TRANSCODER_AVAILABLE = True
except ImportError:
    RUST_TRANSCODER_AVAILABLE = False
    logging.getLogger("tg_video_streamer").info("transcode_client not available — using direct ffmpeg")

# Global queue manager instance
queue_manager: QueueManager = None

# Global Redis command handler instance
redis_command_handler: RedisCommandHandler = None

# Active channel streams (channel_id -> asyncio.Task)
active_streams: dict = {}

# Auto-End imports
try:
    from auto_end import AutoEndHandler
    AUTO_END_AVAILABLE = True
except ImportError:
    AUTO_END_AVAILABLE = False
    logging.getLogger("tg_video_streamer").warning("auto_end module not available — auto-end disabled")

# Prometheus imports
try:
    from prometheus_client import start_http_server, Counter
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.getLogger("tg_video_streamer").warning("prometheus_client not available — metrics will not be exported")

# AyuGram imports (optional - alternative streaming backend)
try:
    from ayugram_adapter import AyuGramAdapter
    AYUGRAM_AVAILABLE = True
except ImportError:
    AYUGRAM_AVAILABLE = False
    logging.getLogger("tg_video_streamer").info("ayugram_adapter not available — pyrogram/pytgcalls mode only")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("tg_video_streamer")

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
# SESSION_STRING is legacy/optional. Authorization is now primarily handled via GUI/Redis commands.
SESSION_STRING = os.getenv("SESSION_STRING", "")
CHAT_ID: Union[int, str] = os.getenv("CHAT_ID", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
VIDEO_QUALITY = os.getenv("VIDEO_QUALITY", "720p")
LOOP = os.getenv("LOOP", "1") == "1"
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
AUTO_END_TIMEOUT_MINUTES = int(os.getenv("AUTO_END_TIMEOUT_MINUTES", "5"))
AUTO_END_ENABLED = os.getenv("AUTO_END_ENABLED", "1") == "1"
# USE_AYUGRAM: Select implementation - 'pytg' (default) or 'ayugram'
USE_AYUGRAM = os.getenv("USE_AYUGRAM", "pytg")

# Global auto-end handler instance
auto_end_handler = None


def _get_backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")


def _get_redis_url() -> str:
    redis_host = os.getenv("REDIS_HOST")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    if redis_host:
        return f"redis://{redis_host}:{redis_port}/{redis_db}"
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis_url
    return f"redis://redis:{redis_port}/{redis_db}"


def _report_streamer_status(item_id: Union[str, None], status: str, duration: Union[int, None] = None):
    if not item_id:
        return
    token = os.getenv("STREAMER_STATUS_TOKEN")
    if not token:
        log.debug("STREAMER_STATUS_TOKEN missing; skipping status update for %s", item_id)
        return
    payload = {"status": status}
    if duration is not None:
        payload["duration"] = duration
    headers = {"X-Streamer-Token": token}
    try:
        response = requests.patch(
            f"{_get_backend_url()}/api/playlist/{item_id}/status",
            json=payload,
            headers=headers,
            timeout=5
        )
        if response.status_code != 200:
            log.warning("Streamer status update failed for %s: %s", item_id, response.text.strip())
    except requests.RequestException as exc:
        log.warning("Unable to report status %s for %s: %s", status, item_id, exc)

# Initialize Prometheus metrics if available
streams_played_total = None
if PROMETHEUS_AVAILABLE:
    streams_played_total = Counter('streams_played_total', 'Total number of streams played')
    try:
        start_http_server(PROMETHEUS_PORT)
        log.info("Prometheus metrics server started on port %d", PROMETHEUS_PORT)
    except Exception as e:
        log.warning("Failed to start Prometheus server: %s", e)
else:
    log.info("Prometheus not available — skipping metrics initialization")

# Initialize Rust transcoder client (optional)
transcode_client = None
if RUST_TRANSCODER_AVAILABLE:
    try:
        transcode_client = TranscodeClient()
        log.info("Rust transcoder client initialized (url: %s)", transcode_client.base_url)
    except Exception as e:
        log.warning("Failed to initialize Rust transcoder client: %s — using direct ffmpeg", e)
        transcode_client = None
else:
    log.info("Rust transcoder not configured — using direct ffmpeg for transcoding")

RUN_APP = True
INTERACTIVE_AUTH = False
if not (API_ID and API_HASH and CHAT_ID):
    logging.getLogger("tg_video_streamer").warning(
        "Missing critical API credentials (API_ID, API_HASH, or CHAT_ID) in .env — running in degraded mode"
    )
    RUN_APP = False
elif not SESSION_STRING:
    # SESSION_STRING is missing — log info but continue to allow lazy initialization via Redis commands
    logging.getLogger("tg_video_streamer").info(
        "SESSION_STRING not provided in .env — starting in idle mode. "
        "Client will be initialized when a start command with session_string is received."
    )
    # RUN_APP = True is default

app = Client(
    name="tg_streamer",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True,
    workdir="./tdlib"
) if SESSION_STRING else None

# Initialize streaming backend (AyuGram or PyTgCalls)
pytg = None
ayugram = None

if USE_AYUGRAM == "1" or USE_AYUGRAM == "ayugram":
    # Use AyuGram adapter
    if AYUGRAM_AVAILABLE and app:
        try:
            ayugram = AyuGramAdapter(app)
            log.info("AyuGram adapter initialized (USE_AYUGRAM=%s)", USE_AYUGRAM)
        except Exception as e:
            log.warning("AyuGram adapter initialization failed: %s", e)
            ayugram = None
    elif not AYUGRAM_AVAILABLE:
        log.warning("AyuGram requested (USE_AYUGRAM=%s) but not available — falling back to PyTgCalls", USE_AYUGRAM)
        # Fall through to PyTgCalls initialization below
        if PYG_AVAILABLE and app:
            try:
                pytg = PyTgCalls(app)
            except Exception as e:
                log.warning("pytgcalls initialization failed: %s", e)
                pytg = None
        elif not PYG_AVAILABLE:
            log.warning("pytgcalls not available — running in degraded mode (no voice/video).")
elif not SESSION_STRING:
    # No session string yet - skip initialization
    pass
else:
    # Use PyTgCalls (default)
    if PYG_AVAILABLE and app:
        try:
            pytg = PyTgCalls(app)
        except Exception as e:
            log.warning("pytgcalls initialization failed: %s", e)
            pytg = None
    elif not PYG_AVAILABLE:
        log.warning("pytgcalls not available — running in degraded mode (no voice/video).")

async def ensure_join(chat: Union[int, str]):
    if not pytg:
        log.info("ensure_join: pytgcalls not available, skipping join test")
        return
    try:
        await pytg.join_group_call(
            chat,
            AudioVideoPiped(
                "anullsrc=r=48000:cl=stereo",
                audio_parameters=HighQualityAudio(),
                video_parameters=HighQualityVideo()
            ),
            stream_type=0
        )
        await pytg.leave_group_call(chat)
    except AlreadyJoinedError:
        await pytg.leave_group_call(chat)
    except Exception as e:
        log.info("join test: %s", e)

async def play_sequence(items: List[dict]):
    global queue_manager

    v_args, a_args = build_ffmpeg_av_args(VIDEO_QUALITY)
    log.info("Playlist contains %d items", len(items))

    # Determine which streaming backend to use
    streaming_backend = None
    backend_name = None

    if ayugram:
        streaming_backend = ayugram
        backend_name = "AyuGram"
        log.info("Using AyuGram backend for streaming")
    elif pytg:
        streaming_backend = pytg
        backend_name = "PyTgCalls"
        log.info("Using PyTgCalls backend for streaming")
    else:
        log.warning("No streaming backend available (pytgcalls and AyuGram unavailable) — entering degraded idle loop")
        await asyncio.sleep(60)
        return

    # Use QueueManager for Redis sync
    chat_id = int(CHAT_ID) if isinstance(CHAT_ID, str) and CHAT_ID.isdigit() else CHAT_ID
    if queue_manager is None:
        queue_manager = QueueManager()
        redis_url = _get_redis_url()
        await queue_manager.init(redis_url)

    queue = await queue_manager.get_queue(chat_id)
    await queue.add_items(items)

    try:
        while True:
            # Check if we are done
            if queue.empty() and queue.queue.empty():
                break

            # Get next item (waits if queue is empty but buffering is active)
            # We need a timeout or check if buffering is done and queue is empty
            try:
                # Wait for next item with a timeout to allow checking for empty state
                prepared_item = await asyncio.wait_for(queue.get_next(), timeout=5.0)
            except asyncio.TimeoutError:
                if not queue.is_running or (not queue.playlist_items and queue.queue.empty()):
                    break
                continue

            track_id = prepared_item["track_id"]
            direct = prepared_item["direct_url"]
            link = prepared_item["link"]
            original_item = prepared_item["original_item"]
            profile = prepared_item["profile"]
            is_audio = prepared_item["is_audio"]

            try:
                log.info("▶️ Playing: %s", link)
                if streams_played_total:
                    streams_played_total.inc()

                _report_streamer_status(track_id, "playing", duration=original_item.get("duration"))

                # Create stream based on backend type
                if backend_name == "AyuGram":
                    # AyuGram backend uses MediaStream from adapter
                    from ayugram_adapter import MediaStream, AudioQuality, VideoQuality

                    if is_audio:
                        log.info("Detected audio-only source for AyuGram")

                        if profile:
                            log.info("Transcoding required (%s): %s", profile.get('description'), direct)

                            # Log Rust transcoder status (future: use for actual transcoding)
                            if transcode_client is not None:
                                is_healthy = await transcode_client.health_check()
                                if is_healthy:
                                    log.info("Rust transcoder available — will use for transcoding")
                                else:
                                    log.warning("Rust transcoder unavailable — using direct ffmpeg fallback")

                            # TODO: Map FFmpeg args to AyuGram MediaStream format
                            # For now, pass URL directly
                            stream = MediaStream(
                                url_or_path=direct,
                                audio_parameters=AudioQuality.HIGH,
                                ffmpeg_parameters=" ".join(['-re', *profile.get('ffmpeg_args', [])])
                            )
                        else:
                            log.info("No transcoding profile matched, using direct MediaStream")
                            stream = MediaStream(
                                url_or_path=direct,
                                audio_parameters=AudioQuality.HIGH
                            )
                    else:
                        # Video stream
                        video_quality_map = {
                            "480p": VideoQuality.SD_480p,
                            "720p": VideoQuality.HD_720p,
                            "1080p": VideoQuality.FHD_1080p,
                            "2k": VideoQuality.QHD_2K,
                            "4k": VideoQuality.UHD_4K,
                        }
                        vq = video_quality_map.get(VIDEO_QUALITY, VideoQuality.HD_720p)

                        stream = MediaStream(
                            url_or_path=direct,
                            audio_parameters=AudioQuality.HIGH,
                            video_parameters=vq,
                            ffmpeg_parameters=" ".join(['-re', *v_args, *a_args])
                        )

                    # Join call with AyuGram
                    await streaming_backend.join_group_call(chat_id, stream)

                else:
                    # PyTgCalls backend (original implementation)
                    if is_audio:
                        log.info("Detected audio-only source")

                        if profile:
                            log.info("Transcoding required (%s): %s", profile.get('description'), direct)

                            # Log Rust transcoder status (future: use for actual transcoding)
                            if transcode_client is not None:
                                is_healthy = await transcode_client.health_check()
                                if is_healthy:
                                    log.info("Rust transcoder available — will use for transcoding")
                                else:
                                    log.warning("Rust transcoder unavailable — using direct ffmpeg fallback")

                            add_args = ['-re', *profile.get('ffmpeg_args', [])]
                            try:
                                stream = AudioPiped(
                                    direct,
                                    audio_parameters=HighQualityAudio(),
                                    additional_ffmpeg_parameters=add_args
                                )
                            except Exception as e:
                                log.exception("Transcoding initialization failed for %s: %s", direct, e)
                                await asyncio.sleep(1)
                                continue
                        else:
                            log.info("No transcoding profile matched, using direct AudioPiped")
                            stream = AudioPiped(
                                direct,
                                audio_parameters=HighQualityAudio()
                            )
                    else:
                        stream = AudioVideoPiped(
                            direct,
                            video_parameters=HighQualityVideo(),
                            audio_parameters=HighQualityAudio(),
                            additional_ffmpeg_parameters=[
                                "-re",
                                *v_args,
                                *a_args
                            ]
                        )

                    # Join call with PyTgCalls
                    await streaming_backend.join_group_call(chat_id, stream)

                # Monitor playback
                # We check every 5 seconds. Max duration 2 hours (1440 * 5s = 7200s).
                for _ in range(1440):
                    await asyncio.sleep(5)
                    # Check if call is still active using backend-specific method
                    if backend_name == "AyuGram":
                        call_info = await streaming_backend.get_call(chat_id)
                        if call_info is None:
                            break
                    else:
                        if streaming_backend.get_call(chat_id) is None:
                            break

                # Leave call using backend-specific method
                if backend_name == "AyuGram":
                    await streaming_backend.leave_call(chat_id)
                else:
                    await streaming_backend.leave_group_call(chat_id)

                # Notify track ended
                await queue.on_track_end(track_id, reason="completed")

                _report_streamer_status(track_id, "queued")

            except Exception as e:
                log.exception("Stream error while playing %s: %s", link, e)

                # Notify track ended with error
                await queue.on_track_end(track_id, reason="error")

                _report_streamer_status(track_id, "error")
                try:
                    # Leave call using backend-specific method
                    if backend_name == "AyuGram":
                        await streaming_backend.leave_call(chat_id)
                    else:
                        await streaming_backend.leave_group_call(chat_id)
                except Exception:
                    pass
                await asyncio.sleep(5)
    finally:
        await queue.stop()
        # Close Redis connection
        await queue.close_redis()


# ============================================================================
# Redis Command Callbacks for multi-channel control
# ============================================================================

async def handle_channel_start(config: ChannelConfig) -> bool:
    """
    Handle start command from backend.
    Creates a new streaming task for the specified channel.
    """
    global active_streams, app, pytg, ayugram

    channel_id = config.channel_id
    log.info("Starting stream for channel %s (%s)", channel_id, config.name)

    # Check if already running
    if channel_id in active_streams and not active_streams[channel_id].done():
        log.warning("Channel %s already has an active stream", channel_id)
        return True

    # Determine which backend to use
    streaming_backend = None
    backend_name = None

    if ayugram:
        streaming_backend = ayugram
        backend_name = "AyuGram"
        log.info("Using AyuGram backend for channel %s", channel_id)
    elif pytg:
        streaming_backend = pytg
        backend_name = "PyTgCalls"
        log.info("Using PyTgCalls backend for channel %s", channel_id)
    else:
        # No backend available - try to initialize one
        if config.session_string:
            log.info("Initializing global Telegram client from command...")
            try:
                app = Client(
                    name="tg_streamer",
                    api_id=config.api_id or API_ID,
                    api_hash=config.api_hash or API_HASH,
                    session_string=config.session_string,
                    in_memory=True,
                    workdir="./tdlib"
                )
                await app.start()

                # Initialize backend based on USE_AYUGRAM setting
                if USE_AYUGRAM == "1" or USE_AYUGRAM == "ayugram":
                    if AYUGRAM_AVAILABLE:
                        ayugram = AyuGramAdapter(app)
                        streaming_backend = ayugram
                        backend_name = "AyuGram"
                        log.info("AyuGram adapter initialized successfully")
                    else:
                        log.warning("AyuGram requested but not available — falling back to PyTgCalls")
                        if PYG_AVAILABLE:
                            pytg = PyTgCalls(app)
                            await pytg.start()
                            streaming_backend = pytg
                            backend_name = "PyTgCalls"
                            log.info("PyTgCalls initialized successfully")
                        else:
                            log.error("Neither AyuGram nor PyTgCalls available")
                            return False
                else:
                    # Use PyTgCalls (default)
                    if PYG_AVAILABLE:
                        pytg = PyTgCalls(app)
                        await pytg.start()
                        streaming_backend = pytg
                        backend_name = "PyTgCalls"
                        log.info("PyTgCalls initialized successfully")
                    else:
                        log.error("pytgcalls library not available")
                        return False
            except Exception as e:
                log.exception("Failed to initialize client from command: %s", e)
                return False
        else:
            log.error("No streaming backend available and no session_string provided - cannot start stream")
            return False
    
    try:
        # Use the chat_id from config
        chat_id = config.chat_id
        if not chat_id:
            log.error("No chat_id in config for channel %s", channel_id)
            return False

        # Create streaming task
        async def stream_channel():
            try:
                # Get playlist from backend
                playlist = []
                try:
                    resp = requests.get(
                        f"{_get_backend_url()}/api/playlist/stream?channel_id={channel_id}",
                        timeout=10
                    )
                    if resp.status_code == 200:
                        playlist = resp.json()
                except Exception as e:
                    log.error("Failed to get playlist for channel %s: %s", channel_id, e)
                    return

                if not playlist:
                    log.warning("No playlist items for channel %s", channel_id)
                    return

                # Start playing
                for item in playlist:
                    if channel_id not in active_streams:
                        log.info("Stream cancelled for channel %s", channel_id)
                        break

                    url = item.get("url")
                    if not url:
                        continue

                    try:
                        stream_url = best_stream_url(url, config.video_quality or "720p")
                        if not stream_url:
                            continue

                        # Create stream based on backend type
                        if backend_name == "AyuGram":
                            # AyuGram backend
                            from ayugram_adapter import MediaStream, AudioQuality, VideoQuality

                            video_quality_map = {
                                "480p": VideoQuality.SD_480p,
                                "720p": VideoQuality.HD_720p,
                                "1080p": VideoQuality.FHD_1080p,
                                "2k": VideoQuality.QHD_2K,
                                "4k": VideoQuality.UHD_4K,
                            }
                            vq = video_quality_map.get(config.video_quality or "720p", VideoQuality.HD_720p)

                            stream = MediaStream(
                                url_or_path=stream_url,
                                audio_parameters=AudioQuality.HIGH,
                                video_parameters=vq
                            )
                        else:
                            # PyTgCalls backend
                            v_args, a_args = build_ffmpeg_av_args(config.video_quality or "720p")
                            stream = AudioVideoPiped(stream_url, HighQualityVideo(), HighQualityAudio())

                        # Join call using backend-specific method
                        if backend_name == "AyuGram":
                            await streaming_backend.join_group_call(chat_id, stream)
                        else:
                            await streaming_backend.join_group_call(chat_id, stream)

                        # Monitor playback
                        for _ in range(1440):
                            await asyncio.sleep(5)
                            # Check if call is still active using backend-specific method
                            if backend_name == "AyuGram":
                                call_info = await streaming_backend.get_call(chat_id)
                                if call_info is None:
                                    break
                            else:
                                if streaming_backend.get_call(chat_id) is None:
                                    break
                            if channel_id not in active_streams:
                                break

                        # Leave call using backend-specific method
                        if backend_name == "AyuGram":
                            await streaming_backend.leave_call(chat_id)
                        else:
                            await streaming_backend.leave_group_call(chat_id)

                    except Exception as e:
                        log.exception("Error playing item for channel %s: %s", channel_id, e)
                        try:
                            # Leave call using backend-specific method
                            if backend_name == "AyuGram":
                                await streaming_backend.leave_call(chat_id)
                            else:
                                await streaming_backend.leave_group_call(chat_id)
                        except Exception:
                            pass
                        await asyncio.sleep(5)

            except Exception as e:
                log.exception("Stream error for channel %s: %s", channel_id, e)
            finally:
                # Clean up
                if channel_id in active_streams:
                    del active_streams[channel_id]
                log.info("Stream ended for channel %s", channel_id)
        
        # Start the streaming task
        task = asyncio.create_task(stream_channel())
        active_streams[channel_id] = task
        
        return True
        
    except Exception as e:
        log.exception(f"Failed to start channel {channel_id}: {e}")
        return False


async def handle_channel_stop(channel_id: str) -> bool:
    """
    Handle stop command from backend.
    Cancels the streaming task for the specified channel.
    """
    global active_streams
    
    log.info(f"Stopping stream for channel {channel_id}")
    
    if channel_id not in active_streams:
        log.warning(f"Channel {channel_id} not in active streams")
        return True  # Already stopped
    
    task = active_streams.pop(channel_id, None)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Try to leave group call
    if pytg:
        try:
            # We need to know which chat_id to leave
            # For now, assume CHAT_ID (legacy single-channel mode)
            await pytg.leave_group_call(CHAT_ID)
        except Exception:
            pass
    
    log.info(f"Stream stopped for channel {channel_id}")
    return True


async def handle_playlist_update(channel_id: str):
    """Handle playlist update notification."""
    log.info(f"Playlist update notification for channel {channel_id}")
    # The stream will automatically pick up new items on next iteration
    # For immediate update, we could restart the stream


async def main():
    global redis_command_handler
    
    # Start Redis command handler immediately to ensure we can receive commands
    # even if the main app fails to start or is in degraded mode.
    redis_command_handler = RedisCommandHandler()
    redis_command_handler.on_start = handle_channel_start
    redis_command_handler.on_stop = handle_channel_stop
    redis_command_handler.on_update_playlist = handle_playlist_update
    try:
        await redis_command_handler.start()
        log.info("Redis command handler started")
    except Exception as e:
        log.error("Failed to start Redis command handler: %s", e)

    if not RUN_APP:
        log.info("Starting in degraded idle mode (missing critical credentials).")
        try:
            while True:
                await asyncio.sleep(60)
        finally:
            if redis_command_handler:
                await redis_command_handler.stop()
        return

    if not app:
        log.info("No global session configured. Waiting for commands via Redis.")
        try:
            while True:
                await asyncio.sleep(60)
        finally:
            if redis_command_handler:
                await redis_command_handler.stop()
        return

    # Try to start the Client and detect invalid/expired sessions early.
    try:
        async with app:
            if pytg:
                await pytg.start()

            try:
                me = await app.get_me()
            except (SessionExpired, AuthKeyInvalid) as e:
                log.exception("Telegram session invalid or expired: %s", e)
                # Continue in idle mode
                while True:
                    await asyncio.sleep(60)
                return

            except SessionPasswordNeeded:
                log.exception("Two-factor auth (password) is required for this account. Cannot continue.")
                # Enter degraded mode
                while True:
                    await asyncio.sleep(60)
                return

            log.info("Logged in as: %s", me.id)
            await ensure_join(CHAT_ID)
            
            # Initialize auto-end handler if available
            global auto_end_handler
            if AUTO_END_AVAILABLE and AUTO_END_ENABLED and pytg:
                try:
                    auto_end_handler = AutoEndHandler(
                        pytgcalls=pytg,
                        chat_id=CHAT_ID,
                        timeout_minutes=AUTO_END_TIMEOUT_MINUTES
                    )
                    await auto_end_handler.start()
                    log.info("Auto-end handler started with %d min timeout", AUTO_END_TIMEOUT_MINUTES)
                except Exception as e:
                    log.warning("Failed to start auto-end handler: %s", e)
                    auto_end_handler = None
            else:
                log.info("Auto-end disabled or not available")
            
            while True:
                params = {}
                if CHANNEL_ID:
                    params['channel_id'] = CHANNEL_ID
                try:
                    resp = requests.get(f"{_get_backend_url()}/api/playlist/", params=params)
                    if resp.status_code == 200:
                        playlist = resp.json()
                        log.info("Fetched %d items from API", len(playlist))
                    else:
                        log.error("Failed to fetch playlist from API: %s", resp.status_code)
                        playlist = []
                except Exception as e:
                    log.error("Error connecting to backend API: %s", e)
                    if os.path.exists("playlist.txt"):
                        log.info("Falling back to playlist.txt")
                        with open("playlist.txt", "r", encoding="utf-8") as f:
                            playlist = [
                                {"url": line.strip()} for line in f
                                if line.strip() and not line.strip().startswith("#")
                            ]
                    else:
                        playlist = []

                if not playlist:
                    log.warning("No URLs found in API or playlist.txt. Waiting...")
                    await asyncio.sleep(60)
                    continue
                await play_sequence(playlist)
                
                if not LOOP:
                    break
            
            # Stop auto-end handler on exit
            if auto_end_handler:
                try:
                    await auto_end_handler.stop()
                    log.info("Auto-end handler stopped")
                except Exception as e:
                    log.warning("Error stopping auto-end handler: %s", e)
            
            # Stop Redis command handler
            if redis_command_handler:
                try:
                    await redis_command_handler.stop()
                    log.info("Redis command handler stopped")
                except Exception as e:
                    log.warning("Error stopping Redis command handler: %s", e)
            
            # Close queue manager
            if queue_manager:
                try:
                    await queue_manager.close_all()
                    log.info("Queue manager closed")
                except Exception as e:
                    log.warning("Error closing queue manager: %s", e)

    except RPCError as e:
        log.exception("Telegram RPC error during startup: %s", e)
        log.error("Entering degraded mode. Check your API_ID/API_HASH/SESSION_STRING or network connectivity.")
        while True:
            await asyncio.sleep(60)
    except Exception as e:
        log.exception("Unhandled error during startup: %s", e)
        # If something unexpected happened, enter degraded mode to keep service alive
        while True:
            await asyncio.sleep(60)

if __name__ == "__main__":
    # Start metrics collector in a background thread
    try:
        REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
        REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
        collector = MetricsCollector(redis_host=REDIS_HOST, redis_port=REDIS_PORT)
        metrics_thread = threading.Thread(target=collector.run_loop, daemon=True)
        metrics_thread.start()
        log.info("Metrics collector started")
    except Exception as e:
        log.error(f"Failed to start metrics collector: {e}")

    asyncio.run(main())
