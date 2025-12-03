"""
Telegram command handlers for lyrics display.

Commands:
- /lyrics: Get lyrics for current playing track
- /lyrics {artist} {song}: Search lyrics by artist and song
- /lyricscache: Show cache statistics
"""

import logging
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message

from src.services.lyrics_service import LyricsService

logger = logging.getLogger(__name__)

# Initialize service
lyrics_service = LyricsService()


async def cmd_lyrics(client: Client, message: Message):
    """
    Get lyrics for current playing track or search by artist/song.
    
    Usage: /lyrics (for current track)
           /lyrics The Weeknd Blinding Lights
    """
    try:
        user_id = message.from_user.id
        
        # Parse command arguments
        args = message.text.split(maxsplit=1)
        
        if len(args) < 2:
            # Try to get lyrics for currently playing track
            result = await lyrics_service.get_current_track_lyrics(user_id)
        else:
            # Search lyrics by artist and song
            query = args[1]
            parts = query.split(maxsplit=1)
            
            if len(parts) < 2:
                await message.reply_text(
                    "❌ **Usage**: `/lyrics [artist] [song]`\n"
                    "**Examples**:\n"
                    "  `/lyrics` (for currently playing track)\n"
                    "  `/lyrics The Weeknd Blinding Lights`"
                )
                return
            
            artist = parts[0]
            song = parts[1]
            
            result = await lyrics_service.search_lyrics(artist, song)
        
        if not result.get("success"):
            await message.reply_text(
                f"❌ Failed to find lyrics: {result.get('error', 'Not found')}"
            )
            return
        
        lyrics = result.get("lyrics", "")
        artist = result.get("artist", "Unknown")
        title = result.get("title", "Unknown")
        cached = result.get("cached", False)
        expires_at = result.get("expires_at")
        
        # Format lyrics response
        # Telegram has a 4096 character limit per message, so we may need to split
        if len(lyrics) > 3000:
            # Send first part and indicate there's more
            first_part = lyrics[:2900]
            remaining = len(lyrics) - 2900
            
            response = (
                f"🎵 **{title}** by {artist}\n"
                f"{'📦 Cached' if cached else '🔍 Fresh'}\n\n"
                f"{first_part}\n\n"
                f"... ({remaining} more characters)"
            )
        else:
            response = (
                f"🎵 **{title}** by {artist}\n"
                f"{'📦 Cached' if cached else '🔍 Fresh'}\n\n"
                f"{lyrics}"
            )
        
        await message.reply_text(response)
        logger.info(f"User {user_id} fetched lyrics for {artist} - {title}")
    except Exception as e:
        logger.error(f"Error in cmd_lyrics: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def cmd_lyricscache(client: Client, message: Message):
    """
    Show lyrics cache statistics.
    
    Usage: /lyricscache
    """
    try:
        # Get cache statistics
        stats = await lyrics_service.get_cache_statistics()
        
        if not stats.get("success"):
            await message.reply_text(
                f"❌ Failed to get cache stats: {stats.get('error', 'Unknown')}"
            )
            return
        
        total_cached = stats.get("total_cached", 0)
        expired_count = stats.get("expired_count", 0)
        active_count = stats.get("active_count", 0)
        avg_ttl_days = stats.get("avg_ttl_days", 0)
        cache_size_mb = stats.get("cache_size_mb", 0)
        
        response = (
            f"💾 **Lyrics Cache Statistics**\n\n"
            f"📊 **Total Cached**: {total_cached}\n"
            f"✅ **Active**: {active_count}\n"
            f"❌ **Expired**: {expired_count}\n"
            f"📈 **Avg TTL**: {avg_ttl_days} days\n"
            f"💽 **Cache Size**: {cache_size_mb:.2f} MB"
        )
        
        await message.reply_text(response)
        logger.info(f"User {message.from_user.id} viewed lyrics cache stats")
    except Exception as e:
        logger.error(f"Error in cmd_lyricscache: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


def register_lyrics_commands(app: Client):
    """
    Register all lyrics command handlers with Pyrogram client.
    
    Args:
        app: Pyrogram Client instance
    """
    # Register /lyrics command
    app.on_message(filters.command("lyrics"))(cmd_lyrics)
    
    # Register /lyricscache command
    app.on_message(filters.command("lyricscache"))(cmd_lyricscache)
    
    logger.info("Lyrics commands registered successfully")
