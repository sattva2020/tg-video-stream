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
pub fn routes(state: Arc<AppState>) -> Router<Arc<AppState>> {
    Router::new()
        // POST /api/v1/transcode - основной эндпоинт транскодирования
        .merge(transcode::routes())
}
