"""
ImportJob model for tracking content import operations.

Supports importing playlists and content from various platforms:
- YouTube playlists
- Vimeo albums
- Local media libraries

Tracks import progress, errors, and results.
"""
import uuid
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, func, BigInteger, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.database import Base, GUID


class ImportStatus(str, PyEnum):
    """Status of import jobs."""
    PENDING = "pending"              # Waiting to start
    IN_PROGRESS = "in_progress"      # Currently processing
    COMPLETED = "completed"          # Finished successfully
    FAILED = "failed"                # Failed with errors
    CANCELLED = "cancelled"          # Cancelled by user
    PAUSED = "paused"                # Paused by user (for resume support)


class ImportPlatform(str, PyEnum):
    """Supported import platforms."""
    YOUTUBE = "youtube"              # YouTube playlists
    VIMEO = "vimeo"                  # Vimeo albums/batches
    LOCAL = "local"                  # Local media files/folders


class ImportJob(Base):
    """Track import operations for content from various platforms."""

    __tablename__ = "import_jobs"

    # Primary key
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)

    # User who initiated the import
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Target channel (optional - if importing to specific channel)
    channel_id = Column(GUID(), ForeignKey("channels.id", ondelete="SET NULL"), nullable=True, index=True)

    # Platform and source
    platform = Column(
        Enum(ImportPlatform, name="import_platform"),
        nullable=False,
        index=True
    )
    source_url = Column(String(2000), nullable=True)  # For YouTube/Vimeo URLs
    source_path = Column(String(2000), nullable=True)  # For local file paths

    # Import status
    status = Column(
        Enum(ImportStatus, name="import_status"),
        nullable=False,
        default=ImportStatus.PENDING,
        index=True
    )

    # Progress tracking
    total_items = Column(BigInteger, nullable=True)       # Total items to import
    processed_items = Column(BigInteger, default=0)       # Items processed so far
    successful_items = Column(BigInteger, default=0)      # Successfully imported
    failed_items = Column(BigInteger, default=0)          # Failed to import
    skipped_items = Column(BigInteger, default=0)         # Duplicates or skipped
    progress_percentage = Column(BigInteger, default=0)   # 0-100

    # Error handling
    error_message = Column(Text, nullable=True)           # Last error message
    error_details = Column(JSONB, nullable=True)          # Detailed error info

    # Import options and metadata
    options = Column(JSONB, nullable=True, default=dict)  # {deduplicate: true, quality: "best"}
    metadata = Column(JSONB, nullable=True, default=dict)  # Platform-specific data

    # Results summary
    results = Column(JSONB, nullable=True, default=dict)   # {imported: [], duplicates: [], failed: []}

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="import_jobs")
    channel = relationship("src.models.telegram.Channel", backref="import_jobs")

    def __repr__(self):
        return f"<ImportJob(id={self.id}, platform={self.platform}, status={self.status})>"

    def update_progress(self, processed: int, successful: int = None, failed: int = None, skipped: int = None):
        """Update progress and calculate percentage."""
        self.processed_items = processed

        if successful is not None:
            self.successful_items = successful
        if failed is not None:
            self.failed_items = failed
        if skipped is not None:
            self.skipped_items = skipped

        # Calculate progress percentage
        if self.total_items and self.total_items > 0:
            self.progress_percentage = int((self.processed_items / self.total_items) * 100)
        else:
            self.progress_percentage = 0

    def mark_started(self):
        """Mark import as started."""
        self.status = ImportStatus.IN_PROGRESS
        from datetime import datetime, timezone
        self.started_at = datetime.now(timezone.utc)

    def mark_completed(self):
        """Mark import as completed."""
        self.status = ImportStatus.COMPLETED
        from datetime import datetime, timezone
        self.completed_at = datetime.now(timezone.utc)
        self.progress_percentage = 100

    def mark_failed(self, error_message: str, error_details: dict = None):
        """Mark import as failed."""
        self.status = ImportStatus.FAILED
        self.error_message = error_message
        if error_details:
            self.error_details = error_details
        from datetime import datetime, timezone
        self.completed_at = datetime.now(timezone.utc)

    def mark_cancelled(self):
        """Mark import as cancelled."""
        self.status = ImportStatus.CANCELLED
        from datetime import datetime, timezone
        self.completed_at = datetime.now(timezone.utc)

    def pause(self):
        """Pause import operation."""
        self.status = ImportStatus.PAUSED

    def resume(self):
        """Resume paused import operation."""
        if self.status == ImportStatus.PAUSED:
            self.status = ImportStatus.IN_PROGRESS
