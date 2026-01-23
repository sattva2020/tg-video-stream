"""
RecordingService for managing live stream recordings.

Features:
- Start/stop recording for live streams
- Recording lifecycle management
- File format validation
- Recording metadata tracking
"""

import logging
import os
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from src.models import LiveStream, Recording, RecordingStatus, RecordingFormat


logger = logging.getLogger(__name__)


class RecordingService:
    """Manages live stream recordings."""

    def __init__(self, db_session: Session):
        """Initialize recording service."""
        self.db = db_session
        self.logger = logger

        # Recording storage path from environment
        self.recordings_path = os.getenv("RECORDINGS_PATH", "/recordings")

    def validate_recording_path(self, path: str) -> bool:
        """
        Validate recording path is within allowed directory.

        Args:
            path: File path to validate

        Returns:
            True if path is valid

        Raises:
            ValueError: If path is outside recordings directory
        """
        try:
            recordings_dir = Path(self.recordings_path).resolve()
            file_path = Path(path).resolve()

            # Check path is within recordings directory
            if not str(file_path).startswith(str(recordings_dir)):
                raise ValueError(f"Recording path must be within {self.recordings_path}")

            # Check parent directory exists
            if not file_path.parent.exists():
                raise ValueError(f"Recording directory does not exist: {file_path.parent}")

            return True

        except Exception as e:
            raise ValueError(f"Recording path validation failed: {e}")

    def generate_recording_path(self, live_stream_id: str, format: RecordingFormat = RecordingFormat.MP4) -> str:
        """
        Generate a unique file path for recording.

        Args:
            live_stream_id: Live stream ID
            format: Recording format

        Returns:
            Absolute file path for recording
        """
        # Create recordings directory if needed
        recordings_dir = Path(self.recordings_path)
        recordings_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        extension = format.value
        filename = f"live_{live_stream_id}_{timestamp}.{extension}"

        return str(recordings_dir / filename)

    def start_recording(
        self,
        live_stream_id: str,
        format: RecordingFormat = RecordingFormat.MP4,
        video_codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        bitrate: Optional[int] = None,
        resolution: Optional[str] = None
    ) -> Recording:
        """
        Start recording for a live stream.

        Args:
            live_stream_id: Live stream ID to record
            format: Recording format (default: MP4)
            video_codec: Video codec (e.g., "h264", "vp9")
            audio_codec: Audio codec (e.g., "aac", "opus")
            bitrate: Target bitrate in kbps
            resolution: Video resolution (e.g., "1920x1080")

        Returns:
            Created Recording object

        Raises:
            ValueError: If stream not found or already recording
        """
        # Get live stream
        live_stream = self.db.query(LiveStream).filter(LiveStream.id == live_stream_id).first()
        if not live_stream:
            raise ValueError(f"Live stream not found: {live_stream_id}")

        # Check if already recording
        if live_stream.active_recording_id:
            existing_recording = self.db.query(Recording).filter(
                Recording.id == live_stream.active_recording_id
            ).first()
            if existing_recording and existing_recording.status == RecordingStatus.RECORDING:
                raise ValueError(f"Live stream already recording: {live_stream_id}")

        # Generate recording path
        file_path = self.generate_recording_path(live_stream_id, format)
        self.validate_recording_path(file_path)

        # Create recording record
        recording = Recording(
            live_stream_id=live_stream_id,
            file_path=file_path,
            status=RecordingStatus.RECORDING,
            started_at=datetime.utcnow(),
            format=format,
            video_codec=video_codec,
            audio_codec=audio_codec or "aac",  # Default audio codec
            bitrate=bitrate,
            resolution=resolution
        )

        self.db.add(recording)
        self.db.commit()
        self.db.refresh(recording)

        # Update live stream with active recording
        live_stream.active_recording_id = recording.id
        self.db.commit()

        self.logger.info(f"Started recording {recording.id} for live stream {live_stream_id}")
        return recording

    def stop_recording(self, recording_id: str, final_duration: Optional[int] = None, final_file_size: Optional[int] = None) -> Recording:
        """
        Stop recording and mark as processing.

        Args:
            recording_id: Recording ID to stop
            final_duration: Optional final duration in seconds
            final_file_size: Optional final file size in bytes

        Returns:
            Updated Recording object

        Raises:
            ValueError: If recording not found or not recording
        """
        recording = self.db.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            raise ValueError(f"Recording not found: {recording_id}")

        if recording.status != RecordingStatus.RECORDING:
            raise ValueError(f"Recording not in progress: {recording_id} (status: {recording.status})")

        # Update recording
        recording.status = RecordingStatus.PROCESSING
        recording.ended_at = datetime.utcnow()
        recording.duration = final_duration
        recording.file_size = final_file_size

        self.db.commit()
        self.db.refresh(recording)

        # Clear active recording from live stream
        live_stream = self.db.query(LiveStream).filter(LiveStream.id == recording.live_stream_id).first()
        if live_stream and live_stream.active_recording_id == recording_id:
            live_stream.active_recording_id = None
            self.db.commit()

        self.logger.info(f"Stopped recording {recording_id} for live stream {recording.live_stream_id}")
        return recording

    def mark_recording_ready(
        self,
        recording_id: str,
        file_url: str,
        duration: int,
        file_size: int,
        thumbnail_url: Optional[str] = None,
        preview_url: Optional[str] = None
    ) -> Recording:
        """
        Mark recording as ready for playback.

        Args:
            recording_id: Recording ID to update
            file_url: URL for accessing the recording
            duration: Final duration in seconds
            file_size: Final file size in bytes
            thumbnail_url: Optional thumbnail URL
            preview_url: Optional preview video URL

        Returns:
            Updated Recording object

        Raises:
            ValueError: If recording not found
        """
        recording = self.db.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            raise ValueError(f"Recording not found: {recording_id}")

        recording.status = RecordingStatus.READY
        recording.file_url = file_url
        recording.duration = duration
        recording.file_size = file_size
        recording.thumbnail_url = thumbnail_url
        recording.preview_url = preview_url

        self.db.commit()
        self.db.refresh(recording)

        self.logger.info(f"Recording {recording_id} marked as ready")
        return recording

    def mark_recording_failed(self, recording_id: str, error_message: str) -> Recording:
        """
        Mark recording as failed.

        Args:
            recording_id: Recording ID to update
            error_message: Error description

        Returns:
            Updated Recording object

        Raises:
            ValueError: If recording not found
        """
        recording = self.db.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            raise ValueError(f"Recording not found: {recording_id}")

        recording.status = RecordingStatus.ERROR
        recording.error_message = error_message
        recording.ended_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(recording)

        # Clear active recording from live stream
        live_stream = self.db.query(LiveStream).filter(LiveStream.id == recording.live_stream_id).first()
        if live_stream and live_stream.active_recording_id == recording_id:
            live_stream.active_recording_id = None
            self.db.commit()

        self.logger.error(f"Recording {recording_id} failed: {error_message}")
        return recording

    def get_recording(self, recording_id: str) -> Optional[Recording]:
        """
        Get recording by ID.

        Args:
            recording_id: Recording ID

        Returns:
            Recording object or None if not found
        """
        return self.db.query(Recording).filter(Recording.id == recording_id).first()

    def get_recordings_for_stream(self, live_stream_id: str, status: Optional[RecordingStatus] = None) -> List[Recording]:
        """
        Get all recordings for a live stream.

        Args:
            live_stream_id: Live stream ID
            status: Optional status filter

        Returns:
            List of Recording objects
        """
        query = self.db.query(Recording).filter(Recording.live_stream_id == live_stream_id)

        if status:
            query = query.filter(Recording.status == status)

        return query.order_by(Recording.created_at.desc()).all()

    def get_active_recording(self, live_stream_id: str) -> Optional[Recording]:
        """
        Get currently active recording for live stream.

        Args:
            live_stream_id: Live stream ID

        Returns:
            Active Recording object or None
        """
        live_stream = self.db.query(LiveStream).filter(LiveStream.id == live_stream_id).first()
        if not live_stream or not live_stream.active_recording_id:
            return None

        recording = self.db.query(Recording).filter(
            Recording.id == live_stream.active_recording_id
        ).first()

        # Only return if still recording
        if recording and recording.status == RecordingStatus.RECORDING:
            return recording

        return None

    def delete_recording(self, recording_id: str) -> bool:
        """
        Delete recording (mark as deleted, remove file).

        Args:
            recording_id: Recording ID to delete

        Returns:
            True if deleted successfully

        Raises:
            ValueError: If recording not found
        """
        recording = self.db.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            raise ValueError(f"Recording not found: {recording_id}")

        # Mark as deleted
        recording.status = RecordingStatus.DELETED
        self.db.commit()

        # Try to delete file
        try:
            file_path = Path(recording.file_path)
            if file_path.exists():
                file_path.unlink()
                self.logger.info(f"Deleted recording file: {recording.file_path}")
        except Exception as e:
            self.logger.warning(f"Failed to delete recording file {recording.file_path}: {e}")

        self.logger.info(f"Recording {recording_id} marked as deleted")
        return True

    def get_all_recordings(
        self,
        status: Optional[RecordingStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Recording]:
        """
        Get all recordings with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum records to return
            offset: Records to skip

        Returns:
            List of Recording objects
        """
        query = self.db.query(Recording)

        if status:
            query = query.filter(Recording.status == status)

        return query.order_by(Recording.created_at.desc()).limit(limit).offset(offset).all()

    def cleanup_old_recordings(self, days: int = 30) -> int:
        """
        Delete old recordings marked as READY older than specified days.

        Args:
            days: Number of days to keep recordings

        Returns:
            Number of recordings deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        old_recordings = self.db.query(Recording).filter(
            Recording.status == RecordingStatus.READY,
            Recording.created_at < cutoff_date
        ).all()

        deleted_count = 0
        for recording in old_recordings:
            try:
                self.delete_recording(str(recording.id))
                deleted_count += 1
            except Exception as e:
                self.logger.error(f"Failed to delete old recording {recording.id}: {e}")

        self.logger.info(f"Cleaned up {deleted_count} old recordings (older than {days} days)")
        return deleted_count
