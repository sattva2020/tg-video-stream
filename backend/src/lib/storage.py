"""
Supabase Storage abstraction for the Telegram broadcast platform.

This module provides a clean interface for file operations with Supabase Storage,
including upload, download, and management of video files with error handling and retry logic.
"""

import os
from typing import BinaryIO, Optional, Dict, Any, List
from pathlib import Path
import aiofiles
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .error_handlers import ServiceUnavailableError, ValidationError


class SupabaseStorageClient:
    """Client for interacting with Supabase Storage."""

    def __init__(self):
        """Initialize Supabase Storage client with configuration."""
        self.project_url = os.getenv("SUPABASE_URL")
        self.api_key = os.getenv("SUPABASE_ANON_KEY")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.bucket_name = os.getenv("SUPABASE_BUCKET", "videos")

        if not all([self.project_url, self.api_key]):
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY environment variables are required")

        # Storage API base URL
        self.storage_url = f"{self.project_url}/storage/v1"

        # HTTP client session
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Enter async context manager."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self.session:
            await self.session.close()

    def _get_headers(self, use_service_key: bool = False) -> Dict[str, str]:
        """
        Get headers for Supabase API requests.

        Args:
            use_service_key: Whether to use service role key for admin operations

        Returns:
            Dict[str, str]: Request headers
        """
        key = self.service_role_key if use_service_key and self.service_role_key else self.api_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, ServiceUnavailableError))
    )
    async def upload_file(
        self,
        file_path: str,
        file_obj: BinaryIO,
        content_type: str,
        cache_control: str = "3600"
    ) -> Dict[str, Any]:
        """
        Upload a file to Supabase Storage with retry logic.

        Args:
            file_path: Path where to store the file in the bucket
            file_obj: File-like object to upload
            content_type: MIME content type of the file
            cache_control: Cache control header value

        Returns:
            Dict[str, Any]: Upload result with file metadata

        Raises:
            ServiceUnavailableError: If upload fails after retries
        """
        if not self.session:
            raise RuntimeError("Storage client not initialized. Use async context manager.")

        upload_url = f"{self.storage_url}/object/{self.bucket_name}/{file_path}"

        headers = self._get_headers(use_service_key=True)
        headers.update({
            "Content-Type": content_type,
            "Cache-Control": cache_control
        })

        # Read file content
        file_obj.seek(0)
        file_data = file_obj.read()

        try:
            async with self.session.post(
                upload_url,
                data=file_data,
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "file_path": file_path,
                        "file_size": len(file_data),
                        "content_type": content_type,
                        "bucket": self.bucket_name,
                        "metadata": result
                    }
                else:
                    error_text = await response.text()
                    raise ServiceUnavailableError(
                        "supabase_storage",
                        {"status_code": response.status, "error": error_text}
                    )

        except aiohttp.ClientError as e:
            raise ServiceUnavailableError(
                "supabase_storage",
                {"error": str(e), "operation": "upload"}
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, ServiceUnavailableError))
    )
    async def generate_signed_url(
        self,
        file_path: str,
        expires_in: int = 3600
    ) -> str:
        """
        Generate a signed URL for downloading a file.

        Args:
            file_path: Path of the file in the bucket
            expires_in: URL expiration time in seconds (default 1 hour)

        Returns:
            str: Signed download URL

        Raises:
            ServiceUnavailableError: If URL generation fails
        """
        if not self.session:
            raise RuntimeError("Storage client not initialized. Use async context manager.")

        url = f"{self.storage_url}/object/sign/{self.bucket_name}/{file_path}"

        headers = self._get_headers()
        params = {"expiresIn": expires_in}

        try:
            async with self.session.post(
                url,
                headers=headers,
                json=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("signedURL", "")
                else:
                    error_text = await response.text()
                    raise ServiceUnavailableError(
                        "supabase_storage",
                        {"status_code": response.status, "error": error_text}
                    )

        except aiohttp.ClientError as e:
            raise ServiceUnavailableError(
                "supabase_storage",
                {"error": str(e), "operation": "generate_signed_url"}
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, ServiceUnavailableError))
    )
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from Supabase Storage.

        Args:
            file_path: Path of the file to delete

        Returns:
            bool: True if deletion successful

        Raises:
            ServiceUnavailableError: If deletion fails
        """
        if not self.session:
            raise RuntimeError("Storage client not initialized. Use async context manager.")

        url = f"{self.storage_url}/object/{self.bucket_name}/{file_path}"

        headers = self._get_headers(use_service_key=True)

        try:
            async with self.session.delete(url, headers=headers) as response:
                if response.status in [200, 204]:
                    return True
                else:
                    error_text = await response.text()
                    raise ServiceUnavailableError(
                        "supabase_storage",
                        {"status_code": response.status, "error": error_text}
                    )

        except aiohttp.ClientError as e:
            raise ServiceUnavailableError(
                "supabase_storage",
                {"error": str(e), "operation": "delete"}
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, ServiceUnavailableError))
    )
    async def list_files(
        self,
        path: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List files in a bucket path.

        Args:
            path: Path prefix to list files from
            limit: Maximum number of files to return
            offset: Offset for pagination

        Returns:
            List[Dict[str, Any]]: List of file metadata

        Raises:
            ServiceUnavailableError: If listing fails
        """
        if not self.session:
            raise RuntimeError("Storage client not initialized. Use async context manager.")

        url = f"{self.storage_url}/object/list/{self.bucket_name}"

        headers = self._get_headers()
        params = {
            "limit": limit,
            "offset": offset
        }
        if path:
            params["prefix"] = path

        try:
            async with self.session.post(
                url,
                headers=headers,
                json=params
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    raise ServiceUnavailableError(
                        "supabase_storage",
                        {"status_code": response.status, "error": error_text}
                    )

        except aiohttp.ClientError as e:
            raise ServiceUnavailableError(
                "supabase_storage",
                {"error": str(e), "operation": "list"}
            )

    async def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific file.

        Args:
            file_path: Path of the file

        Returns:
            Optional[Dict[str, Any]]: File metadata if found, None otherwise
        """
        try:
            files = await self.list_files(path=file_path, limit=1)
            if files and len(files) > 0:
                return files[0]
            return None
        except ServiceUnavailableError:
            return None

    async def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            file_path: Path of the file

        Returns:
            bool: True if file exists
        """
        metadata = await self.get_file_metadata(file_path)
        return metadata is not None


class StorageService:
    """High-level storage service with additional utilities."""

    def __init__(self):
        """Initialize storage service."""
        self.client = SupabaseStorageClient()

    async def __aenter__(self):
        """Enter async context manager."""
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def upload_video_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        user_id: int,
        content_type: str = "video/mp4"
    ) -> Dict[str, Any]:
        """
        Upload a video file with user-specific path structure.

        Args:
            file_obj: Video file object
            filename: Original filename
            user_id: User ID for path organization
            content_type: MIME content type

        Returns:
            Dict[str, Any]: Upload result
        """
        # Generate path: videos/{user_id}/{timestamp}_{filename}
        import uuid
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_path = f"videos/{user_id}/{timestamp}_{unique_id}_{filename}"

        # Validate file size (should be done before calling this method)
        file_obj.seek(0, 2)  # Seek to end
        file_size = file_obj.tell()
        file_obj.seek(0)  # Seek back to beginning

        if file_size > 2 * 1024 * 1024 * 1024:  # 2GB limit
            raise ValidationError("File size exceeds 2GB limit")

        # Upload file
        result = await self.client.upload_file(
            file_path=file_path,
            file_obj=file_obj,
            content_type=content_type,
            cache_control="31536000"  # 1 year cache for videos
        )

        return result

    async def get_video_download_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Get a signed download URL for a video file.

        Args:
            file_path: Path of the video file
            expires_in: URL expiration time in seconds

        Returns:
            str: Signed download URL
        """
        return await self.client.generate_signed_url(file_path, expires_in)

    async def delete_video_file(self, file_path: str) -> bool:
        """
        Delete a video file.

        Args:
            file_path: Path of the video file

        Returns:
            bool: True if deletion successful
        """
        return await self.client.delete_file(file_path)

    async def get_storage_usage(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get storage usage statistics.

        Args:
            user_id: Optional user ID to filter by

        Returns:
            Dict[str, Any]: Storage usage statistics
        """
        path_prefix = f"videos/{user_id}/" if user_id else "videos/"

        try:
            files = await self.client.list_files(path=path_prefix, limit=1000)

            total_size = sum(file.get("metadata", {}).get("size", 0) for file in files)
            file_count = len(files)

            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "user_id": user_id
            }
        except ServiceUnavailableError:
            return {
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "file_count": 0,
                "user_id": user_id,
                "error": "Unable to retrieve storage usage"
            }


# Global storage service instance
_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get the global storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service


# Backwards-compatible export
Storage = StorageService