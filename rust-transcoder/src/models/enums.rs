//! Перечисления для аудио форматов, кодеков и статусов

use serde::{Deserialize, Serialize};
use std::fmt;

/// Поддерживаемые аудио форматы (контейнеры)
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum AudioFormat {
    /// Ogg container (для Opus)
    #[default]
    Opus,
    /// MP3
    Mp3,
    /// AAC в ADTS container
    Aac,
    /// Raw PCM (S16LE)
    Pcm,
    /// WAV container
    Wav,
    /// FLAC
    Flac,
}

impl AudioFormat {
    /// Возвращает MIME type для формата
    pub fn content_type(&self) -> &'static str {
        match self {
            AudioFormat::Opus => "audio/ogg",
            AudioFormat::Mp3 => "audio/mpeg",
            AudioFormat::Aac => "audio/aac",
            AudioFormat::Pcm => "audio/pcm",
            AudioFormat::Wav => "audio/wav",
            AudioFormat::Flac => "audio/flac",
        }
    }

    /// Возвращает FFmpeg format name
    pub fn ffmpeg_format(&self) -> &'static str {
        match self {
            AudioFormat::Opus => "ogg",
            AudioFormat::Mp3 => "mp3",
            AudioFormat::Aac => "adts",
            AudioFormat::Pcm => "s16le",
            AudioFormat::Wav => "wav",
            AudioFormat::Flac => "flac",
        }
    }

    /// Расширение файла
    pub fn extension(&self) -> &'static str {
        match self {
            AudioFormat::Opus => "ogg",
            AudioFormat::Mp3 => "mp3",
            AudioFormat::Aac => "aac",
            AudioFormat::Pcm => "pcm",
            AudioFormat::Wav => "wav",
            AudioFormat::Flac => "flac",
        }
    }
}

impl fmt::Display for AudioFormat {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AudioFormat::Opus => write!(f, "opus"),
            AudioFormat::Mp3 => write!(f, "mp3"),
            AudioFormat::Aac => write!(f, "aac"),
            AudioFormat::Pcm => write!(f, "pcm"),
            AudioFormat::Wav => write!(f, "wav"),
            AudioFormat::Flac => write!(f, "flac"),
        }
    }
}

/// Поддерживаемые аудио кодеки
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum AudioCodec {
    /// libopus - высококачественный Opus encoder
    #[default]
    Libopus,
    /// libmp3lame - MP3 encoder
    Libmp3lame,
    /// AAC encoder (ffmpeg native или libfdk_aac)
    Aac,
    /// PCM signed 16-bit little-endian
    PcmS16le,
    /// FLAC lossless
    Flac,
}

impl AudioCodec {
    /// Возвращает FFmpeg codec name
    pub fn ffmpeg_codec(&self) -> &'static str {
        match self {
            AudioCodec::Libopus => "libopus",
            AudioCodec::Libmp3lame => "libmp3lame",
            AudioCodec::Aac => "aac",
            AudioCodec::PcmS16le => "pcm_s16le",
            AudioCodec::Flac => "flac",
        }
    }

    /// Проверяет совместимость кодека с форматом
    pub fn is_compatible_with(&self, format: AudioFormat) -> bool {
        matches!(
            (self, format),
            (AudioCodec::Libopus, AudioFormat::Opus)
                | (AudioCodec::Libmp3lame, AudioFormat::Mp3)
                | (AudioCodec::Aac, AudioFormat::Aac)
                | (AudioCodec::PcmS16le, AudioFormat::Pcm)
                | (AudioCodec::PcmS16le, AudioFormat::Wav)
                | (AudioCodec::Flac, AudioFormat::Flac)
        )
    }
}

impl fmt::Display for AudioCodec {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.ffmpeg_codec())
    }
}

/// Качество транскодирования
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "lowercase")]
pub enum AudioQuality {
    /// Низкое качество (экономия трафика)
    Low,
    /// Среднее качество (баланс)
    #[default]
    Medium,
    /// Высокое качество
    High,
    /// Максимальное качество (lossless где возможно)
    Lossless,
}

impl AudioQuality {
    /// Возвращает битрейт для кодека в kbps
    pub fn bitrate_for_codec(&self, codec: AudioCodec) -> u32 {
        match (self, codec) {
            // Opus
            (AudioQuality::Low, AudioCodec::Libopus) => 32,
            (AudioQuality::Medium, AudioCodec::Libopus) => 64,
            (AudioQuality::High, AudioCodec::Libopus) => 128,
            (AudioQuality::Lossless, AudioCodec::Libopus) => 256,

            // MP3
            (AudioQuality::Low, AudioCodec::Libmp3lame) => 64,
            (AudioQuality::Medium, AudioCodec::Libmp3lame) => 128,
            (AudioQuality::High, AudioCodec::Libmp3lame) => 192,
            (AudioQuality::Lossless, AudioCodec::Libmp3lame) => 320,

            // AAC
            (AudioQuality::Low, AudioCodec::Aac) => 48,
            (AudioQuality::Medium, AudioCodec::Aac) => 96,
            (AudioQuality::High, AudioCodec::Aac) => 160,
            (AudioQuality::Lossless, AudioCodec::Aac) => 256,

            // PCM/FLAC - битрейт не применим, возвращаем 0
            (_, AudioCodec::PcmS16le) => 0,
            (_, AudioCodec::Flac) => 0,
        }
    }

