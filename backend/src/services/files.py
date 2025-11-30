import os
from typing import List
from pathlib import Path

# Default to absolute path relative to project root if not set
# Assuming backend is running from project root or backend/
# We'll try to find the data/media folder
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DEFAULT_MEDIA_ROOT = PROJECT_ROOT / "data" / "media"

MEDIA_ROOT = os.getenv("MEDIA_ROOT", str(DEFAULT_MEDIA_ROOT))

class FileService:
    def __init__(self, root_dir: str = MEDIA_ROOT):
        self.root_dir = Path(root_dir).resolve()
        if not self.root_dir.exists():
            try:
                self.root_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create media root {self.root_dir}: {e}")

    def list_files(self) -> List[str]:
        files = []
        if not self.root_dir.exists():
            return []
            
        for file in self.root_dir.glob("**/*"):
            if file.is_file():
                # Return path relative to root_dir
                # We only want video files usually, but for now list all
                if file.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.mp3']:
                    files.append(str(file.relative_to(self.root_dir)))
        return files

    def validate_file(self, file_path: str) -> bool:
        # Prevent directory traversal
        try:
            full_path = (self.root_dir / file_path).resolve()
            # Check if the resolved path starts with the root_dir
            if str(self.root_dir) not in str(full_path):
                return False
            return full_path.exists() and full_path.is_file()
        except Exception:
            return False
