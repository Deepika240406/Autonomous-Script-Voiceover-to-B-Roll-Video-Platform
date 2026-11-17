from abc import ABC, abstractmethod
from typing import Optional, BinaryIO
import os


class BaseStorage(ABC):
    @abstractmethod
    def save_file(self, relative_path: str, source_path: str) -> str:
        """Saves a local file to storage and returns its accessible URL or URI."""
        pass

    @abstractmethod
    def save_bytes(self, relative_path: str, data: bytes, content_type: Optional[str] = None) -> str:
        """Saves byte content directly to storage and returns its accessible URL."""
        pass

    @abstractmethod
    def get_file_url(self, relative_path: str) -> str:
        """Returns the download URL for a stored file."""
        pass

    @abstractmethod
    def get_local_path(self, relative_path: str) -> str:
        """Returns the local path or downloads remote object to a local cached path."""
        pass
