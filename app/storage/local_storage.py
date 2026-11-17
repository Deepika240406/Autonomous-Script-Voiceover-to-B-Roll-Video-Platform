import os
import shutil
from typing import Optional
from app.storage.base import BaseStorage
from app.config import settings
from app.core.logging import logger


class LocalStorage(BaseStorage):
    def __init__(self, base_dir: str = settings.LOCAL_STORAGE_PATH):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _full_path(self, relative_path: str) -> str:
        # Prevent directory traversal
        clean_rel = os.path.normpath(relative_path).lstrip("/\\")
        dest = os.path.abspath(os.path.join(self.base_dir, clean_rel))
        if not dest.startswith(self.base_dir):
            raise ValueError(f"Path traversal detected: {relative_path}")
        return dest

    def save_file(self, relative_path: str, source_path: str) -> str:
        dest_path = self._full_path(relative_path)
        if os.path.abspath(source_path) != os.path.abspath(dest_path):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(source_path, dest_path)
        logger.debug(f"Saved file {source_path} -> {dest_path}")
        return self.get_file_url(relative_path)

    def save_bytes(self, relative_path: str, data: bytes, content_type: Optional[str] = None) -> str:
        dest_path = self._full_path(relative_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)
        logger.debug(f"Saved {len(data)} bytes to {dest_path}")
        return self.get_file_url(relative_path)

    def get_file_url(self, relative_path: str) -> str:
        clean_rel = os.path.normpath(relative_path).replace("\\", "/").lstrip("/")
        return f"{settings.API_V1_PREFIX}/storage/{clean_rel}"

    def get_local_path(self, relative_path: str) -> str:
        return self._full_path(relative_path)
