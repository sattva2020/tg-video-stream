"""
Telegram command handlers for schedule management.

Commands:
- /schedule {time} {playlist}: Schedule playlist for automatic playback (admin only)
- /unschedule {id}: Cancel scheduled playlist (admin only)
- /schedules: List all scheduled playlists
"""

import logging
from typing import Optional, Dict, Any
import re

from pyrogram import Client, filters
from pyrogram.types import Message

from src.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

# Initialize service
scheduler_service = SchedulerService()


def parse_time_format(time_str: str) -> Optional[str]:
    """
    Parse time string to HH:MM format or validate cron expression.
    
    Args:
        time_str: Time string like "08:00" or "0 8 * * *"
        
    Returns:
        Formatted time string or None if invalid
    """
    time_str = time_str.strip()
    
    # Check HH:MM format
    if re.match(r"^\d{1,2}:\d{2}$", time_str):
        parts = time_str.split(":")
        hours = int(parts[0])
        minutes = int(parts[1])
        if 0 <= hours < 24 and 0 <= minutes < 60:
            return f"{hours:02d}:{minutes:02d}"
    
    # Check if it looks like cron expression
    if len(time_str.split()) == 5:
        return time_str  # Return as-is for cron validation in service
    
    return None


async def cmd_schedule(client: Client, message: Message):
    """
    Schedule a playlist for automatic playback.
    
    Usage: /schedule 08:00 morning_playlist
           /schedule 0 8 * * * morning_playlist
    """
    try:
        # Parse command arguments
        parts = message.text.split(maxsplit=3)
        
        # Try to extract time and playlist
        if len(parts) < 3:
            await message.reply_text(
                "❌ **Usage**: `/schedule <time> <playlist>`\n"
                "**Examples**:\n"
                "  `/schedule 08:00 morning` (daily at 8:00)\n"
                "  `/schedule 0 8 * * * morning` (cron format)\n"
                "  `/schedule 0 8 * * 1-5 weekday` (weekdays only)"
            )
            return
        
        time_str = parts[1]
        playlist_name = parts[2]
        user_id = message.from_user.id
        
        # Validate time format
        time_format = parse_time_format(time_str)
        if not time_format:
            await message.reply_text(
                "❌ Invalid time format\n"
                "Use HH:MM or cron expression (e.g., `0 8 * * *`)"
            )
            return
        
        # Find playlist
        playlist = await scheduler_service.find_playlist(playlist_name)
        if not playlist:
            await message.reply_text(
                f"❌ Playlist '{playlist_name}' not found\n"
                f"Use `/playlists` to see available playlists"
            )
            return
        
        # Create schedule
        result = await scheduler_service.create_schedule(
            playlist_id=playlist["id"],
            time=time_format,
            recurrence="daily",  # Default to daily
            created_by=user_id
        )
        
        if result.get("success"):
            schedule_id = result.get("schedule_id")
            next_trigger = result.get("next_trigger_time", "Unknown")
            
            await message.reply_text(
                f"✅ **Schedule created**\n"
                f"**Playlist**: {playlist_name}\n"
                f"**Time**: {time_format}\n"
                f"**Schedule ID**: `{schedule_id}`\n"
                f"**Next playback**: {next_trigger}"
            )
            logger.info(f"Admin {user_id} created schedule for {playlist_name}")
        else:
            await message.reply_text(
                f"❌ Failed to create schedule: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_schedule: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_unschedule(client: Client, message: Message):
    """
    Cancel a scheduled playlist.
    
    Usage: /unschedule 123
    """
    try:
        # Extract schedule ID from command
        args = message.text.split()
        if len(args) < 2:
            await message.reply_text(
                "❌ **Usage**: `/unschedule <schedule_id>`\n"
                "Use `/schedules` to see all schedules"
            )
            return
        
        try:
            schedule_id = int(args[1])
        except ValueError:
            await message.reply_text("❌ Schedule ID must be a number")
            return
        
        user_id = message.from_user.id
        
        # Delete schedule
        result = await scheduler_service.delete_schedule(schedule_id)
        
        if result.get("success"):
            await message.reply_text(
                f"✅ **Schedule #{schedule_id} cancelled**"
            )
            logger.info(f"Admin {user_id} deleted schedule {schedule_id}")
        else:
            await message.reply_text(
                f"❌ Failed to delete schedule: {result.get('error', 'Not found')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_unschedule: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_schedules(client: Client, message: Message):
    """
    List all scheduled playlists.
    
    Usage: /schedules
    """
    try:
        # Get all active schedules
        schedules = await scheduler_service.list_schedules(active_only=True)
        
        if not schedules:
            await message.reply_text(
                "❌ No schedules configured\n"
                "Use `/schedule` to create a new schedule (admin only)"
            )
            return
        
        # Format schedule list
        response = "📅 **Scheduled Playlists**\n\n"
        for schedule in schedules[:15]:  # Limit to 15 schedules
            schedule_id = schedule.get("id")
            playlist_name = schedule.get("playlist_name", "Unknown")
            time_str = schedule.get("time", "Unknown")
            recurrence = schedule.get("recurrence", "Unknown")
            next_trigger = schedule.get("next_trigger_time", "Unknown")
            
            status = "✅ Active" if schedule.get("enabled") else "⏸️ Inactive"
            
            response += (
                f"**#{schedule_id}** | {status}\n"
                f"  📀 {playlist_name}\n"
                f"  🕐 {time_str} ({recurrence})\n"
                f"  ⏱️ Next: {next_trigger}\n\n"
            )
        
        if len(schedules) > 15:
            response += f"...and {len(schedules) - 15} more\n"
        
        response += "💡 Use `/unschedule <id>` to cancel a schedule"
        
        await message.reply_text(response)
        logger.info(f"User {message.from_user.id} listed schedules")
    except Exception as e:
        logger.error(f"Error in cmd_schedules: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


def register_scheduler_commands(app: Client):
    """
    Register all scheduler command handlers with Pyrogram client.
    
    Args:
        app: Pyrogram Client instance
    """
    # Register /schedule command (admin only)
    app.on_message(filters.command("schedule") & filters.user("admin"))(cmd_schedule)
    
    # Register /unschedule command (admin only)
    app.on_message(filters.command("unschedule") & filters.user("admin"))(cmd_unschedule)
    
    # Register /schedules command
    app.on_message(filters.command("schedules"))(cmd_schedules)
    
    logger.info("Scheduler commands registered successfully")
