import subprocess, json, os, shlex, asyncio
from typing import List, Tuple
import logging
import audio_utils

log = logging.getLogger("tg_video_streamer")

async def expand_playlist(urls: List[str]) -> List[str]:
    """
    Если среди ссылок есть YouTube-плейлисты — развернуть в список видео-URL.
    Для одиночных видео возвращает как есть.
    """
    out = []
    loop = asyncio.get_running_loop()

    for u in urls:
        u = u.strip()
        if not u:
            continue
        
        # Check if it's a local file
        if os.path.exists(u) or u.startswith("file://"):
            out.append(u)
            continue

        # Check for M3U playlist
        if u.lower().endswith('.m3u') or u.lower().endswith('.m3u8'):
             playlist_items = await audio_utils.fetch_playlist(u)
             if playlist_items:
                 out.extend(playlist_items)
                 continue

        try:
            cmd = ["yt-dlp", "--flat-playlist", "-J", u]
            
            def _run_ytdlp():
                return subprocess.run(cmd, capture_output=True, text=True, check=True)

            proc = await loop.run_in_executor(None, _run_ytdlp)
            data = json.loads(proc.stdout)
            if "entries" in data:
                for e in data["entries"]:
                    # склеиваем полноценный URL видео
                    if e.get("url"):
                        if "youtube" in (data.get("extractor", "")).lower():
                            out.append(f"https://www.youtube.com/watch?v={e['url']}")
                        else:
                            out.append(e["url"])
            else:
                out.append(u)
        except Exception:
            out.append(u)
    return out

def build_ffmpeg_av_args(quality: str) -> Tuple[list, list]:
    """
    Возвращает (video_args, audio_args) для FFmpeg в зависимости от желаемого качества.
    Также добавляет аргументы из переменной окружения FFMPEG_ARGS.
    """
    quality = (quality or "720p").lower()
    # Base video args with low-latency presets
    base_v = ["-preset", "ultrafast", "-tune", "zerolatency"]
    
    if quality == "1080p":
        v = [*base_v, "-vf", "scale=-2:1080", "-b:v", "3500k"]
    elif quality == "480p":
        v = [*base_v, "-vf", "scale=-2:480", "-b:v", "900k"]
    else:  # 720p
        v = [*base_v, "-vf", "scale=-2:720", "-b:v", "1800k"]

    a = ["-ar", "48000", "-b:a", "128k"]

    # Inject custom arguments from environment
    custom_args_str = os.getenv("FFMPEG_ARGS", "")
    if custom_args_str:
        try:
            custom_args = shlex.split(custom_args_str)
            # We append custom args to video args list, as pytgcalls usually takes one list of additional params
            # or we can distribute them. The caller (main.py) joins them:
            # additional_ffmpeg_parameters=["-re", *v_args, *a_args]
            # So appending to v is fine.
            v.extend(custom_args)
        except Exception:
            pass

    return v, a

async def best_stream_url(youtube_url: str) -> str:
    """
    Получить прямой URL лучшего видео-/аудио потока для ffmpeg.
    """
    # Check if it's a local file
    if os.path.exists(youtube_url) or youtube_url.startswith("file://"):
        return youtube_url

    # Check if it's a direct audio file
    if audio_utils.is_audio_file(youtube_url):
        return youtube_url

    loop = asyncio.get_running_loop()
    cmd = ["yt-dlp", "-g", "-f", "best", youtube_url]
    
    def _run_ytdlp_best():
        return subprocess.run(cmd, capture_output=True, text=True, check=True)

    try:
        proc = await loop.run_in_executor(None, _run_ytdlp_best)
        lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
        return lines[0] if lines else youtube_url
    except Exception as e:
        log.error(f"Error getting best stream url for {youtube_url}: {e}")
        return youtube_url
