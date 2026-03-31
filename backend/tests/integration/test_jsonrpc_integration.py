"""
Integration tests for JSON-RPC WebSocket endpoint.
"""
import pytest
from fastapi.testclient import TestClient


class TestWebSocketConnectionLifecycle:
    """Test WebSocket connection connect/authenticate/disconnect cycle"""

    @pytest.mark.asyncio
    async def test_connect_with_valid_token(self, client: TestClient, valid_jwt_token):
        """Test that WebSocket connection succeeds with valid JWT token"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            # Connection should be established
            assert websocket is not None

    @pytest.mark.asyncio
    async def test_connect_without_token_closed(self, client: TestClient):
        """Test that WebSocket connection is closed without token"""
        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect("/api/ws/jsonrpc"):
                pass
        # Connection should be rejected (may raise exception)

    @pytest.mark.asyncio
    async def test_connect_with_invalid_token_closed(self, client: TestClient):
        """Test that WebSocket connection is closed with invalid token"""
        with pytest.raises(Exception):
            with client.websocket_connect(
                "/api/ws/jsonrpc?token=invalid.token.here"
            ):
                pass
        # Should close with code 1008

    @pytest.mark.asyncio
    async def test_connect_with_expired_token(self, client: TestClient, expired_jwt_token):
        """Test that WebSocket connection is closed with expired token"""
        with pytest.raises(Exception):
            with client.websocket_connect(
                "/api/ws/jsonrpc?token=" + expired_jwt_token
            ):
                pass
        # Should close with code 1008

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self, client: TestClient, valid_jwt_token):
        """Test that WebSocket properly cleans up on disconnect"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            # Send a request to ensure connection is working
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "get_stream_status",
                "params": {"channel_id": 123},
                "id": 1
            })
            # Disconnect happens here when exiting context manager
        # If no exception, cleanup occurred successfully


