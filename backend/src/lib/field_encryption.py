"""
Field-level encryption for sensitive database fields.

This module provides encryption/decryption utilities for protecting
sensitive data at rest in the database (e.g., PII, secrets, tokens).
"""
from cryptography.fernet import Fernet
from src.core.config import settings
import base64
import logging

logger = logging.getLogger(__name__)


class FieldEncryptionError(Exception):
    """Raised when field encryption/decryption fails."""
    pass


def _get_encryption_key() -> bytes:
    """
    Get and validate the field encryption key.

    Returns:
        bytes: 32-byte url-safe base64-encoded key suitable for Fernet

    Raises:
        FieldEncryptionError: If key is missing or invalid
    """
    key = settings.DATA_ENCRYPTION_KEY

    if not key:
        raise FieldEncryptionError(
            "DATA_ENCRYPTION_KEY is not set. Field encryption requires a valid key. "
            "Generate one with: openssl rand -base64 32"
        )

    # Ensure key is bytes
    if isinstance(key, str):
        key = key.encode()

    # Validate key format - Fernet requires 32-byte url-safe base64-encoded key
    try:
        # Attempt to create a Fernet instance to validate the key
        Fernet(key)
    except (ValueError, base64.binascii.Error) as e:
        raise FieldEncryptionError(
            f"Invalid DATA_ENCRYPTION_KEY format. Must be 32-byte url-safe base64-encoded key. Error: {e}"
        )

    return key


def encrypt_field(plaintext: str | None) -> str | None:
    """
    Encrypt a field value for storage in the database.

    Args:
        plaintext: The plain text value to encrypt (can be None or empty)

    Returns:
        str | None: Encrypted value as base64-encoded string, or None if input was None

    Raises:
        FieldEncryptionError: If encryption fails

    Examples:
        >>> encrypted = encrypt_field("sensitive_data")
        >>> decrypted = decrypt_field(encrypted)
        >>> assert decrypted == "sensitive_data"
    """
    # Handle None/empty values - return as-is
    if plaintext is None:
        return None
    if plaintext == "":
        return ""

    # Check if field encryption is enabled
    if not settings.DATA_ENCRYPTION_ENABLED:
        logger.debug("Field encryption disabled, returning plaintext")
        return plaintext

    try:
        key = _get_encryption_key()
        fernet = Fernet(key)
        encrypted_bytes = fernet.encrypt(plaintext.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    except FieldEncryptionError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        raise FieldEncryptionError(f"Failed to encrypt field: {e}")


def decrypt_field(ciphertext: str | None) -> str | None:
    """
    Decrypt a field value from the database.

    Args:
        ciphertext: The encrypted value from database (can be None or empty)

    Returns:
        str | None: Decrypted plain text value, or None if input was None

    Raises:
        FieldEncryptionError: If decryption fails

    Examples:
        >>> encrypted = encrypt_field("sensitive_data")
        >>> decrypted = decrypt_field(encrypted)
        >>> assert decrypted == "sensitive_data"
    """
    # Handle None/empty values - return as-is
    if ciphertext is None:
        return None
    if ciphertext == "":
        return ""

    # Check if field encryption is enabled
    if not settings.DATA_ENCRYPTION_ENABLED:
        logger.debug("Field encryption disabled, returning ciphertext as plaintext")
        return ciphertext

    try:
        key = _get_encryption_key()
        fernet = Fernet(key)
        decrypted_bytes = fernet.decrypt(ciphertext.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except FieldEncryptionError:
        # Re-raise our custom errors
        raise
    except Exception as e:
        raise FieldEncryptionError(f"Failed to decrypt field: {e}")


def is_encrypted_value(value: str | None) -> bool:
    """
    Check if a value appears to be encrypted (heuristic check).

    This is a lightweight check that can be used to determine if a value
    needs decryption. It checks if the value is valid base64 and has the
    expected structure of Fernet output.

    Args:
        value: The value to check

    Returns:
        bool: True if the value appears to be encrypted, False otherwise
    """
    if not value:
        return False

    try:
        # Fernet output is base64-encoded and typically has a specific structure
        # Standard Fernet token: base64(timestamp || IV || ciphertext || HMAC)
        # Minimum length is around 44 chars for empty plaintext
        if len(value) < 44:
            return False

        # Try to decode as base64
        decoded = base64.urlsafe_b64decode(value.encode('utf-8'))

        # Fernet tokens have at least: timestamp (8 bytes) + IV (16 bytes) + HMAC (32 bytes)
        # So minimum is 56 bytes decoded
        if len(decoded) < 56:
            return False

        return True
    except Exception:
        return False
