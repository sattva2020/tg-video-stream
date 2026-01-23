"""Sattva API Client."""

import logging
import time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from sattva_api.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    SattvaAPIError,
    ValidationError,
)
from sattva_api.resources import (
    APIKeysResource,
    ChannelsResource,
    PlaylistsResource,
    StreamsResource,
    WebhooksResource,
)

logger = logging.getLogger(__name__)


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

        # Initialize HTTP session with connection pooling and retry strategy
        self._client = requests.Session()
        self._client.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json",
            "User-Agent": f"SattvaPythonSDK/0.1.0",
        })

        # Configure retry strategy for connection errors
        retry_strategy = Retry(
            total=0,  # We handle retries at the API level for rate limiting
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PATCH", "DELETE", "PUT"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self._client.mount("http://", adapter)
        self._client.mount("https://", adapter)

        # Initialize resource managers
        self.streams = StreamsResource(self)
        self.playlists = PlaylistsResource(self)
        self.channels = ChannelsResource(self)
        self.webhooks = WebhooksResource(self)
        self.api_keys = APIKeysResource(self)

    def __repr__(self) -> str:
        """Return string representation of the client."""
        return f"<SattvaClient(base_url='{self.base_url}')>"

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close the HTTP client."""
        self.close()

    def close(self):
        """Close the HTTP client and release resources."""
        if self._client:
            self._client.close()
            self._client = None

    def _handle_error(self, response: requests.Response) -> None:
        """
        Handle API error responses.

        Args:
            response: The HTTP response object

        Raises:
            AuthenticationError: If authentication fails (401)
            RateLimitError: If rate limit is exceeded (429)
            NotFoundError: If resource is not found (404)
            ValidationError: If request validation fails (422)
            SattvaAPIError: For other API errors
        """
        status_code = response.status_code
        url = str(response.url)

        try:
            error_data = response.json()
            message = error_data.get("detail", error_data.get("message", "Unknown error"))
        except Exception:
            message = response.text or "Unknown error"

        logger.error(f"API error {status_code} for {url}: {message}")

        if status_code == 401:
            raise AuthenticationError(
                message="Invalid API key or unauthorized access",
                status_code=status_code,
                response=error_data if error_data else None,
            )
        elif status_code == 429:
            retry_after = response.headers.get("X-Retry-After")
            if retry_after:
                try:
                    retry_after = int(retry_after)
                except ValueError:
                    retry_after = None

            raise RateLimitError(
                message="Rate limit exceeded",
                retry_after=retry_after,
                status_code=status_code,
                response=error_data if error_data else None,
            )
        elif status_code == 404:
            raise NotFoundError(
                message=message,
                status_code=status_code,
                response=error_data if error_data else None,
            )
        elif status_code == 422:
            raise ValidationError(
                message=message,
                status_code=status_code,
                response=error_data if error_data else None,
            )
        else:
            raise SattvaAPIError(
                message=message,
                status_code=status_code,
                response=error_data if error_data else None,
            )

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        retry_count: int = 0,
    ) -> dict[str, Any] | list[Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE, etc.)
            path: API endpoint path (will be joined with base_url)
            params: Query parameters
            data: Form data
            json_data: JSON request body
            headers: Additional headers (merged with default headers)
            retry_count: Current retry count (used internally for retries)

        Returns:
            Parsed JSON response data

        Raises:
            SattvaAPIError: If the request fails after retries
        """
        if not self._client:
            raise SattvaAPIError("Client has been closed. Create a new client instance.")

        url = f"{self.base_url}/{path.lstrip('/')}"
        request_headers = {}

        # Merge additional headers with default headers
        if headers:
            request_headers.update(headers)

        logger.debug(f"{method} {url}")

        try:
            response = self._client.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_data,
                headers=request_headers if headers else None,
                timeout=self.timeout,
            )

            # Handle successful responses
            if response.status_code >= 200 and response.status_code < 300:
                # Handle empty responses (e.g., DELETE requests)
                if not response.content:
                    return {}

                return response.json()

            # Handle rate limiting with automatic retry
            if response.status_code == 429 and retry_count < self.max_retries:
                retry_after = response.headers.get("X-Retry-After")
                if retry_after:
                    try:
                        delay = float(retry_after)
                    except ValueError:
                        delay = self.retry_delay
                else:
                    delay = self.retry_delay

                retry_count += 1
                logger.warning(
                    f"Rate limited. Retrying in {delay}s (attempt {retry_count}/{self.max_retries})"
                )
                time.sleep(delay)
                return self._request(
                    method=method,
                    path=path,
                    params=params,
                    data=data,
                    json_data=json_data,
                    headers=headers,
                    retry_count=retry_count,
                )

            # Handle errors
            self._handle_error(response)

        except requests.Timeout as e:
            raise SattvaAPIError(
                message=f"Request timed out after {self.timeout}s",
                status_code=None,
            ) from e
        except requests.ConnectionError as e:
            raise SattvaAPIError(
                message="Network error occurred",
                status_code=None,
            ) from e
        except (AuthenticationError, RateLimitError, NotFoundError, ValidationError):
            # Re-raise known exceptions
            raise
        except SattvaAPIError:
            # Re-raise API errors
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            logger.exception(f"Unexpected error during request: {e}")
            raise SattvaAPIError(
                message=f"Unexpected error: {str(e)}",
                status_code=None,
            ) from e

    def get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any] | list[Any]:
        """
        Make a GET request.

        Args:
            path: API endpoint path
            params: Query parameters
            headers: Additional headers

        Returns:
            Parsed JSON response
        """
        return self._request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        data: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any] | list[Any]:
        """
        Make a POST request.

        Args:
            path: API endpoint path
            data: Form data
            json_data: JSON request body
            headers: Additional headers

        Returns:
            Parsed JSON response
        """
        return self._request("POST", path, data=data, json_data=json_data, headers=headers)

    def patch(
        self,
        path: str,
        data: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any] | list[Any]:
        """
        Make a PATCH request.

        Args:
            path: API endpoint path
            data: Form data
            json_data: JSON request body
            headers: Additional headers

        Returns:
            Parsed JSON response
        """
        return self._request("PATCH", path, data=data, json_data=json_data, headers=headers)

    def delete(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """
        Make a DELETE request.

        Args:
            path: API endpoint path
            params: Query parameters
            headers: Additional headers

        Returns:
            Parsed JSON response (empty dict for 204 No Content)
        """
        return self._request("DELETE", path, params=params, headers=headers)

    def put(
        self,
        path: str,
        data: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
    ) -> dict[str, Any] | list[Any]:
        """
        Make a PUT request.

        Args:
            path: API endpoint path
            data: Form data
            json_data: JSON request body
            headers: Additional headers

        Returns:
            Parsed JSON response
        """
        return self._request("PUT", path, data=data, json_data=json_data, headers=headers)
