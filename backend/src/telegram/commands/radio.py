"""
Telegram command handlers for radio stream management.

Commands:
- /addradio {url} {name}: Add internet radio stream (admin only)
- /radio {name}: Play specific radio stream
- /radiolist: List all available radio streams
- /radiostop: Stop radio playback
"""

import logging
from typing import Optional
from urllib.parse import urlparse

from pyrogram import Client, filters
from pyrogram.types import Message

from src.services.radio_service import RadioService
from src.middleware.auth import require_admin

logger = logging.getLogger(__name__)

# Initialize service
radio_service = RadioService()


def is_valid_url(url: str) -> bool:
    """
    Validate if URL is properly formatted.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


async def cmd_addradio(client: Client, message: Message):
    """
    Add a new internet radio stream (admin only).
    
    Usage: /addradio https://stream.example.com/radio.mp3 "My Radio"
    """
    try:
        # Check if admin
        user_id = message.from_user.id
        
        # Parse command arguments
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.reply_text(
                "❌ **Usage**: `/addradio <url> <name>`\n"
                "**Example**: `/addradio https://stream.example.com/radio.mp3 MyRadio`"
            )
            return
        
        url = parts[1]
        name = parts[2]
        
        # Validate URL
        if not is_valid_url(url):
            await message.reply_text(
                "❌ Invalid URL format. Must start with http:// or https://"
            )
            return
        
        # Validate name
        if len(name) < 2 or len(name) > 100:
            await message.reply_text(
                "❌ Stream name must be between 2 and 100 characters"
            )
            return
        
        # Call service
        result = await radio_service.add_stream(
            url=url,
            name=name,
            added_by=user_id
        )
        
        if result.get("success"):
            stream_id = result.get("stream_id")
            await message.reply_text(
                f"✅ **Radio stream added**\n"
                f"**Name**: {name}\n"
                f"**ID**: `{stream_id}`"
            )
            logger.info(f"Admin {user_id} added radio stream: {name}")
        else:
            await message.reply_text(
                f"❌ Failed to add stream: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_addradio: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_radio(client: Client, message: Message):
    """
    Play a specific radio stream.
    
    Usage: /radio MyRadio
    """
    try:
        # Extract stream name from command
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply_text(
                "❌ **Usage**: `/radio <name>`\n"
                "**Tip**: Use `/radiolist` to see available streams"
            )
            return
        
        stream_name = args[1]
        user_id = message.from_user.id
        channel_id = message.chat.id
        
        # Find stream by name
        stream = await radio_service.get_stream_by_name(stream_name)
        if not stream:
            await message.reply_text(
                f"❌ Stream '{stream_name}' not found\n"
                f"Use `/radiolist` to see available streams"
            )
            return
        
        # Start playback
        result = await radio_service.play_stream(
            stream_id=stream["id"],
            user_id=user_id,
            channel_id=channel_id
        )
        
        if result.get("success"):
            await message.reply_text(
                f"🎙️ **Now playing**: {stream['name']}\n"
                f"🌍 **Country**: {stream.get('country', 'Unknown')}\n"
                f"🎵 **Genre**: {stream.get('genre', 'Various')}"
            )
            logger.info(f"User {user_id} started playing radio: {stream_name}")
        else:
            await message.reply_text(
                f"❌ Failed to play stream: {result.get('error', 'Unknown error')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_radio: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_radiolist(client: Client, message: Message):
    """
    List all available radio streams.
    
    Usage: /radiolist
    """
    try:
        # Get all active streams
        streams = await radio_service.list_streams(active_only=True)
        
        if not streams:
            await message.reply_text(
                "❌ No radio streams available\n"
                "Use `/addradio` to add a new stream (admin only)"
            )
            return
        
        # Format stream list
        response = "🎙️ **Available Radio Streams**\n\n"
        for idx, stream in enumerate(streams[:20], 1):  # Limit to 20 streams
            country = stream.get("country", "?")
            genre = stream.get("genre", "Various")
            response += (
                f"{idx}. **{stream['name']}**\n"
                f"   🌍 {country} | 🎵 {genre}\n"
            )
        
        if len(streams) > 20:
            response += f"\n...and {len(streams) - 20} more"
        
        response += "\n\n💡 Use `/radio <name>` to play a stream"
        
        await message.reply_text(response)
        logger.info(f"User {message.from_user.id} listed radio streams")
    except Exception as e:
        logger.error(f"Error in cmd_radiolist: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_radiostop(client: Client, message: Message):
    """
    Stop radio playback.
    
    Usage: /radiostop
    """
    try:
        user_id = message.from_user.id
        channel_id = message.chat.id
        
        # Stop playback
        result = await radio_service.stop_stream(
            user_id=user_id,
            channel_id=channel_id
        )
        
        if result.get("success"):
            await message.reply_text("⏹️ **Radio stopped**")
            logger.info(f"User {user_id} stopped radio playback")
        else:
            await message.reply_text(
                f"❌ Failed to stop: {result.get('error', 'No active stream')}"
            )
    except Exception as e:
        logger.error(f"Error in cmd_radiostop: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


def register_radio_commands(app: Client):
    """
    Register all radio command handlers with Pyrogram client.
    
    Args:
        app: Pyrogram Client instance
    """
    # Register /addradio command (admin only)
    app.on_message(filters.command("addradio") & filters.user("admin"))(cmd_addradio)
    
    # Register /radio command
    app.on_message(filters.command("radio"))(cmd_radio)
    
    # Register /radiolist command
    app.on_message(filters.command("radiolist"))(cmd_radiolist)
    
    # Register /radiostop command
    app.on_message(filters.command("radiostop"))(cmd_radiostop)
    
    logger.info("Radio commands registered successfully")
