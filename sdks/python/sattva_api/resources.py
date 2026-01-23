"""Resource classes for Sattva API SDK."""

import logging
from typing import Any, Optional
import uuid

logger = logging.getLogger(__name__)


class BaseResource:
    """Base class for API resources."""

    def __init__(self, client):
        """
        Initialize the resource with a client instance.

        Args:
            client: SattvaClient instance
        """
        self.client = client


class ChannelsResource(BaseResource):
    """Resource for managing channels."""

    def list(self) -> list[dict[str, Any]]:
        """
        List all channels.

        Returns:
            List of channel objects
        """
        logger.debug("Listing channels")
        response = self.client.get("/channels/")
        return response

    def get(self, channel_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Get a specific channel by ID.

        Args:
            channel_id: Channel UUID

        Returns:
            Channel object
        """
        logger.debug(f"Getting channel {channel_id}")
        response = self.client.get(f"/channels/{channel_id}")
        return response

    def create(
        self,
        account_id: str | uuid.UUID,
        chat_id: int,
        name: str,
        chat_username: Optional[str] = None,
        ffmpeg_args: Optional[str] = None,
        video_quality: str = "best",
        stream_type: str = "video",
        playlist_id: Optional[str | uuid.UUID] = None,
    ) -> dict[str, Any]:
        """
        Create a new channel.

        Args:
            account_id: Telegram account UUID
            chat_id: Telegram chat ID
            name: Channel name
            chat_username: Optional Telegram username
            ffmpeg_args: Optional FFmpeg arguments
            video_quality: Video quality setting (default: "best")
            stream_type: Stream type "video" or "audio" (default: "video")
            playlist_id: Optional playlist UUID to associate

        Returns:
            Created channel object
        """
        logger.debug(f"Creating channel {name}")
        data = {
            "account_id": str(account_id),
            "chat_id": chat_id,
            "name": name,
            "video_quality": video_quality,
            "stream_type": stream_type,
        }
        if chat_username:
            data["chat_username"] = chat_username
        if ffmpeg_args:
            data["ffmpeg_args"] = ffmpeg_args
        if playlist_id:
            data["playlist_id"] = str(playlist_id)

        response = self.client.post("/channels/", json_data=data)
        return response

    def update(
        self,
        channel_id: str | uuid.UUID,
        name: Optional[str] = None,
        ffmpeg_args: Optional[str] = None,
        video_quality: Optional[str] = None,
        stream_type: Optional[str] = None,
        placeholder_image: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Update a channel.

        Args:
            channel_id: Channel UUID
            name: Optional new name
            ffmpeg_args: Optional FFmpeg arguments
            video_quality: Optional video quality
            stream_type: Optional stream type
            placeholder_image: Optional placeholder image URL

        Returns:
            Updated channel object
        """
        logger.debug(f"Updating channel {channel_id}")
        data = {}
        if name is not None:
            data["name"] = name
        if ffmpeg_args is not None:
            data["ffmpeg_args"] = ffmpeg_args
        if video_quality is not None:
            data["video_quality"] = video_quality
        if stream_type is not None:
            data["stream_type"] = stream_type
        if placeholder_image is not None:
            data["placeholder_image"] = placeholder_image

        response = self.client.patch(f"/channels/{channel_id}", json_data=data)
        return response

    def delete(self, channel_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Delete a channel.

        Args:
            channel_id: Channel UUID

        Returns:
            Deletion response
        """
        logger.debug(f"Deleting channel {channel_id}")
        response = self.client.delete(f"/channels/{channel_id}")
        return response

    def start(self, channel_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Start streaming to a channel.

        Args:
            channel_id: Channel UUID

        Returns:
            Status response
        """
        logger.debug(f"Starting channel {channel_id}")
        response = self.client.post(f"/channels/{channel_id}/start")
        return response

    def stop(self, channel_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Stop streaming to a channel.

        Args:
            channel_id: Channel UUID

        Returns:
            Status response
        """
        logger.debug(f"Stopping channel {channel_id}")
        response = self.client.post(f"/channels/{channel_id}/stop")
        return response

    def restart(self, channel_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Restart streaming to a channel.

        Args:
            channel_id: Channel UUID

        Returns:
            Status response
        """
        logger.debug(f"Restarting channel {channel_id}")
        response = self.client.post(f"/channels/{channel_id}/restart")
        return response


class StreamsResource(BaseResource):
    """Resource for managing streams (alias for channels)."""

    def __init__(self, client):
        """
        Initialize the streams resource.

        Args:
            client: SattvaClient instance
        """
        super().__init__(client)
        # Streams are managed through channels
        self._channels = ChannelsResource(client)

    def list(self) -> list[dict[str, Any]]:
        """
        List all streams (channels).

        Returns:
            List of stream objects
        """
        return self._channels.list()

    def get(self, stream_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Get a specific stream by ID.

        Args:
            stream_id: Stream (channel) UUID

        Returns:
            Stream object
        """
        return self._channels.get(stream_id)

    def start(self, stream_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Start a stream.

        Args:
            stream_id: Stream (channel) UUID

        Returns:
            Status response
        """
        return self._channels.start(stream_id)

    def stop(self, stream_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Stop a stream.

        Args:
            stream_id: Stream (channel) UUID

        Returns:
            Status response
        """
        return self._channels.stop(stream_id)

    def restart(self, stream_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Restart a stream.

        Args:
            stream_id: Stream (channel) UUID

        Returns:
            Status response
        """
        return self._channels.restart(stream_id)


class PlaylistsResource(BaseResource):
    """Resource for managing playlist items."""

    def list(self, channel_id: Optional[str | uuid.UUID] = None) -> list[dict[str, Any]]:
        """
        List playlist items.

        Args:
            channel_id: Optional channel UUID to filter by

        Returns:
            List of playlist items
        """
        logger.debug("Listing playlist items")
        params = {}
        if channel_id:
            params["channel_id"] = str(channel_id)

        response = self.client.get("/playlist/", params=params)
        return response

    def get(self, item_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Get a specific playlist item.

        Args:
            item_id: Playlist item UUID

        Returns:
            Playlist item object
        """
        logger.debug(f"Getting playlist item {item_id}")
        response = self.client.get(f"/playlist/{item_id}")
        return response

    def create(
        self,
        url: str,
        title: Optional[str] = None,
        type: str = "youtube",
        duration: Optional[int] = None,
        fetch_metadata: bool = True,
    ) -> dict[str, Any]:
        """
        Add an item to the playlist.

        Args:
            url: Media URL (YouTube, local file, or stream URL)
            title: Optional title
            type: Media type - "youtube", "local", or "stream" (default: "youtube")
            duration: Optional duration in seconds
            fetch_metadata: Whether to fetch metadata asynchronously (default: True)

        Returns:
            Created playlist item
        """
        logger.debug(f"Adding playlist item: {url}")
        data = {
            "url": url,
            "type": type,
            "fetch_metadata": fetch_metadata,
        }
        if title:
            data["title"] = title
        if duration is not None:
            data["duration"] = duration

        response = self.client.post("/playlist/", json_data=data)
        return response

    def update(
        self,
        item_id: str | uuid.UUID,
        url: Optional[str] = None,
        title: Optional[str] = None,
        type: Optional[str] = None,
        duration: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Update a playlist item.

        Args:
            item_id: Playlist item UUID
            url: Optional new URL
            title: Optional new title
            type: Optional new media type
            duration: Optional new duration

        Returns:
            Updated playlist item
        """
        logger.debug(f"Updating playlist item {item_id}")
        data = {}
        if url is not None:
            data["url"] = url
        if title is not None:
            data["title"] = title
        if type is not None:
            data["type"] = type
        if duration is not None:
            data["duration"] = duration

        response = self.client.patch(f"/playlist/{item_id}", json_data=data)
        return response

    def delete(self, item_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Delete a playlist item.

        Args:
            item_id: Playlist item UUID

        Returns:
            Deletion response
        """
        logger.debug(f"Deleting playlist item {item_id}")
        response = self.client.delete(f"/playlist/{item_id}")
        return response

    def reorder(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Reorder playlist items.

        Args:
            items: List of {"id": uuid, "position": int} dicts

        Returns:
            Reorder response
        """
        logger.debug(f"Reordering {len(items)} playlist items")
        data = {"items": items}
        response = self.client.post("/playlist/reorder", json_data=data)
        return response

    def update_status(
        self,
        item_id: str | uuid.UUID,
        status: str,
        duration: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Update the status of a playlist item.

        Args:
            item_id: Playlist item UUID
            status: New status - "playing", "queued", or "error"
            duration: Optional duration in seconds

        Returns:
            Updated playlist item
        """
        logger.debug(f"Updating status for playlist item {item_id} to {status}")
        data = {"status": status}
        if duration is not None:
            data["duration"] = duration

        response = self.client.patch(f"/playlist/{item_id}/status", json_data=data)
        return response


class WebhooksResource(BaseResource):
    """Resource for managing webhook subscriptions."""

    def list(self) -> list[dict[str, Any]]:
        """
        List all webhook subscriptions.

        Returns:
            List of webhook objects (secret not included)
        """
        logger.debug("Listing webhooks")
        response = self.client.get("/webhooks/")
        return response

    def get(self, webhook_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Get a specific webhook.

        Args:
            webhook_id: Webhook UUID

        Returns:
            Webhook object (secret not included)
        """
        logger.debug(f"Getting webhook {webhook_id}")
        response = self.client.get(f"/webhooks/{webhook_id}")
        return response

    def create(
        self,
        url: str,
        event_types: list[str],
        secret: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new webhook subscription.

        Args:
            url: Webhook URL to receive events
            event_types: List of event types to subscribe to
                         (e.g., ["stream.started", "stream.stopped"])
            secret: Optional secret for signature verification
                    (if not provided, one will be generated)

        Returns:
            Created webhook object with secret (only time secret is returned)
        """
        logger.debug(f"Creating webhook for {url}")
        data = {
            "url": url,
            "event_types": event_types,
        }
        if secret:
            data["secret"] = secret

        response = self.client.post("/webhooks/", json_data=data)
        return response

    def update(
        self,
        webhook_id: str | uuid.UUID,
        url: Optional[str] = None,
        event_types: Optional[list[str]] = None,
        is_active: Optional[bool] = None,
    ) -> dict[str, Any]:
        """
        Update a webhook subscription.

        Args:
            webhook_id: Webhook UUID
            url: Optional new URL
            event_types: Optional new list of event types
            is_active: Optional active status

        Returns:
            Updated webhook object
        """
        logger.debug(f"Updating webhook {webhook_id}")
        data = {}
        if url is not None:
            data["url"] = url
        if event_types is not None:
            data["event_types"] = event_types
        if is_active is not None:
            data["is_active"] = is_active

        response = self.client.patch(f"/webhooks/{webhook_id}", json_data=data)
        return response

    def delete(self, webhook_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Delete a webhook subscription.

        Args:
            webhook_id: Webhook UUID

        Returns:
            Deletion response
        """
        logger.debug(f"Deleting webhook {webhook_id}")
        response = self.client.delete(f"/webhooks/{webhook_id}")
        return response

    def test(self, webhook_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Send a test event to a webhook.

        Args:
            webhook_id: Webhook UUID

        Returns:
            Test result
        """
        logger.debug(f"Testing webhook {webhook_id}")
        response = self.client.post(f"/webhooks/{webhook_id}/test")
        return response

    def rotate_secret(self, webhook_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Rotate a webhook's secret.

        Args:
            webhook_id: Webhook UUID

        Returns:
            Updated webhook object with new secret (only time secret is returned)
        """
        logger.debug(f"Rotating secret for webhook {webhook_id}")
        response = self.client.post(f"/webhooks/{webhook_id}/rotate-secret")
        return response

    def list_events(
        self,
        webhook_id: str | uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        List delivery events for a webhook.

        Args:
            webhook_id: Webhook UUID
            limit: Maximum number of events to return (default: 100)
            offset: Number of events to skip (default: 0)

        Returns:
            List of webhook event objects
        """
        logger.debug(f"Listing events for webhook {webhook_id}")
        params = {"limit": limit, "offset": offset}
        response = self.client.get(f"/webhooks/{webhook_id}/events", params=params)
        return response


class APIKeysResource(BaseResource):
    """Resource for managing API keys."""

    def list(self) -> list[dict[str, Any]]:
        """
        List all API keys.

        Returns:
            List of API key objects (key value not included)
        """
        logger.debug("Listing API keys")
        response = self.client.get("/keys/")
        return response

    def get(self, key_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Get a specific API key.

        Args:
            key_id: API key UUID

        Returns:
            API key object (key value not included)
        """
        logger.debug(f"Getting API key {key_id}")
        response = self.client.get(f"/keys/{key_id}")
        return response

    def create(
        self,
        name: str,
        scopes: list[str],
        rate_limit: Optional[int] = None,
        expires_at: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new API key.

        Args:
            name: Key name/description
            scopes: List of permission scopes
                   (e.g., ["read:streams", "write:streams"])
            rate_limit: Optional requests per minute limit
            expires_at: Optional expiration date (ISO 8601 format)

        Returns:
            Created API key object with key value (only time key is returned)
        """
        logger.debug(f"Creating API key: {name}")
        data = {
            "name": name,
            "scopes": scopes,
        }
        if rate_limit is not None:
            data["rate_limit"] = rate_limit
        if expires_at:
            data["expires_at"] = expires_at

        response = self.client.post("/keys/", json_data=data)
        return response

    def update(
        self,
        key_id: str | uuid.UUID,
        name: Optional[str] = None,
        rate_limit: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> dict[str, Any]:
        """
        Update an API key.

        Args:
            key_id: API key UUID
            name: Optional new name
            rate_limit: Optional new rate limit
            is_active: Optional active status

        Returns:
            Updated API key object
        """
        logger.debug(f"Updating API key {key_id}")
        data = {}
        if name is not None:
            data["name"] = name
        if rate_limit is not None:
            data["rate_limit"] = rate_limit
        if is_active is not None:
            data["is_active"] = is_active

        response = self.client.patch(f"/keys/{key_id}", json_data=data)
        return response

    def delete(self, key_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Delete an API key.

        Args:
            key_id: API key UUID

        Returns:
            Deletion response
        """
        logger.debug(f"Deleting API key {key_id}")
        response = self.client.delete(f"/keys/{key_id}")
        return response

    def revoke(self, key_id: str | uuid.UUID) -> dict[str, Any]:
        """
        Revoke an API key (alias for delete).

        Args:
            key_id: API key UUID

        Returns:
            Revocation response
        """
        logger.debug(f"Revoking API key {key_id}")
        response = self.client.post(f"/keys/{key_id}/revoke")
        return response
