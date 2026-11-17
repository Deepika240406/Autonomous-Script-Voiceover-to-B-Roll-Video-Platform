import pyttsx3
import os
import asyncio
from typing import Dict, Any, List
from app.providers.tts.base import BaseTTSProvider
from app.utils.ffmpeg import inspect_audio
from app.core.logging import logger


class Pyttsx3TTSProvider(BaseTTSProvider):
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: str
    ) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        def _run_pyttsx3():
            engine = pyttsx3.init()
            # Set speech rate
            engine.setProperty("rate", 165)
            engine.save_to_file(text, output_path)
            engine.runAndWait()

        await asyncio.to_thread(_run_pyttsx3)
        audio_info = inspect_audio(output_path)
        duration = audio_info["duration"]

        # Approximate word timings if word boundaries not natively emitted by pyttsx3
        words = text.strip().split()
        word_timings: List[Dict[str, Any]] = []
        if words and duration > 0:
            per_word = duration / len(words)
            for i, w in enumerate(words):
                word_timings.append({
                    "word": w,
                    "start": round(i * per_word, 3),
                    "end": round((i + 1) * per_word, 3),
                })

        logger.info(f"Pyttsx3 synthesized {len(text)} chars to {output_path} (duration: {duration:.2f}s)")
        return {
            "audio_path": output_path,
            "duration": duration,
            "voice": "local-pyttsx3",
            "word_timings": word_timings,
        }
