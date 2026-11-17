import os
from typing import Dict, Any, List
from app.providers.speech.base import BaseSpeechProvider
from app.utils.ffmpeg import inspect_audio
from app.core.exceptions import SilentAudioException, MusicOnlyAudioException, AudioCorruptedException


class MockSpeechProvider(BaseSpeechProvider):
    def __init__(self, predefined_text: str = "This is realistic narration timed accurately to the voice."):
        self.predefined_text = predefined_text

    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        basename = os.path.basename(audio_path).lower()
        if "corrupt" in basename:
            raise AudioCorruptedException("Audio file is corrupt or unreadable.")
        if "silent" in basename:
            raise SilentAudioException("Audio contains no detectable speech or is completely silent.")
        if "music" in basename:
            raise MusicOnlyAudioException("Audio appears to be music-only without intelligible narration speech.")

        audio_info = inspect_audio(audio_path)
        duration = audio_info["duration"]

        words = self.predefined_text.split()
        num_words = max(1, len(words))
        step = duration / num_words

        word_list = []
        for i, w in enumerate(words):
            word_list.append({
                "word": w,
                "start": round(i * step, 3),
                "end": round((i + 1) * step, 3),
                "confidence": 0.98,
            })

        return {
            "text": self.predefined_text,
            "language": "en",
            "speech_coverage": 0.95,
            "segments": [
                {
                    "start": 0.0,
                    "end": duration,
                    "text": self.predefined_text,
                    "words": word_list,
                }
            ],
        }
