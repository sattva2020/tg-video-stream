"""
AyuGram Client - PyTgCalls-compatible interface.

This module provides the main AyuGramClient class that implements a
PyTgCalls-compatible interface for interacting with AyuGram's voice/video
call functionality.

The client accepts a Pyrogram or Telethon client and provides async methods
for joining/leaving group calls, managing streams, and controlling playback.

Example:
    >>> from ayugram import AyuGramClient
    >>> from pyrogram import Client
    >>>
    >>> app = Client("my_account", api_id=123, api_hash="abc")
    >>> client = AyuGramClient(app)
    >>>
    >>> await client.start()
    >>> await client.join_group_call(chat_id, stream)
    >>> await client.idle()
"""

import logging
from typing import Union, Optional, Any

# Try to import Pyrogram client
try:
    from pyrogram import Client as PyrogramClient
    PYROGRAM_AVAILABLE = True
except ImportError:
    PYROGRAM_AVAILABLE = False
    PyrogramClient = Any  # type: ignore

# Try to import Telethon client
try:
    from telethon import TelegramClient as TelethonClient
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False
    TelethonClient = Any  # type: ignore

from ayugram.types import AudioPiped, AudioVideoPiped, StreamType
from ayugram.exceptions import AyuGramError, CallError, ConnectionError

logger = logging.getLogger("ayugram.client")


