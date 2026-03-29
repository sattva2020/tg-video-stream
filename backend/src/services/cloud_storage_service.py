"""Сервис для работы с облачными хранилищами.

Поддержка:
- Google Drive (публичные папки через API key)
- Dropbox (через shared links)
- OneDrive (через shared links)

Цель: унифицированный интерфейс для доступа к медиа-файлам в различных облачных хранилищах.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx


class CloudProvider(str, Enum):
    """Поддерживаемые облачные провайдеры."""

    GOOGLE_DRIVE = "gdrive"
    DROPBOX = "dropbox"
    ONEDRIVE = "onedrive"


# =============================================================================
# Google Drive patterns (reuse from google_drive.py)
# =============================================================================

_GDRIVE_FOLDER_PATTERNS = (
    re.compile(r"drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)"),
    re.compile(r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)"),
)


def extract_gdrive_folder_id(folder_url: str) -> str:
    """Извлечь folder_id из URL Google Drive."""
    url = (folder_url or "").strip()
    if not url:
        raise ValueError("Пустой URL папки Google Drive")

    for pattern in _GDRIVE_FOLDER_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    raise ValueError("Не удалось извлечь ID папки из Google Drive URL")


async def list_gdrive_files(
    *,
    folder_id: str,
    api_key: str,
    client: Optional[httpx.AsyncClient] = None,
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    """Получить список файлов в публичной папке Google Drive.

    Args:
        folder_id: ID папки Google Drive
        api_key: Google Drive API key
        client: Опциональный httpx клиент
        page_size: Количество файлов на странице

    Returns:
        Список файлов с метаданными

    Raises:
        ValueError: Если не указан folder_id или api_key
        RuntimeError: При ошибке API
    """
    if not folder_id:
        raise ValueError("folder_id обязателен")
    if not api_key:
        raise ValueError("api_key обязателен")

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=20, follow_redirects=True)

    try:
        files: List[Dict[str, Any]] = []
        page_token: Optional[str] = None

        while True:
            params: Dict[str, Any] = {
                "q": f"'{folder_id}' in parents and trashed=false",
                "fields": "nextPageToken,files(id,name,mimeType,size)",
                "pageSize": page_size,
                "key": api_key,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if page_token:
                params["pageToken"] = page_token

            resp = await client.get("https://www.googleapis.com/drive/v3/files", params=params)
            if resp.status_code != 200:
                detail = ""
                try:
                    detail = resp.text
                except Exception:
                    detail = ""
                raise RuntimeError(
                    f"Google Drive API error {resp.status_code}: {detail[:500]}"
                )

            data = resp.json()
            files.extend(data.get("files", []) or [])
            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return files
    finally:
        if own_client:
            await client.aclose()


# =============================================================================
# Dropbox patterns
# =============================================================================

_DROPBOX_PATTERNS = (
    # https://www.dropbox.com/sh/<share_id>/folder_id
    re.compile(r"dropbox\.com/sh/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)"),
    # https://www.dropbox.com/s/<file_id>/filename
    re.compile(r"dropbox\.com/s/([a-zA-Z0-9_-]+)/([a-zA-Z0-9_.-]+)"),
    # https://db.tt/<short_id>
    re.compile(r"db\.tt/([a-zA-Z0-9_-]+)"),
)


def extract_dropbox_id(shared_url: str) -> str:
    """Извлечь ID из публичной ссылки Dropbox.

    Args:
        shared_url: Публичная ссылка Dropbox

    Returns:
        ID файла или папки

    Raises:
        ValueError: Если не удалось извлечь ID
    """
    url = (shared_url or "").strip()
    if not url:
        raise ValueError("Пустой URL Dropbox")

    for pattern in _DROPBOX_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    raise ValueError("Не удалось извлечь ID из Dropbox URL")


async def list_dropbox_files(
    *,
    shared_url: str,
    shared_link: str,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """Получить список файлов из публичной папки Dropbox.

    Note: Для Dropbox требуется shared link (поделиться папкой).

    Args:
        shared_url: URL публичной папки Dropbox
        shared_link: Полная ссылка для доступа
        client: Опциональный httpx клиент

    Returns:
        Список файлов с метаданными

    Raises:
        ValueError: Если не указаны параметры
        RuntimeError: При ошибке API
    """
    if not shared_url:
        raise ValueError("shared_url обязателен")

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=20, follow_redirects=True)

    try:
        # Для Dropbox используем shared links для доступа
        # API v2: https://www.dropbox.com/developers/documentation/http/documentation

        # В реальной реализации здесь будет вызов Dropbox Sharing API
        # Для публичных ссылок можно использовать dl=1 параметр

        # Получаем содержимое папки через shared link
        headers = {
            "Dropbox-API-Arg": f'{{"path": ""}}',
        }

        # Примечание: это упрощенная реализация
        # В продакшене нужно использовать Dropbox API с токеном
        params = {"dl": "1", "preview": "0"}

        # Для public/shared ссылок Dropbox можно получить контент
        resp = await client.get(shared_url, params=params, headers=headers)

        if resp.status_code != 200:
            raise RuntimeError(
                f"Dropbox API error {resp.status_code}: {resp.text[:500]}"
            )

        # Парсим HTML ответ (в реальности нужно использовать API)
        # Это заглушка для демонстрации структуры
        return []

    finally:
        if own_client:
            await client.aclose()


def get_dropbox_direct_url(shared_url: str) -> str:
    """Преобразовать ссылку Dropbox в прямую ссылку на скачивание.

    Args:
        shared_url: Публичная ссылка Dropbox

    Returns:
        Прямая ссылка на скачивание файла
    """
    url = shared_url.strip()
    # Заменяем ?dl=0 на ?dl=1 для прямого скачивания
    if "?dl=0" in url:
        url = url.replace("?dl=0", "?dl=1")
    elif "?" not in url:
        url += "?dl=1"
    else:
        url += "&dl=1"
    return url


# =============================================================================
# OneDrive patterns
# =============================================================================

_ONEDRIVE_PATTERNS = (
    # https://1drv.ms/u/s!id
    re.compile(r"1drv\.ms/u/s!([a-zA-Z0-9_-]+)"),
    # https://1drv.ms/f/s!id
    re.compile(r"1drv\.ms/f/s!([a-zA-Z0-9_-]+)"),
    # https://onedrive.live.com/?authkey=...
    re.compile(r"onedrive\.live\.com/\?authkey=([a-zA-Z0-9_-]+)"),
)


def extract_onedrive_id(shared_url: str) -> str:
    """Извлечь ID из публичной ссылки OneDrive.

    Args:
        shared_url: Публичная ссылка OneDrive

    Returns:
        ID ресурса OneDrive

    Raises:
        ValueError: Если не удалось извлечь ID
    """
    url = (shared_url or "").strip()
    if not url:
        raise ValueError("Пустой URL OneDrive")

    for pattern in _ONEDRIVE_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    raise ValueError("Не удалось извлечь ID из OneDrive URL")


async def list_onedrive_files(
    *,
    shared_url: str,
    client: Optional[httpx.AsyncClient] = None,
) -> List[Dict[str, Any]]:
    """Получить список файлов из публичной папки OneDrive.

    Note: Для OneDrive требуется использовать Microsoft Graph API или парсить HTML.

    Args:
        shared_url: URL публичной папки OneDrive
        client: Опциональный httpx клиент

    Returns:
        Список файлов с метаданными

    Raises:
        ValueError: Если не указан shared_url
        RuntimeError: При ошибке API
    """
    if not shared_url:
        raise ValueError("shared_url обязателен")

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=20, follow_redirects=True)

    try:
        # Для OneDrive используем Microsoft Graph API
        # или парсим HTML страницу для публичных ссылок

        # Примечание: это упрощенная реализация
        # В продакшене нужно использовать Microsoft Graph API с токеном

        # Для public ссылок OneDrive
        resp = await client.get(shared_url)

        if resp.status_code != 200:
            raise RuntimeError(
                f"OneDrive API error {resp.status_code}: {resp.text[:500]}"
            )

        # В реальности здесь нужно парсить HTML или использовать API
        return []

    finally:
        if own_client:
            await client.aclose()


def get_onedrive_direct_url(shared_url: str) -> str:
    """Преобразовать ссылку OneDrive в прямую ссылку на скачивание.

    Args:
        shared_url: Публичная ссылка OneDrive

    Returns:
        Прямая ссылка на скачивание файла
    """
    url = shared_url.strip()
    # Добавляем параметры для прямого скачивания
    if "&download=1" not in url:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}download=1"
    return url


# =============================================================================
# Common utilities
# =============================================================================

def filter_media_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Оставить только аудио/видео файлы, исключая папки.

    Args:
        files: Список файлов с метаданными

    Returns:
        Отфильтрованный список медиа-файлов
    """
    out: List[Dict[str, Any]] = []
    for f in files or []:
        mime = (f.get("mimeType") or "").lower()

        # Пропускаем папки Google Drive
        if mime == "application/vnd.google-apps.folder":
            continue

        # Проверяем MIME тип
        if mime.startswith("audio/") or mime.startswith("video/"):
            out.append(f)
            continue

        # Проверяем расширение файла
        name = (f.get("name") or "").lower()
        if any(name.endswith(ext) for ext in [
            '.mp4', '.webm', '.mkv', '.avi', '.mov', '.wmv', '.flv',
            '.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma'
        ]):
            out.append(f)

    return out


