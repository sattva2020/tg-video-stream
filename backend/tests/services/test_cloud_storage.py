"""
Integration tests for CloudStorageService.

Tests cover:
- Google Drive integration (folder ID extraction, file listing)
- Dropbox integration (URL extraction, direct URL generation)
- OneDrive integration (URL extraction, direct URL generation)
- Media file filtering
- URL normalization
- Error handling
"""
import pytest
from unittest.mock import MagicMock, Mock, patch, AsyncMock
import httpx

from src.services.cloud_storage_service import (
    CloudProvider,
    CloudStorageService,
    extract_gdrive_folder_id,
    extract_dropbox_id,
    extract_onedrive_id,
    list_gdrive_files,
    list_dropbox_files,
    list_onedrive_files,
    filter_media_files,
    normalize_cloud_url,
    get_dropbox_direct_url,
    get_onedrive_direct_url,
)


# ======================== FIXTURES ========================

@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def cloud_storage_service():
    """CloudStorageService instance with test API keys."""
    return CloudStorageService(
        gdrive_api_key="test_gdrive_api_key",
        dropbox_token="test_dropbox_token",
        onedrive_token="test_onedrive_token",
    )


# ======================== TEST CLASSES ========================

class TestGoogleDriveExtraction:
    """Test Google Drive folder ID extraction."""

    def test_extract_gdrive_folder_id_from_folder_url(self):
        """Test extraction from standard folder URL."""
        url = "https://drive.google.com/drive/folders/1ABC123xyz789"
        folder_id = extract_gdrive_folder_id(url)
        assert folder_id == "1ABC123xyz789"

    def test_extract_gdrive_folder_id_from_u_folder_url(self):
        """Test extraction from /u/0/ folder URL."""
        url = "https://drive.google.com/drive/u/1/folders/1ABC123xyz789"
        folder_id = extract_gdrive_folder_id(url)
        assert folder_id == "1ABC123xyz789"

    def test_extract_gdrive_folder_id_from_open_url(self):
        """Test extraction from open URL."""
        url = "https://drive.google.com/open?id=1ABC123xyz789"
        folder_id = extract_gdrive_folder_id(url)
        assert folder_id == "1ABC123xyz789"

    def test_extract_gdrive_folder_id_empty_url(self):
        """Test error on empty URL."""
        with pytest.raises(ValueError, match="Пустой URL"):
            extract_gdrive_folder_id("")

    def test_extract_gdrive_folder_id_invalid_url(self):
        """Test error on invalid URL."""
        with pytest.raises(ValueError, match="Не удалось извлечь"):
            extract_gdrive_folder_id("https://example.com/invalid")


class TestDropboxExtraction:
    """Test Dropbox ID extraction."""

    def test_extract_dropbox_id_from_folder_url(self):
        """Test extraction from folder URL."""
        url = "https://www.dropbox.com/sh/abc123/xyz789"
        share_id = extract_dropbox_id(url)
        assert share_id == "abc123"

    def test_extract_dropbox_id_from_file_url(self):
        """Test extraction from file URL."""
        url = "https://www.dropbox.com/s/abc123/filename.mp4"
        share_id = extract_dropbox_id(url)
        assert share_id == "abc123"

    def test_extract_dropbox_id_from_short_url(self):
        """Test extraction from short URL."""
        url = "https://db.tt/abc123"
        share_id = extract_dropbox_id(url)
        assert share_id == "abc123"

    def test_extract_dropbox_id_empty_url(self):
        """Test error on empty URL."""
        with pytest.raises(ValueError, match="Пустой URL"):
            extract_dropbox_id("")

    def test_extract_dropbox_id_invalid_url(self):
        """Test error on invalid URL."""
        with pytest.raises(ValueError, match="Не удалось извлечь"):
            extract_dropbox_id("https://example.com/invalid")