class AyuGramClient:
    """
    PyTgCalls-compatible client for AyuGram voice/video calls.

    This client wraps a Pyrogram or Telethon client and provides a
    PyTgCalls-compatible interface for voice/video call operations.

    The client manages:
    - Group call join/leave operations
    - Stream playback (audio/video)
    - Connection lifecycle (start/stop/idle)

    Attributes:
        _app: The underlying Pyrogram/Telethon client instance
        _is_started: Whether the client has been started
        _active_calls: Dictionary tracking active group calls

    Example:
        >>> from ayugram import AyuGramClient
        >>> from pyrogram import Client
        >>> from ayugram.types import AudioVideoPiped
        >>>
        >>> # Initialize with Pyrogram client
        >>> app = Client("my_account", api_id=123, api_hash="abc")
        >>> client = AyuGramClient(app)
        >>>
        >>> # Start the client
        >>> await client.start()
        >>>
        >>> # Join a voice chat with a stream
        >>> stream = AudioVideoPiped("https://example.com/video.mp4")
        >>> await client.join_group_call(chat_id=-1001234567890, stream=stream)
        >>>
        >>> # Keep the client running
        >>> await client.idle()
    """

    def __init__(self, app: Union[PyrogramClient, TelethonClient]):
        """
        Initialize AyuGramClient with a Pyrogram or Telethon client.

        The client accepts either a Pyrogram or Telethon client instance
        and uses it for Telegram API interactions.

        Args:
            app: Pyrogram or Telethon client instance

        Raises:
            TypeError: If the provided client is not a supported type

        Example:
            >>> from pyrogram import Client
            >>> from ayugram import AyuGramClient
            >>>
            >>> app = Client("my_account", api_id=123, api_hash="abc")
            >>> client = AyuGramClient(app)

        Note:
            The client must be started before joining group calls.
            Use await client.start() to initialize the connection.
        """
        # Validate client type
        is_pyrogram = PYROGRAM_AVAILABLE and isinstance(app, PyrogramClient)
        is_telethon = TELETHON_AVAILABLE and isinstance(app, TelethonClient)

        if not (is_pyrogram or is_telethon):
            raise TypeError(
                f"Expected Pyrogram or Telethon client, got {type(app).__name__}. "
                f"Supported types: pyrogram.Client, telethon.TelegramClient"
            )

        self._app = app
        self._is_started = False
        self._active_calls: dict = {}

        # Log which client type we're using
        if is_pyrogram:
            self._client_type = "pyrogram"
            logger.info("AyuGramClient initialized with Pyrogram client")
        else:
            self._client_type = "telethon"
            logger.info("AyuGramClient initialized with Telethon client")

    async def start(self):
        """
        Start the client and establish connection to Telegram servers.

        This method initializes the underlying Pyrogram/Telethon client
        and establishes a connection to Telegram servers.

        Raises:
            ConnectionError: If connection to Telegram fails
            AyuGramError: If client is already started

        Example:
            >>> client = AyuGramClient(app)
            >>> await client.start()
            >>> print("Client started successfully")
        """
        if self._is_started:
            raise AyuGramError("Client is already started")

        try:
            logger.info("Starting AyuGramClient...")

            # Start the underlying client
            if hasattr(self._app, 'start'):
                # Both Pyrogram and Telethon have a start() method
                await self._app.start()
            else:
                raise AyuGramError("Underlying client does not have a start() method")

            self._is_started = True
            logger.info("AyuGramClient started successfully")

        except ConnectionError as e:
            logger.error(f"Failed to start AyuGramClient: {e}")
            raise ConnectionError(f"Failed to connect to Telegram: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error starting AyuGramClient: {e}")
            raise AyuGramError(f"Failed to start client: {e}") from e

    async def stop(self):
        """
        Stop the client and close all connections.

        This method stops the underlying client and closes all active
        group calls. All active streams will be terminated.

        Raises:
            AyuGramError: If client is not started

        Example:
            >>> await client.stop()
            >>> print("Client stopped")
        """
        if not self._is_started:
            raise AyuGramError("Client is not started")

        try:
            logger.info("Stopping AyuGramClient...")

            # Leave all active calls
            if self._active_calls:
                logger.info(f"Leaving {len(self._active_calls)} active calls")
                for chat_id in list(self._active_calls.keys()):
                    try:
                        await self.leave_group_call(chat_id)
                    except Exception as e:
                        logger.warning(f"Error leaving call for {chat_id}: {e}")

            # Stop the underlying client
            if hasattr(self._app, 'stop'):
                await self._app.stop()
            else:
                raise AyuGramError("Underlying client does not have a stop() method")

            self._is_started = False
            logger.info("AyuGramClient stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping AyuGramClient: {e}")
            raise AyuGramError(f"Failed to stop client: {e}") from e

    async def idle(self):
        """
        Keep the client running indefinitely.

        This method blocks until the client is stopped. It's useful
        for keeping the script running while handling voice chats.

        Raises:
            AyuGramError: If client is not started

        Example:
            >>> await client.start()
            >>> await client.idle()  # Blocks until stopped
        """
        if not self._is_started:
            raise AyuGramError("Client is not started")

        try:
            logger.info("AyuGramClient entering idle mode")

            # Use the underlying client's idle method if available
            if hasattr(self._app, 'idle'):
                await self._app.idle()
            else:
                # Fallback: run forever until interrupted
                import asyncio
                try:
                    await asyncio.Event().wait()
                except (asyncio.CancelledError, KeyboardInterrupt):
                    logger.info("Idle mode interrupted")

        except Exception as e:
            logger.error(f"Error in idle mode: {e}")
            raise AyuGramError(f"Idle mode failed: {e}") from e

    async def join_group_call(
        self,
        chat_id: Union[int, str],
        stream: StreamType,
        join_as: Optional[Union[int, str]] = None,
        invite_hash: Optional[str] = None,
    ):
        """
        Join a group call and start streaming.

        This method joins a voice chat in the specified chat and starts
        streaming the provided audio/video content.

        Args:
            chat_id: Chat ID or username where the voice chat is located
            stream: Stream configuration (AudioPiped or AudioVideoPiped)
            join_as: Optional user ID to join as (for channels)
            invite_hash: Optional invite hash for restricted voice chats

        Raises:
            CallError: If joining the call fails
            AyuGramError: If client is not started or stream type is invalid

        Example:
            >>> from ayugram.types import AudioVideoPiped
            >>>
            >>> stream = AudioVideoPiped("https://example.com/video.mp4")
            >>> await client.join_group_call(-1001234567890, stream)
        """
        if not self._is_started:
            raise AyuGramError("Client is not started")

        if not isinstance(stream, (AudioPiped, AudioVideoPiped)):
            raise AyuGramError(
                f"Invalid stream type: {type(stream).__name__}. "
                f"Expected AudioPiped or AudioVideoPiped"
            )

        try:
            logger.info(f"Joining group call for chat_id={chat_id}")

            # TODO: Implement actual AyuGram RPC call in subsequent subtasks
            # For now, just track the call as active
            self._active_calls[str(chat_id)] = {
                "stream": stream,
                "join_as": join_as,
                "invite_hash": invite_hash,
            }

            logger.info(f"Successfully joined group call for chat_id={chat_id}")

        except CallError as e:
            logger.error(f"Failed to join group call: {e}")
            raise CallError(f"Failed to join call for {chat_id}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error joining group call: {e}")
            raise CallError(f"Unexpected error joining call: {e}") from e

    async def leave_group_call(self, chat_id: Union[int, str]):
        """
        Leave a group call and stop streaming.

        This method leaves the voice chat in the specified chat and
        stops any active stream.

        Args:
            chat_id: Chat ID or username where the voice chat is located

        Raises:
            CallError: If leaving the call fails
            AyuGramError: If client is not started

        Example:
            >>> await client.leave_group_call(-1001234567890)
        """
        if not self._is_started:
            raise AyuGramError("Client is not started")

        try:
            logger.info(f"Leaving group call for chat_id={chat_id}")

            # TODO: Implement actual AyuGram RPC call in subsequent subtasks
            # For now, just remove from active calls
            if str(chat_id) in self._active_calls:
                del self._active_calls[str(chat_id)]
                logger.info(f"Successfully left group call for chat_id={chat_id}")
            else:
                logger.warning(f"No active call found for chat_id={chat_id}")

        except CallError as e:
            logger.error(f"Failed to leave group call: {e}")
            raise CallError(f"Failed to leave call for {chat_id}: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error leaving group call: {e}")
            raise CallError(f"Unexpected error leaving call: {e}") from e

    @property
    def is_started(self) -> bool:
        """
        Check if the client is started.

        Returns:
            True if the client is started, False otherwise

        Example:
            >>> if client.is_started:
            ...     print("Client is running")
        """
        return self._is_started

    @property
    def active_calls(self) -> dict:
        """
        Get all active group calls.

        Returns:
            Dictionary mapping chat IDs to their call info

        Example:
            >>> calls = client.active_calls
            >>> print(f"Active calls: {len(calls)}")
        """
        return self._active_calls.copy()


__all__ = ["AyuGramClient"]
