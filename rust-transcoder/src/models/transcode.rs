//! Модели запросов и ответов для транскодирования

use serde::{Deserialize, Serialize};
use uuid::Uuid;

use super::enums::{AudioCodec, AudioFormat, AudioQuality, EqPreset, TranscodeStatus, VideoCodec, VideoFormat, VideoQuality};

/// Аудио фильтры для транскодирования
#[derive(Debug, Clone, Default, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub struct AudioFilters {
    /// EQ preset (flat, bass_boost, voice, treble)
    #[serde(default)]
    pub eq_preset: Option<EqPreset>,

    /// Множитель скорости (0.5-2.0, где 1.0 = без изменений)
    #[serde(default)]
    pub speed: Option<f32>,

    /// Множитель громкости (0.0-2.0, где 1.0 = без изменений)
    #[serde(default)]
    pub volume: Option<f32>,
}

impl AudioFilters {
    /// Валидация фильтров
    pub fn validate(&self) -> Result<(), String> {
        // Проверка speed
        if let Some(speed) = self.speed {
            if speed < 0.5 || speed > 2.0 {
                return Err("speed must be between 0.5 and 2.0".to_string());
            }
        }

        // Проверка volume
        if let Some(volume) = self.volume {
            if volume < 0.0 || volume > 2.0 {
                return Err("volume must be between 0.0 and 2.0".to_string());
            }
        }

        Ok(())
    }

    /// Проверяет, есть ли активные фильтры
    pub fn has_filters(&self) -> bool {
        self.eq_preset.is_some() || self.speed.is_some() || self.volume.is_some()
    }
}

/// Запрос на транскодирование аудио
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "snake_case")]
pub struct TranscodeRequest {
    /// URL источника аудио
    pub source_url: String,

    /// Целевой формат (opus, mp3, aac, pcm)
    #[serde(default = "default_format")]
    pub format: AudioFormat,

    /// Также принимаем output_format как alias для format
    #[serde(default)]
    pub output_format: Option<String>,

    /// Аудио кодек
    #[serde(default = "default_codec")]
    pub codec: AudioCodec,

    /// Качество транскодирования
    #[serde(default)]
    pub quality: AudioQuality,

    /// Битрейт в kbps (если не указан - определяется quality)
    #[serde(default)]
    pub bitrate: Option<u32>,

    /// Sample rate в Hz (если не указан - определяется quality)
    #[serde(default)]
    pub sample_rate: Option<u32>,

    /// Количество каналов (1=mono, 2=stereo)
    #[serde(default)]
    pub channels: Option<u8>,

    /// Аудио фильтры (speed, volume, eq_preset)
    #[serde(default)]
    pub audio_filters: Option<AudioFilters>,

    /// Применить нормализацию громкости
    #[serde(default)]
    pub normalize: bool,

    /// Целевой уровень громкости в LUFS (для нормализации)
    #[serde(default = "default_target_loudness")]
    pub target_loudness: f32,

    /// Применить fade in (секунды)
    #[serde(default)]
    pub fade_in: Option<f32>,

    /// Применить fade out (секунды)
    #[serde(default)]
    pub fade_out: Option<f32>,
}

fn default_format() -> AudioFormat {
    AudioFormat::Opus
}

fn default_codec() -> AudioCodec {
    AudioCodec::Libopus
}

fn default_target_loudness() -> f32 {
    -16.0
}

