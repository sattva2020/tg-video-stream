# AyuGram Python SDK

Async Python client for AyuGram JSON-RPC API with a PyTgCalls-compatible interface. Provides seamless integration with the Sattva streaming platform, enabling session management, voice/video call operations, and stream control.

## Features

- **PyTgCalls-Compatible API**: Drop-in replacement for PyTgCalls with the same method signatures
- **Async/Await**: Fully async implementation using `asyncio` and `aiohttp`
- **Session Management**: Create, load, save, and delete sessions with optional Redis caching
- **Voice/Video Calls**: Join/leave voice chats, play audio/video streams
- **Stream Control**: Pause, resume, seek, volume control
- **Event Handling**: Register listeners for call and stream events
- **Type Safety**: Full type hints with Pydantic validation
- **Error Handling**: Comprehensive exception hierarchy

## Installation

### From PyPI (when published)

```bash
pip install ayugram-python
```

### From Source

```bash
git clone https://github.com/sattva-ai/ayugram-python.git
cd ayugram-python
pip install -e .
```

### With Optional Dependencies

```bash
# Install with Redis support for session caching
pip install -e ".[redis]"

# Install with development dependencies
pip install -e ".[dev]"
```

### Requirements

- Python 3.11 or higher
- AyuGram headless engine (or mock JSON-RPC server for development)
- Pyrogram or Telethon client

## Quickstart

### Basic Usage

```python
import asyncio
from ayugram import AyuGramClient
from pyrogram import Client
from ayugram.types import AudioPiped

# Create Pyrogram client
app = Client(
    "my_account",
    api_id=12345678,
    api_hash="your_api_hash"
)

# Create AyuGram client
ayugram = AyuGramClient(app)

async def main():
    # Start the client
    await ayugram.start()

    # Join a voice chat
    chat_id = -1001234567890  # Channel or group ID
    stream = AudioPiped("path/to/audio.mp3")
    await ayugram.join_group_call(chat_id, stream)

    # Keep client running to handle events
    await ayugram.idle()

if __name__ == "__main__":
    asyncio.run(main())
```

### Session Management

```python
import asyncio
from ayugram import AyuGramClient
from pyrogram import Client

app = Client("my_account", api_id=12345678, api_hash="your_api_hash")
ayugram = AyuGramClient(app)

async def main():
    # Create new session with phone number
    async def on_code(code):
        print(f"Received code: {code}")

    await ayugram.create_session(
        phone_number="+1234567890",
        on_code_callback=on_code
    )

    # Session is automatically saved
    # Next time, you can load it:
    # await ayugram.load_session("my_account.session")

    await ayugram.start()
    # ... use the client
    await ayugram.stop()

asyncio.run(main())
```

### Stream Control

```python
import asyncio
from ayugram import AyuGramClient
from ayugram.types import AudioVideoPiped
from pyrogram import Client

app = Client("my_account", api_id=12345678, api_hash="your_api_hash")
ayugram = AyuGramClient(app)

async def main():
    await ayugram.start()

    chat_id = -1001234567890
    stream = AudioVideoPiped(
        "path/to/video.mp4",
        audio_parameters=HighQualityAudio(),
        video_parameters=HighQualityVideo()
    )

    # Join and play
    await ayugram.join_group_call(chat_id, stream)

    # Pause playback
    await ayugram.pause(chat_id)

    # Resume playback
    await ayugram.resume(chat_id)

    # Change volume (0-100)
    await ayugram.set_volume(chat_id, 75)

    # Get current state
    state = await ayugram.get_state(chat_id)
    print(f"Playing: {state.is_playing}, Position: {state.position_ms}ms")

    # Leave call
    await ayugram.leave_group_call(chat_id)

asyncio.run(main())
```

### Event Handling

```python
import asyncio
from ayugram import AyuGramClient
from pyrogram import Client

app = Client("my_account", api_id=12345678, api_hash="your_api_hash")
ayugram = AyuGramClient(app)

# Register event listeners
@ayugram.on('call_joined')
async def on_call_joined(chat_id: int):
    print(f"Joined call in chat {chat_id}")

@ayugram.on('stream_ended')
async def on_stream_ended(chat_id: int):
    print(f"Stream ended in chat {chat_id}")
    # Auto-play next track from queue
    await play_next_track(chat_id)

async def main():
    await ayugram.start()
    await ayugram.idle()

asyncio.run(main())
```

## API Reference

### AyuGramClient

Main client class for interacting with AyuGram JSON-RPC API.

#### Constructor

