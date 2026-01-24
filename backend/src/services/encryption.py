from cryptography.fernet import Fernet
from src.core.config import settings
import base64
import re

class EncryptionService:
    # Prefix to identify TOTP-encrypted data (separate encryption context)
    TOTP_PREFIX = "totp:"

    def __init__(self):
        key = settings.SESSION_ENCRYPTION_KEY
        # Ensure key is bytes and valid base64
        if isinstance(key, str):
            key = key.encode()

        # Fernet requires a 32-byte url-safe base64-encoded key.
        # If the user provided a raw string or something else, we might need to handle it.
        # For now, we assume the user followed instructions (openssl rand -base64 32).
        try:
            self.fernet = Fernet(key)
        except ValueError:
            # Fallback or error if key is invalid format
            # In production, this should crash to alert the admin.
            raise ValueError("Invalid SESSION_ENCRYPTION_KEY. Must be 32 url-safe base64-encoded bytes.")

    def encrypt(self, data: str) -> str:
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, token: str) -> str:
        if not token:
            return ""
        return self.fernet.decrypt(token.encode()).decode()

    def encrypt_totp_secret(self, secret: str) -> str:
        """
        Encrypt a TOTP secret for secure storage.

        Args:
            secret: TOTP secret (typically base32 encoded)

        Returns:
            Encrypted token with TOTP prefix

        Raises:
            ValueError: If secret is invalid or empty
        """
        if not secret:
            raise ValueError("TOTP secret cannot be empty")

        # Basic validation: TOTP secrets should be base32 (alphanumeric + padding)
        # Typical length is 16-32 characters for base32
        # Base32 uses uppercase A-Z and digits 2-7 (RFC 4648)
        stripped_secret = secret.strip()
        if not re.match(r'^[A-Z2-7]+=*$', stripped_secret):
            raise ValueError("Invalid TOTP secret format. Must be base32 encoded (uppercase A-Z, digits 2-7).")

        # Encrypt with prefix to identify as TOTP data (separate context)
        encrypted = self.encrypt(f"{self.TOTP_PREFIX}{stripped_secret}")
        return encrypted

    def decrypt_totp_secret(self, encrypted_secret: str) -> str:
        """
        Decrypt a TOTP secret from storage.

        Args:
            encrypted_secret: Encrypted TOTP token

        Returns:
            Decrypted TOTP secret (without prefix)

        Raises:
            ValueError: If token is invalid, empty, or not TOTP data
        """
        if not encrypted_secret:
            raise ValueError("Encrypted TOTP secret cannot be empty")

        try:
            decrypted = self.decrypt(encrypted_secret)

            # Validate that this is TOTP data (has prefix)
            if not decrypted.startswith(self.TOTP_PREFIX):
                raise ValueError("Invalid encrypted TOTP secret: missing prefix")

            # Return secret without prefix
            secret = decrypted[len(self.TOTP_PREFIX):]

            # Validate the decrypted secret format
            if not secret or not re.match(r'^[A-Z2-7]+=*$', secret):
                raise ValueError("Decrypted data is not a valid TOTP secret")

            return secret

        except Exception as e:
            # Re-raise with clearer context
            raise ValueError(f"Failed to decrypt TOTP secret: {str(e)}") from e

# Singleton instance
encryption_service = EncryptionService()
