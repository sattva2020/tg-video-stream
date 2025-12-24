//! Unit tests для enums модуля
//!
//! Тестирует все enum типы: AudioFormat, AudioCodec, AudioQuality, EqPreset, TranscodeStatus

use rust_transcoder::models::{AudioCodec, AudioFormat, AudioQuality, EqPreset, TranscodeStatus};

// ============================================================================
// AudioFormat Tests
// ============================================================================

#[test]
fn test_audio_format_content_type() {
    assert_eq!(AudioFormat::Opus.content_type(), "audio/ogg");
    assert_eq!(AudioFormat::Mp3.content_type(), "audio/mpeg");
    assert_eq!(AudioFormat::Aac.content_type(), "audio/aac");
    assert_eq!(AudioFormat::Pcm.content_type(), "audio/pcm");
    assert_eq!(AudioFormat::Wav.content_type(), "audio/wav");
    assert_eq!(AudioFormat::Flac.content_type(), "audio/flac");
}

#[test]
fn test_audio_format_ffmpeg_format() {
    assert_eq!(AudioFormat::Opus.ffmpeg_format(), "ogg");
    assert_eq!(AudioFormat::Mp3.ffmpeg_format(), "mp3");
    assert_eq!(AudioFormat::Aac.ffmpeg_format(), "adts");
    assert_eq!(AudioFormat::Pcm.ffmpeg_format(), "s16le");
    assert_eq!(AudioFormat::Wav.ffmpeg_format(), "wav");
    assert_eq!(AudioFormat::Flac.ffmpeg_format(), "flac");
}

#[test]
fn test_audio_format_extension() {
    assert_eq!(AudioFormat::Opus.extension(), "ogg");
    assert_eq!(AudioFormat::Mp3.extension(), "mp3");
    assert_eq!(AudioFormat::Aac.extension(), "aac");
    assert_eq!(AudioFormat::Pcm.extension(), "pcm");
    assert_eq!(AudioFormat::Wav.extension(), "wav");
    assert_eq!(AudioFormat::Flac.extension(), "flac");
}

#[test]
fn test_audio_format_display() {
    assert_eq!(AudioFormat::Opus.to_string(), "opus");
    assert_eq!(AudioFormat::Mp3.to_string(), "mp3");
    assert_eq!(AudioFormat::Aac.to_string(), "aac");
    assert_eq!(AudioFormat::Pcm.to_string(), "pcm");
    assert_eq!(AudioFormat::Wav.to_string(), "wav");
    assert_eq!(AudioFormat::Flac.to_string(), "flac");
}

#[test]
fn test_audio_format_default() {
    let default_format: AudioFormat = Default::default();
    assert_eq!(default_format, AudioFormat::Opus);
}

