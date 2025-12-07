//! Unit тесты для FFmpeg command builder
//!
//! Проверяет корректность генерации FFmpeg аргументов.

use rust_transcoder::transcoder::{TranscodeProfile, FfmpegProcess};
use rust_transcoder::models::{AudioFormat, AudioCodec, AudioQuality};

/// Тест: Профиль Opus генерирует корректные аргументы
#[test]
fn test_opus_profile_args() {
    let profile = TranscodeProfile {
        source_url: "https://example.com/test.mp3".to_string(),
        format: AudioFormat::Opus,
        codec: AudioCodec::Libopus,
        bitrate: 64,
        sample_rate: 48000,
        channels: 2,
        normalize: false,
        target_loudness: -16.0,
        fade_in: None,
        fade_out: None,
    };

    let args = profile.build_ffmpeg_args();

    // Проверяем обязательные аргументы
    assert!(args.contains(&"-i".to_string()));
    assert!(args.contains(&"https://example.com/test.mp3".to_string()));
    assert!(args.contains(&"-c:a".to_string()));
    assert!(args.contains(&"libopus".to_string()));
    assert!(args.contains(&"-b:a".to_string()));
    assert!(args.contains(&"64k".to_string()));
    assert!(args.contains(&"-ar".to_string()));
    assert!(args.contains(&"48000".to_string()));
    assert!(args.contains(&"-f".to_string()));
    assert!(args.contains(&"ogg".to_string()));
    assert!(args.contains(&"pipe:1".to_string()));
}

/// Тест: Профиль MP3 генерирует корректные аргументы
#[test]
fn test_mp3_profile_args() {
    let profile = TranscodeProfile {
        source_url: "test.wav".to_string(),
        format: AudioFormat::Mp3,
        codec: AudioCodec::Libmp3lame,
        bitrate: 192,
        sample_rate: 44100,
        channels: 2,
        normalize: false,
        target_loudness: -16.0,
        fade_in: None,
        fade_out: None,
    };

    let args = profile.build_ffmpeg_args();

    assert!(args.contains(&"libmp3lame".to_string()));
    assert!(args.contains(&"192k".to_string()));
    assert!(args.contains(&"44100".to_string()));
    assert!(args.contains(&"mp3".to_string()));
}

/// Тест: Профиль AAC генерирует корректные аргументы
#[test]
fn test_aac_profile_args() {
    let profile = TranscodeProfile {
        source_url: "test.flac".to_string(),
        format: AudioFormat::Aac,
        codec: AudioCodec::Aac,
        bitrate: 128,
        sample_rate: 48000,
        channels: 2,
        normalize: false,
        target_loudness: -16.0,
        fade_in: None,
        fade_out: None,
    };

    let args = profile.build_ffmpeg_args();

    assert!(args.contains(&"aac".to_string()), "Should use AAC codec");
    assert!(args.contains(&"adts".to_string()), "Should use ADTS format");
}

/// Тест: Нормализация добавляет loudnorm фильтр
#[test]
fn test_normalize_adds_loudnorm_filter() {
    let profile = TranscodeProfile {
        source_url: "test.mp3".to_string(),
        format: AudioFormat::Opus,
        codec: AudioCodec::Libopus,
        bitrate: 64,
        sample_rate: 48000,
        channels: 2,
        normalize: true,
        target_loudness: -16.0,
        fade_in: None,
        fade_out: None,
    };

    let args = profile.build_ffmpeg_args();

    // Должен быть -af с loudnorm
    let af_idx = args.iter().position(|a| a == "-af");
    assert!(af_idx.is_some(), "Should have -af flag");
    
    let filter_arg = &args[af_idx.unwrap() + 1];
    assert!(filter_arg.contains("loudnorm"), "Should contain loudnorm filter");
    assert!(filter_arg.contains("-16"), "Should contain target loudness");
}

/// Тест: Fade in добавляет afade фильтр
#[test]
fn test_fade_in_adds_afade_filter() {
    let profile = TranscodeProfile {
        source_url: "test.mp3".to_string(),
        format: AudioFormat::Opus,
        codec: AudioCodec::Libopus,
        bitrate: 64,
        sample_rate: 48000,
        channels: 2,
        normalize: false,
        target_loudness: -16.0,
        fade_in: Some(2.5),
        fade_out: None,
    };

    let args = profile.build_ffmpeg_args();

    let af_idx = args.iter().position(|a| a == "-af");
    assert!(af_idx.is_some(), "Should have -af flag");
    
    let filter_arg = &args[af_idx.unwrap() + 1];
    assert!(filter_arg.contains("afade=t=in"), "Should contain fade in filter");
    assert!(filter_arg.contains("d=2.5"), "Should contain fade duration");
}