class TestOneDriveExtraction:
    """Test OneDrive ID extraction."""

    def test_extract_onedrive_id_from_short_url(self):
        """Test extraction from 1drv.ms URL."""
        url = "https://1drv.ms/u/s!abc123xyz789"
        resource_id = extract_onedrive_id(url)
        assert resource_id == "abc123xyz789"

    def test_extract_onedrive_id_from_f_short_url(self):
        """Test extraction from 1drv.ms/f URL."""
        url = "https://1drv.ms/f/s!abc123xyz789"
        resource_id = extract_onedrive_id(url)
        assert resource_id == "abc123xyz789"

    def test_extract_onedrive_id_from_live_url(self):
        """Test extraction from onedrive.live.com URL."""
        url = "https://onedrive.live.com/?authkey=abc123xyz789"
        resource_id = extract_onedrive_id(url)
        assert resource_id == "abc123xyz789"

    def test_extract_onedrive_id_empty_url(self):
        """Test error on empty URL."""
        with pytest.raises(ValueError, match="Пустой URL"):
            extract_onedrive_id("")

    def test_extract_onedrive_id_invalid_url(self):
        """Test error on invalid URL."""
        with pytest.raises(ValueError, match="Не удалось извлечь"):
            extract_onedrive_id("https://example.com/invalid")


class TestListGDriveFiles:
    """Test Google Drive file listing."""

    @pytest.mark.asyncio
    async def test_list_gdrive_files_success(self, mock_httpx_client):
        """Test successful file listing."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "files": [
                {"id": "1", "name": "video1.mp4", "mimeType": "video/mp4", "size": "1024000"},
                {"id": "2", "name": "video2.webm", "mimeType": "video/webm", "size": "2048000"},
            ],
            "nextPageToken": None
        }
        mock_httpx_client.get.return_value = mock_response

        files = await list_gdrive_files(
            folder_id="test_folder_id",
            api_key="test_api_key",
            client=mock_httpx_client
        )

        assert len(files) == 2
        assert files[0]["name"] == "video1.mp4"
        assert files[1]["name"] == "video2.webm"

    @pytest.mark.asyncio
    async def test_list_gdrive_files_empty_folder(self, mock_httpx_client):
        """Test listing empty folder."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"files": [], "nextPageToken": None}
        mock_httpx_client.get.return_value = mock_response

        files = await list_gdrive_files(
            folder_id="test_folder_id",
            api_key="test_api_key",
            client=mock_httpx_client
        )

        assert len(files) == 0

    @pytest.mark.asyncio
    async def test_list_gdrive_files_pagination(self, mock_httpx_client):
        """Test pagination handling."""
        # First page
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "files": [{"id": "1", "name": "video1.mp4", "mimeType": "video/mp4"}],
            "nextPageToken": "page2_token"
        }

        # Second page
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "files": [{"id": "2", "name": "video2.mp4", "mimeType": "video/mp4"}],
            "nextPageToken": None
        }

        mock_httpx_client.get.side_effect = [mock_response1, mock_response2]

        files = await list_gdrive_files(
            folder_id="test_folder_id",
            api_key="test_api_key",
            client=mock_httpx_client
        )

        assert len(files) == 2
        assert mock_httpx_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_list_gdrive_files_api_error(self, mock_httpx_client):
        """Test API error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_httpx_client.get.return_value = mock_response

        with pytest.raises(RuntimeError, match="Google Drive API error 403"):
            await list_gdrive_files(
                folder_id="test_folder_id",
                api_key="test_api_key",
                client=mock_httpx_client
            )

    @pytest.mark.asyncio
    async def test_list_gdrive_files_missing_folder_id(self):
        """Test error on missing folder_id."""
        with pytest.raises(ValueError, match="folder_id обязателен"):
            await list_gdrive_files(folder_id="", api_key="test_key")

    @pytest.mark.asyncio
    async def test_list_gdrive_files_missing_api_key(self):
        """Test error on missing api_key."""
        with pytest.raises(ValueError, match="api_key обязателен"):
            await list_gdrive_files(folder_id="test_id", api_key="")


class TestListDropboxFiles:
    """Test Dropbox file listing."""

    @pytest.mark.asyncio
    async def test_list_dropbox_files_success(self, mock_httpx_client):
        """Test successful file listing (stub implementation)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get.return_value = mock_response

        files = await list_dropbox_files(
            shared_url="https://www.dropbox.com/sh/abc123/xyz789",
            shared_link="https://www.dropbox.com/sh/abc123/xyz789",
            client=mock_httpx_client
        )

        # Current implementation returns empty list (stub)
        assert isinstance(files, list)

    @pytest.mark.asyncio
    async def test_list_dropbox_files_missing_url(self):
        """Test error on missing shared_url."""
        with pytest.raises(ValueError, match="shared_url обязателен"):
            await list_dropbox_files(shared_url="", shared_link="test")


