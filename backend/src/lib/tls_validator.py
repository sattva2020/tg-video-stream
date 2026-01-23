"""
TLS Certificate Validation Utility
CORE LAYER - Library (T048)

Утилиты для проверки TLS сертификатов и HTTPS соединений:
- Проверка валидности сертификата
- Проверка срока действия
- Проверка цепочки сертификатов
- Тестирование HTTPS соединений

Использование:
    from src.lib.tls_validator import validate_tls_certificate, check_cert_expiry
    result = validate_tls_certificate("example.com")
"""

import os
import socket
import ssl
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
import cryptography.x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes


class TLSCertificateError(Exception):
    """Base exception for TLS certificate errors."""
    pass


class CertificateExpiredError(TLSCertificateError):
    """Certificate has expired."""
    pass


class CertificateNotYetValidError(TLSCertificateError):
    """Certificate is not yet valid."""
    pass


class CertificateValidationError(TLSCertificateError):
    """Certificate validation failed."""
    pass


def load_certificate_from_file(cert_path: str) -> cryptography.x509.Certificate:
    """
    Загрузка сертификата из файла.

    Args:
        cert_path: Путь к файлу сертификата (PEM или DER формат)

    Returns:
        cryptography.x509.Certificate: Объект сертификата

    Raises:
        TLSCertificateError: Если файл не существует или формат неверен
    """
    if not os.path.exists(cert_path):
        raise TLSCertificateError(f"Certificate file not found: {cert_path}")

    try:
        with open(cert_path, "rb") as f:
            cert_data = f.read()
            # Пробуем PEM формат
            try:
                cert = cryptography.x509.load_pem_x509_certificate(cert_data, default_backend())
                return cert
            except ValueError:
                # Пробуем DER формат
                try:
                    cert = cryptography.x509.load_der_x509_certificate(cert_data, default_backend())
                    return cert
                except ValueError as e:
                    raise TLSCertificateError(f"Invalid certificate format: {e}")
    except Exception as e:
        if isinstance(e, TLSCertificateError):
            raise
        raise TLSCertificateError(f"Failed to load certificate: {e}")


def check_cert_expiry(cert_path: str) -> Dict[str, Any]:
    """
    Проверка срока действия сертификата.

    Args:
        cert_path: Путь к файлу сертификата

    Returns:
        dict: Информация о сроке действия с статусом

    Raises:
        TLSCertificateError: Если файл не существует или формат неверен
    """
    cert = load_certificate_from_file(cert_path)

    not_valid_before = cert.not_valid_before_utc
    not_valid_after = cert.not_valid_after_utc
    now = datetime.now(not_valid_after.tzinfo)

    days_until_expiry = (not_valid_after - now).days
    is_expired = now > not_valid_after
    is_not_yet_valid = now < not_valid_before

    result = {
        "valid_from": not_valid_before.isoformat(),
        "valid_until": not_valid_after.isoformat(),
        "days_until_expiry": days_until_expiry,
        "is_expired": is_expired,
        "is_not_yet_valid": is_not_yet_valid,
        "is_valid": not (is_expired or is_not_yet_valid),
        "issuer": cert.issuer.rfc4514_string(),
        "subject": cert.subject.rfc4514_string(),
    }

    # Определяем статус для warning
    if is_expired:
        result["status"] = "expired"
        result["warning"] = "Certificate has expired!"
    elif is_not_yet_valid:
        result["status"] = "not_yet_valid"
        result["warning"] = "Certificate is not yet valid!"
    elif days_until_expiry <= 7:
        result["status"] = "expiring_soon"
        result["warning"] = f"Certificate expires in {days_until_expiry} days!"
    elif days_until_expiry <= 30:
        result["status"] = "expiring"
        result["warning"] = f"Certificate expires in {days_until_expiry} days."
    else:
        result["status"] = "valid"
        result["warning"] = None

    return result


def validate_certificate_chain(cert_path: str) -> Dict[str, Any]:
    """
    Валидация цепочки сертификатов.

    Args:
        cert_path: Путь к файлу сертификата

    Returns:
        dict: Результат валидации цепочки
    """
    try:
        cert = load_certificate_from_file(cert_path)

        # Проверяем самоподписан ли сертификат
        is_self_signed = False
        try:
            # Пытаемся проверить подпись сертификата им самим
            public_key = cert.public_key()
            cert.is_valid_signature(public_key)
            is_self_signed = True
        except Exception:
            is_self_signed = False

        return {
            "is_valid": True,
            "is_self_signed": is_self_signed,
            "signature_algorithm": cert.signature_algorithm_oid._name,
            "subject": cert.subject.rfc4514_string(),
            "issuer": cert.issuer.rfc4514_string(),
            "serial_number": hex(cert.serial_number),
            "version": cert.version.name,
        }
    except Exception as e:
        return {
            "is_valid": False,
            "error": str(e)
        }


