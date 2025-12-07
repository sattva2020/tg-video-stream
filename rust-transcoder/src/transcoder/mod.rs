//! Transcoder модуль - логика транскодирования через FFmpeg
//!
//! Содержит FFmpeg wrapper и профили транскодирования.

pub mod ffmpeg;
pub mod filters;
pub mod profiles;

// Re-export основных типов
pub use ffmpeg::FfmpegProcess;
pub use profiles::TranscodeProfile;
