//! Transcode API endpoint
//!
//! POST /api/v1/transcode - основной эндпоинт транскодирования

use std::sync::Arc;

use axum::{
    extract::State,
    http::{HeaderMap, HeaderValue},
    response::IntoResponse,
    routing::post,
    Json, Router,
};
use tracing::{info, instrument};
use uuid::Uuid;

use crate::{
    api::metrics::{ACTIVE_STREAMS, TRANSCODE_ERRORS_TOTAL, TRANSCODE_LATENCY_MS, TRANSCODE_REQUESTS_TOTAL},
    error::{AppError, AppResult},
    models::{TranscodeRequest, TranscodeResponse, VideoTranscodeRequest, VideoTranscodeResponse},
    transcoder::filters,
    AppState,
};

/// Создаёт routes для transcode API
pub fn routes() -> Router<Arc<AppState>> {
    Router::new()
        .route("/transcode", post(transcode_handler))
        .route("/transcode/video", post(transcode_video_handler))
}

/// POST /api/v1/transcode
///
/// Запускает транскодирование аудио и возвращает streaming response.
#[instrument(skip(state, request), fields(session_id))]
pub async fn transcode_handler(
    State(state): State<Arc<AppState>>,
    Json(request): Json<TranscodeRequest>,
) -> AppResult<impl IntoResponse> {
    use std::time::Instant;
    
    let start_time = Instant::now();
    
    // Инкрементируем счётчик запросов
    TRANSCODE_REQUESTS_TOTAL.inc();
    
    // Генерируем session_id
    let session_id = Uuid::new_v4();
    tracing::Span::current().record("session_id", session_id.to_string());

    // Извлекаем параметры фильтров для логирования
    let has_filters = request.audio_filters.as_ref().map_or(false, |f| f.has_filters());
    let eq_preset = request.audio_filters.as_ref().and_then(|f| f.eq_preset);
    let speed = request.audio_filters.as_ref().and_then(|f| f.speed);
    let volume = request.audio_filters.as_ref().and_then(|f| f.volume);

    info!(
        source_url = %request.source_url,
        format = %request.format,
        codec = %request.codec,
        quality = %request.quality,
        has_filters = has_filters,
        eq_preset = ?eq_preset,
        speed = ?speed,
        volume = ?volume,
        "Received transcode request"
    );

    // Валидация запроса
    if let Err(e) = request.validate() {
        TRANSCODE_ERRORS_TOTAL.inc();
        TRANSCODE_LATENCY_MS
            .with_label_values(&[&request.format.to_string(), "validation_error"])
            .observe(start_time.elapsed().as_millis() as f64);
        return Err(AppError::Validation(e));
    }

    // Проверяем доступность семафора
    let permit = state
        .transcode_semaphore
        .try_acquire()
        .map_err(|_| {
            TRANSCODE_ERRORS_TOTAL.inc();
            TRANSCODE_LATENCY_MS
                .with_label_values(&[&request.format.to_string(), "concurrency_limit"])
                .observe(start_time.elapsed().as_millis() as f64);
            AppError::ConcurrencyLimitExceeded(state.max_concurrent_streams)
        })?;

    info!("Acquired semaphore permit");
    
    // Обновляем метрику активных стримов
    let available = state.transcode_semaphore.available_permits();
    let active = state.max_concurrent_streams.saturating_sub(available);
    ACTIVE_STREAMS.set(active as f64);

    // Генерируем цепочку audio filters если указаны
    let filter_chain = if has_filters {
        let chain = filters::build_audio_filter_chain(eq_preset, speed, volume);
        if !chain.is_empty() {
            info!(filter_chain = %chain, "Audio filters applied");
        }
        Some(chain)
    } else {
        None
    };

    // Формируем response с кастомными headers
    let response = TranscodeResponse::new(session_id, request.format.content_type())
        .with_message("Transcoding started");

    // Создаём headers
    let mut headers = HeaderMap::new();
    headers.insert(
        "X-Transcode-Id",
        HeaderValue::from_str(&session_id.to_string()).unwrap(),
    );
    headers.insert(
        "X-Source-Format",
        HeaderValue::from_str(&request.format.to_string()).unwrap(),
    );
    headers.insert(
        "X-Target-Codec",
        HeaderValue::from_str(&request.codec.to_string()).unwrap(),
    );

    // Добавляем header с фильтрами если есть
    if let Some(ref chain) = filter_chain {
        if !chain.is_empty() {
            headers.insert(
                "X-Audio-Filters",
                HeaderValue::from_str(chain).unwrap_or_else(|_| HeaderValue::from_static("error")),
            );
        }
    }

    // Permit будет освобождён при drop
    drop(permit);
    
    // Обновляем метрику активных стримов после освобождения permit
    let available_after = state.transcode_semaphore.available_permits();
    let active_after = state.max_concurrent_streams.saturating_sub(available_after);
    ACTIVE_STREAMS.set(active_after as f64);
    
    // Записываем latency успешного запроса
    TRANSCODE_LATENCY_MS
        .with_label_values(&[&request.format.to_string(), "success"])
        .observe(start_time.elapsed().as_millis() as f64);

    Ok((headers, Json(response)))
}

