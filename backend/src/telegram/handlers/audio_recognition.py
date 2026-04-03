"""
Telegram handler for audio message recognition.

Features:
- Handle voice messages and audio files
- Use Shazam to identify tracks
- Store recognition history
- Enforce rate limiting (10 req/min)
- Integration with RateLimitQueueService for API calls
"""

import logging
from pathlib import Path
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message

from src.services.shazam_service import ShazamService

logger = logging.getLogger(__name__)

# Initialize services
shazam_service = ShazamService()


async def handle_audio_recognition(client: Client, message: Message):
    """
    Handle voice messages and audio files for track identification.

    Supported formats: MP3, WAV, OGG, M4A (max 10 MB)

    Args:
        client: Pyrogram Client instance
        message: Message containing audio or voice
    """
    try:
        user_id = message.from_user.id
        channel_id = message.chat.id

        # Show processing indicator (immediate response - not queued)
        status_msg = await message.reply_text("🔍 **Analyzing audio...**")

        # Download audio file using direct API call (user-facing, needs to be fast)
        audio_file = None
        file_name = None

        if message.voice:
            # Voice message
            file_name = f"voice_{message.message_id}"
            audio_file = await client.download_media(
                message,
                file_name=file_name
            )
        elif message.audio:
            # Audio file
            file_name = f"audio_{message.message_id}"
            audio_file = await client.download_media(
                message,
                file_name=file_name
            )
        else:
            await status_msg.edit_text("❌ No audio file detected")
            return
        
        # Validate file size (max 10 MB)
        file_size = Path(audio_file).stat().st_size if audio_file else 0
        if file_size > 10 * 1024 * 1024:  # 10 MB
            await status_msg.edit_text("❌ Audio file too large (max 10 MB)")
            if audio_file and Path(audio_file).exists():
                Path(audio_file).unlink()
            return
        
        # Validate format
        valid_formats = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
        file_ext = Path(audio_file).suffix.lower() if audio_file else ""
        
        if file_ext not in valid_formats:
            await status_msg.edit_text(
                f"❌ Unsupported format: {file_ext}\n"
                f"Supported: MP3, WAV, OGG, M4A, FLAC"
            )
            if audio_file and Path(audio_file).exists():
                Path(audio_file).unlink()
            return
        
        # Call Shazam service
        result = await shazam_service.identify_track(
            audio_file=audio_file,
            user_id=user_id,
            channel_id=channel_id
        )
        
        # Cleanup downloaded file
        if audio_file and Path(audio_file).exists():
            try:
                Path(audio_file).unlink()
            except Exception as e:
                logger.warning(f"Failed to cleanup audio file: {e}")
        
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            if result.get("rate_limited"):
                retry_after = result.get("retry_after")
                wait_hint = f"Please wait ~{retry_after}s" if retry_after else "Please wait a moment"
                await status_msg.edit_text(
                    "❌ **Rate limit exceeded**\n"
                    f"{wait_hint} before trying again (10 req/min limit)"
                )
            elif "no match" in error_msg.lower():
                await status_msg.edit_text(
                    "❌ **No match found**\n"
                    "Could not identify this track. Try with a clearer audio sample."
                )
            else:
                await status_msg.edit_text(f"❌ Recognition failed: {error_msg}")
            logger.warning(f"Shazam recognition failed for user {user_id}: {error_msg}")
            return
        
        # Format recognition result
        track_id = result.get("track_id")
        artist = result.get("artist", "Unknown")
        title = result.get("title", "Unknown")
        confidence = result.get("confidence", 0.0)
        album = result.get("album", "Unknown")
        release_year = result.get("release_year", "Unknown")
        
        # Create response message
        confidence_pct = confidence * 100
        confidence_bar = "█" * int(confidence_pct / 5) + "░" * (20 - int(confidence_pct / 5))
        
        response = (
            f"✅ **Track Identified**\n\n"
            f"🎵 **{title}**\n"
            f"🎤 **Artist**: {artist}\n"
            f"💿 **Album**: {album}\n"
            f"📅 **Year**: {release_year}\n\n"
            f"📊 **Confidence**: {confidence_bar} {confidence_pct:.0f}%\n"
            f"📌 **ID**: `{track_id}`"
        )
        
        await status_msg.edit_text(response)
        logger.info(
            f"User {user_id} successfully identified: {artist} - {title} "
            f"(confidence: {confidence_pct:.0f}%)"
        )
    
    except Exception as e:
        logger.error(f"Error in handle_audio_recognition: {e}", exc_info=True)
        await message.reply_text(f"❌ Error: {str(e)}")


