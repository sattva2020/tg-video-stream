//! URL validation module - защита от SSRF атак
//!
//! Проверяет что source_url не позволяет:
//! - Доступ к локальным файлам (file://)
//! - Доступ к внутренним IP адресам (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
//! - Доступ к localhost (127.0.0.1, ::1)

use std::net::{IpAddr, Ipv4Addr, Ipv6Addr};
use url::Url;

/// Ошибки валидации URL
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UrlValidationError {
    /// Некорректный URL формат
    InvalidFormat(String),
    /// Запрещённая схема (file://, data:// и т.д.)
    ForbiddenScheme(String),
    /// Доступ к приватному IP адресу
    PrivateIpAddress(String),
    /// Доступ к localhost
    LocalhostAccess,
    /// Отсутствует хост
    MissingHost,
}

impl std::fmt::Display for UrlValidationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidFormat(msg) => write!(f, "Invalid URL format: {}", msg),
            Self::ForbiddenScheme(scheme) => {
                write!(f, "Forbidden URL scheme: {} (only http/https allowed)", scheme)
            }
            Self::PrivateIpAddress(ip) => {
                write!(f, "Access to private IP address is forbidden: {}", ip)
            }
            Self::LocalhostAccess => write!(f, "Access to localhost is forbidden"),
            Self::MissingHost => write!(f, "URL must contain a host"),
        }
    }
}

/// Проверяет является ли IP адрес приватным
fn is_private_ip(ip: &IpAddr) -> bool {
    match ip {
        IpAddr::V4(ipv4) => is_private_ipv4(ipv4),
        IpAddr::V6(ipv6) => is_private_ipv6(ipv6),
    }
}

/// Проверяет является ли IPv4 адрес приватным
fn is_private_ipv4(ip: &Ipv4Addr) -> bool {
    // 10.0.0.0/8
    ip.octets()[0] == 10
        // 172.16.0.0/12
        || (ip.octets()[0] == 172 && (ip.octets()[1] >= 16 && ip.octets()[1] <= 31))
        // 192.168.0.0/16
        || (ip.octets()[0] == 192 && ip.octets()[1] == 168)
        // 127.0.0.0/8 (loopback)
        || ip.octets()[0] == 127
        // 169.254.0.0/16 (link-local)
        || (ip.octets()[0] == 169 && ip.octets()[1] == 254)
        // 0.0.0.0/8 (current network)
        || ip.octets()[0] == 0
}

/// Проверяет является ли IPv6 адрес приватным
fn is_private_ipv6(ip: &Ipv6Addr) -> bool {
    // ::1 (loopback)
    ip.is_loopback()
        // fc00::/7 (unique local)
        || (ip.segments()[0] & 0xfe00) == 0xfc00
        // fe80::/10 (link-local)
        || (ip.segments()[0] & 0xffc0) == 0xfe80
}

/// Проверяет является ли хост localhost
fn is_localhost(host: &str) -> bool {
    matches!(
        host.to_lowercase().as_str(),
        "localhost" | "127.0.0.1" | "::1" | "[::1]"
    )
}

