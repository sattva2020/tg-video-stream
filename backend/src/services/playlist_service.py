import os
from typing import List
from src.core.config import settings

class PlaylistService:
    def __init__(self, file_path: str = settings.PLAYLIST_PATH):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not os.path.exists(self.file_path):
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w') as f:
                f.write("# Telegram Stream Playlist\n")

    def get_playlist(self) -> List[str]:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            # Filter out comments and empty lines
            return [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
        except Exception as e:
            print(f"Error reading playlist: {e}")
            return []

    def update_playlist(self, items: List[str]) -> bool:
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write("# Telegram Stream Playlist\n")
                for item in items:
                    f.write(f"{item}\n")
            return True
        except Exception as e:
            print(f"Error writing playlist: {e}")
            return False

    def add_item(self, url: str) -> bool:
        items = self.get_playlist()
        if url not in items:
            items.append(url)
            return self.update_playlist(items)
        return True

    def remove_item(self, url: str) -> bool:
        items = self.get_playlist()
        if url in items:
            items = [item for item in items if item != url]
            return self.update_playlist(items)
        return False

playlist_service = PlaylistService()
