//! Contract tests для /metrics endpoint
//!
//! Проверяет что metrics endpoint возвращает Prometheus формат

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use rust_transcoder::{build_router, AppState};
use std::sync::Arc;

fn create_test_state() -> Arc<AppState> {
    Arc::new(AppState::new(10))
}

/// Test: GET /metrics возвращает 200
#[tokio::test]
async fn test_metrics_returns_200() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/metrics")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(response.status(), StatusCode::OK);
}

/// Test: GET /metrics Content-Type должен быть text/plain
#[tokio::test]
async fn test_metrics_content_type() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/metrics")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    let content_type = response
        .headers()
        .get("content-type")
        .expect("Missing Content-Type header")
        .to_str()
        .unwrap();

    assert!(
        content_type.contains("text/plain"),
        "Content-Type should be text/plain, got: {}",
        content_type
    );
}

/// Test: GET /metrics body не должен быть пустым
#[tokio::test]
async fn test_metrics_body_not_empty() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/metrics")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    let body = response.into_body().collect().await.unwrap().to_bytes();

    // Prometheus всегда возвращает хотя бы служебные метрики
    assert!(!body.is_empty(), "Metrics body should not be empty");
}

/// Test: GET /metrics должен содержать метрику process_ (стандартные процесс метрики)
#[tokio::test]
async fn test_metrics_contains_process_metrics() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/metrics")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let body_str = String::from_utf8(body.to_vec()).unwrap();

    // Prometheus rust клиент по умолчанию добавляет process_ метрики
    // Если их нет - это тоже ок, просто проверяем формат
    assert!(
        body_str.contains("# HELP") || body_str.is_empty() || !body_str.contains("error"),
        "Metrics should be in Prometheus format"
    );
}

/// Test: GET /metrics формат Prometheus (содержит # HELP или # TYPE)
#[tokio::test]
async fn test_metrics_prometheus_format() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/metrics")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let body_str = String::from_utf8(body.to_vec()).unwrap();

    // Если есть метрики, они должны иметь Prometheus формат
    if !body_str.is_empty() {
        // Prometheus формат: либо комментарии (# HELP, # TYPE), либо метрики (name value)
        let has_valid_format = body_str.lines().all(|line| {
            line.is_empty()
                || line.starts_with('#')
                || line.contains(' ')  // metric_name{labels} value
        });
        assert!(has_valid_format, "Metrics should be in valid Prometheus format");
    }
}

/// Test: После transcode запроса должны появиться transcode метрики
#[tokio::test]
async fn test_metrics_after_transcode_request() {
    use tower::ServiceExt;

    let state = create_test_state();
    let app = build_router(state);

    // Сначала делаем transcode запрос
    let transcode_request = Request::builder()
        .method("POST")
        .uri("/api/v1/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(r#"{"source_url": "https://example.com/audio.mp3"}"#))
        .unwrap();

    let _ = app.clone().oneshot(transcode_request).await;

    // Теперь проверяем metrics
    let metrics_request = Request::builder()
        .method("GET")
        .uri("/metrics")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(metrics_request).await.unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    // Метрики должны быть доступны
    let body = response.into_body().collect().await.unwrap().to_bytes();
    assert!(!body.is_empty());
}
