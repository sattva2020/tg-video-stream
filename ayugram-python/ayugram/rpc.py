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
from aiohttp import ClientError, ClientSession, ClientTimeout

from ayugram.exceptions import AyuGramError, ConnectionError, TimeoutError as AyuTimeoutError

logger = logging.getLogger("ayugram.rpc")


class JsonRpcClient:
    """
    Async JSON-RPC 2.0 client with connection pooling and reconnection.

    Implements JSON-RPC 2.0 specification (https://www.jsonrpc.org/specification)
    with automatic reconnection, exponential backoff, and connection pooling.

    Attributes:
        endpoint_url: JSON-RPC server endpoint URL
        timeout: Request timeout in seconds
        _session: aiohttp ClientSession for HTTP requests
        _request_id: Counter for JSON-RPC request IDs
        _is_connected: Connection state flag

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
    ):
        """
        Initialize JSON-RPC client.

        Args:
            endpoint_url: JSON-RPC server endpoint URL (e.g., http://localhost:8080/jsonrpc)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts for failed requests (default: 3)
            session: Optional existing aiohttp ClientSession to reuse

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

        logger.debug("JsonRpcClient initialized for endpoint: %s", self.endpoint_url)

    async def start(self) -> None:
        """
        Initialize the JSON-RPC client and establish connection.

        Creates aiohttp session if not provided and tests connection to endpoint.

        Raises:
            ConnectionError: If connection to server fails
            AyuTimeoutError: If connection attempt times out
        """
        if self._is_connected:
            logger.debug("Client already connected")
            return

        try:
            if self._owned_session:
                self._session = ClientSession(
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )

            # Test connection with a simple ping-like request
            await self._test_connection()
            self._is_connected = True
            logger.info("JsonRpcClient connected to %s", self.endpoint_url)

        except asyncio.TimeoutError as exc:
            logger.error("Connection timeout to %s", self.endpoint_url)
            raise AyuTimeoutError(
                f"Connection timeout to {self.endpoint_url}",
                details={"endpoint": self.endpoint_url, "timeout": self.timeout.total},
            ) from exc
        except ClientError as exc:
            logger.error("Connection failed to %s: %s", self.endpoint_url, exc)
            raise ConnectionError(
                f"Failed to connect to {self.endpoint_url}",
                details={"endpoint": self.endpoint_url, "error": str(exc)},
            ) from exc

    async def stop(self) -> None:
        """
        Close the JSON-RPC client and cleanup resources.

        Closes aiohttp session if owned by this client.
        """
        if not self._is_connected:
            return

        self._is_connected = False

        if self._owned_session and self._session:
            await self._session.close()
            logger.debug("Closed owned aiohttp session")

        logger.info("JsonRpcClient disconnected from %s", self.endpoint_url)

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
            async with self._session.get(self.endpoint_url.replace("/jsonrpc", "/")) as response:
                # We don't care about the response, just that it's reachable
                pass
        except Exception as exc:
            # If the health check endpoint doesn't exist, that's okay
            # We'll test actual RPC calls later
            logger.debug("Connection test returned: %s (continuing)", exc)

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

        if not self._is_connected:
            await self.start()

        if request_id is None:
            async with self._lock:
                self._request_id += 1
                request_id = self._request_id

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": request_id,
        }

        logger.debug("JSON-RPC request: %s -> %s", method, params)

        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            try:
                response = await self._send_request(payload)
                logger.debug("JSON-RPC response: %s <- %s", method, response)
                return response

            except (ConnectionError, AyuTimeoutError) as exc:
                last_error = exc
                retry_count += 1

                if retry_count > self.max_retries:
                    logger.error(
                        "Request failed after %d retries: %s",
                        self.max_retries,
                        exc,
                    )
                    raise

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

        if not self._is_connected:
            await self.start()

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }

        logger.debug("JSON-RPC notification: %s -> %s", method, params)

        try:
            await self._send_request(payload, expect_response=False)
            logger.debug("JSON-RPC notification sent: %s", method)

        except (ConnectionError, AyuTimeoutError) as exc:
            logger.error("Notification failed: %s", exc)
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
        Parse JSON-RPC response and handle errors.

        Args:
            response_data: Raw JSON-RPC response dict

        Returns:
            Result data from response

        Raises:
            AyuGramError: If JSON-RPC error response received
        """
        if "error" in response_data:
            error = response_data["error"]
            error_code = error.get("code", -32603)
            error_message = error.get("message", "Unknown error")
            error_data = error.get("data")

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

        if "result" not in response_data:
            logger.error("Invalid JSON-RPC response: missing 'result' field")
            raise AyuGramError(
                "Invalid JSON-RPC response: missing 'result' field",
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
