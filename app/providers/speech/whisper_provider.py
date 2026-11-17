import os
from typing import Dict, Any, List
from app.providers.speech.base import BaseSpeechProvider
from app.config import settings
from app.core.exceptions import SilentAudioException, MusicOnlyAudioException, AudioCorruptedException
from app.utils.ffmpeg import inspect_audio
from app.core.logging import logger

_loaded_whisper_model = None


def get_whisper_model():
    global _loaded_whisper_model
    if _loaded_whisper_model is None:
        import whisper
        logger.info(f"Loading Whisper model '{settings.WHISPER_MODEL_SIZE}' on {settings.WHISPER_DEVICE}...")
        _loaded_whisper_model = whisper.load_model(settings.WHISPER_MODEL_SIZE, device=settings.WHISPER_DEVICE)
    return _loaded_whisper_model


class WhisperSpeechProvider(BaseSpeechProvider):
    def transcribe(self, audio_path: str) -> Dict[str, Any]:
        if not os.path.exists(audio_path):
            raise AudioCorruptedException(f"Audio file {audio_path} does not exist.")

        audio_info = inspect_audio(audio_path)
        total_duration = audio_info["duration"]

        try:
            model = get_whisper_model()
            result = model.transcribe(audio_path, word_timestamps=True)
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise AudioCorruptedException(f"Speech transcription failed: {str(e)}")

        raw_text = (result.get("text") or "").strip()
        segments_raw = result.get("segments", [])

        # Validate meaningful speech content
        if not raw_text or len(segments_raw) == 0:
            raise SilentAudioException("Whisper detected no intelligible speech in the audio.")

        parsed_segments: List[Dict[str, Any]] = []
        speech_time = 0.0

        for seg in segments_raw:
            start = round(float(seg.get("start", 0.0)), 3)
            end = round(float(seg.get("end", 0.0)), 3)
            seg_text = (seg.get("text") or "").strip()
            speech_time += max(0.0, end - start)

            words_data: List[Dict[str, Any]] = []
            for w in seg.get("words", []):
                words_data.append({
                    "word": (w.get("word") or "").strip(),
                    "start": round(float(w.get("start", start)), 3),
                    "end": round(float(w.get("end", end)), 3),
                    "confidence": round(float(w.get("probability", 1.0)), 3),
                })

            parsed_segments.append({
                "start": start,
                "end": end,
                "text": seg_text,
                "words": words_data,
            })

        speech_coverage = min(1.0, speech_time / max(0.1, total_duration))
        logger.info(f"Whisper finished: '{raw_text[:60]}...' (speech coverage: {speech_coverage:.1%})")

        # Reject audio with virtually no speech coverage
        if speech_coverage < 0.05 and len(raw_text.split()) < 3:
            raise SilentAudioException("Speech coverage is less than 5% with minimal word content.")

        return {
            "text": raw_text,
            "language": result.get("language", "en"),
            "speech_coverage": round(speech_coverage, 3),
            "segments": parsed_segments,
        }
