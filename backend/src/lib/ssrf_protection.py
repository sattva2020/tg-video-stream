"""
SSRF (Server-Side Request Forgery) protection utility.

Защита от SSRF (Server-Side Request Forgery) атак.
Блокирует запросы к внутренним и приватным сетевым ресурсам.

This module provides URL validation to prevent SSRF attacks by blocking:
- Private IP addresses (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Loopback addresses (127.0.0.0/8)
- Link-local addresses (169.254.0.0/16)
- Localhost hostnames
- Cloud metadata endpoints
- Non-HTTP/HTTPS schemes
"""

import re
import socket
from ipaddress import ip_address, IPv4Address, IPv6Address
from typing import Optional, Tuple
from urllib.parse import urlparse


class SSRFProtection:
    """
    Server-Side Request Forgery (SSRF) protection.

    Защита от SSRF атак.
    Блокирует запросы к внутренним ресурсам.

    This class validates URLs to prevent SSRF attacks by checking:
    - URL scheme (only http/https allowed)
    - Private IP ranges
    - Localhost hostnames
    - Cloud metadata endpoints

    Example:
        >>> is_safe, error = SSRFProtection.validate_url("http://192.168.1.1/video")
        >>> print(is_safe)  # False
        >>> print(error)  # "Private IP address blocked"

        >>> is_safe, error = SSRFProtection.validate_url("https://example.com/video.mp4")
        >>> print(is_safe)  # True
        >>> print(error)  # None
    """

    # Private IP ranges patterns
    # Шаблоны приватных IP диапазонов
    PRIVATE_IP_PATTERNS = [
        r'^10\.',                  # 10.0.0.0/8
        r'^172\.(1[6-9]|2\d|3[01])\.',  # 172.16.0.0/12
        r'^192\.168\.',            # 192.168.0.0/16
        r'^127\.',                 # 127.0.0.0/8 (localhost)
        r'^169\.254\.',            # 169.254.0.0/16 (link-local)
        r'^0\.',                   # 0.0.0.0/8
    ]

    # Blocked local hostnames
    # Заблокированные локальные имена хостов
    BLOCKED_HOSTNAMES = [
        'localhost',
        'localhost.localdomain',
        'ip6-localhost',
        'ip6-loopback',
    ]

    # Cloud metadata endpoints (CRITICAL to block these!)
    # Конечные точки метаданных облачных сервисов (КРИТИЧЕСКИ важно блокировать!)
    CLOUD_METADATA_ENDPOINTS = [
        '169.254.169.254',         # AWS/GCP/Azure metadata
        '100.100.100.200',         # Alibaba Cloud
        'metadata.google.internal',  # GCP
    ]

    # Allowed URL schemes
    # Разрешенные схемы URL
    ALLOWED_SCHEMES = ('http', 'https')

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL for SSRF protection.

        Проверка URL для защиты от SSRF атак.

        Args:
            url: URL to validate / URL для проверки

        Returns:
            Tuple of (is_safe, error_message)
            Кортеж (is_safe, error_message)
            - is_safe: True if URL is safe, False otherwise / True если URL безопасен
            - error_message: Error message if unsafe, None if safe / Сообщение об ошибке или None

        Example:
            >>> is_safe, error = SSRFProtection.validate_url("http://192.168.1.1/video")
            >>> assert is_safe is False
            >>> assert "private" in error.lower()

            >>> is_safe, error = SSRFProtection.validate_url("https://example.com/video.mp4")
            >>> assert is_safe is True
            >>> assert error is None
        """
        try:
            # Parse URL
            parsed = urlparse(url.strip())

            # Block non-http/https schemes (file://, ftp://, etc.)
            # Блокируем схемы кроме http/https
            if parsed.scheme not in cls.ALLOWED_SCHEMES:
                return False, f"URL scheme '{parsed.scheme}' not allowed"

            # Extract hostname
            # Извлекаем имя хоста
            hostname = parsed.hostname or parsed.netloc.split(':')[0]

            if not hostname:
                return False, "Invalid URL: no hostname"

            # Block cloud metadata endpoints (CRITICAL SECURITY CHECK)
            # Блокируем конечные точки метаданных облачных сервисов (КРИТИЧЕСКАЯ ПРОВЕРКА)
            if hostname in cls.CLOUD_METADATA_ENDPOINTS:
                return False, "Cloud metadata endpoint blocked"

            # Block common local hostnames
            # Блокируем общеупотребительные локальные имена хостов
            if hostname.lower() in cls.BLOCKED_HOSTNAMES:
                return False, "Local hostname blocked"

            # Check if hostname is an IP address
            # Проверяем, является ли имя хоста IP-адресом
            try:
                ip = ip_address(hostname)

                # Check IPv4 addresses for private/reserved ranges
                # Проверяем IPv4 адреса на приватные/зарезервированные диапазоны
                if isinstance(ip, IPv4Address):
                    if ip.is_private:
                        return False, "Private IP address blocked"
                    if ip.is_loopback:
                        return False, "Loopback address blocked"
                    if ip.is_link_local:
                        return False, "Link-local address blocked"
                    if ip.is_reserved:
                        return False, "Reserved IP blocked"
                    if ip.is_multicast:
                        return False, "Multicast IP blocked"

                # Check IPv6 addresses
                # Проверяем IPv6 адреса
                if isinstance(ip, IPv6Address):
                    if ip.is_private:
                        return False, "Private IPv6 address blocked"
                    if ip.is_loopback:
                        return False, "IPv6 loopback address blocked"
                    if ip.is_link_local:
                        return False, "IPv6 link-local address blocked"
                    if ip.is_reserved:
                        return False, "Reserved IPv6 address blocked"

            except ValueError:
                # Hostname is not an IP address, need to resolve DNS
                # Имя хоста не является IP-адресом, нужно разрешить DNS
                try:
                    # Resolve hostname to IP addresses
                    # Разрешаем имя хоста в IP адреса
                    addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
                    
                    # Check all resolved IPs
                    # Проверяем все разрешённые IP адреса
                    for family, _, _, _, sockaddr in addr_info:
                        resolved_ip_str = sockaddr[0]
                        
                        try:
                            resolved_ip = ip_address(resolved_ip_str)
                            
                            # Check IPv4 addresses
                            if isinstance(resolved_ip, IPv4Address):
                                if resolved_ip.is_private:
                                    return False, f"Hostname resolves to private IP: {resolved_ip_str}"
                                if resolved_ip.is_loopback:
                                    return False, f"Hostname resolves to loopback IP: {resolved_ip_str}"
                                if resolved_ip.is_link_local:
                                    return False, f"Hostname resolves to link-local IP: {resolved_ip_str}"
                                if resolved_ip.is_reserved:
                                    return False, f"Hostname resolves to reserved IP: {resolved_ip_str}"
                                if resolved_ip.is_multicast:
                                    return False, f"Hostname resolves to multicast IP: {resolved_ip_str}"
                            
                            # Check IPv6 addresses
                            if isinstance(resolved_ip, IPv6Address):
                                if resolved_ip.is_private:
                                    return False, f"Hostname resolves to private IPv6: {resolved_ip_str}"
                                if resolved_ip.is_loopback:
                                    return False, f"Hostname resolves to IPv6 loopback: {resolved_ip_str}"
                                if resolved_ip.is_link_local:
                                    return False, f"Hostname resolves to IPv6 link-local: {resolved_ip_str}"
                                if resolved_ip.is_reserved:
                                    return False, f"Hostname resolves to reserved IPv6: {resolved_ip_str}"
                        
                        except ValueError:
                            # Skip if IP parsing fails
                            continue
                
                except socket.gaierror:
                    # DNS resolution failed
                    return False, "Hostname DNS resolution failed"
                except Exception as e:
                    # Unexpected error during DNS resolution
                    return False, f"DNS resolution error: {str(e)}"

            # URL passed all SSRF checks
            # URL прошел все проверки SSRF
            return True, None

        except Exception as e:
            # Unexpected error during validation
            # Непредвиденная ошибка при проверке
            return False, f"URL validation failed: {str(e)}"

    @classmethod
    def validate_url_with_context(cls, url: str, context: Optional[dict] = None) -> dict:
        """
        Validate URL with detailed context information.

        Проверка URL с подробной контекстной информацией.

        Args:
            url: URL to validate / URL для проверки
            context: Additional context for logging / Дополнительный контекст для логирования

        Returns:
            Dictionary with validation result:
            {
                'safe': bool,
                'error': str or None,
                'hostname': str,
                'scheme': str,
                'is_private_ip': bool,
                'is_loopback': bool,
                'context': dict
            }
        """
        result = {
            'safe': False,
            'error': None,
            'hostname': None,
            'scheme': None,
            'is_private_ip': False,
            'is_loopback': False,
            'context': context or {}
        }

        try:
            parsed = urlparse(url.strip())
            result['scheme'] = parsed.scheme
            result['hostname'] = parsed.hostname or parsed.netloc.split(':')[0]

            # Run validation
            is_safe, error = cls.validate_url(url)
            result['safe'] = is_safe
            result['error'] = error

            # Add IP classification
            try:
                ip = ip_address(result['hostname'])
                result['is_private_ip'] = ip.is_private
                result['is_loopback'] = ip.is_loopback
            except ValueError:
                pass  # Not an IP address

        except Exception as e:
            result['error'] = f"Validation failed: {str(e)}"

        return result
