"""Sattva API Client."""

from typing import Optional


class SattvaClient:
    """Client for interacting with the Sattva API."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.sattva.io/api/v1",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the Sattva API client.

        Args:
            api_key: Your Sattva API key
            base_url: Base URL for the API (default: https://api.sattva.io/api/v1)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retries for rate-limited requests (default: 3)
            retry_delay: Delay between retries in seconds (default: 1.0)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Resource attributes will be populated in subtask-5-2
        self.streams = None
        self.playlists = None
        self.channels = None
        self.webhooks = None
        self.api_keys = None

    def __repr__(self) -> str:
        return f"<SattvaClient(base_url='{self.base_url}')>"
