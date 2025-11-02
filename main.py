import os
import asyncio
import logging
from typing import List, Union

from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.exceptions import AlreadyJoinedError
from pytgcalls.types import AudioVideoPiped, HighQualityAudio, HighQualityVideo

from dotenv import load_dotenv
from utils import expand_playlist, build_ffmpeg_av_args, best_stream_url

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

if not (API_ID and API_HASH and SESSION_STRING and CHAT_ID):
    raise SystemExit("Please set API_ID, API_HASH, SESSION_STRING, CHAT_ID in .env")

app = Client(
    name="tg_streamer",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True,
    workdir="./tdlib"
)

pytg = PyTgCalls(app)

async def ensure_join(chat: Union[int, str]):
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
    while True:
        for link in urls:
            try:
                direct = best_stream_url(link)
                log.info("▶️ Playing: %s", link)
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
    async with app:
        await pytg.start()
        me = await app.get_me()
        log.info("Logged in as: %s", me.id)
        await ensure_join(CHAT_ID)
        with open("playlist.txt", "r", encoding="utf-8") as f:
            urls = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
        if not urls:
            raise SystemExit("playlist.txt is empty")
        await play_loop(urls)

if __name__ == "__main__":
    asyncio.run(main())
