import subprocess, json, os, shlex, asyncio
from typing import List, Tuple, Optional, Dict, Any
import logging
import audio_utils

log = logging.getLogger("tg_video_streamer")

# Базовый путь для локальных медиа-файлов
# На сервере: /opt/sattva-streamer/data/music/
# В Docker: /app/data/music/
MEDIA_BASE_PATH = os.getenv("MEDIA_BASE_PATH", "/opt/sattva-streamer/data/music")


def resolve_file_url(url: str) -> str:
    """
    Преобразует file:// URL в абсолютный путь.
    
    Примеры:
        file://muzyka_dlya_meditatsii/track.mp3 -> /opt/sattva-streamer/data/music/muzyka_dlya_meditatsii/track.mp3
        /absolute/path/file.mp3 -> /absolute/path/file.mp3
        https://example.com/file.mp3 -> https://example.com/file.mp3
    """
    if url.startswith("file://"):
        relative_path = url[7:]  # Убираем "file://"
        absolute_path = os.path.join(MEDIA_BASE_PATH, relative_path)
        if os.path.exists(absolute_path):
            return absolute_path
        else:
            log.warning(f"File not found: {absolute_path}, trying relative path")
            # Fallback: попробуем найти в текущей директории
            if os.path.exists(relative_path):
                return os.path.abspath(relative_path)
            return absolute_path  # Вернём абсолютный путь для лучшей диагностики
    return url

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
        
        # Check if it's a local file or file:// URL
        if u.startswith("file://"):
            resolved = resolve_file_url(u)
            out.append(resolved)
            continue
        
        if os.path.exists(u):
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
                        url_val = e['url']
                        if "youtube" in (data.get("extractor", "")).lower():
                            if url_val.startswith("http"):
                                out.append(url_val)
                            else:
                                out.append(f"https://www.youtube.com/watch?v={url_val}")
                        else:
                            out.append(url_val)
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
    
    Phase 5 (T051-T052): Автоматическая конвертация аудио форматов
    - Определяет MP3/FLAC файлы
    - Конвертирует через Rust transcoder → Opus/WAV
    - Fallback на прямое использование при ошибках
    """
    # Check if it's a file:// URL - resolve to absolute path
    if youtube_url.startswith("file://"):
        resolved = resolve_file_url(youtube_url)
        log.debug(f"Resolved file:// URL: {youtube_url} -> {resolved}")
        return resolved
    
    # Check if it's a local file
    if os.path.exists(youtube_url):
        return youtube_url

    # Check if it's a direct audio file
    if audio_utils.is_audio_file(youtube_url):
        # Phase 5: Попытка конвертации MP3/FLAC → Opus через Rust transcoder
        converted_url = await audio_utils.convert_audio_format(
            source_url=youtube_url,
            target_format="opus",
            use_rust_transcoder=True
        )
        # convert_audio_format возвращает исходный URL при ошибках (fallback)
        return converted_url if converted_url else youtube_url

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

async def get_stream_quality(url: str, timeout: int = 10) -> Optional[Dict[str, Any]]:
    """
    Feature 022 (T001): Получить информацию о качестве потока.
    
    Анализирует аудио/видео поток и возвращает метрики качества:
    - Кодек
    - Битрейт
    - Разрешение (для видео)
    - FPS (для видео)
    - Уровень качества (low/medium/high/lossless)
    
    Args:
        url: URL потока для анализа
        timeout: Таймаут FFprobe в секундах
        
    Returns:
        Dict с информацией о качестве или None если анализ неудачен
        
    Examples:
        >>> quality = await get_stream_quality("https://example.com/audio.mp3")
        >>> print(quality['overall_quality'])  # 'medium'
    """
    try:
        # Lazy import to avoid dependency issues
        from ffprobe_utils import analyze_stream_quality
        
        stream_quality = await analyze_stream_quality(url, timeout)
        if stream_quality:
            return stream_quality.to_dict()
        return None
    except ImportError:
        log.warning("ffprobe_utils module not available")
        return None
    except Exception as e:
        log.error(f"Error analyzing stream quality for {url}: {e}")
        return None