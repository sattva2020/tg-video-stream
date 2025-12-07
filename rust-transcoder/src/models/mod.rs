//! Models модуль - структуры данных для API
//!
//! Содержит все модели запросов/ответов и перечисления.

pub mod enums;
pub mod transcode;

// Re-export основных типов для удобства
pub use enums::{AudioCodec, AudioFormat, AudioQuality, EqPreset, TranscodeStatus};
pub use transcode::{AudioFilters, TranscodeRequest, TranscodeResponse, TranscodeStatusResponse};
