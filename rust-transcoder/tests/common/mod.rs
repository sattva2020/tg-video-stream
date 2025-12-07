//! Общие утилиты для тестов

use std::sync::Arc;

use axum::Router;

// Re-export from main crate
use rust_transcoder::{AppState, build_router};

/// Создаёт тестовое приложение с ограниченным concurrency
pub fn create_test_app() -> Router {
    let state = Arc::new(AppState::new(10));
    build_router(state)
}

/// Создаёт тестовое приложение с кастомным concurrency limit
pub fn create_test_app_with_limit(max_concurrent: usize) -> Router {
    let state = Arc::new(AppState::new(max_concurrent));
    build_router(state)
}
