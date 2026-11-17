from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class CandidateClip:
    clip_id: str
    provider: str
    title: str
    description: str
    tags: List[str]
    download_url: str
    duration: float
    width: int
    height: int
    fps: float
    licence_name: str
    licence_url: str
    attribution: str
    is_ai_generated: bool = False
    preview_url: Optional[str] = None


class BaseFootageProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def search(self, query: str, min_duration: float = 3.0, count: int = 5) -> List[CandidateClip]:
        """Searches footage provider and returns candidate clips matching query."""
        pass

    @abstractmethod
    async def download_clip(self, clip: CandidateClip, dest_path: str) -> str:
        """Downloads candidate clip video file to local dest_path."""
        pass
