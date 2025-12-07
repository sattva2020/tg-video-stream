"""
Тесты для fallback механизма

Unit tests для retry/circuit breaker логики.
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestCircuitBreaker:
    """Тесты для CircuitBreaker pattern."""

    def test_initial_state_is_closed(self):
        """Circuit breaker должен быть closed при создании."""
        from streamer.transcode_client import CircuitBreaker

        cb = CircuitBreaker(threshold=5, timeout=30.0)

        assert cb.is_closed is True
        assert cb.is_open is False
        assert cb.is_half_open is False

    def test_opens_after_threshold_failures(self):
        """Circuit breaker открывается после threshold failures."""
        from streamer.transcode_client import CircuitBreaker

        cb = CircuitBreaker(threshold=3, timeout=30.0)

        # Регистрируем failures
        cb.record_failure()
        assert cb.is_closed is True

        cb.record_failure()
        assert cb.is_closed is True

        cb.record_failure()
        # После третьего failure должен открыться
        assert cb.is_open is True

    def test_success_resets_failure_count(self):
        """Успешный вызов сбрасывает счётчик failures."""
        from streamer.transcode_client import CircuitBreaker

        cb = CircuitBreaker(threshold=3, timeout=30.0)

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0
        assert cb.is_closed is True

    def test_half_open_after_timeout(self):
        """После timeout circuit breaker переходит в half-open."""
        from streamer.transcode_client import CircuitBreaker

        cb = CircuitBreaker(threshold=1, timeout=0.1)

        # Открываем
        cb.record_failure()
        assert cb.is_open is True

        # Ждём timeout
        time.sleep(0.15)

        # Теперь должен быть half-open
        assert cb.is_half_open is True

    def test_closes_on_success_in_half_open(self):
        """В half-open state успех закрывает circuit breaker."""
        from streamer.transcode_client import CircuitBreaker

        cb = CircuitBreaker(threshold=1, timeout=0.1)

        # Открываем и ждём timeout
        cb.record_failure()
        time.sleep(0.15)

        assert cb.is_half_open is True

        # Успех должен закрыть
        cb.record_success()
        assert cb.is_closed is True

    def test_opens_on_failure_in_half_open(self):
        """В half-open state failure снова открывает circuit breaker."""
        from streamer.transcode_client import CircuitBreaker

        cb = CircuitBreaker(threshold=1, timeout=0.1)

        # Открываем и ждём timeout
        cb.record_failure()
        time.sleep(0.15)

        assert cb.is_half_open is True

        # Failure должен снова открыть
        cb.record_failure()
        assert cb.is_open is True

    def test_allow_request_when_closed(self):
        """В closed state запросы разрешены."""
        from streamer.transcode_client import CircuitBreaker

        cb = CircuitBreaker(threshold=3, timeout=30.0)

        assert cb.allow_request() is True

    def test_block_request_when_open(self):
        """В open state запросы блокируются."""
        from streamer.transcode_client import CircuitBreaker

        cb = CircuitBreaker(threshold=1, timeout=30.0)
        cb.record_failure()

        assert cb.is_open is True
        assert cb.allow_request() is False


class TestRetryLogic:
    """Тесты для retry логики с exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_calculates_correct_delays(self):
        """Проверяет что delay увеличивается экспоненциально."""
        from streamer.transcode_client import calculate_backoff_delay

        base_delay = 1.0
        max_delay = 60.0

        # Первая попытка
        delay1 = calculate_backoff_delay(attempt=0, base_delay=base_delay, max_delay=max_delay)
        assert delay1 == 1.0

        # Вторая попытка (2^1 = 2)
        delay2 = calculate_backoff_delay(attempt=1, base_delay=base_delay, max_delay=max_delay)
        assert delay2 == 2.0

        # Третья попытка (2^2 = 4)
        delay3 = calculate_backoff_delay(attempt=2, base_delay=base_delay, max_delay=max_delay)
        assert delay3 == 4.0

    @pytest.mark.asyncio
    async def test_retry_respects_max_delay(self):
        """Delay не превышает max_delay."""
        from streamer.transcode_client import calculate_backoff_delay

        delay = calculate_backoff_delay(
            attempt=10,  # 2^10 = 1024
            base_delay=1.0,
            max_delay=60.0,
        )

        assert delay == 60.0

    @pytest.mark.asyncio
    async def test_retry_with_jitter(self):
        """Jitter добавляет случайность к delay."""
        from streamer.transcode_client import calculate_backoff_delay

        delays = set()
        for _ in range(10):
            delay = calculate_backoff_delay(
                attempt=2,
                base_delay=1.0,
                max_delay=60.0,
                jitter=True,
            )
            delays.add(round(delay, 2))

        # С jitter должны быть разные значения
        assert len(delays) > 1


class TestFallbackSubprocess:
    """Тесты для fallback subprocess ffmpeg."""

    @pytest.mark.asyncio
    async def test_subprocess_command_building(self):
        """Тест построения ffmpeg команды для fallback."""
        from streamer.transcode_client import build_ffmpeg_command

        cmd = build_ffmpeg_command(
            source_url="https://example.com/audio.mp3",
            format="opus",
            bitrate=64,
            sample_rate=48000,
        )

        assert "ffmpeg" in cmd[0]
        assert "-i" in cmd
        assert "https://example.com/audio.mp3" in cmd
        assert "libopus" in cmd
        assert "64k" in cmd

    @pytest.mark.asyncio
    async def test_subprocess_command_with_filters(self):
        """Тест построения команды с фильтрами."""
        from streamer.transcode_client import build_ffmpeg_command

        cmd = build_ffmpeg_command(
            source_url="https://example.com/audio.mp3",
            format="opus",
            normalize=True,
            target_loudness=-16.0,
        )

        assert "-af" in cmd
        # Ищем аргумент после -af
        af_idx = cmd.index("-af")
        filters = cmd[af_idx + 1]
        assert "loudnorm" in filters

    @pytest.mark.asyncio
    async def test_subprocess_handles_pipe_output(self):
        """Тест что subprocess правильно настроен для pipe output."""
        from streamer.transcode_client import build_ffmpeg_command

        cmd = build_ffmpeg_command(
            source_url="https://example.com/audio.mp3",
            format="opus",
        )

        # Должен выводить в pipe:1
        assert "pipe:1" in cmd or "-" in cmd


class TestHealthCheck:
    """Тесты для health check Rust сервиса."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Тест успешного health check."""
        from streamer.transcode_client import TranscodeClient

        client = TranscodeClient(rust_transcoder_url="http://localhost:8090")

        with patch.object(client, "_make_health_request") as mock_health:
            mock_health.return_value = {"status": "healthy"}

            is_healthy = await client.check_health()

            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Тест неудачного health check."""
        from streamer.transcode_client import TranscodeClient
        import httpx

        client = TranscodeClient(rust_transcoder_url="http://localhost:8090")

        with patch.object(client, "_make_health_request") as mock_health:
            mock_health.side_effect = httpx.ConnectError("Connection refused")

            is_healthy = await client.check_health()

            assert is_healthy is False
