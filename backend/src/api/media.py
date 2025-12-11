"""
API endpoints для работы с медиафайлами на сервере.
Позволяет сканировать папки и получать метаданные файлов.
"""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
import mimetypes

from src.api.auth import get_current_user
from src.models.user import User

router = APIRouter(prefix="/media", tags=["media"])

# Конфигурация путей
MUSIC_ROOT = os.getenv("MUSIC_ROOT", "/app/music")  # Путь к папке с музыкой
ALLOWED_EXTENSIONS = {'.mp3', '.mp4', '.m4a', '.flac', '.ogg', '.wav', '.opus', '.aac'}


class MediaFile(BaseModel):
    """Информация о медиафайле."""
    path: str              # Относительный путь от MUSIC_ROOT
    filename: str          # Имя файла
    title: Optional[str]   # Название трека (из тегов)
    artist: Optional[str]  # Исполнитель
    album: Optional[str]   # Альбом
    duration: int          # Длительность в секундах
    size: int              # Размер файла в байтах
    mime_type: str         # MIME тип


class FolderInfo(BaseModel):
    """Информация о папке."""
    path: str
    name: str
    files_count: int
    total_size: int
    total_duration: int


def get_file_metadata(file_path: Path) -> Optional[MediaFile]:
    """Извлечь метаданные из аудиофайла."""
    try:
        audio = MutagenFile(file_path, easy=True)
        
        # Длительность
        duration = int(audio.info.length) if audio and hasattr(audio.info, 'length') else 0
        
        # Теги
        title = None
        artist = None
        album = None
        
        if audio and hasattr(audio, 'tags') and audio.tags:
            title = audio.tags.get('title', [None])[0] if 'title' in audio.tags else None
            artist = audio.tags.get('artist', [None])[0] if 'artist' in audio.tags else None
            album = audio.tags.get('album', [None])[0] if 'album' in audio.tags else None
        
        # Если нет тегов - используем имя файла
        if not title:
            title = file_path.stem
        
        # MIME тип
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'audio/mpeg'  # по умолчанию
        
        return MediaFile(
            path=str(file_path.relative_to(MUSIC_ROOT)),
            filename=file_path.name,
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            size=file_path.stat().st_size,
            mime_type=mime_type
        )
    except Exception as e:
        print(f"Error reading metadata from {file_path}: {e}")
        return None


@router.get("/folders", response_model=List[str])
async def list_music_folders(
    current_user: User = Depends(get_current_user)
):
    """Получить список папок с музыкой."""
    music_root = Path(MUSIC_ROOT)
    
    if not music_root.exists():
        raise HTTPException(status_code=404, detail="Music folder not found")
    
    folders = []
    for item in music_root.rglob("*"):
        if item.is_dir():
            # Проверяем, есть ли в папке аудиофайлы
            has_audio = any(
                f.suffix.lower() in ALLOWED_EXTENSIONS
                for f in item.iterdir()
                if f.is_file()
            )
            if has_audio:
                folders.append(str(item.relative_to(music_root)))
    
    # Добавляем корневую папку
    if any(f.suffix.lower() in ALLOWED_EXTENSIONS for f in music_root.iterdir() if f.is_file()):
        folders.insert(0, ".")
    
    return sorted(folders)


@router.get("/folders/{folder_path:path}/info", response_model=FolderInfo)
async def get_folder_info(
    folder_path: str,
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о папке."""
    music_root = Path(MUSIC_ROOT)
    target_folder = music_root / folder_path
    
    # Проверка безопасности
    try:
        target_folder = target_folder.resolve()
        if not str(target_folder).startswith(str(music_root.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not target_folder.exists() or not target_folder.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Сканируем папку
    files_count = 0
    total_size = 0
    total_duration = 0
    
    for file in target_folder.iterdir():
        if file.is_file() and file.suffix.lower() in ALLOWED_EXTENSIONS:
            files_count += 1
            total_size += file.stat().st_size
            
            # Пытаемся получить длительность
            try:
                audio = MutagenFile(file)
                if audio and hasattr(audio.info, 'length'):
                    total_duration += int(audio.info.length)
            except Exception:
                pass
    
    return FolderInfo(
        path=folder_path,
        name=target_folder.name if folder_path != "." else "Music Root",
        files_count=files_count,
        total_size=total_size,
        total_duration=total_duration
    )


@router.get("/folders/{folder_path:path}/files", response_model=List[MediaFile])
async def list_folder_files(
    folder_path: str,
    recursive: bool = Query(False, description="Сканировать рекурсивно"),
    current_user: User = Depends(get_current_user)
):
    """Получить список файлов в папке с метаданными."""
    music_root = Path(MUSIC_ROOT)
    target_folder = music_root / folder_path
    
    # Проверка безопасности
    try:
        target_folder = target_folder.resolve()
        if not str(target_folder).startswith(str(music_root.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")
    
    if not target_folder.exists() or not target_folder.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Сканируем файлы
    files = []
    pattern = "**/*" if recursive else "*"
    
    for file_path in target_folder.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
            metadata = get_file_metadata(file_path)
            if metadata:
                files.append(metadata)
    
    # Сортируем по имени файла
    files.sort(key=lambda f: f.filename.lower())
    
    return files


@router.get("/scan", response_model=List[MediaFile])
async def scan_music_folder(
    folder: Optional[str] = Query(None, description="Папка для сканирования (относительно MUSIC_ROOT)"),
    recursive: bool = Query(True, description="Рекурсивное сканирование"),
    current_user: User = Depends(get_current_user)
):
    """
    Сканировать папку с музыкой и вернуть список файлов с метаданными.
    Используется для создания плейлистов из локальных файлов.
    """
    music_root = Path(MUSIC_ROOT)
    
    if not music_root.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Music folder not found: {MUSIC_ROOT}. Set MUSIC_ROOT environment variable."
        )
    
    # Определяем целевую папку
    if folder:
        target_folder = music_root / folder
        try:
            target_folder = target_folder.resolve()
            # Проверка безопасности - не даём выйти за пределы MUSIC_ROOT
            if not str(target_folder).startswith(str(music_root.resolve())):
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid folder path")
        
        if not target_folder.exists() or not target_folder.is_dir():
            raise HTTPException(status_code=404, detail="Folder not found")
    else:
        target_folder = music_root
    
    # Сканируем файлы
    files = []
    pattern = "**/*" if recursive else "*"
    
    for file_path in target_folder.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
            metadata = get_file_metadata(file_path)
            if metadata:
                files.append(metadata)
    
    return files
