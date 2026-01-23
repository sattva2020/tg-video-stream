# Multi-Platform Redis Commands

This document describes the multi-platform streaming commands supported by the Redis command handler.

## Command Format

All commands are JSON messages published to the `stream:control` Redis channel:

```json
{
  "action": "command_name",
  "channel_id": "channel_uuid",
  ... additional fields
}
```

## Available Commands

### add_platform
Add a platform destination to a channel.

```json
{
  "action": "add_platform",
  "channel_id": "channel_uuid",
  "platform_config": {
    "platform_id": "platform_uuid",
    "platform_type": "youtube|twitch|custom",
    "rtmp_url": "rtmp://...",
    "stream_key": "stream_key",
    "video_quality": "720p",
    "enabled": true
  }
}
```

### remove_platform
Remove a platform destination from a channel.

```json
{
  "action": "remove_platform",
  "channel_id": "channel_uuid",
  "platform_id": "platform_uuid"
}
```

### start_platform
Start streaming to a specific platform.

```json
{
  "action": "start_platform",
  "channel_id": "channel_uuid",
  "platform_id": "platform_uuid",
  "source_url": "http://source_url"  // Optional
}
```

### stop_platform
Stop streaming to a specific platform.

```json
{
  "action": "stop_platform",
  "channel_id": "channel_uuid",
  "platform_id": "platform_uuid"
}
```

### start_all_platforms
Start streaming to all configured platforms for a channel.

```json
{
  "action": "start_all_platforms",
  "channel_id": "channel_uuid",
  "source_url": "http://source_url"
}
```

### stop_all_platforms
Stop streaming to all platforms for a channel.

```json
{
  "action": "stop_all_platforms",
  "channel_id": "channel_uuid"
}
```

### get_platform_status
Get status of a specific platform.

```json
{
  "action": "get_platform_status",
  "channel_id": "channel_uuid",
  "platform_id": "platform_uuid"
}
```

### get_all_platform_statuses
Get status of all platforms for a channel.

```json
{
  "action": "get_all_platform_statuses",
  "channel_id": "channel_uuid"
}
```

## Response Format

Status updates are published to Redis keys with the pattern:
- `stream:status:{channel_id}` - Channel-level status
- Platform-specific status is included in the `extra` field

Example status:
```json
{
  "status": "running",
  "updated_at": "2024-01-23T10:00:00Z",
  "extra": {
    "platform_statuses": [...],
    "platform_count": 3
  }
}
```

## Callback Registration

The streamer service must register callbacks for these commands:

```python
handler = RedisCommandHandler()
handler.on_add_platform = my_add_platform_callback
handler.on_remove_platform = my_remove_platform_callback
handler.on_start_platform = my_start_platform_callback
handler.on_stop_platform = my_stop_platform_callback
handler.on_start_all_platforms = my_start_all_platforms_callback
handler.on_stop_all_platforms = my_stop_all_platforms_callback
handler.on_get_platform_status = my_get_platform_status_callback
handler.on_get_all_platform_statuses = my_get_all_platform_statuses_callback
```
