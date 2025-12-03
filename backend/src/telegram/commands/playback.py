"""
Telegram command handlers for playback control.

Commands:
- /speed {value}: Set playback speed (0.5-2.0x)
- /pitch {semitones}: Adjust pitch (-12 to +12 semitones)
- /seek {time}: Seek to specific time (MM:SS or seconds)
- /rewind {seconds}: Rewind by N seconds (default: 10s)
- /forward {seconds}: Skip forward by N seconds (default: 10s)
- /position: Get current playback position
"""

import logging
import re
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message

from src.services.playback_service import PlaybackService
from src.dependencies import get_current_user
from src.schemas.telegram_user import TelegramUserSchema

logger = logging.getLogger(__name__)

# Initialize service
playback_service = PlaybackService()


def parse_time_format(time_str: str) -> Optional[int]:
    """
    Parse time string to seconds.
    Accepts formats: "1:30", "90", "1m30s"
    
    Args:
        time_str: Time string to parse
        
    Returns:
        Seconds as int, or None if invalid format
    """
    time_str = time_str.strip()
    
    # Try MM:SS format
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 2:
            try:
                minutes = int(parts[0])
                seconds = int(parts[1])
                if 0 <= seconds < 60:
                    return minutes * 60 + seconds
            except ValueError:
                pass
    
    # Try seconds only
    try:
        seconds = int(time_str)
        if seconds >= 0:
            return seconds
    except ValueError:
        pass
    
    # Try M:SS format
    try:
        minutes = int(time_str.rstrip("m"))
        if minutes >= 0:
            return minutes * 60
    except ValueError:
        pass
    
    return None