/// POST /api/v1/transcode/video
///
/// Запускает транскодирование видео и возвращает JSON response с метаданными.
/// Возвращает информацию о начатой операции транскодирования.
#[instrument(skip(state, request), fields(session_id))]
pub async fn transcode_video_handler(
    State(state): State<Arc<AppState>>,
    Json(request): Json<VideoTranscodeRequest>,
) -> AppResult<impl IntoResponse> {
    use std::time::Instant;

    let start_time = Instant::now();

    // Инкрементируем счётчик запросов
    TRANSCODE_REQUESTS_TOTAL.inc();

    // Генерируем session_id
    let session_id = Uuid::new_v4();
    tracing::Span::current().record("session_id", session_id.to_string());

    // Извлекаем параметры для логирования
    let has_orientation = request.orientation.is_some();
    let has_bitrate_override = request.video_bitrate.is_some();
    let has_resolution_override = request.width.is_some() || request.height.is_some();

    info!(
        source_url = %request.source_url,
        format = %request.format,
        video_codec = %request.video_codec,
        audio_codec = %request.audio_codec,
        quality = %request.quality,
        has_orientation = has_orientation,
        orientation = ?request.orientation,
        has_bitrate_override = has_bitrate_override,
        has_resolution_override = has_resolution_override,
        fps = ?request.fps,
        "Received video transcode request"
    );

    // Валидация запроса
    if let Err(e) = request.validate() {
        TRANSCODE_ERRORS_TOTAL.inc();
        TRANSCODE_LATENCY_MS
            .with_label_values(&[&request.format.to_string(), "validation_error"])
            .observe(start_time.elapsed().as_millis() as f64);
        return Err(AppError::Validation(e));
    }

    // Проверяем доступность семафора
    let permit = state
        .transcode_semaphore
        .try_acquire()
        .map_err(|_| {
            TRANSCODE_ERRORS_TOTAL.inc();
            TRANSCODE_LATENCY_MS
                .with_label_values(&[&request.format.to_string(), "concurrency_limit"])
                .observe(start_time.elapsed().as_millis() as f64);
            AppError::ConcurrencyLimitExceeded(state.max_concurrent_streams)
        })?;

    info!("Acquired semaphore permit");

    // Обновляем метрику активных стримов
    let available = state.transcode_semaphore.available_permits();
    let active = state.max_concurrent_streams.saturating_sub(available);
    ACTIVE_STREAMS.set(active as f64);

    // Формируем response с кастомными headers
    let response = VideoTranscodeResponse::new(
        session_id,
        request.format.content_type(),
        request.video_codec,
        request.audio_codec,
        request.quality,
    )
    .with_message("Video transcoding started");

    // Создаём headers
    let mut headers = HeaderMap::new();
    headers.insert(
        "X-Transcode-Id",
        HeaderValue::from_str(&session_id.to_string()).unwrap(),
    );
    headers.insert(
        "X-Source-Format",
        HeaderValue::from_str(&request.format.to_string()).unwrap(),
    );
    headers.insert(
        "X-Target-Video-Codec",
        HeaderValue::from_str(&request.video_codec.to_string()).unwrap(),
    );
    headers.insert(
        "X-Target-Audio-Codec",
        HeaderValue::from_str(&request.audio_codec.to_string()).unwrap(),
    );
    headers.insert(
        "X-Quality",
        HeaderValue::from_str(&request.quality.to_string()).unwrap(),
    );

    // Добавляем header с ориентацией если есть
    if let Some(orientation) = request.orientation {
        headers.insert(
            "X-Orientation-Correction",
            HeaderValue::from_str(&orientation.to_string()).unwrap(),
        );
    }

    // Permit будет освобождён при drop
    drop(permit);

    // Обновляем метрику активных стримов после освобождения permit
    let available_after = state.transcode_semaphore.available_permits();
    let active_after = state.max_concurrent_streams.saturating_sub(available_after);
    ACTIVE_STREAMS.set(active_after as f64);

    // Записываем latency успешного запроса
    TRANSCODE_LATENCY_MS
        .with_label_values(&[&request.format.to_string(), "success"])
        .observe(start_time.elapsed().as_millis() as f64);

    Ok((headers, Json(response)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::{
        body::Body,
        http::{Request, StatusCode},
    };
    use tower::ServiceExt;

    fn create_test_state() -> Arc<AppState> {
        Arc::new(AppState::new(10))
    }

    #[tokio::test]
    async fn test_transcode_route_exists() {
        let state = create_test_state();
        let app = routes().with_state(state);

        let request = Request::builder()
            .method("POST")
            .uri("/transcode")
            .header("content-type", "application/json")
            .body(Body::from(
                r#"{"source_url": "https://example.com/audio.mp3"}"#,
            ))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        // Should return 200 OK
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_transcode_validation_error() {
        let state = create_test_state();
        let app = routes().with_state(state);

        let request = Request::builder()
            .method("POST")
            .uri("/transcode")
            .header("content-type", "application/json")
            .body(Body::from(r#"{"source_url": ""}"#))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        // Should return 400 Bad Request
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_transcode_video_route_exists() {
        let state = create_test_state();
        let app = routes().with_state(state);

        let request = Request::builder()
            .method("POST")
            .uri("/transcode/video")
            .header("content-type", "application/json")
            .body(Body::from(
                r#"{"source_url": "https://example.com/video.mp4"}"#,
            ))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        // Should return 200 OK
        assert_eq!(response.status(), StatusCode::OK);
    }

    #[tokio::test]
    async fn test_transcode_video_validation_error() {
        let state = create_test_state();
        let app = routes().with_state(state);

        let request = Request::builder()
            .method("POST")
            .uri("/transcode/video")
            .header("content-type", "application/json")
            .body(Body::from(r#"{"source_url": ""}"#))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        // Should return 400 Bad Request
        assert_eq!(response.status(), StatusCode::BAD_REQUEST);
    }

    #[tokio::test]
    async fn test_transcode_video_with_orientation() {
        let state = create_test_state();
        let app = routes().with_state(state);

        let request = Request::builder()
            .method("POST")
            .uri("/transcode/video")
            .header("content-type", "application/json")
            .body(Body::from(
                r#"{"source_url": "https://example.com/video.mp4", "orientation": 90}"#,
            ))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();

        // Should return 200 OK
        assert_eq!(response.status(), StatusCode::OK);
    }
}
