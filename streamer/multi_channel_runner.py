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
from pyrogram.errors import FloodWait

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
    from pytgcalls import filters as fl
    from pytgcalls.types import (
        MediaStream, AudioQuality, VideoQuality, StreamEnded,
        ChatUpdate, GroupCallParticipant, UpdatedGroupCallParticipant
    )
    PYTGCALLS_AVAILABLE = True
except ImportError:
    PYTGCALLS_AVAILABLE = False
    log.warning("pytgcalls not available")

# Import our modules
from redis_command_handler import RedisCommandHandler, ChannelConfig
from multi_channel import MultiChannelManager

# Global state
running_channels: Dict[str, Dict[str, Any]] = {}  # channel_id -> {client, pytg, task}
stream_ended_events: Dict[int, asyncio.Event] = {}  # chat_id -> Event (signals stream ended)
manager: Optional[MultiChannelManager] = None
command_handler: Optional[RedisCommandHandler] = None


async def on_stream_ended(pytg: PyTgCalls, update: StreamEnded):
    """
    Global handler for StreamEnded event.
    
    Called by PyTgCalls when a stream finishes playing.
    Sets the event to signal playback loop to move to next track.
    """
    chat_id = update.chat_id
    log.info(f"StreamEnded event for chat {chat_id}")
    
    if chat_id in stream_ended_events:
        stream_ended_events[chat_id].set()
    else:
        log.warning(f"StreamEnded for unknown chat {chat_id}")


async def on_chat_update(pytg: PyTgCalls, update: ChatUpdate):
    """
    Handler for chat status updates (kicked, left group, etc.).
    
    Automatically stops the stream if we get kicked or leave the group.
    """
    chat_id = update.chat_id
    status = update.status
    
    log.warning(f"ChatUpdate for chat {chat_id}: {status}")
    
    # Find channel_id by chat_id
    channel_id = None
    for cid, data in running_channels.items():
        if data.get("chat_id") == chat_id:
            channel_id = cid
            break
    
    if channel_id:
        log.warning(f"Stopping channel {channel_id} due to chat update: {status}")
        await stop_channel_stream(channel_id)
        if command_handler:
            await command_handler.update_status(
                channel_id, "stopped",
                error=f"Stopped: {status}"
            )


