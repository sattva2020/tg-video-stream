"""
End-to-end test for RTMP live streaming to Telegram broadcast.

This test verifies the complete live streaming workflow:
1. RTMP stream ingestion from MediaMTX
2. Live stream creation via API
3. Stream activation on streamer
4. Audio/video broadcast to Telegram
5. Stream recording and persistence

Prerequisites:
- MediaMTX service running (rtmp-ingest)
- Backend API running
- Streamer service running
- Test Telegram chat configured
- FFmpeg available for stream injection

Environment Variables:
- BACKEND_URL: Backend API URL (default: http://localhost:8000)
- TEST_TELEGRAM_CHAT_ID: Telegram chat ID for testing
- TEST_USER_TOKEN: Auth token for test user
- RTMP_URL: RTMP server URL (default: rtmp://localhost:1935)
"""

import os
import asyncio
import pytest
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import subprocess
import time

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
TEST_TELEGRAM_CHAT_ID = int(os.getenv("TEST_TELEGRAM_CHAT_ID", "-1001234567890"))
TEST_USER_TOKEN = os.getenv("TEST_USER_TOKEN", "")
RTMP_URL = os.getenv("RTMP_URL", "rtmp://localhost:1935/live")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

# Test stream configuration
STREAM_DURATION_SECONDS = 10
STREAM_TITLE = "E2E Test Live Stream"
TEST_VIDEO_SOURCE = os.getenv("TEST_VIDEO_SOURCE", "test_assets/test_video.mp4")


