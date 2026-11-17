from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseTTSProvider(ABC):
    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Synthesizes text into speech at output_path.
        Returns a dict containing:
        - audio_path: str
        - duration: float
        - voice: str
        - word_timings: List[Dict[str, Any]] (each with word, start, end)
        """
        pass