async def on_participant_joined(pytg: PyTgCalls, update: UpdatedGroupCallParticipant):
    """
    Handler for participant join events.
    
    Logs when someone joins the voice chat.
    """
    chat_id = update.chat_id
    participant = update.participant
    action = update.action
    
    if action == GroupCallParticipant.Action.JOINED:
        log.info(f"Participant {participant.user_id} joined voice chat in {chat_id}")
    elif action == GroupCallParticipant.Action.LEFT:
        log.info(f"Participant {participant.user_id} left voice chat in {chat_id}")


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
        
        # Register StreamEnded handler for automatic track switching
        @pytg.on_update(fl.stream_end())
        async def stream_end_handler(_: PyTgCalls, update: StreamEnded):
            await on_stream_ended(_, update)
        
        # Register ChatUpdate handler for kicked/left detection
        @pytg.on_update(fl.chat_update(
            ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT
        ))
        async def chat_update_handler(_: PyTgCalls, update: ChatUpdate):
            await on_chat_update(_, update)
        
        # Register participant join/leave handler for logging
        @pytg.on_update(fl.call_participant())
        async def participant_handler(_: PyTgCalls, update: UpdatedGroupCallParticipant):
            await on_participant_joined(_, update)
        
        await pytg.start()
        
        # Create stream ended event for this chat
        stream_ended_events[resolved_chat_id] = asyncio.Event()
        
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
    except FloodWait as e:
        # Handle FloodWait by waiting and retrying
        wait_time = e.value
        log.warning(f"Channel {channel_id}: FloodWait, waiting {wait_time} seconds...")
        await asyncio.sleep(wait_time + 1)
        return await start_channel_stream(config)  # Retry
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
            
            # Remove stream ended event for this chat
            if chat_id in stream_ended_events:
                del stream_ended_events[chat_id]
        
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
                    
                    for video_link in expanded:
                        if channel_id not in running_channels:
                            break

                        stream_url = await best_stream_url(video_link)
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
                            # Clear any previous stream ended event
                            if chat_id in stream_ended_events:
                                stream_ended_events[chat_id].clear()
                            
                            # Determine audio quality from config
                            audio_quality_map = {
                                "low": AudioQuality.LOW,
                                "medium": AudioQuality.MEDIUM,
                                "high": AudioQuality.HIGH,
                                "studio": AudioQuality.STUDIO,
                            }
                            audio_quality = audio_quality_map.get(
                                config.audio_quality.lower() if config.audio_quality else "studio",
                                AudioQuality.STUDIO
                            )
                            
                            # Determine video quality from config
                            # Supports: SD_480p, HD_720p, FHD_1080p, QHD_2K, UHD_4K
                            video_quality_map = {
                                "480p": VideoQuality.SD_480p,
                                "sd": VideoQuality.SD_480p,
                                "720p": VideoQuality.HD_720p,
                                "hd": VideoQuality.HD_720p,
                                "1080p": VideoQuality.FHD_1080p,
                                "fhd": VideoQuality.FHD_1080p,
                                "2k": VideoQuality.QHD_2K,
                                "qhd": VideoQuality.QHD_2K,
                                "1440p": VideoQuality.QHD_2K,
                                "4k": VideoQuality.UHD_4K,
                                "uhd": VideoQuality.UHD_4K,
                                "2160p": VideoQuality.UHD_4K,
                            }
                            video_quality = video_quality_map.get(
                                config.video_quality.lower() if config.video_quality else "480p",
                                VideoQuality.SD_480p
                            )
                            
                            # Build MediaStream parameters
                            media_kwargs = {
                                "audio_parameters": audio_quality,
                            }
                            
                            # Prepare FFmpeg parameters
                            # We use build_ffmpeg_av_args to get optimized parameters for the target quality
                            v_args, a_args = build_ffmpeg_av_args(config.video_quality or "480p")
                            ffmpeg_params_list = v_args + a_args
                            ffmpeg_params_str = " ".join(ffmpeg_params_list)
                            
                            # Add ffmpeg_parameters if configured
                            if config.ffmpeg_args:
                                media_kwargs["ffmpeg_parameters"] = f"{ffmpeg_params_str} {config.ffmpeg_args}"
                            else:
                                media_kwargs["ffmpeg_parameters"] = ffmpeg_params_str
                            
                            log.info(f"Channel {channel_id}: Using FFmpeg params: {media_kwargs['ffmpeg_parameters']}")
                            
                            # Add ytdlp_parameters if configured
                            
                            # Add ytdlp_parameters if configured
                            if config.ytdlp_parameters:
                                media_kwargs["ytdlp_parameters"] = config.ytdlp_parameters
                            
                            # Add headers if configured
                            if config.stream_headers:
                                media_kwargs["headers"] = config.stream_headers
                            
                            # Determine stream type based on configuration
                            # If stream_type is 'audio', force audio-only mode
                            # If stream_type is 'video' (default), try to stream video
                            stream_type = getattr(config, 'stream_type', 'video')
                            
                            # Check if content is audio-only
                            is_audio_only = stream_url.lower().endswith(('.flac', '.mp3', '.wav', '.ogg', '.m4a', '.aac'))
                            
                            if stream_type == 'audio':
                                media_kwargs["video_flags"] = MediaStream.Flags.IGNORE
                                media = MediaStream(stream_url, **media_kwargs)
                            else:
                                # Video mode
                                if is_audio_only:
                                    # Audio content in Video mode -> Try to use placeholder
                                    placeholder_path = None
                                    
                                    # 1. Try custom placeholder
                                    custom_placeholder = getattr(config, 'placeholder_image', None)
                                    if custom_placeholder:
                                        # Backend stores as "data/placeholders/..."
                                        # We need to map it to local path
                                        # Assuming streamer is in /opt/sattva-streamer/streamer and data is in /opt/sattva-streamer/data
                                        
                                        # If path starts with data/, replace with ../data/
                                        if custom_placeholder.startswith("data/"):
                                            custom_placeholder = os.path.join("..", custom_placeholder)
                                        
                                        custom_path = os.path.abspath(custom_placeholder)
                                        if os.path.exists(custom_path):
                                            placeholder_path = custom_path
                                            log.info(f"Using custom placeholder: {placeholder_path}")
                                    
                                    # 2. Fallback to default
                                    if not placeholder_path:
                                        placeholder_path = os.path.abspath("assets/placeholder.png")
                                    
                                    if os.path.exists(placeholder_path):
                                        log.info(f"Using placeholder for audio content: {placeholder_path}")
                                        
                                        # Add loop and shortest flags to loop image until audio ends
                                        extra_flags = "-loop 1 -shortest"
                                        if "ffmpeg_parameters" in media_kwargs:
                                            media_kwargs["ffmpeg_parameters"] += f" {extra_flags}"
                                        else:
                                            media_kwargs["ffmpeg_parameters"] = extra_flags
                                        
                                        media_kwargs["video_parameters"] = video_quality
                                        
                                        # Use placeholder as video source, stream_url as audio source
                                        media = MediaStream(placeholder_path, audio_path=stream_url, **media_kwargs)
                                    else:
                                        log.warning(f"Placeholder not found at {placeholder_path}, streaming audio only")
                                        media_kwargs["video_flags"] = MediaStream.Flags.IGNORE
                                        media = MediaStream(stream_url, **media_kwargs)
                                else:
                                    media_kwargs["video_parameters"] = video_quality
                                    media = MediaStream(stream_url, **media_kwargs)
                            
                            await pytg.play(chat_id, media)
                        except Exception as e:
                            log.error(f"Channel {channel_id}: Join call failed: {e}")
                            await asyncio.sleep(5)
                            continue
                        
                        # Wait for StreamEnded event (with timeout fallback)
                        # Use 7200s (2 hours) as max timeout for very long FLAC albums
                        max_duration = item.get("duration") or 7200
                        log.info(f"Channel {channel_id}: Waiting for StreamEnded (max {max_duration}s)")
                        
                        try:
                            event = stream_ended_events.get(chat_id)
                            if event:
                                # Wait for StreamEnded event with timeout
                                await asyncio.wait_for(event.wait(), timeout=max_duration)
                                log.info(f"Channel {channel_id}: StreamEnded received, moving to next track")
                            else:
                                # Fallback: no event registered, use old polling method
                                log.warning(f"Channel {channel_id}: No stream event, using duration wait")
                                await asyncio.sleep(min(max_duration, 600))
                        except asyncio.TimeoutError:
                            log.warning(f"Channel {channel_id}: Timeout waiting for StreamEnded, forcing next track")
                        except asyncio.CancelledError:
                            log.info(f"Channel {channel_id}: Cancelled while waiting for stream end")
                            raise
                        
                        # Check if channel still running
                        if channel_id not in running_channels:
                            break
                    
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