impl TranscodeRequest {
    /// Валидация запроса
    pub fn validate(&self) -> Result<(), String> {
        // Проверка URL
        if self.source_url.is_empty() {
            return Err("source_url is required".to_string());
        }

        // SSRF защита: проверка что URL безопасен
        super::url_validation::validate_source_url(&self.source_url)
            .map_err(|e| format!("SSRF protection: {}", e))?;

        // Проверка битрейта
        if let Some(bitrate) = self.bitrate {
            if bitrate < 8 || bitrate > 512 {
                return Err("bitrate must be between 8 and 512 kbps".to_string());
            }
        }

        // Проверка sample rate
        if let Some(sr) = self.sample_rate {
            let valid_rates = [8000, 12000, 16000, 24000, 44100, 48000, 96000];
            if !valid_rates.contains(&sr) {
                return Err(format!(
                    "sample_rate must be one of: {:?}",
                    valid_rates
                ));
            }
        }

        // Проверка каналов
        if let Some(ch) = self.channels {
            if ch < 1 || ch > 2 {
                return Err("channels must be 1 (mono) or 2 (stereo)".to_string());
            }
        }

        // Проверка audio_filters
        if let Some(ref filters) = self.audio_filters {
            filters.validate()?;
        }

        // Проверка fade
        if let Some(fade) = self.fade_in {
            if fade < 0.0 || fade > 30.0 {
                return Err("fade_in must be between 0 and 30 seconds".to_string());
            }
        }

        if let Some(fade) = self.fade_out {
            if fade < 0.0 || fade > 30.0 {
                return Err("fade_out must be between 0 and 30 seconds".to_string());
            }
        }

        // Проверка target_loudness
        if self.target_loudness < -70.0 || self.target_loudness > 0.0 {
            return Err("target_loudness must be between -70 and 0 LUFS".to_string());
        }

        Ok(())
    }
}

/// Начальный ответ при старте транскодирования
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "snake_case")]
pub struct TranscodeResponse {
    /// Уникальный ID сессии транскодирования
    pub session_id: Uuid,

    /// Статус транскодирования
    pub status: TranscodeStatus,

    /// Content-Type результирующего потока
    pub content_type: String,

    /// Сообщение (опционально)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
}

impl TranscodeResponse {
    pub fn new(session_id: Uuid, content_type: impl Into<String>) -> Self {
        Self {
            session_id,
            status: TranscodeStatus::Processing,
            content_type: content_type.into(),
            message: None,
        }
    }

    pub fn with_message(mut self, message: impl Into<String>) -> Self {
        self.message = Some(message.into());
        self
    }
}

/// Ответ о статусе сессии транскодирования
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "snake_case")]
pub struct TranscodeStatusResponse {
    /// ID сессии
    pub session_id: Uuid,

    /// Текущий статус
    pub status: TranscodeStatus,

    /// Время работы в секундах
    pub duration_seconds: f64,

    /// Переданные байты
    pub bytes_transferred: u64,

    /// Сообщение об ошибке (если есть)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

/// Запрос на транскодирование видео
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "snake_case")]
pub struct VideoTranscodeRequest {
    /// URL источника видео
    pub source_url: String,

    /// Целевой формат видео (mp4, mkv, webm)
    #[serde(default = "default_video_format")]
    pub format: VideoFormat,

    /// Видео кодек (h264, h265)
    #[serde(default = "default_video_codec")]
    pub video_codec: VideoCodec,

    /// Аудио кодек (aac, mp3, opus)
    #[serde(default = "default_video_audio_codec")]
    pub audio_codec: AudioCodec,

    /// Качество транскодирования (low, medium, high, ultra)
    #[serde(default)]
    pub quality: VideoQuality,

    /// Битрейт видео в kbps (если не указан - определяется quality)
    #[serde(default)]
    pub video_bitrate: Option<u32>,

    /// Битрейт аудио в kbps (если не указан - определяется quality)
    #[serde(default)]
    pub audio_bitrate: Option<u32>,

    /// Ширина видео в пикселях (если не указана - определяется aspect ratio)
    #[serde(default)]
    pub width: Option<u32>,

    /// Высота видео в пикселях (если не указана - определяется quality)
    #[serde(default)]
    pub height: Option<u32>,

    /// FPS (если не указан - как в source)
    #[serde(default)]
    pub fps: Option<u32>,

    /// Коррекция ориентации (0, 90, 180, 270 градусов)
    #[serde(default)]
    pub orientation: Option<u32>,

    /// Применить нормализацию громкости
    #[serde(default)]
    pub normalize: bool,

    /// Целевой уровень громкости в LUFS
    #[serde(default = "default_target_loudness")]
    pub target_loudness: f32,
}

