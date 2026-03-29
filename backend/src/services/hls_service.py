"""Сервис для работы с HLS/DASH потоками.

Поддержка:
- HLS (HTTP Live Streaming) - .m3u8 плейлисты
- DASH (Dynamic Adaptive Streaming over HTTP) - .mpd манифесты
- VOD (Video on Demand) потоки
- Live потоки

Цель: извлечение метаданных и валидация стриминговых URL для воспроизведения.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx


logger = logging.getLogger(__name__)


class StreamType(str, Enum):
    """Тип потока."""

    HLS = "hls"
    DASH = "dash"
    UNKNOWN = "unknown"


class StreamVariant:
    """Вариант потока (качество/ресолюция)."""

    def __init__(
        self,
        bandwidth: Optional[int] = None,
        resolution: Optional[str] = None,
        codecs: Optional[str] = None,
        uri: Optional[str] = None,
        is_default: bool = False,
    ):
        """Инициализировать вариант потока.

        Args:
            bandwidth: Пропускная способность в bit/s
            resolution: Разрешение (например, "1920x1080")
            codecs: Кодеки (например, "avc1.64001f,mp4a.40.2")
            uri: URI варианта потока
            is_default: Является ли вариантом по умолчанию
        """
        self.bandwidth = bandwidth
        self.resolution = resolution
        self.codecs = codecs
        self.uri = uri
        self.is_default = is_default

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь."""
        return {
            "bandwidth": self.bandwidth,
            "resolution": self.resolution,
            "codecs": self.codecs,
            "uri": self.uri,
            "is_default": self.is_default,
        }


# =============================================================================
# Вспомогательные функции для детекции и парсинга
# =============================================================================

def detect_stream_type(url: str) -> StreamType:
    """Определить тип потока по URL.

    Args:
        url: URL потока

    Returns:
        StreamType enum значение
    """
    if not url:
        return StreamType.UNKNOWN

    url_lower = url.lower().strip()

    # Проверяем расширение файла
    if ".m3u8" in url_lower or url_lower.endswith("m3u8"):
        return StreamType.HLS

    if ".mpd" in url_lower or url_lower.endswith("mpd"):
        return StreamType.DASH

    # Проверяем по типу контента (если можно определить)
    # Для этого потребуется HTTP запрос, выполняется в validate_stream

    return StreamType.UNKNOWN


def _parse_resolution(resolution_str: Optional[str]) -> Optional[str]:
    """Очистить и нормализовать разрешение.

    Args:
        resolution_str: Строка с разрешением

    Returns:
        Нормализованная строка или None
    """
    if not resolution_str:
        return None

    # Очищаем от лишних пробелов
    resolution_str = resolution_str.strip()

    # Проверяем формат WxH или WxH@FPS
    match = re.match(r"(\d+)x(\d+)(?:@(\d+))?", resolution_str)
    if match:
        width, height, fps = match.groups()
        if fps:
            return f"{width}x{height}@{fps}"
        return f"{width}x{height}"

    return None


def _parse_bandwidth(bandwidth_str: Optional[str]) -> Optional[int]:
    """Парсить пропускную способность из строки.

    Args:
        bandwidth_str: Строка с bandwidth (число или "BANDWIDTH=...")

    Returns:
        Пропускная способность в bit/s или None
    """
    if not bandwidth_str:
        return None

    # Извлекаем число
    match = re.search(r"(\d+)", str(bandwidth_str))
    if match:
        try:
            return int(match.group(1))
        except (ValueError, TypeError):
            pass

    return None


# =============================================================================
# HLS (HTTP Live Streaming) функции
# =============================================================================