```python
AyuGramClient(
    client: Union[Pyrogram.Client, Telethon.Client],
    engine_url: str = None,
    session_dir: str = "./sessions"
)
```

**Parameters:**
- `client` - Pyrogram or Telethon client instance
- `engine_url` - AyuGram engine URL (default: from `AYUGRAM_ENGINE_URL` env var or `http://localhost:8080/jsonrpc`)
- `session_dir` - Directory for session files (default: from `AYUGRAM_SESSION_DIR` env var or `./sessions`)

#### Lifecycle Methods

##### `start()`
Initialize connection to AyuGram engine.

```python
await ayugram.start()
```

**Returns:** `None`

**Raises:**
- `ConnectionError` - If engine is unreachable
- `AuthenticationError` - If session is invalid

##### `stop()`
Gracefully shutdown the client.

```python
await ayugram.stop()
```

**Returns:** `None`

##### `idle()`
Keep client running and handle incoming events.

```python
await ayugram.idle()
```

**Returns:** `None` (runs indefinitely until cancelled)

**Note:** This method is required for event handling and keeps the client alive.

#### Session Management

##### `create_session()`
Create a new session with phone number authentication.

```python
await ayugram.create_session(
    phone_number: str,
    on_code_callback: Callable[[str], Awaitable[None]],
    password_callback: Callable[[str], Awaitable[None]] = None
)
```

**Parameters:**
- `phone_number` - Phone number in international format (e.g., `+1234567890`)
- `on_code_callback` - Async callback that receives OTP code
- `password_callback` - Optional async callback for 2FA password

**Returns:** `None`

**Raises:**
- `AuthenticationError` - If authentication fails
- `TimeoutError` - If OTP entry times out

##### `load_session()`
Load an existing session from disk.

```python
await ayugram.load_session(session_file: str)
```

**Parameters:**
- `session_file` - Path to session file

**Returns:** `None`

##### `save_session()`
Save current session to disk.

```python
await ayugram.save_session(path: str = None)
```

**Parameters:**
- `path` - Optional custom path (default: auto-generated)

**Returns:** `None`

##### `delete_session()`
Delete current session.

```python
await ayugram.delete_session()
```

**Returns:** `None`

#### Voice/Video Call Methods

##### `join_group_call()`
Join a voice chat and start streaming.

```python
await ayugram.join_group_call(
    chat_id: Union[int, str],
    stream: Union[AudioPiped, AudioVideoPiped]
)
```

**Parameters:**
- `chat_id` - Channel or group ID
- `stream` - Stream object (AudioPiped or AudioVideoPiped)

**Returns:** `None`

**Raises:**
- `CallError` - If join fails
- `AlreadyJoinedError` - If already in call

##### `leave_group_call()`
Leave a voice chat.

```python
await ayugram.leave_group_call(chat_id: Union[int, str])
```

**Parameters:**
- `chat_id` - Channel or group ID

**Returns:** `None`

#### Stream Control Methods

##### `play()`
Play a stream in an active call.

```python
await ayugram.play(
    chat_id: Union[int, str],
    stream: Union[AudioPiped, AudioVideoPiped]
)
```

**Parameters:**
- `chat_id` - Channel or group ID
- `stream` - Stream object

**Returns:** `None`

##### `pause()`
Pause playback in a call.

```python
await ayugram.pause(chat_id: Union[int, str])
```

**Parameters:**
- `chat_id` - Channel or group ID

**Returns:** `None`

##### `resume()`
Resume paused playback.

```python
await ayugram.resume(chat_id: Union[int, str])
```

**Parameters:**
- `chat_id` - Channel or group ID

**Returns:** `None`

##### `seek_stream()`
Seek to a specific position.

```python
await ayugram.seek_stream(chat_id: Union[int, str], position_seconds: int)
```

**Parameters:**
- `chat_id` - Channel or group ID
- `position_seconds` - Target position in seconds

**Returns:** `None`

**Example:**
```python
await ayugram.seek_stream(chat_id, 60)  # Seek to 1 minute
```

**Note:** Only supported if tg-engine implements seek functionality.

##### `rewind_stream()`
Rewind stream by N seconds.

```python
await ayugram.rewind_stream(chat_id: Union[int, str], seconds: int)
```

**Parameters:**
- `chat_id` - Channel or group ID
- `seconds` - Number of seconds to rewind (must be positive)

**Returns:** `None`

**Example:**
```python
await ayugram.rewind_stream(chat_id, 10)  # Rewind 10 seconds
```

##### `forward_stream()`
Forward stream by N seconds.

```python
await ayugram.forward_stream(chat_id: Union[int, str], seconds: int)
```

