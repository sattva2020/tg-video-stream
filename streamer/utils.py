import subprocess, json
from typing import List, Tuple

def expand_playlist(urls: List[str]) -> List[str]:
    """
    Если среди ссылок есть YouTube-плейлисты — развернуть в список видео-URL.
    Для одиночных видео возвращает как есть.
    """
    out = []
    for u in urls:
        u = u.strip()
        if not u:
            continue
        try:
            cmd = ["yt-dlp", "--flat-playlist", "-J", u]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
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
    """
    quality = (quality or "720p").lower()
    if quality == "1080p":
        v = ["-vf", "scale=-2:1080", "-b:v", "3500k"]
    elif quality == "480p":
        v = ["-vf", "scale=-2:480", "-b:v", "900k"]
    else:  # 720p
        v = ["-vf", "scale=-2:720", "-b:v", "1800k"]

    a = ["-ar", "48000", "-b:a", "128k"]
    return v, a

def best_stream_url(youtube_url: str) -> str:
    """
    Получить прямой URL лучшего видео-/аудио потока для ffmpeg.
    """
    cmd = ["yt-dlp", "-g", "-f", "best", youtube_url]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    return lines[0] if lines else youtube_url
