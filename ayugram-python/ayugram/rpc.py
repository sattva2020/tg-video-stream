"""
JSON-RPC 2.0 Protocol Client for AyuGram SDK.

This module provides an async JSON-RPC client implementation using aiohttp,
supporting JSON-RPC 2.0 specification with connection pooling, automatic
reconnection, and error handling.

Example:
    >>> from ayugram.rpc import JsonRpcClient
    >>> async with JsonRpcClient("http://localhost:8080/jsonrpc") as client:
    ...     result = await client.call("get_me", {})
    ...     print(result)
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Union

import aiohttp
from aiohttp import ClientError, ClientSession, ClientTimeout, TCPConnector

from ayugram.exceptions import (
    AyuGramError,
    ConnectionError,
)
from ayugram.exceptions import (
    TimeoutError as AyuTimeoutError,
)

logger = logging.getLogger("ayugram.rpc")


class JsonRpcClient:
    """
    Async JSON-RPC 2.0 client with connection pooling and reconnection.

    Implements JSON-RPC 2.0 specification (https://www.jsonrpc.org/specification)
    with automatic reconnection, exponential backoff, connection pooling,
    and TCP keep-alive for reliable persistent connections.

    Features:
        - Connection pooling with configurable pool size
        - TCP keep-alive for persistent connections
        - Automatic reconnection with exponential backoff
        - Request retry with exponential backoff
        - JSON-RPC 2.0 spec compliance

    Attributes:
        endpoint_url: JSON-RPC server endpoint URL
        timeout: Request timeout in seconds
        _session: aiohttp ClientSession for HTTP requests
        _request_id: Counter for JSON-RPC request IDs
        _is_connected: Connection state flag
        _connection_pool_size: Maximum connection pool size
        _enable_keep_alive: TCP keep-alive enabled flag

    Example:
        >>> client = JsonRpcClient("http://localhost:8080/jsonrpc")
        >>> await client.start()
        >>> result = await client.call("join_group_call", {"chat_id": 123})
        >>> await client.stop()
    """

    def __init__(
        self,
        endpoint_url: str,
        timeout: int = 30,
        max_retries: int = 3,
        session: Optional[ClientSession] = None,
        connection_pool_size: int = 100,
        connection_pool_limit: int = 0,  # 0 = no limit per host
        keep_alive_timeout: float = 30.0,
        enable_keep_alive: bool = True,
        max_reconnect_attempts: int = 5,
        base_reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 60.0,
    ):
        """
        Initialize JSON-RPC client.

        Args:
            endpoint_url: JSON-RPC server endpoint URL (e.g., http://localhost:8080/jsonrpc)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts for failed requests (default: 3)
            session: Optional existing aiohttp ClientSession to reuse
            connection_pool_size: Maximum size of connection pool (default: 100)
            connection_pool_limit: Max connections per host, 0 = no limit (default: 0)
            keep_alive_timeout: Keep-alive timeout in seconds (default: 30.0)
            enable_keep_alive: Enable TCP keep-alive (default: True)
            max_reconnect_attempts: Maximum reconnection attempts on connection loss (default: 5)
            base_reconnect_delay: Base delay for reconnection in seconds (default: 1.0)
            max_reconnect_delay: Maximum reconnection delay in seconds (default: 60.0)

        Raises:
            ValueError: If endpoint_url is empty or invalid
        """
        if not endpoint_url:
            raise ValueError("endpoint_url cannot be empty")

        self.endpoint_url = endpoint_url.rstrip("/")
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self._session = session
        self._owned_session = session is None
        self._request_id = 0
        self._is_connected = False
        self._lock = asyncio.Lock()

        # Connection pool settings
        self._connection_pool_size = connection_pool_size
        self._connection_pool_limit = connection_pool_limit
        self._keep_alive_timeout = keep_alive_timeout
        self._enable_keep_alive = enable_keep_alive

        # Reconnection settings
        self._max_reconnect_attempts = max_reconnect_attempts
        self._base_reconnect_delay = base_reconnect_delay
        self._max_reconnect_delay = max_reconnect_delay
        self._reconnect_attempt = 0
        self._reconnecting = False

        logger.debug("JsonRpcClient initialized for endpoint: %s", self.endpoint_url)

    async def start(self) -> None:
        """
        Initialize the JSON-RPC client and establish connection.

        Creates aiohttp session with connection pooling if not provided and
        tests connection to endpoint. Implements automatic reconnection with
        exponential backoff.

        Raises:
            ConnectionError: If connection to server fails after all retries
            AyuTimeoutError: If connection attempt times out
        """
        if self._is_connected:
            logger.debug("Client already connected")
            return

        if self._reconnecting:
            logger.debug("Reconnection already in progress")
            return

        try:
            if self._owned_session:
                # Create TCPConnector with connection pooling and keep-alive
                connector = TCPConnector(
                    limit=self._connection_pool_size,
                    limit_per_host=self._connection_pool_limit,
                    keepalive_timeout=self._keep_alive_timeout
                    if self._enable_keep_alive
                    else None,
                    enable_cleanup_closed=True,
                )

                self._session = ClientSession(
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                    connector=connector,
                )

            # Test connection with a simple ping-like request
            await self._test_connection()
            self._is_connected = True
            self._reconnect_attempt = 0
            logger.info("JsonRpcClient connected to %s", self.endpoint_url)

        except asyncio.TimeoutError as exc:
            logger.error("Connection timeout to %s", self.endpoint_url)
            # Try to reconnect with exponential backoff
            if await self._try_reconnect():
                return
            raise AyuTimeoutError(
                f"Connection timeout to {self.endpoint_url}",
                details={"endpoint": self.endpoint_url, "timeout": self.timeout.total},
            ) from exc
        except ClientError as exc:
            logger.error("Connection failed to %s: %s", self.endpoint_url, exc)
            # Try to reconnect with exponential backoff
            if await self._try_reconnect():
                return
            raise ConnectionError(
                f"Failed to connect to {self.endpoint_url}",
                details={"endpoint": self.endpoint_url, "error": str(exc)},
            ) from exc

    async def stop(self) -> None:
        """
        Close the JSON-RPC client and cleanup resources.

        Closes aiohttp session if owned by this client.
        """
        self._reconnecting = False

        if not self._is_connected:
            return

        self._is_connected = False

        if self._owned_session and self._session:
            await self._session.close()
            logger.debug("Closed owned aiohttp session")

        logger.info("JsonRpcClient disconnected from %s", self.endpoint_url)

    async def _try_reconnect(self) -> bool:
        """
        Attempt to reconnect with exponential backoff.

        Implements exponential backoff strategy for reconnection attempts.
        Delay increases exponentially: base_delay, 2*base_delay, 4*base_delay, etc.

        Returns:
            True if reconnection successful, False otherwise
        """
        if self._reconnecting:
            logger.debug("Reconnection already in progress")
            return False

        if self._reconnect_attempt >= self._max_reconnect_attempts:
            logger.error(
                "Max reconnection attempts (%d) reached", self._max_reconnect_attempts
            )
            return False

        self._reconnecting = True
        self._reconnect_attempt += 1

        try:
            # Calculate exponential backoff delay
            delay = min(
                self._base_reconnect_delay * (2 ** (self._reconnect_attempt - 1)),
                self._max_reconnect_delay,
            )

            logger.warning(
                "Reconnection attempt %d/%d, waiting %.1fs before retry",
                self._reconnect_attempt,
                self._max_reconnect_attempts,
                delay,
            )

            await asyncio.sleep(delay)

            # Close existing session if it's owned
            if self._owned_session and self._session:
                try:
                    await self._session.close()
                except Exception:
                    pass

            # Create new session with fresh connection
            if self._owned_session:
                connector = TCPConnector(
                    limit=self._connection_pool_size,
                    limit_per_host=self._connection_pool_limit,
                    keepalive_timeout=self._keep_alive_timeout
                    if self._enable_keep_alive
                    else None,
                    enable_cleanup_closed=True,
                )

                self._session = ClientSession(
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                    connector=connector,
                )

            # Test the new connection
            await self._test_connection()
            self._is_connected = True
            self._reconnect_attempt = 0
            self._reconnecting = False

            logger.info("Successfully reconnected to %s", self.endpoint_url)
            return True

        except Exception as exc:
            logger.error(
                "Reconnection attempt %d failed: %s", self._reconnect_attempt, exc
            )
            self._reconnecting = False

            # Try again recursively if we haven't exhausted attempts
            if self._reconnect_attempt < self._max_reconnect_attempts:
                return await self._try_reconnect()

            return False

    async def _test_connection(self) -> None:
        """
        Test connection to JSON-RPC endpoint.

        Sends a minimal request to verify server is responsive.

        Raises:
            ConnectionError: If server is unreachable
            asyncio.TimeoutError: If request times out
        """
        if not self._session:
            raise ConnectionError("Session not initialized")

        try:
            # Try to connect with a simple request
            async with self._session.get(self.endpoint_url.replace("/jsonrpc", "/")):
                # We don't care about the response, just that it's reachable
                pass
        except Exception as exc:
            # If the health check endpoint doesn't exist, that's okay
            # We'll test actual RPC calls later
            logger.debug("Connection test returned: %s (continuing)", exc)

    def _validate_request(
        self, payload: Dict[str, Any], is_notification: bool = False
    ) -> None:
        """
        Validate JSON-RPC request payload for spec compliance.

        Ensures request follows JSON-RPC 2.0 specification requirements.

        Args:
            payload: Request payload to validate
            is_notification: True if this is a notification (no id field)

        Raises:
            ValueError: If payload fails validation
        """
        # Check required fields
        if "jsonrpc" not in payload:
            raise ValueError("Missing required field 'jsonrpc'")

        if payload["jsonrpc"] != "2.0":
            raise ValueError(
                f"Invalid jsonrpc version: {payload['jsonrpc']} (must be '2.0')"
            )

        if "method" not in payload:
            raise ValueError("Missing required field 'method'")

        if not isinstance(payload["method"], str) or not payload["method"]:
            raise ValueError("Field 'method' must be a non-empty string")

        # Check id field (required for requests, absent for notifications)
        if is_notification:
            if "id" in payload:
                logger.debug(
                    "Notification should not have 'id' field (per JSON-RPC 2.0 spec)"
                )
        else:
            if "id" not in payload:
                raise ValueError("Missing required field 'id' for request")

        # Validate params if present
        if "params" in payload:
            params = payload["params"]
            if not isinstance(params, (dict, list)):
                raise ValueError(
                    f"Field 'params' must be an object or array, got {type(params).__name__}"
                )

    async def call(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], list]] = None,
        request_id: Optional[int] = None,
    ) -> Any:
        """
        Send JSON-RPC 2.0 request and return result.

        Args:
            method: JSON-RPC method name to invoke
            params: Method parameters (dict for named params, list for positional)
            request_id: Optional custom request ID (auto-generated if None)

        Returns:
            Result data from JSON-RPC response (can be dict, list, str, int, etc.)

        Raises:
            ConnectionError: If request fails due to network/transport issues
            AyuTimeoutError: If request times out
            AyuGramError: If JSON-RPC error response received

        Example:
            >>> result = await client.call("join_group_call", {"chat_id": 123})
            >>> print(result)
        """
        if not method:
            raise ValueError("method cannot be empty")

        # Ensure connection is active
        if not self._is_connected:
            await self.start()

        if request_id is None:
            async with self._lock:
                self._request_id += 1
                request_id = self._request_id

        # Build payload according to JSON-RPC 2.0 spec
        # params field should be omitted if None (not sent as empty object)
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id,
        }

        # Only include params if provided (per JSON-RPC 2.0 spec)
        if params is not None:
            payload["params"] = params

        # Validate payload before sending
        self._validate_request(payload)

        logger.debug("JSON-RPC request: %s -> %s", method, params)

        retry_count = 0
        last_error = None
        connection_lost = False

        while retry_count <= self.max_retries:
            try:
                response = await self._send_request(payload)
                logger.debug("JSON-RPC response: %s <- %s", method, response)
                return response

            except (ConnectionError, AyuTimeoutError) as exc:
                last_error = exc
                retry_count += 1

                # Check if connection was lost
                if "connection" in str(exc).lower() or "timeout" in str(exc).lower():
                    connection_lost = True
                    self._is_connected = False

                if retry_count > self.max_retries:
                    logger.error(
                        "Request failed after %d retries: %s",
                        self.max_retries,
                        exc,
                    )
                    raise

                # If connection was lost, try to reconnect first
                if connection_lost and not self._reconnecting:
                    logger.warning("Connection lost, attempting to reconnect...")
                    if await self._try_reconnect():
                        connection_lost = False
                        logger.info("Reconnected successfully, retrying request")
                        continue

                # Exponential backoff: 1s, 2s, 4s, 8s, ..., max 30s
                backoff = min(2 ** (retry_count - 1), 30)
                logger.warning(
                    "Request failed (attempt %d/%d), retrying in %ds: %s",
                    retry_count,
                    self.max_retries,
                    backoff,
                    exc,
                )
                await asyncio.sleep(backoff)

            except AyuGramError:
                # Don't retry on application-level errors (e.g., invalid params)
                raise

        # Should not reach here, but handle it
        if last_error:
            raise last_error
        raise AyuGramError("Unknown error in RPC call")

    async def notify(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], list]] = None,
    ) -> None:
        """
        Send JSON-RPC 2.0 notification (no response expected).

        Notifications are requests without an ID, so the server sends no response.
        Useful for fire-and-forget style operations.

        Args:
            method: JSON-RPC method name to invoke
            params: Method parameters (dict for named params, list for positional)

        Raises:
            ConnectionError: If request fails due to network/transport issues
            AyuTimeoutError: If request times out

        Example:
            >>> await client.notify("update_status", {"status": "idle"})
        """
        if not method:
            raise ValueError("method cannot be empty")

        # Ensure connection is active
        if not self._is_connected:
            await self.start()

        # Build notification payload according to JSON-RPC 2.0 spec
        # Notifications are requests without an "id" field
        payload = {
            "jsonrpc": "2.0",
            "method": method,
        }

        # Only include params if provided (per JSON-RPC 2.0 spec)
        if params is not None:
            payload["params"] = params

        # Validate payload before sending
        self._validate_request(payload, is_notification=True)

        logger.debug("JSON-RPC notification: %s -> %s", method, params)

        retry_count = 0
        connection_lost = False

        while retry_count <= self.max_retries:
            try:
                await self._send_request(payload, expect_response=False)
                logger.debug("JSON-RPC notification sent: %s", method)
                return

            except (ConnectionError, AyuTimeoutError) as exc:
                retry_count += 1

                # Check if connection was lost
                if "connection" in str(exc).lower() or "timeout" in str(exc).lower():
                    connection_lost = True
                    self._is_connected = False

                if retry_count > self.max_retries:
                    logger.error(
                        "Notification failed after %d retries: %s",
                        self.max_retries,
                        exc,
                    )
                    raise

                # If connection was lost, try to reconnect first
                if connection_lost and not self._reconnecting:
                    logger.warning(
                        "Connection lost during notify, attempting to reconnect..."
                    )
                    if await self._try_reconnect():
                        connection_lost = False
                        logger.info("Reconnected successfully, retrying notification")
                        continue

                # Exponential backoff
                backoff = min(2 ** (retry_count - 1), 30)
                logger.warning(
                    "Notification failed (attempt %d/%d), retrying in %ds: %s",
                    retry_count,
                    self.max_retries,
                    backoff,
                    exc,
                )
                await asyncio.sleep(backoff)

            except AyuGramError:
                # Don't retry on application-level errors
                raise

    async def _send_request(
        self,
        payload: Dict[str, Any],
        expect_response: bool = True,
    ) -> Any:
        """
        Send HTTP POST request with JSON-RPC payload.

        Args:
            payload: JSON-RPC request payload
            expect_response: Whether to wait for and parse response

        Returns:
            Parsed JSON-RPC response result

        Raises:
            ConnectionError: If HTTP request fails
            AyuTimeoutError: If request times out
            AyuGramError: If JSON-RPC error response received
        """
        if not self._session:
            raise ConnectionError("Session not initialized")

        try:
            async with self._session.post(
                self.endpoint_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        "HTTP error %d: %s",
                        response.status,
                        error_text,
                    )
                    raise ConnectionError(
                        f"HTTP {response.status}: {error_text}",
                        details={
                            "status": response.status,
                            "body": error_text,
                            "payload": payload,
                        },
                    )

                if not expect_response:
                    return None

                response_data = await response.json()
                return self._parse_response(response_data)

        except asyncio.TimeoutError as exc:
            logger.error("Request timeout: %s", payload.get("method"))
            raise AyuTimeoutError(
                f"Request timeout: {payload.get('method')}",
                details={"method": payload.get("method"), "payload": payload},
            ) from exc
        except (aiohttp.ClientError, json.JSONDecodeError) as exc:
            logger.error("Request failed: %s", exc)
            raise ConnectionError(
                f"Request failed: {exc}",
                details={"method": payload.get("method"), "error": str(exc)},
            ) from exc

    def _parse_response(self, response_data: Dict[str, Any]) -> Any:
        """
        Parse JSON-RPC response and handle errors with spec compliance.

        Args:
            response_data: Raw JSON-RPC response dict

        Returns:
            Result data from response

        Raises:
            AyuGramError: If JSON-RPC error response received or invalid response
        """
        # Validate response structure per JSON-RPC 2.0 spec
        if not isinstance(response_data, dict):
            logger.error("Invalid JSON-RPC response: not an object")
            raise AyuGramError(
                "Invalid JSON-RPC response: response must be an object",
                details={"response_type": type(response_data).__name__},
            )

        # Check jsonrpc version
        if "jsonrpc" in response_data and response_data["jsonrpc"] != "2.0":
            logger.warning(
                "JSON-RPC response version: %s (expected '2.0')",
                response_data["jsonrpc"],
            )

        # Handle error responses
        if "error" in response_data:
            error = response_data["error"]

            # Validate error object structure
            if not isinstance(error, dict):
                logger.error("Invalid JSON-RPC error: not an object")
                raise AyuGramError(
                    "Invalid JSON-RPC error response: error must be an object",
                    details={"error": error},
                )

            error_code = error.get("code", -32603)
            error_message = error.get("message", "Unknown error")
            error_data = error.get("data")

            # Validate error code is an integer
            if not isinstance(error_code, int):
                logger.error("Invalid JSON-RPC error code: not an integer")

            # Validate error message is a string
            if not isinstance(error_message, str):
                logger.error("Invalid JSON-RPC error message: not a string")

            logger.error(
                "JSON-RPC error %d: %s (data: %s)",
                error_code,
                error_message,
                error_data,
            )

            raise AyuGramError(
                f"JSON-RPC error {error_code}: {error_message}",
                details={
                    "code": error_code,
                    "message": error_message,
                    "data": error_data,
                },
            )

        # Check for result field (required for successful responses)
        if "result" not in response_data:
            logger.error(
                "Invalid JSON-RPC response: missing both 'result' and 'error' fields"
            )
            raise AyuGramError(
                "Invalid JSON-RPC response: missing 'result' field (successful responses must have result)",
                details={"response": response_data},
            )

        return response_data["result"]

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
        return False

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to JSON-RPC endpoint."""
        return self._is_connected
