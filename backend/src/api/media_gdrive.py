"""Прокси-эндпоинты для стриминга файлов из публичного Google Drive.

Задача:
- Не светить GOOGLE_DRIVE_API_KEY наружу.
- Дать стримеру URL с расширением файла в path (важно для определения аудио по расширению).
- Поддержать HTTP Range (ffmpeg/yt-dlp часто требует частичные чтения).

Важно:
- Эндпоинт не требует авторизации, как и /api/schedule/... (внутренний API для стримера).
"""

from __future__ import annotations

import os
from typing import Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse


router = APIRouter(prefix="/media/gdrive", tags=["media"])


_GOOGLE_DRIVE_MEDIA_URL = "https://www.googleapis.com/drive/v3/files/{file_id}"


def _pick_passthrough_headers(upstream_headers: httpx.Headers) -> Dict[str, str]:
    allowlist = {
        "content-type",
        "content-length",
        "content-range",
        "accept-ranges",
        "cache-control",
        "etag",
        "last-modified",
    }
    out: Dict[str, str] = {}
    for k, v in upstream_headers.items():
        lk = k.lower()
        if lk in allowlist:
            out[k] = v
    return out


@router.get("/files/{file_id}/{filename}")
async def stream_public_gdrive_file(
    file_id: str,
    filename: str,
    request: Request,
):
    """Стриминг файла Google Drive через backend-прокси.

    `filename` используется только для расширения/читаемости URL.
    """
    api_key = os.getenv("GOOGLE_DRIVE_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_DRIVE_API_KEY is not configured")

    upstream_url = _GOOGLE_DRIVE_MEDIA_URL.format(file_id=file_id)
    params = {"alt": "media", "key": api_key}

    upstream_headers: Dict[str, str] = {}
    range_header = request.headers.get("range")
    if range_header:
        upstream_headers["Range"] = range_header

    if_range_header = request.headers.get("if-range")
    if if_range_header:
        upstream_headers["If-Range"] = if_range_header

    client = httpx.AsyncClient(timeout=60, follow_redirects=True)
    stream_cm = client.stream("GET", upstream_url, params=params, headers=upstream_headers)

    try:
        upstream = await stream_cm.__aenter__()
    except Exception:
        await client.aclose()
        raise HTTPException(status_code=502, detail="Failed to connect to Google Drive")

    async def _iter_bytes():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await stream_cm.__aexit__(None, None, None)
            await client.aclose()

    # Ошибки Google Drive не проксируем как поток — возвращаем HTTPException.
    if upstream.status_code >= 400:
        try:
            body = (await upstream.aread())[:500]
        except Exception:
            body = b""
        await stream_cm.__aexit__(None, None, None)
        await client.aclose()
        raise HTTPException(
            status_code=upstream.status_code,
            detail=f"Google Drive returned {upstream.status_code}" + (f": {body.decode(errors='ignore')}" if body else ""),
        )

    response_headers = _pick_passthrough_headers(upstream.headers)
    media_type: Optional[str] = upstream.headers.get("content-type")

    # filename сейчас не используем для Content-Disposition намеренно: не хотим давать
    # возможность инъекций/неожиданного поведения. При необходимости добавим позже.
    _ = filename

    return StreamingResponse(
        _iter_bytes(),
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=media_type,
    )
