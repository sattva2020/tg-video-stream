"""
Unit тесты для audio API endpoints.

Тестирует:
- POST /audio/transcode - транскодирование аудио
- GET /audio/transcode/stream - streaming
- GET /audio/settings - получение настроек
- PUT /audio/settings - обновление настроек
- GET /audio/health - health check
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json


class TestTranscodeEndpoint:
    """Тесты для POST /audio/transcode."""
    
    def test_transcode_success(self, client, auth_headers, mock_rust_transcoder):
        """Успешный запрос транскодирования."""
        payload = {
            "source_url": "https://example.com/audio.mp3",
            "format": "mp3",
            "codec": "libmp3lame",
            "quality": "high",
            "speed": 1.5
        }
        
        response = client.post(
            "/api/v1/audio/transcode",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "processing"
        
        # Проверка вызова rust-transcoder
        mock_rust_transcoder.post.assert_called_once()
    
    def test_transcode_with_equalizer_preset(self, client, auth_headers, mock_rust_transcoder):
        """Транскодирование с equalizer preset."""
        payload = {
            "source_url": "https://example.com/audio.mp3",
            "format": "opus",
            "codec": "libopus",
            "quality": "medium",
            "speed": 1.0,
            "equalizer_preset": "bass_boost"
        }
        
        response = client.post(
            "/api/v1/audio/transcode",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
    
    def test_transcode_with_custom_equalizer(self, client, auth_headers, mock_rust_transcoder):
        """Транскодирование с custom equalizer."""
        payload = {
            "source_url": "https://example.com/audio.mp3",
            "format": "mp3",
            "codec": "libmp3lame",
            "quality": "high",
            "speed": 0.8,
            "equalizer_custom": {
                "bands": [
                    {"frequency": 60, "gain": 3.0},
                    {"frequency": 230, "gain": 1.5}
                ]
            }
        }
        
        response = client.post(
            "/api/v1/audio/transcode",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
    
    def test_transcode_invalid_speed(self, client, auth_headers):
        """Ошибка валидации: недопустимая скорость."""
        payload = {
            "source_url": "https://example.com/audio.mp3",
            "format": "mp3",
            "codec": "libmp3lame",
            "quality": "high",
            "speed": 3.0  # Слишком быстро (max 2.0)
        }
        
        response = client.post(
            "/api/v1/audio/transcode",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_transcode_unauthorized(self, client):
        """Ошибка: отсутствует authentication."""
        payload = {
            "source_url": "https://example.com/audio.mp3",
            "format": "mp3",
            "codec": "libmp3lame",
            "quality": "high",
            "speed": 1.0
        }
        
        response = client.post("/api/v1/audio/transcode", json=payload)
        
        assert response.status_code == 401
    
    def test_transcode_rust_service_unavailable(self, client, auth_headers):
        """Ошибка: rust-transcoder недоступен."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            payload = {
                "source_url": "https://example.com/audio.mp3",
                "format": "mp3",
                "codec": "libmp3lame",
                "quality": "high",
                "speed": 1.0
            }
            
            response = client.post(
                "/api/v1/audio/transcode",
                json=payload,
                headers=auth_headers
            )
            
            assert response.status_code == 503


