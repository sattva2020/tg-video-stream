"""
Import Service for importing playlists and content from various platforms.

Supports importing from:
- YouTube playlists (via yt-dlp)
- Vimeo albums/batches (via yt-dlp)
- Local media libraries (file system scanning)

Integrates with DeduplicationService to detect duplicate content during import.
"""
import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session

from src.models.import_job import ImportJob, ImportPlatform, ImportStatus
from src.models.playlist import Playlist, PlaylistItem
from src.schemas.import_schemas import ImportCreateRequest
from src.services.deduplication_service import DeduplicationService
from src.tasks.media import extract_video_metadata

logger = logging.getLogger(__name__)


class ImportService:
    """Service for managing content import operations from various platforms."""

    def __init__(self):
        """Initialize import service."""
        self.deduplication_service = DeduplicationService()

    def create_import_job(
        self,
        db: Session,
        request: ImportCreateRequest,
        user_id: UUID
    ) -> ImportJob:
        """
        Create a new import job.

        Args:
            db: Database session
            request: Import creation request
            user_id: User initiating the import

        Returns:
            Created ImportJob instance

        Raises:
            ValueError: If request validation fails
        """
        # Validate request based on platform
        if request.platform == ImportPlatform.YOUTUBE and not request.source_url:
            raise ValueError("source_url is required for YouTube imports")
        if request.platform == ImportPlatform.VIMEO and not request.source_url:
            raise ValueError("source_url is required for Vimeo imports")
        if request.platform == ImportPlatform.LOCAL and not request.source_path:
            raise ValueError("source_path is required for local imports")

        # Create import job
        import_job = ImportJob(
            user_id=user_id,
            platform=request.platform,
            source_url=request.source_url,
            source_path=request.source_path,
            channel_id=request.channel_id,
            status=ImportStatus.PENDING,
            options=request.options or {},
            metadata={},
            results={}
        )

        db.add(import_job)
        db.commit()
        db.refresh(import_job)

        logger.info(f"Created import job {import_job.id} for platform {request.platform}")
        return import_job

    def fetch_import_items(
        self,
        platform: ImportPlatform,
        source_url: Optional[str] = None,
        source_path: Optional[str] = None,
        options: Dict[str, Any] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetch items from the import source without importing them.

        Args:
            platform: Import platform
            source_url: URL for YouTube/Vimeo
            source_path: Path for local files
            options: Import options

        Returns:
            Tuple of (items list, metadata dict)
        """
        options = options or {}

        if platform == ImportPlatform.YOUTUBE:
            return self._fetch_youtube_items(source_url, options)
        elif platform == ImportPlatform.VIMEO:
            return self._fetch_vimeo_items(source_url, options)
        elif platform == ImportPlatform.LOCAL:
            return self._fetch_local_items(source_path, options)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    def _fetch_youtube_items(
        self,
        source_url: str,
        options: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetch items from YouTube playlist.

        Args:
            source_url: YouTube playlist URL
            options: Import options

        Returns:
            Tuple of (items list, metadata dict)
        """
        logger.info(f"Fetching YouTube items from {source_url}")

        try:
            # Use existing media.py function
            metadata = extract_video_metadata(source_url)

            if metadata.get("error"):
                raise ValueError(f"Failed to fetch YouTube metadata: {metadata['error']}")

            if not metadata.get("is_playlist"):
                # Single video - convert to playlist format
                return [{
                    "url": metadata.get("url"),
                    "title": metadata.get("title"),
                    "duration": metadata.get("duration"),
                    "thumbnail": metadata.get("thumbnail"),
                    "uploader": metadata.get("uploader"),
                    "type": "youtube"
                }], {
                    "playlist_title": metadata.get("title", "Single Video"),
                    "extractor": metadata.get("extractor")
                }

            # Playlist
            entries = metadata.get("entries", [])
            items = []

            for entry in entries:
                if not entry.get("url"):
                    continue

                items.append({
                    "url": entry["url"],
                    "title": entry.get("title") or entry["url"],
                    "duration": entry.get("duration"),
                    "thumbnail": entry.get("thumbnail"),
                    "uploader": entry.get("uploader"),
                    "type": "youtube"
                })

            logger.info(f"Fetched {len(items)} items from YouTube playlist")
            return items, {
                "playlist_title": metadata.get("playlist_title"),
                "playlist_id": metadata.get("playlist_id"),
                "extractor": metadata.get("extractor")
            }

        except Exception as e:
            logger.exception(f"Error fetching YouTube items")
            raise ValueError(f"Failed to fetch YouTube items: {str(e)}")

    def _fetch_vimeo_items(
        self,
        source_url: str,
        options: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetch items from Vimeo album or batch.

        Args:
            source_url: Vimeo album/batch URL
            options: Import options

        Returns:
            Tuple of (items list, metadata dict)
        """
        logger.info(f"Fetching Vimeo items from {source_url}")

        try:
            # Use yt-dlp for Vimeo as well
            metadata = extract_video_metadata(source_url)

            if metadata.get("error"):
                raise ValueError(f"Failed to fetch Vimeo metadata: {metadata['error']}")

            if not metadata.get("is_playlist"):
                # Single video
                return [{
                    "url": metadata.get("url"),
                    "title": metadata.get("title"),
                    "duration": metadata.get("duration"),
                    "thumbnail": metadata.get("thumbnail"),
                    "uploader": metadata.get("uploader"),
                    "type": "vimeo"
                }], {
                    "album_title": metadata.get("title", "Single Video"),
                    "extractor": metadata.get("extractor")
                }

            # Album/batch
            entries = metadata.get("entries", [])
            items = []

            for entry in entries:
                if not entry.get("url"):
                    continue

                items.append({
                    "url": entry["url"],
                    "title": entry.get("title") or entry["url"],
                    "duration": entry.get("duration"),
                    "thumbnail": entry.get("thumbnail"),
                    "uploader": entry.get("uploader"),
                    "type": "vimeo"
                })

            logger.info(f"Fetched {len(items)} items from Vimeo album")
            return items, {
                "album_title": metadata.get("playlist_title"),
                "album_id": metadata.get("playlist_id"),
                "extractor": metadata.get("extractor")
            }

        except Exception as e:
            logger.exception(f"Error fetching Vimeo items")
            raise ValueError(f"Failed to fetch Vimeo items: {str(e)}")

    def _fetch_local_items(
        self,
        source_path: str,
        options: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetch items from local media library.

        Args:
            source_path: Path to file or directory
            options: Import options (recursive, file_types)

        Returns:
            Tuple of (items list, metadata dict)
        """
        logger.info(f"Fetching local items from {source_path}")

        if not os.path.exists(source_path):
            raise ValueError(f"Path does not exist: {source_path}")

        recursive = options.get("recursive", True)
        file_types = options.get("file_types", [
            ".mp4", ".mkv", ".avi", ".mov", ".wmv",  # Video
            ".mp3", ".wav", ".flac", ".m4a", ".ogg",  # Audio
            ".m3u", ".m3u8"  # Playlists
        ])

        items = []
        total_size = 0

        if os.path.isfile(source_path):
            # Single file
            file_path = source_path
            if any(file_path.lower().endswith(ext) for ext in file_types):
                stat = os.stat(file_path)
                items.append({
                    "url": file_path,
                    "title": os.path.basename(file_path),
                    "duration": None,  # Will be fetched later if needed
                    "type": "local",
                    "file_size": stat.st_size
                })
                total_size += stat.st_size
        else:
            # Directory - scan for media files
            if recursive:
                for root, dirs, files in os.walk(source_path):
                    for filename in files:
                        if any(filename.lower().endswith(ext) for ext in file_types):
                            file_path = os.path.join(root, filename)
                            stat = os.stat(file_path)
                            items.append({
                                "url": file_path,
                                "title": filename,
                                "duration": None,
                                "type": "local",
                                "file_size": stat.st_size
                            })
                            total_size += stat.st_size
            else:
                for filename in os.listdir(source_path):
                    file_path = os.path.join(source_path, filename)
                    if os.path.isfile(file_path) and any(
                        filename.lower().endswith(ext) for ext in file_types
                    ):
                        stat = os.stat(file_path)
                        items.append({
                            "url": file_path,
                            "title": filename,
                            "duration": None,
                            "type": "local",
                            "file_size": stat.st_size
                        })
                        total_size += stat.st_size

        logger.info(f"Fetched {len(items)} local items, total size: {total_size} bytes")
        return items, {
            "source_path": source_path,
            "recursive": recursive,
            "total_size_bytes": total_size,
            "file_count": len(items)
        }

    def process_import(
        self,
        db: Session,
        import_job: ImportJob
    ) -> ImportJob:
        """
        Process an import job synchronously.

        For large imports, use Celery tasks instead (see import_tasks.py).

        Args:
            db: Database session
            import_job: Import job to process

        Returns:
            Updated import job
        """
        logger.info(f"Processing import job {import_job.id}")

        try:
            # Mark as started
            import_job.mark_started()
            db.commit()

            # Fetch items from source
            items, metadata = self.fetch_import_items(
                platform=import_job.platform,
                source_url=import_job.source_url,
                source_path=import_job.source_path,
                options=import_job.options
            )

            # Store metadata
            import_job.metadata = metadata
            import_job.total_items = len(items)
            db.commit()

            # Deduplicate if enabled
            options = import_job.options or {}
            if options.get("deduplicate", True):
                unique_items, duplicate_items, dup_summary = \
                    self.deduplication_service.check_duplicates_batch(
                        db,
                        items,
                        channel_id=str(import_job.channel_id) if import_job.channel_id else None
                    )
                logger.info(f"Deduplication: {dup_summary['unique']} unique, "
                          f"{dup_summary['duplicates']} duplicates")
            else:
                unique_items = items
                duplicate_items = []
                dup_summary = {"unique": len(items), "duplicates": 0}

            # Import unique items
            imported = []
            failed = []
            for i, item in enumerate(unique_items):
                try:
                    # Create playlist item
                    playlist_item = PlaylistItem(
                        url=item["url"],
                        title=item.get("title"),
                        duration=item.get("duration"),
                        type=item.get("type", import_job.platform.value),
                        channel_id=import_job.channel_id,
                        position=i  # Temporary position
                    )

                    # Add thumbnail if available
                    if item.get("thumbnail") and hasattr(playlist_item, "thumbnail"):
                        playlist_item.thumbnail = item["thumbnail"]

                    db.add(playlist_item)
                    imported.append(item)

                    # Update progress
                    import_job.update_progress(
                        processed=i + 1,
                        successful=len(imported),
                        failed=len(failed),
                        skipped=len(duplicate_items)
                    )
                    db.commit()

                except Exception as e:
                    logger.warning(f"Failed to import item {item.get('url')}: {e}")
                    failed.append({**item, "error": str(e)})

            # Store results
            import_job.results = {
                "imported": imported,
                "duplicates": duplicate_items,
                "failed": failed,
                "summary": {
                    "total": len(items),
                    "imported": len(imported),
                    "duplicates": len(duplicate_items),
                    "failed": len(failed)
                }
            }

            # Mark as completed
            import_job.mark_completed()
            db.commit()

            logger.info(f"Import job {import_job.id} completed: "
                       f"{len(imported)} imported, {len(duplicate_items)} duplicates, "
                       f"{len(failed)} failed")

            return import_job

        except Exception as e:
            logger.exception(f"Error processing import job {import_job.id}")
            import_job.mark_failed(str(e))
            db.commit()
            raise

    def create_playlist_from_import(
        self,
        db: Session,
        import_job: ImportJob,
        name: str,
        description: Optional[str] = None,
        user_id: Optional[UUID] = None
    ) -> Playlist:
        """
        Create a playlist from successfully imported items.

        Args:
            db: Database session
            import_job: Completed import job
            name: Playlist name
            description: Optional description
            user_id: User ID for playlist ownership

        Returns:
            Created playlist

        Raises:
            ValueError: If import job not completed or no items imported
        """
        if import_job.status != ImportStatus.COMPLETED:
            raise ValueError("Can only create playlist from completed import job")

        results = import_job.results or {}
        imported_items = results.get("imported", [])

        if not imported_items:
            raise ValueError("No items were imported successfully")

        # Calculate total duration
        total_duration = sum(item.get("duration", 0) for item in imported_items)

        # Create playlist
        playlist = Playlist(
            user_id=user_id or import_job.user_id,
            name=name,
            description=description or f"Imported from {import_job.platform.value}",
            is_public=False,
            color="#8B5CF6",  # Purple for imports
            icon="download",
            items=imported_items,
            items_count=len(imported_items),
            total_duration=total_duration
        )

        db.add(playlist)
        db.commit()
        db.refresh(playlist)

        logger.info(f"Created playlist {playlist.id} from import job {import_job.id}")
        return playlist

    def cancel_import(self, db: Session, import_job: ImportJob) -> ImportJob:
        """
        Cancel an import job.

        Args:
            db: Database session
            import_job: Import job to cancel

        Returns:
            Updated import job

        Raises:
            ValueError: If job cannot be cancelled
        """
        if import_job.status in [ImportStatus.COMPLETED, ImportStatus.FAILED, ImportStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel job with status {import_job.status}")

        import_job.mark_cancelled()
        db.commit()

        logger.info(f"Cancelled import job {import_job.id}")
        return import_job

    def pause_import(self, db: Session, import_job: ImportJob) -> ImportJob:
        """
        Pause an import job.

        Args:
            db: Database session
            import_job: Import job to pause

        Returns:
            Updated import job

        Raises:
            ValueError: If job cannot be paused
        """
        if import_job.status != ImportStatus.IN_PROGRESS:
            raise ValueError("Can only pause in-progress jobs")

        import_job.pause()
        db.commit()

        logger.info(f"Paused import job {import_job.id}")
        return import_job

    def resume_import(self, db: Session, import_job: ImportJob) -> ImportJob:
        """
        Resume a paused import job.

        Args:
            db: Database session
            import_job: Import job to resume

        Returns:
            Updated import job

        Raises:
            ValueError: If job cannot be resumed
        """
        if import_job.status != ImportStatus.PAUSED:
            raise ValueError("Can only resume paused jobs")

        import_job.resume()
        db.commit()

        logger.info(f"Resumed import job {import_job.id}")
        return import_job

    def get_import_summary(self, import_job: ImportJob) -> Dict[str, Any]:
        """
        Get a summary of import job results.

        Args:
            import_job: Import job

        Returns:
            Summary dict with statistics
        """
        results = import_job.results or {}
        summary = results.get("summary", {})

        duration = None
        if import_job.started_at and import_job.completed_at:
            duration = int((import_job.completed_at - import_job.started_at).total_seconds())

        errors = []
        failed_items = results.get("failed", [])
        for item in failed_items:
            if item.get("error"):
                errors.append(item["error"])

        return {
            "job_id": str(import_job.id),
            "platform": import_job.platform.value,
            "status": import_job.status.value,
            "total_items": summary.get("total", import_job.total_items or 0),
            "imported_count": summary.get("imported", import_job.successful_items),
            "duplicate_count": summary.get("duplicates", import_job.skipped_items),
            "failed_count": summary.get("failed", import_job.failed_items),
            "duration_seconds": duration,
            "errors": errors[:10]  # Limit to first 10 errors
        }


# Singleton instance
import_service = ImportService()
