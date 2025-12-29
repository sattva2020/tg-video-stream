import os
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any
from mutagen import File as MutagenFile
from pydantic import BaseModel

MUSIC_ROOT = os.getenv("MUSIC_ROOT", "/app/music")
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

class ScanResult(BaseModel):
    """Результат сканирования."""
    folder: str
    files: List[MediaFile]
    total: int

def get_file_metadata(file_path: Path, music_root: Path = Path(MUSIC_ROOT)) -> Optional[MediaFile]:
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
            path=str(file_path.relative_to(music_root)),
            filename=file_path.name,
            title=title,
            artist=artist,
            album=album,
            duration=duration,
            size=file_path.stat().st_size,
            mime_type=mime_type
        )
    except Exception as e:
        # print(f"Error reading metadata from {file_path}: {e}")
        return None

def scan_folder(folder_path: str, recursive: bool = True) -> List[MediaFile]:
    """
    Сканировать папку с музыкой и вернуть список файлов с метаданными.
    folder_path: относительный путь от MUSIC_ROOT
    """
    music_root = Path(MUSIC_ROOT)
    
    if not music_root.exists():
        raise FileNotFoundError(f"Music folder not found: {MUSIC_ROOT}")
    
    # Определяем целевую папку
    if folder_path and folder_path != ".":
        target_folder = music_root / folder_path
    else:
        target_folder = music_root

    try:
        target_folder = target_folder.resolve()
        # Проверка безопасности - не даём выйти за пределы MUSIC_ROOT
        if not str(target_folder).startswith(str(music_root.resolve())):
            raise PermissionError("Access denied")
    except Exception:
        raise ValueError("Invalid folder path")
    
    if not target_folder.exists() or not target_folder.is_dir():
        raise FileNotFoundError("Folder not found")
    
    # Сканируем файлы
    files = []
    pattern = "**/*" if recursive else "*"
    
    for file_path in target_folder.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
            metadata = get_file_metadata(file_path, music_root)
            if metadata:
                files.append(metadata)
    
    # Сортируем по имени файла
    files.sort(key=lambda f: f.filename.lower())
    
    return files

def list_folders(root_path: str = ".") -> List[FolderInfo]:
    """Получить список папок с музыкой."""
    music_root = Path(MUSIC_ROOT)
    
    if not music_root.exists():
        raise FileNotFoundError("Music folder not found")
    
    folders = []
    for item in music_root.rglob("*"):
        if item.is_dir():
            # Считаем аудиофайлы в папке
            audio_files = [
                f for f in item.iterdir()
                if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS
            ]
            if audio_files:
                total_size = sum(f.stat().st_size for f in audio_files)
                folders.append(FolderInfo(
                    path=str(item.relative_to(music_root)),
                    name=item.name,
                    files_count=len(audio_files),
                    total_size=total_size,
                    total_duration=0  # Вычисление длительности дорого, пропускаем
                ))
    
    # Добавляем корневую папку если в ней есть аудио
    root_audio = [f for f in music_root.iterdir() if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS]
    if root_audio:
        folders.insert(0, FolderInfo(
            path=".",
            name="Корневая папка",
            files_count=len(root_audio),
            total_size=sum(f.stat().st_size for f in root_audio),
            total_duration=0
        ))
    
    return sorted(folders, key=lambda x: x.path)