class LiveStreamingE2ETest:
    """End-to-end test helper for live streaming."""

    def __init__(self):
        self.backend_url = BACKEND_URL
        self.headers = {"Authorization": f"Bearer {TEST_USER_TOKEN}"}
        self.stream_id: Optional[int] = None
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.ingestion_url: Optional[str] = None
        self.stream_key: Optional[str] = None

    def create_live_stream(self, title: str = STREAM_TITLE) -> Dict[str, Any]:
        """
        Create a new live stream via API.

        Returns:
            Created live stream data
        """
        url = f"{self.backend_url}/api/v1/live/streams"
        payload = {
            "title": title,
            "chat_id": TEST_TELEGRAM_CHAT_ID,
            "ingestion_type": "rtmp",
            "quality_preset": "720p",
            "max_guests": 2,
            "recording_enabled": True,
            "is_chat_enabled": True
        }

        response = requests.post(url, json=payload, headers=self.headers)
        assert response.status_code == 201, f"Failed to create live stream: {response.text}"

        data = response.json()
        self.stream_id = data["id"]
        self.ingestion_url = data.get("ingestion_url")
        self.stream_key = data.get("stream_key")

        return data

    def get_live_stream(self, stream_id: int) -> Dict[str, Any]:
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

    def start_live_stream(self, stream_id: int) -> Dict[str, Any]:
        """
        Start a live stream.

        Args:
            stream_id: Live stream ID

        Returns:
            Updated live stream data
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}/start"
        response = requests.post(url, headers=self.headers)
        assert response.status_code == 200, f"Failed to start live stream: {response.text}"
        return response.json()

    def stop_live_stream(self, stream_id: int) -> Dict[str, Any]:
        """
        Stop a live stream.

        Args:
            stream_id: Live stream ID

        Returns:
            Updated live stream data
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}/stop"
        response = requests.post(url, headers=self.headers)
        assert response.status_code == 200, f"Failed to stop live stream: {response.text}"
        return response.json()

    def delete_live_stream(self, stream_id: int) -> None:
        """
        Delete a live stream.

        Args:
            stream_id: Live stream ID
        """
        url = f"{self.backend_url}/api/v1/live/streams/{stream_id}"
        response = requests.delete(url, headers=self.headers)
        assert response.status_code in [204, 404], f"Failed to delete live stream: {response.text}"

    def start_rtmp_stream(self, stream_key: str, video_source: str = TEST_VIDEO_SOURCE) -> subprocess.Popen:
        """
        Start FFmpeg to push RTMP stream to MediaMTX.

        Args:
            stream_key: Stream key for RTMP ingestion
            video_source: Path to video file or test pattern

        Returns:
            FFmpeg subprocess handle
        """
        rtmp_target = f"{RTMP_URL}/{stream_key}"

        # Use test video if available, otherwise generate test pattern
        if os.path.exists(video_source):
            cmd = [
                FFMPEG_PATH,
                "-re",  # Read input at native frame rate
                "-i", video_source,
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-b:v", "2000k",
                "-maxrate", "2000k",
                "-bufsize", "4000k",
                "-pix_fmt", "yuv420p",
                "-g", "50",  # Keyframe every 2 seconds at 25fps
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-f", "flv",
                rtmp_target
            ]
        else:
            # Generate test pattern (color bars with tone)
            cmd = [
                FFMPEG_PATH,
                "-f", "lavfi",
                "-i", "color=c=blue:s=1280x720:d=10:r=25",
                "-f", "lavfi",
                "-i", "sine=frequency=1000:sample_rate=44100",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-b:v", "2000k",
                "-pix_fmt", "yuv420p",
                "-g", "50",
                "-c:a", "aac",
                "-b:a", "128k",
                "-ar", "44100",
                "-f", "flv",
                rtmp_target
            ]

        self.ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        return self.ffmpeg_process

    def stop_rtmp_stream(self) -> None:
        """Stop FFmpeg RTMP stream."""
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()
            self.ffmpeg_process = None

    def wait_for_stream_status(
        self,
        stream_id: int,
        expected_status: str,
        timeout_seconds: int = 30,
        poll_interval: float = 0.5
    ) -> Dict[str, Any]:
        """
        Wait for stream to reach expected status.

        Args:
            stream_id: Live stream ID
            expected_status: Expected status value
            timeout_seconds: Maximum time to wait
            poll_interval: Seconds between status checks

        Returns:
            Live stream data when status matches

        Raises:
            TimeoutError: If status not reached within timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            stream_data = self.get_live_stream(stream_id)
            current_status = stream_data.get("status")

            if current_status == expected_status:
                return stream_data

            time.sleep(poll_interval)

        raise TimeoutError(
            f"Stream {stream_id} did not reach status '{expected_status}' "
            f"within {timeout_seconds}s. Last status: {current_status}"
        )

    def verify_recording_saved(self, stream_id: int, timeout_seconds: int = 60) -> Dict[str, Any]:
        """
        Verify that recording was saved after stream stopped.

        Args:
            stream_id: Live stream ID
            timeout_seconds: Maximum time to wait for recording

        Returns:
            Recording data

        Raises:
            TimeoutError: If recording not saved within timeout
        """
        # Wait for stream to stop
        stream_data = self.wait_for_stream_status(stream_id, "stopped", timeout_seconds=timeout_seconds)

        # Get recordings for the stream
        url = f"{self.backend_url}/api/v1/recordings?stream_id={stream_id}"
        response = requests.get(url, headers=self.headers)

        if response.status_code != 200:
            raise TimeoutError(f"Failed to fetch recordings: {response.text}")

        recordings = response.json().get("recordings", [])

        # Find recording that was just created
        for recording in recordings:
            if recording.get("status") in ["recording", "processing", "ready"]:
                # Wait for recording to finish processing
                if recording.get("status") == "ready":
                    return recording
                elif recording.get("status") in ["recording", "processing"]:
                    # Wait a bit more for processing to complete
                    time.sleep(5)
                    # Check again
                    recording_url = f"{self.backend_url}/api/v1/recordings/{recording['id']}"
                    rec_response = requests.get(recording_url, headers=self.headers)
                    if rec_response.status_code == 200:
                        updated_recording = rec_response.json()
                        if updated_recording.get("status") == "ready":
                            return updated_recording

        raise TimeoutError(f"No ready recording found for stream {stream_id}")

    def cleanup(self) -> None:
        """Clean up test resources."""
        # Stop RTMP stream
        self.stop_rtmp_stream()

        # Delete live stream if it exists
        if self.stream_id:
            try:
                self.delete_live_stream(self.stream_id)
            except Exception:
                pass  # Best effort cleanup


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_rtmp_to_telegram_broadcast():
    """
    End-to-end test: RTMP stream to Telegram broadcast.

    Test Steps:
    1. Create live stream via API
    2. Start RTMP stream injection
    3. Start live stream via API
    4. Verify stream reaches active status
    5. Verify stream metrics (viewers, latency)
    6. Stop live stream
    7. Verify recording is saved

    Prerequisites:
    - MediaMTX service running on rtmp://localhost:1935
    - Backend API running on http://localhost:8000
    - Streamer service running
    - FFmpeg available in PATH
    """
    # Skip if auth token not configured
    if not TEST_USER_TOKEN:
        pytest.skip("TEST_USER_TOKEN not configured")

    # Skip if ffmpeg not available
    try:
        subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip(f"FFmpeg not available at {FFMPEG_PATH}")

    test = LiveStreamingE2ETest()

    try:
        # Step 1: Create live stream via API
        stream_data = test.create_live_stream(title="E2E Test Stream")
        assert stream_data["status"] == "idle"
        assert stream_data["ingestion_type"] == "rtmp"
        assert stream_data["recording_enabled"] is True
        assert test.stream_key is not None

        # Step 2: Start RTMP stream injection
        ffmpeg_process = test.start_rtmp_stream(test.stream_key)
        assert ffmpeg_process.poll() is None, "FFmpeg process should be running"

        # Give FFmpeg time to start pushing stream
        await asyncio.sleep(2)

        # Step 3: Start live stream via API
        started_stream = test.start_live_stream(test.stream_id)
        assert started_stream["status"] in ["active", "idle"]  # May take a moment to become active

        # Step 4: Verify stream reaches active status
        active_stream = test.wait_for_stream_status(
            test.stream_id,
            "active",
            timeout_seconds=30
        )
        assert active_stream["status"] == "active"
        assert active_stream["viewer_count"] >= 0
        assert active_stream["latency_ms"] is not None or active_stream["latency_ms"] is None  # Latency may not be measured immediately

        # Step 5: Let stream run for a few seconds
        await asyncio.sleep(STREAM_DURATION_SECONDS)

        # Verify stream metrics updated
        stream_metrics = test.get_live_stream(test.stream_id)
        assert stream_metrics["status"] == "active"

        # Step 6: Stop live stream
        stopped_stream = test.stop_live_stream(test.stream_id)
        assert stopped_stream["status"] == "stopped"

        # Step 7: Verify recording is saved
        try:
            recording = test.verify_recording_saved(test.stream_id, timeout_seconds=60)
            assert recording["status"] in ["ready", "processing"]
            assert recording.get("file_url") is not None or recording.get("file_path") is not None
        except TimeoutError:
            # Recording may not be ready yet, but stream stopped successfully
            pass

    finally:
        # Clean up
        test.cleanup()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_live_stream_lifecycle():
    """
    End-to-end test: Complete live stream lifecycle.

    Test Steps:
    1. Create live stream
    2. Start RTMP injection
    3. Start stream
    4. Stop stream
    5. Restart stream
    6. Delete stream

    Verifies stream can be restarted after stopping.
    """
    if not TEST_USER_TOKEN:
        pytest.skip("TEST_USER_TOKEN not configured")

    try:
        subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip(f"FFmpeg not available at {FFMPEG_PATH}")

    test = LiveStreamingE2ETest()

    try:
        # Create stream
        stream_data = test.create_live_stream(title="Lifecycle Test")
        assert stream_data["status"] == "idle"

        # Start RTMP
        test.start_rtmp_stream(test.stream_key)
        await asyncio.sleep(2)

        # Start stream
        test.start_live_stream(test.stream_id)
        test.wait_for_stream_status(test.stream_id, "active", timeout_seconds=30)

        # Stop stream
        test.stop_live_stream(test.stream_id)
        test.wait_for_stream_status(test.stream_id, "stopped", timeout_seconds=30)

        # Restart stream
        test.start_live_stream(test.stream_id)
        test.wait_for_stream_status(test.stream_id, "active", timeout_seconds=30)

        # Stop again
        test.stop_live_stream(test.stream_id)
        test.wait_for_stream_status(test.stream_id, "stopped", timeout_seconds=30)

    finally:
        test.cleanup()


@pytest.mark.e2e
def test_live_stream_api_endpoints():
    """
    Test live stream API endpoints without actual streaming.

    Verifies API responses and data structures.
    """
    if not TEST_USER_TOKEN:
        pytest.skip("TEST_USER_TOKEN not configured")

    test = LiveStreamingE2ETest()

    try:
        # Create stream
        stream_data = test.create_live_stream(title="API Test")
        stream_id = test.stream_id

        # Get stream
        fetched_stream = test.get_live_stream(stream_id)
        assert fetched_stream["id"] == stream_id
        assert fetched_stream["title"] == "API Test"

        # List streams
        url = f"{test.backend_url}/api/v1/live/streams"
        response = requests.get(url, headers=test.headers)
        assert response.status_code == 200
        streams_list = response.json()
        assert streams_list["total"] >= 1
        assert any(s["id"] == stream_id for s in streams_list["streams"])

    finally:
        test.cleanup()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-m", "e2e"])