    /// Возвращает sample rate в Hz
    pub fn sample_rate(&self) -> u32 {
        match self {
            AudioQuality::Low => 24000,
            AudioQuality::Medium => 44100,
            AudioQuality::High => 48000,
            AudioQuality::Lossless => 48000,
        }
    }
}

impl fmt::Display for AudioQuality {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AudioQuality::Low => write!(f, "low"),
            AudioQuality::Medium => write!(f, "medium"),
            AudioQuality::High => write!(f, "high"),
            AudioQuality::Lossless => write!(f, "lossless"),
        }
    }
}

/// Статус сессии транскодирования
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum TranscodeStatus {
    /// В очереди на обработку
    Queued,
    /// Идёт обработка
    Processing,
    /// Стриминг активен
    Streaming,
    /// Успешно завершено
    Completed,
    /// Ошибка
    Failed,
    /// Отменено
    Cancelled,
}

/// Предустановки эквалайзера
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize, Default)]
#[serde(rename_all = "snake_case")]
pub enum EqPreset {
    /// Без изменений (pass-through)
    #[default]
    Flat,
    /// Усиление низких частот (+6dB @ 100Hz)
    BassBoost,
    /// Оптимизация для голоса (highpass 80Hz, mid boost)
    Voice,
    /// Усиление высоких частот (+4dB @ 8kHz)
    Treble,
}

impl EqPreset {
    /// Возвращает описание preset
    pub fn description(&self) -> &'static str {
        match self {
            EqPreset::Flat => "No EQ applied",
            EqPreset::BassBoost => "Enhanced bass (+6dB @ 100Hz)",
            EqPreset::Voice => "Voice optimized (highpass 80Hz, presence boost)",
            EqPreset::Treble => "Enhanced treble (+4dB @ 8kHz)",
        }
    }
}

impl fmt::Display for EqPreset {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            EqPreset::Flat => write!(f, "flat"),
            EqPreset::BassBoost => write!(f, "bass_boost"),
            EqPreset::Voice => write!(f, "voice"),
            EqPreset::Treble => write!(f, "treble"),
        }
    }
}

impl fmt::Display for TranscodeStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TranscodeStatus::Queued => write!(f, "queued"),
            TranscodeStatus::Processing => write!(f, "processing"),
            TranscodeStatus::Streaming => write!(f, "streaming"),
            TranscodeStatus::Completed => write!(f, "completed"),
            TranscodeStatus::Failed => write!(f, "failed"),
            TranscodeStatus::Cancelled => write!(f, "cancelled"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_audio_format_content_type() {
        assert_eq!(AudioFormat::Opus.content_type(), "audio/ogg");
        assert_eq!(AudioFormat::Mp3.content_type(), "audio/mpeg");
        assert_eq!(AudioFormat::Aac.content_type(), "audio/aac");
    }

    #[test]
    fn test_audio_format_ffmpeg() {
        assert_eq!(AudioFormat::Opus.ffmpeg_format(), "ogg");
        assert_eq!(AudioFormat::Aac.ffmpeg_format(), "adts");
    }

    #[test]
    fn test_codec_compatibility() {
        assert!(AudioCodec::Libopus.is_compatible_with(AudioFormat::Opus));
        assert!(!AudioCodec::Libopus.is_compatible_with(AudioFormat::Mp3));
        assert!(AudioCodec::Libmp3lame.is_compatible_with(AudioFormat::Mp3));
        assert!(AudioCodec::Aac.is_compatible_with(AudioFormat::Aac));
    }

    #[test]
    fn test_quality_bitrate() {
        assert_eq!(AudioQuality::Medium.bitrate_for_codec(AudioCodec::Libopus), 64);
        assert_eq!(AudioQuality::High.bitrate_for_codec(AudioCodec::Libmp3lame), 192);
        assert_eq!(AudioQuality::Lossless.bitrate_for_codec(AudioCodec::PcmS16le), 0);
    }

    #[test]
    fn test_quality_sample_rate() {
        assert_eq!(AudioQuality::Low.sample_rate(), 24000);
        assert_eq!(AudioQuality::High.sample_rate(), 48000);
    }

    #[test]
    fn test_transcode_status_display() {
        assert_eq!(TranscodeStatus::Processing.to_string(), "processing");
        assert_eq!(TranscodeStatus::Completed.to_string(), "completed");
    }

    #[test]
    fn test_eq_preset_display() {
        assert_eq!(EqPreset::Flat.to_string(), "flat");
        assert_eq!(EqPreset::BassBoost.to_string(), "bass_boost");
        assert_eq!(EqPreset::Voice.to_string(), "voice");
        assert_eq!(EqPreset::Treble.to_string(), "treble");
    }

    #[test]
    fn test_eq_preset_description() {
        assert!(!EqPreset::Flat.description().is_empty());
        assert!(EqPreset::BassBoost.description().contains("bass"));
        assert!(EqPreset::Voice.description().contains("voice") || EqPreset::Voice.description().contains("Voice"));
    }
}
