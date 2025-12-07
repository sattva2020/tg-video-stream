"""
Transcode Client

Асинхронный клиент для взаимодействия с Rust transcoder сервисом.
Поддерживает fallback на subprocess ffmpeg при недоступности сервиса.
"""

import asyncio
import logging
import os
import random
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Optional

import httpx

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Состояния Circuit Breaker."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit Breaker pattern для защиты от cascading failures.
    
    States:
    - CLOSED: Нормальная работа, запросы проходят
    - OPEN: Сервис недоступен, запросы блокируются
    - HALF_OPEN: Пробный режим после timeout
    """

    def __init__(self, threshold: int = 5, timeout: float = 30.0):
        """
        Args:
            threshold: Количество failures до открытия
            timeout: Время в секундах до перехода в half-open
        """
        self.threshold = threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self._state = CircuitBreakerState.CLOSED

    @property
    def is_closed(self) -> bool:
        self._check_state_transition()
        return self._state == CircuitBreakerState.CLOSED

    @property
    def is_open(self) -> bool:
        self._check_state_transition()
        return self._state == CircuitBreakerState.OPEN

    @property
    def is_half_open(self) -> bool:
        self._check_state_transition()
        return self._state == CircuitBreakerState.HALF_OPEN

    def _check_state_transition(self) -> None:
        """Проверяет и обновляет состояние на основе timeout."""
        if self._state == CircuitBreakerState.OPEN and self.last_failure_time:
            if time.time() - self.last_failure_time >= self.timeout:
                self._state = CircuitBreakerState.HALF_OPEN
                logger.info("Circuit breaker transitioned to HALF_OPEN")

    def record_failure(self) -> None:
        """Регистрирует неудачный запрос."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self._state == CircuitBreakerState.HALF_OPEN:
            # В half-open любой failure снова открывает
            self._state = CircuitBreakerState.OPEN
            logger.warning("Circuit breaker re-opened after failure in HALF_OPEN")
        elif self.failure_count >= self.threshold:
            self._state = CircuitBreakerState.OPEN
            logger.warning(
                f"Circuit breaker OPENED after {self.failure_count} failures"
            )

    def record_success(self) -> None:
        """Регистрирует успешный запрос."""
        if self._state == CircuitBreakerState.HALF_OPEN:
            logger.info("Circuit breaker CLOSED after successful request")
        
        self.failure_count = 0
        self.last_failure_time = None
        self._state = CircuitBreakerState.CLOSED

    def open(self) -> None:
        """Принудительно открывает circuit breaker."""
        self._state = CircuitBreakerState.OPEN
        self.last_failure_time = time.time()

    def allow_request(self) -> bool:
        """Проверяет, можно ли выполнить запрос."""
        self._check_state_transition()
        return self._state != CircuitBreakerState.OPEN


def calculate_backoff_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = False,
) -> float:
    """
    Вычисляет delay для exponential backoff.
    
    Args:
        attempt: Номер попытки (0-based)
        base_delay: Базовый delay в секундах
        max_delay: Максимальный delay
        jitter: Добавить случайность
    
    Returns:
        Delay в секундах
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    
    if jitter:
        # Добавляем jitter ±25%
        jitter_range = delay * 0.25
        delay = delay + random.uniform(-jitter_range, jitter_range)
        delay = max(0.1, delay)  # Минимум 100ms
    
    return delay


@dataclass
class AudioFilters:
    """Аудио фильтры для транскодирования."""
    
    eq_preset: Optional[str] = None  # flat, bass_boost, voice, treble
    speed: Optional[float] = None  # 0.5-2.0
    volume: Optional[float] = None  # 0.0-2.0
    
    def to_dict(self) -> dict[str, Any]:
        """Конвертирует в dict для API запроса."""
        data = {}
        if self.eq_preset is not None:
            data["eq_preset"] = self.eq_preset
        if self.speed is not None:
            data["speed"] = self.speed
        if self.volume is not None:
            data["volume"] = self.volume
        return data
    
    def has_filters(self) -> bool:
        """Проверяет наличие активных фильтров."""
        return any([self.eq_preset, self.speed, self.volume])


@dataclass
class TranscodeRequest:
    """Запрос на транскодирование."""
    
    source_url: str
    format: str = "opus"
    codec: str = "libopus"
    quality: str = "medium"
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    audio_filters: Optional[AudioFilters] = None
    normalize: bool = False
    target_loudness: float = -16.0
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Конвертирует в dict для API запроса."""
        data = {
            "source_url": self.source_url,
            "format": self.format,
            "codec": self.codec,
            "quality": self.quality,
            "normalize": self.normalize,
            "target_loudness": self.target_loudness,
        }
        
        if self.bitrate is not None:
            data["bitrate"] = self.bitrate
        if self.sample_rate is not None:
            data["sample_rate"] = self.sample_rate
        if self.channels is not None:
            data["channels"] = self.channels
        if self.audio_filters is not None and self.audio_filters.has_filters():
            data["audio_filters"] = self.audio_filters.to_dict()
        if self.fade_in is not None:
            data["fade_in"] = self.fade_in
        if self.fade_out is not None:
            data["fade_out"] = self.fade_out
            
        return data


