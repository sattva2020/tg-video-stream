"""
Call control RPC methods for managing audio/video stream operations.

Provides JSON-RPC methods to start, stop, and restart call streams
using the StreamController service.
"""
import logging
from typing import Optional

from fastapi_websocket_rpc import RpcMethodsBase

from src.services.stream_controller import StreamController


logger = logging.getLogger(__name__)


class CallControlMethods(RpcMethodsBase):
    """
    JSON-RPC methods for call control operations.

    This class provides methods to control stream lifecycle (start/stop/restart)
    and retrieve stream logs. All operations are performed through the
    StreamController service which manages Docker containers or systemd services.

    Note: StreamController operations affect a global stream, not per-channel.
    The channel_id parameter is validated for API consistency but not used
    in stream operations.
    """

    # Valid quality presets for stream
    VALID_QUALITIES = ["360p", "480p", "720p", "1080p", "1440p", "2160p"]

    def __init__(self, stream_controller: StreamController, user_id: Optional[str] = None):
        """
        Initialize CallControlMethods with required dependencies.

        Args:
            stream_controller: StreamController instance for stream operations
            user_id: Optional user identifier from JWT payload for logging
        """
        super().__init__()
        self.stream_controller = stream_controller
        self.user_id = user_id
        self.logger = logger

    def _validate_channel_id(self, channel_id: int) -> None:
        """
        Validate channel_id parameter.

        Args:
            channel_id: Channel identifier to validate

        Raises:
            ValueError: If channel_id is not a positive integer
        """
        if not isinstance(channel_id, int) or channel_id <= 0:
            raise ValueError(f"channel_id must be a positive integer, got {channel_id}")

    def _validate_quality(self, quality: str) -> None:
        """
        Validate quality parameter.

        Args:
            quality: Quality preset string to validate

        Raises:
            ValueError: If quality is not in valid presets list
        """
        if quality not in self.VALID_QUALITIES:
            raise ValueError(
                f"Invalid quality '{quality}'. Must be one of: {', '.join(self.VALID_QUALITIES)}"
            )

    async def start_call(self, channel_id: int, quality: str = "720p") -> dict:
        """
        Start a call stream.

        Starts the audio/video stream using the configured StreamController.
        The quality parameter is validated but may not be used by all
        StreamController implementations (Docker/systemd).

        Args:
            channel_id: Positive integer channel identifier
            quality: Stream quality preset (default: "720p")

        Returns:
            Dict with operation result:
                - success (bool): True if stream started successfully
                - channel_id (int): The channel ID from request
                - quality (str): Quality preset used
                - message (str): Success or error message

        Raises:
            ValueError: If channel_id or quality parameters are invalid
        """
        self._validate_channel_id(channel_id)
        self._validate_quality(quality)

        self.logger.info(
            "Starting call for user=%s channel=%s quality=%s",
            self.user_id,
            channel_id,
            quality,
        )

        # Start stream via StreamController
        # Note: StreamController.start_stream() does not use channel_id
        # It controls a single global stream (Docker container or systemd service)
        success = self.stream_controller.start_stream()

        message = "Call started" if success else "Failed to start call"

        self.logger.info(
            "Start call result for user=%s channel=%s: %s",
            self.user_id,
            channel_id,
            message,
        )

        return {
            "success": success,
            "channel_id": channel_id,
            "quality": quality,
            "message": message,
        }

    async def stop_call(self, channel_id: int) -> dict:
        """
        Stop a call stream.

        Stops the audio/video stream using the configured StreamController.

        Args:
            channel_id: Positive integer channel identifier

        Returns:
            Dict with operation result:
                - success (bool): True if stream stopped successfully
                - channel_id (int): The channel ID from request
                - message (str): Success or error message

        Raises:
            ValueError: If channel_id parameter is invalid
        """
        self._validate_channel_id(channel_id)

        self.logger.info(
            "Stopping call for user=%s channel=%s",
            self.user_id,
            channel_id,
        )

        # Stop stream via StreamController
        # Note: StreamController.stop_stream() does not use channel_id
        success = self.stream_controller.stop_stream()

        message = "Call stopped" if success else "Failed to stop call"

        self.logger.info(
            "Stop call result for user=%s channel=%s: %s",
            self.user_id,
            channel_id,
            message,
        )

        return {
            "success": success,
            "channel_id": channel_id,
            "message": message,
        }

    async def restart_call(self, channel_id: int) -> dict:
        """
        Restart a call stream.

        Restarts the audio/video stream using the configured StreamController.
        This is equivalent to stopping and immediately starting the stream.

        Args:
            channel_id: Positive integer channel identifier

        Returns:
            Dict with operation result:
                - success (bool): True if stream restarted successfully
                - channel_id (int): The channel ID from request
                - message (str): Success or error message

        Raises:
            ValueError: If channel_id parameter is invalid
        """
        self._validate_channel_id(channel_id)

        self.logger.info(
            "Restarting call for user=%s channel=%s",
            self.user_id,
            channel_id,
        )

        # Restart stream via StreamController
        # Note: StreamController.restart_stream() does not use channel_id
        success = self.stream_controller.restart_stream()

        message = "Call restarted" if success else "Failed to restart call"

        self.logger.info(
            "Restart call result for user=%s channel=%s: %s",
            self.user_id,
            channel_id,
            message,
        )

        return {
            "success": success,
            "channel_id": channel_id,
            "message": message,
        }

    async def get_stream_logs(self, channel_id: int, lines: int = 100) -> dict:
        """
        Retrieve recent stream logs.

        Gets the most recent log lines from the stream container or service.
        Logs are global to the stream, not specific to the channel.

        Args:
            channel_id: Positive integer channel identifier
            lines: Number of log lines to retrieve (default: 100)

        Returns:
            Dict with operation result:
                - success (bool): True if logs retrieved successfully
                - channel_id (int): The channel ID from request
                - lines (int): Number of lines requested
                - logs (list[str]): List of log lines
                - message (str): Status message

        Raises:
            ValueError: If channel_id or lines parameters are invalid
        """
        self._validate_channel_id(channel_id)

        if not isinstance(lines, int) or lines <= 0:
            raise ValueError(f"lines must be a positive integer, got {lines}")

        self.logger.info(
            "Fetching stream logs for user=%s channel=%s lines=%s",
            self.user_id,
            channel_id,
            lines,
        )

        # Get logs via StreamController
        # Note: StreamController.get_logs() does not use channel_id
        # Logs are global to the stream container/service
        logs = self.stream_controller.get_logs(lines=lines)

        success = len(logs) > 0 or lines == 0

        message = f"Retrieved {len(logs)} log lines" if success else "Failed to retrieve logs"

        self.logger.info(
            "Stream logs result for user=%s channel=%s: %s",
            self.user_id,
            channel_id,
            message,
        )

        return {
            "success": success,
            "channel_id": channel_id,
            "lines": lines,
            "logs": logs,
            "message": message,
        }