async def pause_channel_stream(channel_id: str) -> bool:
    """Pause streaming for a channel."""
    if channel_id not in running_channels:
        log.warning(f"Channel {channel_id} not running")
        return False
    
    try:
        channel_data = running_channels[channel_id]
        pytg = channel_data.get("pytg")
        chat_id = channel_data.get("chat_id")
        
        if pytg and chat_id:
            await pytg.pause(chat_id)
            log.info(f"Channel {channel_id} paused")
            return True
        return False
    except Exception as e:
        log.exception(f"Error pausing channel {channel_id}: {e}")
        return False


async def resume_channel_stream(channel_id: str) -> bool:
    """Resume streaming for a channel."""
    if channel_id not in running_channels:
        log.warning(f"Channel {channel_id} not running")
        return False
    
    try:
        channel_data = running_channels[channel_id]
        pytg = channel_data.get("pytg")
        chat_id = channel_data.get("chat_id")
        
        if pytg and chat_id:
            await pytg.resume(chat_id)
            log.info(f"Channel {channel_id} resumed")
            return True
        return False
    except Exception as e:
        log.exception(f"Error resuming channel {channel_id}: {e}")
        return False


async def skip_channel_track(channel_id: str) -> bool:
    """Skip to next track by triggering stream_ended event."""
    if channel_id not in running_channels:
        log.warning(f"Channel {channel_id} not running")
        return False
    
    try:
        channel_data = running_channels[channel_id]
        chat_id = channel_data.get("chat_id")
        
        # Trigger stream ended event to move to next track
        if chat_id and chat_id in stream_ended_events:
            stream_ended_events[chat_id].set()
            log.info(f"Channel {channel_id} skipping to next track")
            return True
        return False
    except Exception as e:
        log.exception(f"Error skipping track on channel {channel_id}: {e}")
        return False


