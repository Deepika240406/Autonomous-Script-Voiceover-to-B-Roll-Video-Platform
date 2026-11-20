import edge_tts
import os
import re
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

        spoken_text = text
        # If user requested a Tamil or Hindi voice but provided English Latin text,
        # automatically translate it to native script so the neural voice speaks genuine Tamil/Hindi
        has_latin = bool(re.search(r"[a-zA-Z]", text))
        if has_latin:
            target_lang = None
            if voice_id.startswith("ta-IN-") or voice.startswith("ta-") or "ta-IN" in voice_id:
                target_lang = "ta"
            elif voice_id.startswith("hi-IN-") or voice.startswith("hi-") or "hi-IN" in voice_id:
                target_lang = "hi"

            if target_lang:
                try:
                    from deep_translator import GoogleTranslator
                    sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", text) if s.strip()]
                    translated_parts = []
                    translator = GoogleTranslator(source="auto", target=target_lang)
                    for s in sentences:
                        t = translator.translate(s)
                        translated_parts.append(t if t else s)
                    spoken_text = " ".join(translated_parts)
                    logger.info(f"Translated narration to '{target_lang}' for voice '{voice_id}': '{spoken_text}'")
                except Exception as e:
                    logger.warning(f"GoogleTranslator to {target_lang} failed: {e}. Trying MyMemoryTranslator...")
                    try:
                        from deep_translator import MyMemoryTranslator
                        alt_target = "ta-IN" if target_lang == "ta" else "hi-IN"
                        translator2 = MyMemoryTranslator(source="en-GB", target=alt_target)
                        translated_parts = [translator2.translate(s) or s for s in sentences]
                        spoken_text = " ".join(translated_parts)
                        logger.info(f"MyMemory translated narration to '{alt_target}': '{spoken_text}'")
                    except Exception as e2:
                        logger.warning(f"Translation fallback to {target_lang} encountered: {e2}. Proceeding with original script.")

        communicate = edge_tts.Communicate(spoken_text, voice_id)
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
        logger.info(f"EdgeTTS synthesized {len(spoken_text)} chars to {output_path} (duration: {audio_info['duration']:.2f}s, voice: {voice_id})")

        return {
            "audio_path": output_path,
            "duration": audio_info["duration"],
            "voice": voice_id,
            "word_timings": word_timings,
            "spoken_text": spoken_text,
        }
