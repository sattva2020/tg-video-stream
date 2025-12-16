//! Metrics endpoint для Prometheus
//!
//! Предоставляет /metrics эндпоинт в формате Prometheus.

use axum::{response::IntoResponse, Extension};
use prometheus::{
    opts, register_counter, register_gauge, register_histogram_vec, Counter, Encoder, Gauge,
    HistogramVec, TextEncoder,
};
use std::sync::Arc;

use crate::AppState;

lazy_static::lazy_static! {
    /// Счётчик общего количества запросов на транскодирование
    pub static ref TRANSCODE_REQUESTS_TOTAL: Counter = register_counter!(
        opts!(
            "transcode_requests_total",
            "Total number of transcode requests"
        )
    )
    .expect("Failed to create transcode_requests_total counter");

    /// Текущее количество активных потоков транскодирования
    pub static ref ACTIVE_STREAMS: Gauge = register_gauge!(
        opts!(
            "active_streams",
            "Current number of active transcoding streams"
        )
    )
    .expect("Failed to create active_streams gauge");

    /// Гистограмма latency транскодирования в миллисекундах
    pub static ref TRANSCODE_LATENCY_MS: HistogramVec = register_histogram_vec!(
        "transcode_latency_milliseconds",
        "Transcode operation latency in milliseconds",
        &["format", "status"],
        vec![10.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0, 5000.0]
    )
    .expect("Failed to create transcode_latency_ms histogram");

    /// Счётчик ошибок транскодирования
    pub static ref TRANSCODE_ERRORS_TOTAL: Counter = register_counter!(
        opts!(
            "transcode_errors_total",
            "Total number of transcode errors"
        )
    )
    .expect("Failed to create transcode_errors_total counter");
}

/// Обновить метрику активных стримов на основе текущего состояния
fn update_active_streams_metric(state: &Arc<AppState>) {
    let available = state.transcode_semaphore.available_permits();
    let max = state.max_concurrent_streams;
    let active = max.saturating_sub(available);
    ACTIVE_STREAMS.set(active as f64);
}

/// GET /metrics - Prometheus метрики
pub async fn metrics_handler(Extension(state): Extension<Arc<AppState>>) -> impl IntoResponse {
    // Обновляем метрику активных стримов перед экспортом
    update_active_streams_metric(&state);

    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();

    encoder
        .encode(&metric_families, &mut buffer)
        .expect("Failed to encode metrics");

    (
        [(
            axum::http::header::CONTENT_TYPE,
            "text/plain; version=0.0.4; charset=utf-8",
        )],
        buffer,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_metrics_handler() {
        let response = metrics_handler().await;
        let (headers, body) = response;
        assert!(!body.is_empty());
    }
}
