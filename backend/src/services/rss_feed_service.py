"""Сервис для парсинга RSS фидов с видео-контентом.

Поддержка:
- RSS/Atom фиды с enclosure тегами
- Media RSS (media:content, media:thumbnail)
- YouTube RSS фиды
- Vimeo RSS фиды
- Видео подкасты

Цель: извлекать видео URL из RSS фидов для добавления в плейлист.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

import httpx


logger = logging.getLogger(__name__)


class VideoEnclosure:
    """Контейнер для информации о видео-enclosure."""

    def __init__(
        self,
        url: str,
        title: Optional[str] = None,
        duration: Optional[int] = None,
        thumbnail: Optional[str] = None,
        mime_type: Optional[str] = None,
        size: Optional[int] = None,
        published: Optional[str] = None,
    ):
        """Инициализировать видео-enclosure.

        Args:
            url: URL видео
            title: Заголовок видео
            duration: Длительность в секундах
            thumbnail: URL превью изображения
            mime_type: MIME тип файла
            size: Размер файла в байтах
            published: Дата публикации (ISO формат)
        """
        self.url = url
        self.title = title
        self.duration = duration
        self.thumbnail = thumbnail
        self.mime_type = mime_type
        self.size = size
        self.published = published

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь."""
        return {
            "url": self.url,
            "title": self.title,
            "duration": self.duration,
            "thumbnail": self.thumbnail,
            "mime_type": self.mime_type,
            "size": self.size,
            "published": self.published,
        }


class FeedFormat(str, Enum):
    """Поддерживаемые форматы фидов."""

    RSS = "rss"
    ATOM = "atom"
    MEDIA_RSS = "media_rss"
    UNKNOWN = "unknown"


# =============================================================================
# Вспомогательные функции для парсинга
# =============================================================================

def _is_video_mime_type(mime_type: Optional[str]) -> bool:
    """Проверить, является ли MIME тип видео.

    Args:
        mime_type: MIME тип для проверки

    Returns:
        True если это видео тип
    """
    if not mime_type:
        return False

    mime_lower = mime_type.lower().strip()

    # Прямые видео типы
    video_types = [
        "video/mp4",
        "video/webm",
        "video/mpeg",
        "video/quicktime",
        "video/x-matroska",
        "video/x-msvideo",
        "video/x-flv",
    ]

    if mime_lower in video_types:
        return True

    # Проверяем префикс
    if mime_lower.startswith("video/"):
        return True

    return False


def _is_video_url(url: str) -> bool:
    """Проверить, является ли URL видео-файлом.

    Args:
        url: URL для проверки

    Returns:
        True если URL указывает на видео-файл
    """
    if not url:
        return False

    url_lower = url.lower().strip()

    # Проверяем расширение файла
    video_extensions = [
        ".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv",
        ".flv", ".m4v", ".mpg", ".mpeg", ".3gp", ".ogv"
    ]

    for ext in video_extensions:
        if url_lower.endswith(ext):
            return True

    return False