def build_ffmpeg_command(
    source_url: str,
    format: str = "opus",
    bitrate: int = 64,
    sample_rate: int = 48000,
    channels: int = 2,
    normalize: bool = False,
    target_loudness: float = -16.0,
    fade_in: Optional[float] = None,
    audio_filters: Optional[AudioFilters] = None,
) -> list[str]:
    """
    Строит команду ffmpeg для fallback subprocess.
    
    Returns:
        Список аргументов для subprocess.
    """
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-y",
        "-i", source_url,
    ]

    # Codec mapping
    codec_map = {
        "opus": "libopus",
        "mp3": "libmp3lame",
        "aac": "aac",
        "pcm": "pcm_s16le",
    }
    codec = codec_map.get(format, "libopus")
    
    cmd.extend(["-c:a", codec])
    
    # Bitrate (если применимо)
    if format not in ("pcm",):
        cmd.extend(["-b:a", f"{bitrate}k"])
    
    # Sample rate
    cmd.extend(["-ar", str(sample_rate)])
    
    # Channels
    cmd.extend(["-ac", str(channels)])
    
    # Audio filters
    filters = []
    
    # EQ preset фильтры
    if audio_filters and audio_filters.eq_preset:
        eq_preset = audio_filters.eq_preset
        if eq_preset == "bass_boost":
            filters.append("equalizer=f=100:width_type=o:width=1.0:g=6.0")
        elif eq_preset == "voice":
            filters.append("highpass=f=80,equalizer=f=3000:width_type=o:width=1.0:g=3.0")
        elif eq_preset == "treble":
            filters.append("equalizer=f=8000:width_type=o:width=1.5:g=4.0")
        # flat - no filter
    
    # Speed filter (atempo)
    if audio_filters and audio_filters.speed:
        speed = audio_filters.speed
        if 0.5 <= speed <= 2.0 and abs(speed - 1.0) > 0.001:
            filters.append(f"atempo={speed:.4f}")
    
    # Volume filter
    if audio_filters and audio_filters.volume:
        vol = audio_filters.volume
        if abs(vol - 1.0) > 0.001:
            # Convert factor to dB: dB = 20 * log10(factor)
            import math
            db = 20.0 * math.log10(vol) if vol > 0 else -96.0
            filters.append(f"volume={db:.1f}dB")
    
    if fade_in:
        filters.append(f"afade=t=in:st=0:d={fade_in:.2f}")
    
    if normalize:
        filters.append(f"loudnorm=I={target_loudness:.1f}:TP=-1.5:LRA=11:print_format=none")
    
    if filters:
        cmd.extend(["-af", ",".join(filters)])
    
    # Output format
    format_map = {
        "opus": "ogg",
        "mp3": "mp3",
        "aac": "adts",
        "pcm": "s16le",
    }
    cmd.extend(["-f", format_map.get(format, "ogg")])
    
    # Output to stdout
    cmd.append("pipe:1")
    
    return cmd