class TestStreamEndpoint:
    """Тесты для GET /audio/transcode/stream."""
    
    def test_stream_success(self, client, auth_headers):
        """Успешный streaming запрос."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "audio/mpeg"}
            
            async def mock_aiter_bytes():
                yield b"audio_chunk_1"
                yield b"audio_chunk_2"
            
            mock_response.aiter_bytes.return_value = mock_aiter_bytes()
            mock_client.get.return_value.__aenter__.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            response = client.get(
                "/api/v1/audio/transcode/stream",
                params={"session_id": "test-session-123"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/mpeg"
    
    def test_stream_missing_session_id(self, client, auth_headers):
        """Ошибка: отсутствует session_id."""
        response = client.get(
            "/api/v1/audio/transcode/stream",
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_stream_unauthorized(self, client):
        """Ошибка: отсутствует authentication."""
        response = client.get(
            "/api/v1/audio/transcode/stream",
            params={"session_id": "test-session-123"}
        )
        
        assert response.status_code == 401


class TestSettingsEndpoint:
    """Тесты для GET/PUT /audio/settings."""
    
    def test_get_settings_success(self, client, auth_headers, test_user_settings):
        """Успешное получение настроек."""
        response = client.get("/api/v1/audio/settings", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["speed"] == 1.0
        assert data["equalizer_preset"] == "flat"
        assert data["pitch_correction"] is False
    
    def test_get_settings_creates_default(self, client, auth_headers, test_user, db_session):
        """Создание настроек по умолчанию при первом запросе."""
        # Убедимся, что настроек нет
        from src.models.playback_settings import PlaybackSettings
        db_session.query(PlaybackSettings).filter(
            PlaybackSettings.user_id == test_user.id
        ).delete()
        db_session.commit()
        
        response = client.get("/api/v1/audio/settings", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "speed" in data
        assert "equalizer_preset" in data
    
    def test_update_settings_speed(self, client, auth_headers, test_user_settings):
        """Обновление speed настройки."""
        payload = {"speed": 1.25}
        
        response = client.put(
            "/api/v1/audio/settings",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["speed"] == 1.25
    
    def test_update_settings_equalizer_preset(self, client, auth_headers, test_user_settings):
        """Обновление equalizer preset."""
        payload = {"equalizer_preset": "bass_boost"}
        
        response = client.put(
            "/api/v1/audio/settings",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["equalizer_preset"] == "bass_boost"
    
    def test_update_settings_pitch_correction(self, client, auth_headers, test_user_settings):
        """Обновление pitch correction."""
        payload = {"pitch_correction": True}
        
        response = client.put(
            "/api/v1/audio/settings",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["pitch_correction"] is True
    
    def test_update_settings_multiple_fields(self, client, auth_headers, test_user_settings):
        """Обновление нескольких настроек одновременно."""
        payload = {
            "speed": 1.5,
            "equalizer_preset": "treble_boost",
            "pitch_correction": True
        }
        
        response = client.put(
            "/api/v1/audio/settings",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["speed"] == 1.5
        assert data["equalizer_preset"] == "treble_boost"
        assert data["pitch_correction"] is True
    
    def test_update_settings_invalid_speed(self, client, auth_headers, test_user_settings):
        """Ошибка валидации: недопустимая скорость."""
        payload = {"speed": 3.0}  # Слишком быстро
        
        response = client.put(
            "/api/v1/audio/settings",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_settings_unauthorized(self, client):
        """Ошибка: отсутствует authentication."""
        response = client.get("/api/v1/audio/settings")
        assert response.status_code == 401
        
        response = client.put("/api/v1/audio/settings", json={"speed": 1.5})
        assert response.status_code == 401


class TestHealthEndpoint:
    """Тесты для GET /audio/health."""
    
    def test_health_check_success(self, client, auth_headers):
        """Успешный health check."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "healthy",
                "service": "rust-transcoder",
                "version": "1.0.0"
            }
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            response = client.get("/api/v1/audio/health", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
    
    def test_health_check_service_down(self, client, auth_headers):
        """Health check: сервис недоступен."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("Connection refused")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            response = client.get("/api/v1/audio/health", headers=auth_headers)
            
            assert response.status_code == 503
    
    def test_health_unauthorized(self, client):
        """Ошибка: отсутствует authentication."""
        response = client.get("/api/v1/audio/health")
        assert response.status_code == 401


class TestEdgeCases:
    """Тесты для edge cases и error handling."""
    
    def test_transcode_empty_source_url(self, client, auth_headers):
        """Edge case: пустой source_url."""
        payload = {
            "source_url": "",
            "format": "mp3",
            "codec": "libmp3lame",
            "quality": "high",
            "speed": 1.0
        }
        
        response = client.post(
            "/api/v1/audio/transcode",
            json=payload,
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    def test_transcode_invalid_format(self, client, auth_headers):
        """Edge case: недопустимый формат."""
        payload = {
            "source_url": "https://example.com/audio.mp3",
            "format": "invalid_format",
            "codec": "libmp3lame",
            "quality": "high",
            "speed": 1.0
        }
        
        response = client.post(
            "/api/v1/audio/transcode",
            json=payload,
            headers=auth_headers
        )
        
        # Может быть 422 (validation) или 400 (bad request)
        assert response.status_code in [400, 422]
    
    def test_update_settings_empty_payload(self, client, auth_headers, test_user_settings):
        """Edge case: пустой payload для обновления."""
        response = client.put(
            "/api/v1/audio/settings",
            json={},
            headers=auth_headers
        )
        
        # Должен вернуть текущие настройки без изменений
        assert response.status_code == 200
    
    def test_transcode_timeout(self, client, auth_headers):
        """Edge case: timeout при запросе к rust-transcoder."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            import httpx
            mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            payload = {
                "source_url": "https://example.com/audio.mp3",
                "format": "mp3",
                "codec": "libmp3lame",
                "quality": "high",
                "speed": 1.0
            }
            
            response = client.post(
                "/api/v1/audio/transcode",
                json=payload,
                headers=auth_headers
            )
            
            assert response.status_code in [503, 504]  # Service unavailable or Gateway timeout
