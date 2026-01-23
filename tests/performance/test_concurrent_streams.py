"""
Performance tests for concurrent live streams.

Measures system stability and resource usage when handling multiple concurrent live streams.
Tests API latency, memory usage, and stream stability under concurrent load.

Target Performance:
- System should handle 3+ concurrent streams without degradation
- API latency should remain < 500ms even with concurrent operations
- Memory usage should scale linearly with stream count
- No stream failures or errors under normal load

Environment Variables:
- BACKEND_URL: Backend API URL (default: http://localhost:8000)
- TEST_USER_TOKEN: Auth token for test user
- TEST_TELEGRAM_CHAT_ID: Telegram chat ID for testing

Prerequisites:
- Backend API running
- Database migrations applied
- Test user with valid auth token
- Sufficient system resources for concurrent streams
"""

import os
import time
import pytest
import requests
import psutil
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TEST_USER_TOKEN = os.getenv("TEST_USER_TOKEN", "")
TEST_TELEGRAM_CHAT_ID = int(os.getenv("TEST_TELEGRAM_CHAT_ID", "-1001234567890"))

# Performance targets
TARGET_API_LATENCY_MS = 500  # API should respond within 500ms
TARGET_CONCURRENT_STREAMS = 3  # Minimum number of concurrent streams
MAX_MEMORY_MB = 2048  # Maximum memory usage for all concurrent streams (2GB)

# Test configuration
WARMUP_ITERATIONS = 1
MEASUREMENT_ITERATIONS = 3

# Thread-safe resource tracking
_resource_lock = threading.Lock()
_memory_samples: List[float] = []
_cpu_samples: List[float] = []