async def parse_hls_master_playlist(
    content: str,
    base_url: str,
) -> Dict[str, Any]:
    """Парсить HLS master playlist (.m3u8).

    Извлекает варианты стримов с разными качествами.

    Args:
        content: Содержимое m3u8 файла
        base_url: Базовый URL для resolving relative paths

    Returns:
        dict с метаданными:
            - variants: Список StreamVariant объектов
            - total_variants: Количество вариантов
            - is_live: True если live stream
            - error: Описание ошибки (если произошла)
    """
    try:
        lines = content.strip().split("\n")

        variants: List[StreamVariant] = []
        current_bandwidth = None
        current_resolution = None
        current_codecs = None
        is_default = False

        # Определяем тип потока (live или VOD)
        is_live = "#EXT-X-PLAYLIST-TYPE" not in content and "#EXT-X-ENDLIST" not in content

        for i, line in enumerate(lines):
            line = line.strip()

            # Пропускаем пустые строки и комментарии (кроме тегов)
            if not line or (line.startswith("#") and not line.startswith("#EXT")):
                continue

            # Извлекаем bandwidth
            if line.startswith("#EXT-X-STREAM-INF:"):
                # Парсим параметры
                bandwidth_match = re.search(r"BANDWIDTH=(\d+)", line)
                if bandwidth_match:
                    current_bandwidth = int(bandwidth_match.group(1))

                resolution_match = re.search(r"RESOLUTION=(\d+x\d+)", line)
                if resolution_match:
                    current_resolution = resolution_match.group(1)

                codecs_match = re.search(r'CODECS="([^"]+)"', line)
                if codecs_match:
                    current_codecs = codecs_match.group(1)

            # Следующая строка после #EXT-X-STREAM-INF - это URI
            if current_bandwidth and not line.startswith("#"):
                uri = line

                # Resolve relative URL
                if uri.startswith("/"):
                    # Absolute path
                    parts = base_url.split("/")
                    uri = f"{parts[0]}//{parts[2]}/{uri.lstrip('/')}"
                elif not uri.startswith("http"):
                    # Relative path
                    base_path = "/".join(base_url.split("/")[:-1])
                    uri = f"{base_path}/{uri}"

                variant = StreamVariant(
                    bandwidth=current_bandwidth,
                    resolution=current_resolution,
                    codecs=current_codecs,
                    uri=uri,
                    is_default=is_default,
                )
                variants.append(variant)

                # Сбрасываем для следующего варианта
                current_bandwidth = None
                current_resolution = None
                current_codecs = None
                is_default = False

        if not variants:
            # Возможно это media playlist (не master)
            # Проверяем наличие сегментов
            if "#EXTINF" in content:
                return {
                    "variants": [],
                    "total_variants": 0,
                    "is_live": is_live,
                    "is_master_playlist": False,
                    "error": None,
                }

            return {
                "variants": [],
                "total_variants": 0,
                "is_live": is_live,
                "is_master_playlist": False,
                "error": "No stream variants found in HLS playlist",
            }

        # Конвертируем в словари
        variants_data = [v.to_dict() for v in variants]

        return {
            "variants": variants_data,
            "total_variants": len(variants),
            "is_live": is_live,
            "is_master_playlist": True,
            "error": None,
        }

    except Exception as e:
        logger.exception("Ошибка при парсинге HLS master playlist")
        return {
            "variants": [],
            "total_variants": 0,
            "is_live": False,
            "is_master_playlist": False,
            "error": str(e),
        }


# =============================================================================
# DASH (MPEG-DASH) функции
# =============================================================================

async def parse_dash_manifest(
    content: str,
    base_url: str,
) -> Dict[str, Any]:
    """Парсить DASH manifest (.mpd).

    Извлекает представления (representations) с разными качествами.

    Args:
        content: Содержимое mpd файла (XML)
        base_url: Базовый URL для resolving relative paths

    Returns:
        dict с метаданными:
            - variants: Список StreamVariant объектов
            - total_variants: Количество вариантов
            - is_live: True если live stream
            - error: Описание ошибки (если произошла)
    """
    try:
        import xml.etree.ElementTree as ET
    except ImportError:
        return {
            "variants": [],
            "total_variants": 0,
            "is_live": False,
            "error": "xml.etree module not available",
        }

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        return {
            "variants": [],
            "total_variants": 0,
            "is_live": False,
            "error": f"Ошибка парсинга XML: {str(e)}",
        }

    try:
        # DASH namespace
        namespaces = {
            "dash": "urn:mpeg:dash:schema:mpd:2011",
        }

        # Определяем тип потока
        mpd_type = root.get("type", "static")
        is_live = mpd_type == "dynamic"

        variants: List[StreamVariant] = []

        # Извлекаем AdaptationSets
        for adaptation_set in root.findall(".//dash:AdaptationSet", namespaces):
            # Нас интересуют только video
            mime_type = adaptation_set.get("mimeType", "")
            if "video" not in mime_type.lower():
                continue

            # Извлекаем Representations
            for representation in adaptation_set.findall(".//dash:Representation", namespaces):
                bandwidth = representation.get("bandwidth")
                width = representation.get("width")
                height = representation.get("height")
                codecs = representation.get("codecs")

                # Формируем разрешение
                resolution = None
                if width and height:
                    resolution = f"{width}x{height}"

                # Извлекаем BaseURL или SegmentList
                base_url_elem = representation.find(".//dash:BaseURL", namespaces)
                if base_url_elem is not None and base_url_elem.text:
                    uri = base_url_elem.text.strip()
                else:
                    # Пробуем найти SegmentTemplate
                    seg_template = representation.find(".//dash:SegmentTemplate", namespaces)
                    if seg_template is not None:
                        media = seg_template.get("media")
                        initialization = seg_template.get("initialization")
                        # Используем initialization как URI
                        uri = initialization or media
                    else:
                        continue

                # Resolve relative URL
                if uri and not uri.startswith("http"):
                    if uri.startswith("/"):
                        parts = base_url.split("/")
                        uri = f"{parts[0]}//{parts[2]}/{uri.lstrip('/')}"
                    else:
                        base_path = "/".join(base_url.split("/")[:-1])
                        uri = f"{base_path}/{uri}"

                if uri:
                    variant = StreamVariant(
                        bandwidth=_parse_bandwidth(bandwidth),
                        resolution=resolution,
                        codecs=codecs,
                        uri=uri,
                        is_default=False,
                    )
                    variants.append(variant)

        if not variants:
            return {
                "variants": [],
                "total_variants": 0,
                "is_live": is_live,
                "error": "No video representations found in DASH manifest",
            }

        # Конвертируем в словари
        variants_data = [v.to_dict() for v in variants]

        return {
            "variants": variants_data,
            "total_variants": len(variants),
            "is_live": is_live,
            "error": None,
        }

    except Exception as e:
        logger.exception("Ошибка при парсинге DASH manifest")
        return {
            "variants": [],
            "total_variants": 0,
            "is_live": False,
            "error": str(e),
        }