class TestListOneDriveFiles:
    """Test OneDrive file listing."""

    @pytest.mark.asyncio
    async def test_list_onedrive_files_success(self, mock_httpx_client):
        """Test successful file listing (stub implementation)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get.return_value = mock_response

        files = await list_onedrive_files(
            shared_url="https://1drv.ms/u/s!abc123",
            client=mock_httpx_client
        )

        # Current implementation returns empty list (stub)
        assert isinstance(files, list)

    @pytest.mark.asyncio
    async def test_list_onedrive_files_missing_url(self):
        """Test error on missing shared_url."""
        with pytest.raises(ValueError, match="shared_url обязателен"):
            await list_onedrive_files(shared_url="")


class TestFilterMediaFiles:
    """Test media file filtering."""

    def test_filter_video_files_by_mime_type(self):
        """Test filtering video files by MIME type."""
        files = [
            {"name": "video.mp4", "mimeType": "video/mp4"},
            {"name": "audio.mp3", "mimeType": "audio/mpeg"},
            {"name": "document.pdf", "mimeType": "application/pdf"},
        ]

        filtered = filter_media_files(files)
        assert len(filtered) == 1
        assert filtered[0]["name"] == "video.mp4"

    def test_filter_audio_files_by_mime_type(self):
        """Test filtering audio files by MIME type."""
        files = [
            {"name": "video.mp4", "mimeType": "video/mp4"},
            {"name": "audio.mp3", "mimeType": "audio/mpeg"},
            {"name": "audio.wav", "mimeType": "audio/wav"},
        ]

        filtered = filter_media_files(files)
        assert len(filtered) == 3  # All media files

    def test_filter_files_by_extension(self):
        """Test filtering by file extension."""
        files = [
            {"name": "video.mp4", "mimeType": "application/octet-stream"},
            {"name": "video.webm", "mimeType": "application/octet-stream"},
            {"name": "document.txt", "mimeType": "text/plain"},
        ]

        filtered = filter_media_files(files)
        assert len(filtered) == 2
        assert all(f["name"].endswith((".mp4", ".webm")) for f in filtered)

    def test_filter_excludes_gdrive_folders(self):
        """Test that Google Drive folders are excluded."""
        files = [
            {"name": "video.mp4", "mimeType": "video/mp4"},
            {"name": "My Folder", "mimeType": "application/vnd.google-apps.folder"},
            {"name": "audio.mp3", "mimeType": "audio/mpeg"},
        ]

        filtered = filter_media_files(files)
        assert len(filtered) == 2
        assert not any(f.get("mimeType") == "application/vnd.google-apps.folder" for f in filtered)

    def test_filter_empty_list(self):
        """Test filtering empty list."""
        assert filter_media_files([]) == []

    def test_filter_none_input(self):
        """Test filtering None input."""
        assert filter_media_files(None) == []


class TestNormalizeCloudUrl:
    """Test URL normalization."""

    def test_normalize_adds_https(self):
        """Test adding https:// prefix."""
        assert normalize_cloud_url("example.com", CloudProvider.GOOGLE_DRIVE) == "https://example.com"
        assert normalize_cloud_url("http://example.com", CloudProvider.GOOGLE_DRIVE) == "https://example.com"

    def test_normalize_protocol_relative_url(self):
        """Test normalizing protocol-relative URL."""
        url = "//drive.google.com/folders/123"
        normalized = normalize_cloud_url(url, CloudProvider.GOOGLE_DRIVE)
        assert normalized == "https://drive.google.com/folders/123"

    def test_normalize_dropbox_urls(self):
        """Test Dropbox URL normalization."""
        assert normalize_cloud_url("http://dropbox.com/s/123", CloudProvider.DROPBOX) == "https://www.dropbox.com/s/123"
        assert normalize_cloud_url("http://www.dropbox.com/s/123", CloudProvider.DROPBOX) == "https://www.dropbox.com/s/123"

    def test_normalize_gdrive_urls(self):
        """Test Google Drive URL normalization."""
        assert normalize_cloud_url("http://drive.google.com/123", CloudProvider.GOOGLE_DRIVE) == "https://drive.google.com/123"
        assert normalize_cloud_url("http://docs.google.com/123", CloudProvider.GOOGLE_DRIVE) == "https://docs.google.com/123"

    def test_normalize_onedrive_urls(self):
        """Test OneDrive URL normalization."""
        assert normalize_cloud_url("http://1drv.ms/u/s!123", CloudProvider.ONEDRIVE) == "https://1drv.ms/u/s!123"
        assert normalize_cloud_url("http://onedrive.live.com/123", CloudProvider.ONEDRIVE) == "https://onedrive.live.com/123"

    def test_normalize_empty_url(self):
        """Test normalizing empty URL."""
        assert normalize_cloud_url("", CloudProvider.GOOGLE_DRIVE) == ""
        assert normalize_cloud_url("   ", CloudProvider.GOOGLE_DRIVE) == ""


