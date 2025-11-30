import requests
import logging
import os
import asyncio
from urllib.parse import urlparse

log = logging.getLogger("tg_video_streamer")

def is_url(path: str) -> bool:
    try:
        result = urlparse(path)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

async def detect_content_type(url: str) -> str:
    """
    Detects the content type of a URL using a HEAD request.
    Returns the Content-Type header or empty string.
    """
    loop = asyncio.get_running_loop()
    try:
        def _head():
            return requests.head(url, allow_redirects=True, timeout=5)
        
        response = await loop.run_in_executor(None, _head)
        return response.headers.get('Content-Type', '').lower()
    except Exception as e:
        log.warning(f"Failed to detect content type for {url}: {e}")
        return ""

def parse_m3u_content(content: str) -> list[str]:
    """
    Parses M3U content and returns a list of URLs.
    Ignores comments and empty lines.
    """
    urls = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            urls.append(line)
    return urls

async def fetch_playlist(url: str) -> list[str]:
    """
    Fetches a playlist from a URL and returns a list of track URLs.
    Supports M3U/M3U8.
    """
    loop = asyncio.get_running_loop()
    try:
        def _get():
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            return resp
            
        response = await loop.run_in_executor(None, _get)
        
        content_type = response.headers.get('Content-Type', '').lower()
        # Basic check for playlist types
        if 'mpegurl' in content_type or 'x-mpegurl' in content_type or url.endswith('.m3u') or url.endswith('.m3u8'):
            return parse_m3u_content(response.text)
        
        # If it's just a text file, treat it as a list of URLs
        if 'text/plain' in content_type:
             return parse_m3u_content(response.text)

        log.warning(f"URL {url} does not appear to be a playlist (Content-Type: {content_type})")
        return []
    except Exception as e:
        log.error(f"Error fetching playlist from {url}: {e}")
        return []

def is_audio_file(url: str) -> bool:
    """
    Checks if the URL points to a known audio file extension.
    """
    path = urlparse(url).path.lower()
    audio_exts = ('.mp3', '.aac', '.ogg', '.wav', '.flac', '.m4a', '.opus')
    return path.endswith(audio_exts)


# Transcoding profiles: map an input shorthand to an ffmpeg profile and explanation.
# Profiles are intentionally conservative and produce Opus (or PCM) suitable for PyTgCalls.
# Added low-latency flags: -application lowdelay, -frame_duration 20
TRANSCODING_PROFILES = {
    'flac': {
        'match_mime': ['audio/flac'],
        'extensions': ['.flac'],
        'ffmpeg_args': ['-vn', '-c:a', 'libopus', '-b:a', '96k', '-f', 'opus', '-application', 'lowdelay', '-frame_duration', '20'],
        'description': 'Transcode FLAC to Opus (96kbps, low latency)'
    },
    'ogg': {
        'match_mime': ['audio/ogg', 'application/ogg'],
        'extensions': ['.ogg'],
        'ffmpeg_args': ['-vn', '-c:a', 'libopus', '-b:a', '96k', '-f', 'opus', '-application', 'lowdelay', '-frame_duration', '20'],
        'description': 'Transcode OGG (non-Opus) to Opus (low latency)'
    },
    'wav': {
        'match_mime': ['audio/wav', 'audio/x-wav'],
        'extensions': ['.wav'],
        'ffmpeg_args': ['-vn', '-c:a', 'libopus', '-b:a', '96k', '-f', 'opus', '-application', 'lowdelay', '-frame_duration', '20'],
        'description': 'Transcode WAV to Opus (low latency)'
    },
}


def get_transcoding_profile(url: str, content_type: str | None = None) -> dict | None:
    """Return a transcoding profile dict if the URL/content type requires transcoding.

    1) Inspect Content-Type header if provided.
    2) Otherwise use file extension heuristics.

    Returns a profile mapping with ffmpeg args or None if no transcoding is required.
    """
    ct = (content_type or '').lower() if content_type else ''
    # 1) check content type
    for name, profile in TRANSCODING_PROFILES.items():
        for mime in profile.get('match_mime', []):
            if mime in ct:
                return profile

    # 2) check extension
    path = urlparse(url).path.lower()
    for name, profile in TRANSCODING_PROFILES.items():
        for ext in profile.get('extensions', []):
            if path.endswith(ext):
                return profile

    return None
