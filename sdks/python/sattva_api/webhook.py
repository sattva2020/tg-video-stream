"""Webhook signature verification utilities."""

import hashlib
import hmac


def verify_webhook_signature(
    payload: bytes | str, signature: str, secret: str
) -> bool:
    """
    Verify a webhook signature.

    Args:
        payload: The raw webhook payload (bytes or string)
        signature: The signature from the X-Sattva-Signature header (format: sha256=...)
        secret: Your webhook secret

    Returns:
        True if the signature is valid, False otherwise

    Example:
        >>> import json
        >>> payload = json.dumps({"event": "stream.started"})
        >>> signature = "sha256=abc123..."
        >>> is_valid = verify_webhook_signature(payload, signature, "my-secret")
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    # Extract the signature hash (remove 'sha256=' prefix if present)
    if signature.startswith("sha256="):
        signature_hash = signature[7:]  # Remove 'sha256=' prefix
    else:
        signature_hash = signature

    # Compute HMAC-SHA256
    expected_signature = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_signature, signature_hash)