class TestGetDirectUrl:
    """Test direct URL generation."""

    def test_get_dropbox_direct_url_with_dl_0(self):
        """Test converting ?dl=0 to ?dl=1."""
        url = "https://www.dropbox.com/s/abc123/video.mp4?dl=0"
        direct = get_dropbox_direct_url(url)
        assert direct == "https://www.dropbox.com/s/abc123/video.mp4?dl=1"

    def test_get_dropbox_direct_url_without_params(self):
        """Test adding ?dl=1 to URL without params."""
        url = "https://www.dropbox.com/s/abc123/video.mp4"
        direct = get_dropbox_direct_url(url)
        assert direct == "https://www.dropbox.com/s/abc123/video.mp4?dl=1"

    def test_get_dropbox_direct_url_with_other_params(self):
        """Test adding &dl=1 to URL with other params."""
        url = "https://www.dropbox.com/s/abc123/video.mp4?foo=bar"
        direct = get_dropbox_direct_url(url)
        assert direct == "https://www.dropbox.com/s/abc123/video.mp4?foo=bar&dl=1"

    def test_get_onedrive_direct_url_without_params(self):
        """Test adding ?download=1 to URL without params."""
        url = "https://1drv.ms/u/s!abc123"
        direct = get_onedrive_direct_url(url)
        assert direct == "https://1drv.ms/u/s!abc123?download=1"

    def test_get_onedrive_direct_url_with_existing_params(self):
        """Test adding &download=1 to URL with existing params."""
        url = "https://1drv.ms/u/s!abc123?foo=bar"
        direct = get_onedrive_direct_url(url)
        assert direct == "https://1drv.ms/u/s!abc123?foo=bar&download=1"


