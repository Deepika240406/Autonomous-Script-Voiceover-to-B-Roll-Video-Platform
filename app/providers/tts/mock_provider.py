import os
import asyncio
from typing import Dict, Any, List
from app.providers.tts.base import BaseTTSProvider
from app.utils.ffmpeg import run_command_sync, inspect_audio


class MockTTSProvider(BaseTTSProvider):
    def __init__(self, words_per_minute: int = 150):
        self.wpm = words_per_minute

    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: str
    ) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        words = text.strip().split()
        num_words = max(1, len(words))
        # Estimate duration in seconds: (words / wpm) * 60
        duration = round(max(1.0, (num_words / self.wpm) * 60.0), 2)

        # Generate audio using ffmpeg sine wave modulated
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"sine=frequency=440:duration={duration}",
            "-af", "volume=0.4",
            output_path
        ]
        await asyncio.to_thread(run_command_sync, cmd)

        per_word = duration / num_words
        word_timings: List[Dict[str, Any]] = []
        for i, w in enumerate(words):
            word_timings.append({
                "word": w,
                "start": round(i * per_word, 3),
                "end": round((i + 1) * per_word, 3),
            })

        return {
            "audio_path": output_path,
            "duration": duration,
            "voice": voice or "mock-voice",
            "word_timings": word_timings,
        }