**Parameters:**
- `chat_id` - Channel or group ID
- `seconds` - Number of seconds to forward (must be positive)

**Returns:** `None`

**Example:**
```python
await ayugram.forward_stream(chat_id, 30)  # Forward 30 seconds
```

##### `set_volume()`
Set playback volume.

```python
await ayugram.set_volume(chat_id: Union[int, str], volume: float)
```

**Parameters:**
- `chat_id` - Channel or group ID
- `volume` - Volume level (0-100 or 0.0-1.0 range)

**Returns:** `None`

**Example:**
```python
# Both formats work
await ayugram.set_volume(chat_id, 50)   # 50% (0-100 range)
await ayugram.set_volume(chat_id, 0.5)  # 50% (0.0-1.0 range)
```

##### `set_speed()`
Set playback speed.

```python
await ayugram.set_speed(chat_id: Union[int, str], speed: float)
```

**Parameters:**
- `chat_id` - Channel or group ID
- `speed` - Speed multiplier (0.5 to 2.0, where 1.0 is normal speed)

**Returns:** `None`

**Example:**
```python
await ayugram.set_speed(chat_id, 1.5)  # Set to 1.5x speed
await ayugram.set_speed(chat_id, 0.75) # Set to 0.75x speed
```

##### `get_stream_state()`
Get current playback state.

```python
state = ayugram.get_stream_state(chat_id: Union[int, str])
```

**Parameters:**
- `chat_id` - Channel or group ID

**Returns:** `StreamState` object or `None` if no state exists

**StreamState Fields:**
- `position_ms: int` - Current playback position in milliseconds
- `duration_ms: int` - Total stream duration in milliseconds (0 if unknown)
- `is_playing: bool` - Whether the stream is currently playing
- `is_paused: bool` - Whether the stream is currently paused
- `volume: float` - Volume level (0.0 to 1.0)
- `speed: float` - Playback speed multiplier (0.5 to 2.0)
- `updated_at: datetime` - Timestamp of last state update

**Example:**
```python
state = ayugram.get_stream_state(chat_id)
if state:
    print(f"Position: {state.position_ms // 1000}s")
    print(f"Volume: {state.volume * 100}%")
    print(f"Speed: {state.speed}x")
```

##### `get_position()`
Get current playback position in seconds.

```python
position = ayugram.get_position(chat_id: Union[int, str])
```

**Parameters:**
- `chat_id` - Channel or group ID

**Returns:** `int` - Current position in seconds, 0 if no state exists

**Example:**
```python
position = ayugram.get_position(chat_id)
print(f"Current position: {position}s")
```

##### `get_volume()`
Get current volume level.

```python
volume = ayugram.get_volume(chat_id: Union[int, str])
```

**Parameters:**
- `chat_id` - Channel or group ID

**Returns:** `float` - Volume level (0.0 to 1.0), 1.0 if no state exists

**Example:**
```python
volume = ayugram.get_volume(chat_id)
print(f"Volume: {volume * 100:.0f}%")
```

#### Event Handling

##### `on()`
Register an event listener.

```python
@ayugram.on('event_name')
async def handler(data):
    pass
```

**Supported Events:**
- `call_joined` - Fired when joining a voice chat
- `call_left` - Fired when leaving a voice chat
- `stream_ended` - Fired when stream finishes
- `connection_state_changed` - Fired when connection state changes

##### `remove_listener()`
Remove an event listener.

```python
ayugram.remove_listener('event_name', handler)
```

#### Properties

##### `is_started`

Check if the client is started.

```python
if ayugram.is_started:
    print("Client is running")
```

**Returns:** `bool` - True if the client is started, False otherwise

##### `active_calls`

Get all active group calls.

```python
calls = ayugram.active_calls
print(f"Active calls: {len(calls)}")
```

**Returns:** `dict` - Dictionary mapping chat IDs to their call info

##### `event_listeners`

Get all registered event listeners.

```python
listeners = ayugram.event_listeners
print(f"Registered events: {list(listeners.keys())}")
```

**Returns:** `dict` - Dictionary mapping event names to lists of callbacks

### SessionManager

Manages AyuGram sessions with file system storage and optional Redis caching. This class can be used independently for advanced session management scenarios.

```python
from ayugram.session import SessionManager

manager = SessionManager("./sessions", redis_url="redis://localhost:6379")
```

#### Constructor

```python
SessionManager(
    session_dir: str = "./sessions",
    redis_url: Optional[str] = None,
    redis_ttl: int = 3600
)
```