class TestCloudStorageService:
    """Test CloudStorageService class."""

    def test_init(self):
        """Test service initialization."""
        service = CloudStorageService(
            gdrive_api_key="test_key",
            dropbox_token="dropbox_token",
            onedrive_token="onedrive_token"
        )
        assert service.gdrive_api_key == "test_key"
        assert service.dropbox_token == "dropbox_token"
        assert service.onedrive_token == "onedrive_token"
        assert service._client is None

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self, cloud_storage_service):
        """Test that get_client creates HTTP client."""
        client = await cloud_storage_service.get_client()
        assert isinstance(client, httpx.AsyncClient)
        assert cloud_storage_service._client is not None

    @pytest.mark.asyncio
    async def test_get_client_reuses_client(self, cloud_storage_service):
        """Test that get_client reuses existing client."""
        client1 = await cloud_storage_service.get_client()
        client2 = await cloud_storage_service.get_client()
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_close(self, cloud_storage_service):
        """Test closing HTTP client."""
        await cloud_storage_service.get_client()
        await cloud_storage_service.close()
        assert cloud_storage_service._client is None

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using service as async context manager."""
        async with CloudStorageService(gdrive_api_key="test") as service:
            assert isinstance(service, CloudStorageService)
            await service.get_client()
        # Client should be closed after exiting context
        assert service._client is None

    @pytest.mark.asyncio
    async def test_list_files_gdrive(self, cloud_storage_service, mock_httpx_client):
        """Test listing files from Google Drive."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "files": [
                {"id": "1", "name": "video.mp4", "mimeType": "video/mp4"},
                {"id": "2", "name": "audio.mp3", "mimeType": "audio/mpeg"},
            ],
            "nextPageToken": None
        }

        with patch.object(cloud_storage_service, 'get_client', return_value=mock_httpx_client):
            files = await cloud_storage_service.list_files(
                provider=CloudProvider.GOOGLE_DRIVE,
                url="https://drive.google.com/drive/folders/test123"
            )

        assert len(files) == 2

    @pytest.mark.asyncio
    async def test_list_files_gdrive_missing_api_key(self, cloud_storage_service):
        """Test error when GDrive API key is missing."""
        service = CloudStorageService()  # No API key

        with pytest.raises(ValueError, match="Требуется gdrive_api_key"):
            await service.list_files(
                provider=CloudProvider.GOOGLE_DRIVE,
                url="https://drive.google.com/drive/folders/test123"
            )

    @pytest.mark.asyncio
    async def test_list_files_dropbox(self, cloud_storage_service, mock_httpx_client):
        """Test listing files from Dropbox."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get.return_value = mock_response

        with patch.object(cloud_storage_service, 'get_client', return_value=mock_httpx_client):
            files = await cloud_storage_service.list_files(
                provider=CloudProvider.DROPBOX,
                url="https://www.dropbox.com/sh/abc123/xyz789"
            )

        assert isinstance(files, list)

    @pytest.mark.asyncio
    async def test_list_files_onedrive(self, cloud_storage_service, mock_httpx_client):
        """Test listing files from OneDrive."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_httpx_client.get.return_value = mock_response

        with patch.object(cloud_storage_service, 'get_client', return_value=mock_httpx_client):
            files = await cloud_storage_service.list_files(
                provider=CloudProvider.ONEDRIVE,
                url="https://1drv.ms/u/s!abc123"
            )

        assert isinstance(files, list)

    @pytest.mark.asyncio
    async def test_list_files_unsupported_provider(self, cloud_storage_service):
        """Test error with unsupported provider."""
        with pytest.raises(ValueError, match="Неподдерживаемый провайдер"):
            await cloud_storage_service.list_files(
                provider="unsupported",
                url="https://example.com"
            )

    def test_get_direct_url_gdrive(self, cloud_storage_service):
        """Test getting direct URL for Google Drive."""
        url = "https://drive.google.com/file/d/abc123/view"
        direct = cloud_storage_service.get_direct_url(CloudProvider.GOOGLE_DRIVE, url)
        assert direct == url  # GDrive returns URL as-is

    def test_get_direct_url_dropbox(self, cloud_storage_service):
        """Test getting direct URL for Dropbox."""
        url = "https://www.dropbox.com/s/abc123/video.mp4"
        direct = cloud_storage_service.get_direct_url(CloudProvider.DROPBOX, url)
        assert "?dl=1" in direct

    def test_get_direct_url_onedrive(self, cloud_storage_service):
        """Test getting direct URL for OneDrive."""
        url = "https://1drv.ms/u/s!abc123"
        direct = cloud_storage_service.get_direct_url(CloudProvider.ONEDRIVE, url)
        assert "?download=1" in direct or "&download=1" in direct
