//! API модуль - HTTP эндпоинты для транскодирования
//!
//! Содержит все HTTP handlers и маршрутизацию.

use std::sync::Arc;

use axum::Router;

use crate::AppState;

pub mod health;
pub mod metrics;
pub mod transcode;

/// Создаёт Router для API v1
pub fn routes(_state: Arc<AppState>) -> Router<Arc<AppState>> {
    use axum::routing::get;

    Router::new()
        // POST /api/v1/transcode - основной эндпоинт транскодирования
        .merge(transcode::routes())
        // GET /api/v1/health - health check с расширенной информацией
        .route("/health", get(health::health_check))
        // GET /api/v1/health/ready - readiness probe
        .route("/health/ready", get(health::readiness_check))
        // GET /api/v1/health/live - liveness probe
        .route("/health/live", get(health::liveness_check))
        // GET /api/v1/metrics - Prometheus metrics
        .route("/metrics", get(metrics::metrics_handler))
}
