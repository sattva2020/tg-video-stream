//! Benchmark: Latency старта транскодирования
//!
//! Проверяет требование SC-001: latency старта транскодирования должна быть < 200ms
//!
//! Запуск: cargo test --release --test benchmark_latency_test -- --nocapture

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use http_body_util::BodyExt;
use rust_transcoder::{build_router, AppState};
use std::sync::Arc;
use std::time::Instant;
use tower::ServiceExt;

/// Создаёт тестовое состояние приложения
fn create_test_state() -> Arc<AppState> {
    Arc::new(AppState::new(50))
}

/// Создаёт тестовый запрос на транскодирование
fn create_transcode_request() -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("content-type", "application/json")
        .body(Body::from(
            r#"{
                "source_url": "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3",
                "format": "opus",
                "quality": "medium"
            }"#,
        ))
        .unwrap()
}

/// Test: Latency старта транскодирования (одиночный запрос)
#[tokio::test]
async fn test_transcode_start_latency() {
    let state = create_test_state();
    let app = build_router(state);

    // Прогреваем систему (1 запрос для JIT компиляции и т.д.)
    let warmup_request = create_transcode_request();
    let _ = app.clone().oneshot(warmup_request).await;

    // Реальный тест
    let start = Instant::now();
    let request = create_transcode_request();
    let response = app.oneshot(request).await.unwrap();
    let latency = start.elapsed();

    println!("✅ Transcode start latency: {:?}", latency);
    println!("   Response status: {}", response.status());

    // SC-001: Latency должна быть < 200ms
    assert!(
        latency.as_millis() < 200,
        "Latency {} ms exceeds 200ms requirement (SC-001)",
        latency.as_millis()
    );

    // Проверяем что response корректный
    assert_eq!(response.status(), StatusCode::OK);
}

/// Test: Latency с различными форматами
#[tokio::test]
async fn test_transcode_latency_multiple_formats() {
    let state = create_test_state();

    let formats = ["opus", "pcm", "aac"];
    let mut results = Vec::new();

    for format in &formats {
        let app = build_router(state.clone());
        
        let request = Request::builder()
            .method("POST")
            .uri("/transcode")
            .header("content-type", "application/json")
            .body(Body::from(format!(
                r#"{{"source_url": "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3", "format": "{}"}}"#,
                format
            )))
            .unwrap();

        let start = Instant::now();
        let response = app.oneshot(request).await.unwrap();
        let latency = start.elapsed();

        results.push((format, latency, response.status()));
    }

    println!("\n📊 Latency по форматам:");
    for (format, latency, status) in &results {
        println!("   {} - {:?} (status: {})", format, latency, status);
        
        // Каждый формат должен быть < 200ms
        assert!(
            latency.as_millis() < 200,
            "Format {} latency {} ms exceeds 200ms",
            format,
            latency.as_millis()
        );
    }

    // Средняя latency
    let avg_latency: u128 = results.iter().map(|(_, l, _)| l.as_millis()).sum::<u128>() / results.len() as u128;
    println!("\n   Average latency: {} ms", avg_latency);
    assert!(avg_latency < 200, "Average latency exceeds 200ms");
}

/// Test: Latency с фильтрами
#[tokio::test]
async fn test_transcode_latency_with_filters() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("POST")
        .uri("/transcode")
        .header("content-type", "application/json")
        .body(Body::from(
            r#"{
                "source_url": "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3",
                "format": "opus",
                "audio_filters": {
                    "speed": 1.5,
                    "eq_preset": "bass_boost",
                    "volume": 1.2
                }
            }"#,
        ))
        .unwrap();

    let start = Instant::now();
    let response = app.oneshot(request).await.unwrap();
    let latency = start.elapsed();

    println!("\n✅ Transcode latency with filters: {:?}", latency);
    println!("   Response status: {}", response.status());

    // С фильтрами latency может быть чуть выше, но всё равно < 300ms
    assert!(
        latency.as_millis() < 300,
        "Latency with filters {} ms exceeds 300ms",
        latency.as_millis()
    );

    assert_eq!(response.status(), StatusCode::OK);
}

