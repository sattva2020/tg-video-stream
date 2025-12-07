//! Contract tests для транскодирования с фильтрами
//!
//! Тестирует применение EQ presets и speed фильтров через /transcode endpoint

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use rust_transcoder::{build_router, AppState};
use serde_json::json;
use std::sync::Arc;
use tokio::sync::Semaphore;
use tower::ServiceExt;

/// Создаёт тестовое AppState
fn create_test_state() -> Arc<AppState> {
    Arc::new(AppState {
        semaphore: Arc::new(Semaphore::new(10)),
        start_time: std::time::Instant::now(),
    })
}

/// Test: POST /transcode с eq_preset=bass_boost возвращает 200
/// 
/// Проверяет что endpoint принимает EQ preset параметр
#[tokio::test]
async fn test_transcode_with_eq_preset_bass_boost() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "eq_preset": "bass_boost"
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    // Должен вернуть 200 или 502 (если ffmpeg не может скачать URL)
    // Главное - не 400 (validation error)
    assert!(
        response.status() == StatusCode::OK || response.status() == StatusCode::BAD_GATEWAY,
        "Expected 200 or 502, got {}",
        response.status()
    );
}

/// Test: POST /transcode с eq_preset=voice возвращает 200
#[tokio::test]
async fn test_transcode_with_eq_preset_voice() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "eq_preset": "voice"
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert!(
        response.status() == StatusCode::OK || response.status() == StatusCode::BAD_GATEWAY,
        "Expected 200 or 502, got {}",
        response.status()
    );
}

/// Test: POST /transcode с speed=1.25 возвращает 200
#[tokio::test]
async fn test_transcode_with_speed_filter() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "speed": 1.25
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert!(
        response.status() == StatusCode::OK || response.status() == StatusCode::BAD_GATEWAY,
        "Expected 200 or 502, got {}",
        response.status()
    );
}

/// Test: POST /transcode с speed < 0.5 возвращает 400 (validation error)
#[tokio::test]
async fn test_transcode_with_invalid_speed_too_low() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "speed": 0.3  // Слишком низкое значение
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(
        response.status(),
        StatusCode::BAD_REQUEST,
        "Speed < 0.5 should return 400"
    );
}

/// Test: POST /transcode с speed > 2.0 возвращает 400 (validation error)
#[tokio::test]
async fn test_transcode_with_invalid_speed_too_high() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "speed": 2.5  // Слишком высокое значение
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(
        response.status(),
        StatusCode::BAD_REQUEST,
        "Speed > 2.0 should return 400"
    );
}

/// Test: POST /transcode с volume=1.5 возвращает 200
#[tokio::test]
async fn test_transcode_with_volume_filter() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "volume": 1.5
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert!(
        response.status() == StatusCode::OK || response.status() == StatusCode::BAD_GATEWAY,
        "Expected 200 or 502, got {}",
        response.status()
    );
}

/// Test: POST /transcode с volume < 0.0 возвращает 400
#[tokio::test]
async fn test_transcode_with_invalid_volume_negative() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "volume": -0.5  // Отрицательное значение
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(
        response.status(),
        StatusCode::BAD_REQUEST,
        "Volume < 0.0 should return 400"
    );
}

/// Test: POST /transcode с volume > 2.0 возвращает 400
#[tokio::test]
async fn test_transcode_with_invalid_volume_too_high() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "volume": 2.5  // Слишком высокое значение
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(
        response.status(),
        StatusCode::BAD_REQUEST,
        "Volume > 2.0 should return 400"
    );
}

/// Test: POST /transcode с invalid eq_preset возвращает 400
#[tokio::test]
async fn test_transcode_with_invalid_eq_preset() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "eq_preset": "invalid_preset"
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert_eq!(
        response.status(),
        StatusCode::BAD_REQUEST,
        "Invalid eq_preset should return 400"
    );
}

/// Test: POST /transcode с комбинацией фильтров (eq_preset + speed + volume)
#[tokio::test]
async fn test_transcode_with_combined_filters() {
    let state = create_test_state();
    let app = build_router(state);

    let body = json!({
        "source_url": "https://example.com/audio.mp3",
        "output_format": "opus",
        "audio_filters": {
            "eq_preset": "flat",
            "speed": 1.1,
            "volume": 0.8
        }
    });

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("Content-Type", "application/json")
        .body(Body::from(serde_json::to_string(&body).unwrap()))
        .unwrap();

    let response = app.oneshot(request).await.unwrap();

    assert!(
        response.status() == StatusCode::OK || response.status() == StatusCode::BAD_GATEWAY,
        "Expected 200 or 502, got {}",
        response.status()
    );
}