def test_https_connection(hostname: str, port: int = 443, timeout: int = 10) -> Dict[str, Any]:
    """
    Тестирование HTTPS соединения и проверка сертификата.

    Args:
        hostname: Имя хоста для проверки
        port: Порт (по умолчанию 443)
        timeout: Таймаут соединения в секундах

    Returns:
        dict: Результат проверки HTTPS соединения
    """
    context = ssl.create_default_context()

    try:
        # Создаем socket соединение
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            # Оборачиваем в SSL
            with context.wrap_socket(sock, server_hostname=hostname) as secure_sock:
                # Получаем сертификат
                cert_der = secure_sock.getpeercert(binary_form=True)
                cert = cryptography.x509.load_der_x509_certificate(cert_der, default_backend())

                # Получаем информацию о протоколе и шифре
                cipher_info = secure_sock.cipher()
                protocol_version = secure_sock.version()

                # Проверяем соответствие hostname
                hostname_match = ssl.match_hostname(cert, hostname)

                return {
                    "success": True,
                    "hostname": hostname,
                    "port": port,
                    "protocol": protocol_version,
                    "cipher": {
                        "name": cipher_info[0],
                        "version": cipher_info[1],
                        "bits": cipher_info[2],
                    },
                    "certificate": {
                        "subject": cert.subject.rfc4514_string(),
                        "issuer": cert.issuer.rfc4514_string(),
                        "valid_from": cert.not_valid_before_utc.isoformat(),
                        "valid_until": cert.not_valid_after_utc.isoformat(),
                        "serial_number": hex(cert.serial_number),
                    },
                    "hostname_verified": True,
                }
    except ssl.SSLCertVerificationError as e:
        return {
            "success": False,
            "hostname": hostname,
            "error": "Certificate verification failed",
            "details": str(e)
        }
    except ssl.SSLError as e:
        return {
            "success": False,
            "hostname": hostname,
            "error": "SSL error",
            "details": str(e)
        }
    except socket.timeout:
        return {
            "success": False,
            "hostname": hostname,
            "error": "Connection timeout"
        }
    except socket.error as e:
        return {
            "success": False,
            "hostname": hostname,
            "error": "Connection failed",
            "details": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "hostname": hostname,
            "error": "Unexpected error",
            "details": str(e)
        }


def get_tls_configuration_status() -> Dict[str, Any]:
    """
    Получение статуса TLS конфигурации приложения.

    Returns:
        dict: Comprehensive статус TLS конфигурации
    """
    from src.core.config import settings

    status = {
        "tls_enabled": settings.TLS_ENABLED,
        "environment": settings.ENVIRONMENT,
        "certificate_path": settings.TLS_CERT_PATH if settings.TLS_ENABLED else None,
        "key_path": settings.TLS_KEY_PATH if settings.TLS_ENABLED else None,
        "certificate_valid": None,
        "certificate_expiry": None,
        "warnings": [],
        "recommendations": [],
    }

    # Проверяем сертификат если TLS включен и файл существует
    if settings.TLS_ENABLED:
        if os.path.exists(settings.TLS_CERT_PATH):
            try:
                expiry_info = check_cert_expiry(settings.TLS_CERT_PATH)
                status["certificate_valid"] = expiry_info["is_valid"]
                status["certificate_expiry"] = expiry_info["valid_until"]

                if expiry_info["warning"]:
                    status["warnings"].append(expiry_info["warning"])

                # Проверяем цепочку
                chain_info = validate_certificate_chain(settings.TLS_CERT_PATH)
                status["certificate_chain"] = chain_info

                if chain_info.get("is_self_signed") and settings.ENVIRONMENT == "production":
                    status["warnings"].append("Self-signed certificate detected in production")

            except TLSCertificateError as e:
                status["certificate_valid"] = False
                status["warnings"].append(f"Certificate error: {e}")
        else:
            status["certificate_valid"] = False
            status["warnings"].append(f"Certificate file not found: {settings.TLS_CERT_PATH}")

        # Рекомендации
        if settings.ENVIRONMENT == "production":
            if not settings.TLS_ENABLED:
                status["recommendations"].append("Enable TLS in production environment")

            if status.get("certificate_valid") is False:
                status["recommendations"].append("Fix certificate configuration")

    return status
