"""
Performance tests for stream switching latency.

Measures the time from switch command to stream status change in the system.
Target: < 2 seconds for stream switch completion (API response + status propagation).

For complete end-to-end latency measurement (switch command → audio change in Telegram),
manual verification is required with actual streamer and Telegram client.

Environment Variables:
- BACKEND_URL: Backend API URL (default: http://localhost:8000)
- TEST_USER_TOKEN: Auth token for test user
- TEST_TELEGRAM_CHAT_ID: Telegram chat ID for testing

Prerequisites:
- Backend API running
- Database migrations applied
- Test user with valid auth token
"""

import os
import time
import pytest
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TEST_USER_TOKEN = os.getenv("TEST_USER_TOKEN", "")
TEST_TELEGRAM_CHAT_ID = int(os.getenv("TEST_TELEGRAM_CHAT_ID", "-1001234567890"))

# Performance targets
TARGET_SWITCH_API_LATENCY_MS = 500  # API should respond within 500ms
TARGET_STATUS_PROPAGATION_MS = 1500  # Status should propagate within 1.5s
TARGET_TOTAL_SWITCH_LATENCY_MS = 2000  # Total: < 2 seconds

# Test configuration
WARMUP_ITERATIONS = 2
MEASUREMENT_ITERATIONS = 5


