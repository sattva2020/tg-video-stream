//! Rust FFmpeg Transcoder Microservice
//!
//! Высокопроизводительный сервис транскодирования аудио на базе Axum + FFmpeg.
//! Предоставляет HTTP API для транскодирования аудио в реальном времени.

use std::net::SocketAddr;
use std::sync::Arc;

use tracing::{info, Level};
use tracing_subscriber::{fmt, layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use rust_transcoder::{build_router, AppState};

/// Инициализация structured logging с tracing
fn init_tracing() {
    let env_filter = EnvFilter::try_from_default_env()
        .unwrap_or_else(|_| EnvFilter::new("info,rust_transcoder=debug,tower_http=debug"));

    tracing_subscriber::registry()
        .with(env_filter)
        .with(
            fmt::layer()
                .json()
                .with_target(true)
                .with_thread_ids(true)
                .with_file(true)
                .with_line_number(true),
        )
        .init();
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Инициализация логирования
    init_tracing();

    info!("Starting Rust FFmpeg Transcoder Microservice");

    // Конфигурация из переменных окружения
    let port: u16 = std::env::var("PORT")
        .unwrap_or_else(|_| "8090".to_string())
        .parse()
        .expect("PORT must be a valid u16");

    let max_concurrent: usize = std::env::var("MAX_CONCURRENT_STREAMS")
        .unwrap_or_else(|_| "50".to_string())
        .parse()
        .expect("MAX_CONCURRENT_STREAMS must be a valid usize");

    // Создаём shared state
    let state = Arc::new(AppState::new(max_concurrent));

    info!(
        port = port,
        max_concurrent_streams = max_concurrent,
        "Configuration loaded"
    );

    // Строим router
    let app = build_router(state);

    // Биндим на все интерфейсы
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    let listener = tokio::net::TcpListener::bind(addr).await?;

    info!(%addr, "Server listening");

    // Запускаем сервер
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;

    info!("Server shutdown complete");

    Ok(())
}

/// Обработка сигналов завершения для graceful shutdown
async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("Failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("Failed to install SIGTERM handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {
            info!("Received Ctrl+C, initiating graceful shutdown");
        }
        _ = terminate => {
            info!("Received SIGTERM, initiating graceful shutdown");
        }
    }
}