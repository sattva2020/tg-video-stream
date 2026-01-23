"""
VideoValidationService for video format validation and transcoding orchestration.

Manages:
- Video validation for Telegram compatibility
- Codec and format checking (h264, h265, aac, mp3, opus)
- Video orientation detection
- Transcoding pipeline orchestration
- Validation result caching

Uses VideoValidator from streamer/video_validator
Integrates with Celery for background transcoding tasks
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

from src.database import get_db

logger = logging.getLogger(__name__)

# Redis keys for validation result caching
VALIDATION_RESULT_KEY = "video:validation:{validation_id}"
VALIDATION_RESULT_TTL = 3600  # 1 hour


class VideoValidationService:
    """
    Service for video validation and transcoding orchestration.

    Provides:
    - Video URL validation for Telegram compatibility
    - Codec and format checking
    - Orientation detection
    - Validation result caching
    - Transcoding task triggering (via Celery)

    Uses VideoValidator from streamer for actual validation logic.
    """

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize video validation service.

        Args:
            db_session: SQLAlchemy database session (optional, will use get_db if not provided)
        """
        self._db = db_session
        self._owns_db = db_session is None
        self._redis: Optional[Any] = None
        self.logger = logger

    @property
    def db(self) -> Session:
        """Get database session. Auto-creates if needed."""
        if self._db is None:
            from src.database import SessionLocal
            self._db = SessionLocal()
            self._owns_db = True
        return self._db

    def close(self):
        """Close database session if we own it."""
        if self._owns_db and self._db is not None:
            try:
                self._db.close()
            except Exception:
                pass
            self._db = None
            self._owns_db = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()
        return False

    async def _get_redis(self):
        """Get or create Redis connection for validation caching."""
        if aioredis is None:
            return None

        if self._redis is None:
            import os
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            try:
                self._redis = aioredis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception as e:
                self.logger.warning(f"Redis connection failed: {e}")
                self._redis = None

        return self._redis

    async def validate_video(
        self,
        url: str,
        timeout: int = 10,
        cache_result: bool = True
    ) -> Dict[str, Any]:
        """
        Validate video URL for Telegram compatibility.

        Args:
            url: Video URL to validate
            timeout: FFprobe timeout in seconds (default: 10)
            cache_result: Whether to cache validation result in Redis

        Returns:
            Validation result dictionary with:
            - validation_id: Unique validation ID
            - valid: bool - whether video passed basic validation
            - is_compatible: bool - whether video is compatible with Telegram
            - video_codec: str or None
            - audio_codec: str or None
            - format: str or None
            - has_orientation: bool
            - orientation_value: int or None
            - errors: list of error strings
            - warnings: list of warning strings
            - transcoding_required: bool
            - transcoding_reasons: list of reasons

        Raises:
            Exception: If validation fails (URL inaccessible, invalid video, etc.)
        """
        try:
            # Import VideoValidator from streamer
            from streamer.video_validator import VideoValidator

            self.logger.info(f"Validating video URL: {url}")

            # Create validator instance
            validator = VideoValidator()

            # Perform validation
            result = await validator.validate_url(url, timeout=timeout)

            # Check if transcoding is required
            transcoding_check = validator.check_transcoding_required(result)

            # Generate validation ID
            validation_id = str(uuid.uuid4())

            # Build response dict
            response = {
                "validation_id": validation_id,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "valid": result.valid,
                "is_compatible": result.is_compatible,
                "video_codec": result.video_codec,
                "audio_codec": result.audio_codec,
                "format": result.format,
                "has_orientation": result.has_orientation,
                "orientation_value": result.orientation_value,
                "errors": result.errors,
                "warnings": result.warnings,
                "transcoding_required": transcoding_check["required"],
                "transcoding_reasons": transcoding_check["reasons"],
            }

            # Cache result if requested
            if cache_result:
                await self._cache_validation_result(validation_id, response)

            self.logger.info(
                f"Validation complete for {url}: compatible={result.is_compatible}, "
                f"transcoding_required={transcoding_check['required']}"
            )

            return response

        except ImportError as e:
            self.logger.error(f"Failed to import VideoValidator: {e}")
            raise Exception(f"Video validation module not available: {e}")
        except Exception as e:
            self.logger.error(f"Error validating video {url}: {e}", exc_info=True)
            raise

    async def _cache_validation_result(
        self,
        validation_id: str,
        result: Dict[str, Any]
    ) -> bool:
        """
        Cache validation result in Redis.

        Args:
            validation_id: Unique validation ID
            result: Validation result dictionary

        Returns:
            True if cached successfully
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return False

            key = VALIDATION_RESULT_KEY.format(validation_id=validation_id)

            # Convert result to JSON-serializable format
            import json
            cache_data = json.dumps(result)

            await redis.setex(key, VALIDATION_RESULT_TTL, cache_data)

            self.logger.debug(f"Cached validation result: {validation_id}")
            return True

        except Exception as e:
            self.logger.warning(f"Error caching validation result: {e}")
            return False

    async def get_validation_result(self, validation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get cached validation result by ID.

        Args:
            validation_id: Validation ID from validate_video()

        Returns:
            Validation result dictionary or None if not found/expired
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return None

            key = VALIDATION_RESULT_KEY.format(validation_id=validation_id)
            cached = await redis.get(key)

            if not cached:
                self.logger.debug(f"Validation result not found or expired: {validation_id}")
                return None

            import json
            result = json.loads(cached)

            self.logger.debug(f"Retrieved cached validation result: {validation_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error getting validation result: {e}", exc_info=True)
            return None

    async def validate_codecs(
        self,
        video_codec: Optional[str],
        audio_codec: Optional[str]
    ) -> Dict[str, Any]:
        """
        Validate video and audio codecs for Telegram compatibility.

        Args:
            video_codec: Video codec name (e.g., 'h264', 'hevc')
            audio_codec: Audio codec name (e.g., 'aac', 'opus')

        Returns:
            Dict with 'valid' bool and 'errors' list

        Examples:
            >>> service = VideoValidationService()
            >>> result = await service.validate_codecs('h264', 'aac')
            >>> print(result['valid'])  # True
        """
        try:
            from streamer.video_validator import VideoValidator

            validator = VideoValidator()
            result = validator.validate_codecs(video_codec, audio_codec)

            self.logger.debug(
                f"Codec validation: video={video_codec}, audio={audio_codec}, "
                f"valid={result['valid']}"
            )

            return result

        except ImportError as e:
            self.logger.error(f"Failed to import VideoValidator: {e}")
            return {"valid": False, "errors": [str(e)]}
        except Exception as e:
            self.logger.error(f"Error validating codecs: {e}", exc_info=True)
            return {"valid": False, "errors": [str(e)]}

    async def check_transcoding_required(
        self,
        validation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if transcoding is required based on validation result.

        Args:
            validation_result: Result dict from validate_video()

        Returns:
            Dict with 'required' bool and 'reasons' list

        Examples:
            >>> service = VideoValidationService()
            >>> result = await service.validate_video("https://example.com/video.avi")
            >>> check = await service.check_transcoding_required(result)
            >>> if check['required']:
            ...     print(f"Transcoding needed: {check['reasons']}")
        """
        try:
            from streamer.video_validator import VideoValidator, ValidationResult

            # Reconstruct ValidationResult from dict
            result = ValidationResult(
                valid=validation_result.get("valid", False),
                is_compatible=validation_result.get("is_compatible", False),
                video_codec=validation_result.get("video_codec"),
                audio_codec=validation_result.get("audio_codec"),
                format=validation_result.get("format"),
                has_orientation=validation_result.get("has_orientation", False),
                orientation_value=validation_result.get("orientation_value"),
                errors=validation_result.get("errors", []),
                warnings=validation_result.get("warnings", []),
            )

            validator = VideoValidator()
            check = validator.check_transcoding_required(result)

            self.logger.debug(
                f"Transcoding check: required={check['required']}, "
                f"reasons={len(check['reasons'])}"
            )

            return check

        except Exception as e:
            self.logger.error(f"Error checking transcoding requirement: {e}", exc_info=True)
            return {"required": False, "reasons": []}

    async def list_recent_validations(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List recent validation IDs from Redis cache.

        Note: This is a best-effort list since Redis doesn't guarantee
        key ordering. Returns empty list if Redis is unavailable.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of validation info dicts with validation_id, url, timestamp
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return []

            # Scan for validation keys
            pattern = VALIDATION_RESULT_KEY.replace("{validation_id}", "*")
            keys = []
            async for key in redis.scan_iter(match=pattern, count=limit):
                keys.append(key)

            if not keys:
                return []

            # Fetch all validation results
            results = []
            import json

            for key in keys[:limit]:
                try:
                    cached = await redis.get(key)
                    if cached:
                        data = json.loads(cached)
                        results.append({
                            "validation_id": data.get("validation_id"),
                            "url": data.get("url"),
                            "timestamp": data.get("timestamp"),
                            "is_compatible": data.get("is_compatible"),
                            "transcoding_required": data.get("transcoding_required"),
                        })
                except Exception:
                    continue

            # Sort by timestamp descending
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            self.logger.debug(f"Listed {len(results)} recent validations")
            return results

        except Exception as e:
            self.logger.error(f"Error listing recent validations: {e}", exc_info=True)
            return []

    async def delete_validation_result(self, validation_id: str) -> bool:
        """
        Delete cached validation result.

        Args:
            validation_id: Validation ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            redis = await self._get_redis()
            if not redis:
                return False

            key = VALIDATION_RESULT_KEY.format(validation_id=validation_id)
            await redis.delete(key)

            self.logger.debug(f"Deleted validation result: {validation_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error deleting validation result: {e}", exc_info=True)
            return False
