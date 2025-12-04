"""
Telegram command handlers for multi-channel management.

Commands:
- /channels: List all configured Telegram channels
- /channel {id|name}: Select active channel for subsequent commands
- /channelinfo: Show current channel settings
- /channelstatus: Show playback status for all channels

User Story 11 (Multi-channel Support):
Администратор может управлять несколькими Telegram каналами
одновременно с независимыми настройками воспроизведения.
"""

import logging
from typing import Optional, List, Dict, Any

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from src.services.channel_service import ChannelService
from src.services.playback_service import PlaybackService
from src.middleware.auth import require_admin

logger = logging.getLogger(__name__)

# Initialize services
channel_service = ChannelService()
playback_service = PlaybackService()

# In-memory user channel selection (could be persisted to Redis/DB)
_user_channel_selection: Dict[int, int] = {}


def get_user_active_channel(user_id: int, default_channel_id: int) -> int:
    """
    Get user's currently selected channel.
    
    Args:
        user_id: Telegram user ID
        default_channel_id: Default channel if none selected
        
    Returns:
        Channel ID for the user
    """
    return _user_channel_selection.get(user_id, default_channel_id)


def set_user_active_channel(user_id: int, channel_id: int) -> None:
    """
    Set user's active channel for commands.
    
    Args:
        user_id: Telegram user ID
        channel_id: Channel ID to set as active
    """
    _user_channel_selection[user_id] = channel_id
    logger.info(f"User {user_id} selected channel {channel_id}")


async def cmd_channels(client: Client, message: Message):
    """
    List all configured Telegram channels.
    
    Usage: /channels
    """
    try:
        user_id = message.from_user.id
        
        # Get all channels (admin sees all, users see only accessible)
        channels = await channel_service.list_channels(user_id=user_id)
        
        if not channels:
            await message.reply_text(
                "❌ **Нет настроенных каналов**\n"
                "Используйте панель администратора для добавления каналов."
            )
            return
        
        # Get current selection
        current_channel_id = get_user_active_channel(user_id, message.chat.id)
        
        # Format channel list
        response = "📺 **Доступные каналы**\n\n"
        
        buttons = []
        for idx, channel in enumerate(channels[:10], 1):
            is_active = channel["id"] == current_channel_id
            status_emoji = "✅" if is_active else "⭕"
            playback_status = channel.get("is_playing", False)
            playback_emoji = "▶️" if playback_status else "⏸️"
            
            response += (
                f"{status_emoji} **{channel['name']}**\n"
                f"   📍 ID: `{channel['id']}`\n"
                f"   {playback_emoji} {channel.get('status', 'Остановлен')}\n\n"
            )
            
            # Create inline button for quick selection
            buttons.append(
                InlineKeyboardButton(
                    text=f"{'✓ ' if is_active else ''}{channel['name']}",
                    callback_data=f"select_channel:{channel['id']}"
                )
            )
        
        if len(channels) > 10:
            response += f"...и ещё {len(channels) - 10} каналов"
        
        response += "\n💡 Используйте `/channel <id>` для выбора канала"
        
        # Create keyboard with 2 buttons per row
        keyboard_rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
        
        await message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup(keyboard_rows) if buttons else None
        )
        logger.info(f"User {user_id} listed {len(channels)} channels")
        
    except Exception as e:
        logger.error(f"Error in cmd_channels: {e}", exc_info=True)
        await message.reply_text(f"❌ Ошибка: {str(e)}")


async def cmd_channel(client: Client, message: Message):
    """
    Select active channel for subsequent commands.
    
    Usage: /channel <id|name>
    """
    try:
        user_id = message.from_user.id
        
        # Extract channel identifier from command
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            current = get_user_active_channel(user_id, message.chat.id)
            channel_info = await channel_service.get_channel(current)
            
            if channel_info:
                await message.reply_text(
                    f"📺 **Текущий канал**\n\n"
                    f"**Название**: {channel_info['name']}\n"
                    f"**ID**: `{channel_info['id']}`\n\n"
                    f"💡 Используйте `/channel <id>` для смены канала"
                )
            else:
                await message.reply_text(
                    "❌ **Канал не выбран**\n"
                    "Используйте `/channels` для просмотра списка"
                )
            return
        
        channel_identifier = args[1].strip()
        
        # Try to find channel by ID or name
        channel = None
        
        # Try as numeric ID first
        try:
            channel_id = int(channel_identifier)
            channel = await channel_service.get_channel(channel_id)
        except ValueError:
            # Try as name
            channel = await channel_service.get_channel_by_name(channel_identifier)
        
        if not channel:
            await message.reply_text(
                f"❌ Канал '{channel_identifier}' не найден\n"
                f"Используйте `/channels` для просмотра списка"
            )
            return
        
        # Check user access to this channel
        has_access = await channel_service.user_has_access(user_id, channel["id"])
        if not has_access:
            await message.reply_text("❌ У вас нет доступа к этому каналу")
            return
        
        # Set active channel
        set_user_active_channel(user_id, channel["id"])
        
        # Get channel status
        status = await channel_service.get_channel_status(channel["id"])
        
        await message.reply_text(
            f"✅ **Канал выбран**\n\n"
            f"**Название**: {channel['name']}\n"
            f"**ID**: `{channel['id']}`\n"
            f"**Статус**: {status.get('status', 'Неизвестно')}\n\n"
            f"💡 Все последующие команды будут применяться к этому каналу"
        )
        logger.info(f"User {user_id} selected channel {channel['id']}")
        
    except Exception as e:
        logger.error(f"Error in cmd_channel: {e}", exc_info=True)
        await message.reply_text(f"❌ Ошибка: {str(e)}")