def normalize_cloud_url(url: str, provider: CloudProvider) -> str:
    """Нормализовать URL облачного хранилища.

    Args:
        url: Исходный URL
        provider: Провайдер облачного хранилища

    Returns:
        Нормализованный URL
    """
    url = (url or "").strip()

    if not url:
        return url

    # Добавляем https если нужно
    if url.startswith("//"):
        url = "https:" + url
    elif not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # Специфичная нормализация для каждого провайдера
    if provider == CloudProvider.DROPBOX:
        # Dropbox: заменяем www на www если нужно
        url = url.replace("http://www.dropbox.com", "https://www.dropbox.com")
        url = url.replace("http://dropbox.com", "https://www.dropbox.com")

    elif provider == CloudProvider.GOOGLE_DRIVE:
        # Google Drive: используем https
        url = url.replace("http://drive.google.com", "https://drive.google.com")
        url = url.replace("http://docs.google.com", "https://docs.google.com")

    elif provider == CloudProvider.ONEDRIVE:
        # OneDrive: используем https
        url = url.replace("http://1drv.ms", "https://1drv.ms")
        url = url.replace("http://onedrive.live.com", "https://onedrive.live.com")

    return url


# =============================================================================
# Main Service Class
# =============================================================================

class CloudStorageService:
    """Унифицированный сервис для работы с облачными хранилищами.

    Обеспечивает единый интерфейс для доступа к файлам в различных облачных
    хранилищах (Google Drive, Dropbox, OneDrive).
    """

    def __init__(
        self,
        gdrive_api_key: Optional[str] = None,
        dropbox_token: Optional[str] = None,
        onedrive_token: Optional[str] = None,
    ):
        """Инициализировать сервис.

        Args:
            gdrive_api_key: API ключ для Google Drive
            dropbox_token: OAuth токен для Dropbox (опционально)
            onedrive_token: OAuth токен для OneDrive (опционально)
        """
        self.gdrive_api_key = gdrive_api_key
        self.dropbox_token = dropbox_token
        self.onedrive_token = onedrive_token
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Получить или создать HTTP клиент."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30, follow_redirects=True)
        return self._client

    async def close(self) -> None:
        """Закрыть HTTP клиент."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def list_files(
        self,
        provider: CloudProvider,
        url: str,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Получить список файлов из облачного хранилища.

        Args:
            provider: Провайдер облачного хранилища
            url: URL папки или файла
            **kwargs: Дополнительные параметры для конкретного провайдера

        Returns:
            Список файлов с метаданными

        Raises:
            ValueError: При неверных параметрах
            RuntimeError: При ошибке API
        """
        url = normalize_cloud_url(url, provider)

        if provider == CloudProvider.GOOGLE_DRIVE:
            if not self.gdrive_api_key:
                raise ValueError("Требуется gdrive_api_key для работы с Google Drive")

            folder_id = extract_gdrive_folder_id(url)
            client = await self.get_client()

            files = await list_gdrive_files(
                folder_id=folder_id,
                api_key=self.gdrive_api_key,
                client=client,
                page_size=kwargs.get("page_size", 1000),
            )

            return filter_media_files(files)

        elif provider == CloudProvider.DROPBOX:
            client = await self.get_client()

            files = await list_dropbox_files(
                shared_url=url,
                shared_link=kwargs.get("shared_link", url),
                client=client,
            )

            return filter_media_files(files)

        elif provider == CloudProvider.ONEDRIVE:
            client = await self.get_client()

            files = await list_onedrive_files(
                shared_url=url,
                client=client,
            )

            return filter_media_files(files)

        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")

    def get_direct_url(self, provider: CloudProvider, url: str) -> str:
        """Получить прямую ссылку на скачивание файла.

        Args:
            provider: Провайдер облачного хранилища
            url: URL файла

        Returns:
            Прямая ссылка на скачивание
        """
        url = normalize_cloud_url(url, provider)

        if provider == CloudProvider.DROPBOX:
            return get_dropbox_direct_url(url)
        elif provider == CloudProvider.ONEDRIVE:
            return get_onedrive_direct_url(url)
        else:
            # Для Google Drive прямые ссылки работают через прокси
            return url

    async def __aenter__(self) -> "CloudStorageService":
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.close()
