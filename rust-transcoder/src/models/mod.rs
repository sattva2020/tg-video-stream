//! Models модуль - структуры данных для API
//!
//! Содержит все модели запросов/ответов и перечисления.

pub mod enums;
pub mod transcode;
pub mod url_validation;

// Re-export основных типов для удобства
pub use enums::{AudioCodec, AudioFormat, AudioQuality, EqPreset, TranscodeStatus};
pub use transcode::{AudioFilters, TranscodeRequest, TranscodeResponse, TranscodeStatusResponse};
pub use url_validation::{validate_source_url, UrlValidationError};
