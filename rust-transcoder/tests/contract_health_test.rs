//! Contract tests для /health endpoint
//!
//! Проверяет что health endpoint возвращает правильную структуру

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use rust_transcoder::{build_router, AppState};
use serde_json::Value;
use std::sync::Arc;

fn create_test_state() -> Arc<AppState> {
    Arc::new(AppState::new(10))
}

/// Test: GET /health возвращает 200 и JSON с обязательными полями
#[tokio::test]
async fn test_health_returns_required_fields() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/health")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: Value = serde_json::from_slice(&body).unwrap();

    // Проверяем обязательные поля
    assert!(json.get("status").is_some(), "Missing 'status' field");
    assert!(json.get("service").is_some(), "Missing 'service' field");
    assert!(json.get("version").is_some(), "Missing 'version' field");
}

/// Test: GET /health status должен быть "healthy"
#[tokio::test]
async fn test_health_status_is_healthy() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/health")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: Value = serde_json::from_slice(&body).unwrap();

    assert_eq!(json["status"], "healthy");
}

/// Test: GET /health service должен быть "rust-transcoder"
#[tokio::test]
async fn test_health_service_name() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/health")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: Value = serde_json::from_slice(&body).unwrap();

    assert_eq!(json["service"], "rust-transcoder");
}

/// Test: GET /health version должен быть валидным semver
#[tokio::test]
async fn test_health_version_is_semver() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/health")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: Value = serde_json::from_slice(&body).unwrap();

    let version = json["version"].as_str().unwrap();
    // Проверяем что version содержит точки (semver формат)
    assert!(
        version.contains('.'),
        "Version '{}' should be semver format",
        version
    );
}

/// Test: GET /health/ready возвращает 200
#[tokio::test]
async fn test_health_ready_returns_200() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/health/ready")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(response.status(), StatusCode::OK);
}

/// Test: GET /health/live возвращает 200
#[tokio::test]
async fn test_health_live_returns_200() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/health/live")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(response.status(), StatusCode::OK);
}

/// Test: GET /health с uptime_seconds если реализован
#[tokio::test]
async fn test_health_uptime_is_positive() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/health")
        .body(Body::empty())
        .unwrap();

    let response = app.oneshot(request).await.unwrap();
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let json: Value = serde_json::from_slice(&body).unwrap();

    // uptime_seconds опционален, но если есть - должен быть >= 0
    if let Some(uptime) = json.get("uptime_seconds") {
        let uptime_val = uptime.as_f64().unwrap();
        assert!(uptime_val >= 0.0, "uptime_seconds should be >= 0");
    }
}