fn default_video_format() -> VideoFormat {
    VideoFormat::Mp4
}

fn default_video_codec() -> VideoCodec {
    VideoCodec::H264
}

fn default_video_audio_codec() -> AudioCodec {
    AudioCodec::Aac
}

impl VideoTranscodeRequest {
    /// Валидация запроса
    pub fn validate(&self) -> Result<(), String> {
        // Проверка URL
        if self.source_url.is_empty() {
            return Err("source_url is required".to_string());
        }

        // SSRF защита: проверка что URL безопасен
        super::url_validation::validate_source_url(&self.source_url)
            .map_err(|e| format!("SSRF protection: {}", e))?;

        // Проверка битрейта видео
        if let Some(bitrate) = self.video_bitrate {
            if bitrate < 100 || bitrate > 50000 {
                return Err("video_bitrate must be between 100 and 50000 kbps".to_string());
            }
        }

        // Проверка битрейта аудио
        if let Some(bitrate) = self.audio_bitrate {
            if bitrate < 32 || bitrate > 320 {
                return Err("audio_bitrate must be between 32 and 320 kbps".to_string());
            }
        }

        // Проверка разрешения
        if let Some(w) = self.width {
            if w < 64 || w > 7680 {
                return Err("width must be between 64 and 7680 pixels".to_string());
            }
        }

        if let Some(h) = self.height {
            if h < 64 || h > 4320 {
                return Err("height must be between 64 and 4320 pixels".to_string());
            }
        }

        // Проверка FPS
        if let Some(fps) = self.fps {
            if fps < 1 || fps > 120 {
                return Err("fps must be between 1 and 120".to_string());
            }
        }

        // Проверка ориентации
        if let Some(orientation) = self.orientation {
            if ![0, 90, 180, 270].contains(&orientation) {
                return Err("orientation must be 0, 90, 180, or 270 degrees".to_string());
            }
        }

        // Проверка target_loudness
        if self.target_loudness < -70.0 || self.target_loudness > 0.0 {
            return Err("target_loudness must be between -70 and 0 LUFS".to_string());
        }

        // Проверка совместимости кодека с форматом
        if !self.video_codec.is_compatible_with(self.format) {
            return Err(format!(
                "video_codec {} is not compatible with format {}",
                self.video_codec, self.format
            ));
        }

        Ok(())
    }
}

/// Ответ на запрос видео транскодирования
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "snake_case")]
pub struct VideoTranscodeResponse {
    /// Уникальный ID сессии транскодирования
    pub session_id: Uuid,

    /// Статус транскодирования
    pub status: TranscodeStatus,

    /// Content-Type результирующего потока
    pub content_type: String,

    /// Сообщение (опционально)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,

    /// Видео кодек
    pub video_codec: String,

    /// Аудио кодек
    pub audio_codec: String,

    /// Качество
    pub quality: String,
}

impl VideoTranscodeResponse {
    pub fn new(
        session_id: Uuid,
        content_type: impl Into<String>,
        video_codec: VideoCodec,
        audio_codec: AudioCodec,
        quality: VideoQuality,
    ) -> Self {
        Self {
            session_id,
            status: TranscodeStatus::Processing,
            content_type: content_type.into(),
            message: None,
            video_codec: video_codec.to_string(),
            audio_codec: audio_codec.to_string(),
            quality: quality.to_string(),
        }
    }

