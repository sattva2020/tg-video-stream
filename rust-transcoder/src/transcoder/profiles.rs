//! Профили транскодирования
//!
//! Определяет параметры транскодирования и генерирует FFmpeg аргументы.

use crate::models::{AudioCodec, AudioFormat, AudioQuality, TranscodeRequest};

/// Профиль транскодирования с полной конфигурацией FFmpeg
#[derive(Debug, Clone)]
pub struct TranscodeProfile {
    /// URL источника
    pub source_url: String,
    /// Формат выходного файла
    pub format: AudioFormat,
    /// Кодек
    pub codec: AudioCodec,
    /// Битрейт в kbps
    pub bitrate: u32,
    /// Sample rate в Hz
    pub sample_rate: u32,
    /// Количество каналов
    pub channels: u8,
    /// Применить нормализацию
    pub normalize: bool,
    /// Целевой уровень громкости (LUFS)
    pub target_loudness: f32,
    /// Fade in (секунды)
    pub fade_in: Option<f32>,
    /// Fade out (секунды)
    pub fade_out: Option<f32>,
}

impl TranscodeProfile {
    /// Создаёт профиль из TranscodeRequest
    pub fn from_request(req: &TranscodeRequest) -> Self {
        let bitrate = req
            .bitrate
            .unwrap_or_else(|| req.quality.bitrate_for_codec(req.codec));
        let sample_rate = req.sample_rate.unwrap_or_else(|| req.quality.sample_rate());
        let channels = req.channels.unwrap_or(2);

        Self {
            source_url: req.source_url.clone(),
            format: req.format,
            codec: req.codec,
            bitrate,
            sample_rate,
            channels,
            normalize: req.normalize,
            target_loudness: req.target_loudness,
            fade_in: req.fade_in,
            fade_out: req.fade_out,
        }
    }

    /// Строит список аргументов для FFmpeg
    pub fn build_ffmpeg_args(&self) -> Vec<String> {
        let mut args = Vec::new();

        // Глобальные опции
        args.extend([
            "-hide_banner".to_string(),
            "-loglevel".to_string(),
            "warning".to_string(),
            "-y".to_string(), // Overwrite output
        ]);

        // Input
        args.extend(["-i".to_string(), self.source_url.clone()]);

        // Audio codec
        args.extend(["-c:a".to_string(), self.codec.ffmpeg_codec().to_string()]);

        // Bitrate (если применимо)
        if self.bitrate > 0 {
            args.extend(["-b:a".to_string(), format!("{}k", self.bitrate)]);
        }

        // Sample rate
        args.extend(["-ar".to_string(), self.sample_rate.to_string()]);

        // Channels
        args.extend(["-ac".to_string(), self.channels.to_string()]);

        // Audio filters
        let filters = self.build_audio_filters();
        if !filters.is_empty() {
            args.extend(["-af".to_string(), filters]);
        }

        // Output format
        args.extend(["-f".to_string(), self.format.ffmpeg_format().to_string()]);

        // Output to stdout for streaming
        args.push("pipe:1".to_string());

        args
    }

    /// Строит цепочку аудио фильтров
    fn build_audio_filters(&self) -> String {
        use super::filters;

        let mut filter_parts = Vec::new();

        // Fade in
        if let Some(duration) = self.fade_in {
            filter_parts.push(filters::fade_in(duration));
        }

        // Fade out (требует знания длительности, пока пропускаем)
        // TODO: Реализовать fade out с duration detection

        // Нормализация loudness
        if self.normalize {
            filter_parts.push(filters::loudnorm(self.target_loudness));
        }

        filter_parts.join(",")
    }
}

/// Предопределённые профили для типичных сценариев
impl TranscodeProfile {
    /// Профиль для Telegram voice
    pub fn telegram_voice(source_url: &str) -> Self {
        Self {
            source_url: source_url.to_string(),
            format: AudioFormat::Opus,
            codec: AudioCodec::Libopus,
            bitrate: 64,
            sample_rate: 48000,
            channels: 2,
            normalize: true,
            target_loudness: -16.0,
            fade_in: None,
            fade_out: None,
        }
    }

    /// Профиль для стриминга (низкая задержка)
    pub fn low_latency(source_url: &str) -> Self {
        Self {
            source_url: source_url.to_string(),
            format: AudioFormat::Opus,
            codec: AudioCodec::Libopus,
            bitrate: 48,
            sample_rate: 48000,
            channels: 2,
            normalize: false,
            target_loudness: -16.0,
            fade_in: None,
            fade_out: None,
        }
    }

    /// Профиль высокого качества
    pub fn high_quality(source_url: &str) -> Self {
        Self {
            source_url: source_url.to_string(),
            format: AudioFormat::Opus,
            codec: AudioCodec::Libopus,
            bitrate: 128,
            sample_rate: 48000,
            channels: 2,
            normalize: true,
            target_loudness: -14.0,
            fade_in: None,
            fade_out: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_telegram_voice_profile() {
        let profile = TranscodeProfile::telegram_voice("https://example.com/audio.mp3");
        let args = profile.build_ffmpeg_args();

        assert!(args.contains(&"-c:a".to_string()));
        assert!(args.contains(&"libopus".to_string()));
        assert!(args.contains(&"-b:a".to_string()));
        assert!(args.contains(&"64k".to_string()));
    }

    #[test]
    fn test_ffmpeg_args_structure() {
        let profile = TranscodeProfile {
            source_url: "https://example.com/test.mp3".to_string(),
            format: AudioFormat::Mp3,
            codec: AudioCodec::Libmp3lame,
            bitrate: 128,
            sample_rate: 44100,
            channels: 2,
            normalize: false,
            target_loudness: -16.0,
            fade_in: None,
            fade_out: None,
        };

        let args = profile.build_ffmpeg_args();

        // Проверяем обязательные элементы
        assert!(args.contains(&"-i".to_string()));
        assert!(args.contains(&"https://example.com/test.mp3".to_string()));
        assert!(args.contains(&"pipe:1".to_string()));
        assert!(args.contains(&"-f".to_string()));
        assert!(args.contains(&"mp3".to_string()));
    }

    #[test]
    fn test_audio_filters_with_normalize() {
        let profile = TranscodeProfile {
            source_url: "test.mp3".to_string(),
            format: AudioFormat::Opus,
            codec: AudioCodec::Libopus,
            bitrate: 64,
            sample_rate: 48000,
            channels: 2,
            normalize: true,
            target_loudness: -16.0,
            fade_in: Some(2.0),
            fade_out: None,
        };

        let args = profile.build_ffmpeg_args();
        assert!(args.contains(&"-af".to_string()));

        // Находим индекс -af и проверяем следующий аргумент
        let af_idx = args.iter().position(|a| a == "-af").unwrap();
        let filters = &args[af_idx + 1];
        assert!(filters.contains("afade"));
        assert!(filters.contains("loudnorm"));
    }
}
