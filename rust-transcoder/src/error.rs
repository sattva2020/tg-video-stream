//! Модуль обработки ошибок
//!
//! Централизованная обработка ошибок с преобразованием в HTTP responses.

use std::io;

use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde::Serialize;
use thiserror::Error;
use tracing::error;

/// Основной тип ошибки приложения
#[derive(Debug, Error)]
pub enum AppError {
    /// Ошибка валидации входных данных
    #[error("Validation error: {0}")]
    Validation(String),

    /// Неподдерживаемый формат или кодек
    #[error("Unsupported format: {0}")]
    UnsupportedFormat(String),

    /// Ошибка FFmpeg процесса
    #[error("FFmpeg error: {0}")]
    Ffmpeg(String),

    /// Ошибка ввода-вывода
    #[error("IO error: {0}")]
    Io(#[from] io::Error),

    /// Источник недоступен
    #[error("Source unavailable: {0}")]
    SourceUnavailable(String),

    /// Превышен лимит concurrent streams
    #[error("Concurrency limit exceeded: max {0} streams allowed")]
    ConcurrencyLimitExceeded(usize),

    /// Таймаут операции
    #[error("Operation timeout: {0}")]
    Timeout(String),

    /// Невалидный фильтр
    #[error("Invalid filter: {0}")]
    FilterInvalid(String),

    /// Внутренняя ошибка сервера
    #[error("Internal server error: {0}")]
    Internal(String),
}

/// Структура ответа об ошибке
#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    /// Код ошибки (machine-readable)
    pub code: String,
    /// Сообщение об ошибке (human-readable)
    pub message: String,
    /// Дополнительные детали (опционально)
    #[serde(skip_serializing_if = "Option::is_none")]
    pub details: Option<String>,
}

impl ErrorResponse {
    pub fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
            details: None,
        }
    }

    pub fn with_details(mut self, details: impl Into<String>) -> Self {
        self.details = Some(details.into());
        self
    }
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, error_response) = match &self {
            AppError::Validation(msg) => (
                StatusCode::BAD_REQUEST,
                ErrorResponse::new("VALIDATION_ERROR", msg),
            ),

            AppError::UnsupportedFormat(msg) => (
                StatusCode::BAD_REQUEST,
                ErrorResponse::new("UNSUPPORTED_FORMAT", msg),
            ),

            AppError::Ffmpeg(msg) => {
                error!(error = %msg, "FFmpeg process error");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    ErrorResponse::new("FFMPEG_ERROR", "Transcoding failed"),
                )
            }

            AppError::Io(err) => {
                error!(error = %err, "IO error");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    ErrorResponse::new("IO_ERROR", "IO operation failed"),
                )
            }

            AppError::SourceUnavailable(msg) => (
                StatusCode::BAD_REQUEST,
                ErrorResponse::new("SOURCE_UNAVAILABLE", msg),
            ),

            AppError::ConcurrencyLimitExceeded(limit) => (
                StatusCode::SERVICE_UNAVAILABLE,
                ErrorResponse::new(
                    "CONCURRENCY_LIMIT_EXCEEDED",
                    format!("Server is at capacity. Maximum {} concurrent streams allowed.", limit),
                ),
            ),

            AppError::Timeout(msg) => (
                StatusCode::GATEWAY_TIMEOUT,
                ErrorResponse::new("TIMEOUT", msg),
            ),

            AppError::FilterInvalid(msg) => (
                StatusCode::BAD_REQUEST,
                ErrorResponse::new("FILTER_INVALID", msg),
            ),

            AppError::Internal(msg) => {
                error!(error = %msg, "Internal server error");
                (
                    StatusCode::INTERNAL_SERVER_ERROR,
                    ErrorResponse::new("INTERNAL_ERROR", "Internal server error"),
                )
            }
        };

        (status, Json(error_response)).into_response()
    }
}

/// Result type alias для AppError
pub type AppResult<T> = Result<T, AppError>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_error_response_creation() {
        let resp = ErrorResponse::new("TEST_ERROR", "Test message");
        assert_eq!(resp.code, "TEST_ERROR");
        assert_eq!(resp.message, "Test message");
        assert!(resp.details.is_none());
    }

    #[test]
    fn test_error_response_with_details() {
        let resp = ErrorResponse::new("TEST_ERROR", "Test message")
            .with_details("Additional info");
        assert_eq!(resp.details, Some("Additional info".to_string()));
    }

    #[test]
    fn test_validation_error() {
        let err = AppError::Validation("Invalid codec".to_string());
        assert!(err.to_string().contains("Invalid codec"));
    }

    #[test]
    fn test_concurrency_error() {
        let err = AppError::ConcurrencyLimitExceeded(50);
        assert!(err.to_string().contains("50"));
    }
}