async def cmd_channelinfo(client: Client, message: Message):
    """
    Show current channel settings and status.
    
    Usage: /channelinfo [channel_id]
    """
    try:
        user_id = message.from_user.id
        
        # Extract optional channel ID
        args = message.text.split(maxsplit=1)
        if len(args) > 1:
            try:
                channel_id = int(args[1].strip())
            except ValueError:
                await message.reply_text("❌ ID канала должен быть числом")
                return
        else:
            channel_id = get_user_active_channel(user_id, message.chat.id)
        
        # Get channel info
        channel = await channel_service.get_channel(channel_id)
        if not channel:
            await message.reply_text("❌ Канал не найден")
            return
        
        # Get playback settings for this channel
        settings = playback_service.get_settings(user_id, channel_id)
        status = await channel_service.get_channel_status(channel_id)
        
        # Format response
        is_playing = status.get("is_playing", False)
        current_track = status.get("current_track", {})
        
        response = (
            f"📺 **Информация о канале**\n\n"
            f"**Название**: {channel['name']}\n"
            f"**ID**: `{channel['id']}`\n"
            f"**Тип**: {channel.get('type', 'channel')}\n\n"
            f"**▶️ Воспроизведение**\n"
            f"Статус: {'Играет' if is_playing else 'Остановлено'}\n"
        )
        
        if is_playing and current_track:
            response += (
                f"Трек: {current_track.get('title', 'Неизвестно')}\n"
                f"Исполнитель: {current_track.get('artist', 'Неизвестно')}\n"
            )
        
        response += (
            f"\n**⚙️ Настройки**\n"
            f"Скорость: {settings.get('speed', 1.0)}x\n"
            f"Эквалайзер: {settings.get('equalizer_preset', 'flat')}\n"
            f"Автовоспроизведение: {'Да' if settings.get('auto_play', True) else 'Нет'}\n"
            f"Перемешивание: {'Да' if settings.get('shuffle', False) else 'Нет'}\n"
        )
        
        await message.reply_text(response)
        logger.info(f"User {user_id} viewed info for channel {channel_id}")
        
    except Exception as e:
        logger.error(f"Error in cmd_channelinfo: {e}", exc_info=True)
        await message.reply_text(f"❌ Ошибка: {str(e)}")


async def cmd_channelstatus(client: Client, message: Message):
    """
    Show playback status for all accessible channels.
    
    Usage: /channelstatus
    """
    try:
        user_id = message.from_user.id
        
        # Get all accessible channels with status
        channels = await channel_service.list_channels(user_id=user_id)
        
        if not channels:
            await message.reply_text("❌ Нет доступных каналов")
            return
        
        response = "📊 **Статус всех каналов**\n\n"
        
        for channel in channels[:10]:
            status = await channel_service.get_channel_status(channel["id"])
            is_playing = status.get("is_playing", False)
            
            if is_playing:
                track = status.get("current_track", {})
                track_info = track.get("title", "Неизвестно")[:30]
                position = status.get("position_formatted", "0:00")
                emoji = "▶️"
            else:
                track_info = "—"
                position = "—"
                emoji = "⏸️"
            
            response += (
                f"{emoji} **{channel['name']}**\n"
                f"   🎵 {track_info}\n"
                f"   ⏱️ {position}\n\n"
            )
        
        if len(channels) > 10:
            response += f"...и ещё {len(channels) - 10} каналов"
        
        await message.reply_text(response)
        logger.info(f"User {user_id} viewed all channel statuses")
        
    except Exception as e:
        logger.error(f"Error in cmd_channelstatus: {e}", exc_info=True)
        await message.reply_text(f"❌ Ошибка: {str(e)}")


async def callback_select_channel(client: Client, callback_query):
    """
    Handle inline button callback for channel selection.
    """
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if not data.startswith("select_channel:"):
            return
        
        channel_id = int(data.split(":")[1])
        
        # Verify access
        has_access = await channel_service.user_has_access(user_id, channel_id)
        if not has_access:
            await callback_query.answer("❌ Нет доступа к этому каналу", show_alert=True)
            return
        
        # Set active channel
        set_user_active_channel(user_id, channel_id)
        
        # Get channel name
        channel = await channel_service.get_channel(channel_id)
        channel_name = channel["name"] if channel else f"ID:{channel_id}"
        
        await callback_query.answer(f"✅ Выбран канал: {channel_name}")
        
        # Update message to reflect selection
        await callback_query.message.edit_text(
            f"✅ **Канал выбран**: {channel_name}\n\n"
            f"Все последующие команды будут применяться к этому каналу.\n"
            f"Используйте `/channels` для смены канала."
        )
        
        logger.info(f"User {user_id} selected channel {channel_id} via callback")
        
    except Exception as e:
        logger.error(f"Error in callback_select_channel: {e}", exc_info=True)
        await callback_query.answer("❌ Ошибка", show_alert=True)


def register_channel_commands(app: Client):
    """
    Register all channel management command handlers with Pyrogram client.
    
    Args:
        app: Pyrogram Client instance
    """
    # Register /channels command
    app.on_message(filters.command("channels"))(cmd_channels)
    
    # Register /channel command
    app.on_message(filters.command("channel"))(cmd_channel)
    
    # Register /channelinfo command
    app.on_message(filters.command("channelinfo"))(cmd_channelinfo)
    
    # Register /channelstatus command
    app.on_message(filters.command("channelstatus"))(cmd_channelstatus)
    
    # Register callback handler for channel selection
    app.on_callback_query(filters.regex(r"^select_channel:\d+$"))(callback_select_channel)
    
    logger.info("Channel management commands registered successfully")