# =============================================================================
# Основная функция валидации
# =============================================================================

async def validate_stream(
    stream_url: str,
    client: Optional[httpx.AsyncClient] = None,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Валидировать HLS/DASH поток и извлечь метаданные.

    Args:
        stream_url: URL потока (.m3u8 или .mpd)
        client: Опциональный HTTP клиент
        timeout: Таймаут запроса в секундах

    Returns:
        dict с результатами валидации:
            - success: True если успешно
            - stream_type: Тип потока (hls, dash)
            - is_live: True если live stream
            - is_accessible: True если URL доступен
            - variants: Список вариантов стрима
            - total_variants: Количество вариантов
            - error: Описание ошибки (если произошла)
    """
    if not stream_url:
        return {
            "success": False,
            "stream_type": StreamType.UNKNOWN.value,
            "error": "Не указан URL потока",
        }

    # Определяем тип потока
    stream_type = detect_stream_type(stream_url)

    if stream_type == StreamType.UNKNOWN:
        return {
            "success": False,
            "stream_type": StreamType.UNKNOWN.value,
            "error": "Не удалось определить тип потока (ожидается .m3u8 или .mpd)",
        }

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    try:
        # Загружаем манифест/плейлист
        resp = await client.get(stream_url)
        if resp.status_code != 200:
            return {
                "success": False,
                "stream_type": stream_type.value,
                "error": f"Ошибка загрузки: HTTP {resp.status_code}",
                "is_accessible": False,
            }

        content = resp.text

        # Парсим в зависимости от типа
        if stream_type == StreamType.HLS:
            result = await parse_hls_master_playlist(content, stream_url)
        else:  # DASH
            result = await parse_dash_manifest(content, stream_url)

        if result.get("error"):
            return {
                "success": False,
                "stream_type": stream_type.value,
                "error": result["error"],
                "is_accessible": True,
            }

        return {
            "success": True,
            "stream_type": stream_type.value,
            "is_live": result.get("is_live", False),
            "is_accessible": True,
            "variants": result.get("variants", []),
            "total_variants": result.get("total_variants", 0),
            "error": None,
        }

    except Exception as e:
        logger.exception(f"Ошибка при валидации потока {stream_url}")
        return {
            "success": False,
            "stream_type": stream_type.value,
            "error": str(e),
            "is_accessible": False,
        }

    finally:
        if own_client and client:
            await client.aclose()


# =============================================================================
# Sync wrapper для удобства
# =============================================================================

def validate_stream_sync(
    stream_url: str,
    timeout: int = 15,
) -> Dict[str, Any]:
    """Синхронная обёртка для validate_stream.

    Args:
        stream_url: URL потока
        timeout: Таймаут запроса

    Returns:
        dict с результатами валидации
    """
    import asyncio

    async def _validate():
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            return await validate_stream(stream_url, client=client)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_validate())


# =============================================================================
# Класс HLSService (как в API)
# =============================================================================

class HLSService:
    """Сервис для работы с HLS/DASH потоками.

    Предоставляет унифицированный интерфейс для валидации и получения
    метаданных стриминговых потоков.
    """

    def __init__(self, timeout: int = 15):
        """Инициализировать сервис.

        Args:
            timeout: Таймаут HTTP запросов по умолчанию
        """
        self.timeout = timeout

    async def validate(
        self,
        stream_url: str,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Dict[str, Any]:
        """Валидировать поток.

        Args:
            stream_url: URL потока
            client: Опциональный HTTP клиент

        Returns:
            Результаты валидации
        """
        return await validate_stream(
            stream_url,
            client=client,
            timeout=self.timeout,
        )

    def validate_sync(self, stream_url: str) -> Dict[str, Any]:
        """Синхронная валидация потока.

        Args:
            stream_url: URL потока

        Returns:
            Результаты валидации
        """
        return validate_stream_sync(stream_url, timeout=self.timeout)

    def detect_type(self, stream_url: str) -> StreamType:
        """Определить тип потока.

        Args:
            stream_url: URL потока

        Returns:
            StreamType enum значение
        """
        return detect_stream_type(stream_url)