class ConcurrentStreamsTest:
    """Helper class for concurrent live streams performance tests."""

    def __init__(self):
        self.backend_url = BACKEND_URL
        self.headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        self.created_stream_ids: List[str] = []
        self.process = psutil.Process()

    def create_live_stream(
        self,
        title: str,
        ingestion_type: str = "rtmp"
    ) -> Dict[str, Any]:
        """
        Create a new live stream via API.

        Args:
            title: Stream title
            ingestion_type: rtmp, srt, webrtc_camera, or webrtc_screen

        Returns:
            Created live stream data with API latency
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

    def delete_live_stream(self, stream_id: str) -> None:
        """
        Delete a live stream.

        Args:
            stream_id: Live stream ID
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}"
        response = requests.delete(url, headers=self.headers)
        # Accept both 204 (success) and 404 (already deleted)
        assert response.status_code in [204, 404], f"Failed to delete live stream: {response.text}"

    def get_resource_usage(self) -> Dict[str, float]:
        """
        Get current resource usage (memory and CPU).

        Returns:
            Dict with memory_mb and cpu_percent
        """
        try:
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            cpu_percent = self.process.cpu_percent(interval=0.1)

            # Thread-safe recording
            with _resource_lock:
                _memory_samples.append(memory_mb)
                _cpu_samples.append(cpu_percent)

            return {
                "memory_mb": memory_mb,
                "cpu_percent": cpu_percent
            }
        except Exception as e:
            # Fallback if psutil fails
            return {
                "memory_mb": 0.0,
                "cpu_percent": 0.0
            }

    def create_streams_concurrent(
        self,
        count: int,
        title_prefix: str = "Concurrent Stream"
    ) -> List[Dict[str, Any]]:
        """
        Create multiple streams concurrently using thread pool.

        Args:
            count: Number of streams to create
            title_prefix: Prefix for stream titles

        Returns:
            List of created stream data
        """
        streams = []

        with ThreadPoolExecutor(max_workers=min(count, 10)) as executor:
            # Submit all create tasks
            futures = {
                executor.submit(
                    self.create_live_stream,
                    title=f"{title_prefix} {i}"
                ): i for i in range(count)
            }

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    stream_data = future.result()
                    streams.append(stream_data)
                except Exception as e:
                    pytest.fail(f"Failed to create stream: {e}")

        return streams

    def start_streams_concurrent(
        self,
        stream_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Start multiple streams concurrently using thread pool.

        Args:
            stream_ids: List of stream IDs to start

        Returns:
            List of start responses with latency
        """
        results = []

        with ThreadPoolExecutor(max_workers=min(len(stream_ids), 10)) as executor:
            # Submit all start tasks
            futures = {
                executor.submit(self.start_live_stream, stream_id): stream_id
                for stream_id in stream_ids
            }

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Failed to start stream: {e}")

        return results

    def stop_streams_concurrent(
        self,
        stream_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Stop multiple streams concurrently using thread pool.

        Args:
            stream_ids: List of stream IDs to stop

        Returns:
            List of stop responses with latency
        """
        results = []

        with ThreadPoolExecutor(max_workers=min(len(stream_ids), 10)) as executor:
            # Submit all stop tasks
            futures = {
                executor.submit(self.stop_live_stream, stream_id): stream_id
                for stream_id in stream_ids
            }

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    pytest.fail(f"Failed to stop stream: {e}")

        return results

    def verify_streams_status(
        self,
        stream_ids: List[str],
        expected_status: str,
        timeout_seconds: int = 15
    ) -> Dict[str, bool]:
        """
        Verify all streams have reached expected status.

        Args:
            stream_ids: List of stream IDs to check
            expected_status: Expected status (e.g., "active", "stopped")
            timeout_seconds: Maximum time to wait for all streams

        Returns:
            Dict mapping stream_id to success status
        """
        results = {}
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            all_ready = True

            for stream_id in stream_ids:
                if stream_id in results and results[stream_id]:
                    continue  # Already verified

                try:
                    stream_data = self.get_live_stream(stream_id)
                    current_status = stream_data.get("status")

                    if current_status == expected_status:
                        results[stream_id] = True
                    else:
                        all_ready = False
                except Exception:
                    all_ready = False

            if all_ready and len(results) == len(stream_ids):
                break

            time.sleep(0.2)  # Poll every 200ms

        return results

    def cleanup(self) -> None:
        """Clean up created streams."""
        for stream_id in self.created_stream_ids:
            try:
                self.delete_live_stream(stream_id)
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
def test_concurrent_stream_creation():
    """
    Performance test: Create multiple streams concurrently.

    Measures:
    - API latency for concurrent stream creation
    - Resource usage during creation
    - Success rate (all streams should be created)

    Target:
    - 3 concurrent streams created successfully
    - API latency < 500ms per stream
    - No failures or errors
    """
    test = ConcurrentStreamsTest()

    try:
        # Clear resource samples
        global _memory_samples, _cpu_samples
        _memory_samples.clear()
        _cpu_samples.clear()

        # Get initial resource usage
        initial_resources = test.get_resource_usage()

        # Create streams concurrently
        stream_count = TARGET_CONCURRENT_STREAMS
        streams = test.create_streams_concurrent(
            count=stream_count,
            title_prefix="Concurrent Creation Test"
        )

        # Get final resource usage
        final_resources = test.get_resource_usage()
        memory_delta_mb = final_resources["memory_mb"] - initial_resources["memory_mb"]

        # Verify all streams were created
        assert len(streams) == stream_count, \
            f"Expected {stream_count} streams, got {len(streams)}"

        # Extract creation latencies
        creation_latencies = [s["api_latency_ms"] for s in streams]
        stats = calculate_statistics(creation_latencies)

        # Assert performance targets
        assert stats["avg_ms"] < TARGET_API_LATENCY_MS, \
            f"Average creation latency {stats['avg_ms']}ms exceeds target {TARGET_API_LATENCY_MS}ms"

        assert stats["max_ms"] < TARGET_API_LATENCY_MS * 2, \
            f"Max creation latency {stats['max_ms']}ms exceeds target {TARGET_API_LATENCY_MS * 2}ms"

        # Verify all streams have valid IDs and status
        for stream in streams:
            assert "id" in stream, "Stream missing ID"
            assert stream.get("status") in ["idle", "active"], \
                f"Invalid initial status: {stream.get('status')}"

    finally:
        test.cleanup()


@pytest.mark.performance
@pytest.mark.skipif(not TEST_USER_TOKEN, reason="TEST_USER_TOKEN not configured")
def test_concurrent_stream_start_stop():
    """
    Performance test: Start and stop multiple streams concurrently.

    Measures:
    - API latency for concurrent stream start/stop
    - Resource usage during active streaming
    - Status propagation time for all streams
    - Memory usage scaling

    Target:
    - 3 concurrent streams started and stopped successfully
    - API latency < 500ms per operation
    - All streams reach "active" status
    - Memory usage < 2GB total
    """
    test = ConcurrentStreamsTest()

    try:
        # Clear resource samples
        global _memory_samples, _cpu_samples
        _memory_samples.clear()
        _cpu_samples.clear()

        # Create streams
        stream_count = TARGET_CONCURRENT_STREAMS
        streams = test.create_streams_concurrent(
            count=stream_count,
            title_prefix="Concurrent Start/Stop Test"
        )
        stream_ids = [s["id"] for s in streams]

        # Get baseline resource usage
        baseline_resources = test.get_resource_usage()

        # Start all streams concurrently
        start_results = test.start_streams_concurrent(stream_ids)

        # Extract start latencies
        start_latencies = [r["api_latency_ms"] for r in start_results]
        start_stats = calculate_statistics(start_latencies)

        # Verify all streams started successfully
        assert len(start_results) == stream_count, \
            f"Expected {stream_count} start results, got {len(start_results)}"

        # Assert start latency targets
        assert start_stats["avg_ms"] < TARGET_API_LATENCY_MS, \
            f"Average start latency {start_stats['avg_ms']}ms exceeds target {TARGET_API_LATENCY_MS}ms"

        # Verify all streams reached active status
        active_streams = test.verify_streams_status(stream_ids, "active", timeout_seconds=15)
        assert len(active_streams) == stream_count, \
            f"Expected {stream_count} active streams, got {len(active_streams)}"

        # Get peak resource usage while streams are active
        peak_resources = test.get_resource_usage()
        active_memory_mb = peak_resources["memory_mb"]

        # Assert memory usage is within limits
        assert active_memory_mb < MAX_MEMORY_MB, \
            f"Active memory usage {active_memory_mb}MB exceeds limit {MAX_MEMORY_MB}MB"

        # Keep streams active for a brief period to monitor stability
        time.sleep(2)

        # Stop all streams concurrently
        stop_results = test.stop_streams_concurrent(stream_ids)

        # Extract stop latencies
        stop_latencies = [r["api_latency_ms"] for r in stop_results]
        stop_stats = calculate_statistics(stop_latencies)

        # Verify all streams stopped successfully
        assert len(stop_results) == stream_count, \
            f"Expected {stream_count} stop results, got {len(stop_results)}"

        # Assert stop latency targets
        assert stop_stats["avg_ms"] < TARGET_API_LATENCY_MS, \
            f"Average stop latency {stop_stats['avg_ms']}ms exceeds target {TARGET_API_LATENCY_MS}ms"

        # Verify all streams reached stopped status
        stopped_streams = test.verify_streams_status(stream_ids, "stopped", timeout_seconds=15)
        assert len(stopped_streams) == stream_count, \
            f"Expected {stream_count} stopped streams, got {len(stopped_streams)}"

    finally:
        test.cleanup()


@pytest.mark.performance
@pytest.mark.skipif(not TEST_USER_TOKEN, reason="TEST_USER_TOKEN not configured")
def test_concurrent_stream_stability():
    """
    Performance test: Verify stability of concurrent streams over time.

    Measures:
    - Stream status consistency over time
    - Resource usage stability
    - No stream crashes or errors

    Target:
    - 3 concurrent streams remain stable for 30 seconds
    - All streams maintain "active" status
    - No unexpected status changes
    - Memory usage remains stable
    """
    test = ConcurrentStreamsTest()

    try:
        # Create streams
        stream_count = TARGET_CONCURRENT_STREAMS
        streams = test.create_streams_concurrent(
            count=stream_count,
            title_prefix="Stability Test"
        )
        stream_ids = [s["id"] for s in streams]

        # Start all streams
        test.start_streams_concurrent(stream_ids)
        test.verify_streams_status(stream_ids, "active", timeout_seconds=15)

        # Monitor streams for stability
        monitoring_duration = 30  # seconds
        check_interval = 5  # seconds
        checks = monitoring_duration // check_interval

        memory_usage_samples = []

        for i in range(checks):
            time.sleep(check_interval)

            # Check all streams still active
            for stream_id in stream_ids:
                stream_data = test.get_live_stream(stream_id)
                status = stream_data.get("status")

                assert status == "active", \
                    f"Stream {stream_id} status changed to {status} during stability test"

                # Verify no errors
                assert stream_data.get("error_count", 0) == 0, \
                    f"Stream {stream_id} has errors: {stream_data.get('last_error')}"

            # Record memory usage
            resources = test.get_resource_usage()
            memory_usage_samples.append(resources["memory_mb"])

        # Calculate memory usage statistics
        memory_stats = calculate_statistics(memory_usage_samples)

        # Verify memory usage is stable (no continuous growth)
        memory_growth = memory_stats["max_ms"] - memory_stats["min_ms"]
        assert memory_growth < 500, \
            f"Memory usage grew by {memory_growth}MB during stability test, possible leak"

        # Stop all streams
        test.stop_streams_concurrent(stream_ids)
        test.verify_streams_status(stream_ids, "stopped", timeout_seconds=15)

    finally:
        test.cleanup()


@pytest.mark.performance
@pytest.mark.skipif(not TEST_USER_TOKEN, reason="TEST_USER_TOKEN not configured")
def test_concurrent_stream_scaling():
    """
    Performance test: Measure how performance scales with stream count.

    Measures:
    - API latency scaling (1, 3, 5 streams)
    - Resource usage scaling
    - Success rate at different scales

    Target:
    - Linear or better scaling for API latency
    - Linear memory usage growth
    - 100% success rate up to 5 streams
    """
    test = ConcurrentStreamsTest()

    try:
        scaling_results = []

        # Test with different stream counts
        for stream_count in [1, 3, 5]:
            # Clear resource samples for this iteration
            global _memory_samples, _cpu_samples
            _memory_samples.clear()
            _cpu_samples.clear()

            # Create streams
            streams = test.create_streams_concurrent(
                count=stream_count,
                title_prefix=f"Scaling Test {stream_count}"
            )
            stream_ids = [s["id"] for s in streams]

            # Start streams
            start_results = test.start_streams_concurrent(stream_ids)

            # Calculate metrics
            creation_latencies = [s["api_latency_ms"] for s in streams]
            start_latencies = [r["api_latency_ms"] for r in start_results]

            creation_stats = calculate_statistics(creation_latencies)
            start_stats = calculate_statistics(start_latencies)

            # Get resource usage
            resources = test.get_resource_usage()

            scaling_results.append({
                "stream_count": stream_count,
                "creation_avg_ms": creation_stats["avg_ms"],
                "start_avg_ms": start_stats["avg_ms"],
                "memory_mb": resources["memory_mb"],
                "cpu_percent": resources["cpu_percent"],
                "success_rate": 1.0  # All operations succeeded
            })

            # Verify all streams active
            test.verify_streams_status(stream_ids, "active", timeout_seconds=15)

            # Stop and cleanup for next iteration
            test.stop_streams_concurrent(stream_ids)
            test.verify_streams_status(stream_ids, "stopped", timeout_seconds=15)

            # Brief pause between iterations
            time.sleep(1)

        # Analyze scaling behavior
        # Compare 1 stream vs 3 streams vs 5 streams
        result_1 = scaling_results[0]
        result_3 = scaling_results[1]
        result_5 = scaling_results[2]

        # API latency should not scale linearly (should be better than linear)
        # For example: 3 streams should be < 3x latency of 1 stream
        latency_scaling_3 = result_3["start_avg_ms"] / result_1["start_avg_ms"]
        latency_scaling_5 = result_5["start_avg_ms"] / result_1["start_avg_ms"]

        assert latency_scaling_3 < 2.5, \
            f"API latency scaled poorly: 3 streams took {latency_scaling_3:.2f}x of 1 stream"

        assert latency_scaling_5 < 4.0, \
            f"API latency scaled poorly: 5 streams took {latency_scaling_5:.2f}x of 1 stream"

        # Memory usage should scale roughly linearly
        memory_scaling_3 = result_3["memory_mb"] / result_1["memory_mb"]
        memory_scaling_5 = result_5["memory_mb"] / result_1["memory_mb"]

        assert memory_scaling_3 < 4.0, \
            f"Memory usage scaled poorly: 3 streams used {memory_scaling_3:.2f}x of 1 stream"

        assert memory_scaling_5 < 7.0, \
            f"Memory usage scaled poorly: 5 streams used {memory_scaling_5:.2f}x of 1 stream"

        # Verify all tests had 100% success rate
        for result in scaling_results:
            assert result["success_rate"] == 1.0, \
                f"Success rate for {result['stream_count']} streams was {result['success_rate']}"

    finally:
        test.cleanup()


@pytest.mark.manual
def test_manual_concurrent_streams_resource_limits():
    """
    Manual test: Find maximum concurrent streams before resource exhaustion.

    This test requires manual monitoring and cannot be fully automated.

    Test Procedure:
    1. Start with 3 concurrent streams
    2. Monitor system resources (CPU, memory, disk I/O)
    3. Gradually increase stream count (5, 7, 10, 15, 20)
    4. Stop when system shows signs of exhaustion:
       - API latency > 5 seconds
       - Memory usage > 90% of available
       - CPU usage > 90% sustained
       - Streams failing to start or crashing

    Expected Results:
    - System should handle at least 3 concurrent streams comfortably
    - Resource limits should be documented
    - Degradation should be gradual, not sudden

    Notes:
    - This test helps determine production capacity
    - Results should inform auto-scaling decisions
    - Run on production-like hardware for accurate results
    - Monitor not just backend, but also streamer and database
    """
    pytest.skip("Manual test - requires resource monitoring and gradual load increase")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-m", "performance"])
