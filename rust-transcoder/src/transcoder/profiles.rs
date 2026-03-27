//! Профили транскодирования
//!
//! Определяет параметры транскодирования и генерирует FFmpeg аргументы.

use crate::models::{AudioCodec, AudioFormat, TranscodeRequest, VideoCodec, VideoFormat};

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
    /// Видео формат (для адаптивного стриминга)
    pub video_format: Option<VideoFormat>,
    /// Видео кодек (для адаптивного стриминга)
    pub video_codec: Option<VideoCodec>,
    /// Ширина видео в пикселях
    pub width: Option<u32>,
    /// Высота видео в пикселях
    pub height: Option<u32>,
    /// Видео битрейт в kbps
    pub video_bitrate: Option<u32>,
    /// FPS (кадров в секунду)
    pub fps: Option<u32>,
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
            video_format: None,
            video_codec: None,
            width: None,
            height: None,
            video_bitrate: None,
            fps: None,
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

        // Video codec (если это видео профиль)
        if let (Some(video_codec), Some(video_format)) = (self.video_codec, self.video_format) {
            args.extend(["-c:v".to_string(), video_codec.ffmpeg_codec().to_string()]);

            // Video bitrate
            if let Some(vbitrate) = self.video_bitrate {
                args.extend(["-b:v".to_string(), format!("{}k", vbitrate)]);
            }

            // Resolution
            if let (Some(width), Some(height)) = (self.width, self.height) {
                args.extend(["-vf".to_string(), format!("scale={}x{}", width, height)]);
            }

            // FPS
            if let Some(fps) = self.fps {
                args.extend(["-r".to_string(), fps.to_string()]);
            }

            // Quick sync/FAST encoding для H.264
            if video_codec == VideoCodec::H264 {
                args.extend(["-preset".to_string(), "fast".to_string()]);
            }
        }

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
        if let Some(video_format) = self.video_format {
            args.extend(["-f".to_string(), video_format.ffmpeg_format().to_string()]);
            // MP4 requires faststart for streaming
            if video_format == VideoFormat::Mp4 {
                args.extend(["-movflags".to_string(), "faststart".to_string()]);
            }
        } else {
            args.extend(["-f".to_string(), self.format.ffmpeg_format().to_string()]);
        }

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
            video_format: None,
            video_codec: None,
            width: None,
            height: None,
            video_bitrate: None,
            fps: None,
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
            video_format: None,
            video_codec: None,
            width: None,
            height: None,
            video_bitrate: None,
            fps: None,
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
            video_format: None,
            video_codec: None,
            width: None,
            height: None,
            video_bitrate: None,
            fps: None,
        }
    }

    /// Адаптивный профиль качества 360p
    ///
    /// Низкое качество для медленных соединений или мобильных устройств.
    /// Видео: 640x360, 1000 kbps, Аудио: 64 kbps
    pub fn quality_360p(source_url: &str) -> Self {
        Self {
            source_url: source_url.to_string(),
            format: AudioFormat::Aac,
            codec: AudioCodec::Aac,
            bitrate: 64,
            sample_rate: 48000,
            channels: 2,
            normalize: false,
            target_loudness: -16.0,
            fade_in: None,
            fade_out: None,
            video_format: Some(VideoFormat::Mp4),
            video_codec: Some(VideoCodec::H264),
            width: Some(640),
            height: Some(360),
            video_bitrate: Some(1000),
            fps: Some(30),
        }
    }

    /// Адаптивный профиль качества 480p
    ///
    /// Среднее качество для баланса между качеством и битрейтом.
    /// Видео: 854x480, 2500 kbps, Аудио: 64 kbps
    pub fn quality_480p(source_url: &str) -> Self {
        Self {
            source_url: source_url.to_string(),
            format: AudioFormat::Aac,
            codec: AudioCodec::Aac,
            bitrate: 64,
            sample_rate: 48000,
            channels: 2,
            normalize: false,
            target_loudness: -16.0,
            fade_in: None,
            fade_out: None,
            video_format: Some(VideoFormat::Mp4),
            video_codec: Some(VideoCodec::H264),
            width: Some(854),
            height: Some(480),
            video_bitrate: Some(2500),
            fps: Some(30),
        }
    }

    /// Адаптивный профиль качества 720p
    ///
    /// Высокое качество для хорошего соединения.
    /// Видео: 1280x720, 5000 kbps, Аудио: 128 kbps
    pub fn quality_720p(source_url: &str) -> Self {
        Self {
            source_url: source_url.to_string(),
            format: AudioFormat::Aac,
            codec: AudioCodec::Aac,
            bitrate: 128,
            sample_rate: 48000,
            channels: 2,
            normalize: false,
            target_loudness: -16.0,
            fade_in: None,
            fade_out: None,
            video_format: Some(VideoFormat::Mp4),
            video_codec: Some(VideoCodec::H264),
            width: Some(1280),
            height: Some(720),
            video_bitrate: Some(5000),
            fps: Some(30),
        }
    }

    /// Адаптивный профиль качества 1080p
    ///
    /// Максимальное качество для быстрого соединения.
    /// Видео: 1920x1080, 8000 kbps, Аудио: 128 kbps
    pub fn quality_1080p(source_url: &str) -> Self {
        Self {
            source_url: source_url.to_string(),
            format: AudioFormat::Aac,
            codec: AudioCodec::Aac,
            bitrate: 128,
            sample_rate: 48000,
            channels: 2,
            normalize: false,
            target_loudness: -16.0,
            fade_in: None,
            fade_out: None,
            video_format: Some(VideoFormat::Mp4),
            video_codec: Some(VideoCodec::H264),
            width: Some(1920),
            height: Some(1080),
            video_bitrate: Some(8000),
            fps: Some(30),
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
            video_format: None,
            video_codec: None,
            width: None,
            height: None,
            video_bitrate: None,
            fps: None,
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
            video_format: None,
            video_codec: None,
            width: None,
            height: None,
            video_bitrate: None,
            fps: None,
        };

        let args = profile.build_ffmpeg_args();
        assert!(args.contains(&"-af".to_string()));

        // Находим индекс -af и проверяем следующий аргумент
        let af_idx = args.iter().position(|a| a == "-af").unwrap();
        let filters = &args[af_idx + 1];
        assert!(filters.contains("afade"));
        assert!(filters.contains("loudnorm"));
    }

    #[test]
    fn test_quality_360p_profile() {
        let profile = TranscodeProfile::quality_360p("https://example.com/video.mp4");
        let args = profile.build_ffmpeg_args();

        // Проверяем видео параметры
        assert!(args.contains(&"-c:v".to_string()));
        assert!(args.contains(&"libx264".to_string()));
        assert!(args.contains(&"-b:v".to_string()));
        assert!(args.contains(&"1000k".to_string()));
        assert!(args.contains(&"-vf".to_string()));
        assert!(args.iter().any(|a| a.contains("scale=640x360")));

        // Проверяем аудио параметры
        assert!(args.contains(&"-c:a".to_string()));
        assert!(args.contains(&"aac".to_string()));
        assert!(args.contains(&"-b:a".to_string()));
        assert!(args.contains(&"64k".to_string()));

        // Проверяем формат
        assert!(args.contains(&"-f".to_string()));
        assert!(args.contains(&"mp4".to_string()));
    }

    #[test]
    fn test_quality_480p_profile() {
        let profile = TranscodeProfile::quality_480p("https://example.com/video.mp4");
        let args = profile.build_ffmpeg_args();

        // Проверяем разрешение и битрейт
        assert!(args.iter().any(|a| a.contains("scale=854x480")));
        assert!(args.contains(&"2500k".to_string()));
    }

    #[test]
    fn test_quality_720p_profile() {
        let profile = TranscodeProfile::quality_720p("https://example.com/video.mp4");
        let args = profile.build_ffmpeg_args();

        // Проверяем разрешение и битрейт
        assert!(args.iter().any(|a| a.contains("scale=1280x720")));
        assert!(args.contains(&"5000k".to_string()));
        // Аудио битрейт выше
        assert!(args.contains(&"128k".to_string()));
    }

    #[test]
    fn test_quality_1080p_profile() {
        let profile = TranscodeProfile::quality_1080p("https://example.com/video.mp4");
        let args = profile.build_ffmpeg_args();

        // Проверяем разрешение и битрейт
        assert!(args.iter().any(|a| a.contains("scale=1920x1080")));
        assert!(args.contains(&"8000k".to_string()));
    }

    #[test]
    fn test_video_profile_has_fast_preset() {
        let profile = TranscodeProfile::quality_720p("https://example.com/video.mp4");
        let args = profile.build_ffmpeg_args();

        // H.264 должен иметь preset fast для быстрого кодирования
        assert!(args.contains(&"-preset".to_string()));
        assert!(args.contains(&"fast".to_string()));
    }

    #[test]
    fn test_video_profile_mp4_faststart() {
        let profile = TranscodeProfile::quality_720p("https://example.com/video.mp4");
        let args = profile.build_ffmpeg_args();

        // MP4 должен иметь movflags faststart для стриминга
        assert!(args.contains(&"-movflags".to_string()));
        assert!(args.contains(&"faststart".to_string()));
    }
}
