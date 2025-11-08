import os
import asyncio
import logging
from typing import List, Union

from pyrogram import Client
from pyrogram.errors import SessionExpired, SessionPasswordNeeded, AuthKeyInvalid, RPCError
try:
    from pytgcalls import PyTgCalls
    from pytgcalls.exceptions import AlreadyJoinedError
    from pytgcalls.types import AudioVideoPiped, HighQualityAudio, HighQualityVideo
    PYG_AVAILABLE = True
except Exception as e:
    # pytgcalls / tgcalls not available — run in degraded mode
    # Persist the full import error to a temporary file for debugging (visible to sysadmin).
    try:
        import traceback
        import pathlib
        p = pathlib.Path('/tmp/pytgcalls_import_error.log')
        with p.open('a', encoding='utf-8') as fh:
            fh.write('--- Import error at startup ---\n')
            fh.write(repr(e) + '\n')
            traceback.print_exc(file=fh)
    except Exception:
        # best-effort only
        pass
    PYG_AVAILABLE = False

from dotenv import load_dotenv
from utils import expand_playlist, build_ffmpeg_av_args, best_stream_url

# Prometheus imports
try:
    from prometheus_client import start_http_server, Counter
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.getLogger("tg_video_streamer").warning("prometheus_client not available — metrics will not be exported")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
log = logging.getLogger("tg_video_streamer")

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
CHAT_ID: Union[int, str] = os.getenv("CHAT_ID", "")
VIDEO_QUALITY = os.getenv("VIDEO_QUALITY", "720p")
LOOP = os.getenv("LOOP", "1") == "1"
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))

# Initialize Prometheus metrics if available
streams_played_total = None
if PROMETHEUS_AVAILABLE:
    streams_played_total = Counter('streams_played_total', 'Total number of streams played')
    try:
        start_http_server(PROMETHEUS_PORT)
        log.info("Prometheus metrics server started on port %d", PROMETHEUS_PORT)
    except Exception as e:
        log.warning("Failed to start Prometheus server: %s", e)
else:
    log.info("Prometheus not available — skipping metrics initialization")

RUN_APP = True
INTERACTIVE_AUTH = False
if not (API_ID and API_HASH and CHAT_ID):
    logging.getLogger("tg_video_streamer").warning(
        "Missing critical API credentials (API_ID, API_HASH, or CHAT_ID) in .env — running in degraded mode"
    )
    RUN_APP = False
elif not SESSION_STRING:
    # SESSION_STRING is missing — log info and proceed with degraded mode
    # User can add SESSION_STRING later and restart
    logging.getLogger("tg_video_streamer").info(
        "SESSION_STRING not provided in .env — running in degraded mode. "
        "To activate: set SESSION_STRING in .env and restart the service"
    )
    RUN_APP = False

app = Client(
    name="tg_streamer",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING if SESSION_STRING else None,
    in_memory=True,
    workdir="./tdlib"
) if SESSION_STRING else Client(
    name="tg_streamer",
    api_id=API_ID,
    api_hash=API_HASH,
    in_memory=True,
    workdir="./tdlib"
)

pytg = None
if PYG_AVAILABLE:
    try:
        pytg = PyTgCalls(app)
    except Exception as e:
        log.warning("pytgcalls initialization failed: %s", e)
        pytg = None
else:
    log.warning("pytgcalls not available — running in degraded mode (no voice/video).")

async def ensure_join(chat: Union[int, str]):
    if not pytg:
        log.info("ensure_join: pytgcalls not available, skipping join test")
        return
    try:
        await pytg.join_group_call(
            chat,
            AudioVideoPiped(
                "anullsrc=r=48000:cl=stereo",
                audio_parameters=HighQualityAudio(),
                video_parameters=HighQualityVideo()
            ),
            stream_type=0
        )
        await pytg.leave_group_call(chat)
    except AlreadyJoinedError:
        await pytg.leave_group_call(chat)
    except Exception as e:
        log.info("join test: %s", e)

async def play_loop(urls: List[str]):
    urls = expand_playlist(urls)
    v_args, a_args = build_ffmpeg_av_args(VIDEO_QUALITY)
    log.info("Expanded playlist: %d items", len(urls))
    if not pytg:
        log.warning("pytgcalls not available — entering degraded idle loop (no streaming)")
        while True:
            await asyncio.sleep(60)
    while True:
        for link in urls:
            try:
                direct = best_stream_url(link)
                log.info("▶️ Playing: %s", link)
                if streams_played_total:
                    streams_played_total.inc()
                stream = AudioVideoPiped(
                    direct,
                    video_parameters=HighQualityVideo(),
                    audio_parameters=HighQualityAudio(),
                    additional_ffmpeg_parameters=[
                        "-re",
                        *v_args,
                        *a_args
                    ]
                )
                await pytg.join_group_call(CHAT_ID, stream)
                # Ждём ~2 часа для не-live ролика, live может идти бесконечно
                for _ in range(24):
                    await asyncio.sleep(300)
                    if pytg.get_call(CHAT_ID) is None:
                        break
                await pytg.leave_group_call(CHAT_ID)
            except Exception as e:
                log.exception("Stream error: %s", e)
                try:
                    await pytg.leave_group_call(CHAT_ID)
                except Exception:
                    pass
                await asyncio.sleep(5)
        if not LOOP:
            break

async def main():
    if not RUN_APP:
        log.info("Starting in degraded idle mode (no Telegram client).")
        # degraded loop: don't attempt to connect to Telegram or start pytgcalls
        while True:
            await asyncio.sleep(60)

    # Try to start the Client and detect invalid/expired sessions early.
    try:
        async with app:
            if pytg:
                await pytg.start()

            try:
                me = await app.get_me()
            except (SessionExpired, AuthKeyInvalid) as e:
                # Session is invalid/expired — log and fall back to degraded mode
                log.exception("Telegram session invalid or expired: %s", e)
                log.error("Switching to degraded mode. To recover: regenerate SESSION_STRING and restart the service. See test/auto_session_runner.py for helpers.")
                # Best-effort: stop any partially started pytgcalls
                try:
                    if pytg:
                        await pytg.stop()
                except Exception:
                    pass
                # Enter degraded idle loop
                while True:
                    await asyncio.sleep(60)

            except SessionPasswordNeeded:
                log.exception("Two-factor auth (password) is required for this account. Cannot continue.")
                # Enter degraded mode
                while True:
                    await asyncio.sleep(60)

            log.info("Logged in as: %s", me.id)
            await ensure_join(CHAT_ID)
            with open("playlist.txt", "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            if not urls:
                raise SystemExit("playlist.txt is empty")
            await play_loop(urls)

    except RPCError as e:
        log.exception("Telegram RPC error during startup: %s", e)
        log.error("Entering degraded mode. Check your API_ID/API_HASH/SESSION_STRING or network connectivity.")
        while True:
            await asyncio.sleep(60)
    except Exception as e:
        log.exception("Unhandled error during startup: %s", e)
        # If something unexpected happened, enter degraded mode to keep service alive
        while True:
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