class TranscodeClient:
    """
    Асинхронный клиент для Rust transcoder сервиса.
    
    Features:
    - HTTP клиент для Rust сервиса
    - Fallback на subprocess ffmpeg
    - Circuit breaker для защиты от cascading failures
    - Retry с exponential backoff
    """

    def __init__(
        self,
        rust_transcoder_url: Optional[str] = None,
        fallback_enabled: bool = True,
        max_retries: int = 3,
        retry_base_delay: float = 1.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 30.0,
        request_timeout: float = 30.0,
    ):
        """
        Args:
            rust_transcoder_url: URL Rust сервиса (default: from env)
            fallback_enabled: Включить fallback на subprocess
            max_retries: Максимальное количество retry
            retry_base_delay: Базовый delay для retry
            circuit_breaker_threshold: Порог для circuit breaker
            circuit_breaker_timeout: Timeout для circuit breaker
            request_timeout: Timeout для HTTP запросов
        """
        self.rust_transcoder_url = rust_transcoder_url or os.getenv(
            "RUST_TRANSCODER_URL", "http://rust-transcoder:8090"
        )
        self.fallback_enabled = fallback_enabled
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.request_timeout = request_timeout
        
        self.circuit_breaker = CircuitBreaker(
            threshold=circuit_breaker_threshold,
            timeout=circuit_breaker_timeout,
        )
        
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization HTTP клиента."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.request_timeout),
            )
        return self._client

    async def close(self) -> None:
        """Закрывает HTTP клиент."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _make_request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Выполняет HTTP запрос к Rust сервису."""
        client = await self._get_client()
        url = f"{self.rust_transcoder_url}{path}"
        return await client.request(method, url, **kwargs)

    async def _make_health_request(self) -> dict:
        """Выполняет health check запрос."""
        response = await self._make_request("GET", "/health")
        response.raise_for_status()
        return response.json()

    async def check_health(self) -> bool:
        """Проверяет доступность Rust сервиса."""
        try:
            await self._make_health_request()
            return True
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def transcode(self, request: TranscodeRequest) -> dict:
        """
        Отправляет запрос на транскодирование.
        
        Returns:
            Response с session_id и status
        """
        if not self.circuit_breaker.allow_request():
            logger.warning("Circuit breaker is OPEN, skipping request")
            raise ConnectionError("Circuit breaker is open")

        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self._make_request(
                    "POST",
                    "/api/v1/transcode",
                    json=request.to_dict(),
                )
                response.raise_for_status()
                
                self.circuit_breaker.record_success()
                return response.json()
                
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                self.circuit_breaker.record_failure()
                logger.warning(
                    f"Transcode request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                
                if attempt < self.max_retries - 1:
                    delay = calculate_backoff_delay(
                        attempt,
                        self.retry_base_delay,
                        jitter=True,
                    )
                    await asyncio.sleep(delay)
            except httpx.HTTPStatusError as e:
                # HTTP ошибки не retriable
                logger.error(f"Transcode request HTTP error: {e}")
                raise

        # Все retry исчерпаны
        raise last_error or ConnectionError("All retries exhausted")

    async def transcode_stream(
        self,
        request: TranscodeRequest,
    ) -> AsyncIterator[bytes]:
        """
        Получает streaming response транскодирования.
        
        При недоступности Rust сервиса использует fallback на subprocess.
        
        Yields:
            Chunks транскодированного аудио
        """
        use_fallback = False

        # Проверяем circuit breaker
        if not self.circuit_breaker.allow_request():
            logger.warning("Circuit breaker OPEN, using fallback")
            use_fallback = True
        
        if not use_fallback:
            try:
                async for chunk in self._stream_from_rust(request):
                    yield chunk
                return
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                self.circuit_breaker.record_failure()
                logger.warning(f"Rust transcoder unavailable: {e}")
                
                if self.fallback_enabled:
                    use_fallback = True
                else:
                    raise

        if use_fallback:
            logger.warning("Using fallback subprocess ffmpeg")
            async for chunk in self._fallback_subprocess(request):
                yield chunk

    async def _stream_from_rust(
        self,
        request: TranscodeRequest,
    ) -> AsyncIterator[bytes]:
        """Стримит аудио из Rust сервиса."""
        client = await self._get_client()
        url = f"{self.rust_transcoder_url}/api/v1/transcode"

        async with client.stream(
            "POST",
            url,
            json=request.to_dict(),
        ) as response:
            response.raise_for_status()
            
            self.circuit_breaker.record_success()
            
            async for chunk in response.aiter_bytes():
                yield chunk

    async def _fallback_subprocess(
        self,
        request: TranscodeRequest,
    ) -> AsyncIterator[bytes]:
        """Fallback на subprocess ffmpeg."""
        cmd = build_ffmpeg_command(
            source_url=request.source_url,
            format=request.format,
            bitrate=request.bitrate or 64,
            sample_rate=request.sample_rate or 48000,
            channels=request.channels or 2,
            normalize=request.normalize,
            target_loudness=request.target_loudness,
            fade_in=request.fade_in,
        )

        logger.info(f"Fallback ffmpeg command: {' '.join(cmd)}")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            while True:
                chunk = await process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
        finally:
            if process.returncode is None:
                process.terminate()
                await process.wait()

            stderr = await process.stderr.read()
            if stderr:
                logger.debug(f"FFmpeg stderr: {stderr.decode(errors='replace')}")


# Singleton instance для использования в приложении
_client: Optional[TranscodeClient] = None


def get_transcode_client() -> TranscodeClient:
    """Возвращает singleton TranscodeClient."""
    global _client
    if _client is None:
        _client = TranscodeClient()
    return _client


async def cleanup_client() -> None:
    """Очищает ресурсы клиента при shutdown."""
    global _client
    if _client:
        await _client.close()
        _client = None
