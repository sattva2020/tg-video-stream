//! FFmpeg процесс wrapper
//!
//! Управление FFmpeg subprocess для транскодирования аудио.

use std::process::Stdio;

use tokio::process::{Child, Command};
use tracing::{debug, instrument};

use crate::error::{AppError, AppResult};
use crate::models::{AudioCodec, AudioFormat, AudioQuality};

use super::profiles::TranscodeProfile;

/// FFmpeg процесс для транскодирования
#[derive(Debug)]
pub struct FfmpegProcess {
    /// Дочерний процесс FFmpeg
    child: Child,
    /// Профиль транскодирования
    profile: TranscodeProfile,
}

impl FfmpegProcess {
    /// Запускает FFmpeg процесс с указанным профилем
    #[instrument(skip(profile), fields(source = %profile.source_url))]
    pub async fn spawn(profile: TranscodeProfile) -> AppResult<Self> {
        let args = profile.build_ffmpeg_args();

        debug!(
            args = ?args,
            "Spawning FFmpeg process"
        );

        let child = Command::new("ffmpeg")
            .args(&args)
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .kill_on_drop(true)
            .spawn()
            .map_err(|e| AppError::Ffmpeg(format!("Failed to spawn FFmpeg: {}", e)))?;

        Ok(Self { child, profile })
    }

    /// Возвращает stdout для чтения транскодированного потока
    pub fn take_stdout(&mut self) -> Option<tokio::process::ChildStdout> {
        self.child.stdout.take()
    }

    /// Возвращает stderr для чтения логов FFmpeg
    pub fn take_stderr(&mut self) -> Option<tokio::process::ChildStderr> {
        self.child.stderr.take()
    }

    /// Проверяет, работает ли процесс
    pub fn is_running(&mut self) -> bool {
        self.child.try_wait().ok().flatten().is_none()
    }

    /// Завершает процесс
    pub async fn kill(&mut self) -> AppResult<()> {
        self.child
            .kill()
            .await
            .map_err(|e| AppError::Ffmpeg(format!("Failed to kill FFmpeg: {}", e)))
    }

    /// Ожидает завершения процесса
    pub async fn wait(&mut self) -> AppResult<std::process::ExitStatus> {
        self.child
            .wait()
            .await
            .map_err(|e| AppError::Ffmpeg(format!("Failed to wait for FFmpeg: {}", e)))
    }

    /// Возвращает профиль
    pub fn profile(&self) -> &TranscodeProfile {
        &self.profile
    }
}

/// Проверяет доступность FFmpeg
pub async fn check_ffmpeg_available() -> AppResult<String> {
    let output = Command::new("ffmpeg")
        .arg("-version")
        .output()
        .await
        .map_err(|e| AppError::Ffmpeg(format!("FFmpeg not found: {}", e)))?;

    if !output.status.success() {
        return Err(AppError::Ffmpeg("FFmpeg returned non-zero exit code".into()));
    }

    let version = String::from_utf8_lossy(&output.stdout);
    let first_line = version.lines().next().unwrap_or("unknown");

    Ok(first_line.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ffmpeg_process_creation() {
        // Unit test - не запускает реальный процесс
        // Интеграционные тесты в tests/
    }
}