async def get_channel_time(channel_id: str) -> Optional[int]:
    """Get current playback position in seconds."""
    if channel_id not in running_channels:
        return None
    
    try:
        channel_data = running_channels[channel_id]
        pytg = channel_data.get("pytg")
        chat_id = channel_data.get("chat_id")
        
        if pytg and chat_id:
            position = await pytg.time(chat_id)
            log.debug(f"Channel {channel_id} position: {position}s")
            return position
        return None
    except Exception as e:
        log.exception(f"Error getting time for channel {channel_id}: {e}")
        return None


async def change_channel_volume(channel_id: str, volume: int) -> bool:
    """Change volume for a channel (0-200)."""
    if channel_id not in running_channels:
        log.warning(f"Channel {channel_id} not running")
        return False
    
    try:
        channel_data = running_channels[channel_id]
        pytg = channel_data.get("pytg")
        chat_id = channel_data.get("chat_id")
        
        if pytg and chat_id:
            # Clamp volume to valid range
            volume = max(0, min(200, volume))
            await pytg.change_volume_call(chat_id, volume)
            log.info(f"Channel {channel_id} volume changed to {volume}%")
            return True
        return False
    except Exception as e:
        log.exception(f"Error changing volume for channel {channel_id}: {e}")
        return False


async def mute_channel_stream(channel_id: str) -> bool:
    """Mute streaming for a channel (audio continues but is muted)."""
    if channel_id not in running_channels:
        log.warning(f"Channel {channel_id} not running")
        return False
    
    try:
        channel_data = running_channels[channel_id]
        pytg = channel_data.get("pytg")
        chat_id = channel_data.get("chat_id")
        
        if pytg and chat_id:
            await pytg.mute(chat_id)
            log.info(f"Channel {channel_id} muted")
            return True
        return False
    except Exception as e:
        log.exception(f"Error muting channel {channel_id}: {e}")
        return False


async def unmute_channel_stream(channel_id: str) -> bool:
    """Unmute streaming for a channel."""
    if channel_id not in running_channels:
        log.warning(f"Channel {channel_id} not running")
        return False
    
    try:
        channel_data = running_channels[channel_id]
        pytg = channel_data.get("pytg")
        chat_id = channel_data.get("chat_id")
        
        if pytg and chat_id:
            await pytg.unmute(chat_id)
            log.info(f"Channel {channel_id} unmuted")
            return True
        return False
    except Exception as e:
        log.exception(f"Error unmuting channel {channel_id}: {e}")
        return False


async def get_channel_participants(channel_id: str) -> Optional[list]:
    """Get list of participants in the voice chat."""
    if channel_id not in running_channels:
        return None
    
    try:
        channel_data = running_channels[channel_id]
        pytg = channel_data.get("pytg")
        chat_id = channel_data.get("chat_id")
        
        if pytg and chat_id:
            participants = await pytg.get_participants(chat_id)
            log.info(f"Channel {channel_id} has {len(participants) if participants else 0} participants")
            return [
                {
                    "user_id": p.user_id,
                    "muted": p.muted,
                    "volume": p.volume,
                    "video": p.video,
                    "raised_hand": p.raised_hand,
                }
                for p in (participants or [])
            ]
        return None
    except Exception as e:
        log.exception(f"Error getting participants for channel {channel_id}: {e}")
        return None


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
    command_handler.on_pause = pause_channel_stream
    command_handler.on_resume = resume_channel_stream
    command_handler.on_skip = skip_channel_track
    command_handler.on_volume = change_channel_volume
    command_handler.on_mute = mute_channel_stream
    command_handler.on_unmute = unmute_channel_stream
    command_handler.on_get_time = get_channel_time
    command_handler.on_get_participants = get_channel_participants
    
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
