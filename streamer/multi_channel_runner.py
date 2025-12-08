"""
Multi-channel Stream Runner with Redis Control.

This module integrates:
- Redis command handler for receiving backend commands
- Multi-channel manager for running concurrent streams
- Pyrogram/PyTgCalls for Telegram streaming

Usage:
    python multi_channel_runner.py

Environment variables:
    API_ID, API_HASH: Telegram API credentials
    REDIS_HOST, REDIS_PORT: Redis connection
    BACKEND_URL: Backend API URL for playlist fetching
"""

import asyncio
import logging
import os
import signal
from typing import Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("multi_channel_runner")

# Import Telegram clients
try:
    from pyrogram import Client
    from pyrogram.errors import SessionExpired, AuthKeyInvalid
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    log.warning("pyrogram not available")

try:
    from pytgcalls import PyTgCalls
    from pytgcalls.types import MediaStream, AudioQuality, VideoQuality
    PYTGCALLS_AVAILABLE = True
except ImportError:
    PYTGCALLS_AVAILABLE = False
    log.warning("pytgcalls not available")

# Import our modules
from redis_command_handler import RedisCommandHandler, ChannelConfig
from multi_channel import MultiChannelManager

# Global state
running_channels: Dict[str, Dict[str, Any]] = {}  # channel_id -> {client, pytg, task}
manager: Optional[MultiChannelManager] = None
command_handler: Optional[RedisCommandHandler] = None


def get_redis_url() -> str:
    """Build Redis URL from environment."""
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", "0")
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis_url
    return f"redis://{redis_host}:{redis_port}/{redis_db}"


async def start_channel_stream(config: ChannelConfig) -> bool:
    """
    Start streaming for a channel.
    
    Creates Pyrogram client with channel's session and starts PyTgCalls.
    """
    global running_channels
    
    channel_id = config.channel_id
    log.info(f"Starting stream for channel {channel_id} ({config.name})")
    
    # Check if already running
    if channel_id in running_channels:
        log.warning(f"Channel {channel_id} already running, stopping first")
        await stop_channel_stream(channel_id)
    
    if not config.session_string:
        log.error(f"No session string for channel {channel_id}")
        return False
    
    if not PYROGRAM_AVAILABLE or not PYTGCALLS_AVAILABLE:
        log.error("Pyrogram or PyTgCalls not available")
        return False
    
    try:
        # Create Pyrogram client with channel's session
        client = Client(
            name=f"channel_{channel_id}",
            api_id=config.api_id,
            api_hash=config.api_hash,
            session_string=config.session_string,
            in_memory=True
        )
        
        # Start client
        await client.start()
        me = await client.get_me()
        log.info(f"Channel {channel_id}: Logged in as {me.id}")
        
        # Resolve chat to get proper peer (required by PyTgCalls)
        # Try username first (more reliable for peer resolution), then fallback to chat_id
        resolved_chat_id = None
        chat_target = f"@{config.chat_username}" if config.chat_username else config.chat_id
        
        try:
            chat = await client.get_chat(chat_target)
            resolved_chat_id = chat.id
            log.info(f"Channel {channel_id}: Resolved chat '{chat.title}' (id: {resolved_chat_id})")
        except Exception as e:
            log.warning(f"Channel {channel_id}: Failed to resolve chat {chat_target}: {e}")
            # If username failed and we have a different chat_id, try that
            if config.chat_username and config.chat_id:
                try:
                    chat = await client.get_chat(config.chat_id)
                    resolved_chat_id = chat.id
                    log.info(f"Channel {channel_id}: Resolved chat by ID '{chat.title}' (id: {resolved_chat_id})")
                except Exception as e2:
                    log.error(f"Channel {channel_id}: Failed to resolve chat by ID {config.chat_id}: {e2}")
        
        if not resolved_chat_id:
            log.error(f"Channel {channel_id}: Could not resolve chat, aborting")
            await client.stop()
            return False
        
        # Create PyTgCalls instance
        pytg = PyTgCalls(client)
        await pytg.start()
        
        # Store channel state with resolved chat_id
        running_channels[channel_id] = {
            "client": client,
            "pytg": pytg,
            "config": config,
            "chat_id": resolved_chat_id
        }
        
        # Start playback loop in background
        task = asyncio.create_task(
            channel_playback_loop(channel_id, config)
        )
        running_channels[channel_id]["task"] = task
        
        log.info(f"Channel {channel_id} started successfully")
        return True
        
    except (SessionExpired, AuthKeyInvalid) as e:
        log.error(f"Invalid session for channel {channel_id}: {e}")
        return False
    except Exception as e:
        log.exception(f"Failed to start channel {channel_id}: {e}")
        return False


async def stop_channel_stream(channel_id: str) -> bool:
    """Stop streaming for a channel."""
    global running_channels
    
    if channel_id not in running_channels:
        log.warning(f"Channel {channel_id} not running")
        return True
    
    log.info(f"Stopping stream for channel {channel_id}")
    
    try:
        channel_data = running_channels[channel_id]
        
        # Cancel playback task
        if "task" in channel_data:
            channel_data["task"].cancel()
            try:
                await channel_data["task"]
            except asyncio.CancelledError:
                pass
        
        # Leave call
        pytg = channel_data.get("pytg")
        chat_id = channel_data.get("chat_id")
        if pytg and chat_id:
            try:
                await pytg.leave_call(chat_id)
            except Exception as e:
                log.debug(f"Leave call error (ok): {e}")
        
        # Stop PyTgCalls
        if pytg:
            try:
                await pytg.stop()
            except Exception:
                pass
        
        # Stop Pyrogram client
        client = channel_data.get("client")
        if client:
            try:
                await client.stop()
            except Exception:
                pass
        
        # Remove from running channels
        del running_channels[channel_id]
        
        log.info(f"Channel {channel_id} stopped")
        return True
        
    except Exception as e:
        log.exception(f"Error stopping channel {channel_id}: {e}")
        return False