#[test]
fn test_audio_format_serialization() {
    let json = serde_json::to_string(&AudioFormat::Opus).unwrap();
    assert_eq!(json, r#""opus""#);

    let json = serde_json::to_string(&AudioFormat::Mp3).unwrap();
    assert_eq!(json, r#""mp3""#);
}

#[test]
fn test_audio_format_deserialization() {
    let format: AudioFormat = serde_json::from_str(r#""opus""#).unwrap();
    assert_eq!(format, AudioFormat::Opus);

    let format: AudioFormat = serde_json::from_str(r#""mp3""#).unwrap();
    assert_eq!(format, AudioFormat::Mp3);
}

// ============================================================================
// AudioCodec Tests
// ============================================================================

#[test]
fn test_audio_codec_ffmpeg_codec() {
    assert_eq!(AudioCodec::Libopus.ffmpeg_codec(), "libopus");
    assert_eq!(AudioCodec::Libmp3lame.ffmpeg_codec(), "libmp3lame");
    assert_eq!(AudioCodec::Aac.ffmpeg_codec(), "aac");
    assert_eq!(AudioCodec::PcmS16le.ffmpeg_codec(), "pcm_s16le");
    assert_eq!(AudioCodec::Flac.ffmpeg_codec(), "flac");
}

#[test]
fn test_audio_codec_compatibility() {
    // Opus + Opus format = compatible
    assert!(AudioCodec::Libopus.is_compatible_with(AudioFormat::Opus));
    
    // Opus + MP3 format = incompatible
    assert!(!AudioCodec::Libopus.is_compatible_with(AudioFormat::Mp3));
    
    // MP3 codec + MP3 format = compatible
    assert!(AudioCodec::Libmp3lame.is_compatible_with(AudioFormat::Mp3));
    
    // AAC codec + AAC format = compatible
    assert!(AudioCodec::Aac.is_compatible_with(AudioFormat::Aac));
    
    // PCM codec + PCM format = compatible
    assert!(AudioCodec::PcmS16le.is_compatible_with(AudioFormat::Pcm));
    
    // PCM codec + WAV format = compatible (PCM can go into WAV)
    assert!(AudioCodec::PcmS16le.is_compatible_with(AudioFormat::Wav));
    
    // FLAC codec + FLAC format = compatible
    assert!(AudioCodec::Flac.is_compatible_with(AudioFormat::Flac));
}

#[test]
fn test_audio_codec_display() {
    assert_eq!(AudioCodec::Libopus.to_string(), "libopus");
    assert_eq!(AudioCodec::Libmp3lame.to_string(), "libmp3lame");
    assert_eq!(AudioCodec::Aac.to_string(), "aac");
    assert_eq!(AudioCodec::PcmS16le.to_string(), "pcm_s16le");
    assert_eq!(AudioCodec::Flac.to_string(), "flac");
}

#[test]
fn test_audio_codec_default() {
    let default_codec: AudioCodec = Default::default();
    assert_eq!(default_codec, AudioCodec::Libopus);
}

// ============================================================================
// AudioQuality Tests
// ============================================================================

#[test]
fn test_audio_quality_bitrate_opus() {
    assert_eq!(AudioQuality::Low.bitrate_for_codec(AudioCodec::Libopus), 32);
    assert_eq!(AudioQuality::Medium.bitrate_for_codec(AudioCodec::Libopus), 64);
    assert_eq!(AudioQuality::High.bitrate_for_codec(AudioCodec::Libopus), 128);
    assert_eq!(AudioQuality::Lossless.bitrate_for_codec(AudioCodec::Libopus), 256);
}

#[test]
fn test_audio_quality_bitrate_mp3() {
    assert_eq!(AudioQuality::Low.bitrate_for_codec(AudioCodec::Libmp3lame), 96);
    assert_eq!(AudioQuality::Medium.bitrate_for_codec(AudioCodec::Libmp3lame), 128);
    assert_eq!(AudioQuality::High.bitrate_for_codec(AudioCodec::Libmp3lame), 192);
    assert_eq!(AudioQuality::Lossless.bitrate_for_codec(AudioCodec::Libmp3lame), 320);
}

#[test]
fn test_audio_quality_bitrate_aac() {
    assert_eq!(AudioQuality::Low.bitrate_for_codec(AudioCodec::Aac), 64);
    assert_eq!(AudioQuality::Medium.bitrate_for_codec(AudioCodec::Aac), 128);
    assert_eq!(AudioQuality::High.bitrate_for_codec(AudioCodec::Aac), 192);
    assert_eq!(AudioQuality::Lossless.bitrate_for_codec(AudioCodec::Aac), 256);
}

#[test]
fn test_audio_quality_sample_rate() {
    assert_eq!(AudioQuality::Low.sample_rate(), 24000);
    assert_eq!(AudioQuality::Medium.sample_rate(), 48000);
    assert_eq!(AudioQuality::High.sample_rate(), 48000);
    assert_eq!(AudioQuality::Lossless.sample_rate(), 48000);
}

#[test]
fn test_audio_quality_default() {
    let default_quality: AudioQuality = Default::default();
    assert_eq!(default_quality, AudioQuality::Medium);
}

#[test]
fn test_audio_quality_display() {
    assert_eq!(AudioQuality::Low.to_string(), "low");
    assert_eq!(AudioQuality::Medium.to_string(), "medium");
    assert_eq!(AudioQuality::High.to_string(), "high");
    assert_eq!(AudioQuality::Lossless.to_string(), "lossless");
}

// ============================================================================
// EqPreset Tests
// ============================================================================

#[test]
fn test_eq_preset_ffmpeg_filter() {
    let flat = EqPreset::Flat.to_ffmpeg_filter();
    assert!(flat.is_empty()); // Flat = no filter

    let bass = EqPreset::BassBoost.to_ffmpeg_filter();
    assert!(bass.contains("equalizer"));
    assert!(bass.contains("60")); // Bass frequency

    let voice = EqPreset::Voice.to_ffmpeg_filter();
    assert!(voice.contains("equalizer"));
    assert!(voice.contains("3000")); // Voice frequency

    let treble = EqPreset::Treble.to_ffmpeg_filter();
    assert!(treble.contains("equalizer"));
    assert!(treble.contains("10000")); // Treble frequency
}

#[test]
fn test_eq_preset_default() {
    let default_preset: EqPreset = Default::default();
    assert_eq!(default_preset, EqPreset::Flat);
}

#[test]
fn test_eq_preset_display() {
    assert_eq!(EqPreset::Flat.to_string(), "flat");
    assert_eq!(EqPreset::BassBoost.to_string(), "bass_boost");
    assert_eq!(EqPreset::Voice.to_string(), "voice");
    assert_eq!(EqPreset::Treble.to_string(), "treble");
}

#[test]
fn test_eq_preset_serialization() {
    let json = serde_json::to_string(&EqPreset::BassBoost).unwrap();
    assert_eq!(json, r#""bass_boost""#);

    let json = serde_json::to_string(&EqPreset::Voice).unwrap();
    assert_eq!(json, r#""voice""#);
}

#[test]
fn test_eq_preset_deserialization() {
    let preset: EqPreset = serde_json::from_str(r#""bass_boost""#).unwrap();
    assert_eq!(preset, EqPreset::BassBoost);

    let preset: EqPreset = serde_json::from_str(r#""voice""#).unwrap();
    assert_eq!(preset, EqPreset::Voice);
}

// ============================================================================
// TranscodeStatus Tests
// ============================================================================

#[test]
fn test_transcode_status_variants() {
    // Проверяем что все варианты можно создать
    let pending = TranscodeStatus::Pending;
    let processing = TranscodeStatus::Processing;
    let completed = TranscodeStatus::Completed;
    let failed = TranscodeStatus::Failed;

    assert_eq!(pending, TranscodeStatus::Pending);
    assert_eq!(processing, TranscodeStatus::Processing);
    assert_eq!(completed, TranscodeStatus::Completed);
    assert_eq!(failed, TranscodeStatus::Failed);
}

#[test]
fn test_transcode_status_display() {
    assert_eq!(TranscodeStatus::Pending.to_string(), "pending");
    assert_eq!(TranscodeStatus::Processing.to_string(), "processing");
    assert_eq!(TranscodeStatus::Completed.to_string(), "completed");
    assert_eq!(TranscodeStatus::Failed.to_string(), "failed");
}

#[test]
fn test_transcode_status_serialization() {
    let json = serde_json::to_string(&TranscodeStatus::Processing).unwrap();
    assert_eq!(json, r#""processing""#);

    let json = serde_json::to_string(&TranscodeStatus::Completed).unwrap();
    assert_eq!(json, r#""completed""#);
}

#[test]
fn test_transcode_status_deserialization() {
    let status: TranscodeStatus = serde_json::from_str(r#""pending""#).unwrap();
    assert_eq!(status, TranscodeStatus::Pending);

    let status: TranscodeStatus = serde_json::from_str(r#""failed""#).unwrap();
    assert_eq!(status, TranscodeStatus::Failed);
}

// ============================================================================
// Integration Tests
// ============================================================================

#[test]
fn test_codec_format_compatibility_matrix() {
    // Полная матрица совместимости
    let test_cases = [
        (AudioCodec::Libopus, AudioFormat::Opus, true),
        (AudioCodec::Libopus, AudioFormat::Mp3, false),
        (AudioCodec::Libmp3lame, AudioFormat::Mp3, true),
        (AudioCodec::Libmp3lame, AudioFormat::Opus, false),
        (AudioCodec::Aac, AudioFormat::Aac, true),
        (AudioCodec::Aac, AudioFormat::Mp3, false),
        (AudioCodec::PcmS16le, AudioFormat::Pcm, true),
        (AudioCodec::PcmS16le, AudioFormat::Wav, true),
        (AudioCodec::PcmS16le, AudioFormat::Opus, false),
        (AudioCodec::Flac, AudioFormat::Flac, true),
        (AudioCodec::Flac, AudioFormat::Wav, false),
    ];

    for (codec, format, expected) in test_cases {
        assert_eq!(
            codec.is_compatible_with(format),
            expected,
            "Compatibility check failed for {:?} + {:?}",
            codec,
            format
        );
    }
}

#[test]
fn test_quality_bitrate_matrix() {
    // Все комбинации качества и кодека
    let qualities = [
        AudioQuality::Low,
        AudioQuality::Medium,
        AudioQuality::High,
        AudioQuality::Lossless,
    ];
    let codecs = [
        AudioCodec::Libopus,
        AudioCodec::Libmp3lame,
        AudioCodec::Aac,
    ];

    for quality in &qualities {
        for codec in &codecs {
            let bitrate = quality.bitrate_for_codec(*codec);
            // Битрейт должен быть разумным
            assert!(bitrate >= 32 && bitrate <= 320, 
                "Unreasonable bitrate {} for {:?} + {:?}", 
                bitrate, quality, codec);
        }
    }
}

#[test]
fn test_all_formats_have_valid_content_types() {
    let formats = [
        AudioFormat::Opus,
        AudioFormat::Mp3,
        AudioFormat::Aac,
        AudioFormat::Pcm,
        AudioFormat::Wav,
        AudioFormat::Flac,
    ];

    for format in &formats {
        let content_type = format.content_type();
        assert!(content_type.starts_with("audio/"), 
            "Invalid content type for {:?}: {}", format, content_type);
    }
}