    pub fn with_message(mut self, message: impl Into<String>) -> Self {
        self.message = Some(message.into());
        self
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn valid_request() -> TranscodeRequest {
        TranscodeRequest {
            source_url: "https://example.com/audio.mp3".to_string(),
            format: AudioFormat::Opus,
            output_format: None,
            codec: AudioCodec::Libopus,
            quality: AudioQuality::Medium,
            bitrate: None,
            sample_rate: None,
            channels: None,
            audio_filters: None,
            normalize: false,
            target_loudness: -16.0,
            fade_in: None,
            fade_out: None,
        }
    }

    #[test]
    fn test_valid_request() {
        let req = valid_request();
        assert!(req.validate().is_ok());
    }

    #[test]
    fn test_empty_source_url() {
        let mut req = valid_request();
        req.source_url = String::new();
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_invalid_bitrate() {
        let mut req = valid_request();
        req.bitrate = Some(1000); // Too high
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_invalid_sample_rate() {
        let mut req = valid_request();
        req.sample_rate = Some(22050); // Not in valid list
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_valid_sample_rate() {
        let mut req = valid_request();
        req.sample_rate = Some(48000);
        assert!(req.validate().is_ok());
    }

    #[test]
    fn test_invalid_channels() {
        let mut req = valid_request();
        req.channels = Some(5); // Invalid
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_transcode_response() {
        let resp = TranscodeResponse::new(Uuid::new_v4(), "audio/ogg");
        assert_eq!(resp.content_type, "audio/ogg");
        assert_eq!(resp.status, TranscodeStatus::Processing);
    }

    // SSRF Protection Tests

    #[test]
    fn test_ssrf_file_scheme_blocked() {
        let mut req = valid_request();
        req.source_url = "file:///etc/passwd".to_string();
        let result = req.validate();
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("SSRF protection"));
        assert!(result.unwrap_err().contains("Forbidden URL scheme"));
    }

    #[test]
    fn test_ssrf_localhost_blocked() {
        let mut req = valid_request();
        req.source_url = "http://localhost:8080/audio.mp3".to_string();
        let result = req.validate();
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("localhost"));
    }

    #[test]
    fn test_ssrf_127_0_0_1_blocked() {
        let mut req = valid_request();
        req.source_url = "http://127.0.0.1/audio.mp3".to_string();
        let result = req.validate();
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("localhost"));
    }

    #[test]
    fn test_ssrf_private_ip_10_blocked() {
        let mut req = valid_request();
        req.source_url = "http://10.0.0.1/audio.mp3".to_string();
        let result = req.validate();
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("private IP"));
    }

    #[test]
    fn test_ssrf_private_ip_192_168_blocked() {
        let mut req = valid_request();
        req.source_url = "http://192.168.1.1/audio.mp3".to_string();
        let result = req.validate();
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("private IP"));
    }