**Parameters:**
- `session_dir` - Directory path for storing session files (default: "./sessions")
- `redis_url` - Optional Redis URL for caching (default: None)
- `redis_ttl` - Redis TTL for cached sessions in seconds (default: 3600)

#### Methods

##### `create_session()`

Create a new session via authentication flow.

```python
session_data = await manager.create_session(
    phone_number: str,
    on_code_callback: Callable,
    rpc_client: Optional[Any] = None
)
```

**Returns:** Dictionary with session data (phone, user_id, auth_key, created_at, last_used)

##### `load_session()`

Load an existing session from Redis cache or file system.

```python
session_data = await manager.load_session(session_name: str)
```

**Returns:** Dictionary containing session data

##### `save_session()`

Save session data to file system.

```python
await manager.save_session(
    session_name: str,
    session_data: Dict[str, Any]
)
```

**Returns:** `None`

##### `delete_session()`

Delete a session from file system and cache.

```python
success = await manager.delete_session(session_name: str)
```

**Returns:** `bool` - True if session was deleted, False if it didn't exist

##### `list_sessions()`

List all available sessions in the session directory.

```python
sessions = manager.list_sessions()
```

**Returns:** List of session names (without .json extension)

##### `session_exists()`

Check if a session exists in file system or cache.

```python
exists = await manager.session_exists(session_name: str)
```

**Returns:** `bool` - True if session exists, False otherwise

### Stream Types

#### AudioPiped

Audio-only stream.

```python
from ayugram.types import AudioPiped

stream = AudioPiped(
    path="path/to/audio.mp3",
    audio_parameters=HighQualityAudio()
)
```

**Parameters:**
- `data_path` (str) - Path to audio file or URL (required)
- `audio_parameters` (HighQualityAudio, optional) - Audio quality parameters
- `additional_ffmpeg_parameters` (List[str], optional) - Additional FFmpeg command-line arguments

**Example:**
```python
# Basic audio stream
stream = AudioPiped("https://example.com/audio.mp3")

# With custom FFmpeg parameters
stream = AudioPiped(
    "https://example.com/audio.mp3",
    additional_ffmpeg_parameters=["-re", "-bufsize", "96000k"]
)
```

#### AudioVideoPiped

Audio and video stream.

```python
from ayugram.types import AudioVideoPiped, HighQualityAudio, HighQualityVideo

stream = AudioVideoPiped(
    path="path/to/video.mp4",
    audio_parameters=HighQualityAudio(),
    video_parameters=HighQualityVideo()
)
```

**Parameters:**
- `data_path` (str) - Path to video file or URL (required)
- `audio_parameters` (HighQualityAudio, optional) - Audio quality parameters
- `video_parameters` (HighQualityVideo, optional) - Video quality parameters
- `additional_ffmpeg_parameters` (List[str], optional) - Additional FFmpeg command-line arguments

**Example:**
```python
# Basic video stream
stream = AudioVideoPiped("https://example.com/video.mp4")

# With custom FFmpeg parameters
stream = AudioVideoPiped(
    "https://example.com/video.mp4",
    additional_ffmpeg_parameters=["-re", "-preset", "fast"]
)
```

### Quality Parameters

#### HighQualityAudio

High-quality audio settings.

```python
from ayugram.types import HighQualityAudio

audio = HighQualityAudio(
    bitrate=128,  # kbps
    channels=2    # Stereo
)
```

#### HighQualityVideo

High-quality video settings.

```python
from ayugram.types import HighQualityVideo

video = HighQualityVideo(
    width=1280,
    height=720,
    fps=30,
    bitrate=2000  # kbps
)
```

### State Types

#### StreamState

Represents the current playback state for a stream.

```python
from ayugram.stream import StreamState

# StreamState is returned by get_stream_state()
state = ayugram.get_stream_state(chat_id)
if state:
    print(f"Position: {state.position_ms}ms")
    print(f"Duration: {state.duration_ms}ms")
    print(f"Playing: {state.is_playing}")
    print(f"Paused: {state.is_paused}")
    print(f"Volume: {state.volume}")
    print(f"Speed: {state.speed}")
```

**Fields:**
- `position_ms` (int) - Current playback position in milliseconds
- `duration_ms` (int) - Total stream duration in milliseconds (0 if unknown)
- `is_playing` (bool) - Whether the stream is currently playing
- `is_paused` (bool) - Whether the stream is currently paused
- `volume` (float) - Volume level (0.0 to 1.0)
- `speed` (float) - Playback speed multiplier (0.5 to 2.0)
- `updated_at` (datetime) - Timestamp of last state update

