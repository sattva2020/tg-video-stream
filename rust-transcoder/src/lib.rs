//! Rust FFmpeg Transcoder Microservice Library
//!
//! Экспортирует публичные типы для тестов и интеграций.

pub mod api;
pub mod error;
pub mod models;
pub mod transcoder;

// Re-export video filter functions для тестов
pub use transcoder::filters::{
    build_video_filter_chain,
    chain_video_filters,
    fps_filter,
    scale_filter,
    transpose_filter,
};

use std::sync::Arc;

use axum::{routing::get, Router};
use tokio::sync::Semaphore;

/// Глобальное состояние приложения
#[derive(Debug)]
pub struct AppState {
    /// Семафор для ограничения concurrent потоков транскодирования
    pub transcode_semaphore: Semaphore,
    /// Максимальное количество concurrent потоков
    pub max_concurrent_streams: usize,
}

impl AppState {
    /// Создаёт новое состояние с указанным лимитом concurrent потоков
    pub fn new(max_concurrent_streams: usize) -> Self {
        Self {
            transcode_semaphore: Semaphore::new(max_concurrent_streams),
            max_concurrent_streams,
        }
    }
}

/// Строит основной Router приложения
pub fn build_router(state: Arc<AppState>) -> Router {
    use tower_http::cors::{Any, CorsLayer};
    
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        // Health endpoints (корневые для Docker healthcheck)
        .route("/health", get(api::health::health_check))
        .route("/health/ready", get(api::health::readiness_check))
        .route("/health/live", get(api::health::liveness_check))
        // Metrics endpoint (корневой для Prometheus scrape)
        .route("/metrics", get(api::metrics::metrics_handler))
        // API v1 routes
        .nest("/api/v1", api::routes(state.clone()))
        .layer(cors)
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_app_state_creation() {
        let state = AppState::new(50);
        assert_eq!(state.max_concurrent_streams, 50);
        assert_eq!(state.transcode_semaphore.available_permits(), 50);
    }

    #[test]
    fn test_app_state_with_different_limits() {
        let state = AppState::new(10);
        assert_eq!(state.max_concurrent_streams, 10);
        assert_eq!(state.transcode_semaphore.available_permits(), 10);
    }
}