def _parse_duration(duration_str: Optional[str]) -> Optional[int]:
    """Парсить длительность из строки.

    Поддерживаемые форматы:
    - Секунды (число)
    - HH:MM:SS
    - ISO 8601 duration (PT1H30M45S)

    Args:
        duration_str: Строка с длительностью

    Returns:
        Длительность в секундах или None
    """
    if not duration_str:
        return None

    duration_str = duration_str.strip()

    # Пробуем парсить как число (секунды)
    try:
        return int(duration_str)
    except (ValueError, TypeError):
        pass

    # Парсим HH:MM:SS формат
    if ":" in duration_str:
        parts = duration_str.split(":")
        try:
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + int(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + int(s)
        except (ValueError, TypeError):
            pass

    # Парсим ISO 8601 duration (PT1H30M45S)
    if duration_str.startswith("PT"):
        try:
            total_seconds = 0
            # Удаляем PT
            duration_str = duration_str[2:]

            # Extract hours
            h_match = re.search(r"(\d+)H", duration_str)
            if h_match:
                total_seconds += int(h_match.group(1)) * 3600

            # Extract minutes
            m_match = re.search(r"(\d+)M", duration_str)
            if m_match:
                total_seconds += int(m_match.group(1)) * 60

            # Extract seconds
            s_match = re.search(r"(\d+)S", duration_str)
            if s_match:
                total_seconds += int(s_match.group(1))

            return total_seconds if total_seconds > 0 else None
        except (ValueError, TypeError):
            pass

    return None


# =============================================================================
# Основная функция парсинга
# =============================================================================

async def parse_feed(
    feed_url: str,
    client: Optional[httpx.AsyncClient] = None,
    max_items: int = 50,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Парсит RSS/Atom feed и извлекает видео-enclosures.

    Args:
        feed_url: URL RSS фида
        client: Опциональный HTTP клиент
        max_items: Максимальное количество элементов для извлечения
        timeout: Таймаут запроса в секундах

    Returns:
        dict с результатами парсинга:
            - success: True если успешно
            - feed_title: Заголовок фида
            - feed_url: URL фида
            - format: Формат фида (rss, atom, media_rss)
            - enclosures: Список VideoEnclosure объектов
            - total_enclosures: Общее количество найденных видео
            - error: Описание ошибки (если произошла)
    """
    if not feed_url:
        return {"success": False, "error": "Не указан URL фида"}

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    try:
        # Загружаем фид
        resp = await client.get(feed_url)
        if resp.status_code != 200:
            return {
                "success": False,
                "error": f"Ошибка загрузки фида: HTTP {resp.status_code}"
            }

        content = resp.text

        # Парсим XML
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            return {"success": False, "error": "Не установлен модуль xml.etree"}

        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            return {"success": False, "error": f"Ошибка парсинга XML: {str(e)}"}

        # Определяем формат фида
        feed_format = _detect_feed_format(root)

        # Извлекаем заголовок фида
        feed_title = _extract_feed_title(root, feed_format)

        # Извлекаем video enclosures
        enclosures = _extract_enclosures(root, feed_format)

        # Ограничиваем количество
        if len(enclosures) > max_items:
            enclosures = enclosures[:max_items]

        # Конвертируем в словари
        enclosures_data = [enc.to_dict() for enc in enclosures]

        return {
            "success": True,
            "feed_title": feed_title,
            "feed_url": feed_url,
            "format": feed_format.value,
            "enclosures": enclosures_data,
            "total_enclosures": len(enclosures),
        }

    except Exception as e:
        logger.exception(f"Ошибка при парсинге фида {feed_url}")
        return {"success": False, "error": str(e)}

    finally:
        if own_client and client:
            await client.aclose()


def _detect_feed_format(root) -> FeedFormat:
    """Определить формат фида по XML элементу.

    Args:
        root: Корневой XML элемент

    Returns:
        FeedFormat enum значение
    """
    tag = root.tag.lower()

    # RSS format
    if "rss" in tag:
        return FeedFormat.RSS

    # Atom format
    if "feed" in tag:
        return FeedFormat.ATOM

    # Check for Media RSS namespaces
    for child in root.iter():
        if "media" in child.tag.lower():
            return FeedFormat.MEDIA_RSS

    return FeedFormat.UNKNOWN


def _extract_feed_title(root, feed_format: FeedFormat) -> Optional[str]:
    """Извлечь заголовок фида.

    Args:
        root: Корневой XML элемент
        feed_format: Формат фида

    Returns:
        Заголовок фида или None
    """
    try:
        if feed_format == FeedFormat.RSS:
            # RSS: /rss/channel/title
            channel = root.find(".//channel")
            if channel is not None:
                title = channel.find("title")
                if title is not None and title.text:
                    return title.text.strip()

        elif feed_format == FeedFormat.ATOM:
            # Atom: /feed/title
            title = root.find(".//{http://www.w3.org/2005/Atom}title")
            if title is None or not title.text:
                title = root.find(".//title")
            if title is not None and title.text:
                return title.text.strip()

        # Fallback: ищем любой title
        title = root.find(".//title")
        if title is not None and title.text:
            return title.text.strip()

    except Exception:
        pass

    return None


def _extract_enclosures(root, feed_format: FeedFormat) -> List[VideoEnclosure]:
    """Извлечь video enclosures из фида.

    Args:
        root: Корневой XML элемент
        feed_format: Формат фида

    Returns:
        Список VideoEnclosure объектов
    """
    enclosures: List[VideoEnclosure] = []

    try:
        if feed_format == FeedFormat.RSS:
            enclosures = _extract_rss_enclosures(root)
        elif feed_format == FeedFormat.ATOM:
            enclosures = _extract_atom_enclosures(root)
        else:
            # Для неизвестного формата пробуем оба метода
            enclosures = _extract_rss_enclosures(root)
            if not enclosures:
                enclosures = _extract_atom_enclosures(root)

    except Exception as e:
        logger.warning(f"Ошибка при извлечении enclosures: {e}")

    return enclosures


def _extract_rss_enclosures(root) -> List[VideoEnclosure]:
    """Извлечь enclosures из RSS фида.

    Поддерживает:
    - <enclosure url="..." type="video/..."/>
    - <media:content url="..." medium="video"/>
    - <media:group><media:content .../></media:group>

    Args:
        root: Корневой XML элемент

    Returns:
        Список VideoEnclosure объектов
    """
    enclosures: List[VideoEnclosure] = []

    # Namespaces для Media RSS
    namespaces = {
        "media": "http://search.yahoo.com/mrss/",
        "yt": "http://www.youtube.com/xml/schemas/2015",
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    }

    # Ищем все items
    items = root.findall(".//item")
    if not items:
        return enclosures

    for item in items:
        # 1. Пробуем стандартный enclosure тег
        enclosure = item.find("enclosure")
        if enclosure is not None:
            url = enclosure.get("url")
            mime_type = enclosure.get("type")
            size_str = enclosure.get("length")

            if url and (_is_video_mime_type(mime_type) or _is_video_url(url)):
                enc = VideoEnclosure(
                    url=url.strip(),
                    mime_type=mime_type,
                    size=int(size_str) if size_str and size_str.isdigit() else None,
                    title=_get_item_text(item, "title"),
                    thumbnail=_extract_media_thumbnail(item, namespaces),
                    published=_get_item_text(item, "pubDate"),
                )
                enclosures.append(enc)
                continue

        # 2. Пробуем Media RSS content
        media_content = item.find(".//media:content", namespaces)
        if media_content is not None:
            url = media_content.get("url")
            mime_type = media_content.get("type")
            medium = media_content.get("medium")
            duration_str = media_content.get("duration")

            if url:
                is_video = (
                    _is_video_mime_type(mime_type) or
                    _is_video_url(url) or
                    medium == "video"
                )

                if is_video:
                    enc = VideoEnclosure(
                        url=url.strip(),
                        mime_type=mime_type,
                        duration=_parse_duration(duration_str),
                        title=_get_item_text(item, "title"),
                        thumbnail=_extract_media_thumbnail(item, namespaces),
                        published=_get_item_text(item, "pubDate"),
                    )
                    enclosures.append(enc)
                    continue

        # 3. Пробуем media:group (YouTube и др.)
        media_group = item.find(".//media:group", namespaces)
        if media_group is not None:
            group_content = media_group.find(".//media:content", namespaces)
            if group_content is not None:
                url = group_content.get("url")
                mime_type = group_content.get("type")
                duration_str = group_content.get("duration")

                if url:
                    enc = VideoEnclosure(
                        url=url.strip(),
                        mime_type=mime_type,
                        duration=_parse_duration(duration_str),
                        title=_get_item_text(item, "title"),
                        thumbnail=_extract_media_thumbnail(item, namespaces),
                        published=_get_item_text(item, "pubDate"),
                    )
                    enclosures.append(enc)
                    continue

        # 4. Пробуем найти video ссылку в description/link
        link = _get_item_text(item, "link")
        if link and _is_video_url(link):
            enc = VideoEnclosure(
                url=link.strip(),
                title=_get_item_text(item, "title"),
                thumbnail=_extract_media_thumbnail(item, namespaces),
                published=_get_item_text(item, "pubDate"),
            )
            enclosures.append(enc)

    return enclosures


def _extract_atom_enclosures(root) -> List[VideoEnclosure]:
    """Извлечь enclosures из Atom фида.

    Поддерживает:
    - <link rel="enclosure" href="..." type="video/..."/>
    - <media:content .../>

    Args:
        root: Корневой XML элемент

    Returns:
        Список VideoEnclosure объектов
    """
    enclosures: List[VideoEnclosure] = []

    namespaces = {
        "media": "http://search.yahoo.com/mrss/",
        "atom": "http://www.w3.org/2005/Atom",
    }

    # Ищем все entries
    entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
    if not entries:
        # Fallback: пробуем без namespace
        entries = root.findall(".//entry")

    if not entries:
        return enclosures

    for entry in entries:
        # 1. Пробуем link rel="enclosure"
        for link in entry.findall(".//{http://www.w3.org/2005/Atom}link"):
            if link is None:
                continue

            rel = link.get("rel", "")
            href = link.get("href")
            mime_type = link.get("type")
            length_str = link.get("length")

            if rel == "enclosure" and href:
                if _is_video_mime_type(mime_type) or _is_video_url(href):
                    enc = VideoEnclosure(
                        url=href.strip(),
                        mime_type=mime_type,
                        size=int(length_str) if length_str and length_str.isdigit() else None,
                        title=_get_item_text(entry, "title"),
                        published=_get_item_text(entry, "published"),
                    )
                    enclosures.append(enc)
                    break

        # 2. Пробуем Media RSS content
        media_content = entry.find(".//media:content", namespaces)
        if media_content is not None:
            url = media_content.get("url")
            mime_type = media_content.get("type")
            medium = media_content.get("medium")
            duration_str = media_content.get("duration")

            if url:
                is_video = (
                    _is_video_mime_type(mime_type) or
                    _is_video_url(url) or
                    medium == "video"
                )

                if is_video:
                    enc = VideoEnclosure(
                        url=url.strip(),
                        mime_type=mime_type,
                        duration=_parse_duration(duration_str),
                        title=_get_item_text(entry, "title"),
                        thumbnail=_extract_media_thumbnail(entry, namespaces),
                        published=_get_item_text(entry, "published"),
                    )
                    enclosures.append(enc)
                    continue

    return enclosures


def _get_item_text(item, tag_name: str) -> Optional[str]:
    """Безопасно извлечь текст из элемента.

    Args:
        item: XML элемент
        tag_name: Имя тега

    Returns:
        Текст или None
    """
    try:
        elem = item.find(tag_name)
        if elem is not None and elem.text:
            return elem.text.strip()
    except Exception:
        pass

    return None


def _extract_media_thumbnail(item, namespaces: Dict[str, str]) -> Optional[str]:
    """Извлечь URL превью изображения из Media RSS.

    Args:
        item: XML элемент item/entry
        namespaces: XML namespaces

    Returns:
        URL превью или None
    """
    try:
        # Пробуем media:thumbnail
        thumbnail = item.find(".//media:thumbnail", namespaces)
        if thumbnail is not None:
            url = thumbnail.get("url")
            if url:
                return url.strip()

        # Пробуем media:group/media:thumbnail
        group = item.find(".//media:group", namespaces)
        if group is not None:
            thumbnail = group.find(".//media:thumbnail", namespaces)
            if thumbnail is not None:
                url = thumbnail.get("url")
                if url:
                    return url.strip()

    except Exception:
        pass

    return None


# =============================================================================
# Sync wrapper для удобства
# =============================================================================

def parse_feed_sync(
    feed_url: str,
    max_items: int = 50,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Синхронная обёртка для parse_feed.

    Args:
        feed_url: URL RSS фида
        max_items: Максимальное количество элементов
        timeout: Таймаут запроса

    Returns:
        dict с результатами парсинга
    """
    import asyncio

    async def _parse():
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            return await parse_feed(feed_url, client=client, max_items=max_items)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_parse())
