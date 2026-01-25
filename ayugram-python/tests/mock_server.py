"""
Mock JSON-RPC Server for AyuGram SDK Testing.

This module provides a mock JSON-RPC server that simulates the AyuGram API
for integration testing. It implements JSON-RPC 2.0 specification and
handles common AyuGram methods like authentication and call operations.

The server is designed for testing purposes only and provides predictable,
deterministic responses for all supported methods.

Example:
    >>> from tests.mock_server import MockAyuGramServer
    >>> server = MockAyuGramServer(port=8080)
    >>> await server.start()
    >>> # Run tests...
    >>> await server.stop()
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
from aiohttp import web
from aiohttp.web import Application, Request, Response

logger = logging.getLogger("ayugram.mock_server")


class MockAyuGramServer:
    """
    Mock JSON-RPC server simulating AyuGram API for testing.

    Implements JSON-RPC 2.0 specification with support for common AyuGram
    methods including authentication, group calls, and stream control.

    Features:
        - JSON-RPC 2.0 compliant request/response handling
        - Configurable port and host
        - Async start/stop lifecycle
        - Customizable method handlers
        - Request/response logging

    Attributes:
        host: Host to bind server to (default: "127.0.0.1")
        port: Port to bind server to (default: 8080)
        server_url: Full URL of the server endpoint
        _app: aiohttp Application instance
        _runner: aiohttp AppRunner instance
        _site: aiohttp AppSite instance
        _handlers: Dict of method name to handler function
        _request_log: List of received requests for testing verification

    Example:
        >>> server = MockAyuGramServer(port=8080)
        >>> await server.start()
        >>> # Server is now running at http://127.0.0.1:8080/jsonrpc
        >>> await server.stop()
    """

    # Default server configuration
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 8080
    RPC_ENDPOINT = "/jsonrpc"

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ):
        """
        Initialize mock JSON-RPC server.

        Args:
            host: Host to bind server to (default: "127.0.0.1")
            port: Port to bind server to (default: 8080)

        Raises:
            ValueError: If port is not in valid range (1-65535)

        Example:
            >>> server = MockAyuGramServer(port=9999)
            >>> print(server.server_url)
            http://127.0.0.1:9999/jsonrpc
        """
        if not 1 <= port <= 65535:
            raise ValueError(f"port must be in range 1-65535, got {port}")

        self.host = host
        self.port = port
        self.server_url = f"http://{host}:{port}{self.RPC_ENDPOINT}"

        self._app: Optional[Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.AppSite] = None
        self._handlers: Dict[str, Callable] = {}
        self._request_log: list = []
        self._sessions: Dict[str, Dict] = {}  # phone -> session data

        # Register default method handlers
        self._register_default_handlers()

    def _register_default_handlers(self):
        """Register default method handlers for common AyuGram methods."""
        self._handlers = {
            "auth.send_code": self._handle_auth_send_code,
            "auth.sign_in": self._handle_auth_sign_in,
            "join_group_call": self._handle_join_group_call,
            "leave_group_call": self._handle_leave_group_call,
            "play": self._handle_play,
            "pause": self._handle_pause,
            "resume": self._handle_resume,
            "get_state": self._handle_get_state,
            "set_volume": self._handle_set_volume,
        }

    async def start(self):
        """
        Start the mock JSON-RPC server.

        Creates and starts the aiohttp web application with the JSON-RPC
        endpoint. The server runs in the background and can handle multiple
        concurrent requests.

        Raises:
            RuntimeError: If server is already running

        Example:
            >>> server = MockAyuGramServer()
            >>> await server.start()
            >>> # Server is now running
            >>> await server.stop()
        """
        if self._site is not None:
            raise RuntimeError("Server is already running")

        logger.info(f"Starting mock AyuGram server at {self.server_url}")

        self._app = web.Application()
        self._app.router.add_post(self.RPC_ENDPOINT, self._handle_jsonrpc)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

        logger.info(f"Mock AyuGram server started at {self.server_url}")

    async def stop(self):
        """
        Stop the mock JSON-RPC server.

        Gracefully shuts down the server, closing all active connections
        and cleaning up resources.

        Example:
            >>> server = MockAyuGramServer()
            >>> await server.start()
            >>> await server.stop()
            >>> # Server has stopped
        """
        if self._site is None:
            logger.warning("Server is not running")
            return

        logger.info(f"Stopping mock AyuGram server at {self.server_url}")

        await self._site.stop()
        await self._runner.cleanup()
        self._site = None
        self._runner = None
        self._app = None

        logger.info("Mock AyuGram server stopped")

    async def _handle_jsonrpc(self, request: Request) -> Response:
        """
        Handle incoming JSON-RPC requests.

        Parses JSON-RPC request, validates it, dispatches to the appropriate
        handler, and returns a JSON-RPC response.

        Args:
            request: aiohttp Request object

        Returns:
            aiohttp Response object with JSON-RPC response
        """
        try:
            # Parse request body
            request_data = await request.json()

            # Log request for testing verification
            self._request_log.append({
                "method": request_data.get("method"),
                "params": request_data.get("params"),
                "id": request_data.get("id"),
            })

            # Validate JSON-RPC request
            if not isinstance(request_data, dict):
                return self._error_response(None, -32600, "Invalid Request", "Request must be an object")

            if request_data.get("jsonrpc") != "2.0":
                return self._error_response(
                    request_data.get("id"),
                    -32600,
                    "Invalid Request",
                    "jsonrpc version must be '2.0'"
                )

            method = request_data.get("method")
            if not method or not isinstance(method, str):
                return self._error_response(
                    request_data.get("id"),
                    -32600,
                    "Invalid Request",
                    "method is required and must be a string"
                )

            params = request_data.get("params", {})
            if params is None:
                params = {}

            request_id = request_data.get("id")

            # Dispatch to handler
            handler = self._handlers.get(method)
            if handler is None:
                logger.warning(f"Method not found: {method}")
                return self._error_response(
                    request_id,
                    -32601,
                    "Method not found",
                    f"Method '{method}' is not supported by mock server"
                )

            # Call handler and get result
            try:
                result = await handler(params)
                return self._success_response(request_id, result)
            except Exception as e:
                logger.error(f"Error handling method {method}: {e}")
                return self._error_response(
                    request_id,
                    -32603,
                    "Internal error",
                    str(e)
                )

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return self._error_response(None, -32700, "Parse error", str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return self._error_response(None, -32603, "Internal error", str(e))

    def _success_response(self, request_id: Any, result: Any) -> Response:
        """Create a successful JSON-RPC response."""
        response_data = {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id,
        }
        return web.json_response(response_data, status=200)

    def _error_response(
        self,
        request_id: Any,
        code: int,
        message: str,
        data: Any = None
    ) -> Response:
        """Create an error JSON-RPC response."""
        error_data = {
            "code": code,
            "message": message,
        }
        if data is not None:
            error_data["data"] = data

        response_data = {
            "jsonrpc": "2.0",
            "error": error_data,
            "id": request_id,
        }
        return web.json_response(response_data, status=200)

    # ========================================================================
    # Method Handlers
    # ========================================================================

    async def _handle_auth_send_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle auth.send_code method.

        Simulates sending an authentication code to a phone number.

        Args:
            params: Dictionary containing 'phone' key

        Returns:
            Dictionary with success status

        Raises:
            ValueError: If phone is missing or invalid
        """
        phone = params.get("phone")
        if not phone:
            raise ValueError("phone parameter is required")

        if not phone.startswith("+"):
            raise ValueError("phone must start with '+'")

        logger.info(f"Mock server: auth.send_code called for {phone}")

        return {
            "success": True,
            "phone": phone,
            "code_hash": "mock_code_hash_12345",
        }

    async def _handle_auth_sign_in(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle auth.sign_in method.

        Simulates authenticating with a phone code.

        Args:
            params: Dictionary containing 'phone' and 'code' keys

        Returns:
            Dictionary with user information

        Raises:
            ValueError: If phone or code is missing/invalid
        """
        phone = params.get("phone")
        code = params.get("code")

        if not phone:
            raise ValueError("phone parameter is required")
        if not code:
            raise ValueError("code parameter is required")

        # Validate code format (mock accepts any 5-digit code)
        if not isinstance(code, str) or len(code) != 5 or not code.isdigit():
            raise ValueError("code must be a 5-digit string")

        logger.info(f"Mock server: auth.sign_in called for {phone}")

        # Create mock session data
        session_data = {
            "phone": phone,
            "user_id": 123456789,
            "auth_key": "mock_auth_key_base64_encoded",
            "first_name": "Test",
            "last_name": "User",
        }

        # Store session
        self._sessions[phone] = session_data

        return session_data

    async def _handle_join_group_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle join_group_call method.

        Simulates joining a voice chat.

        Args:
            params: Dictionary containing 'chat_id' key

        Returns:
            Dictionary with join confirmation
        """
        chat_id = params.get("chat_id")
        if chat_id is None:
            raise ValueError("chat_id parameter is required")

        logger.info(f"Mock server: join_group_call called for chat {chat_id}")

        return {
            "success": True,
            "chat_id": chat_id,
            "call_id": "mock_call_id_12345",
        }

    async def _handle_leave_group_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle leave_group_call method.

        Simulates leaving a voice chat.

        Args:
            params: Dictionary containing 'chat_id' key

        Returns:
            Dictionary with leave confirmation
        """
        chat_id = params.get("chat_id")
        if chat_id is None:
            raise ValueError("chat_id parameter is required")

        logger.info(f"Mock server: leave_group_call called for chat {chat_id}")

        return {
            "success": True,
            "chat_id": chat_id,
        }

    async def _handle_play(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle play method."""
        chat_id = params.get("chat_id")
        if chat_id is None:
            raise ValueError("chat_id parameter is required")

        logger.info(f"Mock server: play called for chat {chat_id}")

        return {"success": True, "chat_id": chat_id, "is_playing": True}

    async def _handle_pause(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pause method."""
        chat_id = params.get("chat_id")
        if chat_id is None:
            raise ValueError("chat_id parameter is required")

        logger.info(f"Mock server: pause called for chat {chat_id}")

        return {"success": True, "chat_id": chat_id, "is_paused": True}

    async def _handle_resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resume method."""
        chat_id = params.get("chat_id")
        if chat_id is None:
            raise ValueError("chat_id parameter is required")

        logger.info(f"Mock server: resume called for chat {chat_id}")

        return {"success": True, "chat_id": chat_id, "is_playing": True}

    async def _handle_get_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get_state method."""
        chat_id = params.get("chat_id")
        if chat_id is None:
            raise ValueError("chat_id parameter is required")

        return {
            "chat_id": chat_id,
            "is_playing": False,
            "is_paused": False,
            "position_ms": 0,
        }

    async def _handle_set_volume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle set_volume method."""
        chat_id = params.get("chat_id")
        volume = params.get("volume")

        if chat_id is None:
            raise ValueError("chat_id parameter is required")
        if volume is None:
            raise ValueError("volume parameter is required")

        logger.info(f"Mock server: set_volume called for chat {chat_id}, volume {volume}")

        return {"success": True, "chat_id": chat_id, "volume": volume}

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def register_handler(self, method: str, handler: Callable):
        """
        Register a custom method handler.

        Allows tests to override default handlers or add new methods.

        Args:
            method: Method name (e.g., "custom_method")
            handler: Async callable that takes params dict and returns result

        Example:
            >>> async def my_handler(params):
            ...     return {"custom": "result"}
            >>> server.register_handler("custom_method", my_handler)
        """
        self._handlers[method] = handler
        logger.info(f"Registered custom handler for method: {method}")

    def unregister_handler(self, method: str):
        """
        Unregister a method handler.

        Args:
            method: Method name to remove

        Example:
            >>> server.unregister_handler("custom_method")
        """
        if method in self._handlers:
            del self._handlers[method]
            logger.info(f"Unregistered handler for method: {method}")

    def clear_request_log(self):
        """Clear the request log."""
        self._request_log.clear()

    def get_request_log(self) -> list:
        """
        Get the request log.

        Returns a list of all requests received by the server, useful for
        testing verification.

        Returns:
            List of request dictionaries with 'method', 'params', and 'id' keys

        Example:
            >>> await server.start()
            >>> # Make some requests...
            >>> log = server.get_request_log()
            >>> assert len(log) > 0
        """
        return self._request_log.copy()

    def get_sessions(self) -> Dict[str, Dict]:
        """
        Get all stored sessions.

        Returns a copy of the sessions dictionary, useful for testing
        authentication flows.

        Returns:
            Dictionary mapping phone numbers to session data

        Example:
            >>> sessions = server.get_sessions()
            >>> assert "+1234567890" in sessions
        """
        return self._sessions.copy()

    def clear_sessions(self):
        """Clear all stored sessions."""
        self._sessions.clear()

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