/// Тест: Комбинация фильтров
#[test]
fn test_combined_filters() {
    let profile = TranscodeProfile {
        source_url: "test.mp3".to_string(),
        format: AudioFormat::Opus,
        codec: AudioCodec::Libopus,
        bitrate: 64,
        sample_rate: 48000,
        channels: 2,
        normalize: true,
        target_loudness: -14.0,
        fade_in: Some(1.0),
        fade_out: None,
    };

    let args = profile.build_ffmpeg_args();

    let af_idx = args.iter().position(|a| a == "-af");
    assert!(af_idx.is_some());
    
    let filter_arg = &args[af_idx.unwrap() + 1];
    assert!(filter_arg.contains("afade"), "Should contain afade");
    assert!(filter_arg.contains("loudnorm"), "Should contain loudnorm");
    assert!(filter_arg.contains(","), "Filters should be comma-separated");
}

/// Тест: Предустановленный профиль telegram_voice
#[test]
fn test_telegram_voice_preset() {
    let profile = TranscodeProfile::telegram_voice("https://youtube.com/watch?v=123");

    assert_eq!(profile.format, AudioFormat::Opus);
    assert_eq!(profile.codec, AudioCodec::Libopus);
    assert_eq!(profile.bitrate, 64);
    assert_eq!(profile.sample_rate, 48000);
    assert!(profile.normalize, "Telegram voice should have normalization");
}

/// Тест: Предустановленный профиль low_latency
#[test]
fn test_low_latency_preset() {
    let profile = TranscodeProfile::low_latency("rtmp://stream.example.com/live");

    assert_eq!(profile.format, AudioFormat::Opus);
    assert_eq!(profile.bitrate, 48);
    assert!(!profile.normalize, "Low latency should skip normalization");
}

/// Тест: Предустановленный профиль high_quality
#[test]
fn test_high_quality_preset() {
    let profile = TranscodeProfile::high_quality("file:///music/song.flac");

    assert_eq!(profile.bitrate, 128);
    assert_eq!(profile.target_loudness, -14.0);
}

/// Тест: Mono output
#[test]
fn test_mono_output() {
    let profile = TranscodeProfile {
        source_url: "test.mp3".to_string(),
        format: AudioFormat::Opus,
        codec: AudioCodec::Libopus,
        bitrate: 32,
        sample_rate: 24000,
        channels: 1,
        normalize: false,
        target_loudness: -16.0,
        fade_in: None,
        fade_out: None,
    };

    let args = profile.build_ffmpeg_args();

    assert!(args.contains(&"-ac".to_string()));
    assert!(args.contains(&"1".to_string()));
}

/// Тест: Quality bitrate mapping для Opus
#[test]
fn test_quality_bitrate_opus() {
    assert_eq!(AudioQuality::Low.bitrate_for_codec(AudioCodec::Libopus), 32);
    assert_eq!(AudioQuality::Medium.bitrate_for_codec(AudioCodec::Libopus), 64);
    assert_eq!(AudioQuality::High.bitrate_for_codec(AudioCodec::Libopus), 128);
    assert_eq!(AudioQuality::Lossless.bitrate_for_codec(AudioCodec::Libopus), 256);
}

/// Тест: Quality bitrate mapping для MP3
#[test]
fn test_quality_bitrate_mp3() {
    assert_eq!(AudioQuality::Low.bitrate_for_codec(AudioCodec::Libmp3lame), 64);
    assert_eq!(AudioQuality::Medium.bitrate_for_codec(AudioCodec::Libmp3lame), 128);
    assert_eq!(AudioQuality::High.bitrate_for_codec(AudioCodec::Libmp3lame), 192);
    assert_eq!(AudioQuality::Lossless.bitrate_for_codec(AudioCodec::Libmp3lame), 320);
}

/// Тест: Глобальные FFmpeg флаги
#[test]
fn test_global_ffmpeg_flags() {
    let profile = TranscodeProfile::telegram_voice("test.mp3");
    let args = profile.build_ffmpeg_args();

    assert!(args.contains(&"-hide_banner".to_string()), "Should hide banner");
    assert!(args.contains(&"-y".to_string()), "Should overwrite output");
}