async def channel_playback_loop(channel_id: str, config: ChannelConfig):
    """
    Main playback loop for a channel.
    
    Fetches playlist from backend and plays items.
    """
    import requests
    from utils import expand_playlist, build_ffmpeg_av_args, best_stream_url
    
    backend_url = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")
    
    log.info(f"Starting playback loop for channel {channel_id}")
    
    channel_data = running_channels.get(channel_id)
    if not channel_data:
        log.error(f"Channel {channel_id} data not found")
        return
    
    pytg = channel_data["pytg"]
    chat_id = channel_data["chat_id"]  # Use resolved chat_id from start_channel_stream
    
    v_args, a_args = build_ffmpeg_av_args(config.video_quality)
    
    try:
        while channel_id in running_channels:
            # Fetch playlist from backend (new unified playlist API)
            playlist = []
            playlist_name = None
            is_shuffled = False
            
            try:
                # Try new unified playlist API first
                resp = requests.get(
                    f"{backend_url}/api/schedule/playlists/channel/{channel_id}/active",
                    timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    playlist = data.get("items", [])
                    playlist_name = data.get("playlist_name")
                    is_shuffled = data.get("is_shuffled", False)
                    source = data.get("source", "unknown")
                    log.info(f"Channel {channel_id}: Fetched {len(playlist)} items from {source}" + 
                             (f" ({playlist_name})" if playlist_name else ""))
                else:
                    log.warning(f"Channel {channel_id}: Playlist fetch failed: {resp.status_code}")
            except Exception as e:
                log.error(f"Channel {channel_id}: Error fetching playlist: {e}")
            
            if not playlist:
                log.info(f"Channel {channel_id}: No items, waiting...")
                # Heartbeat: refresh running status while waiting
                if command_handler:
                    await command_handler.update_status(channel_id, "running")
                await asyncio.sleep(60)
                continue
            
            # Shuffle if enabled
            if is_shuffled:
                import random
                playlist = playlist.copy()
                random.shuffle(playlist)
                log.info(f"Channel {channel_id}: Shuffled playlist")
            
            # Play each item
            for item in playlist:
                if channel_id not in running_channels:
                    break
                    
                link = item.get("url", "")
                if not link:
                    continue
                
                try:
                    # Expand playlists and get stream URL
                    expanded = await expand_playlist([link])
                    if not expanded:
                        continue
                    
                    stream_url = await best_stream_url(expanded[0])
                    log.info(f"Channel {channel_id}: Playing {stream_url[:50]}...")
                    
                    # Update status
                    if command_handler:
                        await command_handler.update_status(
                            channel_id,
                            "playing",
                            current_item=item.get("title", stream_url[:50])
                        )
                    
                    # Join group call and stream
                    try:
                        await pytg.play(
                            chat_id,
                            MediaStream(
                                stream_url,
                                audio_parameters=AudioQuality.STUDIO,
                                video_parameters=VideoQuality.FHD_1080p
                            )
                        )
                    except Exception as e:
                        log.error(f"Channel {channel_id}: Join call failed: {e}")
                        await asyncio.sleep(5)
                        continue
                    
                    # Wait for playback (with periodic checks)
                    duration = item.get("duration", 300)  # default 5 min
                    elapsed = 0
                    while elapsed < duration and channel_id in running_channels:
                        await asyncio.sleep(5)
                        elapsed += 5
                        
                        # Check if still in call (handle both sync and async calls property)
                        try:
                            calls = pytg.calls
                            if asyncio.iscoroutine(calls):
                                calls = await calls
                            if chat_id not in calls:
                                break
                        except Exception:
                            break
                    
                    # Leave call before next track
                    try:
                        await pytg.leave_call(chat_id)
                    except Exception:
                        pass
                    
                except Exception as e:
                    log.exception(f"Channel {channel_id}: Stream error: {e}")
                    await asyncio.sleep(5)
            
            # Loop completed, wait before restart
            await asyncio.sleep(5)
            
    except asyncio.CancelledError:
        log.info(f"Channel {channel_id}: Playback loop cancelled")
    except Exception as e:
        log.exception(f"Channel {channel_id}: Playback loop error: {e}")
    finally:
        # Update status to stopped
        if command_handler:
            await command_handler.update_status(channel_id, "stopped")


async def main():
    """Main entry point."""
    global manager, command_handler
    
    log.info("Starting Multi-Channel Stream Runner")
    
    # Initialize command handler
    redis_url = get_redis_url()
    command_handler = RedisCommandHandler(redis_url)
    
    # Register callbacks
    command_handler.on_start = start_channel_stream
    command_handler.on_stop = stop_channel_stream
    
    # Start command handler
    await command_handler.start()
    log.info("Redis command handler started, waiting for commands...")
    
    # Setup graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        log.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for shutdown
    try:
        await shutdown_event.wait()
    except asyncio.CancelledError:
        pass
    
    # Cleanup
    log.info("Shutting down...")
    
    # Stop all channels
    for channel_id in list(running_channels.keys()):
        await stop_channel_stream(channel_id)
    
    # Stop command handler
    if command_handler:
        await command_handler.stop()
    
    log.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
