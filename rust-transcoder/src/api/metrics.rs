//! Metrics endpoint для Prometheus
//!
//! Предоставляет /metrics эндпоинт в формате Prometheus.

use axum::response::IntoResponse;
use prometheus::{Encoder, TextEncoder};

/// GET /metrics - Prometheus метрики
pub async fn metrics_handler() -> impl IntoResponse {
    let encoder = TextEncoder::new();
    let metric_families = prometheus::gather();
    let mut buffer = Vec::new();

    encoder
        .encode(&metric_families, &mut buffer)
        .expect("Failed to encode metrics");

    (
        [(axum::http::header::CONTENT_TYPE, "text/plain; charset=utf-8")],
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
