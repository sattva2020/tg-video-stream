from cryptography.fernet import Fernet
from src.core.config import settings
import base64

class EncryptionService:
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

# Singleton instance
encryption_service = EncryptionService()
