"""
JSON-RPC 2.0 WebSocket API for call control and media streaming.

Provides a JSON-RPC interface over WebSocket for remote control of:
- Call stream lifecycle (start/stop/restart)
- Media playback parameters (speed, pitch, equalizer)
- Stream status and logs

Clients connect with JWT authentication and send standard JSON-RPC requests.
"""
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, Query, WebSocketDisconnect
from fastapi_websocket_rpc import WebsocketRPCEndpoint
from jose import JWTError

from src.api.jsonrpc.methods import CallControlMethods, MediaStreamingMethods
from src.services.stream_controller import get_stream_controller
from src.services.playback_service import PlaybackService

router = APIRouter()
log = logging.getLogger("jsonrpc")


async def jsonrpc_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    JSON-RPC 2.0 WebSocket endpoint with JWT authentication.

    Query parameters:
        - token: JWT authentication token (required)

    Connection flow:
        1. Client connects with ?token=<jwt> query parameter
        2. Server validates JWT BEFORE accepting connection
        3. Connection accepted with 101 status
        4. Client sends JSON-RPC requests
        5. Server processes and returns JSON-RPC responses

    JSON-RPC request format:
        {
            "jsonrpc": "2.0",
            "method": "method_name",
            "params": {"param1": "value1", ...},
            "id": 1
        }

    JSON-RPC response format:
        {
            "jsonrpc": "2.0",
            "result": {...},
            "id": 1
        }

    Available RPC methods:
        Call Control:
            - start_call(channel_id, quality)
            - stop_call(channel_id)
            - restart_call(channel_id)
            - get_stream_logs(channel_id, lines)

        Media Streaming:
            - set_playback_speed(channel_id, speed)
            - set_pitch(channel_id, semitones)
            - set_equalizer_preset(channel_id, preset_name)
            - set_equalizer_custom(channel_id, bands)
            - get_stream_status(channel_id)

    Error codes (JSON-RPC 2.0):
        - -32700: Parse error
        - -32600: Invalid Request
        - -32601: Method not found
        - -32602: Invalid params
        - -32603: Internal error
    """
    # ========================================================================
    # JWT Authentication (BEFORE accepting connection)
    # ========================================================================

    if not token:
        log.warning("WebSocket connection attempt without token")
        await websocket.close(code=1008, reason="Policy Violation: Missing authentication token")
        return

    # Decode JWT token
    from src.api.jsonrpc.auth import get_token_payload

    payload = get_token_payload(token)
    if not payload:
        log.warning("Invalid token for WebSocket connection")
        await websocket.close(code=1008, reason="Policy Violation: Invalid authentication token")
        return

    # Extract user_id from payload
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        log.warning("Token payload missing 'sub' or 'user_id'")
        await websocket.close(code=1008, reason="Policy Violation: Token missing user identifier")
        return

    # ========================================================================
    # Accept connection and initialize services
    # ========================================================================

    await websocket.accept()
    log.info(f"JSON-RPC WebSocket connected for user={user_id}")

    # Get database session (lazy import to avoid circular dependencies)
    from src.database import SessionLocal
    db = SessionLocal()

    try:
        # Initialize services
        stream_controller = get_stream_controller()
        playback_service = PlaybackService(db_session=db)

        # Instantiate RPC method classes with user_id
        call_control_methods = CallControlMethods(
            stream_controller=stream_controller,
            user_id=user_id,
        )

        media_streaming_methods = MediaStreamingMethods(
            playback_service=playback_service,
            user_id=user_id,
        )

        # Combine all RPC methods
        # Note: WebsocketRPCEndpoint can handle multiple RpcMethodsBase instances
        rpc_methods = [call_control_methods, media_streaming_methods]

        # Create JSON-RPC endpoint
        endpoint = WebsocketRPCEndpoint(*rpc_methods)

        # Main loop - handle JSON-RPC requests
        log.info(f"Starting JSON-RPC main loop for user={user_id}")
        await endpoint.main_loop(websocket)

    except WebSocketDisconnect:
        log.info(f"JSON-RPC WebSocket disconnected for user={user_id}")
    except JWTError as e:
        log.error(f"JWT error for user={user_id}: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
    except Exception as e:
        log.error(f"JSON-RPC error for user={user_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass
    finally:
        # Cleanup database connection
        try:
            db.close()
        except Exception as e:
            log.error(f"Error closing database connection: {e}")

        log.info(f"JSON-RPC connection cleanup completed for user={user_id}")


# Register the WebSocket route
router.add_websocket_route("/jsonrpc", jsonrpc_websocket)