class StreamSwitchingLatencyTest:
    """Helper class for stream switching latency tests."""

    def __init__(self):
        self.backend_url = BACKEND_URL
        self.headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        self.created_stream_ids: List[str] = []

    def create_live_stream(
        self,
        title: str = "Latency Test Stream",
        ingestion_type: str = "rtmp"
    ) -> Dict[str, Any]:
        """
        Create a new live stream via API.

        Args:
            title: Stream title
            ingestion_type: rtmp, srt, webrtc_camera, or webrtc_screen

        Returns:
            Created live stream data
        """
        url = f"{self.backend_url}/api/v1/live/streams"
        payload = {
            "title": title,
            "chat_id": TEST_TELEGRAM_CHAT_ID,
            "ingestion_type": ingestion_type,
            "quality_preset": "720p",
            "max_guests": 2,
            "recording_enabled": False,
            "is_chat_enabled": False
        }

        start_time = time.time()
        response = requests.post(url, json=payload, headers=self.headers)
        api_latency_ms = (time.time() - start_time) * 1000

        assert response.status_code == 201, f"Failed to create live stream: {response.text}"

        data = response.json()
        data["api_latency_ms"] = api_latency_ms
        self.created_stream_ids.append(data["id"])

        return data

    def get_live_stream(self, stream_id: str) -> Dict[str, Any]:
        """
        Get live stream details by ID.

        Args:
            stream_id: Live stream ID

        Returns:
            Live stream data
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}"
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200, f"Failed to get live stream: {response.text}"
        return response.json()

    def start_live_stream(self, stream_id: str) -> Dict[str, Any]:
        """
        Start a live stream via API.

        Args:
            stream_id: Live stream ID

        Returns:
            Response with latency measurement
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}/start"

        start_time = time.time()
        response = requests.post(url, headers=self.headers)
        api_latency_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200, f"Failed to start live stream: {response.text}"

        data = response.json()
        data["api_latency_ms"] = api_latency_ms

        return data

    def stop_live_stream(self, stream_id: str) -> Dict[str, Any]:
        """
        Stop a live stream via API.

        Args:
            stream_id: Live stream ID

        Returns:
            Response with latency measurement
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}/stop"

        start_time = time.time()
        response = requests.post(url, headers=self.headers)
        api_latency_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200, f"Failed to stop live stream: {response.text}"

        data = response.json()
        data["api_latency_ms"] = api_latency_ms

        return data

    def switch_to_live(self, stream_id: str) -> Dict[str, Any]:
        """
        Switch to live stream via API.

        Args:
            stream_id: Live stream ID

        Returns:
            Response with latency measurement
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}/switch-live"

        start_time = time.time()
        response = requests.post(url, headers=self.headers)
        api_latency_ms = (time.time() - start_time) * 1000

        assert response.status_code == 200, f"Failed to switch to live: {response.text}"

        data = response.json()
        data["api_latency_ms"] = api_latency_ms

        return data

    def measure_status_propagation(
        self,
        stream_id: str,
        expected_status: str,
        timeout_seconds: int = 10
    ) -> float:
        """
        Measure time from API call to status propagation.

        Args:
            stream_id: Live stream ID
            expected_status: Status to wait for
            timeout_seconds: Maximum time to wait

        Returns:
            Time in milliseconds until status propagated
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            stream_data = self.get_live_stream(stream_id)
            current_status = stream_data.get("status")

            if current_status == expected_status:
                propagation_time_ms = (time.time() - start_time) * 1000
                return propagation_time_ms

            time.sleep(0.1)  # Poll every 100ms

        raise TimeoutError(
            f"Status did not propagate to '{expected_status}' within {timeout_seconds}s. "
            f"Last status: {current_status}"
        )

    def measure_complete_switch_latency(
        self,
        stream_id: str,
        switch_operation: str = "start"
    ) -> Dict[str, float]:
        """
        Measure complete switch latency (API call + status propagation).

        Args:
            stream_id: Live stream ID
            switch_operation: Type of switch ("start", "stop", "switch_live")

        Returns:
            Dict with latency measurements in milliseconds
        """
        if switch_operation == "start":
            # Start stream
            start_time = time.time()
            response = self.start_live_stream(stream_id)
            api_latency_ms = response["api_latency_ms"]
            expected_status = "active"
        elif switch_operation == "stop":
            # Stop stream
            start_time = time.time()
            response = self.stop_live_stream(stream_id)
            api_latency_ms = response["api_latency_ms"]
            expected_status = "stopped"
        elif switch_operation == "switch_live":
            # Switch to live
            start_time = time.time()
            response = self.switch_to_live(stream_id)
            api_latency_ms = response["api_latency_ms"]
            expected_status = "active"
        else:
            raise ValueError(f"Unknown switch operation: {switch_operation}")

        # Measure status propagation
        propagation_latency_ms = self.measure_status_propagation(stream_id, expected_status)
        total_latency_ms = api_latency_ms + propagation_latency_ms

        return {
            "api_latency_ms": api_latency_ms,
            "propagation_latency_ms": propagation_latency_ms,
            "total_latency_ms": total_latency_ms
        }

    def cleanup(self) -> None:
        """Clean up created streams."""
        for stream_id in self.created_stream_ids:
            try:
                url = f"{self.backend_url}/api/v1/live/streams/{stream_id}"
                requests.delete(url, headers=self.headers)
            except Exception:
                pass  # Best effort cleanup
        self.created_stream_ids.clear()


def calculate_statistics(latencies: List[float]) -> Dict[str, float]:
    """
    Calculate statistics for latency measurements.

    Args:
        latencies: List of latency values in milliseconds

    Returns:
        Dict with min, max, avg, median, p95, p99
    """
    if not latencies:
        return {}

    sorted_latencies = sorted(latencies)
    n = len(latencies)

    return {
        "min_ms": round(sorted_latencies[0], 2),
        "max_ms": round(sorted_latencies[-1], 2),
        "avg_ms": round(sum(latencies) / n, 2),
        "median_ms": round(sorted_latencies[n // 2], 2),
        "p95_ms": round(sorted_latencies[int(n * 0.95)] if n >= 20 else sorted_latencies[-1], 2),
        "p99_ms": round(sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1], 2)
    }


@pytest.mark.performance
@pytest.mark.skipif(not TEST_USER_TOKEN, reason="TEST_USER_TOKEN not configured")
def test_stream_creation_api_latency():
    """
    Performance test: Measure stream creation API latency.

    Target: API response < 500ms
    """
    test = StreamSwitchingLatencyTest()

    try:
        latencies = []

        # Warmup
        for _ in range(WARMUP_ITERATIONS):
            test.create_live_stream(title=f"Warmup Stream {_}")

        # Measurements
        for i in range(MEASUREMENT_ITERATIONS):
            stream_data = test.create_live_stream(title=f"Latency Test Stream {i}")
            latencies.append(stream_data["api_latency_ms"])

        stats = calculate_statistics(latencies)

        # Assert performance targets
        assert stats["avg_ms"] < TARGET_SWITCH_API_LATENCY_MS, \
            f"Average API latency {stats['avg_ms']}ms exceeds target {TARGET_SWITCH_API_LATENCY_MS}ms"
        assert stats["p95_ms"] < TARGET_SWITCH_API_LATENCY_MS * 1.5, \
            f"P95 API latency {stats['p95_ms']}ms exceeds target {TARGET_SWITCH_API_LATENCY_MS * 1.5}ms"

    finally:
        test.cleanup()


@pytest.mark.performance
@pytest.mark.skipif(not TEST_USER_TOKEN, reason="TEST_USER_TOKEN not configured")
def test_stream_start_api_latency():
    """
    Performance test: Measure stream start API latency.

    Target: API response < 500ms
    """
    test = StreamSwitchingLatencyTest()

    try:
        # Create stream for testing
        stream_data = test.create_live_stream(title="Start Latency Test")
        stream_id = stream_data["id"]

        latencies = []

        # Warmup (stop and restart)
        for _ in range(WARMUP_ITERATIONS):
            test.stop_live_stream(stream_id)
            test.start_live_stream(stream_id)

        # Measurements
        for _ in range(MEASUREMENT_ITERATIONS):
            # Stop before each start
            test.stop_live_stream(stream_id)
            response = test.start_live_stream(stream_id)
            latencies.append(response["api_latency_ms"])

        stats = calculate_statistics(latencies)

        # Assert performance targets
        assert stats["avg_ms"] < TARGET_SWITCH_API_LATENCY_MS, \
            f"Average start API latency {stats['avg_ms']}ms exceeds target {TARGET_SWITCH_API_LATENCY_MS}ms"
        assert stats["p95_ms"] < TARGET_SWITCH_API_LATENCY_MS * 1.5, \
            f"P95 start API latency {stats['p95_ms']}ms exceeds target {TARGET_SWITCH_API_LATENCY_MS * 1.5}ms"

    finally:
        test.cleanup()


@pytest.mark.performance
@pytest.mark.skipif(not TEST_USER_TOKEN, reason="TEST_USER_TOKEN not configured")
def test_stream_stop_api_latency():
    """
    Performance test: Measure stream stop API latency.

    Target: API response < 500ms
    """
    test = StreamSwitchingLatencyTest()

    try:
        # Create and start stream for testing
        stream_data = test.create_live_stream(title="Stop Latency Test")
        stream_id = stream_data["id"]
        test.start_live_stream(stream_id)

        latencies = []

        # Warmup
        for _ in range(WARMUP_ITERATIONS):
            test.start_live_stream(stream_id)
            test.stop_live_stream(stream_id)

        # Measurements
        for _ in range(MEASUREMENT_ITERATIONS):
            # Start before each stop
            test.start_live_stream(stream_id)
            response = test.stop_live_stream(stream_id)
            latencies.append(response["api_latency_ms"])

        stats = calculate_statistics(latencies)

        # Assert performance targets
        assert stats["avg_ms"] < TARGET_SWITCH_API_LATENCY_MS, \
            f"Average stop API latency {stats['avg_ms']}ms exceeds target {TARGET_SWITCH_API_LATENCY_MS}ms"
        assert stats["p95_ms"] < TARGET_SWITCH_API_LATENCY_MS * 1.5, \
            f"P95 stop API latency {stats['p95_ms']}ms exceeds target {TARGET_SWITCH_API_LATENCY_MS * 1.5}ms"

    finally:
        test.cleanup()


@pytest.mark.performance
@pytest.mark.skipif(not TEST_USER_TOKEN, reason="TEST_USER_TOKEN not configured")
def test_switch_to_live_complete_latency():
    """
    Performance test: Measure complete switch to live latency.

    Measures: API call time + status propagation time
    Target: Total < 2 seconds
    """
    test = StreamSwitchingLatencyTest()

    try:
        # Create stream for testing
        stream_data = test.create_live_stream(title="Complete Switch Latency Test")
        stream_id = stream_data["id"]

        total_latencies = []
        api_latencies = []
        propagation_latencies = []

        # Warmup
        for _ in range(WARMUP_ITERATIONS):
            test.stop_live_stream(stream_id)
            test.measure_complete_switch_latency(stream_id, "start")

        # Measurements
        for _ in range(MEASUREMENT_ITERATIONS):
            test.stop_live_stream(stream_id)
            measurements = test.measure_complete_switch_latency(stream_id, "start")

            api_latencies.append(measurements["api_latency_ms"])
            propagation_latencies.append(measurements["propagation_latency_ms"])
            total_latencies.append(measurements["total_latency_ms"])

        api_stats = calculate_statistics(api_latencies)
        propagation_stats = calculate_statistics(propagation_latencies)
        total_stats = calculate_statistics(total_latencies)

        # Assert performance targets
        assert api_stats["avg_ms"] < TARGET_SWITCH_API_LATENCY_MS, \
            f"Average API latency {api_stats['avg_ms']}ms exceeds target {TARGET_SWITCH_API_LATENCY_MS}ms"

        assert propagation_stats["avg_ms"] < TARGET_STATUS_PROPAGATION_MS, \
            f"Average propagation latency {propagation_stats['avg_ms']}ms exceeds target {TARGET_STATUS_PROPAGATION_MS}ms"

        assert total_stats["avg_ms"] < TARGET_TOTAL_SWITCH_LATENCY_MS, \
            f"Average total latency {total_stats['avg_ms']}ms exceeds target {TARGET_TOTAL_SWITCH_LATENCY_MS}ms"

        # Assert P95 total latency is acceptable
        assert total_stats["p95_ms"] < TARGET_TOTAL_SWITCH_LATENCY_MS * 1.2, \
            f"P95 total latency {total_stats['p95_ms']}ms exceeds target {TARGET_TOTAL_SWITCH_LATENCY_MS * 1.2}ms"

    finally:
        test.cleanup()


@pytest.mark.performance
@pytest.mark.skipif(not TEST_USER_TOKEN, reason="TEST_USER_TOKEN not configured")
def test_stream_stop_complete_latency():
    """
    Performance test: Measure complete stream stop latency.

    Measures: API call time + status propagation time
    Target: Total < 2 seconds
    """
    test = StreamSwitchingLatencyTest()

    try:
        # Create stream for testing
        stream_data = test.create_live_stream(title="Stop Complete Latency Test")
        stream_id = stream_data["id"]

        total_latencies = []
        api_latencies = []
        propagation_latencies = []

        # Warmup
        for _ in range(WARMUP_ITERATIONS):
            test.start_live_stream(stream_id)
            test.measure_complete_switch_latency(stream_id, "stop")

        # Measurements
        for _ in range(MEASUREMENT_ITERATIONS):
            test.start_live_stream(stream_id)
            measurements = test.measure_complete_switch_latency(stream_id, "stop")

            api_latencies.append(measurements["api_latency_ms"])
            propagation_latencies.append(measurements["propagation_latency_ms"])
            total_latencies.append(measurements["total_latency_ms"])

        api_stats = calculate_statistics(api_latencies)
        propagation_stats = calculate_statistics(propagation_latencies)
        total_stats = calculate_statistics(total_latencies)

        # Assert performance targets
        assert api_stats["avg_ms"] < TARGET_SWITCH_API_LATENCY_MS, \
            f"Average API latency {api_stats['avg_ms']}ms exceeds target {TARGET_SWITCH_API_LATENCY_MS}ms"

        assert propagation_stats["avg_ms"] < TARGET_STATUS_PROPAGATION_MS, \
            f"Average propagation latency {propagation_stats['avg_ms']}ms exceeds target {TARGET_STATUS_PROPAGATION_MS}ms"

        assert total_stats["avg_ms"] < TARGET_TOTAL_SWITCH_LATENCY_MS, \
            f"Average total latency {total_stats['avg_ms']}ms exceeds target {TARGET_TOTAL_SWITCH_LATENCY_MS}ms"

    finally:
        test.cleanup()


@pytest.mark.performance
@pytest.mark.skipif(not TEST_USER_TOKEN, reason="TEST_USER_TOKEN not configured")
def test_multiple_stream_switching_latency():
    """
    Performance test: Measure latency when switching between multiple streams.

    Simulates rapid switching scenarios (e.g., switching between different camera angles).
    Target: Each switch < 2 seconds
    """
    test = StreamSwitchingLatencyTest()

    try:
        # Create multiple streams
        streams = []
        for i in range(3):
            stream_data = test.create_live_stream(
                title=f"Multi-Switch Test Stream {i}",
                ingestion_type="rtmp"
            )
            streams.append(stream_data)

        switch_latencies = []

        # Warmup
        for _ in range(WARMUP_ITERATIONS):
            for stream in streams:
                test.stop_live_stream(stream["id"])
            for stream in streams:
                test.measure_complete_switch_latency(stream["id"], "start")
            for stream in streams:
                test.measure_complete_switch_latency(stream["id"], "stop")

        # Measurements: Switch between streams
        for iteration in range(MEASUREMENT_ITERATIONS):
            # Stop all streams
            for stream in streams:
                test.stop_live_stream(stream["id"])

            # Start first stream
            measurements_1 = test.measure_complete_switch_latency(streams[0]["id"], "start")
            switch_latencies.append(("start", iteration, 0, measurements_1["total_latency_ms"]))

            # Switch to second stream (stop first, start second)
            test.measure_complete_switch_latency(streams[0]["id"], "stop")
            measurements_2 = test.measure_complete_switch_latency(streams[1]["id"], "start")
            switch_latencies.append(("switch", iteration, 1, measurements_2["total_latency_ms"]))

            # Switch to third stream
            test.measure_complete_switch_latency(streams[1]["id"], "stop")
            measurements_3 = test.measure_complete_switch_latency(streams[2]["id"], "start")
            switch_latencies.append(("switch", iteration, 2, measurements_3["total_latency_ms"]))

        # Extract latencies
        all_latencies = [latency[3] for latency in switch_latencies]
        stats = calculate_statistics(all_latencies)

        # Assert performance targets
        assert stats["avg_ms"] < TARGET_TOTAL_SWITCH_LATENCY_MS, \
            f"Average switch latency {stats['avg_ms']}ms exceeds target {TARGET_TOTAL_SWITCH_LATENCY_MS}ms"

        assert stats["max_ms"] < TARGET_TOTAL_SWITCH_LATENCY_MS * 1.5, \
            f"Max switch latency {stats['max_ms']}ms exceeds target {TARGET_TOTAL_SWITCH_LATENCY_MS * 1.5}ms"

    finally:
        test.cleanup()


@pytest.mark.manual
def test_manual_end_to_end_stream_switching_latency():
    """
    Manual test: Measure end-to-end stream switching latency.

    This test requires manual verification with:
    1. Active streamer service
    2. Connected Telegram client
    3. Audio monitoring equipment

    Test Procedure:
    1. Start a scheduled stream playing music
    2. Send switch-to-live command
    3. Record timestamp when command is sent
    4. Monitor Telegram audio output
    5. Record timestamp when audio changes to live stream
    6. Calculate latency difference

    Target: < 2 seconds from command to audio change

    Expected Results:
    - API response: < 500ms
    - Status propagation: < 1.5s
    - Audio change in Telegram: < 2s total

    Notes:
    - This test cannot be automated as it requires human listening
    - Actual latency depends on:
      * Network conditions
      * Telegram Bot API processing time
      * Streamer buffer size
      * Audio codec encoding/decoding time
    - For accurate measurement, use audio recording software to capture timestamps
    """
    # This is a placeholder for manual testing
    # Actual implementation requires human verification
    pytest.skip("Manual test - requires human verification with Telegram client")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-m", "performance"])
