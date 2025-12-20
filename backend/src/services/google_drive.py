"""Утилиты для работы с публичными папками Google Drive.

Цель: поддержать импорт треков из публичной папки Drive без OAuth.

Подход:
- Получаем folder_id из URL.
- Листим файлы через Google Drive API v3 с API key.
- Для воспроизведения используем прокси-эндпоинт backend (без утечки API key).

Важно:
- API key хранится только на сервере (env GOOGLE_DRIVE_API_KEY).
- В плейлист сохраняем относительные ссылки вида /api/media/gdrive/files/{file_id}/{filename}.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import httpx


_FOLDER_ID_PATTERNS = (
    # https://drive.google.com/drive/folders/<id>
    re.compile(r"drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)"),
    # https://drive.google.com/open?id=<id>
    re.compile(r"drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)"),
)


def extract_drive_folder_id(folder_url: str) -> str:
    """Извлечь folder_id из URL Google Drive."""
    url = (folder_url or "").strip()
    if not url:
        raise ValueError("Пустой URL папки Google Drive")

    for pattern in _FOLDER_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    raise ValueError("Не удалось извлечь ID папки из Google Drive URL")


async def list_drive_folder_files(
    *,
    folder_id: str,
    api_key: str,
    client: Optional[httpx.AsyncClient] = None,
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    """Получить список файлов в публичной папке Google Drive.

    Требуется включенный Google Drive API и API key.
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
                # На всякий случай: shared drives
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


def filter_media_files(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Оставить только аудио/видео файлы, исключая папки."""
    out: List[Dict[str, Any]] = []
    for f in files or []:
        mime = (f.get("mimeType") or "").lower()
        if mime == "application/vnd.google-apps.folder":
            continue
        if mime.startswith("audio/") or mime.startswith("video/"):
            out.append(f)
    return out
