"""
Тесты для transcode_client.py

Integration tests для взаимодействия с Rust transcoder сервисом.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTranscodeClient:
    """Тесты для TranscodeClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Тест инициализации клиента с URL."""
        from streamer.transcode_client import TranscodeClient

        client = TranscodeClient(
            rust_transcoder_url="http://localhost:8090",
            fallback_enabled=True,
        )

        assert client.rust_transcoder_url == "http://localhost:8090"
        assert client.fallback_enabled is True

    @pytest.mark.asyncio
    async def test_transcode_request_success(self):
        """Тест успешного запроса на транскодирование."""
        from streamer.transcode_client import TranscodeClient, TranscodeRequest

        client = TranscodeClient(rust_transcoder_url="http://localhost:8090")

        with patch.object(client, "_make_request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "session_id": "test-uuid",
                "status": "processing",
                "content_type": "audio/ogg",
            }
            mock_request.return_value = mock_response

            result = await client.transcode(
                TranscodeRequest(
                    source_url="https://example.com/audio.mp3",
                    format="opus",
                    quality="medium",
                )
            )

            assert result["session_id"] == "test-uuid"

    @pytest.mark.asyncio
    async def test_fallback_on_connection_error(self):
        """Тест fallback на subprocess при connection error."""
        from streamer.transcode_client import TranscodeClient, TranscodeRequest
        import httpx

        client = TranscodeClient(
            rust_transcoder_url="http://localhost:8090",
            fallback_enabled=True,
        )

        with patch.object(client, "_make_request") as mock_request:
            # Симулируем connection error
            mock_request.side_effect = httpx.ConnectError("Connection refused")

            with patch.object(client, "_fallback_subprocess") as mock_fallback:
                mock_fallback.return_value = b"audio_data"

                result = await client.transcode_stream(
                    TranscodeRequest(
                        source_url="https://example.com/audio.mp3",
                        format="opus",
                    )
                )

                # Должен был вызваться fallback
                mock_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self):
        """Тест что fallback не вызывается когда отключён."""
        from streamer.transcode_client import TranscodeClient, TranscodeRequest
        import httpx

        client = TranscodeClient(
            rust_transcoder_url="http://localhost:8090",
            fallback_enabled=False,
        )

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(httpx.ConnectError):
                await client.transcode(
                    TranscodeRequest(
                        source_url="https://example.com/audio.mp3",
                        format="opus",
                    )
                )

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Тест что circuit breaker открывается после нескольких failures."""
        from streamer.transcode_client import TranscodeClient, TranscodeRequest
        import httpx

        client = TranscodeClient(
            rust_transcoder_url="http://localhost:8090",
            fallback_enabled=True,
            circuit_breaker_threshold=3,
        )

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = httpx.ConnectError("Connection refused")

            with patch.object(client, "_fallback_subprocess") as mock_fallback:
                mock_fallback.return_value = b"audio_data"

                # Делаем несколько неудачных запросов
                for _ in range(5):
                    await client.transcode_stream(
                        TranscodeRequest(source_url="https://example.com/audio.mp3")
                    )

                # Circuit breaker должен быть открыт
                assert client.circuit_breaker.is_open is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_after_timeout(self):
        """Тест что circuit breaker переходит в half-open после timeout."""
        from streamer.transcode_client import TranscodeClient

        client = TranscodeClient(
            rust_transcoder_url="http://localhost:8090",
            circuit_breaker_timeout=0.1,  # 100ms для теста
        )

        # Открываем circuit breaker
        client.circuit_breaker.open()
        assert client.circuit_breaker.is_open is True

        # Ждём timeout
        await asyncio.sleep(0.15)

        # Должен перейти в half-open
        assert client.circuit_breaker.is_half_open is True

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Тест retry с exponential backoff."""
        from streamer.transcode_client import TranscodeClient, TranscodeRequest
        import httpx

        client = TranscodeClient(
            rust_transcoder_url="http://localhost:8090",
            max_retries=3,
            retry_base_delay=0.01,  # Маленький delay для теста
        )

        call_times = []

        async def mock_request(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            raise httpx.ConnectError("Connection refused")

        with patch.object(client, "_make_request", side_effect=mock_request):
            with pytest.raises(Exception):
                await client.transcode(
                    TranscodeRequest(source_url="https://example.com/audio.mp3")
                )

        # Проверяем что было 3 попытки
        assert len(call_times) == 3

        # Проверяем что delay увеличивался
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]
            # Exponential backoff: второй delay должен быть больше первого
            assert delay2 >= delay1


class TestTranscodeRequest:
    """Тесты для TranscodeRequest model."""

    def test_request_defaults(self):
        """Тест значений по умолчанию."""
        from streamer.transcode_client import TranscodeRequest

        req = TranscodeRequest(source_url="https://example.com/audio.mp3")

        assert req.format == "opus"
        assert req.quality == "medium"
        assert req.normalize is False

    def test_request_with_filters(self):
        """Тест запроса с фильтрами."""
        from streamer.transcode_client import TranscodeRequest

        req = TranscodeRequest(
            source_url="https://example.com/audio.mp3",
            format="opus",
            normalize=True,
            target_loudness=-16.0,
            fade_in=2.0,
        )

        assert req.normalize is True
        assert req.target_loudness == -16.0
        assert req.fade_in == 2.0

    def test_request_to_dict(self):
        """Тест конвертации в dict для API."""
        from streamer.transcode_client import TranscodeRequest

        req = TranscodeRequest(
            source_url="https://example.com/audio.mp3",
            format="mp3",
            bitrate=192,
        )

        data = req.to_dict()

        assert data["source_url"] == "https://example.com/audio.mp3"
        assert data["format"] == "mp3"
        assert data["bitrate"] == 192