/// Test: Health endpoint latency (должна быть < 50ms)
#[tokio::test]
async fn test_health_endpoint_latency() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/health")
        .body(Body::empty())
        .unwrap();

    let start = Instant::now();
    let response = app.oneshot(request).await.unwrap();
    let latency = start.elapsed();

    println!("\n✅ Health endpoint latency: {:?}", latency);

    // Health endpoint должен быть очень быстрым (< 50ms)
    assert!(
        latency.as_millis() < 50,
        "Health endpoint latency {} ms exceeds 50ms",
        latency.as_millis()
    );

    assert_eq!(response.status(), StatusCode::OK);
}

/// Test: Metrics endpoint latency (должна быть < 100ms)
#[tokio::test]
async fn test_metrics_endpoint_latency() {
    let state = create_test_state();
    let app = build_router(state);

    let request = Request::builder()
        .method("GET")
        .uri("/metrics")
        .body(Body::empty())
        .unwrap();

    let start = Instant::now();
    let response = app.oneshot(request).await.unwrap();
    let latency = start.elapsed();

    println!("\n✅ Metrics endpoint latency: {:?}", latency);

    // Metrics endpoint должен быть быстрым (< 100ms)
    assert!(
        latency.as_millis() < 100,
        "Metrics endpoint latency {} ms exceeds 100ms",
        latency.as_millis()
    );

    assert_eq!(response.status(), StatusCode::OK);
}

/// Benchmark: 10 последовательных запросов
#[tokio::test]
async fn benchmark_sequential_requests() {
    let state = create_test_state();
    let mut latencies = Vec::new();

    for i in 0..10 {
        let app = build_router(state.clone());
        let request = create_transcode_request();

        let start = Instant::now();
        let response = app.oneshot(request).await.unwrap();
        let latency = start.elapsed();

        latencies.push(latency);
        assert_eq!(response.status(), StatusCode::OK);

        if i == 0 {
            println!("\n📊 Sequential requests benchmark:");
        }
        println!("   Request {}: {:?}", i + 1, latency);
    }

    // Статистика
    let min = latencies.iter().min().unwrap();
    let max = latencies.iter().max().unwrap();
    let avg: u128 = latencies.iter().map(|l| l.as_millis()).sum::<u128>() / latencies.len() as u128;

    println!("\n   Min: {:?}", min);
    println!("   Max: {:?}", max);
    println!("   Avg: {} ms", avg);

    // Средняя latency должна быть < 200ms
    assert!(avg < 200, "Average latency exceeds 200ms: {} ms", avg);
}

/// Test: Concurrent requests (проверка производительности семафора)
#[tokio::test]
async fn test_concurrent_requests_latency() {
    let state = Arc::new(AppState::new(10)); // 10 concurrent max
    let mut handles = Vec::new();

    println!("\n📊 Concurrent requests (5 parallel):");

    // Запускаем 5 параллельных запросов
    for i in 0..5 {
        let state_clone = state.clone();
        let handle = tokio::spawn(async move {
            let app = build_router(state_clone);
            let request = create_transcode_request();

            let start = Instant::now();
            let response = app.oneshot(request).await.unwrap();
            let latency = start.elapsed();

            (i, latency, response.status())
        });
        handles.push(handle);
    }

    // Ждём завершения всех
    let results = futures::future::join_all(handles).await;

    for result in results {
        let (i, latency, status) = result.unwrap();
        println!("   Request {}: {:?} (status: {})", i + 1, latency, status);

        // Каждый запрос должен быть < 500ms (с учётом конкурентности)
        assert!(
            latency.as_millis() < 500,
            "Concurrent request latency {} ms exceeds 500ms",
            latency.as_millis()
        );
    }
}
