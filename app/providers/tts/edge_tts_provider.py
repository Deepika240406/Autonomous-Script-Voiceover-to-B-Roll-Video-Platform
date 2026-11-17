import edge_tts
import os
from typing import Dict, Any, List
from app.providers.tts.base import BaseTTSProvider
from app.utils.ffmpeg import inspect_audio
from app.core.logging import logger


VOICE_MAP = {
    "en-IN-female": "en-IN-NeerjaNeural",
    "en-IN-male": "en-IN-PrabhatNeural",
    "hi-IN-female": "hi-IN-SwaraNeural",
    "hi-IN-male": "hi-IN-MadhurNeural",
    "ta-IN-female": "ta-IN-PallaviNeural",
    "ta-IN-male": "ta-IN-ValluvarNeural",
    "en-US-female": "en-US-JennyNeural",
    "en-US-male": "en-US-GuyNeural",
}


class EdgeTTSProvider(BaseTTSProvider):
    async def synthesize(
        self,
        text: str,
        voice: str,
        output_path: str
    ) -> Dict[str, Any]:
        voice_id = VOICE_MAP.get(voice, voice)
        # Default fallback if unknown
        if not voice_id.endswith("Neural"):
            voice_id = "en-IN-NeerjaNeural"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        communicate = edge_tts.Communicate(text, voice_id)
        submaker = edge_tts.SubMaker()

        word_timings: List[Dict[str, Any]] = []

        with open(output_path, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)
                    offset_sec = chunk["offset"] / 10_000_000.0
                    duration_sec = chunk["duration"] / 10_000_000.0
                    word_timings.append({
                        "word": chunk["text"],
                        "start": round(offset_sec, 3),
                        "end": round(offset_sec + duration_sec, 3),
                    })

        audio_info = inspect_audio(output_path)
        logger.info(f"EdgeTTS synthesized {len(text)} chars to {output_path} (duration: {audio_info['duration']:.2f}s)")

        return {
            "audio_path": output_path,
            "duration": audio_info["duration"],
            "voice": voice_id,
            "word_timings": word_timings,
        }
