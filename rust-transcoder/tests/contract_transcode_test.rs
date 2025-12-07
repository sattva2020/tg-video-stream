//! Contract тесты для POST /transcode endpoint
//!
//! Проверяет соответствие API контракту OpenAPI.

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use serde_json::{json, Value};
use tower::ServiceExt;

mod common;

/// Тест: Успешный запрос на транскодирование возвращает 200 OK
#[tokio::test]
async fn test_transcode_valid_request_returns_200() {
    let app = common::create_test_app();

    let request = Request::builder()
        .method("POST")
        .uri("/api/v1/transcode")
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "source_url": "https://example.com/audio.mp3",
            "format": "opus",
            "quality": "medium"
        }).to_string()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(response.status(), StatusCode::OK);
}

/// Тест: Response содержит обязательные поля (session_id, status, content_type)
#[tokio::test]
async fn test_transcode_response_has_required_fields() {
    let app = common::create_test_app();

    let request = Request::builder()
        .method("POST")
        .uri("/api/v1/transcode")
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "source_url": "https://example.com/audio.mp3"
        }).to_string()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(response.status(), StatusCode::OK);

    let body = axum::body::to_bytes(response.into_body(), 10240).await.unwrap();
    let json: Value = serde_json::from_slice(&body).unwrap();

    assert!(json.get("session_id").is_some(), "Response must contain session_id");
    assert!(json.get("status").is_some(), "Response must contain status");
    assert!(json.get("content_type").is_some(), "Response must contain content_type");
}

/// Тест: Пустой source_url возвращает 400 Bad Request
#[tokio::test]
async fn test_transcode_empty_source_url_returns_400() {
    let app = common::create_test_app();

    let request = Request::builder()
        .method("POST")
        .uri("/api/v1/transcode")
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "source_url": ""
        }).to_string()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

/// Тест: Невалидный bitrate возвращает 400 Bad Request
#[tokio::test]
async fn test_transcode_invalid_bitrate_returns_400() {
    let app = common::create_test_app();

    let request = Request::builder()
        .method("POST")
        .uri("/api/v1/transcode")
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "source_url": "https://example.com/audio.mp3",
            "bitrate": 1000  // Too high, max 512
        }).to_string()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

/// Тест: Запрос с невалидным JSON возвращает 400/422
#[tokio::test]
async fn test_transcode_invalid_json_returns_error() {
    let app = common::create_test_app();

    let request = Request::builder()
        .method("POST")
        .uri("/api/v1/transcode")
        .header("content-type", "application/json")
        .body(Body::from("not valid json"))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    // Axum returns 422 for JSON parse errors
    assert!(
        response.status() == StatusCode::BAD_REQUEST 
        || response.status() == StatusCode::UNPROCESSABLE_ENTITY
    );
}

/// Тест: Ошибка содержит code и message
#[tokio::test]
async fn test_transcode_error_response_format() {
    let app = common::create_test_app();

    let request = Request::builder()
        .method("POST")
        .uri("/api/v1/transcode")
        .header("content-type", "application/json")
        .body(Body::from(json!({
            "source_url": ""
        }).to_string()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);

    let body = axum::body::to_bytes(response.into_body(), 10240).await.unwrap();
    let json: Value = serde_json::from_slice(&body).unwrap();

    assert!(json.get("code").is_some(), "Error must contain code");
    assert!(json.get("message").is_some(), "Error must contain message");
}

/// Тест: Разные форматы (opus, mp3, aac)
#[tokio::test]
async fn test_transcode_supports_multiple_formats() {
    let formats = vec!["opus", "mp3", "aac"];

    for format in formats {
        let app = common::create_test_app();

        let request = Request::builder()
            .method("POST")
            .uri("/api/v1/transcode")
            .header("content-type", "application/json")
            .body(Body::from(json!({
                "source_url": "https://example.com/audio.mp3",
                "format": format
            }).to_string()))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        assert_eq!(
            response.status(), 
            StatusCode::OK,
            "Format '{}' should be supported", 
            format
        );
    }
}

/// Тест: Качество (low, medium, high, lossless)
#[tokio::test]
async fn test_transcode_supports_quality_levels() {
    let qualities = vec!["low", "medium", "high", "lossless"];

    for quality in qualities {
        let app = common::create_test_app();

        let request = Request::builder()
            .method("POST")
            .uri("/api/v1/transcode")
            .header("content-type", "application/json")
            .body(Body::from(json!({
                "source_url": "https://example.com/audio.mp3",
                "quality": quality
            }).to_string()))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        assert_eq!(
            response.status(), 
            StatusCode::OK,
            "Quality '{}' should be supported", 
            quality
        );
    }
}
