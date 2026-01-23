"""
Telegram handler for message capture and chat overlay.

Features:
- Capture text messages from Telegram chats
- Store messages for overlay display
- WebSocket broadcast for real-time updates
- Filter inappropriate content via moderation service
- Support anonymous and authenticated users
"""

import logging
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message

from src.infrastructure.persistence.repositories.sqlalchemy_stream_repository import SQLAlchemyStreamRepository
from src.infrastructure.persistence.repositories.sqlalchemy_interaction_repository import InteractionRepository
from src.models.interaction import ChatMessage as ChatMessageORM, ChatMessageStatus
from src.api.websocket import notify_chat_message

logger = logging.getLogger(__name__)

# Initialize repositories
stream_repository = SQLAlchemyStreamRepository()
interaction_repository = InteractionRepository()


async def handle_text_message(client: Client, message: Message):
    """
    Handle text messages from Telegram chats for overlay display.

    Captures messages and stores them for the chat overlay feature.
    Messages are broadcast via WebSocket for real-time display.

    Args:
        client: Pyrogram Client instance
        message: Message containing text
    """
    try:
        # Skip empty messages
        if not message.text:
            return

        chat_id = message.chat.id
        telegram_message_id = message.message_id

        # Get the stream associated with this chat
        from src.domain.value_objects.chat_id import ChatId
        stream = await stream_repository.get_by_chat_id(ChatId(chat_id))

        if not stream:
            # Stream not found - this chat is not registered for overlay
            logger.debug(f"No stream found for chat_id {chat_id}, skipping message capture")
            return

        stream_id = str(stream.id)

        # Extract user information
        user_id = None
        author_name = "Anonymous"
        author_avatar_url = None

        if message.from_user:
            user_id = message.from_user.id

            # Get display name (prefer first_name + last_name, fallback to username)
            if message.from_user.first_name:
                author_name = message.from_user.first_name
                if message.from_user.last_name:
                    author_name += f" {message.from_user.last_name}"
            elif message.from_user.username:
                author_name = message.from_user.username

            # Get avatar URL if available
            if message.from_user.photo:
                try:
                    # Get user profile photo
                    photos = await client.get_profile_photos(user_id)
                    if photos and photos.total_count > 0:
                        # Get the largest photo
                        photo = photos.photos[0]
                        if photo and len(photo) > 0:
                            file_id = photo[-1].file_id
                            author_avatar_url = f"tg://avatar?id={file_id}"
                except Exception as e:
                    logger.warning(f"Failed to get avatar for user {user_id}: {e}")

        # Get message timestamp
        original_timestamp = datetime.fromtimestamp(message.date) if message.date else None

        # Check for moderation - filter inappropriate content
        from src.services.moderation_service import ModerationService
        moderation_service = ModerationService()

        moderation_result = await moderation_service.check_content(message.text)
        is_filtered = moderation_result.get("is_filtered", False)
        filter_reason = moderation_result.get("filter_reason") if is_filtered else None

        # Create ChatMessage ORM record
        chat_message = ChatMessageORM(
            stream_id=stream.id,
            author_id=None,  # Will be linked if user exists in system
            telegram_user_id=user_id,
            author_name=author_name,
            author_avatar_url=author_avatar_url,
            content=message.text,
            message_status=ChatMessageStatus.PENDING if not is_filtered else ChatMessageStatus.HIDDEN,
            telegram_message_id=telegram_message_id,
            original_timestamp=original_timestamp,
            is_filtered=is_filtered,
            filter_reason=filter_reason,
            is_flagged=False
        )

        # Save to database
        await interaction_repository.save_chat_message(chat_message)
        message_id = str(chat_message.id)

        # Broadcast via WebSocket if not filtered
        if not is_filtered:
            await notify_chat_message(
                stream_id=stream_id,
                message_id=message_id,
                author_name=author_name,
                content=message.text,
                channel_id=str(chat_id)
            )
            logger.info(
                f"Captured message from {author_name} (user_id={user_id}) "
                f"in chat {chat_id} for stream {stream_id}"
            )
        else:
            logger.info(
                f"Filtered message from {author_name} (user_id={user_id}) "
                f"in chat {chat_id}. Reason: {filter_reason}"
            )

    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}", exc_info=True)


async def handle_edited_message(client: Client, message: Message):
    """
    Handle edited messages from Telegram chats.

    Updates the existing message in the database and broadcasts the change.

    Args:
        client: Pyrogram Client instance
        message: Edited message
    """
    try:
        if not message.text:
            return

        chat_id = message.chat.id
        telegram_message_id = message.message_id

        # Get the stream associated with this chat
        from src.domain.value_objects.chat_id import ChatId
        stream = await stream_repository.get_by_chat_id(ChatId(chat_id))

        if not stream:
            return

        stream_id = str(stream.id)

        # Find existing message by telegram_message_id
        existing_message = await interaction_repository.get_chat_message_by_telegram_id(
            telegram_message_id=telegram_message_id,
            stream_id=stream.id
        )

        if not existing_message:
            # Message not found, treat as new message
            await handle_text_message(client, message)
            return

        # Check moderation for edited content
        from src.services.moderation_service import ModerationService
        moderation_service = ModerationService()

        moderation_result = await moderation_service.check_content(message.text)
        is_filtered = moderation_result.get("is_filtered", False)
        filter_reason = moderation_result.get("filter_reason") if is_filtered else None

        # Update message content
        existing_message.content = message.text
        existing_message.is_filtered = is_filtered
        existing_message.filter_reason = filter_reason

        if is_filtered:
            existing_message.message_status = ChatMessageStatus.HIDDEN

        # Save updates
        await interaction_repository.save_chat_message(existing_message)

        # Broadcast update via WebSocket
        if not is_filtered:
            await notify_chat_message(
                stream_id=stream_id,
                message_id=str(existing_message.id),
                author_name=existing_message.author_name,
                content=message.text,
                channel_id=str(chat_id)
            )
            logger.info(f"Updated message {existing_message.id} from chat {chat_id}")

    except Exception as e:
        logger.error(f"Error in handle_edited_message: {e}", exc_info__)


def register_message_handlers(app: Client):
    """
    Register message capture handlers with Pyrogram client.

    Args:
        app: Pyrogram Client instance
    """
    # Handle text messages (private chats, groups, channels)
    app.on_message(filters.text & ~filters.edited)(handle_text_message)

    # Handle edited messages
    app.on_message(filters.text & filters.edited)(handle_edited_message)

    logger.info("Message capture handlers registered successfully")
