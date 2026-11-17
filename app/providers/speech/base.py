from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseSpeechProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribes speech from audio file with timestamps.
        Returns:
        {
            "text": str,
            "language": str,
            "speech_coverage": float,
            "segments": [
                {
                    "start": float,
                    "end": float,
                    "text": str,
                    "words": [{"word": str, "start": float, "end": float, "confidence": float}]
                }
            ]
        }
        """
        pass