async def handle_audio_upload(client: Client, message: Message):
    """
    Handle audio file uploads (documents with audio MIME type).
    
    Args:
        client: Pyrogram Client instance
        message: Message containing document
    """
    try:
        
        # Check if document is audio
        if not message.document:
            return
        
        mime_type = message.document.mime_type or ""
        valid_audio_mimes = {
            "audio/mpeg",      # MP3
            "audio/wav",       # WAV
            "audio/ogg",       # OGG
            "audio/mp4",       # M4A
            "audio/x-flac",    # FLAC
            "audio/flac"
        }
        
        if mime_type not in valid_audio_mimes:
            return
        
        # Forward to audio recognition handler
        await handle_audio_recognition(client, message)
    
    except Exception as e:
        logger.error(f"Error in handle_audio_upload: {e}", exc_info=True)


def register_audio_handlers(app: Client):
    """
    Register audio message handlers with Pyrogram client.

    Args:
        app: Pyrogram Client instance
    """
    # Handle voice messages
    app.on_message(filters.voice)(handle_audio_recognition)

    # Handle audio files
    app.on_message(filters.audio)(handle_audio_recognition)

    # Handle document uploads (audio files)
    app.on_message(filters.document)(handle_audio_upload)

    logger.info("Audio recognition handlers registered successfully")


async def send_recognition_result_queued(
    client: Client,
    chat_id: int,
    result: dict,
    account_id: Optional[str] = None,
):
    """
    Отправить результат распознавания через очередь (пример интеграции).

    Эта функция демонстрирует использование RateLimitQueueService
    для API вызовов которые могут быть выполнены асинхронно.

    Args:
        client: Pyrogram Client instance
        chat_id: ID чата для отправки результата
        result: Результат распознавания от ShazamService
        account_id: ID аккаунта для rate limiting

    Note:
        Для немедленных ответов пользователю используйте прямой API вызов.
        Для фоновых задач и массовых рассылок используйте очередь.
    """
    from src.services.rate_limit_queue_service import RequestType, RequestPriority
    from src.services.telegram_rate_limiter import telegram_api_queue

    # Формируем сообщение
    track_id = result.get("track_id", "unknown")
    artist = result.get("artist", "Unknown")
    title = result.get("title", "Unknown")
    confidence = result.get("confidence", 0.0)
    album = result.get("album", "Unknown")
    release_year = result.get("release_year", "Unknown")

    confidence_pct = confidence * 100
    confidence_bar = "█" * int(confidence_pct / 5) + "░" * (20 - int(confidence_pct / 5))

    response = (
        f"✅ **Track Identified**\n\n"
        f"🎵 **{title}**\n"
        f"🎤 **Artist**: {artist}\n"
        f"💿 **Album**: {album}\n"
        f"📅 **Year**: {release_year}\n\n"
        f"📊 **Confidence**: {confidence_bar} {confidence_pct:.0f}%\n"
        f"📌 **ID**: `{track_id}`"
    )

    try:
        # Используем queue для API вызова (низкий приоритет, фоновая задача)
        await telegram_api_queue.execute_api_call(
            client=client,
            method="send_message",
            params={
                "chat_id": chat_id,
                "text": response,
            },
            request_type=RequestType.BACKGROUND_SYNC,
            account_id=account_id,
            priority=RequestPriority.LOW,
        )

        logger.info(
            f"Recognition result sent via queue for chat {chat_id}: "
            f"{artist} - {title}"
        )

    except Exception as e:
        logger.error(f"Failed to send queued result for chat {chat_id}: {e}")
        # Fallback: отправляем напрямую
        try:
            await client.send_message(chat_id, response)
        except Exception as fallback_error:
            logger.error(f"Fallback send also failed: {fallback_error}")


# Экспорт вспомогательных функций для использования в других модулях
__all__ = [
    "register_audio_handlers",
    "handle_audio_recognition",
    "handle_audio_upload",
    "send_recognition_result_queued",  # Пример интеграции с очередью
]
