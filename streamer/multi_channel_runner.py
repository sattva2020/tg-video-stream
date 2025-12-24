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
    from pyrogram.errors import SessionExpired, AuthKeyInvalid, RPCError, BadMsgNotification
    # Note: 'from pyrogram import raw' removed - not needed anymore
    # PyTgCalls handles group call creation internally via GroupCallConfig(auto_start=True)
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    log.warning("pyrogram not available")

try:
    from pytgcalls import PyTgCalls
    from pytgcalls import filters as fl
    from pytgcalls.types import (
        MediaStream, AudioQuality, VideoQuality, StreamEnded,
        ChatUpdate, GroupCallParticipant, UpdatedGroupCallParticipant,
        GroupCallConfig  # For auto_start group call creation
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
playlist_update_events: Dict[str, asyncio.Event] = {}  # channel_id -> Event (signals playlist update)
play_in_progress: Dict[int, bool] = {}  # chat_id -> True if play() is executing (ignore StreamEnded during this)
manager: Optional[MultiChannelManager] = None
command_handler: Optional[RedisCommandHandler] = None


def _env_truthy(name: str, default: bool = True) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _format_exception(e: BaseException) -> str:
    msg = str(e).strip()
    if msg:
        return f"{type(e).__name__}: {msg}"
    return type(e).__name__


def _human_hint_for_telegram_error(e: BaseException) -> Optional[str]:
    """Возвращает короткую подсказку по типовым причинам вылета из видеочата."""
    name = type(e).__name__
    text = (str(e) or "").upper()

    # Чаще всего auto_start упирается в админские права.
    if "ADMIN" in name.upper() or "CHAT_ADMIN_REQUIRED" in text or "ADMIN" in text:
        return (
            "Нет прав начинать видеочат. Запустите видеочат вручную админом "
            "или выдайте аккаунту-стримеру права/роль администратора. "
            "Как обходной путь: установите TG_CALL_AUTO_START=0 и стартуйте видеочат вручную."
        )

    # Типичная история при сетевой блокировке звонков.
    if "CALL" in name.upper() and ("TIMEOUT" in text or "CONNECTION" in text or "NETWORK" in text):
        return (
            "Похоже на сетевую проблему Telegram Calls (UDP/VoIP). Проверьте звонки 1-на-1, "
            "попробуйте другую сеть/моб.интернет или VPN."
        )

    return None


async def on_stream_ended(pytg: PyTgCalls, update: StreamEnded):
    """
    Global handler for StreamEnded event.
    
    Called by PyTgCalls when a stream finishes playing.
    Sets the event to signal playback loop to move to next track.
    
    IMPORTANT: We ignore StreamEnded events that fire during play() execution,
    because PyTgCalls can emit a 'stale' StreamEnded from previous state.
    """
    chat_id = update.chat_id
    
    # Debug: log current state
    is_playing = play_in_progress.get(chat_id, False)
    log.info(f"StreamEnded event for chat {chat_id} (play_in_progress={is_playing}, known_chats={list(play_in_progress.keys())})")
    
    # Ignore StreamEnded if play() is still executing for this chat
    # This prevents race condition where StreamEnded fires during play() call
    if is_playing:
        log.warning(f"StreamEnded IGNORED for chat {chat_id} - play() still in progress")
        return
    
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


# NOTE: ensure_group_call() was removed - PyTgCalls handles this automatically!
# When calling pytg.play() with GroupCallConfig(auto_start=True) (default),
# PyTgCalls creates the group call if it doesn't exist.
# See: pytgcalls/methods/stream/play.py lines 71-76


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
        
        # Start client with retries for transient BadMsgNotification issues
        start_attempts = 0
        while start_attempts < 5:
            try:
                await client.start()
                me = await client.get_me()
                log.info(f"Channel {channel_id}: Logged in as {me.id}")
                break
            except BadMsgNotification as e:
                start_attempts += 1
                log.warning(f"BadMsgNotification during start (attempt {start_attempts}): {e}. Retrying after backoff...")
                try:
                    await client.stop()
                except Exception:
                    pass
                await asyncio.sleep(1 + start_attempts * 2)
            except RPCError as e:
                log.exception(f"RPCError during client start: {e}")
                try:
                    await client.stop()
                except Exception:
                    pass
                return f"Failed to start: {str(e)}"
            except (SessionExpired, AuthKeyInvalid) as e:
                log.error(f"Invalid session for channel {channel_id}: {e}")
                try:
                    await client.stop()
                except Exception:
                    pass
                return f"Invalid session: {str(e)}"
            except Exception as e:
                log.exception(f"Unexpected error during client start: {e}")
                try:
                    await client.stop()
                except Exception:
                    pass
                return f"Failed to start: {str(e)}"
        else:
            log.error(f"Channel {channel_id}: Could not initialize client after retries")
            return f"Failed to start: could not initialize client after retries"
        
        # Resolve chat to get proper peer (required by PyTgCalls)
        # Try username first (more reliable for peer resolution), then fallback to chat_id
        resolved_chat_id = None
        chat_target = f"@{config.chat_username}" if config.chat_username else config.chat_id
        last_error = None
        
        # CRITICAL: Load dialogs first to populate Pyrogram's peer cache
        # This ensures that chats not in the recent cache can be resolved
        log.info(f"Channel {channel_id}: Pre-loading dialogs to populate peer cache...")
        try:
            dialog_count = 0
            async for dialog in client.get_dialogs(limit=200):
                dialog_count += 1
                # Check if this is our target chat
                if hasattr(dialog.chat, 'id'):
                    if dialog.chat.id == config.chat_id or (config.chat_username and getattr(dialog.chat, 'username', None) == config.chat_username.lstrip('@')):
                        log.info(f"Channel {channel_id}: Found target chat '{dialog.chat.title}' (id: {dialog.chat.id}) in dialogs at position {dialog_count}")
            log.info(f"Channel {channel_id}: Loaded {dialog_count} dialogs into cache")
        except Exception as e:
            log.warning(f"Channel {channel_id}: Failed to pre-load dialogs: {e}, continuing anyway...")
        
        async def try_resolve(target):
            try:
                return await client.get_chat(target)
            except Exception as e:
                nonlocal last_error
                last_error = str(e)
                return None

        # 1. Try primary target (username or ID)
        chat = await try_resolve(chat_target)
        
        # 2. If failed and we have a separate ID (when username was primary), try ID
        if not chat and config.chat_username and config.chat_id:
            log.warning(f"Channel {channel_id}: Failed to resolve by username {chat_target}, trying ID {config.chat_id}")
            chat = await try_resolve(config.chat_id)

        # 3. If still failed and ID looks like it needs -100 prefix
        if not chat and config.chat_id:
            cid = str(config.chat_id)
            # Check if it's a negative ID that doesn't start with -100 and is long enough to be a channel ID
            # (Basic group IDs are usually shorter, but let's just try adding -100 if it fails)
            if cid.startswith("-") and not cid.startswith("-100"):
                # e.g. -5059943333 -> -1005059943333
                try:
                    new_id = int("-100" + cid[1:])
                    log.info(f"Channel {channel_id}: Retrying with -100 prefix: {new_id}")
                    chat = await try_resolve(new_id)
                except ValueError:
                    pass

        if chat:
            resolved_chat_id = chat.id
            log.info(f"Channel {channel_id}: Resolved chat '{chat.title}' (id: {resolved_chat_id})")
        else:
            # Diagnostic information for resolve failures
            log.error(f"Channel {channel_id}: Failed to resolve chat. Last error: {last_error}")
            try:
                me = await client.get_me()
                log.info(
                    f"Channel {channel_id}: session account: id={me.id}, username={getattr(me, 'username', None)}"
                )
            except Exception as e_me:
                log.info(f"Channel {channel_id}: Could not fetch session 'me' for diagnostics: {e_me}")

            # If common 'Peer id invalid' or 'ID not found', try listing recent dialogs to see what's visible
            if last_error and ("Peer id invalid" in last_error or "ID not found" in last_error):
                try:
                    dialogs = await client.get_dialogs(limit=200)
                    found = any(
                        getattr(d.chat, 'id', None) == config.chat_id or getattr(d.chat, 'id', None) == resolved_chat_id
                        for d in dialogs
                    )
                    log.info(f"Channel {channel_id}: Dialogs scan (limit 200) found target chat: {found}")
                except Exception as e_dialogs:
                    log.info(f"Channel {channel_id}: Failed to scan dialogs for diagnostics: {e_dialogs}")

        if not resolved_chat_id:
            log.error(f"Channel {channel_id}: Could not resolve chat, aborting")
            await client.stop()
            return f"Could not resolve chat: {last_error}"
        
        # NOTE: We removed manual ensure_group_call() - PyTgCalls handles this automatically!
        # When calling pytg.play() with GroupCallConfig(auto_start=True) (default),
        # PyTgCalls will create the group call if it doesn't exist.
        # This avoids race conditions with PyTgCalls' internal cache.
        
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

        # Sanity-check get_me before starting PyTgCalls - helps detect BadMsgNotification early
        get_me_attempts = 0
        while get_me_attempts < 4:
            try:
                candidate_me = await client.get_me()
                # ensure we received a proper User-like object
                if getattr(candidate_me, 'id', None):
                    break
                else:
                    get_me_attempts += 1
                    log.warning(f"Channel {channel_id}: client.get_me returned unexpected value (attempt {get_me_attempts}), retrying...")
                    await asyncio.sleep(1 + get_me_attempts * 2)
            except Exception as e:
                get_me_attempts += 1
                log.warning(f"Channel {channel_id}: client.get_me failed (attempt {get_me_attempts}): {e!r}")
                await asyncio.sleep(1 + get_me_attempts * 2)
        else:
            log.error(f"Channel {channel_id}: client.get_me failed repeatedly before starting PyTgCalls, aborting")
            try:
                await client.stop()
            except Exception:
                pass
            return f"Failed to start: client.get_me failed"
        
        # Start PyTgCalls with retries to handle transient BadMsgNotification errors
        start_attempts = 0
        while start_attempts < 5:
            try:
                await pytg.start()
                break
            except BadMsgNotification as e:
                start_attempts += 1
                log.warning(f"BadMsgNotification during pytg.start (attempt {start_attempts}): {e}. Retrying after backoff...")
                try:
                    await pytg.stop()
                except Exception:
                    pass
                try:
                    await client.stop()
                except Exception:
                    pass
                await asyncio.sleep(1 + start_attempts * 2)
                # Recreate client and pytg for next attempt
                client = Client(
                    name=f"channel_{channel_id}",
                    api_id=config.api_id,
                    api_hash=config.api_hash,
                    session_string=config.session_string,
                    in_memory=True
                )
                await client.start()
                pytg = PyTgCalls(client)
                # re-register handlers
                @pytg.on_update(fl.stream_end())
                async def stream_end_handler(_: PyTgCalls, update: StreamEnded):
                    await on_stream_ended(_, update)
                @pytg.on_update(fl.chat_update(
                    ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT
                ))
                async def chat_update_handler(_: PyTgCalls, update: ChatUpdate):
                    await on_chat_update(_, update)
                @pytg.on_update(fl.call_participant())
                async def participant_handler(_: PyTgCalls, update: UpdatedGroupCallParticipant):
                    await on_participant_joined(_, update)
            except RPCError as e:
                log.exception(f"RPCError during pytg.start: {e}")
                try:
                    await pytg.stop()
                except Exception:
                    pass
                return f"Failed to start: {str(e)}"
            except AttributeError as e:
                # AttributeError here often means Pyrogram returned an unexpected object
                # (e.g. BadMsgNotification) which caused attribute access to fail.
                # Treat AttributeError as transient: retry with backoff, recreate client and pytg,
                # and re-resolve the chat id in case the session cache needs refreshing.
                start_attempts += 1
                log.warning(
                    f"AttributeError during pytg.start (attempt {start_attempts}): {e!r}. "
                    "Treating as transient and retrying after backoff..."
                )
                try:
                    await pytg.stop()
                except Exception:
                    pass
                try:
                    await client.stop()
                except Exception:
                    pass

                # Backoff delay increases with attempts
                await asyncio.sleep(1 + start_attempts * 3)

                # Recreate client and pytg for next attempt
                client = Client(
                    name=f"channel_{channel_id}",
                    api_id=config.api_id,
                    api_hash=config.api_hash,
                    session_string=config.session_string,
                    in_memory=True
                )
                try:
                    await client.start()
                except Exception as e2:
                    log.exception(f"Failed to restart client after AttributeError retry: {e2}")
                    continue

                # Try re-resolving the chat to refresh local peer cache
                try:
                    refreshed = None
                    try:
                        refreshed = await try_resolve(resolved_chat_id or chat_target)
                    except Exception as e3:
                        log.debug(f"Re-resolve attempt failed (ok): {e3}")

                    if refreshed:
                        resolved_chat_id = refreshed.id
                        log.info(f"Channel {channel_id}: Re-resolved chat after retry: {refreshed.title} (id: {resolved_chat_id})")
                    else:
                        log.debug(f"Channel {channel_id}: Re-resolve did not return chat; will retry pytg.start anyway")
                except Exception as e4:
                    log.debug(f"Channel {channel_id}: Exception while re-resolving chat: {e4}")

                pytg = PyTgCalls(client)
                # re-register handlers
                @pytg.on_update(fl.stream_end())
                async def stream_end_handler(_: PyTgCalls, update: StreamEnded):
                    await on_stream_ended(_, update)
                @pytg.on_update(fl.chat_update(
                    ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT
                ))
                async def chat_update_handler(_: PyTgCalls, update: ChatUpdate):
                    await on_chat_update(_, update)
                @pytg.on_update(fl.call_participant())
                async def participant_handler(_: PyTgCalls, update: UpdatedGroupCallParticipant):
                    await on_participant_joined(_, update)

                # Continue retry loop
                continue
            except Exception as e:
                # Some pyrogram/pytgcalls errors arrive as generic exceptions but contain
                # transient hints (BadMsgNotification / msg_seqno too high). Treat these
                # as retryable with the same backoff and recreation logic.
                msg = str(e) or ""
                if "BadMsgNotification" in msg or "msg_seqno" in msg or "too high" in msg:
                    start_attempts += 1
                    log.warning(f"Transient error during pytg.start (attempt {start_attempts}): {e!r}. Retrying after backoff...")
                    try:
                        await pytg.stop()
                    except Exception:
                        pass
                    try:
                        await client.stop()
                    except Exception:
                        pass
                    await asyncio.sleep(1 + start_attempts * 3)

                    # Recreate client and pytg for next attempt
                    client = Client(
                        name=f"channel_{channel_id}",
                        api_id=config.api_id,
                        api_hash=config.api_hash,
                        session_string=config.session_string,
                        in_memory=True
                    )
                    try:
                        await client.start()
                    except Exception as e2:
                        log.exception(f"Failed to restart client after transient error: {e2}")
                        continue

                    pytg = PyTgCalls(client)
                    # re-register handlers
                    @pytg.on_update(fl.stream_end())
                    async def stream_end_handler(_: PyTgCalls, update: StreamEnded):
                        await on_stream_ended(_, update)
                    @pytg.on_update(fl.chat_update(
                        ChatUpdate.Status.KICKED | ChatUpdate.Status.LEFT_GROUP | ChatUpdate.Status.CLOSED_VOICE_CHAT
                    ))
                    async def chat_update_handler(_: PyTgCalls, update: ChatUpdate):
                        await on_chat_update(_, update)
                    @pytg.on_update(fl.call_participant())
                    async def participant_handler(_: PyTgCalls, update: UpdatedGroupCallParticipant):
                        await on_participant_joined(_, update)

                    continue

                log.exception(f"Unexpected error during pytg.start: {e}")
                try:
                    await pytg.stop()
                except Exception:
                    pass
                return f"Failed to start: {str(e)}"
        else:
            log.error(f"Channel {channel_id}: Could not start PyTgCalls after retries")
            try:
                await client.stop()
            except Exception:
                pass
            return f"Failed to start: could not initialize PyTgCalls"

        # Wait for PyTgCalls to fully initialize
        await asyncio.sleep(5)
        
        # Create stream ended event for this chat
        stream_ended_events[resolved_chat_id] = asyncio.Event()
        playlist_update_events[channel_id] = asyncio.Event()
        play_in_progress[resolved_chat_id] = False  # Initialize play flag
        
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
        return f"Invalid session: {str(e)}"
    except FloodWait as e:
        # Handle FloodWait by waiting and retrying
        wait_time = e.value
        log.warning(f"Channel {channel_id}: FloodWait, waiting {wait_time} seconds...")
        await asyncio.sleep(wait_time + 1)
        return await start_channel_stream(config)  # Retry
    except Exception as e:
        log.exception(f"Failed to start channel {channel_id}: {e}")
        return f"Failed to start: {str(e)}"


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
            if chat_id in play_in_progress:
                del play_in_progress[chat_id]
        
        if channel_id in playlist_update_events:
            del playlist_update_events[channel_id]

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
                
                # Wait for 60 seconds OR until playlist update event
                if channel_id in playlist_update_events:
                    playlist_update_events[channel_id].clear()
                    try:
                        await asyncio.wait_for(playlist_update_events[channel_id].wait(), timeout=60)
                        log.info(f"Channel {channel_id}: Woke up by playlist update")
                    except asyncio.TimeoutError:
                        pass
                else:
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

                # Если backend отдаёт относительный URL (например, /api/media/...),
                # превращаем его в абсолютный, иначе ffmpeg воспримет как локальный путь.
                if link.startswith("/api/"):
                    link = backend_url.rstrip("/") + link
                
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
                            # Note: event.clear() moved to AFTER play() succeeds
                            # to prevent race condition with StreamEnded during play()
                            
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
                            
                            # Check if content is audio-only by file extension
                            is_audio_only = stream_url.lower().endswith(('.flac', '.mp3', '.wav', '.ogg', '.m4a', '.aac'))
                            
                            log.info(f"Channel {channel_id}: stream_type={stream_type}, is_audio_only={is_audio_only}, url={stream_url[:80]}")
                            
                            if stream_type == 'audio' or is_audio_only:
                                # Audio file with video placeholder - creates VIDEO CHAT (not voice chat)
                                # Based on official PyTgCalls example: piped_image_calls
                                # See: https://github.com/pytgcalls/pytgcalls/blob/master/example/piped_image_calls/
                                
                                # Path to placeholder - try .mp4 first (pre-rendered video), then .png
                                # .mp4 is preferred because PyTgCalls 2.2.1 has a bug with is_image detection
                                # where PNG files cause SIGILL crash in NTgCalls on some CPUs
                                import os as os_check
                                channel_mp4 = f"/opt/sattva-streamer/data/placeholders/{channel_id}.mp4"
                                channel_png = f"/opt/sattva-streamer/data/placeholders/{channel_id}.png"
                                default_mp4 = "/opt/sattva-streamer/data/placeholders/default.mp4"
                                default_png = "/opt/sattva-streamer/data/placeholders/default.png"
                                
                                placeholder_path = None
                                placeholder_is_video = False
                                # Prefer .mp4 files (pre-rendered video from static image)
                                if os_check.path.exists(channel_mp4):
                                    placeholder_path = channel_mp4
                                    placeholder_is_video = True
                                elif os_check.path.exists(channel_png):
                                    placeholder_path = channel_png
                                elif os_check.path.exists(default_mp4):
                                    placeholder_path = default_mp4
                                    placeholder_is_video = True
                                elif os_check.path.exists(default_png):
                                    placeholder_path = default_png
                                
                                if placeholder_path:
                                    # Use placeholder (video or image) + audio = VIDEO CHAT
                                    if placeholder_is_video:
                                        # Pre-rendered .mp4 video - simpler approach, works reliably
                                        # The .mp4 file is created from static image with ffmpeg:
                                        # ffmpeg -loop 1 -i image.png -c:v libx264 -t 3600 -pix_fmt yuv420p -r 1 -an output.mp4
                                        media = MediaStream(
                                            placeholder_path,
                                            audio_path=stream_url,
                                            audio_parameters=audio_quality,
                                            video_parameters=video_quality,
                                        )
                                        log.info(f"Channel {channel_id}: Video chat mode with pre-rendered video placeholder '{placeholder_path}' + audio")
                                    else:
                                        # PNG image - need workaround for PyTgCalls bug
                                        # WORKAROUND for PyTgCalls 2.2.1 bug: is_image detection fails
                                        # because `is_image &= ...` when initial value is False always = False
                                        # We manually add -loop 1 -framerate 1 via ffmpeg_parameters
                                        media = MediaStream(
                                            placeholder_path,
                                            audio_path=stream_url,
                                            audio_parameters=audio_quality,
                                            video_parameters=video_quality,
                                            # --video prefix tells PyTgCalls to add these params to video stream only
                                            ffmpeg_parameters='--video -loop 1 -framerate 1',
                                        )
                                        log.info(f"Channel {channel_id}: Video chat mode with PNG placeholder '{placeholder_path}' + audio (with -loop 1)")
                                else:
                                    # Fallback to audio-only if no placeholder
                                    media = MediaStream(
                                        stream_url,
                                        audio_parameters=audio_quality,
                                        video_flags=MediaStream.Flags.IGNORE,
                                    )
                                    log.warning(f"Channel {channel_id}: No placeholder found, using audio-only mode")
                            else:
                                # Video mode - content has video
                                media_kwargs["video_parameters"] = video_quality
                                media = MediaStream(stream_url, **media_kwargs)
                            
                            log.info(f"Channel {channel_id}: Calling pytg.play() with MediaStream('{stream_url}')")
                            
                            # PyTgCalls has built-in retry (4 attempts) in connect_call.py
                            # GroupCallConfig(auto_start=True) tells PyTgCalls to create
                            # the video chat if it doesn't exist (default behavior)
                            auto_start = _env_truthy("TG_CALL_AUTO_START", default=True)
                            if not auto_start:
                                log.warning(
                                    "Channel %s: TG_CALL_AUTO_START=0 — авто-создание видеочата отключено; "
                                    "видеочат должен быть уже запущен в группе",
                                    channel_id,
                                )
                            try:
                                # Set flag BEFORE play() to ignore any StreamEnded during execution
                                play_in_progress[chat_id] = True
                                
                                try:
                                    # Try to join explicitly first to handle BadMsgNotification
                                    await pytg.join_group_call(
                                        chat_id,
                                        media,
                                        config=GroupCallConfig(auto_start=auto_start)
                                    )
                                except Exception as e:
                                    if "BadMsgNotification" in str(e):
                                        log.warning(f"Channel {channel_id}: BadMsgNotification on join, retrying in 2s...")
                                        await asyncio.sleep(2)
                                        # Retry with play() which handles connection internally
                                        await pytg.play(
                                            chat_id,
                                            media,
                                            config=GroupCallConfig(auto_start=auto_start)
                                        )
                                    else:
                                        # If join failed for other reasons, try play() anyway as fallback
                                        await pytg.play(
                                            chat_id, 
                                            media, 
                                            config=GroupCallConfig(auto_start=auto_start)
                                        )

                                log.info(f"Channel {channel_id}: pytg.play() completed successfully")
                            except Exception as play_error:
                                formatted = _format_exception(play_error)
                                hint = _human_hint_for_telegram_error(play_error)
                                log.exception(f"Channel {channel_id}: play() failed: {formatted}")
                                if command_handler:
                                    await command_handler.update_status(
                                        channel_id,
                                        "error",
                                        error=(formatted + (f" | hint: {hint}" if hint else "")),
                                    )
                                raise play_error
                            finally:
                                # Clear flag AFTER play() completes (success or failure)
                                play_in_progress[chat_id] = False
                        except Exception as e:
                            formatted = _format_exception(e)
                            hint = _human_hint_for_telegram_error(e)
                            log.exception(f"Channel {channel_id}: Join call failed: {formatted}")
                            if command_handler:
                                await command_handler.update_status(
                                    channel_id,
                                    "error",
                                    error=(formatted + (f" | hint: {hint}" if hint else "")),
                                )
                            await asyncio.sleep(5)
                            continue
                        
                        # Wait for StreamEnded event (with timeout fallback)
                        # Use 7200s (2 hours) as max timeout for very long FLAC albums
                        max_duration = item.get("duration") or 7200
                        log.info(f"Channel {channel_id}: Waiting for StreamEnded (max {max_duration}s)")
                        
                        try:
                            event = stream_ended_events.get(chat_id)
                            if event:
                                # CRITICAL: Clear event AFTER play() succeeds, right before waiting
                                # This prevents race condition where StreamEnded fires during play()
                                event.clear()
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
                    if "ConnectionNotFound" in str(e):
                        log.error(f"Channel {channel_id}: Voice Chat connection failed. Please ensure Voice Chat is started in the channel.")
                        await asyncio.sleep(10)
                    else:
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


async def update_channel_playlist(channel_id: str) -> bool:
    """
    Handle playlist update notification.
    
    Signals the playback loop to wake up and re-fetch the playlist immediately.
    """
    if channel_id not in running_channels:
        log.warning(f"Channel {channel_id} not running, cannot update playlist")
        return False
    
    if channel_id in playlist_update_events:
        playlist_update_events[channel_id].set()
        log.info(f"Channel {channel_id}: Playlist update signal sent")
        return True
    
    return False


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
    command_handler.on_update_playlist = update_channel_playlist
    
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