    #[test]
    fn test_ssrf_private_ip_172_16_blocked() {
        let mut req = valid_request();
        req.source_url = "http://172.16.0.1/audio.mp3".to_string();
        let result = req.validate();
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("private IP"));
    }

    #[test]
    fn test_ssrf_public_url_allowed() {
        let mut req = valid_request();
        req.source_url = "https://cdn.example.com/audio.mp3".to_string();
        assert!(req.validate().is_ok());
    }

    #[test]
    fn test_ssrf_public_ip_allowed() {
        let mut req = valid_request();
        req.source_url = "http://8.8.8.8/audio.mp3".to_string();
        assert!(req.validate().is_ok());
    }

    // AudioFilters tests
    #[test]
    fn test_audio_filters_valid_speed() {
        let filters = AudioFilters {
            eq_preset: None,
            speed: Some(1.5),
            volume: None,
        };
        assert!(filters.validate().is_ok());
    }

    #[test]
    fn test_audio_filters_speed_too_low() {
        let filters = AudioFilters {
            eq_preset: None,
            speed: Some(0.3), // < 0.5
            volume: None,
        };
        assert!(filters.validate().is_err());
    }

    #[test]
    fn test_audio_filters_speed_too_high() {
        let filters = AudioFilters {
            eq_preset: None,
            speed: Some(2.5), // > 2.0
            volume: None,
        };
        assert!(filters.validate().is_err());
    }

    #[test]
    fn test_audio_filters_valid_volume() {
        let filters = AudioFilters {
            eq_preset: None,
            speed: None,
            volume: Some(1.5),
        };
        assert!(filters.validate().is_ok());
    }

    #[test]
    fn test_audio_filters_volume_negative() {
        let filters = AudioFilters {
            eq_preset: None,
            speed: None,
            volume: Some(-0.5), // < 0.0
        };
        assert!(filters.validate().is_err());
    }

    #[test]
    fn test_audio_filters_volume_too_high() {
        let filters = AudioFilters {
            eq_preset: None,
            speed: None,
            volume: Some(2.5), // > 2.0
        };
        assert!(filters.validate().is_err());
    }

    #[test]
    fn test_audio_filters_has_filters() {
        let empty = AudioFilters::default();
        assert!(!empty.has_filters());

        let with_eq = AudioFilters {
            eq_preset: Some(EqPreset::BassBoost),
            speed: None,
            volume: None,
        };
        assert!(with_eq.has_filters());

        let with_speed = AudioFilters {
            eq_preset: None,
            speed: Some(1.25),
            volume: None,
        };
        assert!(with_speed.has_filters());
    }

    #[test]
    fn test_request_with_valid_filters() {
        let mut req = valid_request();
        req.audio_filters = Some(AudioFilters {
            eq_preset: Some(EqPreset::Voice),
            speed: Some(1.0),
            volume: Some(0.8),
        });
        assert!(req.validate().is_ok());
    }

    #[test]
    fn test_request_with_invalid_filters() {
        let mut req = valid_request();
        req.audio_filters = Some(AudioFilters {
            eq_preset: None,
            speed: Some(3.0), // Invalid
            volume: None,
        });
        assert!(req.validate().is_err());
    }

    // VideoTranscodeRequest tests
    fn valid_video_request() -> VideoTranscodeRequest {
        VideoTranscodeRequest {
            source_url: "https://example.com/video.mp4".to_string(),
            format: VideoFormat::Mp4,
            video_codec: VideoCodec::H264,
            audio_codec: AudioCodec::Aac,
            quality: VideoQuality::Medium,
            video_bitrate: None,
            audio_bitrate: None,
            width: None,
            height: None,
            fps: None,
            orientation: None,
            normalize: false,
            target_loudness: -16.0,
        }
    }

    #[test]
    fn test_video_valid_request() {
        let req = valid_video_request();
        assert!(req.validate().is_ok());
    }

    #[test]
    fn test_video_empty_source_url() {
        let mut req = valid_video_request();
        req.source_url = String::new();
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_video_invalid_video_bitrate() {
        let mut req = valid_video_request();
        req.video_bitrate = Some(100000); // Too high
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_video_invalid_audio_bitrate() {
        let mut req = valid_video_request();
        req.audio_bitrate = Some(1000); // Too high
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_video_invalid_resolution() {
        let mut req = valid_video_request();
        req.width = Some(10000); // Too high
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_video_invalid_fps() {
        let mut req = valid_video_request();
        req.fps = Some(200); // Too high
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_video_invalid_orientation() {
        let mut req = valid_video_request();
        req.orientation = Some(45); // Invalid
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_video_valid_orientation() {
        let mut req = valid_video_request();
        req.orientation = Some(90);
        assert!(req.validate().is_ok());

        req.orientation = Some(180);
        assert!(req.validate().is_ok());

        req.orientation = Some(270);
        assert!(req.validate().is_ok());
    }

    #[test]
    fn test_video_ssrf_protection() {
        let mut req = valid_video_request();
        req.source_url = "file:///etc/passwd".to_string();
        assert!(req.validate().is_err());
        assert!(req.validate().unwrap_err().contains("SSRF protection"));
    }

    #[test]
    fn test_video_codec_compatibility() {
        let mut req = valid_video_request();
        req.video_codec = VideoCodec::H265;
        req.format = VideoFormat::Webm;
        // H265 is not compatible with WebM
        assert!(req.validate().is_err());
    }

    #[test]
    fn test_video_transcode_response() {
        let resp = VideoTranscodeResponse::new(
            Uuid::new_v4(),
            "video/mp4",
            VideoCodec::H264,
            AudioCodec::Aac,
            VideoQuality::High,
        );
        assert_eq!(resp.content_type, "video/mp4");
        assert_eq!(resp.status, TranscodeStatus::Processing);
        assert_eq!(resp.video_codec, "libx264");
        assert_eq!(resp.audio_codec, "aac");
        assert_eq!(resp.quality, "high");
    }
}