class TestJSONRPCProtocol:
    """Test JSON-RPC 2.0 protocol compliance"""

    @pytest.mark.asyncio
    async def test_valid_jsonrpc_request(self, client: TestClient, valid_jwt_token):
        """Test sending valid JSON-RPC request"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "start_call",
                "params": {"channel_id": 123, "quality": "720p"},
                "id": 1
            })

            response = websocket.receive_json()
            assert response["jsonrpc"] == "2.0"
            assert "result" in response or "error" in response
            assert response["id"] == 1

    @pytest.mark.asyncio
    async def test_method_not_found_error(self, client: TestClient, valid_jwt_token):
        """Test that unknown method returns JSON-RPC error -32601"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "nonexistent_method",
                "params": {},
                "id": 1
            })

            response = websocket.receive_json()
            assert "error" in response
            assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_invalid_params_error_negative_channel(self, client: TestClient, valid_jwt_token):
        """Test that invalid params return JSON-RPC error -32602 for negative channel_id"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "start_call",
                "params": {"channel_id": -1, "quality": "720p"},
                "id": 1
            })

            response = websocket.receive_json()
            assert "error" in response
            assert response["error"]["code"] == -32602
            assert "channel_id" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_invalid_params_error_invalid_quality(self, client: TestClient, valid_jwt_token):
        """Test that invalid params return JSON-RPC error -32602 for invalid quality"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "start_call",
                "params": {"channel_id": 123, "quality": "invalid"},
                "id": 1
            })

            response = websocket.receive_json()
            assert "error" in response
            assert response["error"]["code"] == -32602
            assert "quality" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_jsonrpc_request_without_id(self, client: TestClient, valid_jwt_token):
        """Test that JSON-RPC notification (request without id) is handled"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            # Notification - no response expected
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "start_call",
                "params": {"channel_id": 123, "quality": "720p"}
            })
            # No response should be sent for notifications
            # We can't easily test "no response", but we can ensure no exception


class TestCallControlIntegration:
    """Test CallControlMethods integration with StreamController"""

    @pytest.mark.asyncio
    async def test_start_call_integration(self, client: TestClient, valid_jwt_token):
        """Test start_call RPC method invokes StreamController"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "start_call",
                "params": {"channel_id": 123, "quality": "720p"},
                "id": 1
            })

            response = websocket.receive_json()
            assert "result" in response
            assert response["result"]["channel_id"] == 123
            assert "success" in response["result"]
            assert "message" in response["result"]

    @pytest.mark.asyncio
    async def test_stop_call_integration(self, client: TestClient, valid_jwt_token):
        """Test stop_call RPC method invokes StreamController"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "stop_call",
                "params": {"channel_id": 123},
                "id": 2
            })

            response = websocket.receive_json()
            assert "result" in response
            assert response["result"]["channel_id"] == 123
            assert "success" in response["result"]

    @pytest.mark.asyncio
    async def test_restart_call_integration(self, client: TestClient, valid_jwt_token):
        """Test restart_call RPC method invokes StreamController"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "restart_call",
                "params": {"channel_id": 456},
                "id": 3
            })

            response = websocket.receive_json()
            assert "result" in response
            assert response["result"]["channel_id"] == 456
            assert "success" in response["result"]

    @pytest.mark.asyncio
    async def test_get_stream_logs_integration(self, client: TestClient, valid_jwt_token):
        """Test get_stream_logs RPC method retrieves logs"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "get_stream_logs",
                "params": {"channel_id": 789, "lines": 10},
                "id": 4
            })

            response = websocket.receive_json()
            assert "result" in response
            assert "logs" in response["result"]
            assert response["result"]["lines"] == 10


class TestMediaStreamingIntegration:
    """Test MediaStreamingMethods integration with PlaybackService"""

    @pytest.mark.asyncio
    async def test_set_playback_speed_integration(self, client: TestClient, valid_jwt_token):
        """Test set_playback_speed RPC method updates database"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "set_playback_speed",
                "params": {"channel_id": 123, "speed": 1.5},
                "id": 1
            })

            response = websocket.receive_json()
            assert "result" in response
            assert response["result"]["speed"] == 1.5

    @pytest.mark.asyncio
    async def test_set_pitch_integration(self, client: TestClient, valid_jwt_token):
        """Test set_pitch RPC method updates database"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "set_pitch",
                "params": {"channel_id": 123, "semitones": 6},
                "id": 2
            })

            response = websocket.receive_json()
            assert "result" in response
            assert response["result"]["pitch_semitones"] == 6

    @pytest.mark.asyncio
    async def test_get_stream_status_integration(self, client: TestClient, valid_jwt_token):
        """Test get_stream_status RPC method retrieves settings"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "get_stream_status",
                "params": {"channel_id": 123},
                "id": 3
            })

            response = websocket.receive_json()
            assert "result" in response
            assert "speed" in response["result"]
            assert "pitch_correction" in response["result"]

    @pytest.mark.asyncio
    async def test_set_playback_speed_out_of_range_error(self, client: TestClient, valid_jwt_token):
        """Test that out-of-range speed returns JSON-RPC error"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "set_playback_speed",
                "params": {"channel_id": 123, "speed": 5.0},
                "id": 4
            })

            response = websocket.receive_json()
            assert "error" in response
            assert response["error"]["code"] == -32602
            assert "Speed" in response["error"]["message"]

    @pytest.mark.asyncio
    async def test_set_pitch_out_of_range_error(self, client: TestClient, valid_jwt_token):
        """Test that out-of-range pitch returns JSON-RPC error"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "set_pitch",
                "params": {"channel_id": 123, "semitones": 20},
                "id": 5
            })

            response = websocket.receive_json()
            assert "error" in response
            assert response["error"]["code"] == -32602
            assert "Pitch" in response["error"]["message"]


class TestMultipleRequests:
    """Test multiple sequential RPC requests on same connection"""

    @pytest.mark.asyncio
    async def test_multiple_sequential_requests(self, client: TestClient, valid_jwt_token):
        """Test multiple RPC requests on same WebSocket connection"""
        with client.websocket_connect(
            "/api/ws/jsonrpc?token=" + valid_jwt_token
        ) as websocket:
            # Request 1
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "start_call",
                "params": {"channel_id": 123, "quality": "720p"},
                "id": 1
            })
            response1 = websocket.receive_json()
            assert response1["id"] == 1

            # Request 2
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "get_stream_status",
                "params": {"channel_id": 123},
                "id": 2
            })
            response2 = websocket.receive_json()
            assert response2["id"] == 2

            # Request 3
            websocket.send_json({
                "jsonrpc": "2.0",
                "method": "stop_call",
                "params": {"channel_id": 123},
                "id": 3
            })
            response3 = websocket.receive_json()
            assert response3["id"] == 3