async def cmd_speed(client: Client, message: Message):
    """
    Set playback speed (0.5x - 2.0x).
    
    Usage: /speed 1.5
    """
    try:
        # Extract speed value from command
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text(
                "❌ **Usage**: `/speed <value>`\n"
                "**Example**: `/speed 1.5`\n"
                "**Range**: 0.5x to 2.0x"
            )
            return
        
        try:
            speed = float(args[1])
        except ValueError:
            await message.reply_text("❌ Speed must be a number (e.g., 1.5)")
            return
        
        if not (0.5 <= speed <= 2.0):
            await message.reply_text(
                "❌ Speed must be between 0.5x and 2.0x"
            )
            return
        
        # Get current user
        user_id = message.from_user.id
        channel_id = message.chat.id
        
        # Call service
        result = await playback_service.set_speed(
            user_id=user_id,
            channel_id=channel_id,
            speed=speed
        )
        
        if result.get("success"):
            await message.reply_text(
                f"✅ **Speed set to {speed}x**"
            )
            logger.info(f"User {user_id} set playback speed to {speed}x")
        else:
            await message.reply_text(
                f"❌ Failed to set speed: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_speed: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_pitch(client: Client, message: Message):
    """
    Adjust playback pitch.
    
    Usage: /pitch +2 or /pitch -3
    """
    try:
        # Extract pitch value from command
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text(
                "❌ **Usage**: `/pitch <semitones>`\n"
                "**Example**: `/pitch +2` (shift up 2 semitones)\n"
                "**Range**: -12 to +12 semitones"
            )
            return
        
        try:
            pitch = int(args[1])
        except ValueError:
            await message.reply_text("❌ Pitch must be an integer (e.g., +2, -3)")
            return
        
        if not (-12 <= pitch <= 12):
            await message.reply_text(
                "❌ Pitch must be between -12 and +12 semitones"
            )
            return
        
        # Get current user
        user_id = message.from_user.id
        channel_id = message.chat.id
        
        # Call service
        result = await playback_service.set_pitch(
            user_id=user_id,
            channel_id=channel_id,
            semitones=pitch
        )
        
        if result.get("success"):
            direction = "↑ up" if pitch > 0 else "↓ down" if pitch < 0 else "→"
            await message.reply_text(
                f"✅ **Pitch adjusted {direction} {abs(pitch)} semitones**"
            )
            logger.info(f"User {user_id} adjusted pitch by {pitch} semitones")
        else:
            await message.reply_text(
                f"❌ Failed to set pitch: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_pitch: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_seek(client: Client, message: Message):
    """
    Seek to specific time in current track.
    
    Usage: /seek 1:30 or /seek 90 (seconds)
    """
    try:
        # Extract time value from command
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text(
                "❌ **Usage**: `/seek <time>`\n"
                "**Examples**: `/seek 1:30` or `/seek 90` (seconds)"
            )
            return
        
        seconds = parse_time_format(args[1])
        if seconds is None:
            await message.reply_text(
                "❌ Invalid time format. Use MM:SS or seconds"
            )
            return
        
        # Get current user
        user_id = message.from_user.id
        channel_id = message.chat.id
        
        # Call service
        result = await playback_service.seek_to(
            user_id=user_id,
            channel_id=channel_id,
            position_seconds=seconds
        )
        
        if result.get("success"):
            minutes = seconds // 60
            secs = seconds % 60
            await message.reply_text(
                f"✅ **Seeking to {minutes}:{secs:02d}**"
            )
            logger.info(f"User {user_id} seeked to {seconds}s")
        else:
            await message.reply_text(
                f"❌ Failed to seek: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_seek: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_rewind(client: Client, message: Message):
    """
    Rewind playback by N seconds (default: 10s).
    
    Usage: /rewind or /rewind 30
    """
    try:
        # Extract seconds from command (default: 10)
        args = message.text.split()
        seconds_to_rewind = 10
        
        if len(args) > 1:
            try:
                seconds_to_rewind = int(args[1])
                if seconds_to_rewind <= 0:
                    await message.reply_text("❌ Rewind seconds must be positive")
                    return
            except ValueError:
                await message.reply_text("❌ Rewind seconds must be an integer")
                return
        
        # Get current user
        user_id = message.from_user.id
        channel_id = message.chat.id
        
        # Call service
        result = await playback_service.rewind(
            user_id=user_id,
            channel_id=channel_id,
            seconds=seconds_to_rewind
        )
        
        if result.get("success"):
            new_position = result.get("new_position", 0)
            minutes = new_position // 60
            secs = new_position % 60
            await message.reply_text(
                f"⏪ **Rewinded {seconds_to_rewind}s → {minutes}:{secs:02d}**"
            )
            logger.info(f"User {user_id} rewinded {seconds_to_rewind}s")
        else:
            await message.reply_text(
                f"❌ Failed to rewind: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_rewind: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_forward(client: Client, message: Message):
    """
    Skip forward by N seconds (default: 10s).
    
    Usage: /forward or /forward 30
    """
    try:
        # Extract seconds from command (default: 10)
        args = message.text.split()
        seconds_to_forward = 10
        
        if len(args) > 1:
            try:
                seconds_to_forward = int(args[1])
                if seconds_to_forward <= 0:
                    await message.reply_text("❌ Forward seconds must be positive")
                    return
            except ValueError:
                await message.reply_text("❌ Forward seconds must be an integer")
                return
        
        # Get current user
        user_id = message.from_user.id
        channel_id = message.chat.id
        
        # Call service
        result = await playback_service.forward(
            user_id=user_id,
            channel_id=channel_id,
            seconds=seconds_to_forward
        )
        
        if result.get("success"):
            new_position = result.get("new_position", 0)
            minutes = new_position // 60
            secs = new_position % 60
            await message.reply_text(
                f"⏩ **Skipped {seconds_to_forward}s → {minutes}:{secs:02d}**"
            )
            logger.info(f"User {user_id} forwarded {seconds_to_forward}s")
        else:
            await message.reply_text(
                f"❌ Failed to skip: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_forward: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_position(client: Client, message: Message):
    """
    Get current playback position.
    
    Usage: /position
    """
    try:
        # Get current user
        user_id = message.from_user.id
        channel_id = message.chat.id
        
        # Call service
        result = await playback_service.get_position(
            user_id=user_id,
            channel_id=channel_id
        )
        
        if result.get("success"):
            current = result.get("current_position", 0)
            total = result.get("total_duration", 0)
            
            current_min = current // 60
            current_sec = current % 60
            total_min = total // 60
            total_sec = total % 60
            
            # Calculate progress bar
            if total > 0:
                progress_pct = (current / total) * 100
                filled = int(progress_pct / 5)
                bar = "█" * filled + "░" * (20 - filled)
                progress_str = f"{bar} {progress_pct:.0f}%"
            else:
                progress_str = "⏸️ No active playback"
            
            await message.reply_text(
                f"**Playback Position**\n\n"
                f"{progress_str}\n\n"
                f"⏱️ {current_min}:{current_sec:02d} / {total_min}:{total_sec:02d}\n"
                f"**Speed**: {result.get('speed', 1.0)}x"
            )
        else:
            await message.reply_text(
                f"❌ Failed to get position: {result.get('error', 'No active playback')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_position: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


def register_playback_commands(app: Client):
    """
    Register all playback command handlers with Pyrogram client.
    
    Args:
        app: Pyrogram Client instance
    """
    # Register /speed command
    app.on_message(filters.command("speed"))(cmd_speed)
    
    # Register /pitch command
    app.on_message(filters.command("pitch"))(cmd_pitch)
    
    # Register /seek command
    app.on_message(filters.command("seek"))(cmd_seek)
    
    # Register /rewind command
    app.on_message(filters.command("rewind"))(cmd_rewind)
    
    # Register /forward command
    app.on_message(filters.command("forward"))(cmd_forward)
    
    # Register /position command
    app.on_message(filters.command("position"))(cmd_position)
    
    logger.info("Playback commands registered successfully")
