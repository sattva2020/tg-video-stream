"""Сервис распознавания музыки (Shazam)."""

from __future__ import annotations

import io
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import redis.asyncio as redis
from redis.asyncio import Redis
from shazamio import Shazam

from src.config.rate_limits import RateLimit, get_limit
from src.core.config import settings


logger = logging.getLogger(__name__)


class ShazamService:
    """Сервис для распознавания аудио и применения лимитов."""
    
    RATE_LIMIT_ENDPOINT = "recognition"
    HISTORY_LIMIT = 50  # Количество записей истории в Redis
    HISTORY_TTL = 60 * 60 * 24 * 30  # 30 дней
    
    def __init__(self, redis_client: Optional[Redis] = None):
        self.shazam = Shazam()
        self.logger = logger
        self._redis: Optional[Redis] = redis_client
        self.redis_url = settings.REDIS_URL
    
    async def recognize_track(
        self,
        audio_data: io.BytesIO,
        user_id: Optional[int] = None,
        mime_type: str = "audio/mpeg",
    ) -> Optional[Dict[str, Any]]:
        """Распознать аудио-буфер и вернуть данные трека."""
        audio_data.seek(0)
        payload = audio_data.read()
        if not payload:
            raise ValueError("Audio buffer is empty")
        result = await self.recognize_audio(payload, mime_type=mime_type)
        if result and user_id:
            self.logger.info(
                "Shazam распознал трек: user=%s artist=%s title=%s",
                user_id,
                result.get("artist"),
                result.get("title"),
            )
        return result
    
    async def identify_track(
        self,
        audio_file: str,
        user_id: int,
        channel_id: Optional[int] = None,
        user_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Обработать файл аудио для Telegram-хэндлера."""
        allowed, retry_after = await self.consume_rate_limit(user_id=user_id, user_role=user_role)
        if not allowed:
            return {
                "success": False,
                "error": "rate_limit_exceeded",
                "rate_limited": True,
                "retry_after": retry_after,
            }
        try:
            with open(audio_file, "rb") as src:
                audio_bytes = src.read()
        except OSError as exc:
            self.logger.error("Не удалось прочитать аудиофайл: %s", exc)
            return {"success": False, "error": "file_read_failed"}
        result = await self.recognize_audio(audio_bytes)
        if not result:
            return {"success": False, "error": "no_match"}
        result.update(
            {
                "success": True,
                "channel_id": channel_id,
            }
        )
        return result
    
    async def recognize_audio(
        self,
        audio_data: bytes,
        mime_type: str = "audio/mpeg",
    ) -> Optional[Dict[str, Any]]:
        """Распознать аудио-данные и вернуть словарь с треком."""
        if not audio_data:
            raise ValueError("Audio data is empty")
        temp_file: Optional[str] = None
        try:
            suffix = ".mp3" if mime_type == "audio/mpeg" else ".audio"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio_data)
                temp_file = tmp.name
            result = await self.shazam.recognize_song(temp_file)
            if not result:
                self.logger.info("Shazam не нашёл совпадений")
                return None
            track_info = self._parse_result(result)
            return track_info
        except Exception as exc:  # noqa: BLE001
            self.logger.error("Ошибка распознавания: %s", exc)
            raise
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    self.logger.debug("Не удалось удалить временный файл %s", temp_file)
    
    def _parse_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Преобразовать ответ Shazam в единый формат."""
        track = result.get("track", {})
        sections = track.get("sections", []) or []
        metadata: list[Dict[str, Any]] = []
        for section in sections:
            if section.get("type") == "SONG":
                metadata = section.get("metadata", []) or []
                break
        album = next(
            (item.get("text") for item in metadata if item.get("title", "").lower() == "album"),
            track.get("subtitle", "Unknown"),
        )
        release_year = next(
            (item.get("text") for item in metadata if item.get("title", "").lower() == "released"),
            None,
        )
        matches = result.get("matches") or []
        if matches:
            best_match = max(matches, key=lambda item: item.get("score", 0))
            raw_score = float(best_match.get("score", 0) or 0)
        else:
            raw_score = float(result.get("confidence", 0) or 0)
        confidence = raw_score / 100 if raw_score > 1 else raw_score
        confidence = max(0.0, min(confidence, 1.0))
        track_id = track.get("key") or track.get("hub", {}).get("actions", [{}])[0].get("id", "")
        cover_url = track.get("images", {}).get("coverart") or track.get("share", {}).get("image")
        duration_seconds = track.get("duration")
        return {
            "track_id": track_id or "",
            "title": track.get("title", "Unknown"),
            "artist": self._extract_artist(track.get("subtitle")),
            "album": album or "Unknown",
            "cover_url": cover_url or "",
            "confidence": confidence,
            "duration_seconds": duration_seconds,
            "release_year": release_year,
            "share_url": track.get("share", {}).get("href", ""),
            "source": "shazam",
        }
    
    def _extract_artist(self, subtitle: Optional[str]) -> str:
        if not subtitle:
            return "Unknown"
        return subtitle.split(" • ")[0].strip() or "Unknown"
    
    async def batch_recognize(self, audio_files: list[bytes]) -> list[Optional[Dict[str, Any]]]:
        """Распознать несколько файлов подряд."""
        results: list[Optional[Dict[str, Any]]] = []
        for audio_data in audio_files:
            try:
                result = await self.recognize_audio(audio_data)
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                self.logger.error("Batch recognition error: %s", exc)
                results.append(None)
        return results
    
    async def is_rate_limited(
        self,
        user_id: int | str,
        user_role: Optional[str] = None,
    ) -> bool:
        """Проверить, исчерпал ли пользователь лимит (без инкремента)."""
        redis_client = await self._get_redis()
        limit = self._resolve_limit(user_role)
        key = self._build_rate_limit_key(limit, str(user_id))
        current = await redis_client.get(key)
        return int(current) >= limit.requests if current is not None else False
    
    async def consume_rate_limit(
        self,
        user_id: int | str,
        user_role: Optional[str] = None,
    ) -> Tuple[bool, int]:
        """Инкрементировать счётчик и вернуть (доступно ли, retry_after)."""
        redis_client = await self._get_redis()
        limit = self._resolve_limit(user_role)
        key = self._build_rate_limit_key(limit, str(user_id))
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, limit.window_seconds + 1)
        if current > limit.requests:
            ttl = await redis_client.ttl(key)
            retry_after = self._retry_after(ttl, limit)
            return False, retry_after
        return True, 0
    
    async def add_to_history(
        self,
        user_id: int | str,
        track_id: Optional[str],
        artist: str,
        title: str,
        confidence: float,
    ) -> None:
        """Сохранить запись о распознавании (минимальная реализация на Redis)."""
        redis_client = await self._get_redis()
        entry_id = await redis_client.incr("shazam:history:seq")
        entry_key = f"shazam:history:entry:{entry_id}"
        payload = {
            "id": entry_id,
            "user_id": str(user_id),
            "track_id": track_id or "",
            "artist": artist,
            "title": title,
            "confidence": confidence,
            "identified_at": int(time.time()),
        }
        await redis_client.hset(entry_key, mapping=payload)
        await redis_client.expire(entry_key, self.HISTORY_TTL)
        index_key = f"shazam:history:index:{user_id}"
        member = str(entry_id)
        await redis_client.zadd(index_key, {member: payload["identified_at"]})
        total = await redis_client.zcard(index_key)
        excess = total - self.HISTORY_LIMIT
        if excess > 0:
            await redis_client.zremrangebyrank(index_key, 0, excess - 1)
        await redis_client.expire(index_key, self.HISTORY_TTL)
    
    async def get_history(
        self,
        user_id: int | str,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Вернуть стрим истории распознаваний из Redis."""
        redis_client = await self._get_redis()
        index_key = f"shazam:history:index:{user_id}"
        total = await redis_client.zcard(index_key)
        if total == 0:
            return {"total": 0, "entries": []}
        start_index = max((page - 1) * page_size, 0)
        end_index = start_index + page_size - 1
        ids = await redis_client.zrevrange(index_key, start_index, end_index)
        entries: list[Dict[str, Any]] = []
        for entry_id in ids:
            member = entry_id.decode() if isinstance(entry_id, bytes) else entry_id
            entry_key = f"shazam:history:entry:{member}"
            data = await redis_client.hgetall(entry_key)
            if not data:
                continue
            entry = {
                "id": int(data.get("id", member) or 0),
                "track_id": data.get("track_id", ""),
                "artist": data.get("artist", "Unknown"),
                "title": data.get("title", "Unknown"),
                "confidence": float(data.get("confidence", 0) or 0),
                "identified_at": self._format_timestamp(data.get("identified_at")),
            }
            entries.append(entry)
        return {"total": total, "entries": entries}
    
    async def get_history_entry(self, entry_id: int) -> Optional[Dict[str, Any]]:
        redis_client = await self._get_redis()
        entry_key = f"shazam:history:entry:{entry_id}"
        data = await redis_client.hgetall(entry_key)
        if not data:
            return None
        return {
            "id": int(data.get("id", entry_id) or entry_id),
            "user_id": data.get("user_id"),
            "track_id": data.get("track_id"),
            "artist": data.get("artist"),
            "title": data.get("title"),
            "confidence": float(data.get("confidence", 0) or 0),
            "identified_at": self._format_timestamp(data.get("identified_at")),
        }
    
    async def delete_from_history(self, entry_id: int) -> bool:
        redis_client = await self._get_redis()
        entry_key = f"shazam:history:entry:{entry_id}"
        data = await redis_client.hgetall(entry_key)
        if not data:
            return False
        user_id = data.get("user_id")
        await redis_client.delete(entry_key)
        if user_id:
            index_key = f"shazam:history:index:{user_id}"
            await redis_client.zrem(index_key, str(entry_id))
        return True
    
    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._redis
    
    def _resolve_limit(self, user_role: Optional[str]) -> RateLimit:
        role = (user_role or "user").lower()
        if role in {"vip", "premium", "admin", "superadmin"}:
            return get_limit(self.RATE_LIMIT_ENDPOINT, "vip")
        return get_limit(self.RATE_LIMIT_ENDPOINT, "user")
    
    def _sanitize_key_component(self, value: str) -> str:
        """Санитизирует строку для использования в Redis ключах."""
        import re
        return re.sub(r'[^a-zA-Z0-9_-]', '', str(value))
    
    def _build_rate_limit_key(self, limit: RateLimit, identifier: str) -> str:
        safe_id = self._sanitize_key_component(identifier)
        window_start = int(time.time() // limit.window_seconds)
        return f"{limit.key_prefix}{safe_id}:{window_start}"
    
    def _retry_after(self, ttl: int, limit: RateLimit) -> int:
        if ttl and ttl > 0:
            return ttl
        return limit.window_seconds

    def _format_timestamp(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        try:
            ts = int(value)
        except (TypeError, ValueError):
            return str(value)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
