//! Health check endpoints
//!
//! Предоставляет /health, /health/ready и /health/live эндпоинты.

use axum::{http::StatusCode, response::IntoResponse, Json};
use serde::Serialize;

/// Ответ health check
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub service: &'static str,
    pub version: &'static str,
}

/// GET /health - базовая проверка здоровья
pub async fn health_check() -> impl IntoResponse {
    Json(HealthResponse {
        status: "healthy",
        service: "rust-transcoder",
        version: env!("CARGO_PKG_VERSION"),
    })
}

/// GET /health/ready - проверка готовности к приёму трафика
pub async fn readiness_check() -> impl IntoResponse {
    // TODO: Проверить доступность FFmpeg
    (StatusCode::OK, "ready")
}

/// GET /health/live - проверка что процесс жив
pub async fn liveness_check() -> impl IntoResponse {
    (StatusCode::OK, "alive")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_health_check() {
        let response = health_check().await;
        // Response should be valid JSON
        let json = response.into_response();
        assert_eq!(json.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_readiness() {
        let response = readiness_check().await;
        let (status, body) = response;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body, "ready");
    }

    #[tokio::test]
    async fn test_liveness() {
        let response = liveness_check().await;
        let (status, body) = response;
        assert_eq!(status, StatusCode::OK);
        assert_eq!(body, "alive");
    }
}