/// Валидирует URL для защиты от SSRF атак
pub fn validate_source_url(url: &str) -> Result<(), UrlValidationError> {
    // Парсим URL
    let parsed = Url::parse(url)
        .map_err(|e| UrlValidationError::InvalidFormat(e.to_string()))?;

    // Проверяем схему (только http/https)
    match parsed.scheme() {
        "http" | "https" => {},
        scheme => return Err(UrlValidationError::ForbiddenScheme(scheme.to_string())),
    }

    // Получаем хост
    let host = parsed
        .host_str()
        .ok_or(UrlValidationError::MissingHost)?;

    // Проверяем localhost
    if is_localhost(host) {
        return Err(UrlValidationError::LocalhostAccess);
    }

    // Пытаемся распарсить как IP адрес
    if let Ok(ip) = host.parse::<IpAddr>() {
        if is_private_ip(&ip) {
            return Err(UrlValidationError::PrivateIpAddress(ip.to_string()));
        }
    }

    // Дополнительная проверка: резолвим доменное имя в IP
    // ВАЖНО: В production следует добавить DNS резолвинг и проверку результата
    // Пример: tokio::net::lookup_host() и проверка каждого IP
    // Сейчас пропускаем эту проверку, так как она требует async контекста

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_http_url() {
        assert!(validate_source_url("http://example.com/audio.mp3").is_ok());
    }

    #[test]
    fn test_valid_https_url() {
        assert!(validate_source_url("https://cdn.example.com/audio.mp3").is_ok());
    }

    #[test]
    fn test_file_scheme_forbidden() {
        let result = validate_source_url("file:///etc/passwd");
        assert!(matches!(result, Err(UrlValidationError::ForbiddenScheme(_))));
    }

    #[test]
    fn test_data_scheme_forbidden() {
        let result = validate_source_url("data:text/plain,hello");
        assert!(matches!(result, Err(UrlValidationError::ForbiddenScheme(_))));
    }

    #[test]
    fn test_localhost_forbidden() {
        let result = validate_source_url("http://localhost:8080/audio.mp3");
        assert!(matches!(result, Err(UrlValidationError::LocalhostAccess)));
    }

    #[test]
    fn test_127_0_0_1_forbidden() {
        let result = validate_source_url("http://127.0.0.1/audio.mp3");
        assert!(matches!(result, Err(UrlValidationError::LocalhostAccess)));
    }

    #[test]
    fn test_ipv6_localhost_forbidden() {
        let result = validate_source_url("http://[::1]/audio.mp3");
        assert!(matches!(result, Err(UrlValidationError::LocalhostAccess)));
    }

    #[test]
    fn test_private_ip_10_x_forbidden() {
        let result = validate_source_url("http://10.0.0.1/audio.mp3");
        assert!(matches!(result, Err(UrlValidationError::PrivateIpAddress(_))));
    }

    #[test]
    fn test_private_ip_192_168_forbidden() {
        let result = validate_source_url("http://192.168.1.1/audio.mp3");
        assert!(matches!(result, Err(UrlValidationError::PrivateIpAddress(_))));
    }

    #[test]
    fn test_private_ip_172_16_forbidden() {
        let result = validate_source_url("http://172.16.0.1/audio.mp3");
        assert!(matches!(result, Err(UrlValidationError::PrivateIpAddress(_))));
    }

    #[test]
    fn test_private_ip_172_31_forbidden() {
        let result = validate_source_url("http://172.31.255.255/audio.mp3");
        assert!(matches!(result, Err(UrlValidationError::PrivateIpAddress(_))));
    }

    #[test]
    fn test_public_ip_allowed() {
        // 8.8.8.8 - публичный DNS Google
        assert!(validate_source_url("http://8.8.8.8/audio.mp3").is_ok());
    }

    #[test]
    fn test_link_local_169_254_forbidden() {
        let result = validate_source_url("http://169.254.1.1/audio.mp3");
        assert!(matches!(result, Err(UrlValidationError::PrivateIpAddress(_))));
    }

    #[test]
    fn test_invalid_url_format() {
        let result = validate_source_url("not-a-valid-url");
        assert!(matches!(result, Err(UrlValidationError::InvalidFormat(_))));
    }

    #[test]
    fn test_url_without_host() {
        let result = validate_source_url("http:///audio.mp3");
        assert!(matches!(result, Err(UrlValidationError::MissingHost)));
    }

    #[test]
    fn test_is_private_ipv4() {
        assert!(is_private_ipv4(&Ipv4Addr::new(10, 0, 0, 1)));
        assert!(is_private_ipv4(&Ipv4Addr::new(172, 16, 0, 1)));
        assert!(is_private_ipv4(&Ipv4Addr::new(192, 168, 1, 1)));
        assert!(is_private_ipv4(&Ipv4Addr::new(127, 0, 0, 1)));
        assert!(!is_private_ipv4(&Ipv4Addr::new(8, 8, 8, 8)));
        assert!(!is_private_ipv4(&Ipv4Addr::new(1, 1, 1, 1)));
    }

    #[test]
    fn test_is_localhost() {
        assert!(is_localhost("localhost"));
        assert!(is_localhost("LOCALHOST"));
        assert!(is_localhost("127.0.0.1"));
        assert!(is_localhost("::1"));
        assert!(is_localhost("[::1]"));
        assert!(!is_localhost("example.com"));
    }
}