### Exceptions

All exceptions inherit from `AyuGramError`.

- `AyuGramError` - Base exception for all AyuGram SDK errors
- `ConnectionError` - Engine connection failed
- `AuthenticationError` - Authentication failed
- `CallError` - Voice call operation failed
- `TimeoutError` - Operation timed out

```python
from ayugram.exceptions import AyuGramError, ConnectionError

try:
    await ayugram.start()
except ConnectionError as e:
    print(f"Failed to connect: {e}")
except AyuGramError as e:
    print(f"Error: {e}")
```

**Exception Attributes:**
- `message` (str) - Human-readable error description
- `details` (dict) - Optional dictionary with additional error context

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AYUGRAM_ENGINE_URL` | AyuGram JSON-RPC endpoint | `http://localhost:8080/jsonrpc` |
| `AYUGRAM_SESSION_DIR` | Session file directory | `./sessions` |
| `AYUGRAM_LOG_LEVEL` | Logging level | `INFO` |
| `AYUGRAM_TIMEOUT` | Request timeout in seconds | `30` |

### Using with AyuGram Engine

When the AyuGram JSON-RPC API is available, start the engine:

```bash
docker run -d \
  --name tg-engine \
  -p 8080:8080 \
  -v tg-engine-session:/data/tg-session \
  -e TDESKTOP_API_ID=37831214 \
  -e TDESKTOP_API_HASH=1a10843db60c599ce2ec67bc6a55f1c2 \
  sattva-tg-engine:latest
```

Then connect your SDK:

```python
from ayugram import AyuGramClient
from pyrogram import Client

app = Client("my_account", api_id=12345678, api_hash="your_api_hash")
ayugram = AyuGramClient(app, engine_url="http://localhost:8080/jsonrpc")
```

### Using Mock Server (Development)

For development without AyuGram engine, use the mock server:

```bash
cd ayugram-python
python tests/mock_server.py
```

The SDK will work with the mock server for testing.

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=ayugram --cov-report=html

# Run integration tests
pytest tests/integration/ -v
```

### Code Quality

```bash
# Format code
black ayugram/
isort ayugram/

# Lint code
ruff check ayugram/

# Type checking
mypy ayugram/

# Security scan
bandit -r ayugram/
```

### Project Structure

```
ayugram-python/
├── ayugram/
│   ├── __init__.py       # Package exports
│   ├── client.py         # Main AyuGramClient class
│   ├── session.py        # Session management
│   ├── types.py          # PyTgCalls-compatible types
│   ├── exceptions.py     # Custom exceptions
│   ├── rpc.py            # JSON-RPC protocol handler
│   └── stream.py         # Stream control methods
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── test_*.py         # Unit tests
│   ├── mock_server.py    # Mock JSON-RPC server
│   └── integration/      # Integration tests
├── examples/
│   ├── basic_usage.py
│   ├── session_management.py
│   └── voice_call.py
├── setup.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Architecture

```
┌─────────────────┐
│  Pyrogram/      │
│  Telethon Client│
└────────┬────────┘
         │
┌────────▼────────┐
│ AyuGramClient   │
│ - PyTgCalls API │
└────────┬────────┘
         │
┌────────▼────────┐
│ JsonRpcClient   │
│ - JSON-RPC 2.0  │
└────────┬────────┘
         │
┌────────▼────────┐
│ AyuGram Engine  │
│ (tg-engine)     │
└─────────────────┘
```

The SDK provides a layered architecture:
1. **AyuGramClient** - PyTgCalls-compatible interface
2. **JsonRpcClient** - JSON-RPC protocol handler
3. **SessionManager** - Session persistence and caching
4. **StreamControl** - Playback control methods

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- [GitHub Repository](https://github.com/sattva-ai/ayugram-python)
- [Bug Reports](https://github.com/sattva-ai/ayugram-python/issues)
- [AyuGram Desktop](https://github.com/AyuGram/AyuGramDesktop)
- [Sattva Platform](https://sattva.io)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- 📧 Email: dev@sattva.io
- 💬 Telegram: [AyuGram Chat](https://t.me/ayugramchat)
- 📖 Documentation: [GitHub Wiki](https://github.com/sattva-ai/ayugram-python/wiki)

## Status

**Current Version:** 0.1.0 (Alpha)

**Note:** This SDK is under active development. The API may change between versions until 1.0.0 is released.

**⚠️ Important:** The AyuGram JSON-RPC API is not yet publicly documented. This SDK is designed based on expected API patterns and includes a mock server for testing. When the official API is released, integration points will be updated.
