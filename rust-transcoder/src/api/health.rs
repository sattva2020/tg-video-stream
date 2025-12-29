//! Health check endpoints
//!
//! Предоставляет /health, /health/ready и /health/live эндпоинты.

use axum::{extract::State, http::StatusCode, response::IntoResponse, Json};
use serde::Serialize;
use std::process::Command;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::AppState;

/// Расширенный ответ health check
#[derive(Debug, Serialize)]
pub struct HealthResponse {
    pub status: &'static str,
    pub service: &'static str,
    pub version: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub uptime_seconds: Option<u64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ffmpeg_version: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub active_streams: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_concurrent_streams: Option<usize>,
}

lazy_static::lazy_static! {
    static ref START_TIME: SystemTime = SystemTime::now();
}

/// Получить версию FFmpeg
fn get_ffmpeg_version() -> Option<String> {
    Command::new("ffmpeg")
        .arg("-version")
        .output()
        .ok()
        .and_then(|output| {
            if output.status.success() {
                String::from_utf8(output.stdout)
                    .ok()
                    .and_then(|s| s.lines().next().map(|line| line.to_string()))
            } else {
                None
            }
        })
}

/// GET /health - базовая проверка здоровья с расширенной информацией
pub async fn health_check(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let uptime = START_TIME
        .elapsed()
        .ok()
        .map(|d| d.as_secs());

    let ffmpeg_version = get_ffmpeg_version();
    
    let active_streams = state.transcode_semaphore.available_permits();
    let max_streams = state.max_concurrent_streams;
    let current_active = max_streams.saturating_sub(active_streams);

    Json(HealthResponse {
        status: "healthy",
        service: "rust-transcoder",
        version: env!("CARGO_PKG_VERSION"),
        uptime_seconds: uptime,
        ffmpeg_version,
        active_streams: Some(current_active),
        max_concurrent_streams: Some(max_streams),
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
