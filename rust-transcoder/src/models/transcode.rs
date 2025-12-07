//! Модели запросов и ответов для транскодирования

use serde::{Deserialize, Serialize};
use uuid::Uuid;

use super::enums::{AudioCodec, AudioFormat, AudioQuality, EqPreset, TranscodeStatus};

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
}
