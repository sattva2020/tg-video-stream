"""
API endpoints для работы с медиафайлами на сервере.
Позволяет сканировать папки и получать метаданные файлов.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pathlib import Path

from src.api.auth import get_current_user
from src.models.user import User
from src.services.media_scanner import (
    MediaFile, FolderInfo, ScanResult,
    list_folders, get_file_metadata, scan_folder,
    MUSIC_ROOT
)

router = APIRouter(prefix="/media", tags=["media"])




@router.get("/folders", response_model=List[FolderInfo])
async def list_music_folders(
    current_user: User = Depends(get_current_user)
):
    """Получить список папок с музыкой."""
    try:
        return list_folders()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folders/{folder_path:path}/info", response_model=FolderInfo)
async def get_folder_info(
    folder_path: str,
    current_user: User = Depends(get_current_user)
):
    """Получить информацию о папке."""
    try:
        files = scan_folder(folder_path, recursive=False)
        total_size = sum(f.size for f in files)
        total_duration = sum(f.duration for f in files)
        
        return FolderInfo(
            path=folder_path,
            name=Path(folder_path).name if folder_path != "." else "Music Root",
            files_count=len(files),
            total_size=total_size,
            total_duration=total_duration
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid folder path")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Folder not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/folders/{folder_path:path}/files", response_model=List[MediaFile])
async def list_folder_files(
    folder_path: str,
    recursive: bool = Query(False, description="Сканировать рекурсивно"),
    current_user: User = Depends(get_current_user)
):
    """Получить список файлов в папке с метаданными."""
    try:
        return scan_folder(folder_path, recursive=recursive)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid folder path")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Folder not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scan", response_model=ScanResult)
async def scan_music_folder(
    folder: Optional[str] = Query(None, description="Папка для сканирования (относительно MUSIC_ROOT)"),
    recursive: bool = Query(True, description="Рекурсивное сканирование"),
    current_user: User = Depends(get_current_user)
):
    """
    Сканировать папку с музыкой и вернуть список файлов с метаданными.
    Используется для создания плейлистов из локальных файлов.
    """
    try:
        files = scan_folder(folder or ".", recursive=recursive)
        return ScanResult(
            folder=folder or ".",
            files=files,
            total=len(files)
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid folder path")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Folder not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
